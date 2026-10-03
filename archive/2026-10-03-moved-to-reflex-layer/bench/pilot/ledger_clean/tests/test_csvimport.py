from decimal import Decimal

import pytest

from ledger.csvimport import read_invoice

CSV = "sku,quantity,unit_price\nA,2,3.25\nB,1,\"1,000.00\"\n"


def test_read_invoice():
    inv = read_invoice(CSV, tax_rate=Decimal("0.10"))
    assert [l.sku for l in inv.lines] == ["A", "B"]
    assert inv.subtotal() == Decimal("1006.50")
    assert inv.total() == Decimal("1107.15")


def test_missing_column():
    with pytest.raises(ValueError, match="unit_price"):
        read_invoice("sku,quantity\nA,1\n")


def test_bad_quantity_names_line():
    with pytest.raises(ValueError, match="line 3"):
        read_invoice("sku,quantity,unit_price\nA,1,1.00\nB,x,1.00\n")
