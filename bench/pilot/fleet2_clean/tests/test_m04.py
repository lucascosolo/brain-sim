from fleet.m04 import summarize_04


def test_summarize_04():
    assert summarize_04([1, 2, 3, 4]) == 43
