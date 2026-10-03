from fleet.m08 import summarize_08


def test_summarize_08():
    assert summarize_08([1, 2, 3, 4]) == 33
