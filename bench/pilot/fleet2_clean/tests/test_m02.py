from fleet.m02 import summarize_02


def test_summarize_02():
    assert summarize_02([1, 2, 3, 4]) == 5.5
