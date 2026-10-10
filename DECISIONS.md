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
