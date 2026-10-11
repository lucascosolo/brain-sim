# plant2 handoff (2026-10-11, updated about 04:50 UTC)

This is the state of work for whoever continues, human or agent. Branch `plant2-stage1`; nothing is
merged to `main` without the owner saying "merge".

## P2-E4 (online memory): closed

- **Verdict:** ONLINE INDEX FAIL + HABITUATION FAIL + RECOVERY FAIL on 5/5 valid gated seeds
  (e756252), as predicted.
- **Records and write-ups:**
  - the Result and post-review readings, appended to `docs/plant2/P2-E4-online-memory.md`
    (89d5bde, 0a42d09);
  - the gated diagnosis, scored against its predictions, with a correction to the exploration
    write-up (`docs/plant2/P2-E4-diagnosis-plan.md`, 0a42d09);
  - the results review (`review/plant2/P2-E4/results-*.md`), all 32 findings in the ledger;
  - the STAGES row;
  - the evaluation for the owner, `docs/plant2/EVAL-after-P2-E4.md` (fd7c753).
- **Wording the owner asked for:** "no pass in 1,500 joint simulations (95 % upper bound about
  0.002)", not "P(PASS) = 0". High-load failure is not a failure to store. The open question is
  keeping access while writing accurately.

## P2-E5 (structured items): in progress

- **Status of the pieces:**
  - **The contract** is frozen at bc28cd9. M = 1,000 is gated: the contract allowed the owner to
    restrict gating to M = 500 only before the freeze, so that question is closed.
  - **The driver** was merged at bf77a17, after an implementation review and a fix-check. The
    plant2 tree is dc16f182. Nothing under `plant2/` may change before the gated seeds are done,
    and untracked files count as dirty.
  - **Exploration seeds 44-45** are running the reported arms (s100, s80, s40, pooled, F40,
    online). Logs are in `~/.cache/brain-sim/plant2/p2_e5/explore_{44,45}.log`. Commit
    `bench/results/plant2.jsonl` as records arrive.
- **When both seeds print "reported arms done":**
  1. Commit the records.
  2. Run `PYTHONPATH=. .venv/bin/python -m plant2.experiments.p2_e5_structured predict`. This
     writes the `power_predictions` record.
  3. Append "Predictions from the real driver (exploration seeds 44-45)" to the contract. It must
     be append-only, because the guard requires the frozen contract to be a byte prefix of
     HEAD's.
  4. Commit, so that the tree is clean and the record is in HEAD.
  5. Run gated seeds 21-25, two lanes, once each: `... p2_e5_structured run --seeds N --gated`.
     Run-once markers are in `~/.cache/brain-sim/plant2/p2_e5/`. Commit records as they arrive.
  6. Run `... p2_e5_structured verdict`, then an independent review.
- **The verdict text must say** that validity 5's `proj_current` and `inh_ok` parts, in the
  online arm's `slot_checks_ok`, hold by construction (P2-E4 code review, F1).

## Exploration readings so far (P2-E5, exploratory, not results)

| measure | seed 44 | seed 45 |
|---|---|---|
| gated arm, M = 500: index | fails C4-spurious (0.84) | passes |
| gated arm, M = 1,000: C2 / joint | 0.47-0.50 / 0-0.01 (both seeds) | |
| grid best at M = 500, plateau-set / main / R_3 store | 1.0 / 0.635 / 1.0 | 0.99 / 0.59 / 0.99 |
| grid best at M = 1,000, plateau-set / main / R_3 store | 0.665 / 0.07 / 0.69 | 0.69 / 0.06 / 0.705 |
| count AUC, M = 500 / 1,000 | 0.9995 / 0.995 | 0.9994 / 0.995 |
| s100 joint, M = 500 / 1,000 | 1.0 / 0.98 | 0.985 / 0.98 |
| s80 joint, M = 500 / 1,000 | 1.0 / 0.755 | 0.99 / 0.65 |
| s40 joint, M = 500 | 0.0 (C2 0.15) | 0.0 (C2 0.125) |

## Waiting on the owner (`EVAL-after-P2-E4.md`, last section)

None of these blocks P2-E5.
1. May burst-gated feedback eligibility (at least 3 continuation spikes) be the next contract?
2. May stabilising inhibition join a Stage 1 recurrent completion mechanism?
3. Where does forward-index cross-talk on correlated items go?
4. Should one latency bar cover index and content?
5. Optional: a reported replay of seed 18's M = 500 habituation copies.

No mechanism contract is drafted before P2-E5's verdict and these rulings.

## Owner guidance in force (`DECISIONS.md`, entries of 2026-10-10 and 2026-10-11)

- **The rulings** fix:
  - the Stage 1 clauses (online, structured input);
  - the Stage 3 gate;
  - the condition on Stage 2 inhibition;
  - the order: P2-E4, then P2-E5 before any Stage 2 work, with capacity scaling continuing.
- **Problems.** Learning-time contamination and operating-point instability are separate
  problems, fixed one mechanism per contract.
- **The plateau-set store** is an upper-bound diagnostic. It is not an acceptable solution.
- **The eligibility hypothesis** is for after P2-E4 and P2-E5. It does not license modifying the
  current experiments. Eligibility must be derived locally.
- **Hard rules:**
  - no rm or deletion code;
  - the original plant stays frozen;
  - results are append-only;
  - no parameter rescue;
  - no merge without the owner.
