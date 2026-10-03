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
