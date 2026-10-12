One material finding remains before committing.

**P2: Some reported aggregates lack portable supporting evidence.** In `analysis/p2r1_replay.py:253–268`, the compact artifact retains every `e3.score()` metric, including `latency_ms_median`, plus memory `recall_median` at 25/50/100 ms and `latency_half_ms`. Its per-cue evidence records only content counts and index `recall50`. Consequently, a reviewer using Git cannot reproduce the content latency median, index 25/100-ms recall medians, or index latency median. The contract requires new aggregate claims to be independently auditable from committed compact outcomes.

Fix either by adding the corresponding per-cue latency and 25/100-ms recall values, representing missing latency as `null`, or by omitting these unsupported supplementary aggregates. The explicitly required C1–C4, joint, D3, D4 and writer precision/recall already have sufficient portable evidence.

Verification completed:

- All six new tests pass: **6 passed in 0.65s**. Used bytecode disabled, plugins disabled, cache/tmpdir plugins disabled, plain assertions, in-memory capture and optional Git locks disabled.
- Independently loaded the saved tiny NPZ with `allow_pickle=False`, restored full cue arrays and memory raster, regenerated all five writer lists from saved continuation cells/counts and assigned cells, and rebuilt each clipped feedback union exactly.
- Replayed every saved content count for all five stores from the loaded NPZ; all matched the compact artifact. Independently recomputed every 50-ms index cue from the restored memory raster and assigned cells; all matched.
- Independently compared tiny captured duty learning with unmodified `e4.Online`: identical inherited state digests and logs. The proposed settled-copy path reproduced inherited `e4.twin_A` memory summaries and R1 replay scores exactly, while leaving the main timeline unchanged.
- Decoded persisted duty slot first-spikes and independently rescored them with inherited scoring; all existing per-slot measurements matched.

Methodology is otherwise consistent:

- Correlated line uses canonical F=10/s=60 generation and inherited E3 learning/evaluation.
- Duty uses inherited schedule, independent item generator, `post=duty_post` and `(ARMS, ARM_DUTY)` background streams. Canonical interval is 50+100+1850=2000 ms.
- Both controls select exclusively from observed R1 responders, with exactly R3 cardinality. Anti-selection orders by count with separately seeded tie breaking. Assigned A does not influence either control.
- R1 and A feedback unions are checked against inherited stores; every arm uses the same eligible lines and clipped-union rule.
- Replay consistently uses 50-ms index/short windows and 75-ms content windows. Oldest-cue ordering agrees with inherited cue construction and scoring.
- “Same raster” is accurate for the five settled replay arms. The code clearly separates inherited live online measurements and does not claim that replay swaps repair online behavior. No sham online intervention is being misrepresented.
- Exclusive artifact creation and append-only journals preserve completed runs and partial results. No forbidden deletion or temporary cleanup was found.
- Full-scale runtime was not measured. Execution performs five complete replay passes per checkpoint and retains multiple stores plus a deep network copy; the tiny-test time should not be extrapolated as a full-run estimate.

No source modifications or full simulations performed.

## Appended disposition — 2026-10-12

**P2 fixed; no material findings remain open in this review.** Limited inspection of the latest driver and test changes confirms that compact half-cue records now include `recall25`, `recall50`, `recall100` and `latency_half_ms`; full-cue records also include `latency_full_ms`. Each content row now includes `latency_ms`, converting non-finite readout latency to JSON `null`. These values are the direct inherited per-cue inputs used to calculate the retained aggregate medians, closing the portable-evidence gap.

The updated test independently reconstructs the three memory recall medians, memory latency median and each content latency median from compact rows, checks latency range/null representation, and compares compact index values with the raw NPZ's saved memory output. This follow-up was source inspection only, as requested; the exact **6 passed in 0.65s** result above predates the fix and is not presented as a rerun of the updated test. The independent raw rereplay and tiny-duty equivalence checks recorded above remain valid for the unchanged simulation, writer selection and persistence paths.

The original report above is preserved verbatim. This report is the sole file created by the reviewer; no implementation or test source was modified, and no broad tests or full simulations were rerun for closure.
