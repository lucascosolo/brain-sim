# Live experiments, 2026-10-03

Every number here was measured today with live `claude -p` calls (CLI list prices; $9.60 in
total, logged in reflex-layer's `bench/results/spend.jsonl`). Every experiment was predeclared
before it ran: `bench/pilot/PREREGISTRATION.md` here, and `bench/arena/PREREGISTRATION.md` in
reflex-layer. Raw rows are in `bench/results/pilot_2026-10-03.jsonl` and reflex-layer's
`bench/results/arena.jsonl`. Where a result led to a change, the change was tested in a new,
separately predeclared round; no earlier row was rewritten.

## The owner's criteria

1. The reflex/brain layer must not take on tasks larger than it can handle and screw something up.
2. Save LLM tokens and turns **without** affecting output quality. Task success and output
   should look the same as, or better than, the LLM working alone.

Quality is judged on **held-out tests** the arms never see, plus the visible ones. Output
similarity to the original correct code is a secondary measure (identical, or lines differing).

## Results

| exp | task set | LLM baseline | correct (agent / hybrid) | cost agent → hybrid | LLM turns | executive alone | rules |
|---|---|---|---|---|---|---|---|
| E2 | 10 ledger bugs ×2 | Haiku agent | 20/20 / 20/20 | $0.55 → **$0.90** (+65%) | 151 → 96 | 12/20 | savings **fail** |
| E2b | same, executive fixed | Haiku agent | 20/20 / 20/20 | $0.54 → $0.22 (−60%) | 149 → 18 | 20/20 | all hold |
| E3 | same | Sonnet agent | 20/20 / 20/20 | $0.58 → $0.23 (−61%) | 111 → 18 | 20/20 | all hold |
| E5h | 26-bug refactor fallout ×2 | Haiku agent | 2/2 / 2/2 | $0.58 → $0.33 (−43%) | 131 → 62 | 0/2 | all hold |
| E5b-h | **fresh** corpus (new seed), skill fixed | Haiku agent | 2/2 / 2/2 | $0.57 → $0.043 (−92%) | 129 → 4 | 2/2 | all hold |
| E5b-s | fresh corpus | Sonnet agent | 2/2 / 2/2 | $0.38 → $0.039 (−90%) | 121 → 4 | 2/2 | all hold |

No run in any arm edited a test file or claimed a false completion. The executive never broke
a previously passing test.

**Output quality.** E5b: hybrid output was byte-identical to the reference in 4/4 runs, the
same as the agents. On the ledger tasks, Sonnet's edits were reference-identical slightly more
often (E3: 18/20 against 15/20). Every differing hybrid edit was a behaviour-identical rewrite
(an extra local variable, or swapped `.replace` order). So: equal on success, near-equal on
minimality.

### Arena (reflex-layer Experiment 2): structural lookups on a novel codebase

| | reflex | Haiku `routine-scanner` | Sonnet agent |
|---|---|---|---|
| correct | 6/7, plus 1 correct abstention | 9/14 | 14/14 (adjudicated; 11/14 strict) |
| confidently wrong | 0 | **2** | 0 |
| cost / median latency | $0 / 0.04 s | $1.02 / 33 s | $2.46 / 18 s |

The reflex **beats the Haiku scanner** on quality: 558 call sites with aliases and shadows,
and 45 aliased subclasses. Against Sonnet it **ties** on quality on every question it
answers, and wins only on cost and latency. Sonnet also answered the receiver-type question
(324 method calls) that the reflex rightly refuses. The predeclared hybrid (reflex, else
scanner) therefore **fails** against Sonnet: the abstention went to the cheap tier, which got
it wrong. Lesson, recorded as a decision: an abstention escalates to the tier that can do the
job.

### E6: traps, where taking the task on is the mistake

- **Environment trap.** A correct module needs a subprocess, which the sandbox refuses. With
  the environment guard **off**, the executive rewrote that correct code in **2/2** runs. With
  it on, 0/6 runs touched it (E6, E6c), and every one was correct.
- **Contradictory tests.** The executive alone always rolled back and stopped (no harm, 6/6).
  But the hybrid with a **Haiku handoff broke 2 passing tests in 2/2 runs**, through the
  handoff agent; the Haiku agent alone did so 1/2. Sonnet did no harm in 4/4. Fix: two
  attempts that regress the same tests are treated as a suspected requirements conflict and
  escalated **to you**, with the question "Which should win?". E6c: 2/2 no harm, no agent
  call, escalated to a human, $0.05.

## What I conclude, and how sure I am

- **Criterion 1.** The executive *itself* never did damage in 92 live runs: no test edits, no
  broken tests, no false "done". Its refusals (exact-once edits, scope guard, sandbox) caught
  every invented or wrong edit. Two real gaps surfaced, and both are fixed and re-tested:
  editing correct code to dodge the sandbox, and handing a contradiction to a weaker agent.
  The remaining risk sits in whatever it hands off to. Its handoff choice is now part of the
  safety design.
- **Criterion 2.** Measured, and it holds here: equal success with 60-92% less spend and 84-97%
  fewer LLM turns. The largest gains come where the architecture fits (many mechanical
  failures, large exact lookups). On small single-bug tasks a well-equipped executive still
  saves about 60%, but only after the evidence-gathering fix. Before it, E2 cost *more*.
- **How far this generalises: not far yet.** The corpora are small and synthetic, I built them
  and the skills, and n is 2 per cell. E5b's fresh seed is the only out-of-sample check, and
  it is the same generator. Real repositories bring imports through installed packages, slow
  suites, flaky tests, subprocess-heavy tests (the sandbox refuses them, so they hand off), and
  failures with no clean traceback.

## Highest-value next steps

1. Run the executive on real failing commits from your own repositories (or a SWE-bench-style
   Python subset), paired with plain Claude Code, using these same rules.
2. Write a structured handoff brief (what was tried, what regressed) into the agent's prompt.
   E6 showed the executive's knowledge is lost at handoff.
3. Apply the arena routing lesson to your `routine-scanner`. For exhaustive lists, alias- or
   type-dependent questions, or large answers, call the reflex CLI first and Sonnet second, not
   Haiku. I did not edit your `agents` repo: it is read-only for me.
4. Swap the hand-written skills for wrapped, qualified existing tools (ruff/pyflakes for
   undefined names), measured the same way.
