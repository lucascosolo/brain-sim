# P2-E6 results: independent methodology audit

**Disposition: complete, integrity-consistent seed101 FEASIBILITY FAIL; pure index FAIL.** The candidate improves canonical specificity substantially but fails the two frozen absolute specificity bars. No tuning, seed102, or gated-seed escalation follows from this result. This is one development seed, not a five-seed gated FAIL or a Stage-1 result.

Reviewed `docs/plant2/P2-E6-load-gated-encoding.md` (contract6733109), `docs/plant2/P2-E6-frozen.json`, driver `plant2/experiments/p2_e6.py` at recorded source `c4cc27b8781095fe3e9d332995bdb24e008bd0f2`, `bench/results/p2e6.jsonl`, and all `bench/results/p2e6/e6-s101-v1-*.json`. The run completed all16 loads and both sanity checks, without interruption, from 2026-10-12T04:06:07Z to04:16:16Z, elapsed608.64s, inside the resource window.

## Independent verification

All96,108 scalar/structural checks in the final read-only audit passed. These included all9,600 portable index rows, all13,200 content rows across22 store/readout combinations, all ten paired comparisons, per-age summaries, and matching digests. Every one of the18 portable artifacts and18 referenced raw archives was present; byte counts and SHA-256 values matched. All11 executable/config source hashes and the contract hash matched the recorded manifest.

From each of the16 load archives, independently reconstructed50ms own/spurious/total responders and the raster digest. Independently regenerated plateau and coin streams, causal pre-write history probabilities (80 float64 bisections), random-control selections, per-cell attempted flip counts, the final forward store, potentiations and depressions for all12,000 represented encoding episodes. Results matched exactly. Across mandatory arms, independently reconstructed both feedback stores from saved E/A/R arrays (24 exact matches), and regenerated all2,000 F10/independent baseline inputs directly from the specified NumPy streams, without importing the generator or experiment driver.

Content aggregates were rescored from saved per-cue reconstruction counts, including the strict intrusion threshold, oldest cohort, short-window diagnostics, percentiles and latency. Reconstruction-layer dynamics and full neural simulations were not rerun. Sensory-digest equality and unchanged-main-state checks were inspected in the driver and recorded evidence; this audit did not independently regenerate the encoding spike trains or evaluation threshold trajectories.

The independently rebuilt70-part prospective screen equals the final `seed_screen`:68 true, two false, complete=true, integrity=true, missing=[]. Wrong-label permutation was regenerated from `(101,32,1000)` and rescored against the unchanged assigned sets: C1=0. The empty archive has zero raster spikes, zero cue responders, zero forward/feedback stores and zero H.

## Measured index result

Fractions below are over200 half cues; oldest bars use the separately identified oldest100. B/C/R mean baseline/candidate/exact flip-count-matched random.

| Condition/load | C1 B / C / R | C2 B / C / R | Joint index B / C / R | Candidate oldest recall / specificity |
|---|---|---|---|---|
| F10/500 | .960 / .945 / .980 | .885 / 1.000 / .870 | .845 / .945 / .850 | .980 / 1.000 |
| F10/1000 | .935 / .970 / .945 | .500 / .895 / .460 | .440 / .865 / .410 | .970 / .890 |
| Independent/500 | .980 / .975 / .965 | 1.000 / 1.000 / 1.000 | .980 / .975 / .965 | .960 / 1.000 |
| Independent/1000 | .960 / .935 / .955 | .975 / .990 / .975 | .935 / .925 / .930 | .940 / .980 |

F10/M1000 C2=179/200 and oldest specificity=89/100 each fall one passing cue short of their respective90% bars. These are exact failures, not rounding artifacts. All relative margins pass: C2 gains are+.395 versus baseline and+.435 versus random; joint gains are+.425 and+.455. Candidate C3=.995. Both loads satisfy F10 recall preservation. The global specificity failure is not confined to the oldest100:11 failures are oldest,10 are elsewhere.

Paired canonical M1000 wins:losses, candidate versus baseline/random, are specificity79:0 /87:0, joint86:1 /94:3, recall8:1 /8:3. This supports a history-dependent assignment benefit beyond the matched attempted-flip budget on this seed. It does not establish seed-general reliability.

Tradeoffs remain. At F10/M500, recall wins:losses are5:8 versus baseline and1:8 versus random; candidate recall is lower despite greater joint success. Independent/M1000 recall is lower by.025 versus baseline (wins:losses1:6), within the frozen.03 allowance; its joint fraction falls.010. Passing non-regression is not unchanged performance.

## Suppression, operating point and age

For canonical M1000:

| Measurement | Baseline | Candidate | Random |
|---|---:|---:|---:|
| Mean own responders | 18.585 | 18.925 | 18.475 |
| Mean spurious responders | 16.970 | 3.145 | 17.075 |
| Forward density | .0558410 | .0576232 | .0557898 |
| Potentiations | 936928 | 950553 | 935886 |
| Depressions | 43472 | 28582 | 43249 |
| Mean assigned-cell onset threshold offset, mV | 5.8111 | 5.4690 | 5.7942 |

Candidate/random each attempt979135 flips, with exact agreement per episode and plateau cell. They do not match additions, depression or density. Improved specificity accompanies more own responses, a denser store and lower threshold offsets; simple silence, higher thresholds or lower density do not explain this pattern. Effective operating states nevertheless differ, so this does not isolate discrimination at matched neural state. Half-cue median latency is23ms versus24ms baseline; the scoring deadline remains50ms.

Candidate specificity by age0–99,100–499,500–999 is.8667,.9070,.8944, with n=15,43,142. These sampled strata do not show a monotonic age gradient. The oldest100 failure supports the preregistered concern, but it is not evidence that age alone causes the remaining errors.

## Content, transfer and scope

Independent inherited content passes every regression check: at500 candidate joint/D4=1.000/1.000 versus baseline.995/1.000; at1000 both candidate and baseline=.975/.960. Absolute content bars also pass there.

Canonical candidate inherited content joint/D4 is.785/.610 at500 and.065/.020 at1000; assigned-A feedback on the same candidate raster yields.990/.990 and.425/.390. At1000, improving the forward index therefore remains insufficient for clean content at the frozen75ms, J=2.8, g=.3 readout. Assigned-A is a diagnostic supplied-key store, not the deployed feedback writer. Cross-encoding-arm content differences jointly reflect changed learning responders/feedback and changed retrieval rasters; they do not isolate a feedback-only effect.

F40 transfer candidate meets all six absolute index bars at both loads. At1000 its vector is C1=.940,C2=.950,C3=.995,C4-recall=.950,C4-specificity=.950,joint=.890; baseline C1/C2/joint=.970/.820/.790. At500 candidate joint=.920 versus baseline.950, and at1000 recall discordance is4:10 versus baseline. This is useful but mixed transfer, not a rescue. F40 candidate inherited content still fails (1000 joint=.200,D4=.070), although assigned-A content passes (.935,.930).

All numerical prediction intervals held: canonical C2=.895 and C1=.970 fall inside their declared ranges; independent C1 deltas−.005/−.025 lie within±.05. The oldest bar failed as anticipated, together with overall specificity. Broad predictive accuracy does not soften the narrower acceptance bars.

A reporting caveat: `learning.probability_min/max` records the computed candidate probabilities in every arm; baseline deploys p=.5. The raw metadata explains this, but these fields must not be presented as baseline's actual variable learning probabilities (`p2_e6.py:55–89,250–272,317–326`).

The demonstrated effect is settled, externally cued retrieval after quiet learning, with random assigned plateau keys and unchanged scaffolding. No new autonomous keys, online deployment, related-unseen-exemplar rejection, or general reasoning capability was tested. Novel C3 cues remain independent random inputs. The next separately contracted exact-degree input null can test higher-order co-occurrence while preserving item sizes and per-line input counts; it cannot guarantee removal of every dependency or exact matching of realized spike eligibility. It must remain a diagnostic, not a revision or rescue of E6.

Suggested results statement: **Seed101 completed with valid evidence and failed the frozen E6 feasibility screen at canonical M1000 specificity (179/200) and oldest specificity (89/100). History-dependent encoding produced large paired specificity/joint gains over baseline and exact flip-count-matched random controls, while independent regressions passed. Canonical content remained poor and the mechanism is rejected under its frozen acceptance criteria; seed102 and gated seeds remain unrun.**
