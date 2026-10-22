# Decisions

Add new entries at the end. Never edit an old entry; mark it superseded and point to the entry
that replaced it. Entries before 2026-10-03 live in `SPEC.md` (the spiking plant's record).

## 2026-10-03: brain-sim becomes a cognitive executive; the spiking plant is frozen

**Superseded in part** by the 2026-10-10 entry (the repository's purpose). The plant
paragraphs stand.

**Decision.** The repository's purpose is now the cognitive executive described in
`docs/architecture.md`: goals, world state, prediction, action selection, memory and learning
in ordinary code, with language models as tools. The spiking-network plant recovered after the
2026-10-02 wipe is kept, unedited, as research material.

**Why.** The owner's direction of 2026-10-03: biological fidelity is no longer a goal, and the
executive function should move out of the LLM. `SPEC.md` section 0 ("Path A", locked
2026-10-01) set the opposite direction for the plant: "no mini-AGI architecture in the plant",
language only as a late emergent capability. That section stays true *of the plant*; it no
longer describes the repository's purpose. Its other non-negotiable, "no LLM as the mind at
runtime", carries over: in the executive, a model supplies missing reasoning at impasses but
never runs the loop.

**What carries over from the plant, and what does not.** No plant code is reused. Its LIF
neurons, STDP and homeostasis have no role in an executive. Its methods do carry over:
predeclared pass/fail tests written before code, a never-trained twin as the baseline (here, a
run without the executive), labelled proxies, never lowering a bar to pass, "one source of
truth" telemetry, and acceptance not counted as execution (here, an applied edit is not a fix
until a fresh test run says so).

**Rejected.** A new repository for the executive. The plant has no code to share, so the
repo is chosen on continuity: the owner's mental model, the issue history and the name.
**Revisit if** the plant work resumes and the two lines need separate CI or releases.

## 2026-10-03: the plant stays at its recovered paths for now

**Decision.** Do not move `brainsim/`, `server/`, `ui/`, the plant tests or `SPEC.md` into a
`legacy/` tree yet. Mark them frozen in `AGENTS.md` and `README.md` instead.

**Why.** Recovery is not closed. `docs/recovery/carved-manifest-2026-10-03.tsv` and
`worktrees-2026-10-03.md` key every file by its original path, and further files may still be
recovered from disk. Moving the tree now would make the next recovered file land beside a moved
copy of its siblings. `git mv` costs nothing later and keeps history either way.

**Rejected.** `git mv` into `legacy/spiking_plant/` now. That would also break the plant's
`pythonpath = .` imports and 248 currently-passing tests.

**Revisit when** the owner declares recovery closed. Then move the plant with `git mv` in one
commit and leave the executive at the root.

## 2026-10-03: the executive depends on reflex-layer; never the reverse

**Decision.** brain-sim imports reflex-layer's `reflex` package in-process
(`pip install -e ../reflex-layer`). reflex-layer knows nothing about brain-sim.

**Why.** reflex-layer owns *capabilities* and the evidence that each is reliable enough to
use; brain-sim owns *deciding* which to use. One direction keeps reflex-layer usable from a
shell or another harness, as its own decision record requires.

**Rejected.**
- A subprocess JSON protocol between them. Safety does not come from a process boundary around
  the registry. It comes from declared effects, per-call grants, the confined `Workspace`, and
  the sandboxed test child, all of which hold in-process. A protocol would add serialization
  and process management with no safety gain today.
- An MCP server. reflex-layer already rejected one for measured reasons (its `DECISIONS.md`,
  2026-10-02).

**Revisit if** a non-Python caller appears, or the executive must run on another machine
than the capabilities.

## 2026-10-03: decision rules, not search, for the first planner

**Decision.** `executive/loop.py` is a fixed-precedence production system: observe if facts are
stale; complete if verified; otherwise work on the most salient open subgoal with the cheapest
applicable operator that has not already failed with the same plan; abandon at an impasse that
deliberation cannot cover; block when nothing can progress.

**Why.** The first task kind (make the failing tests pass) decomposes into independent
subgoals, one per failing test. No observed task yet needs ordering between dependent subgoals,
so GOAP or HTN search would be machinery without a test that needs it. The rules are short
enough to read in one sitting, and every decision is traced with all candidates and reasons.

**Revisit when** a task needs steps whose order matters (for example "reproduce, then bisect,
then fix"). That is the point to add HTN-style decomposition inside a skill.

## 2026-10-03: reflexes in reflex-layer, skills and memory in brain-sim

**Decision.** Single deterministic capabilities with exact or measured reliability live in
reflex-layer (`reflex/caps`). Multi-step procedures that branch on observations (skills, for
example `fix_name_typo`) live in brain-sim as operators, with their success counted per failure
class in procedural memory. A skill can be promoted into a reflex-layer capability once its
behaviour is deterministic and a benchmark marks it `measured`.

**Why.** It matches the owner's three levels (reflex, skill, deliberation) and keeps "is this
tool reliable" (benchmarks) apart from "is this the right tool here" (the executive).

## 2026-10-03: memory is exact matching, not embeddings

**Decision.** Episodic memory is append-only JSONL. "Can memory answer this?" means: an
episode with the same failure signature, on byte-identical implicated files, that a fresh test
run verified as fixed. Procedural memory counts outcomes per operator per exception type, with
Laplace-smoothed priors.

**Why.** Exact matching is checkable and cannot hallucinate a match. It is memoization, and it
is labelled as such. It is the floor that any fuzzier recall has to beat. No vector database:
reflex-layer's prior-art review found embeddings help only at the margin.

**Revisit when** the episode log shows repeated near-identical failures that exact matching
misses. Then measure a fuzzier key against this one.

## 2026-10-03: deliberation through `claude -p`, tool-less, schema-bound, not yet run live

**Decision.** `ClaudeCLIDeliberator` calls `claude -p --output-format json --tools ""
--json-schema … --max-budget-usd …` from an empty directory the executive owns, wrapped in a
recorder so every live answer can be replayed for free.

**Why.** It adds no dependency, and its `total_cost_usd` matches reflex-layer's spend
accounting. With no tools the model cannot act; it can only return data.

**Not done.** It has not been run against the live CLI: that spends money, and the owner's
workflow requires an explicit yes. The flags were taken from `claude --help` (CLI 2.1.288).
`structured_output` as the field carrying schema output is an unverified assumption, with a
fallback to parsing `result`.

## 2026-10-03: tests are protected from edits by default

**Decision.** The executive's workspace refuses writes to `tests/*`, `test_*.py`, `*_test.py`
and `conftest.py`.

**Why.** The goal is verified by running tests. If whatever proposes a fix could also edit the
tests, verification would be gameable, and "verified" would become a false-confidence
generator. The refusal is structural, through `Workspace.is_protected`, not an instruction to the model.

**Revisit for** tasks whose goal is to write or fix tests. Those need a different verifier
(for example mutation checks), not a removed guard.

## 2026-10-03: the executive verifies against the start-of-task test set and hands back a clean tree on block

**Decision.** Three changes, each closing a finding from the adversarial review.
- Test configuration (`pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini`) is protected by
  default, like tests. A model edit to it is refused (F4 A: a deselecting `addopts` used to
  produce `complete`).
- The first fresh observation records a baseline: the collected test ids and the ones that ran.
  Completion now also requires every baseline test to be collected still and none that ran to
  have become a skip. Otherwise the task blocks with the names (F4: a library-side
  `pytest.skip` made the failure vanish and read as fixed).
- On block, if any kept edit is not a verified fix, every kept edit is restored, newest first,
  and the pending attempt is closed as `restored_on_block` (F5). Restoring all, not only the
  unverified ones, avoids leaving a mixture of edits that never existed together. When every
  kept edit is a verified fix, they stay, because the handoff agent benefits from them.
- The executive blocks on any runner outcome outside `all_passed`, `tests_failed`,
  `no_tests_collected`, and requires `all_passed` for completion. This picks up reflex-layer's
  new `report_unverified` (F3) and anything added later.

**Changed test.** The resume test used to assert that the pending edit survived the
budget stop. That edit is now restored; the test asserts the original tree, then that a resumed
run re-applies the fix and completes.

**Not closed.** F4 C (a float subclass whose `__eq__` is always true) passes every test and
needs the mutation half of CANDIDATES.md B4.

## 2026-10-03: the executive must not apply a model patch it cannot judge (E7)

**What happened.** E7 rep 1 (six complex tasks with held-out tests) ran the hybrid against
Sonnet alone. On two tasks the executive's Sonnet deliberator saw the caller (`orders.py`)
but not the module holding the bug (`tax.py`). It said so in its diagnosis, at confidence
0.6, and proposed dividing by 100 in the caller. The visible tests passed, and the executive
declared the task complete. A held-out test failed. Sonnet alone fixed `tax.py` on both
tasks. That is the failure the owner named: the executive calling the shots on work larger
than it can judge.

**Decision.** Three changes, all deterministic.
- **Evidence.** The projection follows imports one hop further: the modules imported by the
  editable files it already shows. `from pkg import mod` resolves to `pkg/mod.py`; it used to
  resolve to `pkg/__init__.py`, which is how `tax.py` went missing. When over the file cap,
  the projection keeps frames first, then called definitions, then imports. It used to keep
  the alphabetically first files.
- **Evidence gate.** A model edit is handed off, not applied, when the function it edits calls
  into a workspace module that was not in the projection. The model cannot judge whether the
  fix belongs there.
- **Confidence gate.** A model edit whose stated confidence is below 0.8 is handed off. The
  model's self-report is weak evidence, but when it says "inferred" and 0.6, applying the edit
  overrules the only reviewer that saw the code.

**Rejected.** Never applying model patches, with deliberation only as a hint for the agent.
That would be safe, but E7's c6 and earlier E3 runs show correct, cheap deliberator fixes. E7b
measures whether the gates keep those and stop the bad ones.

**Rule restated for this project.** The executive takes a task only while it can verify it.
Anything else is handed over untouched, apart from fixes the tests verified. Reflex-layer's
capabilities stay tools that a model calls, with the model in charge.

## 2026-10-04: reconciling the plant replaces content at frozen paths when the evidence is byte-exact

**Decision.** The plant's paths stay where they are, but a file at a frozen path may be replaced
by another recovered version when (a) that version is identified by blob id or is the only copy
consistent with the code beside it, and (b) the replacement is its own commit, so one revert
undoes it. Two files were replaced on that basis: `brainsim/net.py` (the triplet traces the
tree's `engine.py` reads) and `ui/stage1_results.json` (master's 8.0-8.47 record in place of a
stale 8.0-8.20 copy). Details and test counts: `docs/recovery/reconciliation-2026-10-04.md`.

**Why.** The freeze exists so recovery can finish against stable paths; it does not oblige the
tree to keep a copy that a better-identified recovery shows to be wrong. The 2026-10-03 merge
ordered versions by mtime, which in this recovery records checkouts, not edits.

**Kept as is.** The tree's branch-line `engine.py`, `params.py`, `hetero.py` and `encode.py`.
They are supersets of master's with every added flag defaulting to master's path, and the
tests pass on them; master's byte-exact copies are in `docs/recovery/variants/master-f9411ab3/`.
Orphaned branch tests stay at their paths and keep failing: making them pass would mean merging
the closed k11 proxy hunts and the rejected 8.17 line.

**Revisit when** the owner declares recovery closed (then the `legacy/` move of 2026-10-03 applies).

## 2026-10-10: the owner's north star; a second plant (plant2) beside the frozen one

**Decision.** The repository's purpose is again a spiking, brain-like learning system, now
under the owner's north star of 2026-10-10: move toward human-level learning and
problem-solving capacity (flexible memory, sequences, abstraction, usable behaviour), with
human level as a horizon and never a claim without evidence. The work happens in a new
package, `plant2/`, on new branches. Nothing merges to `main` until the owner says "merge".
The recovered plant stays frozen at its paths (`AGENTS.md` invariant 4). The staged path, with
its gates, is `docs/plant2/STAGES.md`. Each experiment's contract is committed before its
code, and results are appended to `bench/results/plant2.jsonl`.

**Why a new package and not more plant experiments.** The audit of 2026-10-10 (summarised in
`STAGES.md`) found that the plant's Stage 1 failures are structural and documented: pair
STDP's fixed point sits below the homeostatic rest weight, the seconds-scale homeostat erases
writes, the cortical code is dense, and the wiring caps recall even with oracle weights
(SPEC 8.2-8.24, 8.49). The best line's code (8.30, 8.46) was not recovered. A new substrate
that drops those causes is cheaper and more honest than a fiftieth proxy on the old one.

**What carries over.** The plant's methods: predeclared kill tests, never-trained or shuffled
controls, labelled proxies, one mechanism per experiment, stop a line on FAIL. Its walls also
carry over: no LLM or transformer as the mind at runtime, no teacher current, no engineered
synchrony, no hand-set weights presented as learning, no bar lowered or rewritten to pass.

**Rejected.**
- Editing the plant on a branch. Recovery is not closed, and its manifests key on those paths.
- Continuing K1.1 on the plant, for the reasons above.
- The literal human-anatomy replica requested earlier on 2026-10-10. The owner's later
  instruction the same day superseded it before any code was written ("prefer lasting,
  specific, experience-driven change and inspectable state over anatomical name-dropping").
  Anatomical structure enters plant2 only where an experiment's metric needs it.

**Supersedes** the first 2026-10-03 entry's statement of the repository's purpose (the
executive it described moved to reflex-layer that day). Its plant paragraphs stand.

## 2026-10-10: P2-E2 tests threshold accommodation, next to a closed gate (flagged to the owner)

**Decision.** P2-E2 (`docs/plant2/P2-E2-accommodation.md`) gives plant2's memory cells a spike
threshold that slowly tracks each cell's own mean membrane potential (tau 10 s, additive). J is
calibrated on a held-out seed, and two void controls must hold: a fixed threshold at the same J
must fail, and a random store must fail.

**Why.** P2-E1's capacity curve and the independent review (`review/plant2/P2-E1/`) show that
no fixed threshold works across loads, because background from other memories sets each cell's
excitability. Two of the three reviewers proposed this mechanism independently. The third
proposed load-balanced plateau allocation. That proposal is deferred: it narrows hub variance
but does not fix slow recall at low load, and it reads per-cell load as an instructive
selector.

**The gate.** The owner's closed gates include "rejected intrinsic homeostasis as previously
run" (K0.14: a rate-setpoint threshold homeostat replacing synaptic scaling in the plant).
P2-E2's mechanism has no setpoint and no spike count, and it does not stand in for a synaptic
homeostat. The contract lists the differences. **This needs the owner's ruling.** If the owner
counts it under the gate, the P2-E2 result is withdrawn from the plant2 line and kept in the
record.

**Rejected for P2-E2** (reviewers' exploratory evidence):
- feedback k-WTA: it always picks winners, so unlearned cues ignite;
- recurrent links: they run away without a stabiliser;
- synaptic-count normalisation: it acts on written synapses, the plant's failure;
- Vogels iSTDP: the owner's wall.

## 2026-10-10: correction to the P2-E2 gate entry, and three questions for the owner

**Correction.** The P2-E2 entry above and the contract's table said K0.14's offset was
"gain-like". It was additive (SPEC around line 2600). The P2-E2 review (`review/plant2/P2-E2/`)
puts it accurately:
- Both are slow, per-cell, additive intrinsic-threshold homeostats.
- They differ in the controlled variable (mean membrane potential against firing rate), in
  role (beside BTSP, against replacing scaling next to STDP) and in network.
- P2-E2's offset tracks each cell's stored load (r = 0.998).

Reviewers judge it not a renamed re-run, but in the gated family. The entry above stands
otherwise.

**Work stops here for the owner.** P2-E2 passed, and every next step depends on these answers.

1. **The gate.** Does P2-E2's threshold accommodation fall under "rejected intrinsic homeostasis
   as previously run"? If yes, P2-E2 is withdrawn from the line and Stage 1 storage is open
   again.
2. **Capacity.** What does "capacity grows with cell count" scale: memory cells alone, inputs
   and memory cells together, or the plateau rate? A reviewer's exploratory surrogate gives
   these items-per-cell results:

   | what scales | effect |
   |---|---|
   | n alone | halves |
   | n with f_q halved | x1.7 |
   | m and n together | x2.2 |

3. **Inhibition in content completion.** May the content-completion experiment (P2-E3) add a
   fixed, activity-proportional inhibition on its readout layer as a declared second element?
   In a reviewer's exploratory runs, no fixed-threshold readout setting passed at M = 1,000
   without it.

## 2026-10-10: the owner's rulings on P2-E2, capacity, and content completion

Given by the owner after reviewing P2-E2 and its independent reviews. Recorded as given.

1. **P2-E2 is accepted as a distinct mechanism, and K0.14 is not reopened.** The rejection of
   intrinsic homeostasis "as previously run" (K0.14) stays closed. P2-E2's voltage-tracking
   threshold accommodation is admitted as its own tested mechanism, because its controlled
   variable, role and learning architecture all differ. Its family membership is recorded
   accurately: like K0.14, it is a slow, per-cell, additive intrinsic-threshold homeostat, and
   its offset tracks each cell's stored load (r = 0.998). The P2-E2 PASS stands with every
   limitation in its addendum.
2. **Capacity growth.** The primary experiment scales the input and memory populations
   together. Absolute active-input count and memory assembly size stay about constant;
   activation percentages are not preserved.
   - Memory-only scaling is the control.
   - Measured: absolute capacity, items per memory cell, synaptic storage cost, and whether
     the growth survives the full LIF simulation.
   - Exploratory surrogate predictions are not results.
3. **Content completion may use fixed inhibition.** P2-E3's reconstruction layer may use fixed,
   activity-proportional feedforward inhibition, declared as an additional fixed circuit
   element. The conditions:
   - matched no-inhibition and shuffled-feedback comparisons are included;
   - parameters are frozen before gated testing, with no per-seed tuning;
   - learning stays one-shot.

**Order of work.**
- P2-E3, content completion, comes first. The primary demonstration is regenerating the actual
  missing input features from a partial cue, not recovering the assigned memory assembly.
- A separate, predeclared **online-memory** experiment must pass before Stage 1 counts as
  complete. It tests recall while the system keeps learning new items, with no artificial
  50 s settle, and covers interference, retention of older memories and repeated-cue
  habituation. P2-E2's contract and result are not changed retroactively.
- After P2-E3, evaluate whether the new capability meaningfully advances the line toward
  sequences, abstraction and independent problem solving.

**Standing discipline.**
- Contracts are committed before implementation.
- Gated seeds are fresh, controls are meaningful, and every result gets an independent review.
- Passing thresholds are never revised, and failures are recorded without unplanned tuning.
- The plant stays frozen; the no-delete rules hold; nothing merges into `main` without the
  owner's approval.
- The objective is genuine, generalisable, experience-driven learning, not collecting passing
  benchmarks.

## 2026-10-10: P2-E3 reviewed; evaluation against the north star; work paused for the owner

**What happened.**
- **P2-E3 (content completion) passed** on 5/5 fresh gated seeds.
- **Four independent reviewers** found no bug that changes a reported number.
- **Their corrections are appended** to the P2-E3 document, with nothing above them edited:
  - the plateau-set control was read backwards: the responder-based write adds nothing
    measurable;
  - the claim is scoped to independent random items;
  - the feedback store saturates past capacity;
  - "inhibition required" holds at 0.25 items per cell only.
- **The readout's span counter was fixed**, and scoring tests were added.

**The evaluation** (`docs/plant2/EVAL-after-P2-E3.md`). P2-E3 is plumbing that later stages
need, not evidence of learning power. It is a spiking Willshaw hetero-associative memory with
random keys. An exploratory check on items that share about 16 % of their lines (two seeds)
collapses content completion: joint 0.15-0.17 at M = 500, against 0.99 for independent items.

**What was decided.**
- **Chosen:** stop before committing the P2-E4 (online memory) contract, and put five decisions
  to the owner. The decisions cover:
  - a structured-input clause in Stage 1;
  - P2-E4's scope past capacity and without the write oracle;
  - inhibition in the memory layer for Stage 2;
  - whether content-using mechanisms (an error-correcting write, familiarity gating) come
    before Stage 2;
  - the Stage 3 gate.

  Both north-star reviewers recommended this pause, and the answers change what P2-E4 should
  gate.
- **Rejected:** committing P2-E4 as drafted and running it. The draft is revised
  (`docs/plant2/P2-E4-online-memory.draft.md`) but has not been red-teamed. Gated seeds 16-20
  are untouched.
- **Rejected:** starting a new mechanism to rescue the structured-input result. That would be
  unplanned tuning of a finding that has not yet been gated.

## 2026-10-10: the owner's rulings after the P2-E3 evaluation

**Provenance.** The owner sent these rulings in reply to `docs/plant2/EVAL-after-P2-E3.md`. They
were drafted with an outside assistant's help and relayed by the owner as their own decisions.
They are recorded here in substance.

1. **Approved: structured-input robustness becomes a Stage 1 gate.**
   - **The test.** A prospective, predeclared test of item-specific episodic recall on correlated
     inputs: related exemplars with about 16 % sibling overlap, scored with the existing
     content-completion and specificity criteria.
   - **Loads and seeds.** M = 500, and ultimately M = 1,000, on fresh seeds.
   - **Diagnostic arms.** Lower and higher overlap levels.
   - **P2-E3 is unchanged.** Its PASS stands, scoped to independent random items.
   - **The objective.** To remember previously experienced correlated items without
     contamination. Generalising to a never-seen family member belongs to Stage 3.
2. **Approved with a condition: P2-E4 stays focused on online memory.**
   - **Gated:** continuous recall, interference resistance, retention of the oldest items,
     habituation and recovery, all at loads within the demonstrated capacity.
   - **Reported stress tests, not P2-E4 gates:** learning past capacity to M = 3,000, and the
     arms without the write oracle.
   - **A future requirement.** Bounded capacity and graceful forgetting must be met before any
     claim of robust, lifelong episodic memory.
   - **What P2-E4 keeps:** the continuous timeline, frozen parameters, the no-settle rule, and
     an honest distinction between experimenter-scheduled writes and autonomous learning.
   - **To add before P2-E4 is frozen:**
     - a blank-cue control proving that recall is caused by the probe, not by lingering
       encoding activity;
     - a never-probed cohort of the oldest items, separating retention from the effects of
       repeated probes;
     - power checks that account for dependent measurements and the full five-seed acceptance
       rule;
     - verification that the optimised reconstruction replay matches continuous simulation.
3. **Conditionally approved: fixed inhibition in the Stage 2 memory layer.**
   - **When.** Stage 2 contracts may declare fixed, activity-proportional inhibition as a
     stabilising circuit element when evidence justifies it.
   - **Required:**
     - a matched no-inhibition comparison;
     - frozen parameters;
     - independent controls;
     - tests showing that it does not just suppress all activity or force an answer.
   - **Not allowed.** P2-E3's coefficient does not carry over automatically, and inhibition is
     never treated as a learning mechanism.
4. **Priority: resolve structured-memory contamination before Stage 2.**
   - **First step.** Run the structured-input test on the existing system with no new
     mechanism.
   - **If it fails,** investigate the responder-based feedback write and its cross-contamination,
     against the plateau-set baseline.
   - **The error-correcting write** (driven by the mismatch between input and regenerated
     content) is an approved research direction, not an assumed solution. Its contract must test
     two things:
     - whether the feedback supplies useful error information;
     - whether corrections preserve unrelated memories.
   - **One new mechanism per contract.**
   - **Familiarity-gated allocation is deferred** until it is settled how repeated inputs should
     be represented in different contexts. Stage 2 needs distinct episode identities when the
     same item appears in different sequences, and familiarity must not erase them.
5. **Approved: a stronger Stage 3 gate.**
   - **The prototype effect and exemplar specificity must pass jointly.**
   - **Label efficiency** is tested at predeclared hard distortion levels, including about 0.8
     where appropriate. The level must not be chosen merely to make the raw-input baseline fail.
   - **Comparisons:** raw input, a never-trained twin, nearest-centroid and k-nearest-neighbour
     classifiers.
   - **The bar.** Meaningful absolute accuracy, plus the predeclared label-efficiency gain.
   - **Averaging or superposition at retrieval does not count** as learned abstraction.

**Execution order.**
1. Red-team and freeze P2-E4, implement it, and run it on untouched gated seeds 16-20.
2. Run the structured-input diagnostic before any Stage 2 work. If it fails, a separately
   contracted correction mechanism comes first.
3. Capacity scaling continues, measuring content accuracy as well as index recall.

**Standing.**
- **Every experiment is evaluated** by whether it reduces the cognition the experimenter
  supplies and increases what the system learns or decides from its own experience.
- **Unchanged rules:**
  - independent review;
  - append-only results;
  - predeclared kill tests;
  - full provenance;
  - no parameter rescue after a failed gate;
  - no deletion;
  - the plant stays frozen;
  - no merge into `main` without the owner's approval.

## 2026-10-11: owner's guidance after P2-E4 exploration (seeds 42-43)

**Provenance.** The owner sent this guidance after reviewing the exploration results, the frozen
code (unchanged) and the diagnosis code. It is recorded in substance.

- **Complete P2-E4 exactly as frozen.**
  - Record the exploratory failures, commit the power predictions, and run gated seeds 16-20 once
    each.
  - Nothing justifies changing the memory mechanism or the pass criteria.
- **Two problems appear distinct.**
  1. Learning-time contamination: the responder-based feedback write ties too many memory cells to
     each experience. Settled twin A at M = 1,000 (exploratory) read the same memory raster through
     three stores:

     | store | seed 42 | seed 43 |
     |---|---|---|
     | online-written | 0.815 | 0.89 |
     | P2-E3-protocol | 0.98 | 0.99 |
     | assigned-assembly (plateau set) | 0.995 | 0.995 |

  2. Operating-point instability: continuous input and repeated cues change which memories can be
     reached, even when their synapses are intact.

  They are not to be fixed together. One mechanism per contract.
- **Twin B's recovery** would show state- or protocol-dependent recovery, not that the threshold
  offset alone is the cause (`docs/plant2/P2-E4-diagnosis-plan.md`, narrowed reading of D3).
- **The assigned-assembly (plateau-set) store is an upper-bound diagnostic, not an acceptable
  solution.** A correction mechanism must let the network find which of its own active cells
  represent the current experience, without being handed that identity. That is the research
  target, not a further gain in recall on independent random items.
- **The order after P2-E4.** Finish the diagnosis and the gated evaluation. Then put first
  whichever failure remains most consequential under the structured-input tests (P2-E5).

## 2026-10-11: P2-E5 red-team acted on (contract revised, not yet frozen)

**The review.** The draft (e736e81) was red-teamed by three critics with refuters, plus a
completeness critic (workflow wf_7b8a1dd3-6aa). The findings are verbatim in
`review/plant2/P2-E5/`. All 31 were accepted, one in part; each disposition is a row in
`review/ledger.jsonl`. The revised contract is `docs/plant2/P2-E5-structured-items.md`.

**What exploration changed** (seeds 44-45; exploratory):
- **At M = 1,000 the forward BTSP index fails on correlated items.** C2 is 0.47-0.50, and the
  spurious cells are siblings' plateau cells. No feedback-write change can repair this, and the
  plateau-set store fails at every readout point. This is a third problem, outside the two the
  owner named.
- **At M = 500 the failure is the responder write.** Index C2 (about 0.90) and C4-spurious
  (about 0.89) still make S1 near-certain to fail: P(all five seeds) is 0.001.
- **The network's own continuation spike count identifies the item's assembly** among the
  responders (AUC >= 0.996). A store written only from cells firing 3 or more spikes matches the
  plateau-set store. This is measured as a reported reading. Adopting it would be a new
  mechanism, and needs the owner's ruling.

**Chosen:**
- **Validity.** P2-E3's convergence rule is kept unchanged. The draft's signed-drift bar is
  withdrawn: it would have made the run INVALID with probability about 0.8.
- **The gate.** C4 is restored to S1. There is a verdict vector, with STRUCTURED INDEX FAIL and
  STRUCTURED CONTENT FAIL labels.
- **Ranking the failures.** A predeclared ranking of failures (Part B: contamination, index and
  operating-point losses) implements the owner's guidance of 2026-10-11. It is built on a
  readout-grid upper bound, not the frozen readout point.
- **The online arm.** It runs on P2-E4's frozen driver (reported) and answers the owner's
  request to test contamination under continuous learning.
- **Controls and the family count.** The s = 100 positive control, a pooled line-frequency
  control and an F = 40 arm are added. F = 10 is fixed by argument.
- **M = 1,000 stays gated,** as the owner's "ultimately 1,000" and the draft read it.

**Rejected:**
- **A write-time regeneration replay** (owner-intent FID5-2, item 3). Ruling 4 assigns it to the
  mechanism's own contract, and the persisted rasters make it recomputable.
- **An F = 20 arm.** F = 40 separates family size from load with a roughly uniform line load.

**Open for the owner:**
- whether M = 1,000 should be gated now;
- whether the activity-gated write may be contracted beside the error-correcting write;
- how to treat forward-index cross-talk, which ruling 4 does not cover.

None of these blocks freezing. The contract gates what the owner ordered and routes these
questions to the owner through its Decision section.

## Addendum (recorded 2026-10-11): owner's comments on P2-E4's first exploration results (2026-10-10)

**Provenance.** This guidance was given before the diagnosis plan was written
(`docs/plant2/P2-E4-diagnosis-plan.md`, which cites it). It was not recorded here at the time.
It is recorded now in substance.

The owner said P2-E4 is exposing a critical weakness in the current architecture, and asked:
- **Do not intervene** in the frozen P2-E4 code or gates on the basis of the exploration results.
- **Diagnose each item after the run:** content against A(x) recall, R(x) recall and latency.
- **Isolate the operating point** with the settled twins.
- **Keep habituation separate.**
- **In P2-E5, test whether contamination worsens under continuous learning,** without adding a
  second mechanism.

P2-E5's online arm (Part D) implements the last point as a reported arm.

## 2026-10-11: owner's reading of P2-E4's results; a hypothesis for after P2-E4 and P2-E5

**Provenance.** The owner sent this after reviewing the P2-E4 contract's appended predictions, the
duty-arm implementation and the first gated readings. It is recorded in substance.

**The finding the owner judges most important so far: an encoding-retrieval trade-off.** The
conditions that improve access to stored memories appear to make those memories less reliable to
write.
- **The main timeline** has a higher threshold offset, weaker assigned-assembly recall, and
  relatively clean reconstruction.
- **The duty arm** has a lower offset, stronger recall, and a much more contaminated store.
- **The caveat.** The duty arm changes the whole stimulation schedule, not only the offset, so it
  does not prove that the offset alone causes the difference.
- **So a threshold adjustment alone** (for example changing the accommodation time constant)
  might trade one failure for another. The owner advises against trying it as the fix.

**What the settled twins establish:**
- **Twin A** (same memory raster, store swaps) establishes a feedback-store quality problem,
  independent of whether the memory-layer state is optimal.
- **Twin B** shows the recallable population changing with the activity regime. Settling
  recovers online failures but also loses some earlier successes; at M = 500 on seed 42, seven
  cues went that way. Settling does not simply improve everything.

**The hypothesis for the next mechanism** (for after P2-E4 and the structured-input
investigation; **not permission to modify current experiments**): a memory cell being active
during an experience should not automatically qualify it to write that experience's content.
- **One candidate:** a local eligibility signal tied to a genuine plateau event. A cell joins
  the feedback write only when its own recent activity and eligibility support the
  association.
- **Recall stays responsive while unrelated active cells are kept out of the write.**
- **The assigned-assembly store is an upper bound.** The eventual mechanism must derive
  eligibility locally, not receive the assembly from the experimenter.

**Wording.**
- "P(PASS) is 0" in the predictions record means **zero passes observed in 1,500 joint
  simulations**, not that a pass is impossible. The 95 % upper bound is about 0.002.
- The P2-E4 Result uses that wording. The contract's appended predictions section is not edited.

**The interpretation to preserve.**
- The high-load failure is not necessarily a failure to store: some information is recoverable
  after a state change.
- The deeper problem may be that the architecture has no reliable way to keep access to its
  memories while writing new ones accurately.
- That is the sharper research question: **the coordination of learning and recall,** ahead of
  more storage capacity.

**Process.** Complete P2-E4's predeclared five-seed evaluation unchanged.

**How it maps onto existing work** (agent's note):
- **P2-E4's exploration diagnosis** (`docs/plant2/P2-E4-diagnosis-plan.md`, results of seeds
  42-43). At M = 1,000, about 95 % of online index failures recover after the settle, while
  content moves the other way: 22 and 27 cues pass online but fail settled, against 8 and 4 the
  reverse. Most online index failures are retrievals slowed by about 8 ms.
- **P2-E5's Part C** measures, without adopting, an activity-based local eligibility: the
  continuation spike count. In exploration it separates the item's assembly from unrelated
  responders with AUC >= 0.996. A store written from cells with 3 or more spikes matches the
  assigned-assembly store.
- **A plateau-trace-gated write** would be local too, but in the current model it reproduces the
  assigned-assembly store exactly. It inherits the random, content-blind plateau key.
- **Neither repairs forward-index cross-talk on correlated items at M = 1,000.**

## 2026-10-11: P2-E5 verification acted on (second revision; not yet frozen)

**The review.** Three verifiers checked the first revision: numbers and power, coverage, and
implementation ambiguity. Their reports are verbatim in `review/plant2/P2-E5/verify-*.md`, and the
36 dispositions are rows in `review/ledger.jsonl`.

**Corrections to the previous entry,** appended rather than edited:
- **"All 31 were accepted, one in part" overstated what was done.** Correction rows now mark:
  - implementation M1 and completeness C4 as accepted in part;
  - methodology M2, B1 and n1 as completed only by this revision.
- **The quoted "P(all five seeds) 0.001"** for S1 at M = 500 rested on one lens and an
  independence assumption. With all four exploratory runs it is 0.0095 (independent model) to
  0.039 (dependent model). By run it ranges from 0.0002 to 0.12. The conclusion stands: the index
  very likely fails S1 at M = 500, whatever the write.

**Chosen in the second revision:**
- **Part D** reads the median-intrusion ratio, not the joint, which sits at a floor at
  M = 1,000.
- **The grid best** is pinned as the maximum joint. Seed 45's grid was run by the lead with the
  red-team's script; at M = 1,000 the plateau-set store's grid best is 0.60 and 0.665.
- **Part B** works in cue counts, caps the contamination loss at the bar, requires a material
  dominant loss, and folds in the NOT ATTRIBUTABLE exclusions. In consequence, M = 500's reading
  depends on the online operating-point loss, which no one has measured on structured items:
  - CONTAMINATION-DOMINANT if it is at most about 0.15;
  - SPLIT near 0.25;
  - OPERATING-POINT-DOMINANT above about 0.35.
- **The Decision** sends any STRUCTURED INDEX FAIL, and any non-contamination or disagreeing
  reading, to the owner before a mechanism contract.
- **Validity 7** checks that the gated write is still P2-E3's, through a read-only step wrapper
  in place of a copied `learn_one`.
- **P2-E3's shuffled leak rule** is quoted unchanged, and P2-E3 addendum item 8 is addressed
  explicitly. It is not met, for stated reasons, with a specificity check if a PASS occurs.

## 2026-10-11: P2-E5 contract frozen (after verification, a fix-check and a final diff check)

The fix-check (`review/plant2/P2-E5/fixcheck-*.md`) and final diff check (`finalcheck.md`) were
acted on, with every finding in the ledger.

**What the fix-check measured** (exploratory). It ran P2-E4's frozen online driver with P2-E5's
structured items (seeds 44-45, M = 500), and found the owner's encoding-retrieval trade-off on
correlated items:
- **The same online-written store,** on the same 200 cues, reads content 0.525-0.58 online
  against 0.035-0.055 after the settle.
- **Index access falls online:** C1 0.77-0.82 against 0.955-0.965.
- **The online state** has a higher threshold offset (3.7 against 1.9 mV), among other
  differences. Which state variable is responsible is not isolated.
- **So the settled protocol gives the cleaner write, not the cleaner retrieval.**
- **The measured net online index loss** is 0.145-0.185. At that value, Part B at M = 500 reads
  CONTAMINATION-DOMINANT with probability about 0.7-0.96, or else SPLIT.

**Corrections to the 2026-10-11 verification entry,** appended rather than edited:
- **Methodology B1 is accepted in part.** Probabilities are given only for S1, validity, Part B,
  s = 100 and P(PASS).
- **The per-run range 0.0002-0.12** is the dependent model's. The independent model gives
  6e-6-0.06.
- **The structured L_o is no longer unmeasured** at M = 500: it is 0.145-0.185, from the
  fix-check.

**The freeze.** The contract is frozen with its `power_reference` record (`analysis/p2e5_power.py
--append`). The P2-E5 driver is written only after P2-E4's gated seeds finish, because the plant2
tree stays frozen until then.

## 2026-10-11: P2-E4 closed out (Result, results review, gated diagnosis); evaluation for the owner

**What was done.**
- **The Result** was appended to P2-E4's contract, with readings added after the review
  (89d5bde, 0a42d09). The verdict, ONLINE INDEX FAIL + HABITUATION FAIL + RECOVERY FAIL, stands
  as recorded. Nothing was re-run, relabelled or retuned.
- **An independent four-lens results review** (`review/plant2/P2-E4/results-*.md`) confirmed it.
  The code reviewer recomputed every gated number, label and validity flag from the hashed logs,
  and all matched. All 32 findings are in the ledger: 27 accepted, 5 deferred to the owner.
- **The diagnosis plan** received a correction to its exploration write-up and the gated D1-D4
  results, scored against their predictions:
  - the causal offset sentences are withdrawn;
  - exploration D1 is withdrawn as a test;
  - D4 is reported net of the control copy (2.0-2.1 mV);
  - "rules out" becomes "does not support".
- **The P2-E4 row** was added to `docs/plant2/STAGES.md`.
- **The evaluation for the owner** is `docs/plant2/EVAL-after-P2-E4.md`.

**Recorded readings (the owner's wording kept).**
- **The prediction:** zero passes in 1,500 simulations, not a mathematical proof.
- **RECOVERY FAIL is read per seed and load** (seeds=1, loads=1), following the frozen rule. It
  rests on seed 18 at M = 500, one item short, with p0 0.831 against the 0.8 bar. Read over all
  seeds and loads, the label would be RECOVERY NOT ESTIMABLE.
- **Validity 5's** `proj_current` and `inh_ok` parts hold by construction. Twin A's zero replay
  mismatch is the evidence that the projection was current. P2-E5 reuses that check, and its
  verdict text will say the same.
- **The failure at high load is not a failure to store.**
  - Online index failures are mostly slowed retrievals of intact assemblies: 86-100 % pass after a
    settle on the same synapses.
  - The online-written content store is contaminated, and the online regime masks it.
- **Which state variable is responsible for the trade-off is not isolated.** The gated data do
  not replicate the exploration's offset correlate.
- **A newly named experimenter supply:** separate encoding and retrieval states, set by the
  schedule. P2-E4 removes nothing at learning time.

**Questions for the owner** (`EVAL-after-P2-E4.md`, last section). No mechanism contract is
drafted before P2-E5's verdict and these rulings.
1. May burst-gated feedback eligibility (at least 3 continuation spikes, k fixed by P2-E5 Part C)
   be the next contract? It is the activity form of the owner's eligibility hypothesis.
2. May fixed stabilising inhibition in the memory layer join a Stage 1 recurrent completion
   mechanism?
3. Where does forward-index cross-talk on correlated items go?
4. Should one latency bar cover index and content in future contracts?
5. Optional: a reported-only replay of seed 18's M = 500 habituation copies.

**Not done, by the owner's direction:**
- the current experiments are not modified;
- P2-E5 runs exactly as frozen.

## 2026-10-11: P2-E5 run and closed out; the result goes to the owner before any mechanism contract

**Result.** STRUCTURED INDEX FAIL + STRUCTURED CONTENT FAIL on 5 of 5 valid fresh gated seeds
(f25d3ed). It is appended to the contract (20273ed). The four-lens results review is in
`review/plant2/P2-E5/results-*.md`, and its 30 findings are in the ledger: 27 accepted, 3 deferred
to the owner. Both independent recomputations matched the records exactly. Nothing was re-run or
retuned.

**Corrections recorded.**
- "Online, the index is specific but slow" (appended predictions, and my report to the owner) is
  withdrawn. The comparison was unpaired, and latency was not measured.
- "No pass observed in simulation" is withdrawn. P(PASS) was an analytic product, numerically zero.
- Part C is reworded: the plateau key is recoverable from activity. It is a measurement, not a
  mechanism.
- Part B at M = 1,000 is CONTAMINATION-DOMINANT under the predeclared grid-best convention, and
  would read INDEX-DOMINANT at the frozen readout. Both are reported. The predeclared reading
  stands.

**Put to the owner** (`docs/plant2/EVAL-after-P2-E5.md`):
- the STRUCTURED INDEX FAIL, which no feedback write can change;
- the finding that no store reaches the content bar at M = 1,000 on these rasters;
- the reviewers' disagreement over the next step, with a recommendation: the burst-gated write as a
  reported replay, then the forward index as the next gated mechanism;
- the choice of F;
- the Part B convention;
- the questions still pending from EVAL-after-P2-E4.

**Not done:**
- No mechanism contract is drafted before the owner rules.
- Familiarity-gated allocation stays deferred.

## 2026-10-12: owner-authorized research takeover (session begun Oct 11, America/Chicago)

Source: the owner's explicit Work-session takeover request, followed by the instruction to
push regular checkpoints. Base fetched and verified: `plant2-stage1` at
`55e16ebff62a90d6402745f44fb860010741eba5`. Work branch:
`codex/plant2-takeover-20261012`. Up to three evidence-driven passes are authorized; a clean
partial experimental checkpoint is required if compute prevents complete gating.

Owner rulings, recorded before any new mechanism experiment:
1. R_3 (at least three continuation spikes) is first a reported replay/diagnostic, not a gated
   eligibility mechanism. Compare inherited, assigned-assembly, size-matched random and
   anti-selected writers, including P2-E4's longer-gap duty schedule and P2-E5's correlations.
   Recovering the supplied plateau key is not self-selected representation.
2. Fixed activity-proportional memory inhibition is authorized as a Stage 1 recurrent-memory
   stabilizer if justified, with no-inhibition, inhibition-only and shuffled/degree-matched
   controls, frozen parameters, and checks against silence or imposed answers. It is not learning.
3. Forward-index interference is the next primary mechanism target. Investigate local error and
   presynaptic-load signals, select one mechanism per contract, and score index independently
   from content. Do not stack unproven mechanisms.
4. Keep the existing 50 ms index and 75 ms content requirements. Any future end-to-end latency
   proposal is separate; no retrospective relaxation.
5. Ten families remains the canonical hard condition; forty families is an additional transfer
   diagnostic, never its replacement.
6. Frozen deployed readout is primary. Best-over-grid is only an explicitly optimistic diagnostic.

Standing: contracts precede implementation; exploratory/calibration/gated seeds stay separate;
all failures and invalid runs remain; decisions/results append only; independent adversarial
review; no main merge, history rewrite, destructive cleanup, or external spending. The recovered
plant and historical experiment code/contracts remain untouched. No Stage 2 advancement without
the required substrate. The absolute no-deletion rule overrides older sandbox exceptions.

Environment: approximately eight CPU cores and 8 GiB cgroup memory; NumPy 2.3.5. Historical
raw cache artifacts are not present here. Shell clone/fetch works, shell push lacks credentials;
checkpoints will use the connected GitHub Git-data API with non-forced, expected-head updates.
The inherited global ~/.agents/AGENTS.md is absent. Both accessible reflex-layer AGENTS variants
were read; brain-sim and the owner's stricter rules apply. Pytest is an existing test dependency,
fetched as verified wheels into a new cache directory without package-manager cleanup. No new
production dependency is introduced. Upstream safety lint is fetched at blob
`443d3c26ef8bdda42ef507eb1382d5c0fc9d915b`; its direct scan reports only the twelve documented legacy
findings. The required pytest wrapper needs the absent reflex package; this limitation is reported
rather than hidden by a stub.


## 2026-10-12: independent baseline audit before new mechanism work

The P2-E4/E5 frozen failures survive independent aggregate recomputation. P2-R1 found material
interpretive errors, now appended to both evaluation documents: the pooled control did not
match per-line marginals; a settled readout was called online retrieval; feedback-only changes
need not inherit composite O4/O5 labels; some claimed replay inputs were never persisted.
The audit also corrects prototype size/line load and overbroad impossibility statements.
These corrections precede the new index mechanism's freeze and do not relabel old gates.

The baseline fast suite passed63 tests,7 slow deselected,57.07s. Safety wrapper collection is
blocked by absent reflex; the exact upstream stricter lint and both wrapper-equivalent
assertions show only the12 grandfathered findings. Pytest runs with sys capture and tmpdir/cache
plugins disabled, preventing its usual automatic temporary-file cleanup.


## 2026-10-12 — P2-R1 completed; index-first direction retained

The predeclared burst replay completed correlated seed44 and duty seed90 at500/1000.
At correlated1000, fixed-readout R3 content is.160 and index specificity.500; cleaning the
tested writer does not solve the canonical stress case. Duty1000 settled R3 content is.995
versus inherited.205, count-matched random.710 and anti.655. This supports writer identity
beyond writer count on those rasters, while R3 nearly reproduces externally assigned keys.
No live R3 result or new gated capability is claimed. Six independent results-review scope
findings accepted; see RESULTS-P2-R1.md and review ledger. P2-E6 contract6733109 selects one
causal presynaptic-history encoding rule; no R3 deployment, readout retuning, inhibition or
recurrence is stacked with it. Historical verdicts and Stage1-incomplete status remain.


## 2026-10-12 — P2-E6 feasibility rejection; exact-degree explanation test selected

P2-E6 seed101 completed all16 loads and both sanity controls in608.64s. The frozen screen
is complete and integrity-valid but fails F10/1000 C2=179/200 and oldest specificity=89/100.
Baseline C2=.500, candidate=.895, exact flip-count-matched random=.460; candidate recall=.970
versus baseline=.935. Independent regression and all other mandatory bars pass. This is a
substantial measured selectivity gain on one development seed, not an overall PASS. Preserve
the failure without retuning: held-out102 and gated111–115 remain untouched. F40 transfer
passes its index bars but cannot rescue the ten-family failure. No Stage1 completion.

Select P2-R2 as the third and final takeover pass: a predeclared input-degree-preserving
control investigates a distinct explanation, separating family grouping from exact line-count
marginals more rigorously than the old pooled control. It uses unchanged E3 learning, two
fresh seeds103/104 and no E6 mechanism, R3 deployment, readout sweep or new inhibition.
The final reviewed contract will be committed before its driver. It is a reported causal
intervention screen, not a capability gate; timing/eligibility/state differences remain
explicit. No fourth pass or Stage2 work is authorized by this selection.


## 2026-10-12 — P2-R2 closure and takeover stop

Third and final pass: the exact-degree input null completed all eight neural checkpoints.
Seed 103 is COMPLETE and meets the declared material structure-sensitivity contrast at1000:
C2 .470→.755, joint index .410→.675, C1 .930→.920. Absolute specificity and content still fail.
At500, its oldest recall drops .980→.910 despite improved content; do not hide that cost.

Seed 104 and the formal two-seed outcome are INVALID. Its original1000 combined evidence file
is empty, and two earlier progress events are absent; the final paired read fails after all
neural/readout stages complete. Retained components independently reconstruct the exact
recorded1,883,558-byte SHA-matching artifact, saved at a separate recovery path. Original
failure evidence remains untouched. Recovered104 C2 .460→.715 and joint .400→.640 are post hoc
numerical evidence, not a valid replication. No replacement, rerun, threshold change or fourth
pass is performed. The cause of the persistence discrepancy is unresolved; no source path
explaining a truncation was identified. Preserve this open integrity limitation.

Next work should first establish durable per-worker evidence and verified checkpoints, then
predeclare fresh explanatory replication before selecting another learning mechanism. Do not
retune E6, combine R3 with it without a new contract, or begin Stage2. The takeover demonstrates
partial selectivity effects and sharper diagnostics, not accepted robust memory, autonomous
keys, capacity growth, abstraction or independent cognition. Stage1 remains incomplete.


## 2026-10-22: autonomous research mandate; a research ledger; evidence durability before any new seed

**Provenance.** The owner's instruction of 2026-10-22 ("autonomous research mandate: open-ended
architectural discovery"), followed the same morning by the ledger structure (research map,
hypothesis ledger, experiment ledger) and the request for a separate speculative backlog. The
agent is lead researcher under the standing rules of this file; the invariants named by the
owner are the 50 ms index process, the 75 ms content process and the ten canonical families.

**Decisions.**
1. Work continues on `plant2-research-20261022`, branched from the takeover tip
   `5b5ee63` so that every takeover result and review is in the history. Nothing merges to
   `main` without "merge".
2. The research record gains `docs/research/` (README, RESEARCH-MAP, HYPOTHESES, EXPERIMENTS,
   BACKLOG, ROADMAP). Its rules are in `docs/research/README.md`; the central one is that a
   proposed idea, an attempted experiment and a demonstrated capability never share a table.
   `docs/plant2/`, `bench/results/` and `review/` stay the primary record and are not edited to
   fit the ledger. The first version of the three ledgers is built by reading the whole record
   with independent extraction and adversarial verification before any synthesis, so that
   numbers enter the ledger from the sources, not from recollection.
3. The first engineering change is evidence durability (`docs/plant2/EVIDENCE-DURABILITY.md`,
   `plant2/evidence.py`): verified exclusive artifacts, sequenced per-worker journals with
   readback, and manifest completeness checks before any stage is declared complete. Every
   reviewer of P2-R2 and the takeover handoff made this the first next step, and no new seed
   is spent before it exists. Frozen drivers are not retrofitted.
4. "Ten canonical neuron families" in the mandate is read as the F = 10 item-family stress
   condition that ruling 5 of 2026-10-12 made canonical; the record has no ten neuron types.
   The owner can correct this reading; nothing yet depends on it.
5. The Python environment on this PC is the uv venv at `~/.cache/brain-sim/venv` (CPython
   3.11.17, NumPy 2.4.6); the takeover ran on NumPy 2.3.5 elsewhere. New records carry their
   own `runtime` field; no claim of byte-identical rasters across the two is made. The required
   safety lint runs standalone from reflex-layer's `tools/safety_lint.py` (blob 443d3c2,
   fetched read-only; the sibling checkout the wrapper test expects is absent here) and reports
   only the twelve grandfathered findings.

**Alternatives rejected.** Keeping the ledger in `review/ledger.jsonl` (that file is the
review-disposition log and has a different schema); putting the ledger in `DECISIONS.md` (it
would bury the owner's rulings); starting a mechanism contract before the durability module
(cheap in compute, but it would spend seeds under the integrity limitation the record left
open).

**Revisit when** the owner rules on the "ten families" reading, or when the ledger's
status vocabulary proves too coarse for a result (then extend the vocabulary in the README,
never reinterpret an existing label).


## 2026-10-22: roadmap checkpoint after P2-R2b; P2-E7 error-gated forward eligibility selected; seed registry; owner questions bundled

**Provenance.** The first checkpoint under the 2026-10-22 mandate, run after P2-R2b closed
(COMPLETE on seeds 105/106, independent recomputation, errata; `docs/plant2/RESULTS-P2-R2b.md`).
The three ledgers were built first (`docs/research/`, commit `82956d5`). A judge panel of five
independent Opus proposers (circuit biology, theory, engineering, supply reduction,
contrarian) and three Opus judges (skeptic, constructive, owner-intent) scored ten proposals;
the full record is `docs/research/ROADMAP.md`, checkpoint 2026-10-22.

**Decisions.**
1. The most consequential limitation is forward-index cross-talk on F10 items at M = 1,000
   (C2 0.435-0.515 gated; .895 after P2-E6 on one seed; .720-.755 under the exact-degree null
   on three valid seeds). Ruling 3 of 2026-10-12 names it; P2-R2b's replication satisfies
   the capability review's condition for choosing a co-occurrence-sensitive mechanism, and by
   P2-R2b erratum 5 that condition informs this decision rather than authorising it.
2. The next contract is **P2-E7: prediction-gated (error-gated) forward eligibility with a
   conserved flip budget** (B-002, H-060; the owner-approved error-correcting family of
   2026-10-10 ruling 4; the local-error signal of 2026-10-12 ruling 3). One mechanism, no new
   parameter, no retuning of P2-E6 (E6's history counts appear only inside a control, never
   in the candidate). The engineering and supply-reduction proposals are merged into one
   contract with these mandatory controls: inherited baseline; count-matched random drop
   (stream 33); history-weighted drop (stream 34, control only); gate-off integrity arm whose
   forward store must equal the baseline's byte for byte; reported no-conservation arm;
   label-oracle comparator (diagnostic only); independent-input baseline and candidate for
   non-regression; the H-042 matched-state diagnostics; P2-E6's sanity checks. A structural
   kill runs before any test phase. The contract is committed before any code, read
   adversarially before freezing, and the feasibility bars are copied from
   `docs/plant2/P2-E6-frozen.json` verbatim.
3. **Seed registry.** P2-E7: development 121, held-out 122, gated 131-135. Branch-segregated
   dendritic storage (B-013), if the owner admits it: development 107, held-out 108, gated
   141-145. Reported replays that need one fresh independent raster: 109. Spent or reserved
   before today: 0-25, 42-45, 90, 97, 99, 101-106, and 102 plus 111-115 (P2-E6, unrun). The
   panel's proposals claimed 107, 108, 121 and 131-135 two or three times each; this entry
   assigns each once. No seed is shared between contracts.
4. P2-E7's baseline-arm raster carries, as reported-only passive diagnostics that change no
   raster and score no outcome, the R_3/R_1/size-matched-random/anti-selected stores (a
   fresh-seed replication of P2-R1 at no simulation cost) and, if its replay is ready, the
   episode-clustered reconstruction store. Per-episode continuation counts and the R, A and
   E sets are persisted through `plant2/evidence.py` so later replays need no new seed.
5. Zero-seed offline records go into `bench/results/` through `plant2/evidence.py` before any
   contract cites them: the branch static screen on the P2-R2b artifacts with its stream-3
   coin-parity gate; the own-versus-spurious first-spike latency split (B-008's cheapest
   test); the regeneration-saturation diagnostic on `bench/results/p2e6`. Until recorded,
   the panel's and judges' offline numbers are quoted only as unrecorded computations.
6. `docs/research/ROADMAP.md` now exists (the constructive judge noted that `BACKLOG.md` and
   decision 2 of the previous entry cited it before it was written).

**Alternatives rejected.** Branch-segregated dendritic storage first (second-ranked, 59-60 of
90; an orthogonal attack on the same limitation, but it needs a ruling on whether a K-branch
cell is the same system or memory-only scaling, and it is not inside ruling 3's named
signals). Memory-layer E%-max inhibition (H-008 records that global feedback inhibition
cannot satisfy C3; ruling 2 allows it only as a stabiliser). Deployed R_3 (ruling 1; content
is index-limited at 1,000 by H-046). Mismatch-gated plateau initiation (blocked on the
familiarity deferral). Non-plateau responder depression (its own author predicts it misses
the bar; kept as the in-scope fallback). Running two mechanism contracts on one development
seed (different selection histories; one mechanism per contract).

**Questions for the owner (none blocks P2-E7).** (a) Does dendritic-subunit storage count as
the same 4,000-cell Stage 1 system under ruling 3, or as memory-only scaling under the
capacity rule (`DECISIONS.md:319-325`)? (b) May R_3 move from reported replay to a gated
contract? (c) May memory-layer inhibition be used standalone rather than as a recurrence
stabiliser? (d) Does the familiarity deferral still block mismatch-gated plateau initiation?
(e) Is the F = 10 reading of "ten canonical neuron families" correct?

**Revisit when** P2-E7's development screen returns (pass: held-out 122, then the gated
contract; structural or kill-rule death: classify the failure and move to B-013 if admitted,
else to responder depression), or when the owner answers any of (a)-(e).


## 2026-10-22: checkpoint 2 after P2-E7; zero-seed screens F/E′ and the P2-R3 replay selected now; P2-E8 graded error weighting selected conditionally on seed 123; owner question (f)

**Provenance.** P2-E7 on development seed 121 closed as an informative FEASIBILITY FAIL with
every number independently reproduced (`docs/plant2/RESULTS-P2-E7.md`, errata 1-12;
`review/plant2/P2-E7/findings-results.md`). Offline screen E located the residual
(`docs/plant2/OFFLINE-SCREENS-20261022b.md`). A second judge panel (workflow wf_d9fc89e1-dac:
three Opus proposers, two Opus judges) produced six proposals and one recommended sequence;
the full record is `docs/research/ROADMAP.md`, checkpoint 2.

**Decisions.**
1. The most consequential limitation is unchanged in kind and narrower in place: the
   residual cross-talk under the error gate is a late-episode leak of prototype lines the
   prediction misses, written at p ≈ 0.84 by the conserved budget, on top of a minor legacy
   of the four to thirteen family members written before the veto engages; and the content
   wall behind the index is intrusion, not missing-line recovery (D1 ≥ .955 on every seed-121
   arm).
2. Selected now, zero seed, in parallel, each under its own frozen contract and recorded
   through `plant2/evidence.py` before anything cites it: **screens F and E′**
   (`docs/plant2/OFFLINE-SCREENS-20261022c.md`: the kill-only screen for the graded rule,
   the ramp, the counterfactual flip counts, the twin-store coverage line, and the
   re-binning of screen E by write-time coverage) and **P2-R3**
   (`docs/plant2/P2-R3-branch-reconstruction-replay.md`: the B-015 bounded reconstruction
   store as an exact reported replay with K = 1 parity, a per-synapse scramble, the
   assigned-A store under the same rule, dose arms, and the intrusion-span decomposition
   first). Neither spends a seed; the replay is the one decision 4 of checkpoint 1 allowed.
3. Selected conditionally as the next seed-spending contract: **P2-E8, graded
   prediction-error weighting of the conserved flip budget** (B-016; the binary veto nested
   as w = 0; no new constant; the P2-E7 binary rule as a same-seed comparator; graded_shuffled
   and history_rank controls holding the exact multiset of p; gate_off integrity; the label
   oracle; independent and mixed non-regression; surplus-only as a reported arm that decides
   nothing). It is contracted only if screen F survives its kills (AUC ≥ 0.70 over episodes
   501-1,000; graded/binary counterfactual prototype-flip ratio ≤ 0.6; not both a ramp ratio
   > 0.85 and a late class concentrated in E′'s low-coverage bins).
4. **Seed registry additions.** P2-E8: development 123, held-out 124, gated 151-155. P2-R3:
   none (replay on seed 121's persisted evidence). Unchanged: P2-E7 121/122/131-135 (122 and
   131-135 stay closed); B-013 107/108/141-145; replays needing a fresh raster 109.
5. P2-E7's verdict stands; no constant is touched; seed 122 does not open.
6. The twin-store teacher proposal is recorded in the backlog (B-017) as closed pending the
   one-line offline record screen F appends (the baseline trajectory's own gate coverage over
   episodes 101-500 against the proposal's own kill); B-013 keeps its zero-seed screen on the
   list, contracted if P2-E8 dies offline.

**Alternatives rejected.** Running P2-E8 on a seed without the offline kill (the judges'
rescue concern; the screen costs nothing). Surplus-only conservation as a standalone
contract (its author predicts C2 below the bar; the closest to a rescue). The twin-store
teacher (the record already contradicts its key prediction; two changes in one contract).
B-013 first (owner ruling pending; its screen needs a single-unit simulation; the error-gate
family still has an untested, cheaper step). A gated content contract now (ruling 3 puts the
index first; P2-R3 is a reported replay).

**Questions for the owner (added to the bundle of checkpoint 1; none blocks the zero-seed
work).** (f) Is a graded prediction-error weight, with the binary veto nested as its w = 0
case, no new constant and the binary rule as a same-seed comparator, a different rule with a
reason rather than a rescue of P2-E7? The orchestrator treats it so and will spend seed 123
only after screen F survives; the owner can veto before then. (g) If P2-R3 shows that
reconstruction-side summation limits content at 1,000, may a content contract on fresh seeds
precede an index pass (ruling 3), and does question (a) extend to reconstruction lines
(ruling 6)?

**Revisit when** screen F returns (pass: contract P2-E8; kill: contract B-013's screen F and
raise question (a), else B-014), or when P2-R3 returns (its step-0 decomposition decides
whether B-015 continues), or when the owner answers (a), (f) or (g).
