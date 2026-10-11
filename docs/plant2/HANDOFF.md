# plant2 handoff (2026-10-11, about 00:35 UTC)

This is the state of work for whoever continues, human or agent. Branch `plant2-stage1`; nothing is
merged to `main` without the owner saying "merge".

## P2-E4 (online memory): where it stands

- **Contract.** `docs/plant2/P2-E4-online-memory.md`, frozen at commit cd17cde.
  - The only edit allowed is an appended predictions section. The guard checks that the contract
    has only had lines added since cd17cde.
- **Frozen code.** plant2 tree 9152f1e4 (commit 0958956). Nothing under `plant2/` may change
  before the gated seeds are done; a change forces exploration to be redone.
- **Exploration seeds 42 and 43.**
  - The gated parts are done and their records are committed (737e8b1). Both are valid and both
    failed, as predicted.
  - The reported arms are still running as background processes. Logs are in
    `~/.cache/brain-sim/plant2/p2_e4/explore_{42,43}.log`. When each prints "reported arms
    done", commit `bench/results/plant2.jsonl`.
- **The diagnosis.** Plan in `docs/plant2/P2-E4-diagnosis-plan.md`, predeclared and corrected
  three times after owner review. Code in `analysis/p2e4_diagnosis.py`, outside plant2/.

## Next steps, in order

1. After the reported arms finish, commit the results file.
2. Run the diagnosis on the exploration seeds:
   `PYTHONPATH=. .venv/bin/python analysis/p2e4_diagnosis.py --seed 42`, then the same for 43.
   Commit the records.
3. Run `PYTHONPATH=. .venv/bin/python -m plant2.experiments.p2_e4_online predict`. This writes the
   `power_predictions` record.
4. **Append** a section "Predictions from the real driver (exploration seeds 42-43)" to the P2-E4
   contract, below the existing predictions. Never edit lines above it. Commit everything, so that
   the tree is clean and the record is in HEAD.
5. Run the gated seeds: `... p2_e4_online run --seeds 16 --gated`, and the same for 17-20. Two run
   in parallel (4 CPUs), about 80-120 min each under load. Each seed runs once; start markers
   live in `~/.cache/brain-sim/plant2/p2_e4/`. Commit the records as they arrive.
6. Run `... p2_e4_online verdict`, then an independent review workflow (methodology, code,
   north-star).
7. Run the diagnosis on the gated seeds (`--gated`). It runs only after the verdict.
8. Write the Result and the addenda into the contract (append-only), add the STAGES row, and
   report to the owner.

## Exploration readings so far (exploratory, not results)

| measure | seed 42 | seed 43 |
|---|---|---|
| online C1, M = 1,000 (bar 0.90) | 0.69 | 0.79 |
| content joint, M = 1,000 | 0.95 | 0.98 |
| never-probed cohort memory, M = 1,000 | 0.67 | 0.81 |
| eligible habituation items, M = 500 | 31 (22 habituated) | 22 (10 habituated) |
| eligible habituation items, M = 1,000 | 4 | 6 |
| recovery | passes | passes |
| settled twin A joint, M = 1,000: online store | 0.815 | 0.89 |
| same raster: P2-E3-protocol store | 0.98 | 0.99 |
| same raster: plateau-set store | 0.995 | 0.995 |
| replay against carried rec | exact | exact |
| stress, M = 2,000: recent C1 / joint | 0.28 / 0.30 | 0.35 / 0.20 |
| stress, M = 3,000: joint | 0.00 | 0.01 |
| writes during probes | 172 | 170 |

Habituation at M = 1,000 is not estimable (eligible below the minimum of 25), and the threshold
offset is 6.9 mV.

## P2-E5 (structured items)

- **The draft.** `docs/plant2/P2-E5-structured-items.draft.md`.
- **The red-team workflow** (run id wf_7b8a1dd3-6aa) was running at handoff. Its output is in the
  session's task output for w75o8iu23.
- **Then:**
  1. render the findings verbatim into `review/plant2/P2-E5/`;
  2. record the ledger decisions;
  3. revise the draft, including the owner's request for an online arm (reported, with no new
     mechanism);
  4. verify the revision, then freeze it as a contract.
- **Seeds.** Gated 21-25; exploration 44-45.

## Owner guidance in force (`DECISIONS.md`, entries of 2026-10-10 and 2026-10-11)

- **The rulings** fix:
  - the Stage 1 clauses (online, structured input);
  - the Stage 3 gate;
  - the condition on Stage 2 inhibition;
  - the order: P2-E4, then P2-E5 before any Stage 2 work, with capacity scaling continuing.
- **Problems.** Learning-time contamination and operating-point instability are separate
  problems, fixed one mechanism per contract.
- **The plateau-set store** is an upper-bound diagnostic. It is not an acceptable solution.
- **Hard rules:**
  - no rm or deletion code;
  - the original plant stays frozen;
  - results are append-only;
  - no parameter rescue;
  - no merge without the owner.
