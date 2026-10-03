"""brain-sim is linted by reflex-layer's safety_lint (the stricter suite version).

The recovered plant's tests carry nine test-hygiene findings (they read recorded results from
the owner's ~/.cache paths, and one list.remove trips the destructive-word check). They are
legacy, recorded here by file so a new finding anywhere fails this test. None is a deletion.
"""
import subprocess
import sys
from pathlib import Path

try:
    import reflex
except ImportError:  # a sibling checkout of reflex-layer, which owns the lint
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "reflex-layer"))
    import reflex

ROOT = Path(__file__).resolve().parents[1]
LINT = Path(reflex.__file__).resolve().parent.parent / "tools" / "safety_lint.py"
LEGACY_TEST_HYGIENE = {
    "tests/k03_pairing.py", "tests/k818_drive_loss.py", "tests/k819_homeostat_ablation.py",
    "tests/k822_frozen_readout.py", "tests/k822_rule_screen.py", "tests/k826_learned.py",
    "tests/k828_override.py", "tests/k848_persist_dual.py", "tests/test_client_evidence.py",
}


def test_no_new_safety_findings():
    proc = subprocess.run([sys.executable, str(LINT), str(ROOT)], capture_output=True, text=True)
    findings = [l for l in proc.stdout.splitlines() if not l.startswith("safety_lint:")]
    new = [f for f in findings if f.split(":", 1)[0] not in LEGACY_TEST_HYGIENE]
    assert not new, "\n".join(new)
    assert all("test names" in f or "destructive test" in f for f in findings), "a legacy finding changed kind"
