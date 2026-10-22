# Research roadmap: plant2

Rewritten in place at each checkpoint; the previous priority order stays in the changelog
(`README.md`, rule 4). The owner's 2026-10-22 mandate sets the procedure a checkpoint follows,
and this file is its record. The ledgers it draws on: `RESEARCH-MAP.md` (what exists and what
is demonstrated), `HYPOTHESES.md` (H-ids), `EXPERIMENTS.md` (what was run), `BACKLOG.md`
(B-ids, speculative). The owner's rulings in `DECISIONS.md` bind every entry here.

## The checkpoint procedure

A checkpoint happens after every experiment closes (result recorded, independent review
done, errata appended, ledgers updated) and before any new contract is drafted. Each one:

1. **Names the most consequential limitation** toward the Stage 1 gate and the north star,
   with the gated numbers that show it and the hypothesis ids that explain it.
2. **Reviews the evidence** for and against each candidate explanation, with labels (gated,
   exploratory, reported-only, INVALID, descriptive, offline) travelling with every number.
3. **Generates several candidate mechanisms**, at least one unconventional, each stated as a
   computational rule with its labelled proxy, its predictions against the record's own
   measures, its controls, the cheapest decisive test and what result would kill it.
4. **Compares them** on expected capability gain, novelty relative to what the record already
   tried, scientific testability, implementation cost, risk, and compliance with the rulings
   and invariants. An independent judge panel scores them before the orchestrator chooses.
5. **Selects one primary mechanism** (ruling 3 of 2026-10-12: one mechanism per contract, no
   stacking of unproven mechanisms), writes the rationale and a pre-mortem, and names the
   hypothesis ids the contract will test.
6. **Executes under contract**: contract committed before code; test-author before
   implementer; independent adversarial read before freeze; a frozen prediction list that is
   decidable from named record fields; durable verified evidence (`plant2/evidence.py`);
   independent results review; errata, never edits.
7. **Documents and updates** the ledgers, this roadmap and `DECISIONS.md`, classifying any
   failure as failed hypothesis, failed implementation, inadequate experiment or unresolved.

## Standing constraints on any contract

- The 50 ms index window and the 75 ms content window stay (ruling 4, 2026-10-12).
- Ten families (F = 10, 40 of 100 prototype lines retained) is the canonical hard condition;
  F = 40 is a transfer diagnostic only (ruling 5). The mandate's phrase "ten canonical neuron
  families" is read as this condition; flagged to the owner in `DECISIONS.md` 2026-10-22.
- Frozen deployed readout is primary; best-over-grid is an explicitly optimistic diagnostic
  (ruling 6). No parameter rescue after a failed gate.
- Forward-index interference is the next primary mechanism target; local error and
  presynaptic-load signals are the approved families to investigate; index is scored
  independently from content (ruling 3).
- R_3 (burst-gated writer) is a reported replay first, not a gated mechanism (ruling 1).
  Fixed activity-proportional memory inhibition is authorised only as a stabiliser with the
  listed controls and gets no capability credit (ruling 2).
- Self-generated keys are deferred by the owner (B-006 `blocked`); familiarity-gated
  allocation is deferred (ruling 4 of 2026-10-10). No Stage 2 work. No LLM in the runtime;
  no teacher current. Frozen drivers and the recovered plant are not edited; new drivers
  import them.
- Task-level reasoning and retrieval stay inside the spiking network; nothing outside it
  decides what is recalled.
- Evidence durability: new drivers write through `plant2/evidence.py`; no git operation on
  this machine while a worker runs; commits after workers exit with verification records.
- Seeds are assigned once, in the `DECISIONS.md` entry that selects a contract, from the
  registry below; a seed is never shared between contracts.

## Seed registry (2026-10-22)

Spent or reserved before this checkpoint (`RESEARCH-MAP.md` section 8): 0-25, 42-45, 90,
97, 99, 101-106; 102 and 111-115 reserved for P2-E6 and never run.

| contract | development | held-out | gated (five) |
|---|---|---|---|
| P2-E7 error-gated forward eligibility | 121 | 122 | 131-135 |
| branch-segregated dendritic storage (only if the owner admits it) | 107 | 108 | 141-145 |
| reported replays that need one fresh independent raster | 109 | — | — |

## Checkpoint 2026-10-22 (the first under the mandate)

### 1. The most consequential limitation

**Forward-index cross-talk on correlated items at the canonical load.** On F10/s60 items at
M = 1,000, index specificity C2 is 0.435-0.515 and C4 spurious 0.35-0.49 on every gated seed,
and content is below the bar at both loads (P2-E5, gated, seeds 21-25;
`docs/plant2/P2-E5-structured-items.md:897-911`). 16.5-18.9 spurious cells per half cue,
98 % of them siblings' plateau cells (reported-only; H-035;
`review/plant2/P2-E5/results-northstar_constructive.md:38`). Every intervention since leaves
it standing:

| intervention | C2 at M = 1,000 (F10) | inherited content | label | source |
|---|---|---|---|---|
| none (P2-E5 system) | 0.435-0.515 | fails every seed, both loads | gated, seeds 21-25 | `P2-E5-structured-items.md:897-911` |
| presynaptic-load-gated encoding (P2-E6) | .500 → .895 | .065 | exploratory, seed 101, FEASIBILITY FAIL | `RESULTS-P2-E6.md:12-43` |
| exact-degree input null (P2-R2 seed 103; P2-R2b seeds 105, 106) | .755; .745; .720 | ≤ .075 | reported-only, explanation test | `RESULTS-P2-R2.md:84-88`; `RESULTS-P2-R2b.md:26-40` |

Why this limitation and not another:

- It is the owner's named next primary target (ruling 3, 2026-10-12).
- It blocks the Stage 1 clause the owner added on 2026-10-10 (item-specific recall on
  correlated inputs), which no experiment has passed.
- Content at M = 1,000 cannot be clean while the index is not (H-046 `supported`): the index
  is upstream of everything the content path can do.
- The explanation work it needed is done. P2-R2b replicated MATERIAL STRUCTURE SENSITIVITY
  on two fresh seeds with verified evidence (H-044 `supported` on three valid seeds), and the
  rider that the low-load gain costs oldest recall did not recur (H-045 `refuted`). The
  capability review's condition for choosing a co-occurrence-sensitive mechanism is met; by
  P2-R2b erratum 5 that informs rather than authorises, which is what this checkpoint is for.

All five panel lenses, reading the ledgers independently, named the same limitation. Three
of them located it more precisely in the same place: a memory cell is one point integrator
that sums a cue's overlap with every item it holds (about five items per cell at f_q 0.005
and M = 1,000), so a half cue's hot lines add up across a sibling cell's several stored
items. Two unrecorded offline computations on the persisted P2-R2b ORIGINAL artifacts
support that reading and are exploratory until reproduced and recorded: with a hard count on
cue synapses, own cells (18.9 per cue at ≥ 20) and non-own cells separate almost perfectly,
and the failure sits in a tail of 87-92 non-own cells per cue with ≥ 12 cue synapses;
spurious cells fire late (median first spike 38-40 ms against 23 ms for own cells). The
constructive judge reproduced the branch count and showed its threshold sensitivity (0.76
non-own cells at ≥ 12 synapses, 10.1 at ≥ 10, 32.29 at ≥ 9), so the static screen's validity
depends on the branch firing point, which no record measures.

The alternatives considered for "most consequential" and why they come later:

- **No online operating point** (P2-E4: O1 C1 0.68-0.74 at M = 1,000, gated; habituation
  50-64 % against a 10 % bar). Real and blocking for the online clause, but the record says
  the online failure is mostly slowed retrieval and threshold coupling (H-027, H-028), and a
  mechanism that reduces interference lowers the drive margin the online conflict rides on.
  Second priority.
- **Experimenter supply** (the write oracle, the random key, episode boundaries, verbatim
  values). The deepest limitation toward the north star, but B-006 is owner-deferred, and
  every reviewer agrees the index must be specific before a self-selected key means anything.
  The selected mechanism removes a sliver of it (the selection half of eligibility).
- **Capacity and forgetting** (edge between 0.25 and 0.375 items per cell; the feedback store
  saturates). A Stage 1 clause too, but it is the same interference seen at higher load on
  independent items; whatever fixes cross-talk at F10 is the first thing to test there.

### 2. Evidence review

What the record says about where the cross-talk comes from (`HYPOTHESES.md` section 4):

- Hot prototype lines accumulate strong synapses into every family member's assembly, so a
  sibling's cells are recruited by shared lines alone (H-035 `mixed`; P2-E5 Part B).
- Holding each line's usage exact while scrambling co-occurrence removes about 60 % of the C2
  bar deficit on three valid seeds and leaves C2 at .720-.755: the family grouping is not
  necessary for the failure, and the design cannot apportion the rest between line load and
  co-occurrence (H-043, H-044; P2-R2b erratum 1).
- Bounding each line's flip budget by its presynaptic history (P2-E6) reaches C2 .895 on one
  development seed, short of the .90 bar, and the exact flip-count control does not reproduce
  the gain (H-040, H-041): line identity matters beyond the budget.
- Index gains at M = 1,000 do not carry content (H-046); at M = 500 they do (inherited content
  .115 → .960 on the null). A mechanism scored on the index alone can still leave content
  failing at 1,000, so the contract must score both, separately (ruling 3).
- Specificity gains on the input side are not global silencing: own responders unchanged,
  spurious responders fewer (descriptive, P2-R2b P6 on seed 105 and, below the bar, 106).
- The main evidence against an error-gated write is that its teacher, the responder-written
  feedback store, is contaminated on F10 (H-055, H-060 evidence against; P2-E5 Part D
  WORSENS). Two judge computations put numbers on it, both offline, judge-computed and
  unrecorded: the F10 feedback store density at M = 1,000 is 0.313-0.318 on seeds 105/106,
  near the readout's count threshold of about 30 % of active memory cells; and on the P2-E6
  seed-101 baseline store, full learned F10 cues regenerate a median 743.5 lines at M = 500
  and 3,643 at M = 1,000, against 133 for independent items. Those are test-time, full-cue,
  settled numbers; encoding-time prediction runs at a higher offset with the item's own
  plateau cells not yet written (H-029), so the record does not say how much of this
  saturation reaches the gate. The contract measures it before any test phase.

What is not known: whether a retrieval-side nonlinearity (B-001, B-013), an encoding-side
error signal (B-002), a population brake (B-003) or a learned pre-storage separation (B-004
learned form) removes the residual; no experiment has run any of them. No ablation isolates
the cue-line term of H-003 at M = 1,000. No record yet measures the pre-screen the skeptic
judge asked for (rebuilding the feedback store episode by episode and scoring the predicted
set's prototype fraction). The P2-R2b raw learned checkpoints under the cache do persist the
per-episode `items`, `A`, `E` and `R` sets (checked 2026-10-22), so that pre-screen is
feasible without a seed; it is contracted as screen A of
`docs/plant2/OFFLINE-SCREENS-20261022.md`, labelled proxy and advisory, and P2-E7's
structural kill measures the exact quantity on the development seed.

### 3. Candidate mechanisms

A judge panel (workflow wf_848f4c6e-5b0, 2026-10-22: five Opus proposers with the lenses
circuit biology, theory, engineering, supply reduction and contrarian; three Opus judges,
skeptic, constructive and owner-intent; full output kept under
`~/.cache/brain-sim/plant2-research-20261022/ledger/mechanism-panel-wf_848f4c6e-5b0.json`)
produced ten proposals that reduce to seven mechanisms. Each is stated as its proposer stated
it; the backlog carries the sketches.

1. **Error-gated (prediction-gated) forward eligibility with a conserved flip budget**
   (engineering and supply-reduction primaries, the same mechanism; B-002, H-060, H-055).
   During the 200 ms encoding a side reconstruction population is stepped from the current
   feedback store through the frozen readout arithmetic (J_fb 2.80, g 0.3, delay 1 and 2),
   with no path back to the memory layer. The predicted set G(x) is the rec lines that spike
   in ticks 0-74. The veto V(x) = E(x) ∩ G(x); only E'(x) = E(x) \ V(x) is toggled, with
   p = min(1, 0.5·|E|/|E'|) so the expected flips per plateau cell are unchanged, and coins
   drawn in the frozen E-major, A-minor order so the store is bit-identical to E3 whenever V
   is empty. The feedback write and every test protocol are unchanged. No new parameter.
   Labelled proxy: mismatch- or novelty-gated plasticity (comparator view; a circuit-level
   proxy, not CA1 physiology).
2. **Branch-segregated (episode-clustered) dendritic storage with an OR soma** (circuit,
   theory and contrarian primaries; new, B-013; related to but distinct from B-001). Each
   memory cell gets K = 8 branch units, each an LIF with the frozen memory constants and its
   own accommodation; each plateau writes onto one fresh branch chosen by a cell-local
   round-robin counter; a branch spike fires the soma through a fixed coupling of 25 mV.
   Nothing in the toggle changes. Labelled proxy: dendritic subunits with branch-restricted
   plasticity. A storage-capacity mechanism, not pattern separation.
3. **Non-plateau responder depression** (theory secondary; B-014). Cells that respond to an
   encoding without a plateau have their active cue synapses depressed, a false-positive
   correction on the forward store. Its author predicts it misses the bar.
4. **E%-max feedback inhibition in the memory layer** (circuit secondary; B-003 family).
   A perisomatic basket-cell proxy; H-008 records that global feedback inhibition or k-WTA
   cannot satisfy C3 (exploratory), which the proposal misread as applying to k-WTA only.
5. **Deployed burst-gated R_3 feedback writer on fresh seeds** (engineering secondary;
   B-011, H-050). A content mechanism; ruling 1 keeps it a reported replay first.
6. **Episode-clustered reconstruction store** (contrarian secondary; B-015). Each continuation
   write puts R(x)'s synapses onto a fresh dendritic branch of every eligible rec line; a line
   regenerates when one stored episode's writers dominate. Reported replay first; the only
   proposal aimed at H-046.
7. **Mismatch-gated plateau initiation** (supply secondary; B-006 family). The network decides
   whether a presentation is written; needs the deferred familiarity ruling.

### 4. Comparison

Judge scores, each 0-5 on six criteria (capability gain, novelty, testability,
implementation cost with 5 cheapest, risk with 5 safest, compliance), summed over the three
judges (max 90). Compliance was scored strictly by the owner-intent judge: anything needing a
deferred ruling scores at most 2.

| mechanism | skeptic / constructive / owner-intent | sum | capability | novelty | testability | cost | risk | compliance |
|---|---|---|---|---|---|---|---|---|
| 1 error-gated eligibility (supply version) | 23 / 23 / 24 | 70 | 11 | 9 | 15 | 12 | 8 | 15 |
| 1 error-gated eligibility (engineering version) | 22 / 23 / 24 | 69 | 11 | 9 | 14 | 12 | 8 | 15 |
| 6 episode-clustered reconstruction store | 19 / 22 / 20 | 61 | 6 | 13 | 13 | 13 | 10 | 6 |
| 2 branch storage (circuit version) | 18 / 22 / 20 | 60 | 10 | 11 | 14 | 9 | 9 | 7 |
| 2 branch storage (theory version) | 19 / 21 / 19 | 59 | 10 | 9 | 15 | 9 | 9 | 7 |
| 3 responder depression | 19 / 19 / 18 | 56 | 6 | 11 | 12 | 12 | 6 | 9 |
| 5 deployed R_3 writer | 19 / 19 / 18 | 56 | 6 | 4 | 13 | 15 | 12 | 6 |
| 2 branch storage (contrarian version) | 17 / 20 / 18 | 55 | 10 | 11 | 14 | 8 | 6 | 6 |
| 7 mismatch-gated plateau initiation | 18 / 17 / 19 | 54 | 9 | 12 | 12 | 11 | 7 | 3 |
| 4 E%-max memory inhibition | 18 / 17 / 17 | 52 | 6 | 8 | 12 | 12 | 6 | 8 |

All three judges ranked the error-gated mechanism first and asked for the engineering and
supply versions to be merged into one contract. Factual errors the judges found and that the
contract corrects: the engineering version's "about 8 coactive responders per rec line"
ignores the frozen inhibition (with 40 active memory cells a line needs about 19 writers, so
the late-onset risk is larger than stated); the two versions claimed colliding seeds; the
E%-max proposal misread H-008; the branch proposals applied H-065's point-cell firing point
to branches and cited the independent-item store density (0.133) for an F10 prediction.

### 5. Selection, rationale, pre-mortem

**Selected: P2-E7, error-gated forward eligibility with a conserved flip budget**, as one
merged contract. It tests H-060 (primary), H-055 (the owner's two required questions: does
the feedback supply useful error information; do corrections preserve unrelated memories),
and bears on H-035, H-041, H-043, H-044 and H-046.

Rationale, in the panel's words and the record's:

- It is the only candidate squarely inside ruling 3 (a local error signal on the forward
  index, one mechanism) and the 2026-10-10 approved error-correcting family, so it needs no
  new ruling. It is the step `EVAL-after-P2-E5` recommended on 2026-10-11 and has never run.
- It adds no free parameter: the 75 ms window, J_fb 2.80, g 0.3 and the 0.5 flip budget are
  inherited and frozen. Nothing is calibrated, so no seed is spent on calibration.
- Its integrity is mechanical: a gate-off arm must reproduce E3's forward store byte for
  byte, and the coin stream stays aligned across arms.
- Its kill tests resolve in well under an hour, and the structural kill fires before any
  test phase (about five minutes into learning).
- It is the only primary that removes any experimenter supply: the network, not the 3-spike
  rule alone, decides which presented lines are written.
- Its controls can fail if the idea is false. The count-matched random drop (stream 33)
  answers "useful error information". The history-weighted drop (stream 34, E6's pseudocount
  weights, used only as a control) separates a co-occurrence-sensitive prediction from a
  hot-line filter in disguise, which is exactly the question P2-R2b erratum 1 left open and
  the capability review's warning against mechanisms that "merely suppress shared features".

Grafts adopted from the other proposals: the gate-off integrity arm, the structural kill
before any test phase, the reported no-conservation arm, the label-oracle comparator
(diagnostic only), the saturation kill with family labels read at scoring time only, the
H-042 matched-state diagnostics per arm, a matched-silence comparator against H-067's
sensitivity-specificity slide, persisted per-episode continuation counts and R, A, E sets so
later R_k and reconstruction-store replays need no new seed, the own-versus-spurious
first-spike latency split (B-008's cheapest test) on every arm, and a log of every episode
with an empty E' as a familiarity event with no repeat arm without an owner ruling.

Pre-mortem (it is three weeks later and this failed):

1. **The teacher was saturated.** By mid-learning the contaminated feedback store regenerates
   the item's unique lines as well as its prototype lines; E' collapses, p reaches 1, late
   items are under-written, and C1 or oldest recall falls more than 0.03. Detected by the
   structural kill (veto precision below 70 % prototype) and kill (d).
2. **The veto engaged too late.** At the encoding offset few siblings respond, V(x) stays
   small until 30-40 members per family are stored, hot-line fan-out freezes near baseline,
   and C2 lands at 0.70-0.88, an informative fail like E6's .895. Detected by the structural
   kill (mean |V| below 5 lines over the last 500 episodes) and recorded as such, never
   retuned.
3. **A hot-line filter in disguise.** The candidate's C2 lands within 0.05 of the
   history-weighted drop, so the gain is E6's load marginal under another name. Kill (e); the
   co-occurrence claim dies even if C2 rises.
4. **The budget, not the error, carried the gain.** Detected by the reported no-conservation
   arm.

Expected outcome, honestly: the judges put capability gain at 3-4 of 5 because the predicted
C2 of 0.82-0.97 straddles the .90 bar and content at F10/1,000 stays below its bar whatever
the index does (H-046). A pass closes the index half of the correlated-items clause only.

### 6. Deferred, and why

- **Branch-segregated dendritic storage (B-013)** is the strongest orthogonal attack on the
  same limitation and scored second. It waits on an owner ruling: does a K-branch memory cell
  count as the same 4,000-cell Stage 1 system, or as memory-only scaling under the capacity
  rule (`DECISIONS.md:319-325`)? If admitted, it runs on its own seed (107) under its own
  contract regardless of P2-E7's outcome, and is never combined with P2-E7 without a third
  contract. Its offline static screen is reproduced and recorded first, with the stream-3
  coin-parity integrity gate and an empirical branch firing curve.
- **Episode-clustered reconstruction store (B-015)** and **deployed R_3 (B-011)** are content
  mechanisms; ruling 3 puts the index first and H-046 says content at 1,000 is index-limited.
  Both ride P2-E7's baseline-arm raster as reported-only passive diagnostics (the raster is
  unchanged under the baseline arm, so nothing is stacked); neither is scored as an outcome.
- **Memory-layer inhibition (B-003, E%-max)** returns only as the stabiliser inside a
  recurrence contract (H-063), after its step-0 latency analysis; H-008's C3 warning stands.
- **Responder depression (B-014)** is the in-scope local-error fallback if the owner does not
  admit branch storage and P2-E7 dies; its author predicts it misses the bar.
- **Mismatch-gated plateau initiation (B-006 family)** stays blocked on the familiarity
  deferral.

Questions bundled for the owner (none blocks P2-E7): (a) admissibility of dendritic-subunit
storage under ruling 3 and the capacity rule; (b) whether R_3 may move from replay to a gated
contract; (c) whether memory inhibition may be used standalone; (d) the familiarity-gating
deferral; (e) confirmation of the F = 10 reading of "ten canonical neuron families".

### 7. Outcome of P2-E7 on development seed 121 (2026-10-22, 20:09-20:19 UTC)

Informative FEASIBILITY FAIL (`docs/plant2/RESULTS-P2-E7.md`): F10/1,000 candidate C2 .745
(bar .90), C1 .895, C4_spurious .720, joint .645; every comparative margin held (+0.265 C2
over the count-matched random drop, +0.110 over the history-weighted drop, non-regression on
independent and mixed inputs); no structural kill fired; integrity true. The veto engaged
late (a family's first four to thirteen members written in full; mean |V| 13.0 over episodes
1-500) and the label oracle, vetoing the true prototype lines from the first episode, reached
C2 .970 with C1 .920; the oracle differs from the candidate in onset, coverage and precision
at once, and the design does not separate them. The budget is load-bearing on this seed
(without it C2 .840 but C1 .680). The responder-written teacher gave a higher C2 than the
clean plateau-set teacher (.745 against .645) with more vetoes at lower precision. Inherited
content stayed at or below .055 on every non-oracle arm. Classification: failed hypothesis in
its stated form; the comparative hypotheses supported on one development seed (exploratory).
Not retuned; held-out seed 122 does not open. Pre-mortem item 2 ("the veto engaged too late
... an informative fail like E6's .895") is what happened, at .745. Independent results
review: every number reproduces; twelve wording errata (`docs/plant2/RESULTS-P2-E7.md`).
The next checkpoint (section 8, pending) starts from the oracle gap.

## Checkpoint 2026-10-22 (second; after P2-E7 on development seed 121)

### 1. The most consequential limitation

**Forward-index cross-talk on correlated items at the canonical load, now located.** P2-E7's
prediction-gated eligibility moved F10/1,000 C2 from .500 to .745 on development seed 121
and left it short of the .90 bar (`docs/plant2/RESULTS-P2-E7.md`; exploratory, one seed).
Offline screen E (`docs/plant2/OFFLINE-SCREENS-20261022b.md`, offline, descriptive) locates
the residual: of the candidate's 8.62 spurious responders per half cue, 6.19 are cells whose
same-family plateau items were all written after the veto had engaged for that family, 1.97
hold a member written in full before engagement (chance level 0.08), and 0.47 hold other
families' items only. The label oracle, which vetoes the true 40 prototype lines from the
first episode, leaves 1.68 and reaches C2 .970 with C1 .920. The legacy of the fully written
early members is minor; the leak is on later episodes.

Why the leak persists under the frozen rule (arithmetic from the contract; a hypothesis
until measured): the prediction covers 0.835 of the eligible prototype lines over episodes
501-1,000, so about one prototype line in six escapes the veto on each late episode, and the
conserved budget writes each unvetoed line with p = min(1, 0.5·|E|/|E'|) ≈ 0.84 at |V| ≈ 40
(p = 1 on the 144 capped episodes) against 0.5 under the baseline rule. In aggregate this is
about 5.5 expected missed-prototype flips per plateau cell on a late episode against about
19.7 prototype flips under the baseline (the skeptic judge's correction of the per-line
statement): the rule removes most of the prototype drive and the residual is what is left,
amplified. During the ramp (blocks 1-4, mean |V| 1.0-17.8) the leak is much larger because
coverage is low. The no_conservation arm supports the reading from the other side: p = 0.5
on E' gives 5.47 spurious responders and C2 .840 but C1 .680 and own50 15.8.

The other limitations keep their order from checkpoint 1. One moves up: inherited content
at F10/1,000 stayed at or below .055 on every non-oracle arm and reached only .310 on the
oracle, and every recorded content failure on seed 121 is an intrusion failure (D1 ≥ .955
everywhere; the oracle's intrusions median 18.5 inherited, 9.0 assigned-A, exploratory): the
content wall behind the index is cross-episode writer summation on the reconstruction lines,
which no index mechanism reaches (H-046, H-036 generalised).

### 2. Evidence review

- Ruling 4's two tests came out favourable on one development seed: the candidate beat the
  count-matched random drop by +0.265 C2 and the history-weighted drop by +0.110; the veto
  never fired on independent inputs; the mixed store's independent subset moved by at most
  two index cues and gained 14 content cues (`RESULTS-P2-E7.md`, errata 1 and 6).
- The conserved budget is load-bearing and double-edged: it preserves recall (own50 within
  0.05 of the baseline) and it writes every escaped prototype line at p ≈ 0.84.
- The responder-written teacher gave more vetoes at lower precision than the clean
  plateau-set teacher and a higher C2 (.745 against .645); no causal attribution (erratum 5).
- Onset: a family's first four to thirteen members are written in full; per-block mean |V|
  1.0, 4.3, 16.8, 17.8, 24.8, 31.2, 34.6, 37.7, 47.5, 50.9. An error gate that learns from
  its own memory response has a self-limiting fixed point: coverage scales with the
  cross-talk it removes (own-gate prototype coverage over 501-1,000 by arm: gate_off .956,
  random_drop .946, history_drop .909, candidate .835, against spurious50 20.96, 19.15,
  12.11, 8.63; cross-trajectory, not an intervention).
- The persisted seed-121 state holds, per arm and episode, the 75-tick encoding raster, the
  gate log (G, V, p, cap, prototype fractions), R, E, A and the continuation counts, so the
  leak, the subthreshold drive of the reconstruction units and the content store's
  per-episode structure can all be measured without a seed.
- The branch static screen (B) and the latency split (C) stand; the riders replicate P2-R1's
  pattern on a fresh seed (R_3 content .925 at 500, .140 at 1,000, reported only).
- Not known: what the late cells carry, line by line; whether graded subthreshold drive
  separates the missed prototype lines from unique lines; whether reconstruction-side
  summation or late memory recruitment limits content at 1,000.

### 3. Candidate mechanisms

A judge panel (workflow wf_d9fc89e1-dac, 2026-10-22: three Opus proposers with the lenses
theory, engineering and contrarian; two Opus judges, skeptic and owner-intent; full output
under `~/.cache/brain-sim/plant2-research-20261022/ledger/checkpoint2-panel-wf_d9fc89e1-dac.json`)
produced six proposals:

1. **Episode-clustered reconstruction store with bounded line-local branches (B-015,
   bounded form), as a zero-seed reported replay on the persisted seed-121 evidence (working
   name P2-R3)** (contrarian primary). Each reconstruction line holds K = 32 writer sets
   filled round-robin by episode; each is an LIF compartment under the frozen readout
   arithmetic and the line spikes when any branch spikes; K = 1 is the frozen readout
   (parity gate). Replayed on the gate_off (deployable), label_oracle (clean-index
   diagnostic), candidate (stacking diagnostic), independent and mixed rasters, with a
   per-synapse scramble control, the assigned-A store under the same rule, and dose arms.
   Aimed at the content wall (H-046, H-036); no seed; decision 4 of checkpoint 1 already
   allows the replay.
2. **P2-E8: graded prediction-error weighting of the conserved flip budget** (engineering
   primary). The same lockstep reconstruction readout, read for its peak subthreshold
   depolarisation d_j: w_j = 0 for predicted lines (the binary veto nested), otherwise
   w_j = 1 − clip(d_j / 20 mV, 0, 1); p_j = min(1, λ·w_j) with λ the exact water-filling
   solution of Σp = 0.5|E|. No new constant (20 mV is the rec threshold gap). Decided first
   by a zero-seed screen (AUC of d_j; counterfactual flip counts) that can only kill.
3. **Leak-neutral (surplus-only) conservation** (engineering secondary): p = 0.5 floor on E'
   and only the vetoed surplus steered by residual error; its author predicts C2 below the
   bar; a reported arm inside 2, deciding nothing.
4. **Branch-segregated dendritic storage with an OR soma (B-013)**, in two forms (theory
   primary with a calibrated count model; contrarian secondary with an out-of-sample
   firing-curve validation): the summation-across-held-items attack; needs owner question
   (a); its zero-seed screen F comes first.
5. **Error-gated eligibility taught by an unselective twin store** (theory secondary): a
   teacher independent of the student's cross-talk, with an earliest-spike truncation. The
   skeptic judge computed from the persisted gate_off gate log that the baseline trajectory's
   own coverage over episodes 101-500 is 0.513, below the proposal's own kill of 0.595, and
   that the twin teacher starts outside P2-E7's kill envelope (precision .685, non-prototype
   .291). To be recorded as a one-line offline result, then closed.

Rescue question, as the judges put it: none of the six retunes a frozen P2-E7 constant; the
graded rule (2) "comes closest" because it functionally softens the ≥ 1-spike criterion
into a continuous one; both judges admit it as a different rule with a stated reason only
with the binary rule as a same-seed comparator, a kill-only offline screen, a fresh seed and
explicit acceptance. Surplus-only is the closest to a rescue and rides as a reported arm.

### 4. Comparison

Judge scores (0-5 on six criteria, total out of 30 per judge; skeptic / owner-intent / sum):

| mechanism | skeptic | owner-intent | sum |
|---|---|---|---|
| 1 B-015 replay (P2-R3) | 25 | 24 | 49 |
| 2 P2-E8 graded error weighting | 20 | 22 | 42 |
| 3 surplus-only conservation | 18 | 20 | 38 |
| 4 B-013 branch storage, contrarian form | 16 | 19 | 35 |
| 4 B-013 branch storage, theory form | 16 | 18 | 34 |
| 5 twin-store teacher | 14 | 18 | 32 |

Both judges ranked the B-015 replay first on testability and cost (exact on three
substrates, parity gate, zero seed, already permitted) and the graded rule second as the
primary seed-spending candidate; both recommended the same sequence: zero-seed screens
first, in parallel, each under an offline-screen contract; then the P2-E8 contract on a
fresh seed only if its screen survives; question (a) to the owner only with a surviving
B-013 screen; a gated content contract only after the owner accepts the reordering against
ruling 3. Factual errors the judges found and that this checkpoint corrects: screen E was
recorded (eb724c3) by the time the proposals were written; the own-gate coverages are .956 /
.946 / .909 / .835; "every missed prototype line is written with higher probability" is
true per line, not in aggregate; the theory primary's count model is unrecorded; the
contrarian primary's D1 question is already answered by the recorded D1 fields.

### 5. Selection, rationale, pre-mortem

**Selected now (zero seed, in parallel, each under its own contract):**

- **Screens F and E′** (`docs/plant2/OFFLINE-SCREENS-20261022c.md`): the kill-only screen
  for the graded rule on the persisted candidate and gate_off states (AUC of the
  subthreshold drive separating missed prototype lines from unpredicted unique lines;
  counterfactual expected prototype flips per plateau cell under binary, graded and
  surplus-only; the ramp; the twin-store coverage line) and the re-binning of screen E's
  late class by write-time coverage.
- **P2-R3** (`docs/plant2/P2-R3-branch-reconstruction-replay.md`): the B-015 bounded
  reconstruction store as an exact reported replay with its parity gate, scramble, assigned-A
  store and dose arms, preceded by the intrusion-span decomposition.
- **B-013 screen F** stays on the list but is not contracted at this checkpoint: it needs
  the single-unit firing curve, which is a (small) simulation, and the owner's question (a)
  is still open; it is contracted if P2-E8's screen F kills.

**Selected conditionally (the next seed-spending contract):** **P2-E8** on development seed
123 (held-out 124, gated 151-155, registered in the `DECISIONS.md` entry), only if screen F
survives its kills (AUC ≥ 0.70 over episodes 501-1,000; counterfactual graded/binary
prototype-flip ratio ≤ 0.6 over 501-1,000; and not both a ramp ratio > 0.85 and a late class
concentrated in the low-coverage bins of E′). It runs the P2-E7 binary rule as a same-seed
comparator, the graded_shuffled and history_rank controls that hold the exact multiset of
p, gate_off integrity, the label oracle, independent and mixed non-regression, and
surplus-only as a reported arm. It is submitted to the owner as question (f): a graded
prediction-error weight with the binary veto nested as its w = 0 case and no new constant is
treated here as a different rule with a reason, not a rescue of P2-E7; the owner can veto
before seed 123 is spent.

Rationale: the residual is located (late-episode leak under an imprecise, self-limited
teacher), the graded signal is the quantity the same reconstruction unit already computes,
the screen can kill it for nothing, and it stays inside ruling 3's local-error family with
no deferred ruling. The B-015 replay attacks the other wall at zero cost with an exact
computation and decides whether content at 1,000 is reconstruction-side summation.

Pre-mortem (it is three weeks later and this failed):

1. **No separation.** Late in learning, about 40 memory spikes in the 75-tick window deliver
   about 34 mV of inhibition and every unspiked line's peak sits near rest; AUC ≈ 0.55;
   screen F kills offline (good: no seed spent).
2. **Drive is load.** Subthreshold drive tracks a line's writer count, so history_rank
   matches graded within 0.05 on seed 123: E6's hot-line marginal again; the co-occurrence
   claim dies even if C2 rises.
3. **Independent perturbation.** The graded rule changes veto-free episodes; independent C1
   or C3 slips past 0.03.
4. **The floor.** The early-member and other-family classes (about 2.4 per cue) leave C2 at
   .82-.87: a second informative fail, read as a second attempt at P2-E7's screen.
5. **P2-R3 splits.** The oracle raster rises while gate_off at F10/500 stays near .30, or the
   scramble lands within 0.05 of the branch store (plain dilution).

### 6. Deferred, and why

- **B-013** waits on its screen F (firing-curve validation out of sample against all seven
  recorded F10/1,000 arms) and on owner question (a); never combined with P2-E8 without a
  third contract.
- **Twin-store teacher** closes when its one-line offline record (gate_off coverage over
  101-500 against its own kill) is appended by screen F.
- **A gated content contract from P2-R3** needs the owner to accept the reordering against
  ruling 3 and to extend question (a) to reconstruction lines (ruling 6).
- **B-014 responder depression** stays the in-scope fallback if P2-E8 dies offline and
  B-013 is not admitted.

### 7. Outcome of screens F and E′ (2026-10-22, 23:13-23:15 UTC)

Screen F survived every kill (candidate AUC 0.858 over episodes 501-1,000; graded/binary
counterfactual prototype-flip ratio 0.441 over 501-1,000 and 0.750 over 1-300), so the
decision rule authorises drafting P2-E8. Screen E′ changes the expected size of its gain:
89 % of the late-class residual cells hold a same-family item written while the prediction
covered less than a quarter of its prototype lines, so about 90 % of the residual (with the
early class) was written during each family's onset ramp, where the graded rule removes only
25 % of the expected missed-prototype flips; the steady-state leak, where it removes 56 %,
holds about 4 % of the residual. B-017 closes (gate_off coverage 0.513 over episodes
101-500 against its own 0.595). Consequence for P2-E8's contract: its predictions are set
from this screen (a modest gain over the binary rule is the honest point prediction, with
the ramp floor as the most likely failure), the binary rule stays the same-seed comparator,
and the mixed-stream and independent arms stay as ruling-4 tests. If P2-E8 lands as a second
informative fail, the ramp floor is established as the error-gate family's structural limit
on this substrate, which is the information that decides between B-013 (owner question (a))
and the content wall.

### 8. Outcome of P2-R3 (2026-10-22, 23:24-23:46 UTC)

Step 0 did not kill: on the oracle raster at 1,000, 135 of 138 failing content cues fail by
intrusions and 97.8 % of the failing cues by intrusions whose active writers span several
episodes (gate_off: 198 of 199, 100 %). The replay (`docs/plant2/RESULTS-P2-R3.md`,
reported-only, exact): K = 32 episode-clustered branches lift content joint on the oracle
raster at 1,000 from .310 to .985 with zero median intrusions, on the deployable gate_off at
500 from .145 to .895, at 1,000 from .005 to .345 (index-limited; unbounded .495), on the
candidate raster from .005 to .710, and on the mixed store from .180 to .830 with its
independent subset at 95 of 95 cues; the per-synapse scramble regenerates nothing (.000
everywhere), so episode clustering is the ingredient; D1 costs at most 0.045. Five
predictions failed by exceeding their upper bounds; parity, scramble, independent and dose
predictions held. **Reading (as corrected by the independent review, errata 7 and 9):** the
content wall at F10/1,000 is reconstruction-side summation, removable by a bounded branch
store; what remains on the deployable substrate at 1,000 (.345) is write-time contamination
of the responder-written writer sets, since the assigned-A writers reach .925 on the same
raster under K = 32; "content tracks the index" (.345 / .710 / .985 for C2 .500 / .745 /
.970) is a three-point observation on one seed, two of the points diagnostics, and the
candidate substrate is a stacking diagnostic, not an exact replay. H-085 enters the ledger as
`mixed` (replay-only). Consequence: the two next seed-spending contracts both wait on the owner:
P2-E8 on question (f) (acceptance file), and a fresh-seed content contract from P2-R3's rule
on question (g) (ordering against ruling 3) with question (a) extended to reconstruction
lines (ruling 6). Independent results review of P2-R3 pending.

## Priority order (current)

1. Screens F and E′: done (section 7); P2-E8 contract frozen, awaiting the owner's
   acceptance of question (f) before seed 123.
1b. P2-R3: done (section 8); a fresh-seed content contract from its rule is drafted next and
   waits on questions (g) and (a).
2. P2-R3 branch-reconstruction replay (zero seed; decides whether content at 1,000 is
   reconstruction-side summation).
3. P2-E8 graded error weighting on seed 123, if screen F survives and the owner does not
   veto question (f).
4. B-013 screen F and owner question (a), if P2-E8 dies offline.
5. Content contract (P2-R3's rule on fresh seeds) and the online operating point, after an
   index mechanism passes at both loads and the owner rules on the reordering.
2. Done 2026-10-22 (`docs/plant2/OFFLINE-SCREENS-20261022.md`, Results): the gate pre-screen
   warns that on the baseline trajectory the teacher saturates late (non-prototype predicted
   fraction crosses 0.25 in block 8 of 10; precision falls below 0.70 in block 9), so P2-E7's
   structural check is the live question; the branch static screen reproduces with its
   integrity gate passed (B-013 stays blocked on the owner's answer); the latency split
   closes B-008 as a standalone mechanism; the saturation counts reproduce the judges'
   numbers.
3. Branch-segregated dendritic storage (B-013), if the owner admits it, on seed 107.
4. Content: one mechanism per contract, after an index mechanism passes at both loads.
5. The online operating point (P2-E4's failures), after the index is specific on F10.

## Changelog

- 2026-10-22: first version, written at the checkpoint after P2-R2b. Priority order as
  above; no previous order.
- 2026-10-22, later the same day: corrected the evidence-review statement that per-episode
  responder sets are not persisted (they are, in the P2-R2b raw learned checkpoints); the
  four zero-seed screens are contracted in `docs/plant2/OFFLINE-SCREENS-20261022.md` and run
  in parallel with the P2-E7 contract review. Priority order unchanged.
- 2026-10-22, checkpoint 2 (after P2-E7 on seed 121, informative FEASIBILITY FAIL):
  previous order was (1) P2-E7, (2) offline screens A-D, (3) B-013 if admitted, (4) content,
  (5) online. New order: (1) screens F/E′, (2) P2-R3 replay, (3) P2-E8 on seed 123 if screen
  F survives, (4) B-013 screen F and question (a), (5) content contract and online.
