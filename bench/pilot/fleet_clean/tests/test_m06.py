from fleet.m06 import summarize_06


def test_summarize_06():
    assert summarize_06([1, 2, 3, 4]) == 5.5
