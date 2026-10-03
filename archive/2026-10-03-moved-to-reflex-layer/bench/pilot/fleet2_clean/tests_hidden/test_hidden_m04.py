from fleet.m04 import summarize_04


def test_hidden_04():
    assert summarize_04([7, 0, 5]) == 50
