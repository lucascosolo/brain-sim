import pytest

from ledger.inventory import InsufficientStock, Inventory


def stocked():
    inv = Inventory()
    inv.receive("A", 5)
    inv.receive("B", 1)
    inv.receive("A", 2)
    return inv


def test_receive_accumulates():
    assert stocked().on_hand("A") == 7
    assert stocked().on_hand("Z") == 0


def test_ship_reduces_stock():
    inv = stocked()
    inv.ship("A", 3)
    assert inv.on_hand("A") == 4


def test_ship_more_than_available_raises():
    with pytest.raises(InsufficientStock) as e:
        stocked().ship("B", 2)
    assert e.value.available == 1


def test_low_stock_report():
    assert stocked().low_stock(1) == ["B"]
