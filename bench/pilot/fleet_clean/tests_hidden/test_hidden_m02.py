from fleet.m02 import summarize_02


def test_hidden_02():
    assert summarize_02([7, 0, 5]) == 8.0
