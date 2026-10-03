from fleet.m09 import summarize_09


def test_hidden_09():
    assert summarize_09([7, 0, 5]) == 8.0
