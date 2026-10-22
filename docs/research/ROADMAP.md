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
the cue-line term of H-003 at M = 1,000. No record measures the pre-screen the skeptic judge
asked for (rebuilding the feedback store episode by episode and scoring the predicted set's
prototype fraction): the P2-R2b artifacts persist per-episode coin counts and degrees, not
the per-episode responder sets, so that measurement is folded into the contract's structural
kill on the development seed.

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

## Priority order (current)

1. P2-E7 error-gated forward eligibility: contract, adversarial read, freeze, tests,
   implementation, development seed 121 with the structural kill before any test phase; held-out
   122 only if every E6-frozen absolute bar holds; gated 131-135 under a separately frozen
   gate.
2. Zero-seed offline records on the persisted P2-R2b artifacts: the branch static screen
   with its coin-parity gate; the own-versus-spurious first-spike latency split (B-008); the
   regeneration-saturation diagnostic on `bench/results/p2e6`. Each appended through
   `plant2/evidence.py` as offline records before any contract cites it.
3. Branch-segregated dendritic storage (B-013), if the owner admits it, on seed 107.
4. Content: one mechanism per contract, after an index mechanism passes at both loads.
5. The online operating point (P2-E4's failures), after the index is specific on F10.

## Changelog

- 2026-10-22: first version, written at the checkpoint after P2-R2b. Priority order as
  above; no previous order.
