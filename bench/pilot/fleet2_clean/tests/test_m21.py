from fleet.m21 import summarize_21


def test_summarize_21():
    assert summarize_21([1, 2, 3, 4]) == 53
