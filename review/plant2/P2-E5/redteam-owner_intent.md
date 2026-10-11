# P2-E5 draft red-team: owner intent lens

Fresh reviewer given only the files (draft at commit e736e81); each finding then checked by a separate refuter. Run 2026-10-10 to 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

The draft keeps the core of the owner's rulings. It sets up a prospective gate on fresh seeds 21-25, at s = 60 (about 16 % sibling overlap) and M = 500 and 1,000. The P2-E3 system is frozen and no mechanism is added. Lower- and higher-overlap arms are included, generalisation is reported and never gated, and the correction is left to a separate contract, with the error-correcting write named as an approved direction. It should not be frozen as written, for three reasons. (1) Its failure branch assumes the responder write is the cause. Exploration on seeds 44 and 45 says that holds only at M = 500. At M = 1,000 the memory index itself fails C2 (0.465-0.48), and the plateau-set reference fails too (0.155-0.18). So 'investigate against the plateau-set baseline' and 'a mechanism aimed at the identified cause' cannot be decided from the draft, and an index failure needs to go to the owner. (2) The new signed-drift validity bar (0.1 mV) would have made P2-E3's own seed 14 INVALID at M = 1,000, and exploration seed 45. The baseline the owner asked for could then end as INVALID rather than FAIL. (3) It has no Decision section: it does not say that P2-E3's PASS stands, scoped, that Stage 2 waits, what a PASS licenses, or what INVALID triggers. 'The target a correction must beat' invites comparing against the failing numbers rather than the unchanged bars. On usefulness for choosing the correction mechanism, the draft states the cause backwards. Siblings' cells receive x's lines, and x's own recall is damaged afterwards, by later siblings writing onto x's cells. The draft also measures nothing at write time, though cheap replays would show where contamination lands and whether the mismatch between input and regenerated content can be credited to the right cells. On settled against online: gate the settled protocol only, as drafted. That follows ruling 1 and keeps online and structure as separate tests, as the owner set them. But say that P2-E3's protocol is the most favourable one for the responder write (addendum 2), and add one reported online-rhythm learning arm with store swaps. In exploration, online learning makes the responder write's contamination worse (joint 0.055-0.065 against 0.105-0.145), while the plateau-set reference does not depend on the protocol.

## Findings

### FID5-1 [major] The FAIL branch presumes the cause is the responder write, but at M = 1,000 the index and the plateau-set reference fail too; no predeclared rule attributes the failure, and there are no split labels

- where: /home/user/brain-sim/docs/plant2/P2-E5-structured-items.draft.md L28-29 (cause), L107-110 (verdicts), L114-116 (plateau-set arm), L139-142 (predictions: 'C2 probably holds'; plateau-set only at M = 500), L149-156 (If it fails); DECISIONS.md ruling 4 ('investigate the responder-based feedback write ... against the plateau-set baseline')
- evidence: EXPLORATORY (~/.cache/brain-sim/review/p2e5-redteam/fidelity/where.py; s = 60, F = 10, frozen P2-E3 values, P2-E3's learning protocol; seeds 44 / 45).
- M = 500: C2 0.92 / 0.915; joint 0.145 / 0.105; plateau-set store 0.93 / 0.94; 2.9 spurious memory responders per half cue. Here contamination is in the feedback write, as the draft says.
- M = 1,000: C1 0.935 / 0.915 and C2 0.48 / 0.465, so S1 FAILS. P2-E3 on independent items at M = 1,000 had C2 0.975-1.0.
- M = 1,000, responders: 16.8 / 18.9 spurious memory responders per cue, against 18.4 / 18.8 of the item's own cells.
- M = 1,000, content: joint 0.000 / 0.000, and the plateau-set store 0.18 / 0.155 (D4 0.16 / 0.09).
- The memory raster does not depend on the feedback store, so the M = 1,000 index failure comes from the forward BTSP store on correlated items. No feedback-write correction can reach that store.
- The methodology lens's independent script gives the same C2 and plateau-set values on both seeds (methodology/s60_F10.jsonl).
- The draft has a single FAIL 'with the failing criteria named', predicts that C2 probably holds, and commits the next contract to 'one mechanism aimed at the identified cause, against the plateau-set baseline'. That baseline itself fails at M = 1,000.
- recommendation: Before freezing:
(a) Add a verdict vector per criterion and load, with split labels: STRUCTURED INDEX FAIL (S1) and STRUCTURED CONTENT FAIL (S2/S4), as P2-E4 did.
(b) Predeclare an attribution reading for each load, from the reported arms. 'Write-attributable': main fails S2/S4, S1 holds, and the plateau-set arm meets S2 and S4 on every gated seed. 'Not confined to the write': S1 fails, or the plateau-set arm fails.
(c) Replace the S1 and plateau-set predictions with the seed 44-45 numbers at both loads.
(d) Add to the FAIL branch: when the reading is 'not confined to the write', record it and put it to the owner before any correction contract. Ruling 4 names the responder write and the plateau-set baseline, and an error-correcting feedback write cannot repair the forward index.
Change no bar.
- independent verifier: **confirmed** (severity should be major): I checked every number. where_e3_s60_seed4{4,5}_M1000.json gives, at M = 1,000: C2 0.48 / 0.465; joint 0.000 / 0.000; plateau-set 0.18 / 0.155 (D4 0.16 / 0.09); spurious memory responders 16.8 / 18.9 against 18.4 / 18.8 own. The methodology file s60_F10.jsonl gives the same values, but it uses the same generator. A third implementation draws its items independently (implementation/fam5.py, streams 20-23) and agrees: C2 0.495 / 0.47 and plateau-set 0.16 / 0.12. P2-E3's records at M = 1,000 have C2 between 0.975 and 1.0. The finding says the memory raster cannot depend on the feedback store, and the code bears this out: E3 never connects fb to the network, and rec is only replayed, so the index failure comes from the forward store. Attribution is borderline even at M = 500: in fam5 on seed 44, C2 is 0.895 and plateau-set D4 is 0.88, both under the bar. That strengthens the case for a predeclared reading at each load. P2-E4's labels ONLINE INDEX FAIL and ONLINE CONTENT FAIL are the model to follow. One overlap: part (c) is already promised by the draft (L134-135).

### FID5-2 [major] The cause is stated in the wrong direction, and the diagnostics miss what an error-correcting write would need: where contamination lands, and the mismatch at write time

- where: /home/user/brain-sim/docs/plant2/P2-E5-structured-items.draft.md L28-29 ('Sibling assemblies fire during the continuation and write their own lines into x's feedback'), L124-130 (per-load diagnostics), L151-156; DECISIONS.md ruling 4 (the error-correcting write's contract must test useful error information and the preservation of unrelated memories)
- evidence: The write sets R(x) x E(x): sibling cells that fire in x's continuation receive x's lines, not the reverse.
EXPLORATORY (where.py; s = 60, M = 500; seeds 44 / 45):
- Extra continuation responders number 51.9 / 54.8 per item. Of these, 99.7 % / 99.8 % are cells of earlier siblings' assemblies; about 20 % of cells are such cells.
- In x's own half-cue recall, a median 93 % of the input to intrusion lines comes from x's own assembly cells.
- Those intrusions are mostly lines that only later siblings have (mean 47.9 / 40.0), against 2.4 / 2.3 lines that only earlier siblings have, plus 36.6 / 35.8 prototype lines x lacks. So x is damaged afterwards, by later siblings' writes onto x's cells.
- Write-time regeneration: rec replayed through the store as it stood before x's write, over x's own logged encoding raster. (P2-E4 runs a live rec through encodings, so this quantity exists in the system.) A median of 501 / 459 lines is regenerated: all 40 of x's prototype lines, 7.4 / 6.7 of its 60 specific lines, all 60 prototype lines x lacks, and 353 / 328 earlier-sibling-specific lines.
- The mismatch is informative: the missing lines are x's specific lines, and the extra lines are the family's other lines. But 52-55 of the 72-75 active cells belong to siblings, so a depression driven by the mismatch would mostly hit synapses that carry the siblings' own memories.
- At M = 1,000, write-time regeneration reaches 3,043 / 3,189 lines: saturated.
The draft lists 'sibling responders in the continuation' and an intrusion split. It does not record their direction, which responders carry the intrusions, or anything at write time.
- recommendation: Correct the cause sentence. Add three reported, untuned measurements. They add no mechanism and are replayed from logged rasters:
(1) intrusions split into lines only later siblings have, lines only earlier siblings have, lines both have, prototype lines not in the item, and other lines;
(2) the share of input to intrusion lines from the item's own assembly cells, against spurious responders;
(3) write-time regeneration over each item's encoding and continuation, through the store before its write, split by line class and by responder class (own, earlier sibling, other), for a fixed subset of items at each load.
State that these inform the choice of the next mechanism but do not make it.
- independent verifier: **partly** (severity should be minor): The direction error is real. The code writes fb.add(R(x) x E(x)), so sibling responders receive x's lines; they do not write their own. The data agree: lines only later siblings have average 47.9 / 40.0, against 2.4 / 2.3 for lines only earlier siblings have, and a median 0.93 of intrusion input comes from x's own cells. The same wrong sentence appears in EVAL-after-P2-E3.md, so the error has spread. The write-time regeneration numbers (501 / 459 lines; 7.4 / 6.7 specific lines) are computed correctly from the pre-write store. Two parts do not hold as stated. First, measurement (3) answers a design question for the error-correcting write, and ruling 4 assigns that question to the mechanism's own contract. The runs are deterministic, so (3) can be recomputed later without touching any gated number, and it is not a condition for freezing. Second, '52-55 of 72-75 active cells' counts continuation responders, not the cells active during encoding, so the claim about which synapses a depression would hit is approximate. Fix the sentence and add the cheap later / earlier / both split and the own-versus-spurious input share; (3) is optional.

### FID5-3 [major] Settled-only gating is right, but the draft does not say that P2-E3's protocol is the most favourable one for the responder write, and it has no online-rhythm arm

- where: /home/user/brain-sim/docs/plant2/P2-E5-structured-items.draft.md L43-50 ('Everything is P2-E3 exactly ... quiet() between items'; 'P2-E4 isolates online operation ... must later pass both'); P2-E3 Addendum 2; P2-E4-online-memory.md limitations ('The responder write's specificity depends on the operating point at write time') and Decision ('Any later change to the write ... must re-pass P2-E4's gates')
- evidence: The draft never cites P2-E3 addendum 2.
EXPLORATORY (where.py online mode, which is the P2-E4 red-team's online line: no quiet(), a 250 ms interval with probes; s = 60, M = 500; seeds 44 / 45). The online line is compared with P2-E3's protocol on each measure:
- |R|: 105 / 111 online against 72 / 75;
- Jaccard: 0.22 / 0.21 against 0.32 / 0.31;
- continuation offset: 4.39 / 4.43 against 5.62 / 5.69 mV;
- settled joint through the online-written store: 0.055 / 0.065 against 0.145 / 0.105;
- plateau-set store: 0.93 / 0.94 under both protocols.
So the operating point makes the responder write's structural contamination worse, and the plateau-set reference does not depend on the protocol. Ruling 1 asks for the existing (settled) criteria, and P2-E4 already gates online recall on independent items. Gating settled therefore keeps the owner's separation of the two questions and makes a FAIL unambiguous.
- recommendation: Keep the gate settled. In 'Why' or 'Hypothesis', state that P2-E3's back-to-back protocol (quiet() between items) is the responder write's most favourable operating point (addendum 2). A PASS is therefore scoped to it, and a FAIL is not an artefact of the operating point.
Add one reported, untuned arm at s = 60 and both loads: learning on P2-E4's frozen online rhythm (its driver exists), then the same settled test, read through the arm's own store, the same-seed P2-E3-protocol store and the plateau-set store.
Do not gate structured recall online here. State that the joint condition (structured and online) is untested, and that any correction must re-pass the gates of P2-E3, P2-E4 and P2-E5 on fresh seeds.
- independent verifier: **partly** (severity should be minor): The numbers check out against where_online_*.json and the e3 outputs: |R| 105 / 111 against 72 / 75; joint 0.055 / 0.065 against 0.145 / 0.105. The draft cites only addendum item 3, never addendum 2. But L48-50 already separates the protocol question and requires both protocols for Stage 1. P2-E4's limitations and Decision already state that the write depends on the operating point, and require a changed write to re-pass P2-E4's gates. 'Most favourable' is shown only against the two rhythms tested (250 ms online, 2 s interval). The plateau-set arm's protocol invariance holds by construction, because the forward store and E are identical across protocols. The online arm cannot change any decision in this contract: the gated verdict is expected to be FAIL even under the favourable protocol. That arm belongs in a correction's contract. A one-line scope statement is worth adding.

### FID5-4 [major] The new convergence validity bar would make the baseline INVALID rather than FAIL

- where: /home/user/brain-sim/docs/plant2/P2-E5-structured-items.draft.md L91 ('every value is frozen from P2-E2 and P2-E3'), L104-105 (|signed mean drift| <= 0.1 mV), L110; P2-E3-content-completion.md validity (mean |dvbar| <= 0.2 mV, signed drift reported); review/plant2/P2-E2/findings-methodology.md F7 (recommends signed drift, sets no bar)
- evidence: Recorded values (bench/results/plant2.jsonl, P2-E3 kill_test_seed): signed drift at M = 1,000 was -0.024, -0.072, -0.070, -0.110 (seed 14) and -0.072 mV. Under |signed drift| <= 0.1 mV, the existing system on its own items would have been INVALID on seed 14.
EXPLORATORY, s = 60 at M = 1,000: -0.076 mV on seed 44 and -0.117 mV on seed 45. Seed 45's mean |dvbar| is 0.122, which is valid under P2-E3's rule.
Signed drift grows with load: P2-E3 at M = 1,500 recorded -0.081 to -0.186 mV.
The owner asked for a baseline record of the existing system. An INVALID seed loses that record and needs an owner's ruling to re-run.
- recommendation: Keep P2-E3's convergence rule unchanged as the validity check, and report signed drift beside it. If the signed rule is adopted instead, set its bar before freezing from the recorded distribution, with margin (for example 0.2 mV), and label the bar as new. Remove 'every value is frozen from P2-E2 and P2-E3' unless it is true.
- independent verifier: **confirmed** (severity should be blocker): P2-E3's validity rule (L161-162) is mean |dvbar| <= 0.2 mV with the signed value reported; P2-E2's F7 recommended signed drift but set no bar. The draft adds |signed| <= 0.1 mV while claiming that every value is frozen. Under that rule, P2-E3's own seed 14 at M = 1,000 (-0.110) would be INVALID. At s = 60 and M = 1,000, two exploratory lenses with different item draws give -0.076 / -0.085 on seed 44 and -0.117 / -0.114 on seed 45. Other arms land near the bar too: s = 40 -0.110 / -0.127, s = 80 on seed 45 -0.101, F = 20 on seed 45 -0.100. On the same seeds, s = 60 adds about 0.03 mV of magnitude over s = 100 (-0.045 to -0.08; -0.088 to -0.115). With five gated seeds, at least one INVALID is more likely than not, so the run would most likely lose the baseline record the owner ordered. I raise this to blocker: the fix is trivial, but the draft cannot be frozen with this bar.

### FID5-5 [major] No Decision section: consequences of PASS, FAIL and INVALID, P2-E3's scope, the hold on Stage 2, and the 'target to beat' wording

- where: /home/user/brain-sim/docs/plant2/P2-E5-structured-items.draft.md L6-10, L68 (s = 100 arm), L107-110, L146-147 ('it fixes the target that a correction mechanism must beat'), L149-156; DECISIONS.md ruling 1 ('P2-E3 is unchanged. Its PASS stands, scoped'), ruling 4, execution order (after P2-E4, before any Stage 2 work); P2-E4-online-memory.md 'Decision (predeclared)'
- evidence: The draft never states:
- that a FAIL leaves P2-E3's PASS standing, scoped to independent items and to its protocol;
- that Stage 2 work waits on this result;
- what a PASS licenses (Stage 1's structured clause only, under the settled protocol, at s = 60 and F = 10);
- what an INVALID triggers.
'The target that a correction mechanism must beat' invites comparing a later mechanism with this FAIL (joint about 0.1-0.15), rather than with the unchanged bars.
The s = 100 arm re-runs P2-E3's generator on fresh seeds 21-25, which makes it a P2-E3 replication, and no reading is given for it.
'The candidate the owner approved' reads as the default mechanism. The other class of fix raised in review, keeping sibling assemblies out of the write (P2-E3 skeptic review, next steps), is not mentioned.
- recommendation: Add a Decision section covering each outcome.
- PASS: Stage 1's structured clause is met for the P2-E3 system under the settled protocol only. Stage 1 still needs online memory and capacity. Any later change to the write re-passes the P2-E3, P2-E4 and P2-E5 gates on fresh seeds.
- FAIL: record it. P2-E3's PASS stands, scoped. No parameter is retuned and no Stage 2 work starts. The next step follows ruling 4, with the mechanism chosen from the predeclared readings (FID5-1, FID5-2); the error-correcting write is one approved direction among others.
- INVALID: goes to the owner.
Also state that the s = 100 arm is reported and cannot reopen P2-E3. Reword L146-147: the bars stay unchanged for any correction, and the plateau-set arm is the reference.
- independent verifier: **partly** (severity should be major): The draft has no Decision section, no run-once or re-run rule, no consequence for INVALID and no stated scope for a PASS. P2-E4 has 'Decision (predeclared)' and 'Run once'. The INVALID path matters most here, given FID5-4. The 'target ... must beat' wording (L146-147) is real, and so is the s = 100 arm on gated seeds with no stated reading (exploratory: joint 0.98 on seeds 44 / 45). Three parts are overstated or wrong. P2-E3's PASS standing and the hold on Stage 2 are already fixed by ruling 1 and the execution order, so restating them is a nicety. 'Cannot reopen P2-E3' is the wrong rule: a replication failure on fresh seeds should be recorded as one and put to the owner, as P2-E3 did with its REPLICATION FAIL label. 'One approved direction among others' overstates ruling 4, which approves only the error-correcting write. The draft's 'approved as a research direction' is faithful; it should add 'not an assumed solution'.

### FID5-6 [minor] The draft does not record what the experimenter still supplies, and the family design adds a supplied choice that is not argued (F = 10)

- where: /home/user/brain-sim/docs/plant2/P2-E5-structured-items.draft.md (no limitations section), L54-61 (F = 10; item k in family k mod F); DECISIONS.md 'Standing' ('Every experiment is evaluated by whether it reduces the cognition the experimenter supplies'); P2-E4-online-memory.md 'Labelled limitations'; EVAL-after-P2-E3.md list
- evidence: P2-E4 lists what the experimenter supplies: the write oracle, the key, the value, the operating point and the input statistics. P2-E5 lists none of these. It removes no supply and adds one: the item distribution, which includes hidden prototypes, s, F = 10 (so 50-100 siblings per family) and the cyclic order.
Family size matters for this result. x's recall is damaged by later siblings writing onto its cells (FID5-2), so F sets how many writers each item faces. F = 10 comes from the reviewer's first exploratory script; no argument is given for it.
- recommendation: Add the EVAL list with each item marked as kept, and state that this diagnostic removes none. Justify F = 10 by argument before freezing, or add one reported, untuned F arm (for example F = 40). Then neither a FAIL nor a later correction can be read as specific to one family size.
- independent verifier: **confirmed** (severity should be minor): The draft has no limitations section; P2-E4 has 'Labelled limitations', and the Standing rule asks what the experimenter supplies. F = 10 comes from the first exploratory script: families.py, whose fam2_*.txt headers read 'F 10'. The methodology lens's F arms show F matters more than the finding argues. With F = 20 on seed 44, M = 500 gives joint 0.405 and plateau-set 0.995, and M = 1,000 gives C2 0.66 and plateau-set 0.52. With F = 40 on seed 45, M = 500 gives joint 0.765, and M = 1,000 gives C2 0.74 and plateau-set 0.85. The FAIL verdict holds across F (main joint at M = 1,000 between 0.0 and 0.045), but the index-versus-write attribution in FID5-1 depends on F. So F should be argued, or one F arm reported.

### FID5-7 [minor] The prototype and new-exemplar cues need ruling 5's label and a stated purpose

- where: /home/user/brain-sim/docs/plant2/P2-E5-structured-items.draft.md L81-83, L128-129; DECISIONS.md ruling 5 ('Averaging or superposition at retrieval does not count as learned abstraction'); EVAL-after-P2-E3.md 'Toward abstraction'
- evidence: In the earlier exploration, the never-seen prototype's half cue read through the plateau-set store regenerates the whole prototype with 12-18 intrusions, because 80-89 memory cells from many sibling assemblies respond (EVAL; ~/.cache/brain-sim/review/p2e3-northstar/fam2_60_p.txt). That is superposition at retrieval, and as a reported number it could later be cited as a prototype effect.
The new-exemplar cues are useful here for a different reason. They measure index-level cross-talk: memory cells answering a family member that was never stored. That is one way contamination can enter.
- recommendation: Keep both cue sets as reported measures. Label the prototype cue as retrieval-time superposition that counts for nothing under Stage 3 (ruling 5). State that the new-exemplar cue measures index cross-talk, not generalisation.
- independent verifier: **confirmed** (severity should be minor): In fam2_60_p.txt, prototype cues through the plateau-set store regenerate the prototype with nmem 89 and 18 intrusions; EVAL describes this as superposition by the count threshold. Ruling 5 says superposition at retrieval does not count as learned abstraction. The draft only says that generalisation is 'reported, never gated'. New-exemplar cues light about 2 memory cells, so labelling them as an index cross-talk measure is accurate. The label is cheap insurance against later misuse; the risk is low, because ruling 5 already governs Stage 3.

### FID5-8 [nit] S1 drops P2-E2's C4, and 'bits per synapse' is out of scope

- where: /home/user/brain-sim/docs/plant2/P2-E5-structured-items.draft.md L95 (S1 = C1, C2, C3), L130; P2-E3 D5 (C1-C4); P2-E2 contract (C4: C1 and C2 within the oldest 100)
- evidence: Ruling 1 says the test is scored with 'the existing ... criteria'. P2-E3's D5 gated C1-C4. C4 is index recall and specificity for the oldest items, which are the items exposed to the most later-sibling writes. Bits per synapse is a measure for the capacity contract.
- recommendation: Gate C1-C4 as P2-E3's D5 did, or state why C4 is dropped. Report bits per synapse only if it costs nothing.
- independent verifier: **confirmed** (severity should be nit): P2-E3's D5 gates P2-E2's C1-C4, and the code's gate_ok includes C4 (e2.summary). Ruling 1 and STAGES say 'existing ... specificity criteria', yet S1 lists only C1-C3 and gives no reason. Dropping C4 does not change the verdict: C2 already fails at M = 1,000, and S4 covers the oldest items' content. Whether to report bits per synapse is a preference.

## Exploratory runs (labelled; not results)

- `~/.cache/brain-sim/review/p2e5-redteam/fidelity/where.py (args: 44 e3 1000 60)` (seed 44; Full P2-E3 contract (J 1.525, J_fb 2.80, g 0.3); P2-E3's learning protocol statement for statement plus raster logging; draft generator s = 60, F = 10, item k in family k mod F; settled test with P2-E3 run_phase on a deep copy; loads 500 and 1,000. EXPLORATORY, not a result.): M = 500 (responder figures over items 401-500):
- |R| 71.9, Jaccard 0.32, continuation offset 5.62 mV.
- Extra responders 51.9 per item: 99.7 % earlier-sibling assembly cells, 0.17 other, 0 none.
- Memory: C1 0.97, C2 0.92, C3 1.0.
- Joint 0.145 (D2 0.15, D4 0.02); plateau-set 0.93 (D4 0.92).
- Intrusions per half cue (mean): 36.6 prototype lines the item lacks, 47.9 lines only later siblings have, 2.4 only earlier siblings, 8.2 both, 4.4 other.
- Share of intrusion input from the item's own assembly cells: median 0.93. Spurious memory responders 2.9 per cue.
- Write-time rec over x's encoding (median 501 lines): x-prototype 40/40, x-specific 7.4/60, prototype lines x lacks 59.9, earlier-sibling-specific 353, other 18.
M = 1,000:
- |R| 153, Jaccard 0.16, offset 11.6 mV.
- Memory: C1 0.935, C2 0.48, C3 0.995. Spurious responders 16.8 per cue against 18.4 own.
- Joint 0.000; plateau-set 0.18 (D4 0.16).
- Own-cell share of intrusion input 0.60. Write-time encoding regeneration 3,043 lines.
- Signed drift -0.076 mV.
- `~/.cache/brain-sim/review/p2e5-redteam/fidelity/where.py (args: 45 e3 1000 60)` (seed 45; As above. EXPLORATORY.): M = 500:
- |R| 74.9, Jaccard 0.31, offset 5.69 mV. Extra responders 54.8 per item, 99.8 % earlier-sibling cells.
- Memory: C1 0.945, C2 0.915.
- Joint 0.105 (D4 0.05); plateau-set 0.94 (D4 0.92).
- Intrusions (mean): 35.8 prototype lines the item lacks, 40.0 only later siblings, 2.3 only earlier siblings. Own-cell share 0.93.
- Write-time encoding (median 459 lines): x-prototype 40, x-specific 6.7, prototype lines x lacks 60, earlier-sibling-specific 328.
M = 1,000:
- |R| 164.
- Memory: C1 0.915, C2 0.465, C3 1.0. Spurious responders 18.9 per cue against 18.8 own.
- Joint 0.000; plateau-set 0.155 (D4 0.09).
- Own-cell share 0.58.
- Signed drift -0.117 mV, which would be INVALID under the draft's 0.1 mV rule; mean |dvbar| 0.122, valid under P2-E3's rule.
- `~/.cache/brain-sim/review/p2e5-redteam/fidelity/where.py (args: 44 online 500 60; uses online_p2e4rt.py, a copy of the P2-E4 red-team's online line)` (seed 44; Same items. No quiet(), 250 ms interval (50/100/100) with probes (recent 25 %, uniform 25 %, novel 15 %, blank 25 %, full 10 %), no live rec. Settled test on a deep copy at M = 500. EXPLORATORY; not P2-E4's frozen driver.): - |R| 105, Jaccard 0.22, continuation offset 4.39 mV. Extra responders 84.8 earlier-sibling cells per item.
- Joint through the online-written store 0.055 (D4 0.0).
- Plateau-set 0.93.
- Memory C1, C2 and C3 equal to the P2-E3-protocol line, as expected: the forward store is identical.
- `~/.cache/brain-sim/review/p2e5-redteam/fidelity/where.py (args: 45 online 500 60)` (seed 45; As above. EXPLORATORY.): - |R| 111, Jaccard 0.21, offset 4.43 mV.
- Joint through the online-written store 0.065 (D4 0.01).
- Plateau-set 0.94.
- `inline read of /home/user/brain-sim/bench/results/plant2.jsonl (P2-E3 kill_test_seed records)` (seed 11-15 (recorded, no new simulation); Arithmetic on recorded settle drift and learning summaries.): - Signed drift at M = 1,000: -0.024, -0.072, -0.070, -0.110 (seed 14) and -0.072 mV. Seed 14 would fail the draft's |signed| <= 0.1 mV rule.
- P2-E3 on independent items at M = 500: continuation offset 4.5 mV, |R| 20.7, Jaccard 0.97.
- So the s = 60 explosion of |R| at M = 500 (72-75) is structural, not an effect of the operating point.

## Reviewer's predictions

For the draft run as written on seeds 21-25, based on two exploratory seeds (44 and 45):
- **S2 (content joint):** FAILS at both loads, about 0.10-0.15 at M = 500 and about 0 at M = 1,000.
- **S4 (oldest items):** FAILS, about 0.0-0.05 at M = 500.
- **S3 (novel cues):** holds (0.985-1.0).
- **S1 (memory index):** FAILS at M = 1,000 on C2 (about 0.45-0.50; C1 about 0.92-0.94). It is borderline at M = 500 (C2 about 0.91-0.92), where a 5-seed failure is plausible.
- **Plateau-set arm:** about 0.93-0.94 at M = 500 (D4 about 0.92), and about 0.15-0.20 at M = 1,000.
- **Validity:** the draft's |signed drift| <= 0.1 mV rule makes at least one INVALID seed at M = 1,000 likely, since 1 of 2 exploration seeds and 1 of 5 P2-E3 seeds exceed it.
- **Online-rhythm learning arm, if added:** |R| about 105-110 and joint about 0.05-0.07 at M = 500, with the plateau-set store unchanged at about 0.93.
- **Expected labels:** STRUCTURED CONTENT FAIL at both loads, plus STRUCTURED INDEX FAIL at M = 1,000. The cause can be attributed to the responder write only at M = 500.
