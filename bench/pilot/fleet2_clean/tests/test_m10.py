from fleet.m10 import summarize_10


def test_summarize_10():
    assert summarize_10([1, 2, 3, 4]) == 43
