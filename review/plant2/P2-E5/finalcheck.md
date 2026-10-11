# P2-E5 final diff check: final

Fresh checker given only the files (diff 3c78f03..93c4c35). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

The contract can be frozen once four minor wording and rule fixes are made; I found no blocker or major problem. All 14 ledger actions from the fix-check are in the diff 3c78f03..93c4c35.

**Ledger actions implemented as stated:** LED-2, LED-3 (Power section), LED-4, LED-5, R2, R3, R7, R8 and R9.

**Implemented, but with gaps:**
- **LED-1:** correction row 338 was appended, but only Parts C and D are labelled qualitative in the Predictions table (n9).
- **R1:** the C2 row of the new Scope table compares two different cue sets (m3).
- **R4:** the plateau-eligibility caveat says "together with" a separate mechanism, which clashes with the one-mechanism rule (n7).
- **R5:** two new void-rule problems: the s = 100 outcomes are not exclusive (m1), and Part B still lists s = 100's validity as 1-4 (m2).
- **R6:** the online-arm parenthetical is literally false (n6).

**Code checks behind R7 and R9:**
- R7: `twin_A` deep-copies S and uses only seed-keyed streams, so a second call with the R_3 store reproduces the raster.
- R9: the seven named blob paths exist in tree 9152f1e4, which is still HEAD:plant2. They cover everything the reused functions execute. `power.py` and `record.py` are imported but used only by P2-E4 code that this arm does not run.

**Power script:** I ran it read-only. Every Power and Predictions number matches its output except one Monte Carlo cell that the new L_o levels shifted (n8).

**Gaps that change a reading:**
- The pooled reading's plateau-set joint has no fixed readout point (m4).
- The s = 100 reading is non-exclusive, and "non-void seed" is undefined when voids are per load (m1).

## Findings

### m1 [minor] The s = 100 reading's three outcomes overlap, and 'non-void seed' is undefined when voids are per load

- where: docs/plant2/P2-E5-structured-items.md L336-341 (Voids: a failure 'voids that arm at that load'), L479-485 (s = 100 REPLICATES / REPLICATION FAIL / NOT ESTIMABLE)
- evidence: REPLICATION FAIL is 'the gate fails at either load on any non-void seed', with no seed minimum. NOT ESTIMABLE is 'fewer than 4 non-void seeds'. No order is given. So with 3 non-void seeds, one of which fails the gate, both labels apply. Voids are per load, but the s = 100 rule counts 'non-void seeds' and needs the gate 'at both loads'. Take a seed whose s = 100 arm is void at M = 1,000 only. It is unclear whether it is non-void. If it counts, 'holds at both loads' cannot be evaluated, so REPLICATES cannot hold, and it is undefined whether the gate 'fails'. If it does not count, a gate failure at its valid M = 500 load is silently dropped.
- fix: Rewrite as an ordered rule, per (seed, load):
- **REPLICATION FAIL** if the gate fails at any non-void (seed, load);
- otherwise **NOT ESTIMABLE** if fewer than 4 seeds are non-void at both loads;
- otherwise **REPLICATES**.
Add a definition: 'a seed is non-void for s = 100 when the arm is non-void at both loads'.

### m2 [minor] Part B's attributable-seed rule still names s = 100's validity as 1-4, but the new Voids section and Part E apply 1-4 and 7, and a crash

- where: docs/plant2/P2-E5-structured-items.md L397-400 (Part B: 'fails its validity checks 1-4 there'), against L336-337 (Voids) and L479 (Part E)
- evidence: The diff added validity 7 to s = 100 and made a crash void the arm. Part B's NOT ATTRIBUTABLE condition was not updated. Suppose s = 100 fails only validity 7 at a load, or crashes there (so it has no gate result). Part B's literal text then leaves the seed attributable. The Denominators bullet says the same seed counts only if non-void. Both rules apply to the same seed and give opposite answers. The online condition in the same list already says 'void or invalid'.
- fix: Change the s = 100 condition to: 'the s = 100 arm is void there (validity 1-4 or 7 fails, or the arm crashes), or fails P2-E3's gate there (D1/2, D3, D4, C1-C4)'.

### m3 [minor] The new Scope table's C2 row compares two different cue sets, and the 'offset suppresses' sentence asserts a cause the owner's own caveat rules out

- where: docs/plant2/P2-E5-structured-items.md L124-137 (Scope table and the sentence after it), L88-89 (Why: 'C2 was 1.0 online')
- evidence: Online C2 of 1.0 is from `block_criteria`: the block's 200 half cues (50 recent, 50 uniform, and 100 cohort items drawn from items 1-200). Settled C2 of 0.90 / 0.945 is twin A's `memory`, on P2-E3's test set (the 100 oldest items plus 100 random). `twin_B` records only memory and content, not spurious cells, so no paired settled C2 exists. The content and C1 rows are paired (twin B, same cues). The C2 row is not, yet the table presents all rows as one store read in two states. Twin A's own numbers imply about 0.96 on its non-oldest 100 cues (2 x 0.90 - 0.84 and 2 x 0.945 - 0.93), so the gap shown is partly a population effect. Separately, 'The online state's higher offset suppresses intrusions and spurious index cells' is causal. The owner's 2026-10-11 caveat (DECISIONS) is that a state comparison 'does not prove that the offset alone causes the difference'.
- fix: Label the C2 row: 'online: the block's 200 half cues; settled: twin A's P2-E3 test set (oldest 100 + 100 random); not paired'. In Why, write 'C2 was 1.0 on the online block's cues, against 0.90-0.945 on twin A's settled test cues (not paired)'. Replace the causal sentence with: 'The online state (higher offset, among other differences) shows fewer intrusions and spurious index cells, and less index access. Which state variable is responsible is not isolated.'

### m4 [minor] The pooled reading's 'plateau-set joint' has no readout point, and the choice decides whether LINE-LOAD-LIMITED can ever be read

- where: docs/plant2/P2-E5-structured-items.md L486-493 (pooled reading), L362-370 (Part A defines frozen and grid-best values for main; J_ub* is the grid best), L648 (prediction)
- evidence: For main's plateau-set store, Part A records both the frozen-point value and the grid best. Part B uses the grid best (J_ub*). The pooled arm gets no grid, since the grid is run only on the gated arm's stores, so it has only a frozen-point value. The M = 1,000 prediction ('0.49 against 0.155') silently uses main's frozen value; main's grid best there is 0.60-0.665. Comparing pooled-frozen with main-grid-best biases the measure against the pooled arm by the grid's optimism (about 90 cues at M = 1,000: frozen 0.12-0.18 against grid best 0.60-0.665). LINE-LOAD-LIMITED ('within 10 cues on both measures') would then essentially never be read.
- fix: Write 'the plateau-set joint at the frozen readout (2.8, 0.3), for both arms' in the LINE LOAD SUFFICIENT, CORRELATION WORSENS and LINE-LOAD-LIMITED bullets.

### n5 [nit] Scope still says two learning rhythms were examined, the second explicitly 'not P2-E4's frozen driver', and then reports frozen-driver results

- where: docs/plant2/P2-E5-structured-items.md L117-126
- evidence: L117-120 reads: 'Two learning rhythms have been examined ...: P2-E3's back-to-back protocol; the P2-E4 red-team's exploratory online line (...; not P2-E4's frozen driver)'. L124 then reads: 'On P2-E4's frozen driver with these items (fix-check R1 ...)'. Three lines have now been examined. The 'write' bullet (|R| 105-111) rests on the red-team line only, though the frozen driver's twin A also supports it (online-written joint 0.035-0.10 against P2-E3-protocol 0.09-0.165).
- fix: Write 'Three learning lines have been examined: ...; and P2-E4's frozen driver (fix-check R1; seeds 44-45, M = 500)'. Optionally cite the frozen driver's twin A joints under 'The write'.

### n6 [nit] The Pins say E3's learn_one is neither copied nor changed 'for the online arm through Online.learn_one', but Online.learn_one is P2-E4's changed copy of it

- where: docs/plant2/P2-E5-structured-items.md L223-229; plant2/experiments/p2_e4_online.py L244-281
- evidence: P2-E4's `Online.learn_one` is commented 'E3.learn_one statement for statement, without quiet(), then the live projection reload'. It does not call E3's learn_one. So for the online arm, E3's body has been copied and changed, by P2-E4. What P2-E5 actually guarantees is that it neither copies nor changes the learn_one it inherits.
- fix: Write 'The inherited learn_one (E3's for the P2-E3-protocol arms, P2-E4's Online.learn_one for the online arm) is neither copied nor changed'.

### n7 [nit] The plateau-eligibility caveat says 'together with' a separate mechanism, which clashes with the single-mechanism-per-contract rule

- where: docs/plant2/P2-E5-structured-items.md L686-689; L32-33 (ruling 4: 'Any correction is a separately contracted single mechanism')
- evidence: 'It is admissible only together with a plateau key the experimenter does not supply, which is a separate mechanism under ruling 4.' Read literally, the candidate needs two mechanisms in one contract. The same sentence calls the key a separate mechanism, which under ruling 4 needs its own contract first.
- fix: Write 'It is admissible only after a separately contracted mechanism supplies a plateau key the experimenter does not (ruling 4); until then it is not a candidate on its own'.

### n8 [nit] One Part B cell no longer matches the script after the new L_o levels shifted the RNG stream, and two Predictions summaries drift from the Power section

- where: docs/plant2/P2-E5-structured-items.md L617 (M = 1,000, L_o 0.15: '0.975'), L640 (Predictions Part B)
- evidence: `ranking()` draws every L_o level from one shared generator, so inserting 0.145 and 0.185 shifts the draws for the later levels. The current output gives CONTAMINATION-DOMINANT 0.9717 at M = 1,000, L_o 0.15; the contract says 0.975, which is the old run's value. The `--append` record will carry 0.972. All other cells still round correctly. The Predictions M = 500 cell says 'about 0.7-0.95', but the Power section (and the script) give 0.96 and 0.71 at the measured L_o. The Predictions M = 1,000 cell calls the operating-point loss material (0.97-0.98) without the Power table's condition 'when L_o >= 0.15'; the script gives 0.0001 at L_o 0.07, and L_o is unmeasured at M = 1,000.
- fix: Change '0.975' to '0.97'. Write 'about 0.7-0.96' in the Predictions M = 500 Part B cell. Add 'if L_o >= 0.15' to the M = 1,000 cell.

### n9 [nit] LED-1 and LED-2 are only partly carried through: the qualitative labels cover Parts C and D only, and DECISIONS keeps the superseded statements

- where: docs/plant2/P2-E5-structured-items.md L627-656 (Predictions); review/ledger.jsonl row 338; DECISIONS.md 2026-10-11 'P2-E5 verification acted on' entry
- evidence: Row 338 says 'Parts C-G are qualitative predictions, labelled so'. Only the Part C and Part D rows carry '(no probability computed)'. The Part E-G rows and the new online-arm rows have no label. Commit 93c4c35 did not touch DECISIONS.md, which still says:
- 'methodology M2, B1 and n1 as completed only by this revision' (B1 is now accepted in part);
- 'By run it ranges from 0.0002 to 0.12', which is the dependent model only;
- that M = 500's Part B reading depends on an L_o 'which no one has measured on structured items', though the fix-check measured it.
LED-1's own fix asked for a matching DECISIONS note.
- fix: Add one line under the Predictions heading: 'Probabilities are computed only for S1, validity, Part B, s = 100 and P(PASS); every other row is a qualitative prediction from exploratory values.' Append a DECISIONS entry for the fix-check that corrects the three statements above.

## Computed (scripts and numbers)

Nothing in /home/user/brain-sim was created, edited or deleted, and `git status` is clean. Outputs are in ~/.cache/brain-sim/review/p2e5-final/: power_out.json (the script's output) and summary.txt. HEAD has moved to 534e3e4 (a P2-E4 seed-18 record), and the contract and power script are unchanged since 93c4c35.

**1. Power script, run read-only** (PYTHONDONTWRITEBYTECODE=1, no `--append`, 4 s).
- Unchanged values:
  - idealised P(PASS) 0.8556 (pooled rates) and 0.7891 (P2-E3-only);
  - oracle at M = 500 alone 0.00183, by run 1.6e-8 to 0.035;
  - P(S1 at M = 500) 0.00949 independent and 0.0392 dependent; by run 5.7e-6 to 0.058 (independent) and 0.000185 to 0.124 (dependent). This matches the new text '6e-6 to 0.06' and '0.0002 to 0.12'.
  - P(INVALID) 0.0067 at SD 0.03 and 0.0596 at SD 0.04;
  - s = 100 per seed and load 0.99966 at M = 500 and 0.954 at M = 1,000.
- Part B, M = 500:

  | L_o | reading probabilities |
  |---|---|
  | 0.07 | CONTAMINATION-DOMINANT 1.0 |
  | 0.145 | CONTAMINATION-DOMINANT 0.9602 |
  | 0.15 | CONTAMINATION-DOMINANT 0.9448 |
  | 0.185 | CONTAMINATION-DOMINANT 0.7048 |
  | 0.25 | SPLIT 0.9179 |
  | 0.35 | SPLIT 0.6008, OPERATING-POINT-DOMINANT 0.3992 |
  | 0.45 | OPERATING-POINT-DOMINANT 0.9908 |

  The operating-point loss is material with probability 0.994 or more from L_o 0.145.
- Part B, M = 1,000:
  - CONTAMINATION-DOMINANT 0.9735 / 0.9748 / 0.9717 / 0.9744 / 0.9726 / 0.9712 / 0.8494 at L_o 0.07 / 0.145 / 0.15 / 0.185 / 0.25 / 0.35 / 0.45 (SPLIT 0.1313 at 0.45);
  - NOT ATTRIBUTABLE 0.0187-0.0215;
  - operating-point loss material: 0.0001 at 0.07, 0.958 at 0.145, 0.967-0.981 from 0.15.
- Sensitivity to J_ub* (M = 1,000, L_o 0.25): CONTAMINATION-DOMINANT 0.177 / 0.481 / 0.687 / 0.919, with NOT ATTRIBUTABLE about 0.02.
- Against the contract: every number in Power and Predictions matches except the M = 1,000, L_o 0.15 cell (0.972 against the contract's 0.975, from the RNG shift) and the Predictions range '0.7-0.95' (the computed upper end is 0.96).

**2. Fix-check exploratory outputs** (regression/partd_probe_s44/45_M500.json, online_validity_s44_M500.json).
- Every new number in the Scope table, the online-arm Predictions rows and the Part D prediction matches:
  - content 0.525 / 0.58 online against 0.055 / 0.035 settled;
  - C1 0.82 / 0.77 against 0.965 / 0.955;
  - offset 3.70 / 3.80 mV against 1.86 / 1.92 mV;
  - twin A joints 0.035 / 0.09 / 0.965 and 0.10 / 0.165 / 0.95;
  - L_o 29 and 37 cues, content gain 94 and 109 cues;
  - R = 124/66.5 = 1.865 and 113/62 = 1.823.
- The paired per-seed claim holds: L_c 67 (180 - 113) against L_o 29 is contamination-dominant; 45 against 37 is a margin of 8 cues, below the 10 needed, so no dominance.
- The C2 row is not paired: online 1.0 is on the block cues; settled 0.90 / 0.945 is twin A's P2-E3 set. Twin A's oldest-100 C2 is 0.84 / 0.93, which implies about 0.96 on its other 100 cues. `twin_B` records no spurious counts.

**3. Code read** (plant2/experiments/p2_e4_online.py, p2_e3_completion.py, p2_e2_accommodation.py).
- `Online.learn_one` is P2-E4's own copy of E3's body, with no super() call.
- `twin_A(S, M, ref_store=None)`: it deep-copies S; `settle_drift` and `evaluate` use the seed-keyed streams (TEST_IN, M, ...); `swap_reference` is the readout with `ref_store`. The second call is therefore deterministic.
- `block_criteria`: C2 is `spur_ok` (spurious < 0.5|A| within win_mem = 50), the same rule as P2-E2. The cohort at M = 500 is 100 items from a permutation of items 1-200.
- `twin_B` returns memory and content only.
- Tree 9152f1e4 equals HEAD:plant2 and holds all seven named files. `p2_e4_online` also imports `power` and `record`, but uses them only in habituation, predictions and record writing, none of which the online arm runs.

**4. Ledger rows 324-339 and DECISIONS.md.**
- Rows 324-337 are the 14 dispositions; rows 338-339 are correction rows for B1 and completeness C4.
- DECISIONS.md was not changed by 93c4c35.

**5. Exclusivity checks on the new rules.**
- Pooled reading: CORRELATION-ATTRIBUTABLE needs at least 4 seeds where the pooled arm passes S2, the other two outcomes at least 4 where it fails, so at most 5 seeds rule out overlap. LINE LOAD SUFFICIENT, CORRELATION WORSENS and LINE-LOAD-LIMITED cannot both hold on one seed. It is exclusive and exhaustive, with the NOT ESTIMABLE precondition.
- s = 100 reading: not exclusive (finding m1).
- Part D: unchanged and exclusive.
- Cost: the added plain-E1 checks per reported arm and the second `twin_A` call stay within the stated 1-1.5 h allowance, so I did not report them.
