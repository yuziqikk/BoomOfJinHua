"""
牌型判断模块 - 炸金花规则
牌型从大到小: 豹子 > 同花顺 > 同花 > 顺子 > 对子 > 单张
"""
from enum import IntEnum
from dataclasses import dataclass
from typing import List, Tuple
from .card_deck import Card, Rank


class HandType(IntEnum):
    """牌型枚举，值越大牌型越大"""
    HIGH_CARD = 1      # 单张
    PAIR = 2           # 对子
    STRAIGHT = 3       # 顺子
    FLUSH = 4          # 同花
    STRAIGHT_FLUSH = 5 # 同花顺
    THREE_OF_KIND = 6  # 豹子


@dataclass
class HandResult:
    """手牌判断结果"""
    hand_type: HandType
    rank_values: Tuple[int, int, int]  # 用于比较的牌值(从大到小)
    display: str  # 牌型显示名称

    def __lt__(self, other: 'HandResult') -> bool:
        """比较两个手牌结果"""
        if self.hand_type != other.hand_type:
            return self.hand_type < other.hand_type
        return self.rank_values < other.rank_values

    def __eq__(self, other: 'HandResult') -> bool:
        return self.hand_type == other.hand_type and self.rank_values == other.rank_values

    def __gt__(self, other: 'HandResult') -> bool:
        return not self < other and not self == other


def get_rank_values(cards: List[Card]) -> List[int]:
    """获取牌面值列表"""
    return sorted([card.rank.num_value for card in cards], reverse=True)


def is_flush(cards: List[Card]) -> bool:
    """判断是否同花(三张牌花色相同)"""
    return len(set(card.suit for card in cards)) == 1


def is_straight(rank_values: List[int]) -> bool:
    """判断是否顺子"""
    sorted_values = sorted(rank_values)

    # 特殊情况: A23 (最小顺子)
    if sorted_values == [2, 3, 14]:
        return True

    # 普通顺子: 连续三张
    return sorted_values[2] - sorted_values[0] == 2 and len(set(sorted_values)) == 3


def is_three_of_kind(rank_values: List[int]) -> bool:
    """判断是否豹子(三张相同)"""
    return len(set(rank_values)) == 1


def is_pair(rank_values: List[int]) -> bool:
    """判断是否对子"""
    return len(set(rank_values)) == 2


def evaluate_hand(cards: List[Card]) -> HandResult:
    """
    评估三张牌的牌型
    返回HandResult对象，包含牌型和比较值
    """
    if len(cards) != 3:
        raise ValueError("炸金花需要3张牌")

    rank_values = get_rank_values(cards)

    # 检查豹子
    if is_three_of_kind(rank_values):
        return HandResult(
            hand_type=HandType.THREE_OF_KIND,
            rank_values=(rank_values[0], rank_values[0], rank_values[0]),
            display="豹子"
        )

    flush = is_flush(cards)
    straight = is_straight(rank_values)

    # 检查同花顺
    if flush and straight:
        # A23顺子特殊处理，比较值设为3,2,1(最小)
        if sorted(rank_values) == [2, 3, 14]:
            return HandResult(
                hand_type=HandType.STRAIGHT_FLUSH,
                rank_values=(3, 2, 1),
                display="同花顺"
            )
        return HandResult(
            hand_type=HandType.STRAIGHT_FLUSH,
            rank_values=tuple(rank_values),
            display="同花顺"
        )

    # 检查同花
    if flush:
        return HandResult(
            hand_type=HandType.FLUSH,
            rank_values=tuple(rank_values),
            display="同花"
        )

    # 检查顺子
    if straight:
        # A23顺子特殊处理
        if sorted(rank_values) == [2, 3, 14]:
            return HandResult(
                hand_type=HandType.STRAIGHT,
                rank_values=(3, 2, 1),
                display="顺子"
            )
        return HandResult(
            hand_type=HandType.STRAIGHT,
            rank_values=tuple(rank_values),
            display="顺子"
        )

    # 检查对子
    if is_pair(rank_values):
        # 对子的比较值: 对子在前，单张在后
        values_count = {}
        for v in rank_values:
            values_count[v] = values_count.get(v, 0) + 1

        pair_value = [v for v, c in values_count.items() if c == 2][0]
        single_value = [v for v, c in values_count.items() if c == 1][0]

        return HandResult(
            hand_type=HandType.PAIR,
            rank_values=(pair_value, pair_value, single_value),
            display="对子"
        )

    # 单张
    return HandResult(
        hand_type=HandType.HIGH_CARD,
        rank_values=tuple(rank_values),
        display="单张"
    )


def compare_hands(cards1: List[Card], cards2: List[Card]) -> int:
    """
    比较两手牌大小
    返回: 1表示cards1大，-1表示cards2大，0表示平局
    """
    result1 = evaluate_hand(cards1)
    result2 = evaluate_hand(cards2)

    if result1 > result2:
        return 1
    elif result1 < result2:
        return -1
    else:
        return 0


def get_winner(players_cards: dict) -> str:
    """
    从多个玩家中找出赢家
    players_cards: {player_id: cards}
    返回: 赢家的player_id
    """
    best_player = None
    best_result = None

    for player_id, cards in players_cards.items():
        result = evaluate_hand(cards)
        if best_result is None or result > best_result:
            best_result = result
            best_player = player_id

    return best_player
