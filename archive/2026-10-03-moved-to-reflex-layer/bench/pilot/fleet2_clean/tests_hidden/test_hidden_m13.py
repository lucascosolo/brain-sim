from fleet.m13 import summarize_13


def test_hidden_13():
    assert summarize_13([7, 0, 5]) == 50
