from fleet.m26 import summarize_26


def test_hidden_26():
    assert summarize_26([7, 0, 5]) == 14
