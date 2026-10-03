from fleet.m29 import summarize_29


def test_hidden_29():
    assert summarize_29([7, 0, 5]) == 5.0
