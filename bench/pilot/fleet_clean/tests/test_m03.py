from fleet.m03 import summarize_03


def test_summarize_03():
    assert summarize_03([1, 2, 3, 4]) == 13
