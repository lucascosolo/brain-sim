# P2-E3 review: north-star lens (constructive)

Fresh reviewer given only the files (review packet in the workflow prompt; no implementer history). Model: session default. Run 2026-10-10. Recorded verbatim, before synthesis.

## Verdict

Yes, as a substrate, not yet as evidence. P2-E3 gives fast (23-28 ms), one-shot, specific regeneration of stored input in input coordinates, with a wide J_fb window (2.00-3.60 mV, about +/-29 %). Prediction, recognition, replay and consolidation all need this. By itself it does not advance sequences, abstraction or problem solving. The content is a verbatim copy keyed to a random plateau index, rec projects nowhere, and items are uniform random of one size, tested on frozen copies. No Stage 2-6 gate is unlocked, and Stage 1 still needs online memory and capacity. Three design facts set the path: index-level transitions, familiarity-gated allocation and the wording of the Stage 3 gate.

## Findings

### F1 [major] Content path is verbatim and a dead end: it enables learning but does not show it

- where: plant2/readout.py; p2_e3_completion.py E3.learn_one; P2-E3 Result 'What it does not show'
- evidence: rec has no outgoing projection and is not simulated during learning. The feedback stores the encoding's eligible lines against R(x), labelled as input-supervised hetero-association. Items are uniform random, a=100, 40 Hz, tested on frozen copies after a 50 s settle. Stored information is about 670 bits per item x 1,000 items over 3.05 M binary synapses, about 0.22 bits per synapse (the Willshaw asymptote is about 0.69).
- recommendation: Record in STAGES that P2-E3 meets Stage 1's content clause and unlocks no later gate. Claim progress toward sequences or abstraction only once the system itself uses regenerated content: in a loop, a comparator or replay.

### F2 [major] Content-only chaining cannot meet Stage 2's context bar; index-level transitions are needed

- where: STAGES.md Stage 2 gate; review/plant2/P2-E2/findings-direction.md F6
- evidence: Chaining through rec content is first-order Markov. A shared item with b successors resolves at most 1/b of the time: 0.5 at b=2, against the 0.80 bar. Random plateaus already give each occurrence its own assembly, a natural 'clone'. mem is silent in background, so BTSP's -3..+2 s window on mem->mem stays sparse (about 23 cells per item) when items come every 1-2 s.
- recommendation: Make Stage 2's primary mechanism BTSP on mem->mem with the forward window, and read content via P2-E3. Add a content-only (Markov-1) arm, predicted <= 0.5 on shared items. Keep the item's own continuation out of the window: within-assembly links ran away to 2,889-3,969 cells in P2-E1's review (F6).

### F3 [major] Allocation ignores familiarity, so re-exposure duplicates memories

- where: P2-E4 draft protocol; random plateaus (p2_e1_btsp.learn_one); P2-E3 D3
- evidence: Plateaus do not depend on content, so a re-exposed item gets a second assembly: about 1,000 forward plus 2,000 feedback synapses, one item's worth. If items recur r times, distinct capacity divides by r, and maps and trials never reuse an index. The P2-E4 draft never re-presents a learned item for learning. A familiarity signal already exists: learned half cues regenerate >= 0.96 of their lines, novel cues a median of 0 (D3 0.99-1.0).
- recommendation: Add a reported re-exposure arm to P2-E4. After Stage 1, the next mechanism: plateau probability gated by the network's own mismatch (input lines that rec did not regenerate), labelled as a novelty proxy. It is the first internal use of the content path.

### F4 [major] P2-E4 draft: O4 and O5 can fail from item sampling alone

- where: P2-E4-online-memory.draft.md, Kill test O4/O5
- evidence: O5 requires all 10 repeated items to pass. At P2-E3's M=1,000 joint rates (0.955-0.985), P(10/10) is 0.63-0.86 per seed. With M=500 included, the chance of passing on all five seeds is about 0.2 with no habituation at all. O4's pairs are correlated within an item, so its effective sample is about 10 items. At C1 0.925-0.955, one or two weak items reach the 0.90 bar without any habituation.
- recommendation: Use >= 50 items per arm. Score only items that pass at repetition 1, and gate a within-item ratio (late repeats over the first 5) with a binomially justified bar. Predeclare the verdict name for an O4-only FAIL and the line's next step.

### F5 [major] P2-E4 scope misses the online regimes that lifelong learning faces

- where: P2-E4 draft protocol and 'Reported'
- evidence: Past capacity, content collapses for items of every age: at M=1,500, joint 0.185-0.290 and D4 0.15-0.22. The clipped feedback never depresses, so it is no palimpsest. The operating point depends on duty (P2-E2 addendum 4): 2 s gaps give 11 % item duty against 33 % in test blocks. The online cost is never measured within a seed. Plateaus occur only inside encodings, so the experimenter still signals when to write.
- recommendation: Report online loads of 1,500 and 2,000, a 0.5 s-gap duty arm, and a paired settled-copy arm at each gated load. Label episode boundaries as an experimenter-provided write signal, to be removed before Stage 2.

### F6 [major] The memory operating point is tuned to one item size; generalisation is untested

- where: P2-E2 J* = 1.525; plant2/predict.py; every P2 item set
- evidence: Exploratory predictor run (M=1,000, J 1.525, accommodation, settle state): P(a written cell fires within 50 ms) is 0.17 at 12 strong cue synapses, 0.47 at 15 and 0.997 at 25. A half cue of a 50-line item gives about 12, so C1 would fail. 200-line items double the writes per plateau and the load effect. Every run so far uses independent 100-line items at 40 Hz. The readout's fraction vote does not depend on size; the memory threshold does.
- recommendation: Add an untuned transfer battery as reported arms in P2-E4 and P2-E5: a = 50 and 200, correlated items, other rates. Make cue-size invariance an explicit target for a later mechanism.

### F7 [major] Stage 3's prototype criterion can be passed by blending (surrogate)

- where: STAGES.md Stage 3 gate
- evidence: Exploratory surrogate, not a plant2 run (P2-E3 index plus Willshaw/FFI vote, memory firing from the predictor; ~/.cache/brain-sim/review/p2e3-northstar/proto.py). At distortion d <= 0.3 with n >= 8 exemplars, the unseen prototype's half cue regenerates 1.00 of it. An exemplar's half cue keeps only 0-5 % of its own idiosyncratic lines, with 10-28 intrusions. At d 0.4-0.5 with n=16, the prototype reaches 0.93-1.00 and exemplars stay verbatim (1.00, 0-5 intrusions).
- recommendation: Ask the owner to amend Stage 3 so prototype regeneration must hold jointly with exemplar specificity. Interference alone then cannot pass it.

### F8 [minor] Stage 3's label-efficiency bar is unreachable where retrieval helps

- where: STAGES.md Stage 3 gate
- evidence: Same surrogate, 10 classes. Nearest-centroid on raw sparse exemplars reaches >= 0.95 with 1 label per class at d <= 0.7. At d=0.8 it needs 4 labels for 0.92, and at d=0.9 it reaches 0.47 with 16. Superposition helps only where exemplars co-ignite (d <= 0.5), and there raw input already needs 1 label. At d=0.8 exemplar pairs share about 6.5 lines and never co-ignite.
- recommendation: Run Stage 3 at d of about 0.8, where any label gain must come from a learned representation. Its primary mechanism is a slow learner trained only on internally regenerated content (replay).

### F9 [minor] The readout expresses about three co-active memories at most

- where: plant2/readout.py (g = 0.3 fraction vote); Stages 2 and 6
- evidence: Exploratory: a synthetic raster replayed through plant2.readout at M=1,000 density (coactive.py). Lines regenerated: 1.00 with 1-2 co-active assemblies, 0.98 with 3, 0.71-0.75 with 4. At g=0 the readout floods (560-3,533 intrusions). So chained replay must switch off earlier steps, and four bindings held at once (Stage 6) cannot all be read in parallel.
- recommendation: Stage 2 contracts gate that at most two earlier assemblies stay active during replay. Plan Stage 6's readout as cued or sequential.

### F10 [minor] Accommodation habituation conflicts with later stages; a principled tau exists

- where: P2-E2 addendum 6; P2-E4 draft O4
- evidence: At tau 10 s, a held cue raised the assembly's vbar by 5.2 mV over 30 s, and Stage 6 needs 10 s holds. Online, load changes slowly: one item per 2.25 s is about 4 % of M=1,000 per 100 s. A tau of >= 100 s would separate the two timescales (speculative).
- recommendation: If O4 fails, keep the FAIL. Change tau only through a new contract that derives it from timescale separation, calibrates on a held-out seed and has the owner's ruling, since the mechanism is in the gated family.

### F11 [nit] Track robustness and efficiency, not only pass fractions

- where: P2-E2 and P2-E3 calibration results
- evidence: Relative width of the passing window: about +/-5 % for P2-E2's J (1.45-1.60 mV), about +/-29 % for P2-E3's J_fb (2.00-3.60 mV). The stores hold about 0.22 bits per synapse.
- recommendation: Report window width and bits per synapse in every contract. Flag operating windows narrower than +/-10 % as fragile.

## Next steps

- P2-E4, online memory: no new mechanism, required by the owner. Before commit, fix F4's statistics and add reported arms: re-exposure, beyond capacity (1,500 and 2,000), 0.5 s-gap duty, paired settled copy, and transfer (a = 50 and 200). Label the episode write signal. Seeds 16-20 are untouched. Measure retention against age, the online minus settled cost, synapses per repeat and a habituation ratio.
- P2-E5, capacity: no new mechanism, owner's design (m and n scale together, a and |A| fixed, memory-only scaling as control). Gate the content criterion D1/2 as well as the index, because content fails first. Exploratory prediction: about 2.2x index capacity at m = n = 8,000, with feedback density halving from 13.4 % to about 7 %. Report bits per synapse.
- If O4 fails: one habituation experiment with one mechanism under a new contract, either tau from timescale separation or a normaliser that tracks load and ignores held cues. It needs the owner's ruling, since the mechanism is in the gated family.
- P2-E6, familiarity-gated allocation. One mechanism: plateau probability scaled by the network's own rec-versus-input mismatch, labelled as a novelty proxy. Gate: a re-exposed item adds <= 10 % of a new item's synapses, novel items are still written, P2-E3's criteria hold, and the store grows with distinct items. Controls: ungated plateaus (duplicates) and shuffled mismatch.
- P2-E7, one-step transitions (Stage 2 entry). One mechanism: BTSP on mem->mem, forward window, items 1-2 s apart. Needs an owner ruling first on activity-proportional inhibition in mem. Gate in content: within 75 ms of cue k, rec shows item k+1 (>= 80 % of lines, < 10 intrusions) on >= 90 % of transitions, and context resolves shared items with 2 successors >= 80 %. Arms: a Markov-1 content chain (predicted <= 0.5) and a reversed window.
- P2-E8, chained replay (the Stage 2 gate). One mechanism: a fast stabiliser such as labelled short-term depression on mem->mem. Gate on STAGES Stage 2 as written, with at most two earlier assemblies active. Speculative prediction: 10-16 ms per step (full-cue latency 10 ms plus 1-6 ms for rec), so 8 items replay in about 0.1 s. Against 250 ms items that is about 20x compression, comparable to hippocampal replay.
- Stage 3: first a diagnostic with no new mechanism, retrieval-time superposition at d 0.4-0.5 and n >= 16, scored on prototype and exemplar specificity together. Then replay-trained consolidation into a slow layer (one mechanism), gated at d of about 0.8 against raw input and a never-trained twin. Stage 4 baseline: episodic control by one-shot (state, action, outcome) content regeneration, before any three-factor rule.
- Generalisation metrics for every contract:
- an untuned transfer battery;
- earlier gates re-run with the new mechanism on;
- online testing by default after P2-E4;
- baselines that bound benchmark-passing (a Markov-1 table, raw-input and kNN readouts, tabular Q);
- relative window width and bits per synapse;
- a list of experimenter-supplied signals that should shrink over time.

## For the owner

P2-E3 is a real, well-controlled step. It enables learning rather than demonstrating it: stored input returns one-shot and specifically, but nothing in the system uses it yet. Your decisions:
1. Approve the P2-E4 fixes: sample sizes, plus re-exposure, beyond-capacity and duty arms.
2. Rule in advance whether Stage 2 may add activity-proportional inhibition in mem. Index-level transitions will likely need it.
3. Amend the Stage 3 gate so blending cannot pass it.
4. Decide whether familiarity-gated allocation comes before Stage 2.
The surrogate figures are exploratory, not results.
