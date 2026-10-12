The frozen FAIL verdicts remain supported by the committed records. The main new problems are causal attribution and several claims in the evaluations—not evidence that the original gated numbers were computed incorrectly.

1. **The pooled control does not preserve per-line frequencies.**  
   `docs/plant2/P2-E5-structured-items.md:194,203` calls it line-frequency matched; `plant2/experiments/p2_e5_structured.py:102` shows why this is inaccurate. Main items sample from their own prototype; pooled items sample uniformly from the union of prototypes. Lines belonging to multiple prototypes consequently lose their exceptional load.

   I independently regenerated all items from the contract’s pinned NumPy streams. The five sibling-overlap means match the recorded validity values.

   At M = 1,000:

   | Seed | Prototype-union load SD, main / pooled | Maximum line load, main / pooled | Mean load on lines in ≥2 prototypes, main / pooled |
   |---|---:|---:|---:|
   | 21 | 15.45 / 7.31 | 144 / 83 | 96.0 / 56.8 |
   | 22 | 13.74 / 7.65 | 147 / 82 | 94.5 / 55.1 |
   | 23 | 13.36 / 7.17 | 137 / 81 | 92.9 / 56.7 |
   | 24 | 13.79 / 7.59 | 137 / 83 | 93.3 / 58.1 |
   | 25 | 14.77 / 7.39 | 148 / 89 | 94.4 / 56.5 |

   Reproduction: generate ten sorted 100-line prototypes using `default_rng([seed,20,10])`. For each k = 1…1,000, main uses `default_rng([seed,21,10,k])`: first 40 of a permutation of `P[k % 10]`, followed by first 60 of a permutation of its complement. Pooled uses `default_rng([seed,23,k])`: choose 40 uniformly from prototype union U, then 60 from the complement of `P[k % 10] ∪ chosen40`. Count appearances with `bincount`; SD uses `ddof=0`.

   For a line belonging to c prototypes, its expected main load is:
   \[
   100c(40/100)+100(10-c)(60/3900).
   \]
   Thus multiplicity alone creates expected loads of approximately 53.85 for c = 1 and 92.31 for c = 2.

   **Implication:** main-versus-pooled improvement mixes removal of sibling structure with flattening of the load distribution. The predeclared pooled labels remain correctly calculated, but “correlation-attributable” is not a clean causal isolation. Pooled failure still shows that the particular sibling structure is unnecessary for failure under that arm.

2. **Feedback-only changes do not guarantee identical O4/O5 results.**  
   `review/plant2/P2-E4/results-northstar_constructive.md:36` explicitly includes O4/O5 among bit-identical criteria. `docs/plant2/EVAL-after-P2-E4.md:135` consequently promises inherited HABITUATION FAIL.

   Source contradicts that guarantee. `p2_e4_online.py:416` defines `both = index_recall_pass AND content_joint`. Lines 622–631 use `both` to construct habituation eligibility, late counts, recovery and collateral outcomes; `hab_criteria` then scores O4/O5 from them.

   This matters in existing data: across 50,000 repeated-copy presentations in committed `hab_items`, **1,009 pass index recall but fail `both`**, including **103 late-window presentations and six first presentations**. A content change can therefore change the composite counts and estimability. Pure memory outputs and the underlying memory-recall decrement remain unchanged; O4/O5 must be rescored.

3. **The evaluations confuse online-written stores with online retrieval.**  
   `docs/plant2/EVAL-after-P2-E5.md:58` reports burst-gated performance of 0.93–0.97 “online,” against 0.05–0.10. Those are **settled twin-A readouts of stores learned online**. The existing system’s actual M = 500 online-block joint is 0.475–0.575. `p2_e5_structured.py:898` explicitly records the quoted figures under `twin_A`.

   This supports cleaner writing under the online learning schedule, not the claimed online retrieval improvement.

4. **“Persisted rasters” do not cover the proposed replay.**  
   All **28 unique E4/E5 cache paths referenced in the committed JSONL are absent** here. I did not verify their hashes or recompute raw spike-level outcomes.

   More fundamentally, `EVAL-after-P2-E5.md:76` recommends replay on persisted E4/E5 rasters including E4’s duty arm, but:
   - E4’s `dump_logs` and `run_seed` persist slot summaries, not the continuation spike counts/rasters needed for burst-selected stores.
   - E4’s duty arm persists aggregate results.
   - E5’s `persist()` saves gated-arm rasters and continuation data; `run_online_arm()` does not call it.

   Recovering the referenced files would therefore still leave some proposed replay inputs missing. Online/duty comparisons require faithful frozen-driver reconstruction and newly captured measurements.

5. **Frozen readout reverses the M = 1,000 failure ranking.**  
   Independently recomputed from committed grid summaries and online losses:

   | Load/readout | L_c range | L_i range | L_o range | Dominance |
   |---|---:|---:|---:|---|
   | 500, grid best | 54–74 | 0 | 12–30 | Contamination, 5/5 |
   | 500, frozen | 144–161 | 0 | 12–30 | Contamination, 5/5 |
   | 1,000, grid best | 110–126 | 39–54 | 65–79 | Contamination, 5/5 |
   | 1,000, frozen | 28–35 | 145–152 | 65–79 | Index, 5/5 |

   These are operational losses, not independent causal contributions. L_c and L_i partition a content shortfall using selected readouts; L_o uses different cues and a frozen readout. S1’s forward-index failure is independent of feedback-write choice regardless of this ranking.

6. **Additional factual overstatements should be corrected prospectively.**
   - `EVAL-after-P2-E5.md:30,101`: approximately 100 items is **family size**, not average prototype-line load. Regenerated prototype-union means are **57.64–58.66 items**.
   - `STAGES.md:85`: prototypes have **100 lines**; each main exemplar retains **40**, replaces **60**, and shares approximately 17 with a sibling. “60-line prototype” is wrong.
   - `EVAL-after-P2-E4.md:27`: “never both” is too strong. Seed 18’s settled twin B has memory recall **0.955** and content joint **0.915**. The defensible claim is that no tested regime satisfies the complete frozen, all-seed requirement.
   - `EVAL-after-P2-E5.md:27` and the Result’s “no store” language should say **none of the tested stores/readout points**. The plateau-set reference is explicitly not a mathematical upper bound. The separate argument that feedback-only changes cannot repair S1 remains sound.
   - `EVAL-after-P2-E4.md:143`: failure of one burst threshold would not establish an architectural impossibility or uniquely require an internally generated encode/retrieve state.

7. **Checks possible from the surviving evidence matched.**  
   I independently checked all 80 E5 criterion-vector bits against recorded counts, 20 S2/S4 counts against persisted per-cue bit strings, ten count AUCs from histograms, and the Part B arithmetic. E4’s embedded item summaries reproduce all O4 eligibility/habituation counts, O5 recovery counts, and recovery discordance **57:2** versus collateral **4:1**. Exact beta-binomial recovery estimability is **0.8311707** for seed 18’s 205/250 control rate; 203/250 gives **0.7936469**.

   Recombining recorded diagnosis summaries gives E4 C1 at 75 ms of **0.955, 0.970, 0.965, 0.965, 0.965** for seeds 16–20. These are aggregate recomputations, not raw replay. Ledger counts match the close-outs: E4 27 accepted/5 deferred; E5 27 accepted/3 deferred.

8. **Independent failure loci and highest-value falsifier.**  
   Same-raster store swaps isolate a feedback-store contribution; unchanged-synapse state comparisons establish a regime-dependent access contribution. Forward-index errors cannot be caused by the feedback store because `rec` has no outputs. These are separable intervention targets, **not proven independent causes**: forward activity determines writers, and operating state affects both retrieval and contamination. Habituation plausibly shares accommodation dynamics with access failure; its composite labels additionally depend on content.

   With **index first and F = 10 canonical already authorized**, an exact-degree shuffle can be reserved as a **distinct diagnostic third pass after mechanism failure**, not an additional gate or reason to delay implementation. Use binary item–line incidence swaps preserving exactly 100 lines per item and every line’s total count; keep plateau keys and frozen scoring unchanged. Compare C2/C4-spurious and main/plateau-set content against the structured arm.

   This directly tests whether failure persists after disrupting family organization without flattening marginal loads. Predeclare swap procedure, mixing checks and repetitions. Such shuffling disrupts higher-order correlations while preserving marginals; it **does not guarantee elimination of every dependency**. A remaining failure supports a marginal-load limitation under that null; improvement supports a contribution from organization beyond those marginals.
