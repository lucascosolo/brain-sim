from fleet.m25 import summarize_25


def test_hidden_25():
    assert summarize_25([7, 0, 5]) == 26
