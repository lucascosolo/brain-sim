from fleet.m09 import summarize_09


def test_summarize_09():
    assert summarize_09([1, 2, 3, 4]) == 43
