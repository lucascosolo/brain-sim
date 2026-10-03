from fleet.m15 import summarize_15


def test_summarize_15():
    assert summarize_15([1, 2, 3, 4]) == 13
