# P2-R2 results: independent methodology and evidence audit

**Formal disposition: INVALID overall.** Seed 103 completed and meets the predeclared **MATERIAL STRUCTURE SENSITIVITY** definition. Seed 104 terminated INVALID when its final paired comparison attempted to read an empty combined artifact. Independently recovered seed104 data support the same numerical direction, but do not restore a valid second contract result or formal replication. No rerun, parameter change, journal repair or original-file overwrite was performed.

Reviewed the frozen contract `docs/plant2/P2-R2-degree-null.md` at 2454f06, driver/source manifest at `c7a5350b6a9c2359d39e4391b5e371901bf9e0ac`, `bench/results/p2r2.jsonl`, portable components under `bench/results/p2r2/`, and their raw archives. Both workers started under the shared clock at 2026-10-12T04:37:19Z. Seed 103 completed in 194.492 s; seed104 stopped in 198.318 s. This was an evidence/integrity failure, not a resource stop or unfavorable neural protocol result.

## Material evidence defect and authorized recovery

`bench/results/p2r2/seed104-ORIGINAL-M1000.json` is zero bytes. The final in-memory load aggregate records an expected 1,883,558 bytes and SHA256 `a16f1b9c209cccd202f3251ce7f931fe948f6284542ddc71d852ab7e47725a7d`. Two progress events are also absent: seed104 ORIGINAL/1000 `load_complete` and DEGREE_NULL/500 `load_started`. Later checkpoints, the final aggregate and component files remain. The failed `paired_load` at 104/1000 is additionally absent, as expected from the exception.

The recorded stage `DEGREE_NULL/1000/replay/assigned_A` is the last progress marker. The assigned-A replay and its artifact completed; the subsequent JSON read in `paired_evidence` fails. It would be inaccurate to describe the neural readout as having crashed. The inspected source uses exclusive creation for portable files, obtains descriptors after writing, and appends each journal record with one checked O_APPEND write. These observations do not establish the cause or actor behind the loss; no I/O root cause is assigned here.

Retained index and both content components, plus the final aggregate's replay timings with `learning_s` omitted, reconstruct the missing combined JSON **exactly**: the recorded byte count and SHA256 both match. At the lead's explicit request, three new exclusive artifacts preserve that recovery:

- `bench/results/p2r2-recovery/seed104-ORIGINAL-M1000-reconstructed.json`: exact historical bytes under a new name.
- `bench/results/p2r2-recovery/seed104-M1000-posthoc-paired.json`: independently computed comparison, explicitly INVALID/no formal replication.
- `bench/results/p2r2-recovery/seed104-recovery-provenance.json`: component hashes, expected/observed artifact state, reconstruction recipe, aggregate timing provenance and missing events.

The original remains zero bytes. Recovery does not manufacture the missing successful paired-stage event. Seed 103 has all 21 required stage receipts; seed104 has 20, missing `paired/1000`. Independently applying the overall stopping/status rules gives INVALID, no replicated label, and no formal both-seed deficit-removal assertion. The manifest preserves the 60-record worker-journal snapshot; the parent's later integrity-disposition append is separate.

## Verification scope

All 13 current source hashes match both runtime manifests. Of 60 distinct recorded artifact descriptors,59 match their files: all 21 raw archives, including the forensic checkpoint, and 38 of 39 portable JSON artifacts. The sole mismatch is the empty combined file above. Its new recovery copy also matches the expected historical hash.

Independently recomputed all 64 structural load/chain/snapshot summaries using integer overlap accumulation, and all 88 structural decision bits. Exact row/block/prefix margins, overlap histograms, lag means, D/Q/R, cumulative-count deviations and matrix hashes agree. Curveball chains were not rerun; attempted/changed-trade counters were checked for consistency, not independently replayed.

For all eight retained load datasets, including the reconstructed104 original component, independently checked 4,800 index rows and 9,600 content rows. Raw rasters reproduce every stored 100 ms first-spike trace and 50 ms own/spurious/total responder and spike count. Aggregate scores, age strata, absolute bars, joint index/content outcomes, content distributions and latency summaries agree. Independently regenerated inherited plateau/variable-length coin draws, exact forward stores, potentiation/depression, final RNG states, store degrees and eligibility-block counts for all 6,000 represented checkpoint episodes. Learned input prefixes match the prescribed original/chain0 matrices. All three recorded paired comparisons agree; the fourth is explicitly post hoc.

No full neural simulation, structural randomization or reconstruction-layer dynamics were rerun. Content scoring was verified from retained reconstruction counts. Recorded unchanged-learning-state checks and threshold capture were source-inspected; threshold trajectories were not independently simulated.

## Structural contrast is strong, but finite

Canonical M1000 chain0 endpoints:

| Seed | Original D → null D | Original Q → null Q | Active-line replacement, 1−R | Within-block cumulative max / RMS |
|---|---|---|---|---|
| 103 | 14.45394 → .00248 | 36.73036 → 18.90274 | 95.257% | 7 / .86565 |
| 104 | 14.39250 → −.00171 | 36.83363 → 19.15428 | 95.217% | 9 / .86611 |

Every original row retains 100 lines; every line's count is preserved exactly in each 100-item block and both load prefixes. Mean overlap stays 3.90948/3.93986, as forced by those degrees. Its agreement is not mixing evidence. Both chains pass the frozen endpoint, late-change and between-chain heuristics at both loads. F40 structural transfer also passes; no F40 neural trajectory was run.

`changed_entry_fraction` uses all binary matrix cells as denominator: it equals `.05 × (1−R)`. Values around 4.76% therefore mean replacement of about 95% of each episode's active lines, not a small perturbation. Finite-chain checks do not certify independent uniform sampling or removal of every higher-order dependency.

## Primary neural contrast

M1000 original → null counts; C1/C2/joint use 200 half cues, oldest bars use 100.

| Evidence status | C1 | C2 | Joint index | Oldest recall | Oldest specificity |
|---|---|---|---|---|---|
| 103, valid completed seed | 186 → 184 | 94 → 151 | 82 → 135 | 93 → 92 | 41 → 68 |
| 104, recovered post hoc; INVALID retained | 187 → 185 | 92 → 143 | 80 → 128 | 93 → 92 | 40 → 67 |

Seed 103 has Delta C2=+.285, Delta joint=+.265, Delta C1=−.010 and Delta oldest recall=−.010. It meets the ordered material-sensitivity definition. Null specificity=.755 and oldest specificity=.680 still fail the90% bars. C3 remains198/200. Null-only:original-only discordances are C2=74:17, joint=75:22 and recall=13:15; improvement is not itemwise monotonic.

Recovered104 yields Delta C2=+.255 and Delta joint=+.240, with both recall deltas−.010, numerically meeting the same definition. Its C2=.715 and oldest specificity=.670 remain below bar; C3=200/200. Post hoc discordances are C2=72:21, joint=69:21 and recall=12:14. These measurements support concordant descriptive evidence, not a restored replicated contract result.

The raw C2 bar-deficit fractions removed are .662791 on valid 103 and .579545 on recovered 104. These are fractions of the measured distance to .90, not fractions of a biological causal mechanism. Formal replication remains unavailable because104 is INVALID.

At M500, null C2=1.000 on both seeds and joint improves by .075. The recall safeguard matters:103 oldest recall falls .980→ .910, so its low-load material-gain flag is false despite better specificity. Seed 104's C1=.960→ .935 and oldest recall=.950→ .940 stay within allowance; its recorded low-load flag is true, subject to the seed's eventual INVALID status.

## Content and causal limits

| Seed/load | Inherited joint original → null | Assigned-A joint original → null |
|---|---|---|
| 103/500 | .115 → .980 | .945 → .990 |
| 104/500, retained INVALID trial | .120 → .995 | .925 → .995 |
| 103/1000 | .005 → .075 | .130 → .320 |
| 104/1000, recovered post hoc | .000 → .125 | .150 → .325 |

At1000, valid 103's inherited gain +.070 is below the declared .10 material-content threshold; recovered 104's+.125 crosses it. Assigned-A gains are +.190/+.175. All 1000 stores still fail absolute joint/oldest-content bars. At500, null inherited and assigned-A content pass their absolute bars. The prediction of large primary index gains and poor inherited content at 1000 holds for103 and is numerically consistent with recovered 104; it does not imply complete memory recovery.

The arms match A, episode schedules, novel items and positional cue masks. They do **not** match learned cue-line identities, actual sensory spikes, eligibility or later BTSP coin assignments. Eligibility block counts differ by up to 3 occurrences per line; RMS differences at 1000 are .24285/.24382. Coin draw counts differ on 713/722 episodes, beginning at episode 1/2, with final cumulative differences +338/−386 and maxima 950/1010. Learning-input and plateau RNG states match; final coin RNG states differ. These are contracted consequences of the input intervention, not grounds to call the arms spike- or coin-matched.

Operating states also change. On103, mean own responders fall 18.990→ 18.660 while spurious responders fall 21.195→ 7.410; mean assigned-cell threshold offset rises 5.89956→ 5.95175 mV. On104 the corresponding values are 18.495→ 18.500,20.405→ 7.685 and5.87096→ 5.88520 mV. Store densities barely change (.056938→ .056995 and.056579→ .056569). Fixed parameter values do not imply a fixed effective threshold or identical learned state.

The valid result shows sensitivity to the contracted block-constrained input intervention while substantial interference remains. It does not partition frequency and correlation into independent causal shares, prove frequency uniquely causes residual failure, or prove all dependence was removed. Content contrasts also combine changed learned feedback with changed own retrieval rasters. Assigned-A remains a supplied diagnostic store. No autonomous keys, online capability, related-unseen-example rejection, new learning mechanism, Stage1 completion or Stage2 authorization was established.

Suggested results statement: **R2 is formally INVALID because seed104 lost a combined evidence artifact before its final paired read. Valid seed103 shows material sensitivity to input grouping at fixed blockwise degrees, yet specificity and content still fail at 1000. Exact-hash recovery provides concordant post hoc104 evidence without restoring formal replication. Preserve the failure and recovered provenance; no rerun or gate rescue follows.**

Brief check of `docs/plant2/RESULTS-P2-R2.md`: its numerical claims and formal INVALID/post hoc distinction agree with this audit, including the joint index-and-inherited-content fraction .005 → .045. The lead corrected the two clarity points identified here: assigned-assembly means are explicitly mapped to seed103=20.132 and seed104=20.003, and cue masks are called positional. No further factual or claim correction was requested.
