import pytest

pytest.importorskip("fastapi")
from plantrag.app import small_talk  # noqa: E402


@pytest.mark.parametrize("text", ["hi", "Hello!", "hey there", "Good morning", "how are you?", "thanks", "Thank you!",
                                  "what can you do?", "who are you", "bye"])
def test_greetings_and_chitchat_get_a_reply(text):
    assert small_talk(text)


@pytest.mark.parametrize("text", [
    "Which insect carries citrus greening disease?", "hi, how is tomato yellow leaf curl virus transmitted?",
    "What is the capital of France?", "help me treat late blight", "what causes late blight of potato?"])
def test_real_questions_are_not_small_talk(text):
    assert small_talk(text) is None
