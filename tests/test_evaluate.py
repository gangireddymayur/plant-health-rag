import unittest

from plantrag.evaluate import gold_ids, hit_at_k, keyword_correct, reciprocal_rank

CHUNKS = [
    {"id": "1-0", "title": "Apple scab", "section": "Introduction", "text": "Caused by Venturia inaequalis."},
    {"id": "1-1", "title": "Apple scab", "section": "Disease cycle", "text": "The fungus overwinters on fallen leaves."},
    {"id": "2-0", "title": "Late blight", "section": "Introduction", "text": "Venturia is not involved here."},
]


class GoldTests(unittest.TestCase):
    def test_needs_title_and_all_patterns(self):
        q = {"gold_title": "Apple scab", "must_contain": [r"Venturia inaequalis"]}
        self.assertEqual(gold_ids(CHUNKS, q), {"1-0"})

    def test_section_filter(self):
        q = {"gold_title": "Apple scab", "must_contain": [r"fungus"], "gold_section": r"Disease cycle"}
        self.assertEqual(gold_ids(CHUNKS, q), {"1-1"})
        q["gold_section"] = r"Introduction"
        self.assertEqual(gold_ids(CHUNKS, q), set())

    def test_other_articles_never_count(self):
        q = {"gold_title": "Apple scab", "must_contain": [r"Venturia"]}
        self.assertNotIn("2-0", gold_ids(CHUNKS, q))


class MetricTests(unittest.TestCase):
    def test_reciprocal_rank(self):
        self.assertEqual(reciprocal_rank(["a", "b", "c"], {"b"}), 0.5)
        self.assertEqual(reciprocal_rank(["a", "b", "c"], {"z"}), 0.0)

    def test_reciprocal_rank_respects_k(self):
        self.assertEqual(reciprocal_rank(["a", "b", "c"], {"c"}, k=2), 0.0)

    def test_hit_at_k(self):
        self.assertEqual(hit_at_k(["a", "b", "c"], {"c"}, 3), 1.0)
        self.assertEqual(hit_at_k(["a", "b", "c"], {"c"}, 2), 0.0)

    def test_keyword_groups_all_must_match(self):
        groups = [["wind", "air"], ["spore"]]
        self.assertTrue(keyword_correct("Spores travel on the wind.", groups))
        self.assertFalse(keyword_correct("It spreads by wind.", groups))


if __name__ == "__main__":
    unittest.main()
