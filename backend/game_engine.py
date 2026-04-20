"""
游戏引擎模块 - 炸金花核心游戏逻辑
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from .card_deck import Card, Deck, cards_to_dict
from .hand_evaluator import evaluate_hand, compare_hands
import logging

# 配置日志
logger = logging.getLogger('zhajinhua.game')
logger.setLevel(logging.DEBUG)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class PlayerState(Enum):
    """玩家状态"""
    WAITING = "waiting"      # 等待中
    PLAYING = "playing"      # 游戏中
    LOOKED = "looked"        # 已看牌
    FOLDED = "folded"        # 已弃牌
    OUT = "out"              # 已出局(积分不足)


class GamePhase(Enum):
    """游戏阶段"""
    WAITING = "waiting"      # 等待玩家
    DEALING = "dealing"      # 发牌中
    PLAYING = "playing"      # 游戏进行中
    FINISHED = "finished"    # 本局结束


@dataclass
class Player:
    """玩家数据"""
    id: str
    nickname: str
    points: int = 100
    cards: List[Card] = field(default_factory=list)
    state: PlayerState = PlayerState.WAITING
    has_looked: bool = False
    current_bet: int = 0  # 本局已下注总额

    def to_dict(self, show_cards: bool = False) -> dict:
        """转换为字典，控制是否显示手牌"""
        return {
            "id": self.id,
            "nickname": self.nickname,
            "points": self.points,
            "cards": cards_to_dict(self.cards) if show_cards else [],
            "state": self.state.value,
            "has_looked": self.has_looked,
            "current_bet": self.current_bet
        }


class GameEngine:
    """炸金花游戏引擎"""

    INITIAL_POINTS = 100  # 初始积分
    MIN_PLAYERS = 2       # 最少玩家数
    MAX_PLAYERS = 6       # 最多玩家数

    def __init__(self):
        self.players: Dict[str, Player] = {}
        self.player_order: List[str] = []  # 玩家操作顺序
        self.current_player_idx: int = 0   # 当前玩家索引
        self.deck: Optional[Deck] = None
        self.phase: GamePhase = GamePhase.WAITING
        self.pot: int = 0                  # 总积分池
        self.base_bet: int = 0             # 底注
        self.base_bet_player: Optional[str] = None  # 设置底注的玩家
        self.round_number: int = 0         # 当前回合数
        self.winner: Optional[str] = None  # 本局赢家
        self.history: List[Dict] = []      # 本局历史记录
        self.folded_this_round: Set[str] = set()  # 本局已弃牌的玩家

    def add_history(self, action_type: str, player_id: str, data: Dict = None):
        """添加历史记录"""
        player = self.players.get(player_id)
        record = {
            "round": self.round_number,
            "player_id": player_id,
            "player_nickname": player.nickname if player else "未知",
            "action": action_type,
            "data": data or {}
        }
        self.history.append(record)

    def clear_history(self):
        """清空历史记录（新一局开始时）"""
        self.history = []
        self.folded_this_round = set()

    def add_player(self, player_id: str, nickname: str) -> bool:
        """添加玩家"""
        if len(self.players) >= self.MAX_PLAYERS:
            return False
        if player_id in self.players:
            return False
        if self.phase != GamePhase.WAITING:
            return False

        self.players[player_id] = Player(
            id=player_id,
            nickname=nickname,
            points=self.INITIAL_POINTS
        )
        self.player_order.append(player_id)
        return True

    def remove_player(self, player_id: str) -> bool:
        """移除玩家"""
        if player_id not in self.players:
            return False

        del self.players[player_id]
        if player_id in self.player_order:
            self.player_order.remove(player_id)
        return True

    def start_game(self) -> Dict:
        """开始游戏"""
        if len(self.players) < self.MIN_PLAYERS:
            return {"success": False, "message": f"至少需要{self.MIN_PLAYERS}名玩家"}

        # 初始化牌组
        self.deck = Deck()
        self.deck.shuffle()

        # 重置游戏状态
        self.pot = 0
        self.base_bet = 0
        self.base_bet_player = None
        self.round_number = 1
        self.winner = None
        self.current_player_idx = 0
        self.clear_history()  # 清空历史记录
        self.add_history("game_start", "system", {"players": [p.nickname for p in self.players.values()]})

        # 发牌
        for player_id, player in self.players.items():
            player.cards = self.deck.deal(3)
            player.state = PlayerState.PLAYING
            player.has_looked = False
            player.current_bet = 0

        self.phase = GamePhase.PLAYING

        return {
            "success": True,
            "message": "游戏开始",
            "current_player": self.player_order[0]
        }

    def get_active_players(self) -> List[str]:
        """获取未弃牌的玩家列表"""
        return [
            pid for pid in self.player_order
            if self.players[pid].state not in [PlayerState.FOLDED, PlayerState.OUT]
        ]

    def get_current_player(self) -> Optional[str]:
        """获取当前玩家ID"""
        if not self.player_order:
            return None
        active = self.get_active_players()
        if not active:
            return None
        return active[self.current_player_idx % len(active)]

    def next_player(self) -> Optional[str]:
        """切换到下一个玩家（自动跳过已弃牌的玩家）"""
        active = self.get_active_players()
        logger.debug(f"next_player: active={active}, current_idx={self.current_player_idx}")

        if len(active) <= 1:
            return None

        # 获取当前玩家在活跃列表中的索引
        current = self.get_current_player()
        logger.debug(f"next_player: current_player={current}")

        if current in active:
            current_idx = active.index(current)
            next_idx = (current_idx + 1) % len(active)
        else:
            # 当前玩家不在活跃列表中（如刚弃牌），从索引0开始
            next_idx = self.current_player_idx % len(active)

        self.current_player_idx = next_idx
        self.round_number += 1
        logger.debug(f"next_player: next_idx={next_idx}, next_player={active[next_idx]}")
        return active[next_idx]

    def check_game_over(self) -> bool:
        """检查游戏是否结束"""
        active = self.get_active_players()
        return len(active) <= 1

    def settle_game(self) -> Dict:
        """结算游戏"""
        active = self.get_active_players()

        if len(active) == 1:
            winner_id = active[0]
        else:
            # 多人比牌决胜负
            players_cards = {
                pid: self.players[pid].cards
                for pid in active
            }
            from .hand_evaluator import get_winner
            winner_id = get_winner(players_cards)

        if winner_id:
            self.winner = winner_id
            self.players[winner_id].points += self.pot

        self.phase = GamePhase.FINISHED

        return {
            "winner": winner_id,
            "winner_nickname": self.players[winner_id].nickname if winner_id else None,
            "pot": self.pot,
            "winner_points": self.players[winner_id].points if winner_id else 0
        }

    def action_blind_bet(self, player_id: str, amount: int) -> Dict:
        """
        闷牌(跟牌) - 未看牌时下注
        amount: 1, 2, 或 4
        规则：闷4（最大值）始终可用，其他金额不能低于当前底注
        """
        player = self.players.get(player_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}

        if player.has_looked:
            return {"success": False, "message": "已看牌，不能闷牌"}

        if player.state == PlayerState.FOLDED:
            return {"success": False, "message": "已弃牌"}

        if amount not in [1, 2, 4]:
            return {"success": False, "message": "闷牌金额必须为1、2或4"}

        if player.points < amount:
            return {"success": False, "message": "积分不足"}

        # 如果已有底注，闷牌金额不能低于底注（但闷4始终可用）
        max_blind_bet = 4
        if self.base_bet > 0 and amount < self.base_bet and amount != max_blind_bet:
            return {"success": False, "message": f"闷牌金额不能低于底注({self.base_bet})，或选择闷4"}

        # 扣除积分
        player.points -= amount
        player.current_bet += amount
        self.pot += amount

        # 设置底注(首个下注玩家)或更新底注(如果闷的金额更大)
        if self.base_bet == 0:
            self.base_bet = amount
            self.base_bet_player = player_id
        elif amount > self.base_bet:
            self.base_bet = amount

        logger.info(f"玩家 {player.nickname} 闷牌 {amount}, 底注={self.base_bet}, 积分池={self.pot}")

        # 添加历史记录
        self.add_history("blind_bet", player_id, {"amount": amount, "pot": self.pot})

        # 切换玩家
        next_pid = self.next_player()

        return {
            "success": True,
            "message": f"闷牌{amount}积分",
            "pot": self.pot,
            "base_bet": self.base_bet,
            "next_player": next_pid
        }

    def action_look(self, player_id: str) -> Dict:
        """看牌"""
        player = self.players.get(player_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}

        if player.has_looked:
            return {"success": False, "message": "已经看过牌了"}

        if player.state == PlayerState.FOLDED:
            return {"success": False, "message": "已弃牌"}

        player.has_looked = True
        player.state = PlayerState.LOOKED

        logger.info(f"玩家 {player.nickname} 看牌")

        # 添加历史记录
        self.add_history("look", player_id)

        return {
            "success": True,
            "message": "已看牌",
            "cards": cards_to_dict(player.cards)
        }

    def action_follow(self, player_id: str) -> Dict:
        """跟牌(看牌后) - 投入2X底注"""
        player = self.players.get(player_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}

        if not player.has_looked:
            return {"success": False, "message": "请先看牌"}

        if player.state == PlayerState.FOLDED:
            return {"success": False, "message": "已弃牌"}

        if self.base_bet == 0:
            return {"success": False, "message": "尚无底注"}

        amount = self.base_bet * 2

        if player.points < amount:
            return {"success": False, "message": f"积分不足，需要{amount}积分"}

        player.points -= amount
        player.current_bet += amount
        self.pot += amount

        logger.info(f"玩家 {player.nickname} 跟牌 {amount}, 积分池={self.pot}")

        # 添加历史记录
        self.add_history("follow", player_id, {"amount": amount, "pot": self.pot})

        next_pid = self.next_player()

        return {
            "success": True,
            "message": f"跟牌{amount}积分",
            "pot": self.pot,
            "base_bet": self.base_bet,
            "next_player": next_pid
        }

    def action_fold(self, player_id: str) -> Dict:
        """弃牌"""
        player = self.players.get(player_id)
        if not player:
            return {"success": False, "message": "玩家不存在"}

        if player.state == PlayerState.FOLDED:
            return {"success": False, "message": "已经弃牌了"}

        logger.info(f"玩家 {player.nickname}({player_id}) 弃牌")

        player.state = PlayerState.FOLDED
        self.folded_this_round.add(player_id)

        # 添加历史记录
        self.add_history("fold", player_id)

        # 检查游戏是否结束
        if self.check_game_over():
            result = self.settle_game()
            return {
                "success": True,
                "message": "弃牌成功",
                "game_over": True,
                "result": result
            }

        # 弃牌后，需要找到下一个活跃玩家
        active = self.get_active_players()
        logger.debug(f"弃牌后活跃玩家: {active}")

        # 找到弃牌玩家在player_order中的位置，下一个活跃玩家
        current_idx_in_order = self.player_order.index(player_id)
        for i in range(1, len(self.player_order)):
            next_idx = (current_idx_in_order + i) % len(self.player_order)
            next_pid = self.player_order[next_idx]
            if next_pid in active:
                self.current_player_idx = active.index(next_pid)
                self.round_number += 1
                logger.debug(f"弃牌后下一个玩家: {next_pid}, current_player_idx={self.current_player_idx}")
                return {
                    "success": True,
                    "message": "弃牌成功",
                    "game_over": False,
                    "next_player": next_pid
                }

        return {
            "success": True,
            "message": "弃牌成功",
            "game_over": False,
            "next_player": None
        }

    def action_compare(self, player_id: str, target_id: str) -> Dict:
        """
        开牌比牌
        player_id: 发起比牌的玩家
        target_id: 被比牌的玩家
        """
        player = self.players.get(player_id)
        target = self.players.get(target_id)

        logger.info(f"开牌请求: {player.nickname if player else '?'} vs {target.nickname if target else '?'}")

        if not player or not target:
            return {"success": False, "message": "玩家不存在"}

        if player.state == PlayerState.FOLDED:
            return {"success": False, "message": "已弃牌，无法开牌"}

        if target.state == PlayerState.FOLDED:
            return {"success": False, "message": "目标玩家已弃牌"}

        if self.base_bet == 0:
            return {"success": False, "message": "尚无底注，请先下注"}

        # 计算开牌费用
        if player.has_looked:
            cost = self.base_bet * 2  # 明开
        else:
            cost = self.base_bet  # 闷开

        if player.points < cost:
            return {"success": False, "message": f"积分不足，需要{cost}积分"}

        logger.debug(f"开牌费用: {cost}, 底注: {self.base_bet}, 玩家已看牌: {player.has_looked}")

        # 扣除积分
        player.points -= cost
        player.current_bet += cost
        self.pot += cost

        # 比牌
        result = compare_hands(player.cards, target.cards)

        if result >= 0:  # player赢或平局(主动开牌者赢)
            loser = target
            winner = player
        else:  # target赢
            loser = player
            winner = target

        logger.info(f"开牌结果: {winner.nickname} 获胜, {loser.nickname} 失败")

        loser.state = PlayerState.FOLDED
        self.folded_this_round.add(loser.id)

        # 输家自动看牌
        if not loser.has_looked:
            loser.has_looked = True

        # 判断是否需要显示牌面
        # 规则：场上只剩两人时，把牌面展示给所有人；否则只广播结果
        active_before_compare = len(self.get_active_players()) + 1  # +1 因为输家还没被计入
        logger.debug(f"开牌前活跃玩家数: {active_before_compare}")

        # 只剩两人时（开牌后只剩1人，开牌前是2人），展示牌面给所有人
        should_reveal_cards = active_before_compare == 2

        # 获取牌型信息
        from .hand_evaluator import evaluate_hand
        player_hand = evaluate_hand(player.cards)
        target_hand = evaluate_hand(target.cards)

        # 添加历史记录
        self.add_history("compare", player_id, {
            "target_id": target_id,
            "target_nickname": target.nickname,
            "winner_nickname": winner.nickname,
            "loser_nickname": loser.nickname,
            "pot": self.pot
        })

        compare_result = {
            "winner": winner.id,
            "winner_nickname": winner.nickname,
            "loser": loser.id,
            "loser_nickname": loser.nickname,
            "both_looked": should_reveal_cards,
            "player_cards": cards_to_dict(player.cards) if should_reveal_cards else [],
            "target_cards": cards_to_dict(target.cards) if should_reveal_cards else [],
            "player_hand_type": player_hand.display if should_reveal_cards else "",
            "target_hand_type": target_hand.display if should_reveal_cards else "",
            "player_id": player_id,
            "target_id": target_id,
            "player_nickname": player.nickname,
            "target_nickname": target.nickname,
            # 输家的牌（只给输家自己看）
            "loser_cards": cards_to_dict(loser.cards),
            "loser_hand_type": evaluate_hand(loser.cards).display
        }

        # 检查游戏是否结束
        if self.check_game_over():
            settle_result = self.settle_game()
            self.add_history("game_over", "system", {"winner": winner.nickname, "pot": self.pot})
            return {
                "success": True,
                "message": f"比牌成功，{winner.nickname}获胜",
                "compare_result": compare_result,
                "game_over": True,
                "result": settle_result,
                "pot": self.pot
            }

        # 开牌后，轮转到下一个活跃玩家
        active = self.get_active_players()
        logger.debug(f"开牌后活跃玩家: {active}, 赢家: {winner.id}")

        # 设置当前玩家为赢家，然后切换到下一个
        if winner.id in active:
            self.current_player_idx = active.index(winner.id)
        else:
            self.current_player_idx = 0

        # 切换到下一个玩家
        next_pid = self.next_player()
        logger.debug(f"开牌后下一个玩家: {next_pid}")

        return {
            "success": True,
            "message": f"比牌成功，{winner.nickname}获胜",
            "compare_result": compare_result,
            "game_over": False,
            "next_player": next_pid,
            "pot": self.pot
        }

    def get_game_state(self, for_player_id: Optional[str] = None) -> Dict:
        """获取游戏状态"""
        players_data = []
        for pid in self.player_order:
            player = self.players[pid]
            # 只有自己且已看牌才能看到自己的牌
            show_cards = (pid == for_player_id and player.has_looked)
            players_data.append(player.to_dict(show_cards=show_cards))

        return {
            "phase": self.phase.value,
            "players": players_data,
            "pot": self.pot,
            "base_bet": self.base_bet,
            "current_player": self.get_current_player(),
            "round_number": self.round_number,
            "winner": self.winner,
            "folded_players": list(self.folded_this_round)
        }

    def get_history(self) -> List[Dict]:
        """获取历史记录"""
        return self.history
