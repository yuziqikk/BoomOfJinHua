"""
扑克牌逻辑模块
标准52张牌(无大小王)
"""
import random
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional


class Suit(Enum):
    """花色"""
    SPADE = "♠"      # 黑桃
    HEART = "♥"      # 红心
    CLUB = "♣"       # 梅花
    DIAMOND = "♦"    # 方块


class Rank(Enum):
    """牌面大小"""
    TWO = (2, "2")
    THREE = (3, "3")
    FOUR = (4, "4")
    FIVE = (5, "5")
    SIX = (6, "6")
    SEVEN = (7, "7")
    EIGHT = (8, "8")
    NINE = (9, "9")
    TEN = (10, "10")
    JACK = (11, "J")
    QUEEN = (12, "Q")
    KING = (13, "K")
    ACE = (14, "A")

    def __init__(self, num_value: int, display: str):
        self._num_value = num_value
        self._display = display

    @property
    def num_value(self) -> int:
        return self._num_value

    @property
    def display(self) -> str:
        return self._display


@dataclass
class Card:
    """单张扑克牌"""
    suit: Suit
    rank: Rank

    def __str__(self) -> str:
        return f"{self.suit.value}{self.rank.display}"

    def to_dict(self) -> dict:
        return {
            "suit": self.suit.value,
            "rank": self.rank.display,
            "value": self.rank.num_value
        }


class Deck:
    """一副扑克牌"""

    def __init__(self):
        self.cards: List[Card] = []
        self.reset()

    def reset(self) -> None:
        """重置牌组为完整的52张牌"""
        self.cards = [
            Card(suit, rank)
            for suit in Suit
            for rank in Rank
        ]

    def shuffle(self) -> None:
        """洗牌"""
        random.shuffle(self.cards)

    def deal(self, num: int = 1) -> List[Card]:
        """发牌，从牌组顶部取出指定数量的牌"""
        if num > len(self.cards):
            raise ValueError(f"牌组剩余{len(self.cards)}张，无法发{num}张")

        dealt_cards = self.cards[:num]
        self.cards = self.cards[num:]
        return dealt_cards

    def deal_hand(self, num_players: int, cards_per_player: int = 3) -> List[List[Card]]:
        """
        给多个玩家发牌
        返回: 每个玩家的手牌列表
        """
        total_cards = num_players * cards_per_player
        if total_cards > len(self.cards):
            raise ValueError(f"牌组剩余{len(self.cards)}张，无法为{num_players}人每人发{cards_per_player}张")

        hands = []
        for _ in range(num_players):
            hand = self.deal(cards_per_player)
            hands.append(hand)
        return hands

    def remaining(self) -> int:
        """剩余牌数"""
        return len(self.cards)


def create_shuffled_deck() -> Deck:
    """创建并洗好一副牌"""
    deck = Deck()
    deck.shuffle()
    return deck


def cards_to_dict(cards: List[Card]) -> List[dict]:
    """将牌列表转换为字典列表(用于JSON序列化)"""
    return [card.to_dict() for card in cards]
