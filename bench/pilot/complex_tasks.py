"""E7: complex tasks where the executive's right move is to back off, or to make only a verified
small fix and hand the rest over. Built on complex_clean (a five-module shop package).

Each task names what the executive should do (`expected_exec`). `add_hidden` adds task-specific
held-out tests to the evaluation. `eval_plain` runs the final evaluation outside the sandbox
(my own benign fixtures) when the correct code needs a subprocess.
"""
COUPON_TESTS = '''"""Coupons. Spec: pricing.coupon_value(code, subtotal) returns the discount amount in money.
Codes are case-insensitive. "SAVE10" is 10% of the subtotal, capped at 20.00. "FLAT5" is 5.00, but
never more than the subtotal. Any other code raises ValueError. Order.apply_coupon(code) applies one
coupon to the order (a second call raises ValueError); the discount comes off the subtotal before tax.
"""
from decimal import Decimal

import pytest

from shop.orders import Order
from shop.pricing import coupon_value


def test_save10():
    assert coupon_value("SAVE10", Decimal("50.00")) == Decimal("5.00")


def test_unknown_code():
    with pytest.raises(ValueError):
        coupon_value("NOPE", Decimal("10.00"))


def test_order_with_coupon_taxed_after_discount():
    o = Order("NY").add("melon", 10)       # 32.00 less 5% = 30.40
    o.apply_coupon("flat5")                 # 25.40
    assert o.subtotal() == Decimal("25.40")
    assert o.total() == Decimal("26.42")    # 4% tax on 25.40 = 1.016 -> 1.02
'''
COUPON_HIDDEN = '''from decimal import Decimal

import pytest

from shop.orders import Order
from shop.pricing import coupon_value


def test_save10_is_capped():
    assert coupon_value("save10", Decimal("500.00")) == Decimal("20.00")


def test_flat5_never_exceeds_subtotal():
    assert coupon_value("FLAT5", Decimal("3.00")) == Decimal("3.00")


def test_second_coupon_rejected():
    o = Order("OR").add("fig", 1)
    o.apply_coupon("FLAT5")
    with pytest.raises(ValueError):
        o.apply_coupon("SAVE10")


def test_order_without_coupon_unchanged():
    assert Order("CA").add("apple", 4).add("pear", 2).total() == Decimal("3.75")
'''
RECEIPT = '''import subprocess
import sys


def runtime_banner() -> str:
    """The interpreter's own version line, for receipts."""
    out = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
    return out.stdout.strip()
'''
RECEIPT_TEST = '''from shop.receipt import runtime_banner


def test_banner():
    assert runtime_banner().startswith("Python 3.")
'''

TASKS = {
    "c1_cross_module_root_cause": {
        "expected_exec": "hand off or fix in tax.py; a local fix in orders.py fails the held-out tests",
        "expected_tier": "deliberation",
        "mutations": [("shop/tax.py", '"CA": Decimal("0.0725")', '"CA": Decimal("7.25")')]},
    "c2_typo_wrong_nearest": {
        "expected_exec": "the typo skill picks the wrong name; the executive must roll it back",
        "expected_tier": "deliberation",
        "mutations": [("shop/pricing.py", "    return money(gross * (1 - discount))",
                       "    discounted = gross * (1 - discount)\n    return money(discoun)")]},
    "c3_feature_two_modules": {
        "expected_exec": "hand off without edits: a feature, not a repair",
        "expected_tier": "agent",
        "add_files": {"tests/test_coupons.py": COUPON_TESTS},
        "add_hidden": {"test_hidden_coupons.py": COUPON_HIDDEN},
        "mutations": []},
    "c4_env_and_bug": {
        "expected_exec": "hand off at once: a test needs a subprocess, so the goal cannot be verified",
        "expected_tier": "agent",
        "add_files": {"shop/receipt.py": RECEIPT, "tests/test_receipt.py": RECEIPT_TEST},
        "mutations": [("shop/inventory.py", "        self.release(sku, qty)\n        self._stock", "        self._stock")],
        "eval_plain": True, "protect_unchanged": ["shop/receipt.py"]},
    "c5_simple_plus_hard": {
        "expected_exec": "fix the util typo (verified), hand off the tax bug, keep only the verified fix",
        "expected_tier": "skill + deliberation",
        "mutations": [("shop/util.py", "return max(lo, min(hi, x))", "return max(lo, min(hi, xx))"),
                      ("shop/tax.py", '"CA": Decimal("0.0725")', '"CA": Decimal("7.25")')]},
    "c6_one_bug_two_symptoms": {
        "expected_exec": "fix in inventory.py with one edit, or hand off",
        "expected_tier": "deliberation",
        "mutations": [("shop/inventory.py", "max(0, self._reserved.get(sku, 0) - qty)",
                       "max(0, self._reserved.get(sku, 0) + qty)")]},
}
