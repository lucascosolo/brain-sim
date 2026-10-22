# Offline screen E: composition of the residual spurious responders under P2-E7 (2026-10-22)

Contract for one zero-seed analysis on the persisted P2-E7 seed-121 evidence, asked for by
the roadmap checkpoint that follows P2-E7's informative FEASIBILITY FAIL. No simulation, no
seed, no frozen driver edited; nothing here is a capability or a gate. Every output is
labelled **offline, descriptive, development seed 121**. The commit that adds this file
freezes it; results are appended below after the run. It extends
`docs/plant2/OFFLINE-SCREENS-20261022.md` (screens A-D) with the same discipline, records and
module.

## Question

Under the P2-E7 rule, which stored items do the residual spurious responders belong to:
the family members written in full before the veto first engaged, the members written after
it, or items of other families? The answer separates two readings of the gap between the
candidate (C2 .745) and the label oracle (.970): a legacy of the early, fully written
members, or an ongoing leak of prototype lines the prediction misses on later episodes.

## Inputs (read-only, verified against their recorded descriptors before use)

For each F10 arm at M = 1,000 of attempt `seed121-1792699741870086415-c573e46d`: the
portable per-load JSON `bench/results/p2e7/<attempt>-F10-<arm>-M1000.json` (per-cue rows with
`index_0based`, `kind`, `own50`, `spurious50`; the `raw` descriptor of the test raster); the
test raster NPZ it names (`raster_ticks`, `raster_cells` ragged, `cue_index`, `cue_onset`,
`cue_kind`); the learned state NPZ beside it, `F10-<arm>-M1000-state.npz` (`A` ragged, the
per-episode plateau sets), whose descriptor is in the arm's `structural_check` or `load`
record; the arm's `structural_check` record (`gate.first_engagement_by_family`, 0-based
episodes, family of 0-based episode k is (k + 1) mod 10).

## Definitions

For each half cue of item q (200 per arm): responders R50 = cells with at least one spike in
the 50 ticks from the cue onset (must equal `own50 + spurious50` of the row, else INVALID for
that arm); spurious S = R50 \ A(q). For each spurious cell c, its plateau items
P(c) = { k : c ∈ A(k) } (every spurious cell has at least one, since a cell without a
plateau has no synapses). With f(q) the cue item's family and e = first engagement of f(q)
(None when the arm never engaged):

- **same-family early**: some k ∈ P(c) has f(k) = f(q) and (e is None or k < e);
- **same-family late**: some k ∈ P(c) has f(k) = f(q), and none of those k is early;
- **other-family only**: no k ∈ P(c) has f(k) = f(q).

Reported per arm: mean per cue of |S|, of each class, and the number of items written
before their family's first engagement; also the chance level of "early" membership (the
fraction of a family's items that are early) so the early class can be read against it.

Arms: baseline (no engagement: every item is early by definition, reported for the identity
check only), candidate, random_drop, history_drop, no_conservation, label_oracle (its
first-engagement fields are None or late, so its classes are reported but not interpreted),
assigned_A_teacher.

## Outputs, records and discipline

Implemented as screen `E` in `analysis/offline_screens_20261022.py` (new functions
`spurious_classes(rows, A, responders_by_cue, first_engagement, F)` and the `run --screen E`
job); records of kind `offline_screen` with `screen: "E"` appended to
`bench/results/offline-screens-20261022.jsonl`, one per arm, with the per-cue table as a
verified artifact under `bench/results/offline-screens-20261022/`, a journal and an
`evidence_verification` record, as screens A-D do. Tests in
`plant2/tests/test_offline_screens.py` (appended; non-slow; synthetic inputs under `run_dir`):
the class rule on hand-built cues, the identity check against `own50 + spurious50`, the
chance-level arithmetic, and the None/late engagement handling. Single process, minutes.

## What this cannot show

A class count on one development seed, not a mechanism: it says where the residual
responders' synapses came from, not what would remove them. The prototype lines each
spurious cell actually carries, and the probability with which they were written (p rises
above 0.5 whenever the veto removes lines, and reaches 1 on capped episodes), are not
persisted per episode and are not computed here.
