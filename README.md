# brain-sim

Research code for a spiking-network brain simulation (the recovered "plant", frozen while
recovery is open; see `README-RECOVERY.md`).

**Since 2026-10-10 the active line is `plant2/`**: a spiking, brain-like learning system aimed
at the north star in `DECISIONS.md` (2026-10-10), built in stages with predeclared kill tests.
The staged path and every experiment's contract and result are in `docs/plant2/`. Measured
results are in `bench/results/plant2.jsonl`.

**The cognitive executive that was developed here moved to
[reflex-layer](https://github.com/lucascosolo/reflex-layer) on 2026-10-03** (`executive/`,
its tests, the pilot experiments E2–E7b and their reports). The copy that was here is frozen
under `archive/2026-10-03-moved-to-reflex-layer/` (see `MOVED.md` there). Nothing was deleted.

## Layout

```
brainsim/ server/ ui/ mockups/ run.py SPEC.md tests/k*.py tests/test_*.py
                  the recovered spiking-network plant: frozen research material (README-RECOVERY.md)
docs/recovery/    recovery manifests; they key on the paths above, so those paths do not move
plant2/           the active line: engine, plasticity rules, experiment drivers, plant2/tests/
docs/plant2/      STAGES.md (staged path and gates) and one contract-plus-result file per experiment
bench/results/    append-only JSONL of measured results
tests/test_safety_lint.py   lints this repository with reflex-layer's tools/safety_lint.py
archive/          frozen copies of material that moved elsewhere (MOVED.md in each)
DECISIONS.md      why it looks this way (the executive-era entries are copied to reflex-layer)
```

## Safety

Nothing here deletes files. See [`AGENTS.md`](AGENTS.md).
