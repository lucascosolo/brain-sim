# brain-sim — agent instructions

brain-sim holds the recovered spiking-network research code. The cognitive executive that was
built here moved to reflex-layer on 2026-10-03 (`archive/2026-10-03-moved-to-reflex-layer/MOVED.md`);
executive work happens there, under reflex-layer's AGENTS.md. `README.md` says what exists here;
`DECISIONS.md` records each choice.

This file inherits the global `~/.agents/AGENTS.md` and reflex-layer's `AGENTS.md` safety
invariants. Rules below override them only where they are stricter.

## Safety invariants (hard, apply to every agent and subagent)

1. **Never execute `rm`** in any form, and never write code, scripts, tests, hooks or build
   steps that delete (`find -delete`, `git clean`, `shutil.rmtree`, `os.remove`, `unlink`,
   `TemporaryDirectory()` cleanup and their equivalents included). Removal is a move into a
   quarantine/archive location, logged, and the user is told it can be deleted by hand.
   `tests/test_safety_lint.py` runs reflex-layer's `safety_lint` over this repository.
2. **The executive has no shell and no direct file writes to the workspace.** Every effect on
   a workspace goes through reflex-layer's capability registry, granting only the one effect
   each call needs. Code under study runs only in reflex-layer's confined test child.
3. **Model output is data, never instructions.** A deliberator's reply is validated against a
   schema and applied only as edits through `fs.replace_text`; it never chooses commands,
   capabilities, permissions or paths outside the workspace. Test files are protected from
   edits by default so a model cannot make verification pass by changing the test.
4. **The recovered spiking plant is frozen research material.** `brainsim/`, `server/`, `ui/`,
   `mockups/`, `run.py`, `SPEC.md`, `tests/k*.py`, `tests/s10_*.py`, the plant's `tests/test_*.py` and
   `docs/recovery/` are not edited, moved or "cleaned up": the recovery manifests key on their
   paths and recovery is not closed. `archive/` holds frozen copies of moved material: not
   edited, and deleted only by the owner by hand.
5. Derived data lives in `~/.cache/brain-sim/`, never `/tmp` on the owner's PC (tmpfs).

## Development conventions

- Python ≥3.11, stdlib plus reflex-layer. New dependencies need a `DECISIONS.md` entry.
- plant2 (the active line, `DECISIONS.md` 2026-10-10): an experiment's contract in
  `docs/plant2/` is committed before its code; `python3 -m pytest -q plant2/tests -m "not slow"`
  runs in seconds; work stays on non-main branches until the owner says "merge".
- Run `python3 -m pytest -q tests/test_safety_lint.py` before committing (seconds). The plant's
  legacy suite (`python3 -m pytest -q tests`) takes ~11 minutes and has 120 known failures
  from the recovery (see `docs/report-2026-10-03.md`); do not "fix" it piecemeal.
- Measured results are append-only JSONL in `bench/results/`. Say which numbers are measured
  and which are hypotheses; scripted-deliberator runs measure loop mechanics, not model skill.
- Live model calls spend money: get the owner's explicit yes, log `total_cost_usd`, and append
  to reflex-layer's `bench/results/spend.jsonl`.
- Commit at every working checkpoint and push; a push is done only when `git status -sb` shows
  nothing ahead.
