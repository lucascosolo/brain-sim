# P2-E5 results review: code lens

Independent reviewer given only the files (HEAD f25d3ed, after the verdict). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

I found no bug in p2_e5_structured.py that changes any gated number, label, reading or validity flag. Everything I recomputed independently matched the records exactly: the persisted sha256 for all 5 seeds; the per-cue joint and index bits; the 8-part counts and vector at both loads; A_digest, matched across the gated, online, s100, pooled, s80 and s40 arms; the sibling overlap and eligible fraction from items I rebuilt from the contract's stream table; Part C count and first-spike AUCs; Part B L_c, L_i and L_o, with McNemar counts consistent with twin B's rates; the Part D ratios; the Part E pooled rows and dose McNemar; the blob ids against tree 9152f1e4; both digests. Replaying seed 23's persisted test raster through stores rebuilt from persisted R, A and E reproduced the frozen-point counts of main, plateau-set and R_3, and the 72-point grid bests (value and location) and passing points at both loads. The verdict STRUCTURED INDEX FAIL + STRUCTURED CONTENT FAIL (5/5 valid) stands on the code.

## Findings

### CC-1 [minor] Part F per-line rates count empty classes as 0.0 instead of leaving them out

- where: plant2/experiments/p2_e5_structured.py:625 (contamination; also per_line_rate and contamination_ratio at 664-669)
- evidence: rates[s][nm].append(cnt / cls[nm].size if cls[nm].size else 0.0). Cued items 0-9 (in the oldest 100) have no earlier siblings, so their earlier_only and both classes are empty. They still add 0.0 to the mean. So per_line_rate and contamination_ratio for earlier_only and both are biased low by about 10/200 = 5 % at both loads. Reported only (Part F): no label, reading or validity flag uses it.
- recommendation: Do not edit the frozen driver. When Part F's rates are quoted (for example as the 'normalised prototype and sibling intrusion rates' a correction must improve), recompute them from the persisted data with empty classes excluded, or state the bias beside them.

### CC-2 [nit] The main store's grid best (J_own*) sits on the grid edge for 4 of 10 seed-loads

- where: gated_diagnostics grid, readings Part B (L_c); contract Part A grid
- evidence: Main-store best at M=500: seed 23 at (J 6.0, g 1.0), the grid's corner. At M=1000: seeds 21, 24 and 25 at g 1.0, the top of the g range. The code applies the frozen grid correctly; my replay of seed 23 reproduced the best and its location. But L_c = min(J_ub*,180) - min(J_own*,180) may overstate the contamination loss where J_own* is censored. A flip would need the main store to gain more than about 28-55 cues beyond the grid: the margins of L_c over the next loss on those seed-loads are 55 (seed 23, M=500) and 47, 44, 38 (M=1000). It is unlikely, but it was not tested.
- recommendation: Report beside Part B that J_own* is edge-censored on these seed-loads. Any later readout recalibration must not treat the grid's g = 1.0 edge as an optimum.

### CC-3 [nit] Reported arms check mean |A| at M = 500 as well as at 1,000

- where: plant2/experiments/p2_e5_structured.py:431-435 (load_validity)
- evidence: Contract validity 3 bounds mean |A| at M = 1,000. load_validity also applies the bound over items 1..500 at M = 500 for the s100, s80, s40, pooled and F40 arms. That check is stricter and can only void a load, which would affect Part B attributability and the s100 reading. No effect here: every reported arm was valid at both loads on all 5 seeds.
- recommendation: No action needed for this verdict. In a future driver, make the per-load check match the contract's wording.

### CC-4 [nit] The items x are not persisted; exact replay depends on regenerating them from the pinned streams

- where: persist() (p2_e5_structured.py:463-500)
- evidence: The .npz holds E, A, R, the continuation counts and first ticks, and the rasters, but not the stored items or the block cues. Scoring a replay needs items[i] for the missing and intrusion sets. I rebuilt them from the contract's stream table without the driver's code. They matched exactly (overlap and eligible fraction equal the records to every digit), so replay is possible, but only through the generator.
- recommendation: A later contract that replays these seeds should pin regenerating the items from streams (seed,20,F) and (seed,21,F,k) and check them against E coverage, as done here.

## Next steps

- Accept the gated numbers and the verdict record (row 152) as computed correctly; no code-level reason to re-run or void any seed.
- When quoting Part F per-line rates or contamination ratios, recompute them from the persisted npz with empty classes excluded (CC-1).
- State beside Part B that J_own* sits on the grid edge (g = 1.0) on 4 of 10 seed-loads (CC-2).
- Keep the scratch scripts (~/.cache/brain-sim/review/p2e5-results/code-correctness/{recompute,indep,replaycheck}.py) as an independent recompute path for later replay contracts.

## For the owner

I checked the P2-E5 code that produced the gated result for bugs and found none that change a gated number, label, reading or validity check. I recomputed the results with my own code from the saved records and the per-cue files for all five gated seeds, and everything matched. I also replayed seed 23's saved test activity through feedback stores rebuilt from the saved data, and got the same frozen-point and readout-grid numbers. The FAIL labels and the Part B-E readings follow correctly from the frozen code. Minor items: the Part F per-line intrusion rates are about 5 % low for two classes (reported only). The main store's best readout point sits on the grid's edge on 4 of 10 seed-loads, which may overstate the contamination loss a little; the margins make a changed reading unlikely, but that was not tested.
