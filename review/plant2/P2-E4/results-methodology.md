# P2-E4 results review: methodology lens

Independent reviewer given only the files (HEAD bbeb25b, after the verdict and the post-verdict diagnosis). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

The verdict can be trusted and was derived correctly. I re-derived it from the per-slot logs (sha256 verified) and got exactly the same vector and labels: ONLINE INDEX FAIL + HABITUATION FAIL + RECOVERY FAIL, all five seeds valid. The events ran in order. Contract frozen at cd17cde, then the driver at d404332, then review and fixes up to 0958956 (plant2 tree 9152f1e4). Exploration started at 23:28. Predictions were committed at 124ecb2 (00:38:40), before the first run-once marker (00:38:56). Every gated record is on tree 9152f1e4 under digest f8f8838b with plant2 clean. The contract was only appended to and the results file is append-only. The diagnosis ran after the verdict as planned, with 0 replay mismatches. Problems: RECOVERY FAIL rests on one seed and load, short by one item. Some exploration text uses causal offset wording that the owner's narrowed reading forbids. The Result needs several disclosures.

## Findings

### F1 [major] RECOVERY FAIL rests on one seed and load, short by one item, under a per-seed-and-load reading of the power call

- where: bench/results/plant2.jsonl kill_test_seed 18 loads.500.habituation; plant2/experiments/p2_e4_online.py hab_criteria p0(); contract label table and pre-implementation O5 prediction
- evidence: Seed 18, M=500: 42 of 47 control passers recover on the repeated copy; 43 are needed. Control rate 0.820, p0 0.829. That value holds across Monte Carlo seeds (0.83) and ICC 0-0.3 (0.80-0.95), but p0 crosses 0.8 near a rate of 0.81, within about one SE. Every other O5 failure is NOT ESTIMABLE (p0 0.010-0.64). The driver uses seeds=1, loads=1. The contract's own prediction quotes about 0.003 at 0.77, an all-seeds figure (seeds 5, loads 2 gives 0.0036; one seed and load gives 0.55). Under that reading p0 at 0.82 is 0.16, which gives RECOVERY NOT ESTIMABLE. Ledger row 212 covers only the per-part rate.
- recommendation: Keep the label. It follows the frozen rule and the row's wording 'on a seed and load'. The Result should state the single seed and load, the one-item margin, p0 0.83 against the 0.8 bar, and the reading used. Append a ledger row recording the per-seed-and-load reading. No relabelling and no rerun.

### F2 [major] Do not carry over 'not evidence of a recovery deficit'; the gated data point the other way

- where: Contract, appended predictions ('It is not evidence of a recovery deficit'); kill_test_seed hab_items
- evidence: The predictions gave O5 recovery a per-seed pass chance of 0.80 at M=1,000. Observed: 0 of 5 seeds (26/34, 25/33, 27/35, 29/36, 27/37 recovered). Post hoc pairing of x's recovery cues, items where the control passes and the repeated copy fails against the reverse: pooled over gated seeds 57 vs 2; at M=1,000 7-10 vs 0-1 per seed. Collateral cues: 4 vs 1. The repeated copy has fewer cue passes than the control on all 10 seed-load pairs.
- recommendation: Report this as post hoc and computed by the reviewer, not a gate, beside the predeclared recovery among habituated items (0.75-1.0). Say that recovery of the repeated item's own cues 10.5-14.5 s later is incomplete while collateral items are spared, so the recovery hypothesis is not supported. Do not call it sampling noise.

### F3 [major] Exploration write-up blames the threshold offset, against the narrowed D3 reading; gated D2 does not replicate the offset pattern

- where: docs/plant2/P2-E4-diagnosis-plan.md, the 'Not predicted' D3 text and 'What the diagnosis says about the two problems'
- evidence: Written at 614246b, after the narrowing at 21245c1: 'the online state's high offset suppresses the intrusions', 'coupled through the threshold offset', 'fixing the operating point alone would be expected to expose the contamination'. Twin B and the duty arm change the regime, not the offset alone (owner, 2026-10-11). Gated D2 at M=1,000, content-only cues minus cues passing both: assembly offset +0.57, +0.27, -0.15, +0.08, +0.40 mV; global +0.25, -0.09, +0.12, +0.07, +0.14 mV. At M=500, seed 20 is negative on both.
- recommendation: Append a correction to the plan; do not edit the old text. In the Result, write 'the online state (higher offset among other differences)' and 'which variable is responsible is not isolated'. Report the offset correlate as small and inconsistent in sign.

### F4 [major] Passing content parts are not evidence of an accurate online write

- where: kill_test_seed vectors (O2, O3 content); lane logs, twin A; diagnosis D3
- evidence: O2 joint 0.93-0.995 and O3 content 0.90-1.0 pass on all five seeds; seed 20 at M=1,000 is exactly at the bar (90/100). Twin A at M=1,000 reads the same raster through three stores: online-written 0.820, 0.905, 0.860, 0.855, 0.850 (below P2-E3's 0.90 bar on 4 of 5 seeds); P2-E3-protocol 0.96-1.0; plateau-set 0.985-1.0. D3 content McNemar at M=1,000 favours the online state on all five seeds (27/8, 21/5, 15/5, 25/6, 28/9). At M=500 all three stores read 0.99-1.0.
- recommendation: The Result should say content passes on 5 of 5 seeds but, at M=1,000, the pass depends on the online state: the online-written store is contaminated and reads worse after a settle. Do not write 'content holds online' without that qualifier, and do not imply ONLINE CONTENT FAIL.

### F5 [minor] Not-estimable meaning differs between vector and labels; M=1,000 habituation is unanswered

- where: hab_criteria vector_state; labels(); ledger row 208
- evidence: For O5, the contract ties 'fail (not estimable)' in the vector to minimum counts. Control passers were 33-50 (at least 25) on every seed and load, yet vector_state says 'fail (not estimable)' at M=1,000 and for seed 20 at M=500, using the power rule. For O4, eligible items were 6-13 at M=1,000 on every seed, and 21 and 20 for seeds 16 and 20 at M=500. The NOT ESTIMABLE labels were dropped under the global reading (row 208, chosen before exploration; both readings defensible).
- recommendation: Use the contract's three states in the Result's vector: O4 'fail (not estimable)' where eligible < 25. O5 at M=1,000 is 'fail', with 'not estimable by the power rule (p0 0.01-0.025)' noted. State that the NOT ESTIMABLE conditions held at M=1,000 for both families but are absorbed into the FAIL labels.

### F6 [minor] HABITUATION FAIL is real, but O4 had little power at the observed rates

- where: kill_test_seed habituation (mcnemar_scored); contract Power section
- evidence: The contract's zero-habituation power, 0.981, assumed a 'both' rate of 0.963. The observed control late rate was 0.75-0.82 at M=500. My null model (ICC 0.09) gives a no-effect pass chance of 0.45-0.79 per estimable seed and load, with about 7-9% of items habituating by chance. Observed: 14/28, 21/33 and 14/27 habituated (50-64%). The predeclared McNemar on 'L >= 8' gives 23/0, 25/0 and 18/0 for seeds 17-19.
- recommendation: The Result should cite the McNemar and the habituated fractions as the evidence, not only the 10% bar. It should say O4 had little power at the realised rates and that this does not weaken the failure. Habituation is measured on copies with sham encodings (SHAM-1).

### F7 [minor] The Result must score failed predictions as well as held ones

- where: Contract predictions (pre-implementation and from the real driver); reported_arms records
- evidence: Failed: O5 at M=500 ('likely holds') failed on seeds 18 and 20. C1 at M=1,000 fell below the predicted 0.70-0.85 on 3 seeds (0.68-0.685); O3 memory below 0.70-0.80 on 3 seeds (0.61-0.67). Collapse: joint 0.72-0.79 at M=1,500 (predicted < 0.3) and 0.18-0.30 at M=2,000 (predicted about 0). Writes during probes 'stored' 0.165-0.20 (predicted nearly all). 30% cues C1 0.0 (predicted 0.2-0.5). Held: ONLINE INDEX and HABITUATION labels; responder |R| 41-44.5 vs 28; Jaccard 0.48-0.53 vs 0.71-0.75; offsets 6.8-7.0 vs 3.7 mV; D3 index recovery 86-100%.
- recommendation: Add a table of held and failed predictions. The stored fraction in the writes-during-probes arm is confounded by online index failure at about M=1,200; call it a stress test.

### F8 [minor] The verdict text must include per-kind rates; recent items fail too

- where: kill_test_verdict per_seed.per_kind; contract Kill test ('per-kind rates are reported in the verdict text')
- evidence: C1 at M=1,000: recent cues (age 0-20) 0.72-0.82; uniform 0.62-0.72; cohort 0.61-0.75. Mean age-0 cued recall is 0.84-0.98, with blank leak 0.
- recommendation: Include the per-kind table. Do not describe the online index failure as forgetting of old items or as interference alone: it reaches the newest items.

### F9 [minor] Diagnosis scoring: exploration D1 was not an independent test; D4 overstates the offset rise

- where: docs/plant2/P2-E4-diagnosis-plan.md (header, D1, D4); diagnosis records 89-94
- evidence: The plan's header computed at least 26% and 19% from the same exploration numbers before it predicted 15-30%. Gated D1 at M=1,000: 22.5-29.5% (held). Index without content was 6/200 = 3.0% on seed 20, not under 3%. D4: the repeated copy's assembly offset rises 3.1-3.3 mV, but the control copy's rises 1.1-1.2 mV, so the repetition-specific rise is about 2.0-2.1 mV. Habituated and non-habituated items rise equally. Plant2 code unchanged; plan header date corrected after predeclaration (e6c5385).
- recommendation: Score D1 on gated seeds only. Report the offset rise net of the control copy. Say 'does not support' rather than 'rules out'. Keep the online association as not estimable (median 0 online probes per item).

### F10 [nit] Process disclosures for the Result

- where: DECISIONS.md 09962a4; record.git_state; guard()
- evidence: The owner's reading (01:05) cites 'the first gated readings' taken from lane logs before the records for seeds 16 and 17 existed (01:15). Nothing changed afterwards. The guard checks that plant2/ is clean, not the whole tree; seed 19's record has dirty=true outside plant2. The 0.002 upper bound comes from 1,500 simulations over 300 posterior draws and covers Monte Carlo error only.
- recommendation: State that the owner's reading came before the five-seed records. State the guard's plant2-only reading. Use the owner's wording ('zero passes in 1,500 simulations') together with the analytic index-only bounds (4e-4 and below 1e-38).

## Next steps

- Append the Result to the contract (append-only). Include: the verdict and labels; the three-state vector per seed and load; per-kind rates; the validity summary; provenance (tree 9152f1e4, digest f8f8838b, 124ecb2 before the markers); the held/failed prediction table; and the disclosures in F1-F10.
- Use the Decision's own words: the claim of a usable online operating point from accommodation is withdrawn at M=500 and M=1,000; Stage 1's '60 s of ongoing activity' clause is not met online by the P2-E3 system; nothing is retuned; P2-E5 comes next; where an operating-point mechanism goes is the owner's call.
- Append a ledger row: recovery estimability is read per seed and load (seeds=1, loads=1); the all-seeds reading would give RECOVERY NOT ESTIMABLE; the O5 vector_state uses the power rule.
- Append a correction to the diagnosis plan narrowing the causal offset sentences and adding net-of-control offsets; then append the gated D1-D4 results with predictions scored.
- Add the STAGES row for P2-E4 (FAIL, labels, scope: independent random items, write oracle still supplied).
- Run no reruns and change no criteria. Recovery asymmetry and the O4 null model are post hoc and must be labelled so.

## For the owner

The P2-E4 verdict holds. All five fresh gated seeds were valid and each ran once, on the frozen code, after the predictions were committed. My independent recomputation matches exactly. Index recall fails online at both loads (C1 0.87-0.93 at M=500, 0.68-0.74 at M=1,000), and newest items fail too. Habituation is real at M=500 (50-64% of eligible items) and could not be estimated at M=1,000. The RECOVERY FAIL label rests on one seed (18, M=500), one item short, and on reading the power rule per seed and load. A post hoc paired check suggests recovery of the repeated item really is incomplete. Content passes, but at M=1,000 that depends on the online state, and the online-written store is contaminated. The Result must not blame the threshold offset: twin B and the duty arm do not isolate it, and the gated offset differences are small and inconsistent.
