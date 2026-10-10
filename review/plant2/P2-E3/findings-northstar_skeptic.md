# P2-E3 review: north-star lens (skeptic)

Fresh reviewer given only the files (review packet in the workflow prompt; no implementer history). Model: session default. Run 2026-10-10. Recorded verbatim, before synthesis.

## Verdict

P2-E3's PASS is procedurally clean and real for what it tested, but by the north-star lens it adds plumbing, not learning power. It is a spiking Willshaw hetero-associative memory: content-blind random keys (plateaus), values copied verbatim through fixed 1:1 wiring, a hand-set count threshold (g = 0.3), protocol-scheduled episodes, and tests on frozen copies after a 50 s rest, on independent random items only. My labelled one-seed exploration shows content completion collapsing when items share ~16 % of lines (joint 0.993 -> 0.147 at M = 500). The add-only feedback store blacks out past M ~ 1,500. It does not yet move the line toward abstraction, sequences or behaviour.

## Findings

### NS1 [major] Content completion collapses on mildly correlated items, and the responder-based write causes it

- where: plant2/experiments/p2_e3_completion.py E3.learn_one (R(x) write); ~/.cache/brain-sim/review/p2e3-northstar/families.py, families2.py, fam*.txt
- evidence: Exploratory, one seed (99), frozen P2-E3 values, 10 prototype families, prototypes never shown. Same script on iid items: joint 0.993 at M = 500. Siblings sharing ~16 of 100 lines: joint 0.62 at M = 250 and 0.147 at M = 500; |R(x)| is 36-52 against |A| 20, because sibling assemblies fire in the continuation and write feedback. The plateau-set store on the same raster gives 0.94. At ~6.5 % overlap all is fine. At 36-64 % overlap rec saturates (median ~2,740-2,840 intrusions per cue). Every gated test used iid items (~2.5 % overlap).
- recommendation: Scope the P2-E3 claim to independent random sparse items in an addendum. Treat structured input as the open question that gates Stages 2-3. Stage 2 (shared items) and Stage 3 (exemplars of prototypes) are correlated by definition.

### NS2 [major] The architecture is a lookup table with spikes: random key, verbatim value, hand-set threshold

- where: docs/plant2/P2-E1-btsp.md (plateaus independent of content and activity); P2-E3 contract 'Learned path' item 4; Result arms table
- evidence: The keys are plateau cells drawn at f_q = 0.005 regardless of input. The value is E(x) copied onto 1:1 rec lines. Inhibition at g x J per memory spike implements a Willshaw count threshold (about 30 % of active cells). The plateau-set arm equals the main arm (0.980-0.990), and label-permuted feedback regenerates pi(x) at 0.968-0.982: the output is whatever was filed under the key. Counting arithmetic predicted the outcome (2.2 against 19 inputs per line). Efficiency is ~0.04 bits per potential feedback synapse (670 bits per item). Rec has no outputs and feeds nothing back.
- recommendation: Describe P2-E3 as a spiking implementation of Willshaw (1969) hetero-association with random indices. Credit it as plumbing for later chaining and replay, not as learning content or structure.

### NS3 [major] What to store and when is decided by the protocol, an oracle the P2-E4 draft keeps

- where: E3.learn_one (quiet(), plateau draw, write at the end of the continuation); run_phase (deep copy, settle); P2-E4 draft 'Learning'
- evidence: Every episode starts with quiet(). Plateaus occur only in encodings, and the write fires once at a protocol-set tick. Rec is not simulated during learning. Tests run on discarded deep copies with plasticity off, after a 50 s settle (C1 0.875 without it, P2-E2 addendum 3). The P2-E4 draft keeps 'plateaus occur only during encodings', so the system is still told which inputs are new and which are probes. A lure containing 50 lines of stored x is x's half cue: it would be recalled as x and never stored. A repeated item gets a second random key (code reading; untested).
- recommendation: In P2-E4, add a reported arm with plateaus at the same rate during probes and learning, plus lure probes (novel items sharing 50 lines with a stored item). Label store/recall gating as an oracle until a mechanism of the system's own decides it.

### NS4 [major] The add-only feedback store blacks out instead of forgetting, and the P2-E4 draft stops before the wall

- where: plant2/btsp.py BinarySynapses.add; bench/results/plant2.jsonl P2-E3 kill_test_seed loads 1500/2000; P2-E4 draft (M <= 1,000)
- evidence: The clipped write never depresses. Feedback density is 0.133 / 0.23 / 0.36 at M = 1,000 / 1,500 / 2,000. At M = 2,000 a half cue lights a median 2,983-3,545 of 4,000 rec lines, and novel cues up to 4,000; at 1,500 novel cues reach 1,225-3,509. The Result's 'D1 stays at 0.97-1.0' at these loads reflects saturation, which it does not report. At P2-E4's 2.25 s per item, a learner reaches M = 1,500 in about an hour. Human memory degrades gracefully.
- recommendation: Extend P2-E4 past capacity (M to 3,000-4,000) and gate recall of recent items (ages 1-100) at every load: a palimpsest test. It is predicted to FAIL and would name the next mechanism, a bounded or depressing feedback write. Report the saturation in an addendum.

### NS5 [major] The pattern risks benchmark collecting: one calibrated element per failed criterion, tested only in-distribution

- where: STAGES experiment log; P2-E2 and P2-E3 calibration sections; review/plant2/P2-E2/findings-direction.md F2
- evidence: P2-E1 failed, so accommodation was added. A reviewer then predicted no readout window, and g = 0.3 was found by exploration before the contract. J and J_fb are calibrated on seed 0 against the gated criteria at the gated loads. Fresh seeds resample the same iid distribution, so 5/5 measures seed variance, not generalisation. Item code, cue fraction (exactly 1/2), rates, duration and |A| never vary. Each PASS was predicted within a few % by counting. The memory J window is 1.45-1.60 mV (+/-5 %), and the gate load of 0.25 items per cell is the last passing grid point.
- recommendation: From now on, each contract predeclares out-of-distribution arms at frozen parameters, reported and not tuned: correlated items, cue fraction 0.3, noisy cues, other item durations. The record then shows where each mechanism stops working.

### NS6 [minor] 'Inhibition required' holds at one load only. At M = 1,500 no inhibition beats the main arm on every seed

- where: Result 'Secondary claim' and STAGES log; bench/results/plant2.jsonl loads 1500
- evidence: At M = 1,500 the joint score is 0.185-0.290 for main against 0.245-0.345 for matched g = 0, and D3 is 0.75-0.795 against 0.88-0.925, on all 5 gated seeds. At M = 250, g = 0 even at J* gives 0.94-0.98. The element sets an operating band around 0.25 items per cell. It does not extend capacity. Neither the Result nor STAGES says so.
- recommendation: Add to the addendum: inhibition is needed at 0.25 items per cell, unnecessary at <= 0.125 and worse than none at 0.375. Do not cite it as a capacity or scaling mechanism.

### NS7 [minor] Missing capacities, and an operating point that habituates

- where: STAGES Stages 2-6; P2-E2 addendum items 3 and 6
- evidence: There are no self-chosen codes, no recurrence or temporal order (sequences), no error or reward signal (credit assignment), and no behaviour. Regenerated content is used by nothing. Accommodation, the operating-point mechanism, cuts recall >= 0.8 to 0.67 under a 30 s repeated cue and needs 50 s of rest. That conflicts with Stage 4 (repeated stimuli) and Stage 6 (holding for 10 s). Recall never changes the system, because tests run on frozen copies.
- recommendation: Read P2-E4's O4 as a line-level result: if the operating point habituates, it is not a substrate for Stages 4-6, and that is not a parameter to retune.

## Next steps

- Write a P2-E3 addendum: scope the claim to independent random sparse items (~2.5 % pairwise overlap); record the M = 1,500-2,000 saturation numbers; state that inhibition helps only at 0.25 items per cell and loses to none at 0.375 on all 5 seeds.
- Revise the P2-E4 draft before red-team: learn past capacity (M to 3,000+) and gate recent-item recall (a palimpsest test); add lure probes sharing 50 lines with a stored item; add a reported arm with plateaus at the same rate during probes (no store/recall oracle); keep O4 habituation gated, as the owner asked.
- Hardest open question: does anything here learn from structure shared across experiences, rather than filing each under a random key? The most efficient test is a no-new-mechanism contract at frozen values: prototype-family items at 2.5 / 6.5 / 16 / 36 % pairwise overlap, gating exemplar completion at 16 %, and reporting |R|/|A|, the plateau-set store and never-seen-prototype regeneration. It costs about 1-2 min per seed per load. My exploration predicts FAIL.
- If that FAILs, Stages 2-3 cannot rest on content-blind keys with responder writes. The next single mechanism must keep sibling assemblies out of the write, or make codes depend on content, with storage gated by the system, for example input-vs-regeneration mismatch (labelled).
- What would change my mind: at frozen parameters, exemplar completion >= 0.9 at >= 15 % overlap, with a never-seen prototype regenerated more completely than exemplars; and online, self-gated storage past M = 3,000 keeping recent items >= 0.9 with no blackout.

## For the owner

Yes, look now, before P2-E4 is committed. P2-E3 is an honest, well-controlled PASS, but it adds a spiking Willshaw lookup table that works for independent random patterns only. In my labelled one-seed exploration, items sharing ~16 % of lines cut content completion from 0.993 to 0.147 at M = 500. The responder-based write, the rule's one experience-driven part, causes it (plateau-set store: 0.94). Decide whether Stage 1 gets a predeclared structured-input clause, and whether P2-E4 must run past capacity without the store/recall oracle. Otherwise Stage 1 may 'pass' on a substrate that Stages 2-3 cannot use.
