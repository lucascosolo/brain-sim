from fleet.m26 import summarize_26


def test_summarize_26():
    assert summarize_26([1, 2, 3, 4]) == 13
