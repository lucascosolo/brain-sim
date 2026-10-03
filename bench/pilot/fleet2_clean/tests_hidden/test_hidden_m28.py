from fleet.m28 import summarize_28


def test_hidden_28():
    assert summarize_28([7, 0, 5]) == 5.0
