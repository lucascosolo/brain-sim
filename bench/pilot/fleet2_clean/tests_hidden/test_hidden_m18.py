from fleet.m18 import summarize_18


def test_hidden_18():
    assert summarize_18([7, 0, 5]) == 50
