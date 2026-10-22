# Research map: plant2

This file maps the plant2 research program on branch `plant2-research-20261022`. It covers:

- the architecture as implemented, how each mechanism works, and what each mechanism is a labelled proxy for;
- the capabilities that meet the `demonstrated` bar in `docs/research/README.md`, kept apart from the results that do not meet it;
- known limitations, what the experimenter still supplies, and the architectural dependencies and invariants;
- the recovered plant that plant2 replaced, and a code map.

Last updated 2026-10-22. The map was built from independent extractions of the record. Those extractions were adversarially verified, and every reviewer correction was applied. The working files are under `.agent/ledger/` and are not part of the ledger. Three sources postdate that extraction and were read directly: `docs/plant2/EVIDENCE-DURABILITY.md`, `docs/plant2/P2-R2b-replication.md` and `docs/plant2/RESULTS-P2-R2b.md`.

Every number cites its source path and carries its label: gated, calibration, exploratory, reported-only, post hoc, descriptive or INVALID.

A capability appears in section 4 only if it is demonstrated. That means a gated, predeclared test passed on fresh seeds against a never-trained or shuffled control. Everything weaker goes in the separate table in section 5. Exploratory, reported, descriptive and post hoc numbers never appear in section 4, not even as caveats; section 4 points to sections 5 and 6 for them.

Proposed ideas live in `docs/research/BACKLOG.md` (items B-001 to B-012) and are not restated here. The contracts, results and reviews under `docs/plant2/`, `bench/results/` and `review/` remain the primary record. Where this map and a source disagree, the source wins and this map is corrected.

## 1. Status in one paragraph

Stage 1 is incomplete (`docs/plant2/STAGES.md:122-124`; `DECISIONS.md:878-880`).

Two gated experiments passed on five fresh seeds each. Both are scoped to independent random items at up to 0.25 items per memory cell, tested with frozen weights after a 50 s settle:
- **P2-E2:** one-shot index memory under slow threshold accommodation (seeds 6-10).
- **P2-E3:** one-shot content completion through a responder-written feedback store plus fixed inhibition (seeds 11-15). P2-E3 also tested on discarded deep copies.

Everything else so far has failed or is not a gate:
- **P2-E1** (BTSP alone): FAIL on completion.
- **P2-E4** (the P2-E2 + P2-E3 system run online): ONLINE INDEX FAIL + HABITUATION FAIL + RECOVERY FAIL.
- **P2-E5** (correlated F10/s60 items): STRUCTURED INDEX FAIL + STRUCTURED CONTENT FAIL.
- **Takeover passes:**
  - P2-R1 is a reported replay.
  - P2-E6 is a FEASIBILITY FAIL on its single development seed.
  - P2-R2's formal two-seed status is INVALID (one valid seed).

On 2026-10-22 the owner's research mandate made evidence durability the first engineering change (`DECISIONS.md:883-925`). The evidence-durability module is committed as `plant2/evidence.py` (`docs/plant2/EVIDENCE-DURABILITY.md`).

P2-R2b, a fresh two-seed replication of P2-R2's exact-degree input null, ran through that module:
- It was measured 2026-10-22, 17:06-17:09 UTC. Two workers started together.
- Both seeds are COMPLETE, and every artifact was verified.
- It replicated MATERIAL STRUCTURE SENSITIVITY at M = 1,000 on seeds 105 and 106.
- It is a reported replication of an explanation test, not a capability (`docs/plant2/RESULTS-P2-R2b.md:3-18`).

Per the review errata, this result "informs, and does not by itself authorise, the next mechanism contract" (`docs/plant2/RESULTS-P2-R2b.md:112-114`). No mechanism contract has been chosen since, and no Stage 2 work has started.

## 2. Architecture as implemented

### Populations

| population | size | model | constants (value, source) | labelled proxy for |
|---|---|---|---|---|
| `inp` | 4,000 lines (m) | Poisson sources. Per-tick spike probability is rate·dt/1000. m uniforms are drawn every tick whatever the rates (common random numbers). Item and cue lines run at r_on and all others at r_off; r_off applies everywhere during settle, gaps and background (`plant2/engine.py:14-29`) | a = 100 active lines per item (2.5 %) (`plant2/experiments/p2_e1_btsp.py:20`; `docs/plant2/P2-E1-btsp.md:55-56`); r_on 40.0 Hz; r_off 0.5 Hz (`p2_e1_btsp.py:20`); dt 1.0 ms (`plant2/engine.py:17`); per-tick probability 0.04 at 40 Hz and 0.0005 at 0.5 Hz (computed, `plant2/engine.py:25`) | CA3/entorhinal input that carries an experience (`docs/plant2/P2-E1-btsp.md:54-57`) |
| `mem` | 4,000 cells (n) | LIF with exact exponential leak toward rest, then delta inputs. Spikes are suppressed for t_ref ticks without clamping v; reset to v_reset.<br>Threshold accommodation (P2-E2 onward): θ_i = vbar_i + (v_th − v_rest), with vbar updated after the membrane update and before the spike test.<br>`quiet()` resets v, t_last and the delay ring but never vbar.<br>No recurrence, inhibition, noise current, injection or homeostat on written synapses. The layer never reads `rec` (`plant2/engine.py:31-84`) | tau_m 20.0 ms: leak factor 0.951229424500714 in float64, stored as float32 0.951229453086853 (both computed, `plant2/engine.py:43`)<br>v_rest −70.0, v_reset −65.0, v_th −50.0 mV; t_ref 2 ticks; d_max 1 (`p2_e1_btsp.py:22, 41`)<br>acc_tau 10,000 ms; none in P2-E1 (`p2_e2_accommodation.py:22, 43`)<br>θ = vbar + 20 mV; vbar starts at −70.0 mV (`plant2/engine.py:48, 55-58`)<br>Plateau probability f_q 0.005 per cell per episode, expected \|A\| = 20.0 (`p2_e1_btsp.py:20, 71`) | memory cells (CA1-like). The plateau is a proxy for entorhinal layer-III instructive input; accommodation is a proxy for slow Na+ inactivation and slow K+ currents (`plant2/btsp.py:1-12`; `docs/plant2/P2-E2-accommodation.md:35-61`) |
| `rec` | 4,000 cells (one per input line) | LIF with the memory constants, no accommodation and no sensory input. Its only inputs are mem→rec feedback (delay 1) and global inhibition (delay 2).<br>Under the P2-E3 protocol (P2-E3, P2-E5 gated arm, P2-E6, P2-R2, P2-R2b) it is replayed from the memory raster, starting at rest after the settle.<br>It runs live only in P2-E4's `Online` driver, which is reused by P2-E5's reported Part D online arm and P2-R1's duty capture (`plant2/readout.py:1-17`; `p2_e4_online.py:224-234`) | same tau_m, v_rest, v_reset, v_th, t_ref; d_max 2<br>Content window 75 ticks (k = 0..74; earliest causal spike k = 2); short window 50 ticks (reported) (`p2_e3_completion.py:27, 37`; `docs/plant2/P2-E3-content-completion.md:116-118`)<br>Span 300 ticks (the `e3.SPAN` constant is not read by `readout()`, `p2_e3_completion.py:27, 237-238`) | reconstruction layer with fixed 1:1 line-to-rec wiring (labelled) |

### Pathways

| from → to | synapse model | learning rule | constants (value, source) |
|---|---|---|---|
| inp → mem (BTSP forward store) | Binary w ∈ {0,1} on all 4,000 × 4,000 potential synapses, all starting at 0. Only w = 1 is stored (`BinarySynapses`: sorted int64 keys pre·n_post + post, with a CSR view by presynaptic cell). A spike on w = 1 adds J mV after 1 ms (`plant2/btsp.py:1-69`) | At episode end, each plateau cell i in A(x) × each eligible input j in E(x) toggles with probability 0.5, both 0→1 and 1→0. Coins are drawn E-major, A-minor. The rule never reads memory spikes, and no homeostat touches written synapses (Wu & Maass 2025, Eq. 1) | J 1.525 mV from P2-E2 on; 1.12 mV in P2-E1 and in the plain-E1 parity twins of P2-E3/E5 (`p2_e3_completion.py:25`; `p2_e1_btsp.py:21`; `p2_e5_structured.py:374, 860`)<br>delay 1 ms; p_flip 0.5; elig_min 3 spikes in the 200 ms encoding; f_q 0.005 (`p2_e1_btsp.py:20`)<br>Calibration (seed 0, not gated): grid 1.40-1.90 step 0.05; passing run 1.45-1.60; J* = 1.525 (`p2_e2_accommodation.py:26`; `docs/plant2/P2-E2-accommodation.md:202`)<br>P2-E1 J-rule history: J = 1.12 was fixed by a rule that double-counted 3.1 cue synapses (measured 24.69 vs predicted 27.76) (`docs/plant2/P2-E1-btsp.md:64-71, 272-282`) |
| mem → rec feedback (deployed, responder-written) | Binary, clipped, add-only `BinarySynapses(4000, 4000)`, key mem·m + line; strength J_fb, delay 1 ms | One-shot write after each continuation: w_fb(i→j) = 1 for every responder i in R(x) (≥ 1 memory spike in the 50 ms continuation) and every eligible line j in E(x). It never depresses and never reads the plateau set | J_fb 2.80 mV. Calibration on seed 0, not gated: passing run 2.00-3.60 at g = 0.3, grid 1.00-6.00 step 0.05 (101 values) for g = 0.3 and g = 0 (`p2_e4_online.py:40`; `p2_e3_completion.py:29, 284-287`; `docs/plant2/P2-E3-content-completion.md:297-304`)<br>t_cont 50 ms (`p2_e3_completion.py:37, 75-82`) |
| mem → rec global inhibition (fixed) | Each memory spike at tick t subtracts g·J_fb from every rec cell at t + 2. Not plastic (`plant2/engine.py:128-141`) | none | g 0.3; weight 0.84 mV per memory spike (computed 0.3 × 2.80); delay 2 ticks (`p2_e3_completion.py:26`; `p2_e4_online.py:232`; `plant2/readout.py:128`). The matched g = 0 arm is reported only |
| mem → rec assigned-A store (diagnostic) | Same binary store; replayed only, never deployed | `fb_plateau.add(A(x) × E(x))`, written from the experimenter's plateau set (`p2_e3_completion.py:83`) | Read at the frozen point J_fb 2.80, g 0.3 (`p2_e6.py:277-278`). "not a deployed mechanism or guaranteed upper bound" (`docs/plant2/P2-R2-degree-null.md:186-187`) |
| mem → rec diagnostic stores (R_k, shuffled, label-permuted) | Binary stores replayed through the memory raster; never deployed | R_k: cells with ≥ k continuation spikes, k ∈ {2,3,4,6}; grid_k = 3.<br>Shuffled: each cell keeps its synapse count and targets are redrawn without replacement (stream 10).<br>Label-permuted: R(x) writes onto E(π(x)) (streams 11 and 24) | Reported 72-point readout grid: J_fb ∈ {1.5, 2.0, 2.4, 2.8, 3.2, 3.6, 4.0, 5.0, 6.0} × g ∈ {0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0} (`p2_e5_structured.py:46-47, 208-240`; `p2_e3_completion.py:137-151`) |
| inp → mem, P2-E6 load-gated variant (candidate arm only) | Same binary store, J and delay | p_j = min(1, λ/h_j), with h_j = H_j + 1 and λ set by bisection so that Σp_j = 0.5·\|E_k\|. A synapse toggles iff its inherited coin u_ji < p_j. H is incremented after the write | pseudocount 1; budget 0.5 per eligible line; 80 bisections; atol 1e-9; random-control stream 31 (`docs/plant2/P2-E6-frozen.json:6-7`; `plant2/experiments/p2_e6.py:55-89`) |

### Learning episode, step by step

1. **Item draw.** A sorted choice of 100 of 4,000 lines from stream (seed, 0). In P2-E5, P2-E6, P2-R2 and P2-R2b it comes instead from the injected `FamilyGen`/`MatrixItems` generator. Quiet time between episodes is not simulated (`p2_e1_btsp.py:67-68`).
   - Loads: P2-E1 M = 1,000, with a capacity curve at 250-4,000 on seed 1 (reported).
   - P2-E2/E3 gate at 250, 500 and 1,000 and report 1,500 and 2,000.
   - P2-E4 gates at 500 and 1,000, with stress loads 1,500, 2,000 and 3,000.
   - P2-E5, E6, R2 and R2b use 500 and 1,000 (`p2_e1_btsp.py:27`; `p2_e2_accommodation.py:27-28`; `p2_e3_completion.py:30-31`; `p2_e4_online.py:40`; `p2_e5_structured.py:44-45`).
2. **`quiet()`.** Resets v, t_last and the ring but keeps vbar. Called in E1, E2, E3, the E5 gated arm and E6. Never called in P2-E4 `Online` or P2-E5's online arm (`plant2/engine.py:60-66`; `p2_e4_online.py:245-281`).
3. **Rates.** Item lines at 40 Hz and all others at 0.5 Hz, for both the encoding and the continuation (`p2_e1_btsp.py:59-63`).
4. **Plateau draw.** n uniforms from stream (seed, 2) select A(x) = cells with u < 0.005. The draw is content- and activity-independent and injects no current. Its validity bar is a mean \|A\| of 18.5-21.5 (`p2_e1_btsp.py:71`; `docs/plant2/P2-E1-btsp.md:79-84`).
5. **Encoding, 200 ms.** Input spikes come from stream (seed, 1). Earlier forward weights act during encoding; the store is updated only at the end (`p2_e1_btsp.py:74-77`).
6. **Eligibility.** E(x) = lines with ≥ 3 input spikes, taken from actual counts and never from item indices. About 0.6 background lines per item become eligible and are written. Validity bar: mean eligible fraction ≥ 0.95 (`p2_e1_btsp.py:78, 86-87`; `docs/plant2/P2-E3-content-completion.md:64-75`).
7. **BTSP toggle.** As in the pathways table; the forward CSR is then reloaded (`plant2/btsp.py:36-49, 62-69`; `p2_e1_btsp.py:55-57, 81-82`).
8. **Continuation, 50 ms** (P2-E3 on). No `quiet()`; same item and rates. Input comes from stream (seed, 9, len(items)−1), a 0-based key. R(x) = memory cells spiking at least once (`p2_e3_completion.py:75-80`).
9. **Feedback write.** `fb.add(R × E)`, plus the diagnostic `fb_plateau.add(A × E)`.
   - P2-E4 reloads the live projection immediately.
   - P2-E5 captures memory spikes through a read-only wrapper and expects exactly 250 steps (`p2_e3_completion.py:81-86`; `p2_e4_online.py:279-286`; `p2_e5_structured.py:149-184`).
10. **P2-E4 online step k.** Encoding 200 ms, continuation 50 ms, pre-gap 50 ms, probe slot 100 ms, post-gap 100 ms: 500 ms per step, rec live, no settle (`p2_e4_online.py:39-41, 322-371`).
11. **Variants.**
    - **P2-E6 candidate** replaces step 7 only.
    - **P2-R2/R2b** replace step 1 only, with a precomputed 1,000 × 4,000 matrix delivered through `MatrixItems` (`p2_e6.py:126-173`; `analysis/p2r2_degree_null.py:130-176`).

### Test protocol

- **Settle.** Before every test phase from P2-E2 on: 50,000 ms of background (5 × acc_tau). Convergence bar: mean absolute vbar change over the last 10,000 ms ≤ 0.2 mV (`p2_e2_accommodation.py:23-25, 71-80`).
- **Copies.** From P2-E3 on, each phase runs on a deep copy. The stores (and in E5/E6 vbar and H) must be bit-identical before and after (`p2_e3_completion.py:348-351`).
- **Cue sets.**
  - 100 oldest items plus 100 random later items, each with a fixed half mask (50 of 100 lines).
  - 200 novel items with half masks.
  - Full cues as a latency reference (`p2_e1_btsp.py:134-142`).
- **Presentation.** A 200 ms lead-in, then for each cue 100 ms of cue followed by a 200 ms gap (300 ms per cue).
  - Phase order: settle, 200 half cues, 200 novel half cues, 200 full cues.
  - P2-E1 `present()` calls `quiet()`; P2-E2 onward does not.
  - P2-E3 does not run P2-E2's 60 s phase, V-A, V-B or repeated-cue arms (`p2_e1_btsp.py:96-121`; `p2_e2_accommodation.py:49-69`; `docs/plant2/P2-E3-content-completion.md:101-112`).
- **Index window.** R50 = memory cells with a first spike within 50 ms of cue onset. Recall is also reported at 25 and 100 ms.
  - recall(x) = \|R50 ∩ A(x)\| / \|A(x)\|
  - spurious(x) = \|R50 \ A(x)\|
  - ignition(y) = \|R50\| for a novel cue (`p2_e1_btsp.py:129-131, 158-168`)
- **Content window.** A rec line counts as regenerated if it spikes at k = 0..74.
  - Missing half = the 50 uncued lines; non-eligible lines count as misses.
  - Intrusions = regenerated lines outside the item.
  - The 50 ms variant and whole cue-plus-gap intrusions are reported only (`plant2/readout.py:19-23, 83-107`).
- **Replay.** All readout arms are replayed from one memory raster: excitation J·count at delay 1, inhibition g·J·n_spikes at delay 2.
  - A ValueError is raised if onsets are closer than 75 ticks or a window runs past the raster.
  - Arms: main (J_fb*, g = 0.3); matched g = 0 (J0 = 1.45 fallback, no calibration window); g = 0 at J_fb*; plus shuffled, label-permuted and plateau-set stores at M = 1,000 (`plant2/readout.py:19-130`; `p2_e3_completion.py:232-242, 346-367`).
- **Persistence (C5).** 60,000 ms of background, then half and novel cues again. This runs as P2-E1 phase 2, and in P2-E2 at M = 1,000 with vbar carried (`p2_e1_btsp.py:239-247`; `p2_e2_accommodation.py:32`).
  - P2-E2 reported arms: a fixed-threshold copy at every load. At M = 1,000 only: a matched-density random store and a repeated-cue arm (20 items × 10 repeats) (`p2_e2_accommodation.py:225-248`).
- **P2-E4 probe slots.** 100 ms slots with the same windows.
  - Gated blocks are the 240 steps ending at M = 500 and 1,000: 50 recent, 50 uniform, 100 never-probed cohort, 20 novel and 20 blank cues.
  - The habituation arm runs on copies with learning paused and sham encodings (`p2_e4_online.py:39-53, 393-498, 514-687`).

### Criteria

| criterion | definition | bar | source |
|---|---|---|---|
| C1 completion | fraction of the 200 cued items with recall ≥ 0.80 in 50 ms | ≥ 0.90 (180/200, computed) | `p2_e1_btsp.py:24-25, 199-217`; `docs/plant2/P2-E1-btsp.md:111` |
| C2 specificity | fraction of cued items with spurious < 0.5·\|A(x)\| | ≥ 0.90 | `p2_e1_btsp.py:24-25, 207-213`; `docs/plant2/P2-E1-btsp.md:112-113` |
| C3 unlearned cues | fraction of the 200 novel half cues (P2-E4: 20 novel slots) with ignition < 0.5 × mean \|A\| | ≥ 0.90 | `p2_e1_btsp.py:24-25, 204-209`; `docs/plant2/P2-E1-btsp.md:114-116` |
| C4 retention | C1 and C2 on the 100 oldest items alone (C4_recall, C4_spurious) | each ≥ 0.90 (90/100) | `p2_e1_btsp.py:205-214`; `docs/plant2/P2-E1-btsp.md:116-118` |
| C5 persistence | C1-C3 again after 60 s of background. Vacuous in P2-E1 (`quiet()`); non-vacuous in form only in P2-E2 | each ≥ 0.90 | `docs/plant2/P2-E1-btsp.md:118-122, 300-307`; `docs/plant2/P2-E2-accommodation.md:396-399` |
| P2-E1 kill test | seeds 1-5; PASS only if every criterion holds on every seed. Validity: eligible fraction ≥ 0.95; strong-synapse set bit-identical before and after every test phase; mean \|A\| 18.5-21.5 | as stated | `p2_e1_btsp.py:24-26, 249-254`; `docs/plant2/P2-E1-btsp.md:106-126` |
| P2-E2 gate and voids | single J* = 1.525; PASS = valid, C1-C4 at M = 250, 500 and 1,000, and C5 at M = 1,000, on every gated seed.<br>Void V-A: the fixed-threshold copy must fail C2 or C3 at M = 1,000 on every gated seed (code: not(C2 and C3)).<br>Void V-B: the matched-density random store must fail C1 at M = 1,000.<br>Validity adds: store sha256 equals P2-E1 learning; convergence ≤ 0.2 mV.<br>Calibration: a J passes if C1-C4 ≥ 0.90 at all three loads; J* = midpoint of the longest contiguous passing run (tie: lower run) | as stated | `p2_e2_accommodation.py:22-35, 173-209, 255-274`; `docs/plant2/P2-E2-accommodation.md:77-141` |
| D1/D2 content joint | per cued item: ≥ 40 of 50 missing lines regenerated (D1) and < 10 intrusions (D2), within 75 ms | joint ≥ 0.90 of 200 at M = 250, 500 and 1,000 | `p2_e3_completion.py:28, 199-227`; `docs/plant2/P2-E3-content-completion.md:126-139` |
| D3 novel cues | a novel half cue regenerates < 10 lines in total | ≥ 0.90 of 200 | `p2_e3_completion.py:28, 210`; `docs/plant2/P2-E3-content-completion.md:137-138` |
| D4 old items | joint on the 100 oldest items | ≥ 0.90 | `p2_e3_completion.py:211, 227`; `docs/plant2/P2-E3-content-completion.md:139` |
| D5 memory layer | P2-E2's C1-C4 hold at the gated loads; failing them with content passing gives "CONTENT PASS / P2-E2 REPLICATION FAIL" | each ≥ 0.90 | `p2_e3_completion.py:245-249, 383, 394-419`; `docs/plant2/P2-E3-content-completion.md:140-147` |
| P2-E3 void, validity, calibration | Void: shuffled-feedback joint < 0.90 at M = 1,000 on every gated seed.<br>Validity: forward-store sha256 equals P2-E1; eligibility; mean \|A\|; convergence at the gate loads (flagged only at 1,500 and 2,000).<br>Calibration (seed 0): a J_fb passes if joint, D3 and D4 ≥ 0.90 at all three loads; J_fb* = midpoint of 2.00-3.60 = 2.80; the g = 0 fallback J0 = 1.45 (joint 0.885 at M = 1,000 on seed 0) | void if not | `p2_e3_completion.py:268-335, 375-419`; `docs/plant2/P2-E3-content-completion.md:148-190, 297-304` |
| O1 online index | C1 and C2 over 200 half cues and C3 over 20 novel cues, online | ≥ 0.90 each | `p2_e4_online.py:448-466`; `docs/plant2/P2-E4-online-memory.md:301` |
| O2 online content | joint over 200 half cues; D3 over 20 novel cues | ≥ 0.90 each | `p2_e4_online.py:459-465`; `docs/plant2/P2-E4-online-memory.md:302` |
| O3 retention | recall and joint over the 100 never-probed cohort cues | ≥ 0.90 each | `p2_e4_online.py:461-465`; `docs/plant2/P2-E4-online-memory.md:303` |
| O4 habituation | eligible items (scored and L_ctl ≥ 8) ≥ 25; habituated items (L_rep ≤ L_ctl − 3) ≤ 10 % of eligible. Fewer than 25 eligible = fail (not estimable), never skipped | as stated | `p2_e4_online.py:642-648`; `docs/plant2/P2-E4-online-memory.md:304, 307` |
| O5 recovery and collateral | among ≥ 25 control-copy passers (≥ 3 of 5 cues passing "both"), ≥ ceil(0.9 n) pass on the repeated copy. Estimability by `power.p_paired_majority` ≥ 0.8 | as stated | `p2_e4_online.py:649-655, 660-665`; `docs/plant2/P2-E4-online-memory.md:305` |
| P2-E4 validity 1-9 and labels | 1 forward store = P2-E1; 2 eligibility and mean \|A\|; 3 feedback store = union R × E; 4 no store change in a slot; 5 live projection current and inhibition = g × J_fb (holds by construction); 6 main line untouched by copies; 7 realised probe audit; 8 repetition 1 identical on both copies; 9 blank-slot leak check (≤ 1 of 20 blank targets recalled, L_A ≤ B_A + 0.05, L_C ≤ B_C + 0.05, positive control ≥ 0.5).<br>Labels: INVALID, PASS, ONLINE INDEX FAIL, ONLINE CONTENT FAIL, HABITUATION FAIL / NOT ESTIMABLE, RECOVERY FAIL / NOT ESTIMABLE | as stated | `p2_e4_online.py:47-53, 964-981, 1069-1122`; `docs/plant2/P2-E4-online-memory.md:319-377` |
| S1 structured index | C1, C2, C3 ≥ 180/200; C4_recall and C4_spurious ≥ 90/100, on F10/s60 items | as stated | `p2_e5_structured.py:55, 358-366`; `docs/plant2/P2-E5-structured-items.md:266-268` |
| S2 structured content | joint at the frozen readout (2.80, 0.3) | ≥ 180/200 | `p2_e5_structured.py:362-364`; `docs/plant2/P2-E5-structured-items.md:269` |
| S3 unlearned | D3 on 200 independent novel cues; cannot detect family contamination | ≥ 180/200 | `p2_e5_structured.py:363-364`; `docs/plant2/P2-E5-structured-items.md:270` |
| S4 oldest | joint on the 100 oldest items | ≥ 90/100 | `p2_e5_structured.py:364`; `docs/plant2/P2-E5-structured-items.md:271` |
| P2-E5 validity 1-7 and labels | 1 forward store = plain P2-E1 on the same items; 2 test copies leave stores and vbar bit-identical; 3 eligibility and mean \|A\|; 4 convergence ≤ 0.2 mV; 5 shuffled-store joint < 0.90 at M = 1,000; 6 within-family overlap 15.0-19.0 lines; 7 R(x) and store from captured continuation spikes.<br>Labels: INVALID, PASS, STRUCTURED INDEX FAIL, STRUCTURED CONTENT FAIL | as stated | `p2_e5_structured.py:44-55, 410-460, 503-531, 953-964`; `docs/plant2/P2-E5-structured-items.md:279-335` |
| P2-E5 reading thresholds (reported, none can change the verdict) | Part B: a loss dominates if ≥ 20 cues and ≥ 10 more than the others, on ≥ 4 seeds.<br>Part C: AVAILABLE FROM ACTIVITY if count AUC ≥ 0.95 and R_3 is within 10 cues of the plateau-set store.<br>Part D: WORSENS if the intrusion ratio R ≥ 1.25 on ≥ 4 seeds; NOT WORSE if R < 1.10 on ≥ 4 seeds.<br>Part E: replication and pooled-control labels | as stated | `p2_e5_structured.py:46-51, 976-1110`; `docs/plant2/P2-E5-structured-items.md:337, 377-480` |
| P2-E6 screen (development seed only, not gated) | Absolute bars: candidate at F10 and independent, both loads, C1, C2, C3, C4_recall and C4_spurious ≥ 0.9 and joint index ≥ 0.85.<br>Comparative: F10/1000 C2 ≥ baseline + 0.20 and ≥ random + 0.10; joint index ≥ each + 0.10.<br>Non-regression: C1 within 0.03 of baseline; independent C2 within 0.03; content joint and D4 within 0.05.<br>Protocol: eligibility ≥ 0.95; mean \|A\| 18.5-21.5; drift ≤ 0.2 mV.<br>Sanity: wrong-label C1 < 0.10; empty-store responders = 0 | as stated | `docs/plant2/P2-E6-frozen.json:14-18`; `plant2/experiments/p2_e6.py:423-484` |
| P2-R2 / P2-R2b labels (explanation test, not a gate) | at M = 1,000, Δ = null − original:<br>RECALL TRADE-OFF if ΔC1 or ΔC4-recall < −0.03.<br>MATERIAL STRUCTURE SENSITIVITY if ΔC2 ≥ 0.15 and Δjoint-index ≥ 0.10 without recall loss.<br>FAILURE PERSISTS WITH SMALL MEASURED BENEFIT if both C2 < 0.90 and \|ΔC2\|, \|Δjoint\| ≤ 0.05.<br>Otherwise MIXED/INTERMEDIATE.<br>Raw bar-deficit fraction removed = (C2_null − C2_orig)/(0.90 − C2_orig).<br>STRUCTURAL CONTRAST UNCERTAIN flags: endpoint \|D_null\| > max(1 line, 0.1\|D_orig\|), or late or between-chain relative Q change > 5 %, \|R\| change > 0.03 or \|D\| change > 0.5 lines | as stated; 20-minute wall ceiling | `analysis/p2r2_degree_null.py:221-235, 563-575`; `docs/plant2/P2-R2-degree-null.md:112-119, 202-219` |
| validity bars | mean eligible fraction ≥ 0.95; mean \|A\| 18.5-21.5; convergence ≤ 0.2 mV.<br>INVALID in P2-E1..E5 (P2-E3 convergence at 1,500 and 2,000 flagged only).<br>Screen parts in P2-E6, where only integrity failures give INVALID.<br>Reported without relaxation in P2-R2, where a programming integrity failure gives INVALID | as stated | `p2_e1_btsp.py:24-25`; `p2_e6.py:316-318, 449-454, 476-479`; `docs/plant2/P2-R2-degree-null.md:190-193`; `docs/plant2/P2-E3-content-completion.md:161-163` |

### Random streams

Every generator is `np.random.default_rng([seed, id, *extra])`, keyed by purpose (`p2_e1_btsp.py:32-33`).

| id | key | purpose | source |
|---|---|---|---|
| 0 | (seed,0) | item draws | `p2_e1_btsp.py:29, 47` |
| 1 | (seed,1) | encoding input spikes in every experiment, m uniforms per tick. It is the only stream BTSP reads; the continuation uses stream 9 | `p2_e1_btsp.py:48, 75`; `p2_e3_completion.py:76` |
| 2 | (seed,2) | plateau draw, n uniforms per episode | `p2_e1_btsp.py:71` |
| 3 | (seed,3) | BTSP coins, \|E\|·\|A\| per episode. Variable length, so it desynchronises across arms | `p2_e1_btsp.py:81`; `docs/plant2/P2-R2-degree-null.md:156-159` |
| 4 | (seed,4,M) | test-set selection and half masks | `p2_e1_btsp.py:135-141` |
| 5 | (seed,5,M,phase) | test input: 1 main, 2 persistence, 99 the 60 s background, 100+phase settle, 77 repeated-cue arm; (seed,5,0,7) never-trained twin | `p2_e1_btsp.py:152, 240, 246`; `p2_e2_accommodation.py:34, 73, 154` |
| 6 | (seed,6) | 200 novel items | `p2_e1_btsp.py:49-50` |
| 8 | (seed,8) | P2-E2 matched-density random store | `p2_e2_accommodation.py:33, 84` |
| 9 | (seed,9,k−1) | continuation input (0-based key) | `p2_e3_completion.py:76`; `p2_e4_online.py:268` |
| 10 | (seed,10,M) | shuffled feedback store | `p2_e3_completion.py:138` |
| 11 | (seed,11,M) | label permutation (P2-E3) | `p2_e3_completion.py:147` |
| 12-17 | (seed,12..17,…) | P2-E4: background, slot input, rolling slot kind, block builder, habituation, novel cue. The habituation key uses the 0-based plan position i + 1, not the item id | `p2_e4_online.py:33, 583` |
| 18 | (seed,18,arm,…) | P2-E4 reported arms 1-5 (twins, writes during probes, OOD, duty) | `p2_e4_online.py:33-34, 311, 380, 771, 843, 859, 880, 1052` |
| 20 | (seed,20,F) | F prototypes of 100 lines | `p2_e5_structured.py:76-78` |
| 21 | (seed,21,F,k) | exemplar k, 1-based; k = 0 is forbidden because it aliases (seed,21,F) | `p2_e5_structured.py:81-85, 103-112` |
| 22 | (seed,22,M) | P2-E5 reported cue block | `p2_e5_structured.py:129-144` |
| 23 | (seed,23,k) | pooled-control exemplars | `p2_e5_structured.py:107-111` |
| 24 | (seed,24,M) | within-family derangement (P2-E5) | `p2_e5_structured.py:222-235` |
| 30 | (seed,30,item,kind) | P2-R1 random and anti-selected writers | `analysis/p2r1_replay.py:30, 65-66` |
| 31 | (seed,31,item,cell) | P2-E6 flip-count-matched random control | `p2_e6.py:84`; `docs/plant2/P2-E6-frozen.json:7` |
| 32 | (seed,32,M) | P2-E6 wrong-label raster permutation | `p2_e6.py:353` |
| 40 | (seed,40,F,block,chain) | P2-R2/R2b Curveball chains (chain 0 delivered, chain 1 diagnostic) | `analysis/p2r2_degree_null.py:253`; `docs/plant2/P2-R2-degree-null.md:72-76` |

### Input generators

- **Independent random items.** Used in P2-E1..E4, in the "independent" arms of E5 and E6, and in the E5 `s100` arm. Each is a sorted 100-of-4,000 draw from stream 0, with about 2.5 % pairwise overlap. The `s100` arm is P2-E3's own generator, not `FamilyGen` with s = 100 (`p2_e1_btsp.py:47-52, 67`; `p2_e5_structured.py:37-38, 122-126`).
- **`FamilyGen`, the canonical F10/s60 condition.** Ten hidden prototypes of 100 lines each (stream 20), never shown. Exemplar k belongs to family k mod F.
  - At s = 60 it **retains 40 prototype lines and replaces 60** with lines outside the prototype (stream 21).
  - M = 500 gives 50 exemplars per family; M = 1,000 gives 100.
  - Expected sibling overlap is (100 − s)²/100 = 16 lines plus chance. The contract states 16.9 over all within-family pairs; the validity bar is 15.0-19.0 (`p2_e5_structured.py:44-45, 76-119`; `docs/plant2/P2-E5-structured-items.md:177-195`).
  - Reported arms: s80 (about 4-6 % overlap), s40 (about 36 %), F40 (families of 12-25) and pooled (`docs/plant2/P2-E5-structured-items.md:197-209`).
- **Pooled control.** Draws 40 lines from the union of the ten prototypes and 60 from outside the exemplar's own prototype (stream 23). There is no sibling correlation; sibling overlap is about 3.7 %. The P2-R1 audit found it matches line loads only approximately and flattens hotspots: main max line loads are 137-148 vs pooled 81-89 at M = 1,000 (`docs/plant2/EVAL-after-P2-E5.md:127-131`).
- **Exact-degree Curveball null** (P2-R2, P2-R2b).
  - The 1,000 canonical F10/s60 rows are split into ten fixed blocks of 100 consecutive episodes, with no trades across blocks.
  - Each block gets exactly 10,000 attempted row-Curveball heat-bath trades.
  - This preserves every row size (100) and every column sum within each block, hence line totals at M = 500 and 1,000.
  - Snapshots are taken at 0, 2,500, 5,000 and 10,000 trades.
  - The chain-0 endpoint is delivered through `MatrixItems`; chain 1 is structural only (`analysis/p2r2_degree_null.py:30-32, 130-176, 238-295`; `docs/plant2/P2-R2-degree-null.md:58-81`).

### Code/contract disagreements recorded by the extraction

1. **Prototype size.** `docs/plant2/STAGES.md:85` says "60-line prototype". The code and contract give 100-line prototypes with 40 retained and 60 replaced (`p2_e5_structured.py:37, 44-45, 76-85`; `docs/plant2/P2-E5-structured-items.md:179-181`). The correction is recorded at `docs/plant2/STAGES.md:106-109` and `docs/plant2/EVAL-after-P2-E5.md:134-136`; the row text is not edited. STAGES.md:85 also says siblings share "about 16 %" of lines, while the audit measured 16.92-16.95 lines (`bench/results/p2r1-audit.jsonl`).
2. **Continuation stream key.** `docs/plant2/P2-E3-content-completion.md:60-61` says stream (seed, 9, k) "for item k". The code uses (seed, 9, len(items)−1), a 0-based index (`p2_e3_completion.py:76`; `p2_e4_online.py:268`).
3. **Habituation copy key.** `docs/plant2/P2-E4-online-memory.md:141` gives (seed, 16, M, x + 1, s) with x the item. The code uses i + 1, with i the 0-based position among the 50 selected items (`p2_e4_online.py:583, 595, 627`). The two are statistically equivalent.
4. **Label joining.** `docs/plant2/P2-E4-online-memory.md:376` says every failure label is joined. The code discards HABITUATION/RECOVERY NOT ESTIMABLE whenever the family's FAIL label is present (`p2_e4_online.py:1089-1091`). This is acknowledged at `:598, 660-661`.
5. **P2-E1 integration wording.** `docs/plant2/P2-E1-btsp.md:58-60` says "forward Euler as in the plant". The engine uses exact exponential decay (0.9512 vs Euler 0.9500, `plant2/engine.py:3-4, 43-44`), corrected at `docs/plant2/P2-E1-btsp.md:255-258`.
6. **P2-E2 reported arms.** The contract promises the random-store arm at every load (`docs/plant2/P2-E2-accommodation.md:173`) and a 100-pair wrong-cue null (`:171`). The code runs the random store only at M = 1,000 and a 200-pair label-shuffled null (`p2_e2_accommodation.py:118-125, 232-236`). This is acknowledged at `:425-426`. The P2-E2 Result also cites P2-E1's digest (`:223-224`), corrected at `:419-420`.
7. **P2-E3 label-permuted degrees.** The contract (`docs/plant2/P2-E3-content-completion.md:184-185`) says every degree is kept. The code permutes whole items, so degrees are kept only approximately: per-cell degree is equal for 36 % of cells (correlation 0.9996) and per-line degree for 3.6 % of lines (correlation 0.947) (`:556-559`).
8. **P2-E3 docstring.** `p2_e3_completion.py:9` shows `--J 2.6`, while the contract fixes J_fb* = 2.80 (`docs/plant2/P2-E3-content-completion.md:304`). E4 and E5 use the CONTRACT value 2.80; `e3.CONTRACT` has no J_fb key.
9. **Index convention, not a disagreement.** "Age-0 blanks in odd sub-blocks" (`docs/plant2/P2-E4-online-memory.md:199`) matches the code's (0, 2, 4, 6, 8) only under 1-based sub-block numbering (`p2_e4_online.py:42, 120`).

## 3. How each mechanism works and what it is a labelled proxy for

**BTSP binary index write.** Each item turns on 100 of 4,000 input lines for 200 ms. An independent random stream picks the item's plateau set A(x): each memory cell joins with probability f_q = 0.005, so about 20 cells. At episode end, every synapse from an eligible line (≥ 3 spikes) onto a plateau cell toggles with probability 0.5. Weights are binary, with J = 1.525 mV and a 1 ms delay.

The rule never reads memory-cell spikes, so the stored index is a random code assigned by the experimenter. A half cue is scored by whether it re-evokes A(x) within 50 ms.

It is a labelled proxy for CA1 behavioural-timescale plasticity as simplified by Wu & Maass 2025. Plateaus stand in for entorhinal layer-III instructive input, and the ≥ 3-spike rule stands in for the seconds-long eligibility trace (`plant2/btsp.py:1-69`; `docs/plant2/P2-E1-btsp.md:46-90`). Alone, at J = 1.12 mV with a fixed threshold, it FAILED C1 at 0.810-0.860 (gated, `docs/plant2/P2-E1-btsp.md:176-188`).

**Slow threshold accommodation.** Each memory cell's threshold is θ_i = vbar_i + 20 mV, where vbar_i tracks the cell's own membrane potential with a 10 s time constant. `quiet()` never resets it, and a 50 s background settle precedes every test phase. Cells that receive more strong synapses sit at higher thresholds, so the network works at one J for all loads.

The offset correlates 0.994-0.998 with each cell's strong-synapse count (descriptive, `docs/plant2/P2-E2-accommodation.md:283-284, 362-363`). It is a labelled proxy for slow Na+ inactivation and slow K+ currents (Azouz & Gray 2000; Platkiewicz & Brette 2011), with "no claim of biology beyond that label."

The owner accepted it as a mechanism distinct from the closed K0.14 intrinsic homeostat. Its membership in the same homeostatic family is recorded (`DECISIONS.md:312-318`).

**One-shot feedback content store plus fixed feedforward inhibition.** After each encoding, the item stays on for a 50 ms continuation. Every memory cell that spikes in that window (R(x)) gets a binary, add-only synapse of J_fb = 2.80 mV onto the rec cell of every eligible input line. Each rec cell is wired 1:1 to one input line.

At test, a fixed inhibition subtracts 0.84 mV (g = 0.3 × J_fb) from every rec cell per memory spike, at delay 2. That implements a count threshold of about 30 % of active memory cells and sets an operating band around 0.25 items per cell. It is not a capacity mechanism (`docs/plant2/P2-E3-content-completion.md:77-87, 478-479, 526-527`).

The store is spiking Willshaw-style hetero-association (Willshaw et al. 1969) with a BTSP-like postsynaptic eligibility, and it stores the input verbatim. The inhibition is a labelled proxy for interneuron feedforward inhibition (Pouille & Scanziani 2001). It is declared as an owner-approved element that is never a learning mechanism (`DECISIONS.md:326-331, 420-429`).

**P2-E6 presynaptic-history gating (tested, rejected under its frozen screen).** Each input line counts the earlier episodes in which it was eligible (H_j). Toggle probabilities become p_j = min(1, λ/(H_j + 1)), with λ set by 80 bisections so that the expected number of flips stays at 0.5·\|E\|. Frequently used lines therefore write less.

It is labelled a computational metaplasticity proxy and "not a biological implementation claim". The normalisation is "a labelled circuit-level proxy, not a strictly pair-local rule" (`docs/plant2/P2-E6-load-gated-encoding.md:21-53`).

On development seed 101 it was a complete, integrity-valid FEASIBILITY FAIL with exactly two failed parts: F10/1000 C2 179/200 and oldest specificity 89/100 (`docs/plant2/RESULTS-P2-E6.md:90-95`). The reviewer's statement: "the mechanism is rejected under its frozen acceptance criteria" (`review/plant2/P2-E6/findings-results.md:65`). Held-out seed 102 and gated seeds 111-115 are unrun.

**R3 burst writer (reported replay only).** Memory cells with at least three spikes in the 50 ms continuation, instead of at least one, write the feedback store. It was tested only as a store swap, replayed on an unchanged settled raster at the frozen readout (J_fb 2.80, g 0.3). The comparisons were the inherited R1, the assigned plateau set, a size-matched random subset and an anti-selected subset.

The owner ruled it "first a reported replay/diagnostic, not a gated eligibility mechanism" (`DECISIONS.md:778-782`). It recovers the experimenter-assigned key with micro precision/recall of .9975/.9657 (correlated, M = 1,000) and .9986/.9997 (duty, M = 1,000) (reported, `docs/plant2/RESULTS-P2-R1.md:25-30`). The record calls this "evidence for recovering an assigned key from activity, not selecting an autonomous representation." It is a labelled proxy for burst-gated eligibility and is not deployed anywhere.

## 4. Demonstrated capabilities

Only these two meet the README's `demonstrated` bar: gated, predeclared, five of five fresh seeds, against void or shuffled controls. Every number in this table is gated. The labelled exploratory and reported numbers that bound these claims are in sections 5 and 6.

| capability | scope conditions | evidence (gated numbers, seeds, source) | what it does not show |
|---|---|---|---|
| One-shot index memory. A half cue re-evokes the written assembly within 50 ms; unlearned half cues ignite almost nothing; the oldest items are retained. C1-C3 hold again on a re-sample after 60 s of background | Independent random sparse items (100 of 4,000 lines); one 200 ms exposure; M = 250, 500, 1,000 (≤ 0.25 items per cell); BTSP plus accommodation at one J* = 1.525 mV (calibrated on seed 0); tested after a 50 s settle with frozen weights and no `quiet()` in test; half cue, 50 ms window. Gated seeds 6-10 | **Gated:** C1 0.945-0.985, C2 0.965-1.000 and C3 0.990-1.000 at every gated load. C4 at M = 1,000: recall 0.93-0.97, spurious 0.96-1.00. C5: 0.915-0.975 / 0.975-0.995 / 0.990-1.000.<br>**Void controls:** the V-A fixed-threshold copy gives C2 0.000-0.015 and C3 0.000; the V-B matched-density random store gives C1 0.000. PASS, valid, not void, 5/5 (`docs/plant2/P2-E2-accommodation.md:221-250`).<br>The index replicates as P2-E3's D5 on fresh seeds 11-15 with the continuation added: C1 0.925-0.985, C2 0.975-1.000, C3 0.990-1.000 (gated, `docs/plant2/P2-E3-content-completion.md:344-348`) | - That the system chose its code: plateaus are random and assigned.<br>- Recall without the settle, or online: P2-E4 FAILED (section 6).<br>- Specificity beyond 0.25 items per cell (section 6).<br>- Capacity growth with cell count: untested.<br>- Real persistence: C5 is non-vacuous in form only (`docs/plant2/P2-E2-accommodation.md:396-399`).<br>- A sharp null: both void controls were near-certain to fail, and V-B fails by construction (`:367-377`).<br>- Correlated items: P2-E5 FAILED |
| One-shot content completion. A half cue regenerates the missing half of the stored input on the reconstruction layer within 75 ms, with few intrusions; novel half cues regenerate almost nothing | Independent random items (about 2.5 % overlap), exactly-half cues; one exposure; M = 250, 500, 1,000 (≤ 0.25 items per cell); P2-E3's back-to-back `quiet()` learning protocol; frozen deep copies after a 50 s settle, plasticity off; J_fb 2.80, g 0.3. Gated seeds 11-15 | **Gated:** joint 0.955-1.000 (≥ 0.990 at M ≤ 500), D3 0.99-1.0, D4 0.940-1.000; PASS, valid, not void, 5/5 (`docs/plant2/P2-E3-content-completion.md:331, 340-348`).<br>**Control:** shuffled-feedback joint 0.000 at M = 1,000 on every gated seed (`:361`) | - Online learning: P2-E4 FAILED its index and habituation gates; the online-timeline numbers for this store are in section 6.<br>- Correlated items: P2-E5 FAILED.<br>- Capacity past about 0.25 items per cell: the store saturates rather than forgets (section 6).<br>- Generalisation or abstraction: the value is copied verbatim and nothing reads rec.<br>- A control that could fail: the shuffled store fails by construction ("met in letter only", `:563-567`).<br>- That inhibition is needed: the matched g = 0 comparison is reported only (section 5) |

## 5. Observed, reported-only or invalid results that are NOT demonstrated capabilities

| result | label | scope conditions | evidence (numbers, seeds, source) | what it does not show |
|---|---|---|---|---|
| BTSP alone writes specific one-shot traces | gated test FAILED; medians from 5 valid seeds | J 1.12 mV, fixed threshold, M = 1,000, `quiet()` before tests; seeds 1-5 | Median recall 0.920-0.941 at 50 ms (1.00 at 100 ms); median spurious 2; C2 0.905-0.950; C3 0.945-0.980 (median ignition 2, max 15-21). But C1 is 0.810-0.860 against 0.90 and C4 recall 0.820-0.890 (`docs/plant2/P2-E1-btsp.md:176-188, 240-248`; `bench/results/plant2.jsonl:1-5`).<br>Full cues: median recall 1.00 at 50 ms and median first-spike latency 10 ms (reported, `:246, 311`) | A pass, or any load-independent operating point. At M = 2,000 and 4,000, C2 and C3 are 0.000 (reported, seed 1 only, `:244`). The never-trained twin is vacuous |
| P2-E1 engine and store are implemented correctly | code review | reviewer checks on the seed-1 store | Dense float64 LIF replay matched the engine with 0 mismatches over 1,800 ticks; the dense toggle model matched the sparse store over 3,600 updates; seed 1 reruns to C1 0.840 (`review/plant2/P2-E1/findings-code.md:7, 17-21`) | Anything about capability; F7 gaps remain (no library versions, tautological `weights_unchanged`) |
| P2-E2 reported arms | reported, not gated | gated seeds 6-10 | 0 hub cells at every gated load; median half-cue latency 22-23 ms (`docs/plant2/P2-E2-accommodation.md:280-282`). Capacity edge: C1 0.93 at M = 1,500 and 0.90-0.93 at M = 2,000, while C2 is 0.715-0.775 and 0.30-0.37 (`:292-301`) | Latency online; capacity growth with cell count |
| P2-E3 fast regeneration | descriptive | main arm, gated seeds, settled copies | Median reconstruction error 0.04 (about 2 of 50 lines); latency 23-25 ms at M = 250/500 and 25-28 ms at M = 1,000 (`docs/plant2/P2-E3-content-completion.md:383, 386-387`) | Latency online or above 0.25 items per cell |
| P2-E3 feedback operating window is wide | calibration, seed 0 only | g = 0.3 | one contiguous passing run of 2.00-3.60 mV, about ±29 % (`docs/plant2/P2-E3-content-completion.md:297-304`) | The same window on other seeds |
| Fixed inhibition makes M = 1,000 regeneration pass | reported comparison, settled at calibration | matched g = 0 at J = 1.45 (fallback); gated seeds 11-15 | matched g = 0 joint 0.770-0.860 vs main 0.955-0.985; g = 0 at J_fb* 0.065-0.155 (`docs/plant2/P2-E3-content-completion.md:364-369, 514-528`) | Need at M ≤ 500 (the matched arm passes, 0.92-0.965); capacity extension (at M = 1,500, g = 0 beats main) |
| Online content regeneration and online specificity | gated sub-criteria passed inside a FAIL verdict; no failable control | online timeline, live rec, M = 500 and 1,000, independent items; seeds 16-20 | O2 joint 0.93-0.995, D3 1.0, O3 content 0.90-1.0; C2, C3 and D3 all 1.0 (`docs/plant2/P2-E4-online-memory.md:639-650`) | - An accurate online write: the online-written store gives 0.82-0.905 on twin A at M = 1,000 (reported, `:697-703`).<br>- Online index: C1 0.68-0.74 at M = 1,000, and 0.89/0.87 on seeds 16/17 at M = 500 (gated FAIL).<br>- "No artefact control can fail in this architecture" (`:314-317`) |
| Settled state passes index and content at M = 500 | reported arm (twin B) | 50 s settle, P2-E3 rhythm, same synapses; seeds 16-20 | Twin B settled index 0.965-0.98 and content 0.99-1.0 at M = 500; at M = 1,000, settled index 0.92-0.975 and content 0.835-0.915 (`docs/plant2/P2-E4-online-memory.md:736-737`) | Online passes. At M = 1,000 no state passes both on every seed; seed 18's twin B reaches 0.955/0.915 (`docs/plant2/EVAL-after-P2-E4.md:223-230`) |
| Blank-slot leak check and twin A replay fidelity | validity checks | 20 blank slots per block; both loads; seeds 16-20 | leak_ok on all five seeds; age-0 cued recall 0.84-0.98; twin A replay had 0 differing spikes in 463k-665k (`docs/plant2/P2-E4-online-memory.md:337-349, 632-634`) | A gated control that can fail. Validity 5 holds by construction |
| Lower-offset duty schedule restores online index access | reported arm on gated seeds | I = 2,000 ms, M = 1,000; seeds 16-20 | C1 0.945-0.985, but the store collapses: twin A 0.175-0.245, online joint 0.485-0.565 (`docs/plant2/P2-E4-online-memory.md:714-715`) | That the offset alone causes it, since the whole schedule changes. The arm was predeclared unable to satisfy the online clause |
| Learning outside the write oracle | reported stress/OOD arms | online state; seeds 16-20 | writes during probes 0.165-0.20 recallable; 30 % cues C1 0.00; noisy half cues 0.075-0.175; lures sharing 50 lines recalled as the stored item 0.90-0.95 (`docs/plant2/P2-E4-online-memory.md:727-730`) | Autonomous learning. Storage depends on the exposure length the experimenter sets (skeptic NS-4) |
| Habituation is graded and universal | post hoc reading | copies with learning paused and sham encodings; M = 500 and 1,000; seeds 16-20 | every item recalls less than its control; mean drop 0.107-0.134; net offset rise 2.0-2.1 mV (`docs/plant2/P2-E4-online-memory.md:804-814`) | That it arises under real encodings; any link to the online index failure |
| The frozen system replicates P2-E3 on independent items | reported arm on gated seeds | s100 arm (P2-E3's generator), settled; seeds 21-25 | joint 0.99-1.0 at M = 500 and 0.97-0.99 at M = 1,000 (`docs/plant2/P2-E5-structured-items.md:922, 987`) | Anything about correlated items |
| Low sibling overlap passes at the lower load | reported arm on gated seeds | s80, F10, M = 500; seeds 21-25 | joint 0.99-0.995 (`docs/plant2/P2-E5-structured-items.md:988`) | It fails at M = 1,000 (0.62-0.74); s40 gives 0.0 at both loads (`:988-990`) |
| The plateau key is recoverable from continuation activity (Part C, AVAILABLE FROM ACTIVITY) | reported reading on gated seeds; a measurement, not a mechanism | gated arm F10/s60, both loads; seeds 21-25 | count AUC 0.9988-0.9995 at M = 500 and 0.9955-0.9971 at M = 1,000; R_3 store within 0-7 cues of the plateau-set store (`docs/plant2/P2-E5-structured-items.md:939-947`) | That the network chooses its own writers: it "reads back the experimenter's key" |
| Assigned-A comparator completes correlated content at the lower load | reported diagnostic comparator | same raster, frozen readout, F10/s60, M = 500; seeds 21-25 | plateau-set S2 186-195 of 200, R_3 186-194, deployed store 19-36 (`docs/plant2/P2-E5-structured-items.md:355-357, 932-937`) | - A solution, or a mathematical upper bound (`docs/plant2/EVAL-after-P2-E5.md:137-138`).<br>- At M = 1,000 no tested store reaches S2 (plateau-set 28-35 frozen, 126-141 at the optimistic grid best) |
| R3 writers restore correlated content at the lower load | reported replay; one reused exploratory seed | F10/s60, M = 500, settled raster, frozen readout; seed 44 | joint .090 (R1) → .965 (R3), equal to assigned A (.965); random .300; anti-selected .090 (`docs/plant2/RESULTS-P2-R1.md:13-22`) | - The full index contract (oldest specificity .84).<br>- Live operation; generalisation across seeds.<br>- At M = 1,000, content is .160 with C2 .500 (`docs/plant2/STAGES.md:116`) |
| R3 writers restore content on an online-written duty store | reported replay; one reused diagnostic seed whose values were known before the contract | I = 2,000 ms duty schedule, M = 1,000, read settled; seed 90 | joint .995 (R3) vs .205 (R1), .710 (size-matched random) and .655 (anti-selected); paired wins 57/0, 68/0, 158/0 (`docs/plant2/RESULTS-P2-R1.md:18, 36-41`) | Live access (live inherited joint .545); O4/O5 repair. Part of the gain is sparsity |
| P2-R1 store swaps leave the raster and index unchanged; P2-E4/E5 verdicts recompute | reported checks and aggregate audit | all loads; baseline 55e16eb | same raster for every arm; corr1000 C2 .500 for every writer (`bench/results/p2r1.jsonl:5, 7, 9, 11`); 80/20/10/30 audit checks passed (`bench/results/p2r1-audit.jsonl:1`) | A raw-data replication (all 28 historical raw cache paths are absent). The check flags are constants emitted after raise-guards pass |
| Presynaptic-history encoding raises F10 index specificity | observed on one development seed; FEASIBILITY FAIL | settled, F10/s60, frozen parameters; seed 101 | M = 1,000: C2 0.500 / 0.895 / 0.460 and joint index 0.440 / 0.865 / 0.410 (baseline / candidate / flip-count-matched random); paired specificity 79:0 and 87:0; spurious responders 16.970 → 3.145.<br>M = 500: the candidate meets all six absolute bars (C2 1.000, joint 0.945) (`docs/plant2/RESULTS-P2-E6.md:12-47`)<br>Latency 23 vs 24 ms; sanity checks pass (wrong-label C1 = 0, empty store 0 responders) (`:97-98`) | - The frozen M = 1,000 bars (C2 179/200, oldest specificity 89/100).<br>- Seed generality; an isolated causal mediator.<br>- Content: inherited joint .785 at 500 and .065 at 1,000 |
| Presynaptic-history encoding does not materially regress independent inputs or F40 index | observed on one development seed; F40 is reported transfer only | settled, both loads; seed 101 | Independent: C2 0.990 vs 0.975 and joint content 0.975 vs 0.975 at M = 1,000; C1 −.025. F40/1000 candidate C2 .950, joint .890 (`docs/plant2/RESULTS-P2-E6.md:55-58, 105-116`) | Multi-seed robustness. F40 inherited content fails (1,000 joint .200) |
| Exact-degree input null raises high-load specificity (MATERIAL STRUCTURE SENSITIVITY) | one valid seed; formal status INVALID | F10/s60 vs block Curveball null, M = 1,000; seed 103 | C2 .470 → .755, joint index .410 → .675, C1 .930 → .920, oldest specificity .410 → .680; inherited content .005 → .075; assigned-A .130 → .320 (`docs/plant2/RESULTS-P2-R2.md:76, 84-88`) | - A capability; the absolute bars still fail.<br>- "Does not show that line frequency is the sole residual cause or that the plant learned pattern separation" (`:133-137`) |
| Exact-degree null at low load | one valid seed; descriptive | M = 500; seed 103 | C2 .895 → 1.000; inherited content .115 → .980; oldest recall .980 → .910 (`docs/plant2/RESULTS-P2-R2.md:75, 90-94`) | Preserved memory |
| The null was delivered as specified; the protocol ran inside the ceiling | structural check; engineering feasibility | both seeds, F10 and F40, both chains | D 14.45394 → 0.00248 and 14.39250 → −0.00171; Q 36.73036 → 18.90274 and 36.83363 → 19.15428; walls 194.49 s and 198.32 s (`docs/plant2/RESULTS-P2-R2.md:12-22, 46-65`) | A uniform-sampling certificate; durability of evidence (one artifact and two events were lost) |
| Seed-104 recovered values | INVALID attempt; descriptive, post hoc reconstruction | ORIGINAL/M1000 artifact rebuilt hash-exact (1,883,558 bytes) | ΔC2 +.255, Δjoint +.240 (post hoc, `docs/plant2/RESULTS-P2-R2.md:32-37, 80-82`) | A valid replication; the cause of the loss |
| The exact-degree contrast replicates on two fresh seeds | reported replication of an explanation test; COMPLETE with verified evidence | F10/s60 vs block Curveball null at M = 1,000 and 500; seeds 105 and 106; CPython 3.11.17, NumPy 2.4.6 | - M = 1,000: C2 .485 → .745 and .455 → .720; joint index .420 → .660 and .390 → .670; ΔC2 +0.260 / +0.265; bar-deficit fraction removed 0.62651 / 0.59551; assigned-A content .175 → .315 and .110 → .295 (MATERIAL GAIN).<br>- M = 500: inherited content .115 → .960 and .140 → .965.<br>- Predictions P1-P4 held; P5 failed; P6 failed on seed 106 (`docs/plant2/RESULTS-P2-R2b.md:26-46, 54-61, 109-111`) | - A memory capability: null C2 (.745, .720) and oldest specificity (.710, .680) still fail .90.<br>- The design "does not apportion the failure between line load and co-occurrence" (`:96-101`).<br>- It removes no supply |

## 6. Known limitations

### 6.1 Cross-cutting

- **Correlated items break both index and content (P2-E5, gated, `docs/plant2/P2-E5-structured-items.md:897-908`).**
  - On F10/s60 items, content fails on every gated seed at both loads: the deployed store passes 19-36 of 200 cues at M = 500.
  - The M = 500 index failure rests on 2 of 5 seeds, by 2-6 cues.
  - At M = 1,000, C2 is 0.435-0.515 and C4 spurious is 0.35-0.49 on every seed.
  - An earlier check on P2-E3 gave joint 0.147/0.167 at M = 500 on seeds 99/97 (exploratory, `docs/plant2/P2-E3-content-completion.md:487-502`).
- **High-load forward-index cross-talk survives every intervention tried** (P2-E6, P2-R2, P2-R2b; `docs/plant2/RESULTS-P2-E6.md:12-43`; `docs/plant2/RESULTS-P2-R2.md:76`; `docs/plant2/RESULTS-P2-R2b.md:26-40`).
  - The P2-E6 candidate reaches C2 .895 (one seed).
  - The exact-degree null reaches C2 .720-.755 on three valid seeds.
  - At M = 1,000, inherited content stays ≤ .075 and assigned-A content ≤ .320.
- **No online operating point.**
  - O1 C1 is 0.68-0.74 at M = 1,000, and 0.89/0.87 on seeds 16/17 at M = 500 (P2-E4, gated, `docs/plant2/P2-E4-online-memory.md:639-650`).
  - P2-E3 wrote at a continuation offset of 8.35-8.56 mV and read at 3.65-3.74 mV after the settle. The record therefore says it relied on separate encoding and retrieval states (`docs/plant2/P2-E4-online-memory.md:773-774`). The P2-R1 errata soften "never both": seed 18's settled twin B reaches 0.955/0.915 (`docs/plant2/EVAL-after-P2-E4.md:223-230`).
  - The index needs the rest: P2-E2's C1 was 0.875 with no settle, 0.915 after 5 s and 0.94 after 50 s (exploratory, seed 0, `docs/plant2/P2-E2-accommodation.md:380-391`).
  - On an online timeline, P2-E3's store gives settled joint 0.81/0.89, and 0.165 with a 2 s interval (exploratory, seeds 42-43, `docs/plant2/P2-E3-content-completion.md:612-642`). P2-E4's online-written store gives 0.82-0.905 (reported).
- **Habituation under repeated cues (P2-E4, gated, `docs/plant2/P2-E4-online-memory.md:655-661, 690-692`).**
  - 50-64 % of eligible items habituated on the estimable seeds 17-19 at M = 500, against a 10 % bar.
  - Seeds 16 and 20 at M = 500, and every seed at M = 1,000, are not estimable but are labelled FAIL.
- **Capacity edge between 0.25 and 0.375 items per cell; no forgetting.**
  - Index C2 is 0.715-0.775 at M = 1,500 (P2-E2, reported, `docs/plant2/P2-E2-accommodation.md:292-301`).
  - The feedback store saturates: density 0.133 / 0.23 / 0.36 at M = 1,000 / 1,500 / 2,000. Novel cues reach 1,225-3,509 lines at M = 1,500 (P2-E3, reported, `docs/plant2/P2-E3-content-completion.md:504-513`).
  - Growth with cell count, bounded capacity and graceful forgetting are all unshown. The owner made the last two prerequisites for any lifelong-memory claim (`DECISIONS.md:408-409`).
- **Operating point calibrated on one held-out seed.**
  - The J* window 1.45-1.60 (about ±5 %) and the J_fb* window 2.00-3.60 (about ±29 %) come from seed 0 (calibration).
  - g = 0.3 was fixed by hand from prior exploration with different dynamics (P2-E2, P2-E3; `p2_e4_online.py:898`; `docs/plant2/P2-E3-content-completion.md:83-85`).
  - "Inhibition required" was settled at calibration and holds at M = 1,000 only (`:514-528`).
- **Controls that cannot fail** (`docs/plant2/P2-E3-content-completion.md:563-570`; `docs/plant2/P2-E5-structured-items.md:279-287`).
  - P2-E2's V-A and V-B were near-certain to fail.
  - P2-E3's shuffled store fails by construction, and `stores_unchanged_by_tests` compares a copy with itself.
  - P2-E4's validity 5 holds by construction.
  - P2-E5's S3 cannot detect family contamination, and "a gated control that could pass if the claim were false" is not met.
- **Persistence is not tested against decay.** C5 is vacuous in P2-E1 and non-vacuous in form only in P2-E2 (`docs/plant2/P2-E1-btsp.md:300-307`; `docs/plant2/P2-E2-accommodation.md:396-399`).
- **Single-seed and reused-seed evidence.**
  - P2-E6 rests on seed 101.
  - P2-R1 rests on reused seeds 44 and 90 that "already informed the hypotheses" (`review/plant2/P2-R1/findings-results-methodology.md:47`).
  - Two seeds in P2-R2/P2-R2b are explanatory screening, not a five-seed gate (`docs/plant2/P2-R2-degree-null.md:199-200`).
- **The null changes more than co-occurrence.**
  - About 95 % of each episode's active lines are replaced.
  - BTSP coin draws desynchronise (713/722 episodes).
  - Eligibility column counts differ by up to 3 in P2-R2 (`docs/plant2/RESULTS-P2-R2.md:103-116`) and by 2-3 in P2-R2b (`docs/plant2/RESULTS-P2-R2b.md:48-50`).
- **A low-load recall cost seen once did not recur.** Seed 103's oldest-recall loss of 0.070 at M = 500 (.980 → .910) did not recur on seeds 105/106 (−0.010, +0.010), so P5 failed. It stays a seed-103 observation (P2-R2b, `docs/plant2/RESULTS-P2-R2b.md:60-68`).
- **Evidence durability before 2026-10-22.**
  - P2-R2 seed 104's combined artifact was found empty at the paired read, and the cause is unresolved.
  - `plant2/evidence.py` guards new drivers only; frozen drivers are not retrofitted (`docs/plant2/EVIDENCE-DURABILITY.md`).
  - Raw caches are absent on this host for P2-E1, for the historical P2-E4/E5 runs (28 paths) and for P2-E6 (`review/plant2/P2-R1/findings-baseline-methodology.md:41`).
- **Runtime drift.**
  - This PC runs CPython 3.11.17 / NumPy 2.4.6. The takeover ran 3.12.14 / 2.3.5, and the P2-R1 replay reviewer ran 3.13.16 / 2.5.3.
  - No byte-identical rasters across runtimes are claimed (`DECISIONS.md:910-913`).
  - Records before the takeover omit library versions, and NumPy SIMD kernels can change digests (`plant2/record.py:31-32`).

### 6.2 Limitations recorded per experiment

- **P2-E1** (`docs/plant2/P2-E1-btsp.md`):
  - Only M = 1,000 was gated; the capacity curve is seed 1 only, n = 1 per point (`:160-163, 291-293`).
  - One fixed J (1.12 mV), from a rule with a double-count error (actual margin 1.24× not 1.4×). The "no operating point" claim rests on unrecorded reviewer sweeps (`:272-299`).
  - C5 and the never-trained twin are vacuous; real nulls were post hoc (`:300-307`).
  - The 50 % masked half cue lies outside Wu & Maass's demonstrated regime (one third masked). Other deviations: trace = plateau set, one fixed threshold, full connectivity, f_w 0.6 in the paper. "These make the test stricter, not easier" (`:313-319`).
  - A(x) is an assigned code, so a pass would not be evidence of thinking power (`:320-323`; `docs/plant2/STAGES.md:54-57`).
  - Plateau gate, eligibility window and episode boundaries are protocol-supplied proxies (`review/plant2/P2-E1/findings-methodology.md:53-57`).
  - Item-level overdispersion (sd 0.105-0.127 vs about 0.07) was not modelled (`review/plant2/P2-E1/findings-code.md:41-45`).
  - Library versions were not recorded, and the npz arrays are absent here.
  - Testing is settled and offline only (`:92, 300-302`; `docs/plant2/STAGES.md:45`).
- **P2-E2** (`docs/plant2/P2-E2-accommodation.md`):
  - Load independence holds only after 5-50 s of background (exploratory, seed 0, `:380-391`).
  - J* was calibrated on seed 0. The calibration-seed prediction cleared C1 by about 0.035; the gated minimum C1 at M = 1,000 is 0.945, and 0.915 after 60 s.
  - C5 re-samples the same equilibrium; the convergence statistic sits near a noise floor at high load.
  - The paired P2-E1 comparison also differs in J and in no-reset state; paired seed 5's record is INVALID.
  - Reported offsets (6.0 mV mean, 10.2-10.3 mV p95) include cue duty, and items 1-100 saw lower thresholds.
  - Habituation is known only from the 10-repeat arm and an exploratory single-seed 30 s run (0.99 → 0.79 → 0.67, `:400-411`).
  - Reviewer evidence is exploratory and unrecorded, and its scripts are missing here.
  - Provenance: records are `dirty = true`; the Result cites P2-E1's digest (`:419-420`).
  - Promised arms did not run as specified (`:425-426`).
  - It is a labelled intrinsic-threshold proxy in K0.14's family. It gets no credit for capacity growth (`docs/plant2/STAGES.md:58-60`) and shows neither bounded capacity nor graceful forgetting (`:63-64`).
- **P2-E3** (`docs/plant2/P2-E3-content-completion.md`):
  - One item size, cue fraction, rate and duration (`:483-485`).
  - Tests ran on deep copies after a settle; online learning, interference and habituation are untested (`:436-438`).
  - Verbatim value; nothing reads rec (`:419-440, 474-482`).
  - Capacity ends between 0.25 and 0.375 items per cell (`:439-440, 504-513`).
  - Gated controls could not fail; label-permuted keeps degrees only approximately (`:554-570`).
  - "Inhibition required" only at M = 1,000 (`:514-528`).
  - Single-seed calibration (`:83-85, 192-205`).
  - The window-key fix changed seed 0's D5 label and was looked for because D5 looked bad (`:539-544`).
  - Provenance: the calibration and gated trees differ by a 17-line verdict subcommand; predictions were committed about 7 s before the gated runs; gated seed 13 was used in a unit test (`:571-582`).
  - Five seeds resample one iid distribution (skeptic NS5).
  - Exploratory scripts are absent.
  - The PASS is scoped to the back-to-back `quiet()` protocol (`:636-641`).
  - Per-seed g = 0, plateau-set and C4 values appear only as ranges.
- **P2-E4** (`docs/plant2/P2-E4-online-memory.md`):
  - P2-E4 removes nothing at learning time (`:768-777`).
  - Sham encodings miss the post-write burst; rec sits about 1.5-3 mV nearer rest (`:75-81`).
  - O4 and O5 were not estimable at M = 1,000, nor O4 on seeds 16 and 20; the labels absorb this into FAIL (`:660-661`).
  - RECOVERY FAIL depends on a per-seed-and-load reading; the all-seeds reading is NOT ESTIMABLE, and seed 18's M = 500 copies were not replayed.
  - Validity 5 holds by construction, validity 4 depends on `BinarySynapses` rebinding, and validity 9 has no content positive control (`:314-317, 348-349`).
  - Twin B and the duty arm change the schedule as well as the state.
  - The trade-off is shown for the responder write, not the architecture.
  - Post hoc numbers (C1 at 75 ms about 0.955-0.97, recovery asymmetry 57 vs 2, the O4 null model) are not gates.
  - Predictions used seeds 42-43 only; P(PASS) was 0.768-0.786, just below the 0.8 target (`:432-434`).
  - Blocks span loads (261-500, 761-1,000); M = 250 is not gated.
  - Source disagreements recorded in the extraction:
    - The cohort sizes of the revised unfrozen contract vs the frozen one; the frozen text governs.
    - The power headline: 0.83 vs 0.855 / 0.788 / 0.62.
    - Seed 18's p0: 0.83 vs 0.831 vs 0.829.
    - Control-copy rates: 0.81-0.85 vs 0.75-0.82 vs 0.61-0.65.
    - Range scopes for lures, writes during probes and \|R\|.
    - The habituation stream key.
    - "Failed as predicted" vs the label probabilities.
    - "Never both" vs the P2-R1 errata.
    - Skeptic NS-2's usable-load reading.
    - O4 estimability wording.
    - The M = 3,000 stress joint: 0.00 vs 0.0-0.01.
    - "Failure to store" wording (`DECISIONS.md:606` vs `:716`).
    - P2-E5 exploration figures cited in EVAL-after-P2-E4.
- **P2-E5** (`docs/plant2/P2-E5-structured-items.md`):
  - A diagnostic that removes no supply and adds one, the item distribution (`:159-160, 1022-1023`).
  - The M = 500 index failure is not robust (`:905-907`).
  - Part B depends on the optimistic, edge-censored grid-best convention (`:927-935`).
  - Part C is scored against the assigned A(x); k = 3 was fixed in advance (`:939-947`).
  - Part D compares whole regimes and sits at floor at M = 1,000 (`:948-956`).
  - The online-vs-settled C2 comparison is unpaired (`:971-977`).
  - The pooled control does not isolate sibling organisation, and "correlation-attributable" is a frozen label (`docs/plant2/EVAL-after-P2-E5.md:127-131`; `:994-996`).
  - S3 cannot detect contamination (`:270, 279-287`).
  - New-exemplar and prototype cues measure cross-talk, not generalisation (`:548-567`).
  - Results hold for s = 60, F = 10, settled; P(PASS) = 0 is not proof that a pass is impossible (`:807-810, 979-981`).
  - Items are not persisted, and the caches are absent (results-code CC-4).
  - Part F per-line rates are biased about 5 % low (CC-1).
  - Exploratory numbers rest on seeds 44-45 (`:16-17`).
  - Seven gated records are dirty outside `plant2/` (`:877-879`).
- **P2-E6** (`docs/plant2/RESULTS-P2-E6.md`; `docs/plant2/P2-E6-load-gated-encoding.md`):
  - One development seed; paired cue fractions are "within one network" (`RESULTS:27-30`).
  - Seeds 102 and 111-115 are unrun (`RESULTS:94-95, 134`).
  - The random control matches attempted flips only, so there is no isolated mediator (`RESULTS:28-30, 41-43`).
  - C3 uses independent novel cues, not related unseen exemplars.
  - Cumulative history estimates prevalence within supplied episodes, and the F40 result does not show nonstationary robustness (`review/plant2/P2-E6/findings-contract-methodology.md:23-24`).
  - The aggregate normalisation is not pair-local, and probabilities above 0.5 raise both potentiation and depression (contract `:44-48`).
  - The metaplasticity framing is unvalidated (contract `:21-26`).
  - The reviewer did not rerun the dynamics (`RESULTS:126-128`).
  - F10 and F40 content stays poor at M = 1,000.
  - The probability fields describe candidate probabilities in all arms.
  - A pseudocount of 1 is not identical to the original 0.8-equivalent prior.
  - Selection through the screen must be disclosed beside any later five-seed result.
  - The raw cache is absent here.
- **P2-R1** (`docs/plant2/RESULTS-P2-R1.md`; `review/plant2/P2-R1/`):
  - Two reused seeds, and 200 cues are not independent samples.
  - All R3/A/random/anti results are settled-copy replays; only R1 was read live (.545).
  - "Index interference persists" is an interpretation.
  - Assigned keys, write timing, eligibility and values remain supplied.
  - One control realisation each; union sizes and degrees differ.
  - Raw NPZ and historical caches are absent; no cross-runtime bit identity.
  - `out_of_window_spikes` is raw-replay-only.
  - The reviewer did not rerun the simulation; the check flags are constants.
  - Source disagreements:
    - "about 16 %" vs 16.9 lines.
    - Duty C2 .970 settled vs .995 live.
    - The audit `--append` target.
    - "Measured 2026-10-12" vs author dates of 2026-10-11 (the same instants).
    - Absolute evidence paths.
  - Takeover environment gaps: no push credentials, the safety wrapper could not collect (12 grandfathered lint findings), and pytest plugins were disabled (`DECISIONS.md:801-825`).
- **P2-R2** (`docs/plant2/RESULTS-P2-R2.md`; `docs/plant2/P2-R2-degree-null.md`):
  - Formally INVALID; seed 104 is descriptive and post hoc (`RESULTS:80-82`).
  - The intervention changes more than frequency: cumulative-count deviation max 7/9, RMS 0.86565/0.86611 (`RESULTS:103-116`).
  - The Curveball budget is not a proven mixing time; only chain 0 was used (contract `:78-81`).
  - Block constraints keep coarse age marginals only (contract `:122-125`).
  - Assigned-A is a supplied reference (contract `:186-187`).
  - Two seeds, with no pooled CI by design (`:197-200`).
  - The absolute bars fail at M = 1,000 on all stores.
  - Seed 103's 0.070 loss at 500.
  - F40 evidence is structural only.
  - Persistence integrity gaps: no fsync, lock, sequence chain or readback (findings-integrity `:27-31`).
  - The four-process limit was enforced manually.
  - Reviewers did not rerun the dynamics or chains.
  - The safety wrapper could not collect.
  - Journal snapshot record count: 61 vs 60 + 1.
  - Contract-review provenance gap: the pre-review draft is not in git history.
  - The record denies autonomous keys, online capability, related-unseen rejection, a new mechanism, capacity growth, graceful forgetting, abstraction, Stage 1 completion and Stage 2 authorisation.
  - Latency summaries exist only in the portable artifacts.

## 7. What the experimenter still supplies

- **When to write (the write oracle).** Plateaus and feedback writes happen only inside protocol-marked encodings, which tells the system which inputs are new and which are tests. Episodes begin with `quiet()`, and the write fires at a protocol-set tick (P2-E3 `docs/plant2/EVAL-after-P2-E3.md:44-46`). Restated by P2-E4, P2-E5, P2-E6, P2-R1 and P2-R2.
- **Episode segmentation.** One item per episode, state reset between items, quiet time not simulated (P2-E1 `docs/plant2/P2-E1-btsp.md:75-76`). Episode boundaries act as a write signal to be removed before Stage 2 (P2-E3, `review/plant2/P2-E3/findings-northstar_constructive.md` F5).
- **The key.** Plateau cells are drawn at random (f_q 0.005), independent of content, and a re-exposed item gets a second, unrelated memory (P2-E1 `docs/plant2/P2-E1-btsp.md:78-84, 320-323`; P2-E3 `docs/plant2/EVAL-after-P2-E3.md:47-48`). R3 and Part C only recover it (P2-E5, P2-R1). Access to A for precision/recall is evaluation-only (P2-R1).
- **The value.** Eligible lines are copied 1:1 onto rec, so the store is input-supervised and verbatim (P2-E3 `docs/plant2/EVAL-after-P2-E3.md:49-50`). Every writer stores the same eligible lines (P2-R1). P2-E2 regenerates no input content; its half cue recovers the assigned assembly only (`docs/plant2/P2-E2-accommodation.md:324`).
- **The input code.** Items are 100 of 4,000 lines at 40 Hz against 0.5 Hz, drawn uniformly (P2-E1 `docs/plant2/P2-E1-btsp.md:54-57`).
- **The eligibility rule and window.** At least 3 spikes in 200 ms (P2-E1 `docs/plant2/P2-E1-btsp.md:85-86`). The 50 ms continuation after each encoding, and the rule that rec is not simulated during learning (P2-E3 contract `:51, 57-62`).
- **The write constants.** p_flip 0.5, binary weights, full connectivity, a fixed threshold in P2-E1, and J set by a rule that double-counted cue synapses (P2-E1 `docs/plant2/P2-E1-btsp.md:61-71, 87-90`).
- **The operating point.**
  - In P2-E1, J "was placed by its rule at the only load where the two effects nearly balance" (`docs/plant2/P2-E1-btsp.md:235-238`).
  - In P2-E2, J came from a predeclared midpoint rule on a held-out seed, and the experimenter set the accommodation setpoint (20 mV) and tau (10 s) (P2-E2 addendum item 1).
  - From P2-E3 on: J_fb, g fixed by hand, and recall that needs rest before testing (P2-E2 addendum 3; `docs/plant2/EVAL-after-P2-E3.md:50-54`).
  - The operating point depends on input duty, and the responder write's specificity depends on the operating point at write time (P2-E4).
  - The fixed inhibition (g = 0.3) is an owner-approved element with matched comparisons (P2-E3 contract `:20-22`).
  - All of these are frozen in P2-E4, E5, E6, R1 and R2. The R3 threshold k = 3 is also fixed (P2-R1).
- **Separate encoding and retrieval states set by the schedule.** Named by P2-E4 (`docs/plant2/P2-E4-online-memory.md:773-774`; `docs/plant2/STAGES.md:84`). The pre/post gaps (50/100 ms) and the probe exposure length, on which storage depends, are also set by the experimenter (P2-E4, skeptic NS-4). The I = 2,000 ms duty schedule is supplied too (P2-R1).
- **The input statistics.** Independent random patterns with clean half cues and item boundaries (P2-E3 `docs/plant2/EVAL-after-P2-E3.md:55-56`). P2-E5 adds hidden prototypes, the overlap s, the family count F and cyclic family order. P2-E6 adds the family/exemplar generator. P2-R2 supplies the original family labels, used only as diagnostic annotations.
- **The test regime.** Discarded copies with plasticity off (P2-E3 `docs/plant2/EVAL-after-P2-E3.md:57-58`). Habituation copies with sham encodings (P2-E4). The 50 s settle, checkpoint deep copies, and the half, novel and full cue sets (P2-E6, P2-R2).
- **The cue protocol, windows and bars.** Fixed half masks, the 50 ms and 75 ms windows, the 0.80/0.90/0.5 bars, the cue set and the 60 s test (P2-E1 `docs/plant2/P2-E1-btsp.md:92-125`).
- **Diagnostic stores.** The inherited responder-written store and, as diagnostic only, the assigned-A store, which uses the supplied key (P2-E6, P2-R2). Writer-selection rules for the random and anti-selected controls (P2-R1).
- **A sparsity prior and aggregate normalisation.** Budget 0.5·\|E\| with pseudocount 1 (P2-E6, `review/plant2/P2-E6/findings-contract-methodology.md:5`).
- **The randomisation recipe.** Row Curveball, 10,000 trades, 100-episode blocks, chain stream keys and fixed seeds (P2-R2, P2-R2b).
- **Standing tests.** "Every experiment is judged by whether it reduces the cognition the experimenter supplies" (`docs/plant2/STAGES.md:71`). P2-E1 records no assessment beyond its labelled proxies. The P2-R1 handoff adds that accommodation "alone is not independent cognition" (`docs/plant2/HANDOFF-takeover-20261012.md:109-112`). P2-R2: "The plant has not learned when to store, how to allocate its own keys, or when to retrieve."
- **Removed so far.** Only the rest before testing and the frozen-copy regime, and only for P2-E4's main-line gated numbers, which then failed (`docs/plant2/EVAL-after-P2-E4.md:16-19`). P2-E5, P2-E6, P2-R1, P2-R2 and P2-R2b remove nothing ("No experimenter-supplied structure is removed", `docs/plant2/RESULTS-P2-R2.md:133-137`; `docs/plant2/RESULTS-P2-R2b.md:80-82`).

## 8. Architectural dependencies and invariants

### Invariants

| invariant | statement | source |
|---|---|---|
| Index window 50 ms | memory responders are first spikes within 50 ticks of onset (C1-C4, S1, O1/O3); not relaxed retrospectively | `p2_e1_btsp.py:21`; `p2_e4_online.py:48`; `docs/plant2/P2-E6-frozen.json:13`; `DECISIONS.md:789-790` |
| Content window 75 ms | regenerated lines spike at k = 0..74 (D1-D4, S2-S4, O2); the 50 ms variant is reported only | `p2_e3_completion.py:27, 37`; `p2_e4_online.py:48`; `DECISIONS.md:789-790` |
| Ten families canonical | F10/s60 is the canonical structured condition | `p2_e5_structured.py:45`; `DECISIONS.md:791-792`; `docs/plant2/EVAL-after-P2-E5.md:144-145` |
| F40 transfer only | forty families is a transfer diagnostic, never a replacement; it never rescues or vetoes F10 | `DECISIONS.md:791-792`; `docs/plant2/RESULTS-P2-E6.md:116` |
| Frozen readout primary | the deployed frozen readout decides; best-over-grid is an explicitly optimistic diagnostic | `DECISIONS.md:793` |
| Frozen memory parameters | J_mem 1.525 mV; acc_tau 10,000 ms; settle 50,000 ms; no other J is run from P2-E3 on | `p2_e3_completion.py:25`; `p2_e2_accommodation.py:22-23`; `docs/plant2/P2-E6-frozen.json:13` |
| Frozen readout parameters | J_fb 2.80 mV and g 0.3 (0.84 mV at delay 2) for every gated or deployed readout; no retuning after failure. P2-E6/R2 hard-code J 2.8, g 0.3, windows 75/50 and 0.9 content bars. The frozen JSON's frozen, mechanism, margins, protocol, sanity and resource fields are not read by code, and the hard-coded values match them | `p2_e4_online.py:40`; `p2_e6.py:277-282, 436-484`; `analysis/p2r2_degree_null.py:399-404` |
| Timing constants | dt 1 ms; encoding 200 ms; continuation 50 ms; cue 100 ms; gap 200 ms; lead-in 200 ms; settle 50,000 ms; convergence window 10,000 ms; delays inp→mem 1, mem→rec 1, inhibition 2 | `p2_e1_btsp.py:20-22`; `p2_e2_accommodation.py:23-25`; `p2_e3_completion.py:37` |
| Inherited source baseline | the seven reused files equal their blobs in plant2 tree `9152f1e4`. For P2-E6, P2-R2 and P2-R2b they and `p2_e5_structured.py` (plus `record.py` for R2/R2b) are pinned to baseline `55e16eb`. The extraction verified this at HEAD `447b2ab`; it was not re-verified for this map (no git during the P2-R2b window) | `p2_e5_structured.py:40-42`; `p2_e6.py:38-39, 494-507`; `analysis/p2r2_degree_null.py:35-36` |
| Forward store identity | for independent items the forward store equals unmodified P2-E1 learning (sha256), because BTSP reads only stream 1. P2-E6 does not require it of the candidate | `p2_e2_accommodation.py:246`; `p2_e3_completion.py:357-360`; `docs/plant2/P2-E6-load-gated-encoding.md:166-167` |
| Tests never change weights | stores (and vbar, H) are bit-identical across test phases; tests run on deep copies | `p2_e3_completion.py:348-351`; `p2_e6.py:313-314` |
| vbar is adaptive state | `quiet()` never resets vbar; no P2-E2/E3/E4 test phase calls `quiet()` | `plant2/engine.py:60-66`; `p2_e2_accommodation.py:49-69` |
| One changed variable per experiment | P2-E4 changes the protocol, P2-E5 the generator, P2-E6 the toggle probabilities, P2-R2/R2b the input matrix | `docs/plant2/P2-E4-online-memory.md:83-92`; `docs/plant2/P2-R2-degree-null.md:153-163` |
| Contracts frozen before code; gated seeds run once | append-only after freeze; run-once markers. Frozen commits: P2-E4 `cd17cde`, P2-E5 `bc28cd9`, P2-E6 `6733109`, P2-R2 `2454f06`, P2-R2b `4cd865b` | `p2_e4_online.py:1277-1311, 1346-1357`; `p2_e5_structured.py:53`; `docs/plant2/P2-E6-frozen.json:3`; `analysis/p2r2_degree_null.py:28`; `docs/plant2/RESULTS-P2-R2b.md:3-5` |
| Results append-only | `bench/results/plant2.jsonl`, `p2e6.jsonl`, `p2r1.jsonl`, `p2r2.jsonl` and `p2r2b.jsonl`. Derived data goes under `~/.cache/brain-sim/` (`BRAINSIM_CACHE` override) | `plant2/record.py:10, 13-18, 48-59`; `p2_e6.py:36`; `analysis/p2r1_replay.py:27`; `analysis/p2r2_degree_null.py:33`; `docs/plant2/P2-R2b-replication.md` ("What differs", item 5) |
| Evidence durability for new drivers | exclusive-create, fsync, read-back, hashed artifacts; per-worker hash-chained journals; verification before consumption. Frozen drivers keep their own writers | `docs/plant2/EVIDENCE-DURABILITY.md`; `DECISIONS.md:902-906` |
| Plant frozen | the recovered plant's paths are not edited; plant2 is a separate package | `AGENTS.md` (invariant 4); `docs/plant2/STAGES.md:31-35` |

### Driver inheritance chain

- `p2_e1_btsp.E1` defines the network, learning, test sets and criteria, and imports `engine`, `btsp` and `record`.
- `p2_e2_accommodation.E2(e1.E1)` adds accommodation, a `present()` without `quiet()`, and `settle()`.
- `p2_e3_completion.E3(e2.E2)` adds the continuation, the feedback write and raster capture. It reads out through `plant2/readout.replay`.
- `p2_e4_online.Online(e3.E3)` adds live rec, the feedback projection, global inhibition and the probe-slot schedule.
- `p2_e5_structured.E5(CaptureMixin, e3.E3)` and `OnlineE5(CaptureMixin, e4.Online)` swap only `_pat` for `FamilyGen`.
- `p2_e6.E6(e3.E3)` replaces only the toggle probabilities. It uses `e5.FamilyGen`, `CONTRACT` and `REUSED_FILES`, and `analysis.p2r1_replay` for digests.
- `analysis/p2r2_degree_null.py` feeds the unchanged E3 learner through `MatrixItems`, with original rows from `e5.FamilyGen`.
- `analysis/p2r2b_replication.py` imports the frozen `p2r2_degree_null` as `r2`, executed byte-identical to `c7a5350`.
  - It rebinds exactly `SEEDS`, `RESULTS`, `EVIDENCE`, `CONTRACT_PATH`, `CONTRACT_COMMIT`, `SOURCES`, `write_json`, `write_npz` and `paired_evidence`.
  - It leaves `r2.INHERITED` untouched, so the inherited files must still equal `55e16eb`.
  - It writes through `plant2/evidence.py`, and a unit test asserts the rebound set (`docs/plant2/P2-R2b-replication.md`, "What differs" item 2).
- `plant2/readout.py` mirrors the engine's arithmetic bit for bit without importing it; `test_p2_e3.py` checks this.
- `plant2/power.py` serves P2-E4 and P2-E5. `plant2/predict.py` is imported by tests only.

Byte-identical at HEAD `447b2ab` (extraction-verified blob ids):

| file | blob id |
|---|---|
| `p2_e4_online.py` | `bc4d1282` |
| `p2_e3_completion.py` | `0a7b6cea` |
| `p2_e2_accommodation.py` | `9cc4f5a9` |
| `p2_e1_btsp.py` | `efaf58f4` |
| `engine.py` | `06795755` |
| `readout.py` | `b114297c` |
| `btsp.py` | `e159d485` |
| `p2_e5_structured.py` | `fd1d3718` |
| `record.py` | `ca9b5ecd` |

### Inherited frozen state

- **Network.**
  - m = n = 4,000; a = 100; 40.0 / 0.5 Hz.
  - LIF tau_m 20.0 ms; v_rest −70.0, v_reset −65.0, v_th −50.0 mV; t_ref 2; dt 1 ms; d_max 1 (mem) and 2 (rec).
  - p_flip 0.5; f_q 0.005; elig_min 3.
  - Encoding 200 ms, continuation 50 ms, cue 100 ms, gap 200 ms (`p2_e1_btsp.py:20-22`; `p2_e3_completion.py:37`).
- **Calibrated values** (seed 0, calibration): J* 1.525 (run 1.45-1.60); J_fb* 2.80 (run 2.00-3.60); g = 0 fallback 1.45 (reported) (`docs/plant2/P2-E2-accommodation.md:202`; `docs/plant2/P2-E3-content-completion.md:297-304`).
- **P2-E6 constants, if reused.** Pseudocount 1, budget 0.5, 80 bisections, atol 1e-9 (`docs/plant2/P2-E6-frozen.json:6-18`).
- **P2-R2 constants.** 10 blocks of 100, 10,000 attempted trades per block, snapshots 0/2,500/5,000/10,000, chain 0 delivered (`analysis/p2r2_degree_null.py:30-31`).
- **Seeds spent.**
  - E1: 1-5, plus capacity seed 1.
  - E2: 0 (calibration), 6-10 (gated), 1-5 (paired).
  - E3: 0, 11-15; exploratory 99/97 and 42-43.
  - E4: 42-43 (exploration), 16-20.
  - E5: 44-45 (exploration), 21-25.
  - P2-R1: 44 and 90.
  - E6: 101; 102 and 111-115 unrun.
  - R2: 103, 104.
  - R2b: 105, 106.
  - Sources: `p2_e2_accommodation.py:29-31`; `docs/plant2/STAGES.md:116`; `docs/plant2/RESULTS-P2-R1.md:15-18`; `docs/plant2/P2-R2-degree-null.md:132-135`; `docs/plant2/P2-R2b-replication.md` ("What differs" item 1).

### Owner rulings that constrain the architecture

- **2026-10-10.**
  - plant2 is a separate package on non-main branches; nothing merges to `main` without "merge"; the plant stays frozen; contracts precede code (`DECISIONS.md:214-223`).
  - Rejected: editing the plant, continuing K1.1 on it, and a literal anatomy replica (`DECISIONS.md:237-243`).
- **2026-10-10.**
  - P2-E2 is accepted as distinct from K0.14, and its PASS stands with every limitation (`DECISIONS.md:312-318`).
  - Capacity is scaled with input and memory together (`:319-325`).
  - P2-E3 may use fixed activity-proportional inhibition with matched controls and frozen parameters, and learning stays one-shot (`:326-331`).
  - Standing discipline: no threshold revision, no unplanned tuning, fresh gated seeds, independent review of every result (`:333-350`).
- **2026-10-10, post-P2-E3.** These rulings were drafted with an outside assistant and relayed by the owner (`DECISIONS.md:390-392`).
  - Structured-input robustness becomes a Stage 1 gate (`DECISIONS.md:394-402`).
  - P2-E4 is scoped to online memory, and bounded capacity and graceful forgetting are required before any lifelong-memory claim (`:403-419`).
  - Inhibition is never a learning mechanism, and the coefficient does not carry over (`:420-429`).
  - Error-correcting write is an approved direction, with one mechanism per contract; familiarity-gated allocation is deferred (`:430-443`).
  - The Stage 3 gate is strengthened (`:444-451`).
- **2026-10-11.**
  - Complete P2-E4 exactly as frozen (`DECISIONS.md:472-480`).
  - The two problems (contamination and operating point) are not fixed together.
  - The assigned-assembly store is an upper-bound diagnostic, not an acceptable solution (`DECISIONS.md:481-503`). The P2-R1 erratum calls it a comparator, not a mathematical upper bound (`docs/plant2/EVAL-after-P2-E5.md:137-138`).
  - Guidance given 2026-10-10 and recorded 2026-10-11: do not intervene in frozen P2-E4 on exploration results (`:551-565`).
  - The owner advises against a threshold adjustment alone as the fix for the encoding-retrieval trade-off (`DECISIONS.md:572-581`).
  - "P(PASS) is 0" means zero passes in 1,500 simulations, not impossibility (`:600-603, 708-712`).
- **2026-10-12, takeover.**
  - Authorised: up to three evidence-driven passes, with no main merge and no external spending (`DECISIONS.md:770-799`).
  - R3 is a reported replay first (`:778-782`).
  - Fixed memory inhibition is authorised as a Stage 1 stabiliser with controls (`:783-785`).
  - Forward-index interference is the next primary target, with one mechanism per contract (`:786-788`).
  - The 50/75 ms bars are kept (`:789-790`).
  - F10 is canonical and F40 transfer only (`:791-792`).
  - The frozen readout is primary (`:793`).
  - Agent-recorded closure, not an owner ruling: do not retune E6, combine R3 with it without a new contract, or begin Stage 2 (`:851-880`).
- **2026-10-22 mandate.**
  - Research continues on `plant2-research-20261022`.
  - The ledger lives in `docs/research/`.
  - Evidence durability comes before any new seed.
  - "Ten canonical neuron families" is read as F = 10, pending the owner's correction (`DECISIONS.md:883-925`).

## 9. The recovered plant

**What it was.** A frozen 2,600-cell LIF network with three regions: sense (200 E), ctx (1,600 E + 400 I) and hpc (320 E + 80 I).
- Flow was sense → ctx → hpc, with no sense → hpc projection on master. It ran at dt 1 ms with delta synapses of 1-8 ms delay, CPU-only (`docs/plant2/AUDIT-2026-10-10.md:11-15`; `SPEC.md:1391`).
- Neurons had an adaptive threshold: tau_m 20 ms, v_rest −70, v_reset −65, θ_0 −50 mV, t_ref 2 ms, tau_θ 150 ms, d_θ 1.5 mV, with Dale's law (`SPEC.md:83-95`).

Plasticity combined:
- pair STDP with fixed point 0.45 w_max (hpc A+ 0.05, A− 0.06, w_max 3.0);
- synaptic scaling of 0.9 per one-second sweep on above-target cells;
- rate-driven structural growth and pruning;
- a rate EMA with tau 2 s against region setpoints (`SPEC.md:1363-1364, 1376-1377, 1405-1409, 3377-3392`).

Stage 0 was not complete: K0.1 and K0.4 were red, and K0.3 was retired red at 0.861 against 1.2 (`docs/plant2/AUDIT-2026-10-10.md:19-20, 26`). A delay-ring slot-reuse defect is real but has not fired (`AUDIT:70`).

Source disagreements:
- SPEC 2.1 says E:I = 4:1 in every region, while the audit lists sense with no I cells (`SPEC.md:95` vs `AUDIT:12`).
- ctx→hpc in-degree is 30 in `params.py` but 40 in 8.32-8.33 (`AUDIT:65-69`).

**What it tried** (K1.1: a half cue recalls ≥ 80 % of a ≤ 20-cell assembly within 50 ms; K1.2-K1.5 were never run):

| SPEC id | approach | outcome | source |
|---|---|---|---|
| S1.0 | sense→ctx population contrast under triplet and gated STDP | ratios 1.029 and 1.020; gate closed by owner | `docs/plant2/AUDIT-2026-10-10.md:28` |
| K0.14 | intrinsic homeostasis replacing scaling | never merged; "rejected intrinsic homeostasis as previously run" (closed-gates list) | `SPEC.md:2592-2645`; `docs/recovery/project-facts-2026-10-03.md:47-48` |
| 8.2 | K1.1 on master | FAIL: half cue 1/16 at 50 ticks; the assembly is a transient response | `SPEC.md:1375-1423` |
| 8.3 | no structural elimination of hpc afferents | FAIL: half cue 0/15 | `SPEC.md:1484-1525` |
| 8.4-8.12 | stacked labelled proxies; encode-mode | best 5/16 | `SPEC.md:2563-2578` |
| 8.13 | two-timescale floor latch | T1 FAIL; "the mechanism as tuned is rejected" | `SPEC.md:2736-2758` |
| 8.14 | write-tagged prune protection | REJECTED on amplitude (survivors 0.876 → 0.624, bar 0.82) | `SPEC.md:2833-2858` |
| 8.18-8.19 | homeostat ablation | no condition eligible on all seeds | `SPEC.md:3431-3482` |
| 8.20, 8.21-8.22 | published triplet and balance rules, offline | none worth building; 8.21's gain stands but "is small" | `SPEC.md:3547-3600, 3854-3918` |
| 8.23-8.24 | oracle-weight ceilings, what-if plants | no arm completes in 50 ticks | `SPEC.md:3973-4123` |
| 8.27-8.37, 8.30 | pending-STDP and expressed tag | 8.30 PASS on its own kill test (supported "by this one contrast on one failing seed"); recall was learned disinhibition (8.35-8.37) | `SPEC.md:4743-4802`; `AUDIT:29` |
| 8.46 | excitatory binding | round test CONFIRMED on six seeds, G +2.4 to +7.0 cells; K1.1 remains FAIL | `SPEC.md:6113-6160` |
| 8.47 | official K1.1 on 8.46 | FAIL on assembly size, 40-61 cells against 20 | `SPEC.md:6162-6175, 6215-6221` |
| 8.48 | persistence and a second pattern | LOST: mean G +4.7 at 1 s, +2.5 at 10 s; Part 2 REJECTED on seed 2 | `SPEC.md:6276-6365` |
| 8.49 | why the gain halves | REJECTED / mixed: scaling causes 72 / 87 / 51 % on seeds 1-3 | `SPEC.md:6424-6492` |

**Diagnosed causes, with numbers:**
1. **The pair-STDP fixed point (0.45 w_max) sits below the homeostatic rest weight.** The sources give the rest weight variously as:
   - 0.6-0.9 (AUDIT);
   - 0.6-0.75 (STAGES);
   - 0.75 (SPEC 8.12);
   - 0.6-0.7 (SPEC 8.19);
   - 0.65-0.85, 0.58-0.62 and 0.6 of the bound (SPEC 8.23).

   One presentation therefore weakens the driven pathway by 6-14 % of w_max (`SPEC.md:2594-2598, 3466-3471, 3567-3569`; `docs/plant2/STAGES.md:21-23`; `AUDIT:35-36`).
2. **The seconds-scale homeostat erases a write within 1-3 sweeps.** Scaling and elimination back each other up. Weights fall 16-17 % during a 2 s encode, and scaling is the largest single cause of the 10 s loss at 51-87 % (`SPEC.md:1493, 2739-2758, 2833-2858, 6424-6492`).
3. **The cortical code is dense.** A 40-cell patch reaches 1,113 of 1,600 cortical E cells, and measured selectivity is 1.3-2.3 (`SPEC.md:3583-3586, 3905-3915`).
4. **The wiring caps recall even with oracle weights:** 8-11 of 16 cells at the bound (`SPEC.md:3973-4024`).
5. **Readouts sit within a few cells of a never-trained twin,** so that twin is a required control (`SPEC.md:3868-3874`).
6. **The Stage 0 operating point sets the noise floor.** Noise alone gives about 0.7 Hz, and lowering the rate target voids the plant: "a redesign of the Stage 0 operating point, not a parameter" (`SPEC.md:4078-4087, 4115-4119`).

The audit's synthesis is that the plant line cannot reach Stage 1 without changing plasticity and homeostasis together. The best line's code (8.30, 8.46) was not recovered (`docs/plant2/AUDIT-2026-10-10.md:72-76`; `DECISIONS.md:225-230`).

The legacy suite failure count disagrees across sources: AGENTS.md says 120 (2026-10-03), README-RECOVERY 111 → 77, and the audit measured 89 (Python 3.13.16, NumPy 2.5.3).

**What plant2 dropped and why:**
- **Pair STDP as the first rule.** Replaced by BTSP, which does not depend on postsynaptic timing, because of the fixed-point problem.
- **Any homeostat acting on written synapses,** because each one erases writes. P2-E2's threshold accommodation is a labelled intrinsic proxy that the owner ruled distinct, with its membership in K0.14's family recorded.
- **Dense cortical codes.** Replaced by independent sparse items.
- **Editing the plant or continuing K1.1 on it.**
- **The literal anatomy replica.**

**What it kept:**
- predeclared kill tests, never-trained or shuffled controls, labelled proxies, and one mechanism per experiment;
- the walls against an LLM or transformer as the mind at runtime, teacher current, engineered synchrony, hand-set weights and lowered bars (`docs/plant2/STAGES.md:5-7, 21-29`; `DECISIONS.md:232-243`).

Recovery is not closed, and the plant's paths are frozen by AGENTS.md invariant 4.

## 10. Code map

| path | purpose | key symbols |
|---|---|---|
| `plant2/engine.py` | LIF populations with optional accommodation, Poisson sources, CSR delayed projections, global inhibition, `Net` stepping and `quiet()` | `Poisson`, `LIF` (`set_accommodation`, `threshold`, `quiet`, `step`), `Projection` (`set_synapses`, `set_csr`, `deliver`), `GlobalInhibition`, `Net` |
| `plant2/btsp.py` | binary sparse synapse store and the BTSP update | `BinarySynapses` (`toggle`, `add`, `csr`, `per_post_count`), `btsp_update` |
| `plant2/readout.py` | replay of reconstruction-layer arms from a memory raster, with the same arithmetic as the engine | `replay` |
| `plant2/record.py` | provenance and append-only results; cache dir (`BRAINSIM_CACHE` override) | `append`, `cache_dir`, `git_state`, `runtime`, `digest` |
| `plant2/power.py` | power of predeclared acceptance rules | `bar_count`, `p_criterion`, `p_rule`, `p_paired_majority` |
| `plant2/predict.py` | single-cell first-spike predictions (used only by tests) | `p_first_spike` |
| `plant2/evidence.py` | evidence durability: exclusive verified artifacts, hash-chained per-worker journals, manifests; no delete, rename or truncate | `write_artifact`, `write_json_artifact`, `write_npz_artifact`, `verify_artifact`, `load_json_artifact`, `load_npz_artifact`, `verify_journal`, `Journal.append`, `Manifest` (`add`, `verify_all`, `require`), `EvidenceError` |
| `plant2/experiments/p2_e1_btsp.py` | P2-E1 network, learning, test sets, criteria C1-C5, kill test, capacity curve | `E1`, `CONTRACT`, `BARS`, `stream`, `test_sets`, `evaluate`, `criteria` |
| `plant2/experiments/p2_e2_accommodation.py` | P2-E2 accommodation subclass, J calibration, void controls | `E2`, `ACC_TAU_MS`, `SETTLE_MS`, `J_GRID`, `calibrate`, `verdict` |
| `plant2/experiments/p2_e3_completion.py` | P2-E3 continuation and responder feedback write, readout and score, store controls | `E3`, `run_phase`, `readout`, `score`, `shuffled_store`, `permuted_store`, `calibrate` |
| `plant2/experiments/p2_e4_online.py` | P2-E4 online driver, probe-slot schedule, habituation arm, twins, labels, guard | `Online`, `Schedule`, `score_slot`, `block_criteria`, `hab_copy`, `twin_A`, `twin_B`, `labels` |
| `plant2/experiments/p2_e5_structured.py` | P2-E5 `FamilyGen`, read-only capture, S1-S4, Parts A-G | `FamilyGen`, `CaptureMixin`, `E5`, `OnlineE5`, `ARM_SPEC`, `REUSED_FILES`, `blob_check` |
| `plant2/experiments/p2_e6.py` | P2-E6 load-gated encoding, screen, seed guards | `E6`, `probabilities`, `flip_mask`, `screen`, `seed_guard`, `FROZEN` |
| `analysis/p2r1_replay.py` | P2-R1 five-writer replay; digest and evidence helpers used by E6 and R2 | `CONTROL_STREAM`, `cue_evidence`, `raster_digest`, `json_bytes` |
| `analysis/p2r2_degree_null.py` | P2-R2 Curveball null (frozen, executed byte-identical to `c7a5350` by R2b) | `MatrixItems`, `curveball_block`, `structural_decision`, `classify`, `paired_evidence`, `run`, `summarize` |
| `analysis/p2r2b_replication.py` | P2-R2b wrapper: rebinds named `r2` attributes, verified writers, post-run evidence verification, P6 | `apply_overrides`, `write_json`, `write_npz`, `paired_evidence`, `ensure_cache_root`, `verification_record`, `summarize`, `p6`, `run`, `main` |
| `analysis/p2e4_diagnosis.py`, `p2e5_power.py`, `p2r1_baseline_audit.py` | post-run diagnosis, power reference, baseline audit (reported, not gates) | — |
| `plant2/tests/` | unit tests, including replay vs engine, evidence, hygiene and the R2b namespace | `test_p2_e3.py`, `test_evidence.py`, `test_p2_r2b.py`, `test_hygiene.py` |
| `docs/plant2/P2-E*.md`, `P2-R2-degree-null.md`, `P2-R2b-replication.md`, `EVIDENCE-DURABILITY.md`, `P2-E6-frozen.json` | predeclared contracts with appended results and addenda | Result and Addendum sections |
| `docs/plant2/RESULTS-P2-E6.md`, `RESULTS-P2-R1.md`, `RESULTS-P2-R2.md`, `RESULTS-P2-R2b.md`, `EVAL-after-P2-E*.md`, `STAGES.md` | measured results, errata, stage log | — |
| `bench/results/plant2.jsonl`, `p2e6.jsonl`, `p2r1.jsonl`, `p2r1-audit.jsonl`, `p2r2.jsonl`, `p2r2b.jsonl`, `p2r2b/` | append-only result journals; R2b per-cue evidence and per-worker journals | `record.append` |
| `docs/research/` | the research ledger (README, BACKLOG, this map) | — |

## 11. Changelog

- 2026-10-22: First version. Built from the adversarially verified extractions (architecture, recovered plant, owner rulings, P2-E1..P2-R2) with every review correction applied, plus `EVIDENCE-DURABILITY.md`, `P2-R2b-replication.md` and `RESULTS-P2-R2b.md`. Only P2-E2 index memory and P2-E3 content completion meet the demonstrated bar. P2-R2b's replication is listed as a reported explanation result.
- 2026-10-22 (critic pass, same day):
  - Corrected O1 C1 at M = 1,000 to 0.68-0.74, and seeds 16/17 at M = 500 to 0.89/0.87.
  - Replaced the P2-E5 M = 1,000 C2 statement with 0.435-0.515 on every seed.
  - Removed descriptive and exploratory numbers from the capability table.
  - Added the extraction's eight code/contract disagreements.
  - Added the missing criteria rows (P2-E1 kill test, P2-E2 gate and voids, P2-E4/E5 validity and readings), the per-experiment limitations and every supply item.
  - Added further non-demonstrated results.
  - Relabelled the takeover closure as agent-recorded.
  - Fixed several source citations.
