import pytest

from plantrag.answer import comparison, requested_count


@pytest.mark.parametrize("q,n", [("Give me 5 points on rice blast", 5), ("10 key symptoms of late blight", 10),
                                 ("3 ways to manage nematodes", 3), ("What is rice blast?", None),
                                 ("Give me 40 points on rice blast", None), ("1 point on aphids", None)])
def test_requested_count(q, n):
    assert requested_count(q) == n


@pytest.mark.parametrize("q,pair", [
    ("What is the difference between early blight and late blight?", ("early blight", "late blight")),
    ("Compare rice blast and sheath blight", ("rice blast", "sheath blight")),
    ("difference between stem rust and leaf rust in 5 points", ("stem rust", "leaf rust")),
    ("How does Karnal bunt differ from loose smut?", ("Karnal bunt", "loose smut")),
    ("early blight vs late blight", ("early blight", "late blight")),
    ("What causes late blight of potato?", None), ("What is the capital of France?", None)])
def test_comparison(q, pair):
    assert comparison(q) == pair
