from fleet.m21 import summarize_21


def test_hidden_21():
    assert summarize_21([7, 0, 5]) == 6.0
