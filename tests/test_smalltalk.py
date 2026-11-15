import unittest

try:
    from plantrag.app import small_talk
except ImportError:  # FastAPI is optional (requirements-app.txt); CI skips these tests
    small_talk = None


@unittest.skipIf(small_talk is None, "FastAPI not installed")
class SmallTalkTests(unittest.TestCase):
    def test_greetings_and_chitchat_get_a_reply(self):
        for q in ["hi", "Hello!", "hey there", "Good morning", "how are you?", "thanks", "Thank you!", "what can you do?", "who are you", "bye"]:
            self.assertTrue(small_talk(q), q)

    def test_real_questions_are_not_small_talk(self):
        for q in ["Which insect carries citrus greening disease?", "hi, how is tomato yellow leaf curl virus transmitted?",
                  "What is the capital of France?", "help me treat late blight", "what causes late blight of potato?"]:
            self.assertIsNone(small_talk(q), q)


if __name__ == "__main__":
    unittest.main()
