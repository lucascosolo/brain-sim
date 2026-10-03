from fleet.m20 import summarize_20


def test_summarize_20():
    assert summarize_20([1, 2, 3, 4]) == 53
