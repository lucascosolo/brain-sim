# Architecture: a cognitive executive over a verified capability layer

Written 2026-10-03, after inspecting brain-sim, reflex-layer and the owner's `~/.agents`
suite (read-only). Decisions are in `DECISIONS.md` in each repository. This page says what
was found, where the boundary sits, and what the first slice proves.

## What the repositories contain

**brain-sim** is a recovered spiking-network research plant, not an executive. It has 2,600
LIF neurons with STDP, homeostasis and structural plasticity (`brainsim/`), a FastAPI/WebSocket
worker and a vanilla-JS viewer (`server/`, `ui/`), and a 6,688-line `SPEC.md` of predeclared
experiments (Stage 0, and Stage 1 sections 8.0 to 8.49). Its episode-memory law K1.1 never
passed. It has no concept of goals, plans, tasks or tools.

The recovery is a mosaic. Thirteen files were carved from git objects and 36 worktrees from
the ext4 journal, and the newest copy of each path was merged. Master `c9863d6` and six
branches were never found. Run here on 2026-10-03, the legacy suite gave **248 passed, 120
failed, 1 skipped** in 11 minutes. The failures are a version mosaic, not regressions: tests
from one branch call APIs that exist only on unrecovered branches (`Engine.gate`,
`_scale_hold`, `donor_k`, `hpc_encode_window`), 48 tests read recorded results from the
owner's `~/.cache/scratch` that did not survive, and a determinism golden hash no longer
matches the merged engine. There is no `AGENTS.md`, no safety lint and no README besides the
recovery note.

**reflex-layer** is a measurement-first project with one finished experiment. A Haiku
`routine-scanner` answered 49 of 56 Django lookups fully correctly and was never confidently
wrong; an `ast` script is exact by construction. There is also a prior-art review, a
no-deletion lint and a quarantine tool. Its deterministic toolkit was planned but not yet
built, and the transcript analyzer is its stated next step.

**~/.agents** (the owner's workflow suite, guide only) already routes work by tier: Tier 0
no model, then Haiku, Sonnet, Opus. It carries a stricter safety lint than reflex-layer's, and
a thrash detector that bounds edit→fail→edit loops *from outside the model*. That last one is
the executive idea in miniature, and its stated rationale is this project's: "a bound on a
repeated loop has to constrain the controller from outside it."

## Duplicated concepts, and who owns each now

| concept | where it existed | owner from now on |
|---|---|---|
| route to the cheapest tier that is verifiably correct | agents `AGENTS.md` (prose), reflex-layer README (principle) | reflex-layer measures each tier; brain-sim enforces the ladder at runtime; the agents suite stays the human-workflow version |
| no-deletion lint | agents `tools/safety-lint` (stricter), reflex-layer `tools/safety_lint.py` (weaker) | reflex-layer, upgraded to the stricter version plus one new rule; brain-sim is linted by it |
| removal = quarantine | agents rm-guard shim, reflex-layer `quarantine.py` | unchanged for humans; inside capabilities, `Workspace.quarantine` and the sandbox's diversion |
| loop bounding / thrash | agents thrash detector (hook on Claude Code) | brain-sim: rejected-plan memory and deliberation budgets per subgoal |
| persistent state files | agents `.agent/state.json` schema | the executive's `state.json` follows the same conventions (JSON, ISO-8601 UTC, units in key names, JSONL logs) but is its own schema: cognitive state, not chunk tracking |
| spend accounting | reflex-layer `spend.jsonl` | the same file, once live model calls run |

## The boundary

```
            objective (a repository whose tests should pass)
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│ brain-sim / executive        (decides; never touches files)      │
│                                                                  │
│  state.json ── goals ─ subgoals ─ salience ─ unresolved questions│
│     │          world facts with freshness (tests, kept edits)    │
│     │          pending prediction (survives a crash)             │
│  loop.py ── observe → decide → act → predict → observe → evaluate│
│     │                     │                          │           │
│  operators.py ladder:  0 memory recall  2 skills  5 deliberation │
│  memory/  episodes.jsonl (exact recall)  procedural.json (priors)│
│  deliberation.py ── Scripted | Replay | Recording | ClaudeCLI ───┼──► model (no tools,
│                                                                  │    JSON schema only)
└──────────────┬───────────────────────────────────────────────────┘
               │ registry.invoke(capability, workspace, [one effect], **params)
┌──────────────▼───────────────────────────────────────────────────┐
│ reflex-layer / reflex        (does; cannot delete)               │
│  spec: effect ∈ {read_only, write_workspace, execute_sandboxed}  │
│        qualification ∈ {exact_by_construction, measured, unqual.}│
│  Workspace: root confinement, protected paths, snapshot→write,   │
│             undo = restore | quarantine move                     │
│  caps: py.definitions/callers/called_names/names_in_scope/       │
│        module_level_definitions, fs.read_span/replace_text/      │
│        restore, git.status, tests.run_pytest                     │
│  sandbox/pytest_boot.py: suite under test runs with deletion     │
│        diverted to quarantine, writes outside its run dir and    │
│        process spawning refused                                  │
│  bench/: evidence that a capability earns its tier               │
└──────────────────────────────────────────────────────────────────┘
```

The rule that makes the boundary hold: the executive holds no file handles and no shell. Every
read, write and test run is a registry call that grants exactly one effect. A skill that
means to read cannot write by accident, because its call grants only `read_only`.

## Preserve, modify, archive, replace

- **Preserve as-is.** reflex-layer's measurement method, its Experiment 1 results, its
  append-only results and its quarantine tool. brain-sim's `SPEC.md`, plant code, plant tests
  and `docs/recovery/`, frozen at their recovered paths (DECISIONS: not moved while recovery
  is open).
- **Preserve the method, not the code.** From brain-sim: predeclared kill tests,
  never-trained baselines, labelled proxies, no bar lowered to pass, and acceptance ≠
  execution. The executive applies the last one directly: an edit is "pending" until a fresh,
  sandboxed test run evaluates its prediction.
- **Modify.** reflex-layer's `safety_lint.py` is now the stricter suite version, takes a ROOT
  argument, and gains a rule against `TemporaryDirectory`/`NamedTemporaryFile` cleanup in
  project code (it caught one in this pass). reflex-layer's `AGENTS.md` invariant 4 now allows
  write capabilities, but only snapshot-first, in a caller-granted root, and never deleting.
  `make_questions.py`'s `ast` index became the library `reflex/caps/pyindex.py`; the benchmark
  is untouched.
- **Archive later.** The plant moves to `legacy/` with `git mv` once the owner closes
  recovery. Nothing is moved now.
- **Replace.** Nothing of the plant is reused as executive machinery. Neurons, STDP and
  regions have no role here, and keeping brain vocabulary for ordinary mechanisms would hide
  what they are (see the adversarial notes below).

## First milestone, as built

> The executive accepts "make this repository's tests pass", represents it as a goal with one
> subgoal per failing test, runs the suite through the sandboxed reflex, fixes what known
> skills can fix with no model, calls a model only when no cheaper operator applies, rolls
> back any edit whose predicted effect is contradicted, and declares success only on a fresh
> run where every collected test passes.

Implemented and tested in `executive/` (13 tests, `tests/test_executive/`) and `reflex/`
(15 tests). `python -m executive bench` runs nine demo tasks; results are in
`bench/results/executive_demo.jsonl`.

## Adversarial notes: what is thin, redundant or better done elsewhere

1. **Most "cognitive" words here are ordinary software.** Salience is a float that orders
   subgoals. Episodic recall is memoization keyed by a hash. Procedural memory is a counts
   table, and the planner is a priority rule list. That is deliberate and fine, but nothing
   here yet *needs* the brain framing. The parts that do real work are the explicit
   prediction recorded before acting, judged against a fresh observation, plus rollback.
   Test-driven repair tools already have these (Agentless, SWE-agent). The difference worth
   testing is that the control loop is deterministic code and the model is called only at
   impasses.
2. **The two hand-written skills duplicate existing deterministic tools.** IDE quick-fixes,
   pyflakes/ruff (F821, undefined name) and `autoimport` already find undefined names and
   missing imports. The better move is to wrap such tools as reflex-layer capabilities after
   qualifying them, not to grow hand-written skills. The two skills exist to exercise the
   ladder, not as a library.
3. **Whether skills save anything depends on frequency, and that is unmeasured.** If
   NameErrors are 1% of real failures, the skill tier is noise. reflex-layer's planned
   transcript analyzer is the instrument that says which mechanical sub-tasks recur in the
   owner's real sessions. It should pick the next skills, not intuition.
4. **A cold deliberation call may cost more than a warm Claude Code turn.** Claude Code
   re-reads its context at the cache-read rate (0.1×, reflex-layer `PRIOR_ART.md`). Each
   executive call is a fresh, small prompt with no cache. Fewer calls is not automatically
   cheaper. Only a paired, cost-metered comparison settles it.
5. **The sandbox will reject real suites.** It refuses every subprocess and every write
   outside its run directory, so suites that spawn processes or write fixtures into the repo
   will fail inside it for reasons that are not bugs. The executive will then see failures
   that are not there. An OS-level sandbox (bubblewrap with a writable overlay) is the
   realistic next layer. The audit hook is not a boundary against hostile native code.
6. **Memory recall is exact or nothing.** It turned a model-dependent fix into a model-free
   one only because the second repository was byte-identical to the first. That is the floor,
   not generalisation. Cognitive compilation (an episode becoming a reusable skill) is not
   implemented.
