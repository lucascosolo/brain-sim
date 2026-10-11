# plant2 handoff (2026-10-11, updated about 02:40 UTC)

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

## Progress since the first handoff (00:35 UTC)

- **Steps 1-4 are done.**
  - The exploration reported arms are committed (1a9ed2d, a4b6b41).
  - The diagnosis on seeds 42-43 is valid (0 mismatches), committed (ba97fcc, 78b9251) and
    written up in the plan (614246b).
  - The predictions are committed (`power_predictions`; P(PASS) 0) and appended to the contract
    (124ecb2).
- **Step 5 is running.** Seeds 16-19 have their gated records committed: all valid, all
  failing. Gated seeds:
  - lane A runs seeds 16, 18 and 20;
  - lane B runs seeds 17 and 19;
  - logs are in `~/.cache/brain-sim/plant2/p2_e4/gated_lane{A,B}.log`, with start markers
    written for 16 and 17;
  - commit the `kill_test_seed` and `reported_arms` records as they arrive.

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
   - The Result words the prediction as "no pass in 1,500 joint simulations (95 % upper bound
     about 0.002)", not "P(PASS) = 0".
   - The interpretation keeps the owner's distinction: high-load failure is not necessarily a
     failure to store; the open question is keeping access while writing accurately
     (`DECISIONS.md`, 2026-10-11).

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

- **The contract is frozen** at commit bc28cd9 (`docs/plant2/P2-E5-structured-items.md`), with
  its `power_reference` record. It went through a red-team, a verification, a fix-check and a
  final diff check. All are in `review/plant2/P2-E5/`, with every finding in the ledger.
- **What is gated:** S1 (P2-E2's C1-C4), S2 joint, S3 leak check and S4 oldest. The condition is
  s = 60 and F = 10, at M = 500 and 1,000, on seeds 21-25. Expected labels: STRUCTURED INDEX
  FAIL and STRUCTURED CONTENT FAIL.
- **Reported readings:**
  - Part B ranks the failures (contamination, index, operating point);
  - Part C measures own-cell identity from activity;
  - Part D tests contamination under continuous learning, on P2-E4's frozen driver;
  - Part E covers replication and confounds;
  - Parts F and G cover where contamination lands and the reported cue kinds.
- **Next:**
  1. Write the driver `plant2/experiments/p2_e5_structured.py` and its tests. Develop them in a
     side worktree or branch, because the main tree's plant2/ must stay clean until P2-E4's
     gated seeds have written all their records.
  2. Run an implementation review, then a fix-check.
  3. Freeze the plant2 tree, run exploration on 44-45, predict, then gated 21-25 once each.
- **Exploratory finding from the fix-check** (in the contract's Scope and in `DECISIONS.md`): on
  structured items the online state reads the same contaminated store far better than the
  settled state, with content 0.525-0.58 against 0.035-0.055, while index access falls. That is
  the owner's trade-off.
- **Open questions for the owner** (they do not block anything):
  - whether M = 1,000 should be gated now;
  - whether the activity-gated write may be contracted;
  - how to treat forward-index cross-talk.

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
