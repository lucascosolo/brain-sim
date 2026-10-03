from fleet.m16 import summarize_16


def test_hidden_16():
    assert summarize_16([7, 0, 5]) == 8.0
