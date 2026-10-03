from fleet.m05 import summarize_05


def test_hidden_05():
    assert summarize_05([7, 0, 5]) == 38
