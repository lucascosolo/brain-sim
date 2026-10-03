# brain-sim

A **cognitive executive**: goals, world state, prediction, action selection and memory in
ordinary, inspectable code, with language models called as tools only when the executive
reaches an impasse. Deterministic capabilities come from
[reflex-layer](https://github.com/lucascosolo/reflex-layer); the executive decides which to use.

> The model supplies missing cognition. It does not host the cognition.

Status, 2026-10-03: first vertical slice. The executive makes a Python repository's failing
tests pass. It fixes what memory and skills can fix with no model, escalates the rest, rolls
back edits whose predicted effect is contradicted, and declares success only on a fresh,
sandboxed test run. Every model answer so far is scripted; no live model has been called.
Details: [`docs/report-2026-10-03.md`](docs/report-2026-10-03.md).

## Run it

```bash
pip install -e ../reflex-layer                       # reflex-layer checked out beside this repo
python3 -m pytest -q tests/test_executive            # 13 tests, seconds
python3 -m executive bench                           # nine demo tasks, scripted deliberators
python3 -m executive run --repo PATH                 # no deliberator: blocks at an impasse
python3 -m executive status --state-dir DIR
```

`--deliberator claude-cli` calls `claude -p` with tools disabled and records every answer for
replay. It spends money, so it is off by default.

## Layout

```
executive/        the executive (new): loop, state, operators, memory, deliberation, metrics, CLI
tests/test_executive/  its tests
docs/architecture.md   what was found, the boundary with reflex-layer, the diagram, adversarial notes
DECISIONS.md      why it looks this way
bench/results/    append-only measured results

brainsim/ server/ ui/ mockups/ run.py SPEC.md tests/k*.py tests/test_*.py
                  the recovered spiking-network plant: frozen research material (README-RECOVERY.md)
docs/recovery/    recovery manifests; they key on the paths above, so those paths do not move
```

## Safety

Nothing here deletes files. The executive has no shell and no direct file access: every effect
goes through reflex-layer's capability registry, granting one declared effect per call. Code
under study runs in a confined child where deletion becomes a quarantine move. Tests are
protected from edits, so verification cannot be gamed. See [`AGENTS.md`](AGENTS.md).
