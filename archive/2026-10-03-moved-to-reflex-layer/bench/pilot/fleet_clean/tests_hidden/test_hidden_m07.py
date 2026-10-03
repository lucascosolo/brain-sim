from fleet.m07 import summarize_07


def test_hidden_07():
    assert summarize_07([7, 0, 5]) == 14
