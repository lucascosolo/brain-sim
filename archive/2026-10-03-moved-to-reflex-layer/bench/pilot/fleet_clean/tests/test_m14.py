from fleet.m14 import summarize_14


def test_summarize_14():
    assert summarize_14([1, 2, 3, 4]) == 6.333
