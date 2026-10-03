# Decisions

Add new entries at the end. Never edit an old entry; mark it superseded and point to the entry
that replaced it. Entries before 2026-10-03 live in `SPEC.md` (the spiking plant's record).

## 2026-10-03: brain-sim becomes a cognitive executive; the spiking plant is frozen

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
