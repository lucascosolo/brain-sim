from fleet.m25 import summarize_25


def test_summarize_25():
    assert summarize_25([1, 2, 3, 4]) == 23
