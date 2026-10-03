import csv
import io
from decimal import Decimal

from ledger.invoice import Invoice
from ledger.money import parse_amount

REQUIRED = ("sku", "quantity", "unit_price")


def read_invoice(text, tax_rate=Decimal("0")):
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)}")
    invoice = Invoice(tax_rate=tax_rate)
    for lineno, row in enumerate(reader, start=2):
        try:
            quantity = int(row["quantity"])
        except ValueError:
            raise ValueError(f"line {lineno}: bad quantity {row['quantity']!r}") from None
        invoice.add(row["sku"].strip(), quantity, parse_amount(row["unit_price"]))
    return invoice
