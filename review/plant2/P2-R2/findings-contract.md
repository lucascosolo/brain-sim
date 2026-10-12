# P2-R2 conditional contract review

Reviewed only `docs/plant2/P2-R2-degree-null-DRAFT.md`, before selection, implementation, or simulation. This is a design review, not verification of the cited papers or runtime estimates.

**Disposition: sound explanatory design, subject to the activation correction and two precise decision-rule clarifications below. No additional arm or simulation is required for this review.**

1. **Make activation match the authorization.** The opening currently permits selection after E6's seed101 result and mandatory evidence are recorded, regardless of the result. Require all of: an observed **FEASIBILITY FAIL under E6's frozen seed101 screen**, completion of its mandatory evidence, termination of E6 simulation processes, and explicit lead selection followed by the R2 contract freeze. E6 PASS, an integrity INVALID, or merely recording a PARTIAL must not satisfy this predicate. This is the main material discrepancy with the authorized conditional third pass.

2. **Specify the structural-stop predicate without an ambiguous chain quantifier.** The draft saves diagnostics for both chains, but uses singular `D_null` and does not explicitly say whether the original-label contrast and 5000→10000 stability bounds apply to chain0 alone or separately to both chains. State the intended scope before implementation. The conservative reading is: at each load, each chain must meet the decorrelation and late-change checks, and the endpoint pair must meet the between-chain checks; any failed mandatory check stops LIF expenditure. This uses the already specified calculations and avoids selecting an interpretation after inspecting them. These remain heuristic adequacy checks, not proof of mixing.

3. **Require an original failure for the “failure persists” label.** Add `C2_original < 0.90` to label3. As written, an original score of0.91 followed by a null score of0.88 with small joint change could be labelled persistent failure, although the original C2 passed. Such a case belongs in MIXED/INTERMEDIATE. This is a logical labeling correction, not a new effect-size threshold.

**What is adequate as written**

- The block trade preserves every row size and every line count within each100-item block, hence the evaluated prefix margins and the oldest100 group's counts. It deliberately changes finer timing and co-occurrence. The estimand accurately names that joint intervention and avoids attributing a unique causal share to frequency or correlation.
- The fixed chain0 endpoint, independent diagnostic chain1, counted no-change trades, fixed sampling budget, and prohibition on extension or endpoint selection avoid performance-driven null selection. Reporting structural failure before LIF expenditure is legitimate; retain that outcome without interpreting neural effects.
- The small direct-versus-adapter parity check plus full-size original input digest is sufficient for the wrapper question. “Untouched RNG states” should mean the adapter does not perturb those streams: their states must match after20 episodes, not remain at initialization.
- Changed sensory spikes, eligibility counts, and subsequent coin-array alignment are disclosed correctly. Paired episode indices still support descriptive common-seed contrasts; they are not identical cue/content interventions. No replacement coin scheme or extra full-size sham is needed.
- Separate recall/specificity/joint outcomes, oldest-item results, activity/state diagnostics, and each arm's own-raster content replay prevent the main interpretation errors. Two seeds provide screening replication, not a capability gate.
- The20-minute ceiling, minute18 launch stop, prelaunch feasibility estimate, retained partial evidence, and ban on abbreviated replacement protocols are clear. Fit remains a measured-runtime judgment; this review has not established it.

The contract can be shortened by consolidating repeated no-tuning and no-capability-claim language. Preserve the activation predicate, exact null algorithm, structural checks, stream caveats, ordered labels, and resource-stop rules unchanged in substance. No further review round is needed if the three corrections above are applied before conditional selection and freeze.
