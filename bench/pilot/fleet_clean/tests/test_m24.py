from fleet.m24 import summarize_24


def test_summarize_24():
    assert summarize_24([1, 2, 3, 4]) == 6.333
