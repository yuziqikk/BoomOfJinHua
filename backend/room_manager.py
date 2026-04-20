"""
房间管理模块
"""
import uuid
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from .game_engine import GameEngine, GamePhase


@dataclass
class Room:
    """游戏房间"""
    id: str
    name: str
    host_id: str  # 房主ID
    created_at: float = field(default_factory=time.time)
    game: GameEngine = field(default_factory=GameEngine)
    player_sids: Dict[str, str] = field(default_factory=dict)  # player_id -> socket_sid
    disconnected_players: Dict[str, str] = field(default_factory=dict)  # nickname -> player_id (断线玩家)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "host_id": self.host_id,
            "player_count": len(self.game.players),
            "phase": self.game.phase.value
        }


class RoomManager:
    """房间管理器"""

    def __init__(self):
        self.rooms: Dict[str, Room] = {}  # room_id -> Room
        self.player_rooms: Dict[str, str] = {}  # player_id -> room_id

    def generate_room_id(self) -> str:
        """生成房间ID (6位数字)"""
        return str(uuid.uuid4().int)[:6]

    def create_room(self, host_id: str, host_nickname: str, room_name: str = "炸金花房间") -> Dict:
        """创建房间"""
        # 如果玩家已在其他房间，先离开
        if host_id in self.player_rooms:
            self.leave_room(host_id)

        room_id = self.generate_room_id()
        while room_id in self.rooms:  # 确保ID唯一
            room_id = self.generate_room_id()

        room = Room(
            id=room_id,
            name=room_name,
            host_id=host_id
        )

        # 房主加入游戏
        room.game.add_player(host_id, host_nickname)

        self.rooms[room_id] = room
        self.player_rooms[host_id] = room_id

        return {
            "success": True,
            "room_id": room_id,
            "room": room.to_dict()
        }

    def join_room(self, player_id: str, nickname: str, room_id: str, sid: str = None) -> Dict:
        """加入房间"""
        if room_id not in self.rooms:
            return {"success": False, "message": "房间不存在"}

        room = self.rooms[room_id]

        # 检查是否有同昵称的断线玩家需要重连
        if nickname in room.disconnected_players:
            old_player_id = room.disconnected_players[nickname]
            # 恢复玩家连接
            if old_player_id in room.game.players:
                # 更新player_id映射（可能已被删除）
                if old_player_id in self.player_rooms:
                    del self.player_rooms[old_player_id]
                self.player_rooms[player_id] = room_id

                # 更新游戏中的玩家ID
                player_data = room.game.players[old_player_id]
                del room.game.players[old_player_id]
                room.game.players[player_id] = player_data

                # 更新玩家顺序
                if old_player_id in room.game.player_order:
                    idx = room.game.player_order.index(old_player_id)
                    room.game.player_order[idx] = player_id

                # 更新房主
                if room.host_id == old_player_id:
                    room.host_id = player_id

                # 更新sid
                if sid:
                    room.player_sids[player_id] = sid

                # 移除断线记录
                del room.disconnected_players[nickname]

                return {
                    "success": True,
                    "room": room.to_dict(),
                    "players": [p.to_dict() for p in room.game.players.values()],
                    "reconnected": True
                }

        # 检查游戏是否已开始
        if room.game.phase != GamePhase.WAITING:
            return {"success": False, "message": "游戏已开始，无法加入"}

        # 检查房间是否已满
        if len(room.game.players) >= GameEngine.MAX_PLAYERS:
            return {"success": False, "message": "房间已满"}

        # 如果玩家已在其他房间，先离开
        if player_id in self.player_rooms:
            old_room_id = self.player_rooms[player_id]
            if old_room_id != room_id:
                self.leave_room(player_id)

        # 加入游戏
        if not room.game.add_player(player_id, nickname):
            return {"success": False, "message": "加入失败"}

        # 记录socket sid
        if sid:
            room.player_sids[player_id] = sid

        self.player_rooms[player_id] = room_id

        return {
            "success": True,
            "room": room.to_dict(),
            "players": [p.to_dict() for p in room.game.players.values()],
            "reconnected": False
        }

    def leave_room(self, player_id: str, force_remove: bool = False) -> Dict:
        """
        离开房间
        force_remove: True表示强制移除玩家(如房间关闭)，False表示标记为断线(可重连)
        """
        if player_id not in self.player_rooms:
            return {"success": False, "message": "未在任何房间"}

        room_id = self.player_rooms[player_id]
        room = self.rooms.get(room_id)

        if not room:
            del self.player_rooms[player_id]
            return {"success": False, "message": "房间不存在"}

        player = room.game.players.get(player_id)

        # 如果游戏进行中且不是强制移除，标记为断线玩家
        if room.game.phase != GamePhase.WAITING and not force_remove and player:
            room.disconnected_players[player.nickname] = player_id
            # 移除sid但保留玩家数据
            if player_id in room.player_sids:
                del room.player_sids[player_id]
            del self.player_rooms[player_id]
            return {"success": True, "message": "已断线，可重新连接"}

        # 从游戏中移除
        room.game.remove_player(player_id)

        # 移除socket sid
        if player_id in room.player_sids:
            del room.player_sids[player_id]

        # 从断线记录中移除
        if player and player.nickname in room.disconnected_players:
            del room.disconnected_players[player.nickname]

        del self.player_rooms[player_id]

        # 如果房间空了，删除房间
        if len(room.game.players) == 0:
            del self.rooms[room_id]
            return {"success": True, "message": "离开成功，房间已关闭"}

        # 如果房主离开，转移房主
        if room.host_id == player_id:
            remaining_players = list(room.game.players.keys())
            if remaining_players:
                room.host_id = remaining_players[0]

        return {"success": True, "message": "离开成功"}

    def get_room(self, room_id: str) -> Optional[Room]:
        """获取房间"""
        return self.rooms.get(room_id)

    def get_player_room(self, player_id: str) -> Optional[Room]:
        """获取玩家所在的房间"""
        if player_id not in self.player_rooms:
            return None
        return self.rooms.get(self.player_rooms[player_id])

    def get_room_players(self, room_id: str) -> List[str]:
        """获取房间内所有玩家ID"""
        room = self.rooms.get(room_id)
        if not room:
            return []
        return list(room.game.players.keys())

    def get_player_sid(self, room_id: str, player_id: str) -> Optional[str]:
        """获取玩家的socket sid"""
        room = self.rooms.get(room_id)
        if not room:
            return None
        return room.player_sids.get(player_id)

    def set_player_sid(self, room_id: str, player_id: str, sid: str):
        """设置玩家的socket sid"""
        room = self.rooms.get(room_id)
        if room:
            room.player_sids[player_id] = sid

    def list_rooms(self) -> List[dict]:
        """列出所有房间"""
        return [room.to_dict() for room in self.rooms.values()]


# 全局房间管理器实例
room_manager = RoomManager()
