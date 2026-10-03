from fleet.m05 import summarize_05


def test_summarize_05():
    assert summarize_05([1, 2, 3, 4]) == 33
