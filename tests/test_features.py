import unittest

from plantrag.answer import comparison, requested_count


class RequestedCountTests(unittest.TestCase):
    def test_numbers_are_found(self):
        self.assertEqual(requested_count("Give me 5 points on rice blast"), 5)
        self.assertEqual(requested_count("10 key symptoms of late blight"), 10)
        self.assertEqual(requested_count("3 ways to manage nematodes"), 3)

    def test_no_or_silly_number(self):
        for q in ["What is rice blast?", "Give me 40 points on rice blast", "1 point on aphids"]:
            self.assertIsNone(requested_count(q), q)


class ComparisonTests(unittest.TestCase):
    def test_comparisons_are_detected(self):
        cases = {
            "What is the difference between early blight and late blight?": ("early blight", "late blight"),
            "Compare rice blast and sheath blight": ("rice blast", "sheath blight"),
            "difference between stem rust and leaf rust in 5 points": ("stem rust", "leaf rust"),
            "How does Karnal bunt differ from loose smut?": ("Karnal bunt", "loose smut"),
            "early blight vs late blight": ("early blight", "late blight"),
        }
        for q, pair in cases.items():
            self.assertEqual(comparison(q), pair, q)

    def test_ordinary_questions_are_not_comparisons(self):
        for q in ["What causes late blight of potato?", "What is the capital of France?"]:
            self.assertIsNone(comparison(q), q)


if __name__ == "__main__":
    unittest.main()
