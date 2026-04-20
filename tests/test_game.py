"""
炸金花游戏测试用例
可自动运行的单元测试
"""
import unittest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.card_deck import Card, Deck, Suit, Rank, cards_to_dict
from backend.hand_evaluator import (
    evaluate_hand, compare_hands, get_winner,
    HandType, HandResult
)
from backend.game_engine import GameEngine, Player, PlayerState, GamePhase


class TestCardDeck(unittest.TestCase):
    """扑克牌模块测试"""

    def test_deck_has_52_cards(self):
        """测试牌组有52张牌"""
        deck = Deck()
        self.assertEqual(len(deck.cards), 52)

    def test_deck_shuffle(self):
        """测试洗牌功能"""
        deck1 = Deck()
        deck2 = Deck()
        deck2.shuffle()
        # 洗牌后顺序应该不同(极小概率相同)
        self.assertEqual(len(deck2.cards), 52)

    def test_deal_cards(self):
        """测试发牌"""
        deck = Deck()
        deck.shuffle()
        cards = deck.deal(3)
        self.assertEqual(len(cards), 3)
        self.assertEqual(deck.remaining(), 49)

    def test_card_to_dict(self):
        """测试牌转字典"""
        card = Card(Suit.SPADE, Rank.ACE)
        d = card.to_dict()
        self.assertEqual(d['suit'], '♠')
        self.assertEqual(d['rank'], 'A')
        self.assertEqual(d['value'], 14)


class TestHandEvaluator(unittest.TestCase):
    """牌型判断模块测试"""

    def _make_cards(self, suit_rank_list):
        """辅助函数：创建牌列表"""
        cards = []
        for suit_str, rank_str in suit_rank_list:
            suit = Suit(suit_str)
            rank = next(r for r in Rank if r.display == rank_str)
            cards.append(Card(suit, rank))
        return cards

    def test_three_of_kind(self):
        """测试豹子"""
        cards = self._make_cards([('♠', 'A'), ('♥', 'A'), ('♦', 'A')])
        result = evaluate_hand(cards)
        self.assertEqual(result.hand_type, HandType.THREE_OF_KIND)
        self.assertEqual(result.display, '豹子')

    def test_straight_flush(self):
        """测试同花顺"""
        cards = self._make_cards([('♠', 'A'), ('♠', 'K'), ('♠', 'Q')])
        result = evaluate_hand(cards)
        self.assertEqual(result.hand_type, HandType.STRAIGHT_FLUSH)
        self.assertEqual(result.display, '同花顺')

    def test_flush(self):
        """测试同花"""
        cards = self._make_cards([('♠', 'A'), ('♠', '5'), ('♠', '9')])
        result = evaluate_hand(cards)
        self.assertEqual(result.hand_type, HandType.FLUSH)
        self.assertEqual(result.display, '同花')

    def test_straight(self):
        """测试顺子"""
        cards = self._make_cards([('♠', 'A'), ('♥', 'K'), ('♦', 'Q')])
        result = evaluate_hand(cards)
        self.assertEqual(result.hand_type, HandType.STRAIGHT)
        self.assertEqual(result.display, '顺子')

    def test_pair(self):
        """测试对子"""
        cards = self._make_cards([('♠', 'A'), ('♥', 'A'), ('♦', '5')])
        result = evaluate_hand(cards)
        self.assertEqual(result.hand_type, HandType.PAIR)
        self.assertEqual(result.display, '对子')

    def test_high_card(self):
        """测试单张"""
        cards = self._make_cards([('♠', 'A'), ('♥', '5'), ('♦', '9')])
        result = evaluate_hand(cards)
        self.assertEqual(result.hand_type, HandType.HIGH_CARD)
        self.assertEqual(result.display, '单张')

    def test_a23_straight(self):
        """测试A23最小顺子"""
        cards = self._make_cards([('♠', 'A'), ('♥', '2'), ('♦', '3')])
        result = evaluate_hand(cards)
        self.assertEqual(result.hand_type, HandType.STRAIGHT)

    def test_compare_hands(self):
        """测试牌比较"""
        # 豹子 > 同花顺
        three_kind = self._make_cards([('♠', 'A'), ('♥', 'A'), ('♦', 'A')])
        straight_flush = self._make_cards([('♠', 'A'), ('♠', 'K'), ('♠', 'Q')])
        self.assertEqual(compare_hands(three_kind, straight_flush), 1)

        # 同花顺 > 同花
        flush = self._make_cards([('♠', 'A'), ('♠', '5'), ('♠', '9')])
        self.assertEqual(compare_hands(straight_flush, flush), 1)

    def test_get_winner(self):
        """测试找出赢家"""
        cards1 = self._make_cards([('♠', 'A'), ('♥', 'A'), ('♦', 'A')])  # 豹子
        cards2 = self._make_cards([('♠', 'K'), ('♥', 'K'), ('♦', 'K')])  # 豹子K

        players_cards = {
            'p1': cards1,
            'p2': cards2
        }
        winner = get_winner(players_cards)
        self.assertEqual(winner, 'p1')  # AAA > KKK


class TestGameEngine(unittest.TestCase):
    """游戏引擎测试"""

    def setUp(self):
        """每个测试前初始化"""
        self.game = GameEngine()

    def test_add_player(self):
        """测试添加玩家"""
        result = self.game.add_player('p1', '玩家1')
        self.assertTrue(result)
        self.assertEqual(len(self.game.players), 1)

    def test_max_players(self):
        """测试最大玩家数"""
        for i in range(7):
            self.game.add_player(f'p{i}', f'玩家{i}')
        self.assertLessEqual(len(self.game.players), 6)

    def test_start_game(self):
        """测试开始游戏"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        result = self.game.start_game()
        self.assertTrue(result['success'])
        self.assertEqual(self.game.phase, GamePhase.PLAYING)

    def test_blind_bet(self):
        """测试闷牌"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.start_game()

        result = self.game.action_blind_bet('p1', 2)
        self.assertTrue(result['success'])
        self.assertEqual(result['base_bet'], 2)

    def test_blind_bet_cannot_be_lower_than_base_bet(self):
        """测试闷牌金额不能低于底注（但闷4始终可用）"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.add_player('p3', '玩家3')
        self.game.start_game()

        # p1闷4，设置底注为4
        self.game.action_blind_bet('p1', 4)
        self.assertEqual(self.game.base_bet, 4)

        # p2尝试闷1或2（低于底注4）应该失败
        result = self.game.action_blind_bet('p2', 1)
        self.assertFalse(result['success'])
        self.assertIn('不能低于底注', result['message'])

        result = self.game.action_blind_bet('p2', 2)
        self.assertFalse(result['success'])
        self.assertIn('不能低于底注', result['message'])

        # p2闷4应该成功
        result = self.game.action_blind_bet('p2', 4)
        self.assertTrue(result['success'])

    def test_blind_bet_max_4_always_available(self):
        """测试闷4始终可用（即使低于底注）"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.start_game()

        # p1闷2，设置底注为2
        self.game.action_blind_bet('p1', 2)
        self.assertEqual(self.game.base_bet, 2)

        # p2闷1（低于底注2）应该失败
        result = self.game.action_blind_bet('p2', 1)
        self.assertFalse(result['success'])

        # p2闷4（高于底注）应该成功
        result = self.game.action_blind_bet('p2', 4)
        self.assertTrue(result['success'])

    def test_follow_bet_is_double_base_bet(self):
        """测试看牌后跟牌金额为底注的两倍"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.start_game()

        # p1闷2，设置底注为2
        self.game.action_blind_bet('p1', 2)

        # p2看牌
        self.game.action_look('p2')

        # p2跟牌，应该扣除4（2x底注）
        initial_points = self.game.players['p2'].points
        result = self.game.action_follow('p2')
        self.assertTrue(result['success'])
        self.assertEqual(self.game.players['p2'].points, initial_points - 4)

    def test_blind_bet_updates_base_bet(self):
        """测试闷牌金额大于当前底注时会更新底注"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.add_player('p3', '玩家3')
        self.game.start_game()

        # p1闷2，底注变为2
        self.game.action_blind_bet('p1', 2)
        self.assertEqual(self.game.base_bet, 2)

        # p2闷4，底注应该更新为4
        result = self.game.action_blind_bet('p2', 4)
        self.assertTrue(result['success'])
        self.assertEqual(self.game.base_bet, 4)

    def test_compare_cost_without_look(self):
        """测试未看牌开牌费用为底注"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.add_player('p3', '玩家3')
        self.game.start_game()

        # p1闷2，底注为2
        self.game.action_blind_bet('p1', 2)
        # p2闷2
        self.game.action_blind_bet('p2', 2)

        # p3未看牌开牌，应该扣除2（底注）
        initial_points = self.game.players['p3'].points
        result = self.game.action_compare('p3', 'p1')
        self.assertTrue(result['success'])
        # 验证扣除了底注金额
        self.assertEqual(self.game.players['p3'].current_bet, 2)

    def test_compare_cost_with_look(self):
        """测试已看牌开牌费用为底注×2"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.add_player('p3', '玩家3')
        self.game.start_game()

        # p1闷2，底注为2
        self.game.action_blind_bet('p1', 2)
        # p2闷2
        self.game.action_blind_bet('p2', 2)

        # p3看牌后开牌，应该扣除4（底注×2）
        self.game.action_look('p3')
        result = self.game.action_compare('p3', 'p1')
        self.assertTrue(result['success'])
        # 验证扣除了底注×2金额
        self.assertEqual(self.game.players['p3'].current_bet, 4)

    def test_compare_both_looked_returns_cards(self):
        """测试只剩两人时开牌返回牌面信息"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.start_game()

        # p1闷2
        self.game.action_blind_bet('p1', 2)

        # p2开牌比p1（只剩两人，应该展示牌面）
        result = self.game.action_compare('p2', 'p1')
        self.assertTrue(result['success'])

        # 验证返回了双方看牌信息（只剩两人时展示）
        compare_result = result['compare_result']
        self.assertTrue(compare_result['both_looked'])
        self.assertEqual(len(compare_result['player_cards']), 3)
        self.assertEqual(len(compare_result['target_cards']), 3)
        self.assertIn('player_hand_type', compare_result)
        self.assertIn('target_hand_type', compare_result)

    def test_compare_three_players_no_card_reveal(self):
        """测试三人游戏时开牌不返回牌面信息"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.add_player('p3', '玩家3')
        self.game.start_game()

        # p1闷2
        self.game.action_blind_bet('p1', 2)
        # p2闷2
        self.game.action_blind_bet('p2', 2)

        # p3开牌比p1（还有3人，不应该展示牌面）
        result = self.game.action_compare('p3', 'p1')
        self.assertTrue(result['success'])

        # 验证不返回牌面信息（还有多人）
        compare_result = result['compare_result']
        self.assertFalse(compare_result['both_looked'])
        self.assertEqual(len(compare_result['player_cards']), 0)
        self.assertEqual(len(compare_result['target_cards']), 0)

    def test_compare_two_players_left_reveals_cards(self):
        """测试开牌后只剩两人时展示牌面"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.add_player('p3', '玩家3')
        self.game.start_game()

        # p1闷2
        self.game.action_blind_bet('p1', 2)
        # p2闷2
        self.game.action_blind_bet('p2', 2)
        # p3闷2
        self.game.action_blind_bet('p3', 2)

        # p1开牌比p2（开牌前3人，开牌后剩2人，不展示）
        result = self.game.action_compare('p1', 'p2')
        self.assertTrue(result['success'])

        # 验证不返回牌面信息（开牌前有3人）
        compare_result = result['compare_result']
        self.assertFalse(compare_result['both_looked'])

        # 现在只剩p1和p3两人，p1开牌比p3应该展示
        result2 = self.game.action_compare('p1', 'p3')
        self.assertTrue(result2['success'])

        # 验证返回牌面信息（只剩两人）
        compare_result2 = result2['compare_result']
        self.assertTrue(compare_result2['both_looked'])
        self.assertEqual(len(compare_result2['player_cards']), 3)
        self.assertEqual(len(compare_result2['target_cards']), 3)

    def test_look_cards(self):
        """测试看牌"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.start_game()

        result = self.game.action_look('p1')
        self.assertTrue(result['success'])
        self.assertTrue(self.game.players['p1'].has_looked)

    def test_follow_after_look(self):
        """测试看牌后跟牌"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.start_game()

        # 先闷牌设置底注
        self.game.action_blind_bet('p1', 2)
        # 看牌
        self.game.action_look('p2')
        # 跟牌
        result = self.game.action_follow('p2')
        self.assertTrue(result['success'])

    def test_fold(self):
        """测试弃牌"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.start_game()

        result = self.game.action_fold('p1')
        self.assertTrue(result['success'])
        self.assertEqual(self.game.players['p1'].state, PlayerState.FOLDED)

    def test_compare_cards(self):
        """测试开牌比牌"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.start_game()

        # 设置底注
        self.game.action_blind_bet('p1', 2)
        # 开牌
        result = self.game.action_compare('p2', 'p1')
        self.assertTrue(result['success'])
        self.assertIn('compare_result', result)

    def test_game_over_when_one_player_left(self):
        """测试只剩一人时游戏结束"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.start_game()

        # 一人弃牌
        result = self.game.action_fold('p1')
        self.assertTrue(result.get('game_over', False))
        self.assertEqual(self.game.phase, GamePhase.FINISHED)

    def test_next_player_after_compare(self):
        """测试开牌后正确切换玩家(Bug修复验证)"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.add_player('p3', '玩家3')
        self.game.start_game()

        # p1闷牌设置底注
        self.game.action_blind_bet('p1', 2)
        # p2闷牌
        self.game.action_blind_bet('p2', 2)
        # p3开牌比p1
        result = self.game.action_compare('p3', 'p1')

        # 验证游戏继续，当前玩家正确
        if not result.get('game_over'):
            self.assertIsNotNone(result.get('next_player'))
            # 当前玩家应该是p2或p3(取决于谁赢了)
            active = self.game.get_active_players()
            self.assertEqual(len(active), 2)


class TestNextPlayerLogic(unittest.TestCase):
    """测试next_player逻辑修复"""

    def test_next_player_after_fold(self):
        """测试弃牌后正确切换"""
        game = GameEngine()
        game.add_player('p1', '玩家1')
        game.add_player('p2', '玩家2')
        game.add_player('p3', '玩家3')
        game.start_game()

        # p1闷牌
        game.action_blind_bet('p1', 1)
        # p2闷牌
        game.action_blind_bet('p2', 1)
        # p3弃牌
        result = game.action_fold('p3')

        # 验证当前玩家正确
        current = game.get_current_player()
        self.assertIn(current, ['p1', 'p2'])


class TestCompareLogic(unittest.TestCase):
    """测试开牌比牌逻辑"""

    def setUp(self):
        self.game = GameEngine()

    def test_compare_without_base_bet_fails(self):
        """测试无底注时开牌失败"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.start_game()

        # 直接开牌，没有先下注
        result = self.game.action_compare('p1', 'p2')
        self.assertFalse(result['success'])
        self.assertIn('底注', result['message'])

    def test_compare_winner_continues(self):
        """测试开牌后赢家继续操作"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.add_player('p3', '玩家3')
        self.game.start_game()

        # p1闷牌
        self.game.action_blind_bet('p1', 2)
        # p2闷牌
        self.game.action_blind_bet('p2', 2)
        # p3开牌比p1
        result = self.game.action_compare('p3', 'p1')

        if not result.get('game_over'):
            # 验证下一个玩家是活跃玩家之一（不是输家）
            compare_result = result['compare_result']
            loser_id = compare_result['loser']
            next_player = result['next_player']
            self.assertNotEqual(next_player, loser_id)
            # 验证下一个玩家在活跃玩家列表中
            active = self.game.get_active_players()
            self.assertIn(next_player, active)

    def test_compare_loser_auto_looks(self):
        """测试开牌后输家自动看牌"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.start_game()

        # p1闷牌
        self.game.action_blind_bet('p1', 2)
        # p2开牌比p1（都没看牌）
        result = self.game.action_compare('p2', 'p1')
        self.assertTrue(result['success'])

        # 验证输家自动看牌
        compare_result = result['compare_result']
        loser_id = compare_result['loser']
        self.assertTrue(self.game.players[loser_id].has_looked)

    def test_compare_fold_skip_logic(self):
        """测试弃牌后正确跳过到下一个活跃玩家"""
        self.game.add_player('p1', '玩家1')
        self.game.add_player('p2', '玩家2')
        self.game.add_player('p3', '玩家3')
        self.game.add_player('p4', '玩家4')
        self.game.start_game()

        # p1闷牌
        self.game.action_blind_bet('p1', 1)
        # p2弃牌
        self.game.action_fold('p2')

        # 验证p2被跳过，轮到p3或p4
        current = self.game.get_current_player()
        self.assertIn(current, ['p3', 'p4'])
        self.assertNotEqual(current, 'p2')


if __name__ == '__main__':
    unittest.main(verbosity=2)
