from fleet.m23 import summarize_23


def test_summarize_23():
    assert summarize_23([1, 2, 3, 4]) == 13
