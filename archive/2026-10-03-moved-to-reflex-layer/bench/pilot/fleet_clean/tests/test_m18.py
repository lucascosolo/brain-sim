from fleet.m18 import summarize_18


def test_summarize_18():
    assert summarize_18([1, 2, 3, 4]) == 13
