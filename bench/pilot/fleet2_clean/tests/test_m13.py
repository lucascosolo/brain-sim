from fleet.m13 import summarize_13


def test_summarize_13():
    assert summarize_13([1, 2, 3, 4]) == 43
