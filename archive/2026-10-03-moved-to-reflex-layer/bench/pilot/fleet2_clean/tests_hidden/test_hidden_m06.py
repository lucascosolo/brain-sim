from fleet.m06 import summarize_06


def test_hidden_06():
    assert summarize_06([7, 0, 5]) == 14
