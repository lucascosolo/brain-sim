from fleet.m08 import summarize_08


def test_hidden_08():
    assert summarize_08([7, 0, 5]) == 38
