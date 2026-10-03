#!/usr/bin/env python3
"""Generate the E5 corpus (fleet_clean/) and its mutation list (fleet_tasks.json). Seeded.

A 30-module package where every module uses helpers from fleet/util.py, with one visible and
one held-out test per module. The single task "s01_refactor_fallout" breaks it the way a careless
rename/move does: 12 modules lose their util import, 12 have a misspelled local, and 2 carry a
real logic bug, so 26 visible tests fail.
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "fleet_clean"
HELPERS = {"clamp": "def clamp(x, lo, hi):\n    return max(lo, min(hi, x))\n",
           "ratio": "def ratio(a, b):\n    return a / b if b else 0.0\n",
           "scale": "def scale(xs, k):\n    return [x * k for x in xs]\n"}


def main():
    rng = random.Random(20261003)
    (OUT / "fleet").mkdir(parents=True, exist_ok=True)
    (OUT / "tests").mkdir(exist_ok=True)
    (OUT / "tests_hidden").mkdir(exist_ok=True)
    (OUT / "conftest.py").write_text("")
    (OUT / "fleet" / "__init__.py").write_text("")
    (OUT / "fleet" / "util.py").write_text("\n\n".join(HELPERS.values()))
    mutations = []
    kinds = ["import"] * 12 + ["typo"] * 12 + ["logic"] * 2 + ["clean"] * 4
    rng.shuffle(kinds)
    for i, kind in enumerate(kinds):
        helper = rng.choice(sorted(HELPERS))
        lo, hi, k = rng.randint(0, 5), rng.randint(20, 40), rng.randint(2, 5)
        call = {"clamp": f"clamp(subtotal, {lo}, {hi})", "ratio": f"ratio(subtotal, {k})",
                "scale": f"sum(scale(values, {k}))"}[helper]
        src = (f"from fleet.util import {helper}\n\n\n"
               f"def summarize_{i:02d}(values):\n"
               f"    subtotal = sum(values)\n"
               f"    adjusted = {call}\n"
               f"    return round(adjusted + len(values) - 1, 3)\n")
        rel = f"fleet/m{i:02d}.py"
        (OUT / rel).write_text(src)
        ns = {}
        exec(compile("\n\n".join(HELPERS.values()) + src.split("\n\n\n", 1)[1], rel, "exec"), ns)
        f = ns[f"summarize_{i:02d}"]
        a, b = [1, 2, 3, 4], [7, 0, 5]
        (OUT / "tests" / f"test_m{i:02d}.py").write_text(
            f"from fleet.m{i:02d} import summarize_{i:02d}\n\n\ndef test_summarize_{i:02d}():\n"
            f"    assert summarize_{i:02d}({a}) == {f(a)!r}\n")
        (OUT / "tests_hidden" / f"test_hidden_m{i:02d}.py").write_text(
            f"from fleet.m{i:02d} import summarize_{i:02d}\n\n\ndef test_hidden_{i:02d}():\n"
            f"    assert summarize_{i:02d}({b}) == {f(b)!r}\n")
        if kind == "import":
            mutations.append([rel, f"from fleet.util import {helper}\n\n\n", "\n\n"])
        elif kind == "typo":
            mutations.append([rel, f"    adjusted = {call}\n", f"    adjusted = {call.replace('subtotal', 'subtotl').replace('values', 'valeus')}\n"])
        elif kind == "logic":
            mutations.append([rel, "len(values) - 1", "len(values) + 1"])
    (HERE / "fleet_tasks.json").write_text(json.dumps(
        {"s01_refactor_fallout": {"expected_tier": "skill (24) + deliberation (2)", "mutations": mutations}}, indent=1))
    print(f"wrote {len(kinds)} modules; {len(mutations)} mutations: "
          + ", ".join(f"{k}={kinds.count(k)}" for k in ("import", "typo", "logic", "clean")))


if __name__ == "__main__":
    main()
