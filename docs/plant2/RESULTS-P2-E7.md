# P2-E7 results: development seed 121, informative FEASIBILITY FAIL

Measured 2026-10-22, 20:09-20:19 UTC, on this PC (CPython 3.11.17, NumPy 2.4.6,
`OPENBLAS_NUM_THREADS=1`), from commit 6a9e204 (driver and riders at 9bc6cf3, contract frozen
at fede3c2, frozen JSON e38a6b0). Records: `bench/results/p2e7.jsonl` (117 rows: 115 from the
run, 2 `rider` rows after it); portable per-cue, structural and state evidence under
`bench/results/p2e7/`; raw checkpoints and per-worker journals under the cache root
`~/.cache/brain-sim/plant2-research-20261022/p2e7`. A first start at 20:07:31 UTC was refused
by the source manifest before any record was written (contract note 5).

**Formal status: COMPLETE; verdict FEASIBILITY FAIL, tagged `informative`.** Four workers,
wall time 610.6 s inside the 3,600 s window, nothing missing, not interrupted; sixteen
`evidence_verification` records (fourteen trajectories, the coordinator with 59 artifacts,
the riders) all passed; `uniform_integrity` true; `gate_off` forward store equals the
baseline's at 500 and 1,000; `matching` digests agree across every arm at every load; no
structural kill fired on any arm; every protocol check holds; sanity loads pass (wrong-label
C1 0.000 with counts preserved; empty store 0 responders). The absolute bars failed on the
F10/1,000 candidate for C1 (.895), C2 (.745), C4_spurious (.720) and joint index (.645);
every comparative margin held. Held-out seed 122 does not open.

## The development screen

F10 arms at M = 1,000 (index window 50 ms; content through the responder-written store and
the assigned-A diagnostic store, 75 ms readout; all values on development seed 121,
exploratory by the README vocabulary):

| arm | C1 | C2 | C3 | C4 recall | C4 spurious | joint | inherited content | assigned-A content | own50 | spurious50 | max prototype out-degree |
|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline (literal E3) | .920 | .500 | 1.000 | .940 | .470 | .425 | .005 | .110 | 18.73 | 20.96 | 1,022 |
| **candidate** | **.895** | **.745** | 1.000 | .940 | .720 | **.645** | .005 | .250 | 18.69 | 8.63 | 618 |
| random_drop (count-matched, stream 33) | .925 | .480 | 1.000 | .960 | .420 | .410 | .000 | .135 | 18.70 | 19.15 | 1,023 |
| history_drop (E6 counts, stream 34) | .945 | .635 | 1.000 | .950 | .580 | .595 | .000 | .180 | 18.74 | 12.11 | 653 |
| gate_off (integrity) | .920 | .500 | 1.000 | .940 | .470 | .425 | .005 | .110 | 18.73 | 20.96 | 1,022 |
| no_conservation (reported) | .680 | .840 | 1.000 | .950 | .800 | .545 | .055 | .385 | 15.78 | 5.47 | 579 |
| label_oracle (diagnostic) | .920 | .970 | 1.000 | .920 | .950 | .890 | .310 | .500 | 18.84 | 1.68 | 460 |
| assigned_A_teacher (reported) | .935 | .645 | 1.000 | .940 | .610 | .580 | .000 | .210 | 19.00 | 11.36 | 667 |

F10 at M = 500: baseline C1 .965, C2 .910, joint .875, inherited content .145; candidate
.950, .970, .920, .280; random_drop .965, .925, .890, .140; history_drop .965, .950, .915,
.190; no_conservation .780, .985, .770, .275; label_oracle .935, 1.000, .935, .990;
assigned_A_teacher .965, .960, .925, .255. Every absolute bar holds on the candidate at
F10/500.

Independent inputs: candidate and baseline are identical at both loads (C1 .965/.960, C2
1.000/.985, joint .965/.945, inherited content .995/.960), with zero vetoed episodes and equal
forward-store digests. Mixed stream (odd episodes F10, even independent, one store), at
M = 1,000: baseline C1 .940, C2 .790, joint .730; candidate .945, .880, .825. Independent
subset (95 half cues, 50 oldest): baseline C1 90, C2 94, joint 89, C4 recall 48, C4 spurious
49, content joint 34 cues; candidate 91, 95, 89, 48, 50, 48 cues. F10 subset (105 cues):
baseline C2 .610, candidate .771. F40 transfer (reported only): baseline C2 .805 / joint .770
at 1,000, candidate .880 / .835.

## Structural checks (before any test phase)

F10 candidate: mean |V| 12.96 over episodes 1-500 and 40.37 over 501-1,000 (per block of 100
episodes: 1.0, 4.3, 16.8, 17.8, 24.8, 31.2, 34.6, 37.7, 47.5, 50.9), maximum 84; veto
precision 0.817; prototype predicted fraction 0.835; non-prototype predicted fraction 0.123;
vetoed episodes 68.4 % overall and 87.8 % over 501-1,000; p capped on 144 episodes; no empty
E'. First engagement by family (0-based episode): 44-46 for three families, 69-92 for four,
127-138 for three, so a family's first four to fourteen members are written in full. The
drop controls' own gates read 54.4 (random) and 48.2 (history) mean |V| over 501-1,000 with
precision 0.687 and 0.745; gate_off (the baseline trajectory) 55.2 and 0.685, non-prototype
0.291. assigned_A_teacher: mean |V| 27.9, precision 0.975, non-prototype 0.012. Independent
candidate: zero vetoes. Mixed candidate: 15.7 mean |V|, precision 0.917; independent-subset
vetoed fraction 0.004. F40 candidate: 16.0, precision 0.965.

## The twelve frozen predictions

| prediction | outcome | evidence |
|---|---|---|
| P1 structural: mean \|V\| ≥ 20, precision ≥ 0.80, prototype predicted ≥ 0.50, non-prototype ≤ 0.10 | **failed on the last clause** | 40.37, 0.817, 0.835 held; non-prototype 0.123 |
| P2 F10/1,000 C2 in [0.82, 0.97] | **failed** | .745 |
| P3 C1 ≥ 0.91 and C4_recall ≥ 0.90 | **failed on C1** | .895 (one cue below the .90 bar as well), C4_recall .940 |
| P4 joint index in [0.75, 0.93] | **failed** | .645 |
| P5 C4_spurious in [0.70, 0.97] | held | .720 |
| P6 inherited content in [0.02, 0.40]; assigned-A in [0.30, 0.60] | **failed, both below** | .005; .250 |
| P7 C3 ≥ 0.98 at F10 and independent, both loads | held | 1.000, 1.000, 1.000, .995 |
| P8 F10/500: C1 ≥ .93, C2 ≥ .97, joint ≥ .90, C4 recall ≥ .94, C4 spurious ≥ .92, content in [0.50, 0.97] | **failed on content** | .950, .970, .920, .960, .960 held; content .280 |
| P9 controls: random ≤ .55; candidate ≥ history + .10; oracle ≥ candidate − .05; no_conservation C1 ≤ candidate C1 | held | .480; .745 − .635 = .110; .970; .680 ≤ .895 |
| P10 independent: ≤ 5 % vetoed episodes, max \|V\| ≤ 2, measures within ±0.02, equal forward digest when no veto | held | 0 %, 0, identical, equal |
| P10b mixed independent subset within ±2 cues (C4 halves ±1) | **failed on content, in the favourable direction** | index counts within +1 cue; content joint +14 cues (34 → 48) |
| P11 spurious50 ≤ 6; own50 within ±1.0; max prototype out-degree ≤ 0.5 × baseline | **failed on two of three** | 8.63; 18.69 vs 18.73 held; 618 vs 511 allowed |
| P12 integrity | held | gate_off = baseline at both loads; uniform_integrity true; matching equal |

No prediction is revised. Most-likely-failure clause: "the oldest-item specificity bar or a
late veto onset"; both occurred.

## Riders (reported only, baseline trajectory, from gate_off's persisted counts)

Feedback stores written from the same continuation spikes and read through the frozen
readout on gate_off's persisted test rasters, content joint: R_3 .925 at 500 and .140 at
1,000; R_1 .145 and .005; size-matched random .310 and .015; anti-selected .100 and .000.
This is P2-R1's pattern on a fresh seed: writer identity helps at 500 and does not repair
content at 1,000. Not stacked, not scored.

## What this establishes, and what it does not

- **The error signal carries information (ruling 4, test i).** The candidate beats the
  count-matched random drop by +0.265 C2 and +0.235 joint index, and the history-weighted
  drop by +0.110 C2 and +0.050 joint, on one development seed; the co-occurrence-sensitive
  prediction adds beyond E6's hot-line marginal (kill e did not fire). P2-E7 is not a
  hot-line filter in disguise.
- **Corrections preserve unrelated memories (ruling 4, test ii).** The veto never fired on
  independent inputs, and in the mixed store the independent subset's index counts moved by
  at most one cue while its content joint rose from 34 to 48 cues.
- **The rule as stated does not reach the bar.** C2 .745 at F10/1,000 against .90, with C1
  one cue below .90 and oldest specificity .720. The veto engages late: a family's first four
  to fourteen members are written in full, mean |V| only passes 20 lines in block 5, and
  p is capped on 144 late episodes. The label oracle, which vetoes the true 40 prototype lines
  from the first episode, reaches C2 .970 with C1 .920: the ceiling of this family of
  mechanisms is high, and the gap is onset and coverage, not the idea.
- **The budget is load-bearing.** Without conservation the veto gives C2 .840 but C1 .680 and
  own50 15.8: the unconserved rule trades recall for specificity along the H-067 curve. The
  conserved rule keeps own50 within 0.05 of the baseline's.
- **The responder-written store is the better teacher.** The clean plateau-set teacher
  engages later (mean |V| 27.9) with higher precision (0.975) and reaches only C2 .645; the
  contaminated store predicts prototype lines earlier and wins. Coverage, not precision,
  limits the gain.
- **Content stays at the floor (H-046).** Inherited content .005 at F10/1,000 on every arm but
  the oracle (.310); at F10/500 the index gain carried only .280 (baseline .145), unlike E6's
  .785 and the degree null's .960, because the fully written early members keep feeding
  spurious responders into the store.
- **Non-prototype prediction stayed under the kill threshold** (0.123 against 0.25) and well
  under the baseline-trajectory pre-screen's 0.29: the veto reduced its own teacher's
  contamination, as the pre-screen's caveat anticipated.

Nothing here is a capability. The random key, episode boundaries, write oracle, verbatim
value and test regime remain supplied; the rule removed only part of the selection half of
eligibility. The result is one development seed under a frozen screen; the comparative
margins are exploratory evidence, not gated.

## Failure classification

Informative FEASIBILITY FAIL: a failed hypothesis in its stated form (the frozen rule does
not clear the absolute bars at the canonical load), with the comparative hypotheses (useful
error information; co-occurrence sensitivity beyond load; preservation of unrelated memories)
supported on one development seed. No implementation failure (integrity checks all true), no
inadequate experiment (every kill rule, screen rule and prediction decided from its named
field), no resource stop. Not retuned; no held-out seed opened. The next step is a roadmap
checkpoint, not a parameter.
