from fleet.m01 import summarize_01


def test_summarize_01():
    assert summarize_01([1, 2, 3, 4]) == 13
