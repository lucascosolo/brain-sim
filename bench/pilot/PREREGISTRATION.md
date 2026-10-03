# Pilot: does executive-first save model spend without losing quality? (predeclared 2026-10-03)

Written and committed before any run of this pilot. Results go to
`bench/results/pilot_2026-10-03.jsonl`, append-only. This file is not edited after the first
run; any change is a new dated section below.

## Owner's criteria (2026-10-03, verbatim intent)

1. The reflex/brain layer must not take on tasks larger than it can handle and screw something up.
2. It should save LLM tokens and turns without affecting output quality.

## Task set

`tasks.py`: ten seeded bugs in `ledger_clean/` (a 5-module library, 22 visible tests, 6 held-out
tests in `tests_hidden/` that are never present during a run). Two are predicted to need only
skills (t01 name typo, t02 missing import); eight are predicted to need deliberation. Each
mutated task fails at least one visible test; checked mechanically before this file was written.

## Arms

- **agent**: plain `claude -p` agent in the task repo. Prompt: "The test suite in this repository
  fails. Fix the code so that all tests pass. Do not modify, add or delete test files. Run the
  tests with `python3 -m pytest -q`." Tools Read, Edit, Glob, Grep and Bash restricted to
  `python3 -m pytest` (probe-checked: other Bash is denied); `--permission-mode dontAsk`,
  `--max-turns 40`, `--max-budget-usd 1.00` (Haiku) / `2.00` (Sonnet).
- **hybrid**: the executive runs first with a Haiku `ClaudeCLIDeliberator` (2 deliberations per
  subgoal, 4 per task, scope guard 2 files / 30 lines). If it ends blocked, the agent arm runs on
  the repository the executive left, with the identical prompt. Cost = both parts.

Every run starts from a fresh copy and a fresh, empty executive memory (memory reuse is not
what this pilot tests).

## Experiments

- **E2 (architecture, same model):** agent-Haiku vs hybrid with Haiku handoff. 10 tasks × 2 reps per arm.
- **E3 (realistic routing):** agent-Sonnet vs hybrid with Sonnet handoff (executive deliberation
  still Haiku). 10 tasks × 2 reps per arm.

## Measures (computed by the harness, never by an arm)

- **correct**: visible and held-out tests all pass on the final repository (held-out tests are
  copied into a separate evaluation copy; the run's repository is never touched by evaluation).
- **tests_modified**: any file under `tests/` or `conftest.py` differs from the clean copy.
- **harm**: held-out or visible tests that passed on the mutated repo before the run and fail
  after it (collateral damage), or tests_modified.
- **claimed_done**: executive status `complete`; agent run ended without error. **false_done**:
  claimed_done and not correct.
- **cost_usd** (CLI-reported list price), **llm_turns** (agent `num_turns`; executive deliberation
  calls), wall seconds.
- **executive_alone**: in hybrid runs, tasks the executive completed without handoff, and
  whether each is correct (an executive-completed task that fails held-out tests counts against
  criterion 1).

## Decision rules, fixed now

- Criterion 1 **fails** if any executive action (not the handoff agent's) causes harm, or if the
  executive claims `complete` on a run that is not correct.
- Criterion 2 **quality part fails** in an experiment if hybrid has fewer correct runs than
  agent. A difference of one run out of twenty is reported as "not distinguishable at this n",
  not as parity proven.
- Criterion 2 **savings part** holds in an experiment only if hybrid's total cost and total
  llm_turns are both lower than agent's.
- Predictions (to be scored, not to steer): hybrid costs less in both experiments; t01 and t02
  need zero deliberations; the executive completes at least half the deliberation tasks alone
  with Haiku; no executive harm.

## Addendum, 2026-10-03, written while E2 was running and before any E2 result was read

Owner: task success and output should look about the same as, or better than, the LLM alone.
Task success is already the primary quality rule (correct runs, held-out tests). Added as a
**secondary output-quality measure**, computed from the run directories by `analyze.py`:
- **matches_reference**: every file under `ledger/` is identical to `ledger_clean/` after the
  run (the seeded bug was reverted exactly, nothing else changed);
- **diff_lines_vs_reference**: changed lines between the final `ledger/` and `ledger_clean/`
  (0 is ideal; larger means extra or different changes).
Reported per arm next to the primary result. It does not change the decision rules above.

## E2 result and E2b (predeclared 2026-10-03, after E2, before E2b)

**E2, as scored by `analyze.py E2`.** 20/20 correct in both arms; no harm, no test edits, no
false completion in either arm; hybrid 96 LLM turns against 151; hybrid **$0.90 against
$0.55**. Criterion 1 holds, quality holds, **savings fails**. Cause, from the traces: for
failures inside methods (t04, t05, t06, t09) the projection held only the test file, so Haiku
invented source text. The exact-once edit guard refused all 15 such edits (no harm), and
the run then paid for the handoff agent too. Default-effort Haiku spent 4k-12k output tokens
per call.

**Changes for E2b**, all in `executive/` with tests:
1. Evidence: the projection also includes workspace modules imported by the files in the
   traceback, and uniquely defined methods the failing frame calls.
2. No editable file in evidence: no model call; hand off at once.
3. The model returns no edits: treat as abstention; hand off without retrying.
4. The deliberator runs `--effort low`.

**E2b:** the same 10 tasks × 2 reps, both arms rerun (paired in time), agent model Haiku.
The decision rules above are unchanged. **E3** then runs as predeclared, with the E2b executive.

## E5: repair at scale (predeclared 2026-10-03, before any E5 run)

Owner: test where the architecture should be better suited, and see whether it can actively
beat the LLM. Hypothesis: when one change breaks many things mechanically (the fallout of a
careless rename or move), deterministic skills fix most of it for free, and the model is
needed only for the few real bugs. An agent instead pays a round trip per fix.

**Corpus.** `make_fleet.py` (seed 20261003) → `fleet_clean/`: 30 modules over `fleet/util.py`,
one visible and one held-out test each. Task `s01_refactor_fallout` (`fleet_tasks.json`) has
12 dropped imports, 12 misspelled locals and 2 logic bugs, so 26 visible tests fail (verified
on a fresh copy without bytecode). Each run starts from a fresh copy and an empty memory.

**Arms.** Same prompt and tools as E2. Fair limits for the larger job: the agent gets 80 turns
and $2 (Haiku) / $4 (Sonnet); the executive gets 200 steps and the E2b deliberation settings.
- **E5h**: agent-Haiku vs hybrid with Haiku handoff, 2 reps each.
- **E5s**: agent-Sonnet vs hybrid with Sonnet handoff (deliberation still Haiku), 2 reps each.

**Rules.** The decision rules above, unchanged. The executive **beats** the agent on this task
if hybrid is correct in every run where the agent is, and costs less in total.

**Predictions (scored, not steering).** The executive resolves 24 of 26 subgoals with no model
and the 2 logic bugs with 1-2 deliberations each. Hybrid cost is at most 20% of agent cost in
both E5h and E5s. Agents finish correctly but use at least 25 turns.
