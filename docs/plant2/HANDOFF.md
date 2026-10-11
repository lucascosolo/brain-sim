# plant2 handoff (2026-10-11, updated about 04:25 UTC)

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

- **P2-E4 is complete.**
  - All five gated seeds (16-20) are valid. Verdict: ONLINE INDEX FAIL + HABITUATION FAIL +
    RECOVERY FAIL (e756252), as predicted. Content holds everywhere.
  - Every gated seed's reported arms and post-verdict diagnosis are committed, with every
    replay exact.
  - The independent results review (methodology, code, and constructive and skeptical
    north-star lenses) is running as workflow wf_e473a6a1-d25. Then: write the Result and
    addenda into the contract (append-only), the STAGES row, and the report to the owner.
  - Wording the owner asked for: "no pass in 1,500 joint simulations (95 % upper bound about
    0.002)", not "P(PASS) = 0".

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

- **The contract is frozen** at bc28cd9.
- **The driver** (`plant2/experiments/p2_e5_structured.py`) was written on side branch
  plant2-p2e5-driver. It had an implementation review (no blocker; the independent
  recomputation matched exactly) and a fix-check. All findings are acted on and in the ledger.
  It was merged at bf77a17. The plant2 tree is now dc16f182.
- **Exploration seeds 44-45** are running on that tree. Logs are in
  `~/.cache/brain-sim/plant2/p2_e5/explore_{44,45}.log`.
- **When both seeds are done:**
  1. commit the records;
  2. run `python -m plant2.experiments.p2_e5_structured predict`;
  3. append "Predictions from the real driver" to the contract, append-only;
  4. commit;
  5. run gated seeds 21-25, two lanes, once each;
  6. run the verdict, then a review.
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
