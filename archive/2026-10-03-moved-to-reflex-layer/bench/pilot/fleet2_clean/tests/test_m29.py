from fleet.m29 import summarize_29


def test_summarize_29():
    assert summarize_29([1, 2, 3, 4]) == 5.5
