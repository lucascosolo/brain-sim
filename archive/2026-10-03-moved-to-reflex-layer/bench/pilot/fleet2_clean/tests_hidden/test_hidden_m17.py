from fleet.m17 import summarize_17


def test_hidden_17():
    assert summarize_17([7, 0, 5]) == 14
