# The plant2 research ledger

Started 2026-10-22 under the owner's autonomous research mandate of that day (recorded in
`DECISIONS.md`). This directory is the durable memory of the research program. It exists to
keep three things that an autonomous researcher tends to blur apart: **an idea that was
proposed**, **an experiment that was attempted**, and **a capability that was demonstrated**.
Each lives in its own file, with its own status vocabulary, and nothing moves between them
without a dated line saying why.

The contracts, results and reviews under `docs/plant2/`, `bench/results/` and `review/` remain
the primary record and are never edited to fit the ledger. The ledger is an index over them
with judgement attached; every number in it cites where it came from.

## The files

| file | what it holds | who edits it |
|---|---|---|
| `RESEARCH-MAP.md` | the current architecture and how each mechanism works; the capabilities actually demonstrated and their evidence; known limitations; architectural dependencies and invariants; what the experimenter still supplies | rewritten in place at each checkpoint, with a changelog at the end |
| `HYPOTHESES.md` | every hypothesis with rationale, expected outcome, confidence, evidence for and against, and the experiment that would settle it | entries are added and their status updated; an entry is never deleted, only closed |
| `EXPERIMENTS.md` | one entry per experiment: objective, code revisions, configuration, seeds, controls, results, failures, reproducibility, conclusions | an entry is appended when a contract is committed and completed when its result is recorded; old entries are corrected only by an appended erratum line |
| `BACKLOG.md` | the speculative research backlog: ambitious or unconventional ideas not yet ready for a contract, with what would have to be true for them to graduate | added to freely; an item graduates to `HYPOTHESES.md` or is closed with the reason |
| `ROADMAP.md` | the current research priorities and the reasoning behind them, updated at each checkpoint | rewritten in place, with the previous priority order kept in its changelog |

Working state for the current session (`.agent/state.json`) is not part of the ledger and is
not committed.

## Status vocabularies

**A hypothesis** is exactly one of: `proposed` (stated, no experiment yet), `under_test`
(a committed contract names it), `supported` (a predeclared test came out as predicted, on the
seeds and loads the contract named), `refuted` (a predeclared test came out against it),
`mixed` (supported in some predeclared conditions and refuted in others), `withdrawn` (the
record itself retracted it, usually in errata), `unresolved` (tested, but the experiment could
not decide). A hypothesis that was tested only on development seeds, or only by a reported
replay, is `under_test` or `mixed`, never `supported`.

**An experiment** is exactly one of: `contracted` (contract committed, no code), `implemented`
(code committed, not yet run), `running`, `complete` (every predeclared measurement exists and
every validity check holds), `invalid` (ran, but a validity or integrity check failed; its
numbers are descriptive only), `partial` (stopped by a resource ceiling with some loads
complete), `abandoned`. Its result label is the contract's own wording (PASS, FAIL, FEASIBILITY
FAIL, INVALID, reported-only) and is copied, never paraphrased upward.

**A capability** appears in `RESEARCH-MAP.md` only when it is `demonstrated`: a gated,
predeclared test passed on fresh seeds (five of five unless the contract said otherwise)
against a never-trained or shuffled control, with the scope conditions (item distribution,
load, settled or online, seeds) written beside it. Anything weaker is one of `observed` (a
valid measurement on a development seed or a single contrast), `reported-only` (a replay on
persisted rasters, not a live system), or `hypothesised`, and lives in `HYPOTHESES.md` or
`EXPERIMENTS.md`, not in the capability table.

**A failure** is classified, because each kind calls for a different response: a
`failed_hypothesis` (the idea was wrong; do not retune it), a `failed_implementation` (a code
defect; fix and rerun under a new attempt id), an `inadequate_experiment` (the design could not
answer the question; redesign), an `unresolved_result` (ran cleanly, did not decide), an
`integrity_incident` (evidence lost or unverifiable; the attempt is invalid regardless of its
numbers), or an `interpretive_error_corrected` (a claim later withdrawn in errata).

## Rules of the ledger

1. A number without a source path is not in the ledger. Precision is the source's precision.
2. A result's label (gated, exploratory, reported-only, INVALID, descriptive, post hoc) travels
   with the number everywhere it is quoted.
3. Proposed, attempted and demonstrated never share a table.
4. Nothing is deleted. Corrections are appended errata with a date; superseded roadmap orders
   stay in the changelog.
5. Before any new contract is drafted, `HYPOTHESES.md` and `BACKLOG.md` are consulted and the
   new contract names the hypothesis ids it tests.
6. Identifiers are stable: experiments keep their contract ids (`P2-E6`, `P2-R2`);
   hypotheses are `H-nnn`; backlog items are `B-nnn`; neither is reused.
7. The owner's rulings in `DECISIONS.md` bind the ledger; where the ledger and a ruling
   disagree, the ruling stands and the ledger is corrected.
