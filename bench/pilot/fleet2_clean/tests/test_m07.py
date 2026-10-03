from fleet.m07 import summarize_07


def test_summarize_07():
    assert summarize_07([1, 2, 3, 4]) == 5.5
