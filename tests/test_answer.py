import unittest

from plantrag.answer import REFUSAL, build_prompt, citations, clean

P = [
    {"title": "Late blight", "section": "Spread", "text": "Spores travel on the wind."},
    {"title": "Apple scab", "section": "Cycle", "text": "It overwinters on leaves."},
]


class PromptTests(unittest.TestCase):
    def test_passages_are_numbered_from_one_with_their_source(self):
        prompt = build_prompt("How does it spread?", P)
        self.assertIn("[1] Late blight > Spread", prompt)
        self.assertIn("[2] Apple scab > Cycle", prompt)
        self.assertTrue(prompt.rstrip().endswith("Answer:"))
        self.assertIn("Question: How does it spread?", prompt)


class CitationTests(unittest.TestCase):
    def test_finds_all_distinct_citations(self):
        self.assertEqual(citations("Spores spread by wind [1]. It overwinters [2][1]."), [1, 2])

    def test_no_citations(self):
        self.assertEqual(citations(REFUSAL), [])

    def test_ignores_other_brackets(self):
        self.assertEqual(citations("See [citation needed] and [3]."), [3])


class CleanTests(unittest.TestCase):
    def test_removes_hidden_reasoning(self):
        self.assertEqual(clean("<think>\nsecret\n</think>\nThe answer [1]."), "The answer [1].")

    def test_leaves_normal_text(self):
        self.assertEqual(clean("  plain answer "), "plain answer")


if __name__ == "__main__":
    unittest.main()
