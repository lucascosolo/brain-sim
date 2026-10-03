from fleet.m28 import summarize_28


def test_summarize_28():
    assert summarize_28([1, 2, 3, 4]) == 13
