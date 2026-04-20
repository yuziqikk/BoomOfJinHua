"""
金花对决 - Flask + SocketIO 后端
"""
from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import os

from .room_manager import room_manager
from .game_engine import GameEngine, Player, GamePhase

app = Flask(__name__,
            static_folder='../frontend',
            template_folder='../frontend')
app.config['SECRET_KEY'] = 'zhajinhua-secret-key-2024'

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


# ==================== HTTP路由 ====================

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/<path:path>')
def static_files(path):
    """静态文件"""
    return send_from_directory('../frontend', path)


# ==================== Socket.IO事件 ====================

@socketio.on('connect')
def on_connect():
    """客户端连接"""
    print(f"客户端连接: {request.sid}")
    emit('connected', {'message': '连接成功'})


@socketio.on('disconnect')
def on_disconnect():
    """客户端断开连接"""
    print(f"客户端断开: {request.sid}")
    # 查找该sid对应的玩家并标记为断线
    for room_id, room in list(room_manager.rooms.items()):
        for player_id, sid in list(room.player_sids.items()):
            if sid == request.sid:
                player = room.game.players.get(player_id)
                nickname = player.nickname if player else None

                result = room_manager.leave_room(player_id)

                # 通知房间内其他玩家
                if '断线' in result.get('message', ''):
                    socketio.emit('player_disconnected', {
                        'player_id': player_id,
                        'nickname': nickname,
                        'players': [p.to_dict() for p in room.game.players.values()]
                    }, room=room_id)
                else:
                    socketio.emit('player_left', {
                        'player_id': player_id,
                        'players': [p.to_dict() for p in room.game.players.values()]
                    }, room=room_id)
                break


@socketio.on('create_room')
def on_create_room(data):
    """创建房间"""
    nickname = data.get('nickname', '玩家')
    room_name = data.get('room_name', '炸金花房间')
    player_id = data.get('player_id') or request.sid

    result = room_manager.create_room(player_id, nickname, room_name)

    if result['success']:
        room_id = result['room_id']
        room_manager.set_player_sid(room_id, player_id, request.sid)
        join_room(room_id)

        room = room_manager.get_room(room_id)
        emit('room_created', {
            'room_id': room_id,
            'room': room.to_dict(),
            'player_id': player_id,
            'players': [p.to_dict() for p in room.game.players.values()]
        })
    else:
        emit('error', {'message': result.get('message', '创建房间失败')})


@socketio.on('join_room')
def on_join_room(data):
    """加入房间"""
    room_id = data.get('room_id')
    nickname = data.get('nickname', '玩家')
    player_id = data.get('player_id') or request.sid

    if not room_id:
        emit('error', {'message': '请输入房间号'})
        return

    result = room_manager.join_room(player_id, nickname, room_id, request.sid)

    if result['success']:
        join_room(room_id)
        room = room_manager.get_room(room_id)

        # 通知所有房间内玩家
        socketio.emit('player_joined', {
            'player_id': player_id,
            'nickname': nickname,
            'players': [p.to_dict() for p in room.game.players.values()],
            'host_id': room.host_id
        }, room=room_id)

        # 发送给加入的玩家
        response = {
            'room_id': room_id,
            'room': room.to_dict(),
            'player_id': player_id,
            'players': result['players'],
            'reconnected': result.get('reconnected', False)
        }

        # 如果是重连，返回游戏状态
        if result.get('reconnected'):
            response['game_state'] = room.game.get_game_state(for_player_id=player_id)
            player = room.game.players.get(player_id)
            if player and player.has_looked:
                response['your_cards'] = [c.to_dict() for c in player.cards]

        emit('room_joined', response)
    else:
        emit('error', {'message': result.get('message', '加入房间失败')})


@socketio.on('leave_room')
def on_leave_room(data):
    """离开房间"""
    player_id = data.get('player_id') or request.sid

    room = room_manager.get_player_room(player_id)
    if room:
        room_id = room.id
        leave_room(room_id)
        result = room_manager.leave_room(player_id)

        # 通知房间内其他玩家
        socketio.emit('player_left', {
            'player_id': player_id
        }, room=room_id)

    emit('room_left', {'success': True})


@socketio.on('start_game')
def on_start_game(data):
    """开始游戏"""
    player_id = data.get('player_id') or request.sid

    room = room_manager.get_player_room(player_id)
    if not room:
        emit('error', {'message': '未在任何房间'})
        return

    # 只有房主可以开始游戏
    if room.host_id != player_id:
        emit('error', {'message': '只有房主可以开始游戏'})
        return

    result = room.game.start_game()

    if result['success']:
        # 通知所有玩家游戏开始
        game_state = room.game.get_game_state()

        # 分别给每个玩家发送他们的手牌
        for pid, player in room.game.players.items():
            sid = room.player_sids.get(pid)
            if sid:
                personal_state = room.game.get_game_state(for_player_id=pid)
                socketio.emit('game_started', {
                    'game_state': personal_state,
                    'your_cards': [c.to_dict() for c in player.cards]
                }, room=sid)

        # 广播游戏状态(不含手牌)
        socketio.emit('game_update', {
            'game_state': game_state
        }, room=room.id)
    else:
        emit('error', {'message': result.get('message', '开始游戏失败')})


@socketio.on('look_cards')
def on_look_cards(data):
    """看牌"""
    player_id = data.get('player_id') or request.sid

    room = room_manager.get_player_room(player_id)
    if not room:
        emit('error', {'message': '未在任何房间'})
        return

    result = room.game.action_look(player_id)

    if result['success']:
        # 只发送给看牌的玩家
        sid = room.player_sids.get(player_id)
        if sid:
            socketio.emit('cards_revealed', {
                'cards': result['cards'],
                'player_id': player_id
            }, room=sid)

        # 广播玩家已看牌状态
        game_state = room.game.get_game_state()
        socketio.emit('game_update', {
            'game_state': game_state
        }, room=room.id)
    else:
        emit('error', {'message': result.get('message', '看牌失败')})


@socketio.on('blind_bet')
def on_blind_bet(data):
    """闷牌"""
    player_id = data.get('player_id') or request.sid
    amount = data.get('amount', 1)

    room = room_manager.get_player_room(player_id)
    if not room:
        emit('error', {'message': '未在任何房间'})
        return

    result = room.game.action_blind_bet(player_id, amount)

    if result['success']:
        game_state = room.game.get_game_state()
        socketio.emit('game_update', {
            'game_state': game_state,
            'last_action': {
                'player_id': player_id,
                'action': 'blind_bet',
                'amount': amount
            }
        }, room=room.id)
    else:
        emit('error', {'message': result.get('message', '闷牌失败')})


@socketio.on('follow')
def on_follow(data):
    """跟牌(看牌后)"""
    player_id = data.get('player_id') or request.sid

    room = room_manager.get_player_room(player_id)
    if not room:
        emit('error', {'message': '未在任何房间'})
        return

    result = room.game.action_follow(player_id)

    if result['success']:
        game_state = room.game.get_game_state()
        socketio.emit('game_update', {
            'game_state': game_state,
            'last_action': {
                'player_id': player_id,
                'action': 'follow'
            }
        }, room=room.id)
    else:
        emit('error', {'message': result.get('message', '跟牌失败')})


@socketio.on('fold')
def on_fold(data):
    """弃牌"""
    player_id = data.get('player_id') or request.sid

    room = room_manager.get_player_room(player_id)
    if not room:
        emit('error', {'message': '未在任何房间'})
        return

    result = room.game.action_fold(player_id)

    if result['success']:
        game_state = room.game.get_game_state()

        if result.get('game_over'):
            socketio.emit('game_over', {
                'game_state': game_state,
                'result': result['result'],
                'last_action': {
                    'player_id': player_id,
                    'action': 'fold'
                }
            }, room=room.id)
        else:
            socketio.emit('game_update', {
                'game_state': game_state,
                'last_action': {
                    'player_id': player_id,
                    'action': 'fold'
                }
            }, room=room.id)
    else:
        emit('error', {'message': result.get('message', '弃牌失败')})


@socketio.on('compare')
def on_compare(data):
    """开牌比牌"""
    player_id = data.get('player_id') or request.sid
    target_id = data.get('target_id')

    if not target_id:
        emit('error', {'message': '请选择比牌对象'})
        return

    room = room_manager.get_player_room(player_id)
    if not room:
        emit('error', {'message': '未在任何房间'})
        return

    result = room.game.action_compare(player_id, target_id)

    if result['success']:
        game_state = room.game.get_game_state()

        if result.get('game_over'):
            socketio.emit('game_over', {
                'game_state': game_state,
                'result': result['result'],
                'compare_result': result['compare_result'],
                'last_action': {
                    'player_id': player_id,
                    'action': 'compare',
                    'target_id': target_id
                }
            }, room=room.id)
        else:
            # 游戏未结束，但需要显示比牌结果
            socketio.emit('compare_result', {
                'game_state': game_state,
                'compare_result': result['compare_result'],
                'last_action': {
                    'player_id': player_id,
                    'action': 'compare',
                    'target_id': target_id
                }
            }, room=room.id)
    else:
        emit('error', {'message': result.get('message', '开牌失败')})


@socketio.on('get_game_state')
def on_get_game_state(data):
    """获取游戏状态"""
    player_id = data.get('player_id') or request.sid

    room = room_manager.get_player_room(player_id)
    if not room:
        emit('error', {'message': '未在任何房间'})
        return

    game_state = room.game.get_game_state(for_player_id=player_id)
    emit('game_state', {'game_state': game_state, 'history': room.game.get_history()})


@socketio.on('get_history')
def on_get_history(data):
    """获取历史记录"""
    player_id = data.get('player_id') or request.sid

    room = room_manager.get_player_room(player_id)
    if not room:
        emit('error', {'message': '未在任何房间'})
        return

    emit('history', {'history': room.game.get_history()})


@socketio.on('new_game')
def on_new_game(data):
    """开始新一局"""
    player_id = data.get('player_id') or request.sid

    room = room_manager.get_player_room(player_id)
    if not room:
        emit('error', {'message': '未在任何房间'})
        return

    # 只有房主可以开始新一局
    if room.host_id != player_id:
        emit('error', {'message': '只有房主可以开始新一局'})
        return

    # 先保存玩家信息
    players_info = [(p.id, p.nickname, p.points) for p in list(room.game.players.values())]

    # 重置游戏引擎
    from .game_engine import GameEngine, Player
    room.game = GameEngine()

    # 重新添加所有玩家(保留积分)
    for pid, nickname, points in players_info:
        room.game.players[pid] = Player(
            id=pid,
            nickname=nickname,
            points=points
        )
        room.game.player_order.append(pid)

    result = room.game.start_game()

    if result['success']:
        # 添加新一局分割记录
        room.game.add_history("new_game", "system", {"players": [p.nickname for p in room.game.players.values()]})

        game_state = room.game.get_game_state()

        # 分别给每个玩家发送他们的手牌
        for pid, player in room.game.players.items():
            sid = room.player_sids.get(pid)
            if sid:
                personal_state = room.game.get_game_state(for_player_id=pid)
                socketio.emit('game_started', {
                    'game_state': personal_state,
                    'your_cards': [c.to_dict() for c in player.cards]
                }, room=sid)

        # 广播游戏状态(不含手牌)给房间内所有人
        socketio.emit('game_update', {
            'game_state': game_state
        }, room=room.id)
    else:
        emit('error', {'message': result.get('message', '开始新游戏失败')})


def run_server(host='0.0.0.0', port=5002, debug=True):
    """启动服务器"""
    print(f"炸金花游戏服务器启动: http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    run_server()
