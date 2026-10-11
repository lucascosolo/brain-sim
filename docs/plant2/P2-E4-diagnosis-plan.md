# P2-E4 post-run diagnosis plan (predeclared, reported, not a gate)

Written 2026-10-10, before any P2-E4 gated seed (16-20) has run, following the owner's comments
on the exploration results of seeds 42-43. P2-E4's frozen contract (cd17cde) and its frozen
driver are not changed. Nothing here can alter a gated number, label or validity check.

## What exploration suggests (seeds 42-43; exploratory, not results)

| seed | load | online C1 (index) | content joint | cohort memory | cohort content | threshold offset |
|---|---|---|---|---|---|---|
| 42 | M = 1,000 | 0.690 | 0.950 | 0.670 | 0.920 | 6.9 mV |
| 43 | M = 1,000 | 0.790 | 0.980 | 0.810 | 0.990 | 6.9 mV |

So at least 26 % (seed 42) and 19 % (seed 43) of half cues regenerate the missing content while
failing index recall.

Habituation at M = 500:
- seed 42: 22 of 31 eligible items habituated, with recovery and collateral passing;
- seed 43: 10 of 22 eligible items habituated (O4 not estimable), with recovery passing.

This points to two separable vulnerabilities:
1. access to the assigned memory code under continuous activity;
2. suppression of recall under repetition, which reverses when the repetition stops.

The diagnosis tests whether they are in fact separate, and where each one sits.

## How it is computed

- **Deterministic re-simulation.** The main timeline of a seed is deterministic given its
  streams. An analysis script outside `plant2/` (`analysis/p2e4_diagnosis.py`) re-runs it with
  extra read-only measurements taken at slot time. It wraps the driver's per-slot scoring at
  runtime and consumes no random draws. The gated code tree therefore stays exactly as frozen.
- **Validity of the re-simulation.** Every gated-block slot outcome that the run logged must be
  reproduced exactly: recall, spurious, missing, intrusions, joint, |R50| and |rec|, all compared
  with the per-slot log referenced by the seed's record. If any slot differs, that seed's diagnosis
  is void and reported as such.
- **Where it runs.**
  - Exploration seeds 42-43 as soon as their records exist (labelled exploratory).
  - The gated seeds after the P2-E4 verdict is recorded (labelled reported, post hoc but
    predeclared here).

## Measures

**D1. Index against content, per cue.**
- For every gated-block half cue, the 2 x 2 of index pass (recall of A(x) >= 0.8 within 50 ms)
  against content pass (the joint).
- Counts per seed, load and kind (recent, uniform, cohort).

**D2. What distinguishes "content without index" cues.** For each cell of D1:
- A(x) recall at 50 ms and at 75 ms. Does a longer window rescue the index?
- R(x) recall at 50 ms: the fraction of the continuation responders, from which x's feedback was
  written, that spike.
- |R(x)| and |R(x) ∩ A(x)|.
- The median first-spike tick of x's A cells, and of x's R cells, that fire within 75 ms.
- The share of x's regenerated missing lines whose feedback came only from cells outside A(x).
  These are lines that receive a written synapse from a spiking R-but-not-A cell and from no
  spiking A cell.
- The item's age.
- At slot onset: the global `vbar` offset, and the mean `vbar` offset of A(x)'s cells (the
  assembly offset).

**D3. State, not erasure (settled twin B, re-simulated per cue).**
- For cues that fail index recall online, the fraction that pass after the 50 s settle on the same
  stored synapses.
- The same for content failures.
- McNemar per seed and load.

**D4. Habituation as a separate phenomenon.**
- Per habituation item: the rise in the assembly offset over the repetitions against
  L_rep - L_ctl.
- Whether items that fail index recall online in the block habituate more, less or equally
  (cross-tabulated by item).
- Recovery among habituated items.

## Predictions (written before the analysis runs)

**D1.** At M = 1,000, "content without index" is 15-30 % of half cues. "Index without content" is
under 3 %.

**D2.** Compared with cues that pass both, "content without index" cues have:
- A(x) recall at 50 ms typically 0.5-0.8, with a 75 ms window rescuing a minority;
- R(x) recall at least as high as A(x) recall;
- later A-cell first spikes, by 5 ms or more;
- a higher assembly offset at onset;
- older items on average.

Most regenerated missing lines are still driven by spiking A cells. Under a quarter come only from
R-but-not-A cells.

**D3.** Most online index failures, at least 70 %, pass after the settle, which would point to
network state rather than erased memories. Content failures also mostly recover. The P2-E3
addendum 2 caveat applies: the online-written store is itself degraded, so some failures may not
recover.

**D4.** The assembly offset rises with repetition, and habituated items show the larger rise.
Index failure in the block is only weakly associated with habituation (the two vulnerabilities are
separable).

## What it does not do

- It gates nothing and changes nothing frozen.
- It does not test a mechanism.
- Any mechanism suggested by it needs its own contract, one at a time, with the owner's ruling
  where the mechanism belongs to a gated family. Accommodation, the operating-point mechanism,
  is in such a family.

## Corrections after the owner's code review (2026-10-11; before the analysis was run on any seed)

The owner reviewed commit e6c5385. Four corrections were made to `analysis/` only; nothing under
`plant2/` changed.

1. **D2 claimed too much.** The old measure ("lines whose feedback came only from cells outside
   A(x)") counted inputs from any spiking cell. It did not require that cell to belong to R(x),
   nor that it fired before the line.
   - **Replaced by candidate-input fractions.** A candidate input is a feedback synapse from a
     memory cell whose first spike within 75 ms came at least one tick (the feedback delay) before
     the line's first spike. Each regenerated missing line is classed as having:
     - an A(x) candidate;
     - only R(x)-not-A(x) candidates;
     - only candidates outside both;
     - no earlier candidate.
   - **A candidate is a possible contributor, not a proven one.** No causal claim rests on D2. A
     causal claim would need a separately contracted ablation.
2. **D3's check was weaker than stated.**
   - **What the record allows.** The reported-arms record holds twin B only as aggregates per kind,
     not per-cue pairs. So the strongest available check is to reproduce every recorded
     aggregate per kind: n, the four pass fractions, and both McNemar discordant counts, which
     pin the discordant pairs.
   - **A missing record** now leaves D3 "not verified" (`D3_verified` false). It is no longer
     counted as valid.
3. **D4 now reports its matched sample sizes:**
   - the number of habituated and non-habituated items that have an online index measurement;
   - the median number of online probes per item.
4. **The replay check now covers every logged main-line step.** It runs from step 1 to the second
   gated load. Each step must exist, and must match kind, target, block and age as well as every
   scoring field. A missing step counts as a mismatch.

**What reproduction establishes.** Deterministic reproduction shows consistency with the recorded
simulation, not proof of a causal explanation. D3 can give strong evidence that network state
matters. D2 and D4 narrow the explanation; they do not establish it.

**Further correction (owner review of 737e8b1, 2026-10-11; before any run of the analysis).** The
D2 classes were not exhaustive: a line with both an R(x)-not-A(x) candidate and a candidate
outside both sets, and no A(x) candidate, fell in none of them. A fifth class,
`mixed_non_A_candidates`, was added. The classes are now exclusive and exhaustive, so their
fractions sum to 1 (tested in `analysis/tests/test_p2e4_diagnosis.py`).

**Reading of D3, narrowed (owner review, 2026-10-11; before any run of the analysis).** Twin B keeps
the stored synapses, the cue identities, the masks and the order. It also changes the presentation
regime:
- the cues come after a 50 s settle;
- on a separate input stream;
- at P2-E3's rhythm (100 ms on, 200 ms off);
- with no learning episodes between them.

So recovery in twin B shows that recall is **state- or protocol-dependent recovery with the
synapses unchanged**. It does not show that the threshold offset alone caused the online failure.
Wherever the predictions above say "network state rather than erased memories", read
"state- or protocol-dependent, not erasure". Isolating accommodation would need a separately
contracted intervention.
