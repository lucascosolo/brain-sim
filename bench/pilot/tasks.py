"""Pilot task set (predeclared 2026-10-03, see PREREGISTRATION.md): one seeded bug per task in ledger_clean.

Each mutation is exact text replacement on a clean copy. `expected_tier` is my prediction of
the cheapest executive tier that can fix it, written before any run.
"""
CLEAN = "ledger_clean"
HIDDEN = "tests_hidden/test_hidden.py"

TASKS = {
    "t01_name_typo": {
        "expected_tier": "skill",
        "mutations": [("ledger/money.py", "for i in range(parts)]", "for i in range(part)]")]},
    "t02_missing_import": {
        "expected_tier": "skill",
        "mutations": [("ledger/csvimport.py", "from ledger.money import parse_amount\n", "")]},
    "t03_off_by_one": {
        "expected_tier": "deliberation",
        "mutations": [("ledger/money.py", "(1 if i < extra else 0)", "(1 if i <= extra else 0)")]},
    "t04_boundary_compare": {
        "expected_tier": "deliberation",
        "mutations": [("ledger/inventory.py", "if quantity > available:", "if quantity > available + 1:")]},
    "t05_rounding_mode": {
        "expected_tier": "deliberation",
        "mutations": [("ledger/invoice.py",
                       "return ((self.subtotal() - self.discount()) * self.tax_rate).quantize(CENT, rounding=ROUND_HALF_UP)",
                       "return ((self.subtotal() - self.discount()) * self.tax_rate).quantize(CENT)")]},
    "t06_order_of_operations": {
        "expected_tier": "deliberation",
        "mutations": [("ledger/invoice.py", "((self.subtotal() - self.discount()) * self.tax_rate)",
                       "(self.subtotal() * self.tax_rate)")]},
    "t07_wrong_index": {
        "expected_tier": "deliberation",
        "mutations": [("ledger/dates.py", "calendar.monthrange(year, month)[1]", "calendar.monthrange(year, month)[0]")]},
    "t08_shared_root_cause": {
        "expected_tier": "deliberation",
        "mutations": [("ledger/money.py", 'text.strip().replace(",", "").replace("$", "")', 'text.strip().replace("$", "")')]},
    "t09_two_bugs": {
        "expected_tier": "deliberation",
        "mutations": [("ledger/inventory.py", "if quantity > available:", "if quantity > available + 1:"),
                      ("ledger/invoice.py", "((self.subtotal() - self.discount()) * self.tax_rate)",
                       "(self.subtotal() * self.tax_rate)")]},
    "t10_attribute_typo": {
        "expected_tier": "deliberation",
        "mutations": [("ledger/inventory.py", "for sku, quantity in self._stock.items()",
                       "for sku, quantity in self._stok.items()")]},
}
