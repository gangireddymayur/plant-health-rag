import unittest

from plantrag.retrieve import rrf, tokenize


class FusionTests(unittest.TestCase):
    def test_item_ranked_high_in_both_lists_wins(self):
        fused = rrf([["a", "b", "c"], ["b", "a", "d"]])
        self.assertEqual({fused[0][0], fused[1][0]}, {"a", "b"})
        self.assertEqual({i for i, _ in fused}, {"a", "b", "c", "d"})

    def test_an_item_in_only_one_list_still_appears(self):
        ids = [i for i, _ in rrf([["a"], ["b"]])]
        self.assertEqual(set(ids), {"a", "b"})

    def test_scores_decrease_down_the_ranking(self):
        scores = [s for _, s in rrf([["a", "b", "c"], ["a", "c", "b"]])]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_rank_one_in_both_lists_beats_rank_one_in_one(self):
        self.assertEqual(rrf([["a", "x"], ["a", "y"]])[0][0], "a")


class TokenizeTests(unittest.TestCase):
    def test_lowercases_and_drops_stop_words(self):
        self.assertEqual(tokenize("How does Late Blight spread?"), ["late", "blight", "spread"])

    def test_keeps_numbers_and_splits_punctuation(self):
        self.assertEqual(tokenize("TYLCV-2 (virus)"), ["tylcv", "2", "virus"])


if __name__ == "__main__":
    unittest.main()
