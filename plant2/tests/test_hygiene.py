"""plant2 tests keep their outputs out of /tmp and out of auto-pruned pytest directories (AGENTS.md 1, 5)."""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANNED = re.compile(r"\b(" + "|".join(["tmp" + "_path", "tmp" + "dir", "tmp" + "_path_factory", "temp" + "file",
                                        "Temporary" + "Directory", "mk" + "dtemp"]) + r")\b|/" + "tmp/")


def test_no_test_uses_temporary_directories():
    hits = [f"{p.name}:{n}" for p in sorted(HERE.glob("*.py")) if p.name != Path(__file__).name
            for n, line in enumerate(p.read_text().splitlines(), 1) if BANNED.search(line)]
    assert not hits, hits
