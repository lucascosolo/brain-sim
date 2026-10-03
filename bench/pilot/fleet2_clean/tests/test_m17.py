from fleet.m17 import summarize_17


def test_summarize_17():
    assert summarize_17([1, 2, 3, 4]) == 13
