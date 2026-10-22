# Hypothesis ledger

This file lists every hypothesis that the plant2 research programme has stated, tested, or inherited from the recovered plant. Each claim appears once, even when several experiments worded it differently, and every experiment's evidence is kept with it. The primary records are the contracts, results and reviews under `docs/plant2/`, `bench/results/` and `review/`. This ledger is an index over those records with a judgement added. It was built from the experiment records `.agent/ledger/P2-E1.json` to `P2-R2.json`, from `owner-rulings.json` and `recovered-plant.json`, and from the P2-R2b replication result of 2026-10-22. Entries are numbered H-001 upward by theme. Entries are never deleted, only closed. `BACKLOG.md` ids (B-nnn) are cited where an entry is the backlog item's testable form. Last updated 2026-10-22.

Statuses use the README vocabulary, applied strictly. `supported` means a predeclared test came out as predicted on the seeds and loads that the contract named. That test is either a gated criterion or a predeclared reported arm of a live run on fresh seeds; a reported arm never creates a capability. `refuted` means a predeclared test came out against the claim, and a failed gated test gives `refuted` even when some sub-results were positive. `mixed` covers a claim that was supported in some predeclared conditions and refuted in others. The README rules that a claim tested only on development seeds or only by a reported replay is `under_test` or `mixed`, never `supported`; this ledger applies the same rule to a claim whose only favourable evidence comes from exploration seeds, post hoc analysis, an audit of committed records, or a single valid seed. `withdrawn` means the record itself retracted the claim. `unresolved` means the experiment ran but its design could not decide. `proposed` means no experiment has addressed the claim; a reviewer's surrogate, synthetic raster or arithmetic does not count as one. No entry is `under_test` at this date. Confidence (low, medium or high) is a separate judgement of whether the statement is true as written. It can be high for a `mixed` entry whose only weakness is the kind of evidence. Each number carries its label: gated, exploratory, reported-only, INVALID, descriptive or post hoc.

## 1. One-shot index memory and operating point

**H-001** One-shot BTSP storage at a rule-fixed synaptic strength
**Statement.** "A plasticity rule that writes in one exposure without depending on postsynaptic spike timing, with bounded binary weights and no homeostat acting on them, stores many items shown once each in a spiking network. Partial cues then re-evoke the written cells quickly and specifically." The setup is BTSP (Wu & Maass 2025, Eq. 1) with Poisson inputs, background activity, leaky integrate-and-fire (LIF) cells, a 50 ms recall window and J = 1.12 mV fixed by rule. The test is the Stage 1 gate, C1-C5 at M = 1,000 on every seed.
**Origin.** Experimenter, P2-E1 contract, predeclared primary hypothesis (`docs/plant2/P2-E1-btsp.md:28-44`), 2026-10-10.
**Status.** `refuted`
**Confidence.** Low: the predeclared kill test failed on completion on every valid seed.
**Expected outcome if true.** C1 (at least 80 % of the assembly within 50 ms for at least 90 % of items), C2, C3, C4 and C5 all pass on every seed at M = 1,000.
**Evidence for.**
- C2 0.905-0.950 and C3 0.945-0.980 pass on 5/5 seeds. Median recall is 0.920-0.941 at 50 ms and 1.00 at 100 ms; full-cue median recall is 1.0 at 50 ms. Mean |A| is 19.74-19.98 and eligibility 0.987-0.988, as predicted (gated; `docs/plant2/P2-E1-btsp.md:109, 176-193, 240-253`).
- The specificity component held as predicted: spurious responders and novel ignition were predicted at about 3 per cue (bar about 10) and came out at a median of 2 (gated; `docs/plant2/P2-E1-btsp.md:144-145, 208`).
- Reviewer nulls: 0 responders in 200 background-only windows; wrong-cue recall 0.006 (exploratory; `docs/plant2/P2-E1-btsp.md:300-307`).
**Evidence against.**
- C1 is 0.810-0.860 against a 0.90 bar on 5/5 valid seeds. The C4 recall half is 0.820-0.890. C5 fails because C1 fails again after 60 s (0.825-0.880). Verdict FAIL (gated; `docs/plant2/P2-E1-btsp.md:176-193`; `bench/results/plant2.jsonl:1-5`).
- 10.2-11.9 % of written cells respond after the window, and failing items have 3-14 late cells. Median recall at 25 ms is 0.42-0.48 (gated; `docs/plant2/P2-E1-btsp.md:213-219, 283-290`).
- Capacity curve: C1 0.610 at M = 250; C2/C3 0.000 at M = 2,000 (reported-only, seed 1, n = 1; `bench/results/plant2.jsonl:7-11`).
**Tested by.** P2-E1
**Experiment needed.** Settled; see the P2-E1 verdict (`docs/plant2/P2-E1-btsp.md`) and H-004 for the mechanism that followed.
**Notes.** As the contract requires, J, f_q, rates, windows and bars stay as they are, and the configuration is not re-run to pass. The specificity component (C2, C3) passed on its own. C5 is vacuous as designed (H-009). Old-item retention is H-058.

**H-002** Setting J from a predicted count of cue synapses
**Statement.** "Set J so that the predicted mean free-membrane depolarisation of a written cell under its half cue, at the full load M = 1,000, is 1.4 x the 20 mV distance from rest to threshold." The rule gives J = 1.12 mV, with a predicted 27.76 cue synapses, mean 27.9 mV and sd 3.95 mV. The contract added that C1 is the criterion most at risk, with predicted median recall 0.90-0.95.
**Origin.** Experimenter, P2-E1 contract, J rule and Predictions (`docs/plant2/P2-E1-btsp.md:64-71, 140-143`), 2026-10-10.
**Status.** `refuted`
**Confidence.** Low: the rule's own synapse-count arithmetic was wrong, and the prediction that C1 is at risk was right only because of that error.
**Expected outcome if true.** Measured cue synapses per written cell are about 27.8, the drive is about 1.4x threshold distance, and C1 passes.
**Evidence for.**
- Median recall 0.920-0.941 lies inside the predicted 0.90-0.95, and C1 is the criterion that failed (gated; `docs/plant2/P2-E1-btsp.md:140-143, 205`).
**Evidence against.**
- Measured 24.69 cue synapses per written cell (sd 3.55, flat in k), a mean drive of about 24.9 mV (1.24x). The correct rule gives J about 1.26 mV. 19 % of written cells have fewer than 22 cue synapses, against about 3 % implied (descriptive; `docs/plant2/P2-E1-btsp.md:138-143, 272-282`; `review/plant2/P2-E1/findings-code.md:11-15`).
- Addendum item 1: at J = 1.25, near the correctly computed value, the run fails on specificity instead (C1 0.99, C2 0.445, C3 0.57) (exploratory, seed 1; `docs/plant2/P2-E1-btsp.md:276-282`).
- The per-cell arithmetic ignores item-level overdispersion (H-007) (post hoc; `review/plant2/P2-E1/findings-code.md:41-45`).
**Tested by.** P2-E1
**Experiment needed.** Settled; see the P2-E1 addendum (`docs/plant2/P2-E1-btsp.md:272-290`). From P2-E2 onward J is calibrated on a held-out seed.
**Notes.** J was fixed explicitly so that the P2-E1 verdict would not depend on it.

**H-003** Stored load, not the cue, sets each cell's excitability
**Statement.** Recall depends on load because other memories' strong synapses raise each cell's depolarisation through two terms of about equal size. Term (1) is the steady background spikes arriving on other memories' strong synapses. Term (2) is other memories' strong synapses on the cue's own input lines. Without a mechanism there is no load-independent operating point ("It is the absence of an operating point"). Accommodation removes only term (1), and term (2) is predicted to set the capacity edge.
**Origin.** Experimenter's post hoc diagnosis in the P2-E1 Result (`docs/plant2/P2-E1-btsp.md:213-238`), 2026-10-10. The P2-E1 direction reviewer corrected it to the two-term form (`review/plant2/P2-E1/findings-direction.md:11-15`), which was written into the P2-E2 contract (`docs/plant2/P2-E2-accommodation.md:22-26`), 2026-10-10.
**Status.** `mixed`
**Confidence.** Medium: completion became load-independent once term (1) was removed, but no ablation isolates term (2).
**Expected outcome if true.** Removing term (1) alone makes completion load-independent and moves the limit to specificity, with the specificity edge set by term (2).
**Evidence for.**
- Reviewer sweeps find no fixed J that passes C1-C4 at M = 1,000 (J = 1.16: C1 0.915, C2 0.84; J = 1.20: C1 0.945, C2 0.69), or at both M = 250 and 1,000 (exploratory; `docs/plant2/P2-E1-btsp.md:291-299`). A reviewer's vectorised re-implementation reproduces the capacity curve's C1 as 0.605/0.675/0.83/0.99 against the measured 0.61/0.635/0.84/0.975 (exploratory; `review/plant2/P2-E1/findings-direction.md:7`).
- Under accommodation, completion holds across load and the limit moves to specificity, with the edge between 0.25 and 0.375 items per cell (reported-only; `docs/plant2/P2-E2-accommodation.md:299-301`). An exact-store surrogate gives C2 0.77 at M = 1,500 against the 0.73-0.78 first reported; the records give 0.715-0.775 (exploratory; `review/plant2/P2-E2/findings-direction.md:38`; `docs/plant2/P2-E2-accommodation.md:422`).
**Evidence against.**
- P2-E1 addendum item 3: the diagnosis "rests on reviewer sweeps, not on the run", and the capacity curve is n = 1 (`docs/plant2/P2-E1-btsp.md:291-299`).
- "Fire but too late" is incomplete: k explains R² 0.017 of recall and cue-synapse count R² 0.16 (post hoc; `review/plant2/P2-E1/findings-methodology.md:29-33`).
- No ablation isolates term (2). P2-E2's C3 at M = 1,500 (up to 0.865) and 2,000 (0.43-0.46) came out above prediction, and direction F5 calls the scaling "mostly combinatorial" (reported-only; `docs/plant2/P2-E2-accommodation.md:313-314, 422-423`; `review/plant2/P2-E2/findings-direction.md` F5).
**Tested by.** P2-E1 (post hoc), P2-E2 (indirectly)
**Experiment needed.** An ablation that removes the cue-line term (2) while background is held constant, at M = 1,000-2,000. No contract names one.
**Notes.** This diagnosis motivated H-004.

**H-004** Slow threshold accommodation gives a load-independent operating point
**Statement.** "Each memory cell's spike threshold slowly tracks its own mean membrane potential, removing the steady load-dependent background offset cell by cell; with one J calibrated on a held-out seed, half-cue completion and specificity hold at 250, 500 and 1,000 stored items, where no fixed threshold at that J does."
**Origin.** Two of the three P2-E1 reviewers proposed it independently (`review/plant2/P2-E1/findings-direction.md:73-77`; `review/plant2/P2-E1/findings-methodology.md:67-72`), 2026-10-10. It was contracted as P2-E2's primary hypothesis (`docs/plant2/P2-E2-accommodation.md:28-33`), 2026-10-10.
**Status.** `supported`
**Confidence.** High for the settled protocol: it passed on 5 of 5 fresh gated seeds at every load while the fixed-threshold arm failed at M = 1,000. Online it fails (H-019).
**Expected outcome if true.** C1-C4 pass at M = 250, 500 and 1,000 and C5 holds on every gated seed, and the fixed-threshold arm at J* fails at M = 1,000.
**Evidence for.**
- J* = 1.525 mV. Gated seeds 6-10 pass C1-C4 at M = 250, 500 and 1,000, and C5. Verdict PASS, valid, not void (gated; `docs/plant2/P2-E2-accommodation.md:223-225`).
- At M = 1,000: C1 0.945-0.955, C2 0.965-1.000, C3 0.990-1.000, against the item-level prediction from calibration seed 0 of C1 0.935, C2 0.97, C3 1.00 (gated; `docs/plant2/P2-E2-accommodation.md:205-218, 303-309`).
- Fixed-threshold arm at J*: at M = 1,000 C1 1.000, C2 0.000-0.015 and C3 0.000, as predicted (C2 ≤ 0.10). The matched-density random store gives C1 0.000 and median recall 0.0, as predicted (≤ 0.10) (gated void controls; `docs/plant2/P2-E2-accommodation.md:152-154, 246-250, 372-377`).
- Recall at 25 ms is 0.57-0.61 against a predicted "about 0.5" and P2-E1's 0.42-0.48; the range excludes paired seed 1 (0.55) (reported-only; `docs/plant2/P2-E2-accommodation.md:155, 280, 424`).
**Evidence against.**
- The addendum narrows the contrast. The fixed arm at J* passes M = 250 and 500 on every gated seed (C1 ≥ 0.995, C2 ≥ 0.905, C3 ≥ 0.92). The claim that "no fixed J passes 250 and 1,000 together" rests on reviewer sweeps (reported-only and exploratory; `docs/plant2/P2-E2-accommodation.md:367-391`).
- The predicted J* of about 1.6 (window 1.50-1.70) was wrong: the window was 1.45-1.60 (exploratory, calibration seed 0; `docs/plant2/P2-E2-accommodation.md:145-146, 202, 213-218`).
- Load independence holds only after a rest: C1 is 0.875 with none, 0.915 after 5 s and 0.94 after 50 s (exploratory, seed 0; `docs/plant2/P2-E2-accommodation.md:380-391`).
**Tested by.** P2-E2; the online scope was tested by P2-E4.
**Experiment needed.** Settled for the settled protocol; see P2-E2. Online use is covered by H-019 and H-026.
**Notes.** The owner ruled "P2-E2 is accepted as a distinct mechanism, and K0.14 is not reopened" (`DECISIONS.md:312-318`); reviewers had called it "squarely in the gated family" (`docs/plant2/P2-E2-accommodation.md:352-366`). The reported 6.0 mV threshold offsets include the test's own cue duty, and background alone predicts about 3.6 mV (reviewer arithmetic and exploratory; `docs/plant2/P2-E2-accommodation.md:392-395`). The convergence statistic is mostly a noise floor at high load: the floor is about 0.065 mV at M = 1,000, so seed 5's 0.207 mV at M = 2,000 is plausibly a fluctuation (post hoc; `docs/plant2/P2-E2-accommodation.md:431-434`). C5 was predicted within 0.03 of phase 1 and observed within 0.035 (seed 9: 0.950 to 0.915) (gated; `docs/plant2/P2-E2-accommodation.md:150, 310`).

**H-005** Accommodation is needed only at M = 1,000
**Statement.** P2-E1's slowness at M = 250 (C1 0.61) came from its J of 1.12, not from load. A fixed threshold at a higher J passes at M ≤ 500, so accommodation is needed only at M = 1,000, and no single fixed J passes at both 250 and 1,000.
**Origin.** P2-E2 direction reviewer F3 and methodology reviewer F2, adopted as addendum item 2 (`docs/plant2/P2-E2-accommodation.md:367-373`), 2026-10-10.
**Status.** `mixed`
**Confidence.** Medium: the first half is recorded on gated seeds, while the "no single fixed J" half rests on exploratory sweeps.
**Expected outcome if true.** The fixed arm passes C1-C3 at M ≤ 500, and a full J sweep finds no value that passes at both 250 and 1,000.
**Evidence for.**
- The recorded fixed arm at J* passes C1-C3 on all gated seeds at M = 250 and 500 (reported-only arm; `docs/plant2/P2-E2-accommodation.md:367-373`).
- On seed 0, M = 250 needs a fixed J ≥ 1.25, and no J in 1.10-1.35 passes at M = 1,000 (exploratory; `review/plant2/P2-E2/findings-methodology.md` F2).
**Evidence against.**
- The "no single fixed J" component was never run as a recorded sweep (`docs/plant2/P2-E2-accommodation.md:367-373`).
**Tested by.** P2-E2 (reported arm and reviewer sweeps)
**Experiment needed.** A predeclared fixed-J sweep on a held-out seed at M = 250 and 1,000. None is contracted, and it is low priority while H-004 holds.
**Notes.** none

**H-006** Widening the recall window trades completion for specificity
**Statement.** Widening the index recall window beyond 50 ms trades C1 for C2 rather than rescuing a fixed-J configuration.
**Origin.** P2-E1 methodology reviewer (`review/plant2/P2-E1/findings-methodology.md:32`), recorded as P2-E1 addendum item 3 (`docs/plant2/P2-E1-btsp.md:299`), 2026-10-10.
**Status.** `mixed`
**Confidence.** Medium: one reviewer's exploratory run supports it, and it was never checked under accommodation.
**Expected outcome if true.** At fixed J, C1 rises and C2 falls monotonically as the window widens.
**Evidence for.**
- At J = 1.12: 75 ms gives C1 0.99, C2 0.72; 100 ms gives C1 1.0, C2 0.50 (exploratory; `review/plant2/P2-E1/findings-methodology.md:32`).
**Evidence against.**
- none recorded. P2-E4 measured C1 at 75 ms (about 0.955-0.97) but not spurious responses or ignition at 75 ms (post hoc; `docs/plant2/P2-E4-online-memory.md:753-761`), so the trade-off was not checked under accommodation.
**Tested by.** Reviewer exploration only
**Experiment needed.** Score C2/C3 at 75 ms alongside C1 in a future predeclared contract, as a reported measure.
**Notes.** The owner ruled out any retrospective relaxation of the 50 ms and 75 ms latency bars (`DECISIONS.md:789-790`).

**H-007** Item recall is overdispersed because an assembly shares one cue spike train
**Statement.** All cells of an assembly share one cue spike train and mask, so item recall is overdispersed and C1 sits 5-6 points below what independent per-cell recall implies. An item-level surrogate (shared cue spikes, independent synapses) reproduces engine C1 within 0.05.
**Origin.** P2-E1 code and methodology reviewers, adopted as addendum item 2 (`docs/plant2/P2-E1-btsp.md:287-290`; `review/plant2/P2-E1/findings-code.md:41-45`), 2026-10-10.
**Status.** `mixed`
**Confidence.** High: the measured spread and P2-E2's accurate item-level C1 prediction agree, though the mechanism itself was checked only in a reviewer surrogate.
**Expected outcome if true.** The sd of item recall is well above the independent-cell value, and item-level simulation predicts C1 accurately.
**Evidence for.**
- Item recall sd is 0.105-0.127 against about 0.07 expected. C1 would be 0.87-0.92 under independence against 0.81-0.86 observed. The surrogate lands within 0.05 at J = 1.12-1.34 for M = 250 and 1,000 (post hoc and exploratory; `review/plant2/P2-E1/findings-code.md:41-45`).
- P2-E2 predicted C1 at M = 1,000 from an item-level simulation (0.935), and the gated seeds gave 0.945-0.955 (gated; `docs/plant2/P2-E2-accommodation.md:205-218, 303-309`).
**Evidence against.**
- The surrogate ignores toggle erasure and uses a fitted 0.92 density factor (numbers carry about ±0.05). It was run by a reviewer and not recorded (`review/plant2/P2-E1/findings-code.md:65`).
**Tested by.** P2-E1 review (surrogate); P2-E2 (indirectly, through the item-level prediction)
**Experiment needed.** None for the ledger. Item-level prediction has been standard in contracts since P2-E2.
**Notes.** none

**H-008** Alternative operating-point mechanisms
**Statement.** Several alternatives fail. Global feedback inhibition or k-winners-take-all (k-WTA) cannot satisfy C3. Recurrent co-plateau links run away. Global feedforward inhibition (FFI) with a fixed gain is not load-independent. Synaptic-count normalisation erases writes. Centred per-cell FFI (inhibition J·S_i/m per input spike) works but needs a gain matched to S.
**Origin.** P2-E1 direction reviewer findings F5, F6, F9 and its list of rejected alternatives (`review/plant2/P2-E1/findings-direction.md:35-45, 59-63, 78`), 2026-10-10.
**Status.** `mixed`
**Confidence.** Medium: these are exploratory simulations on two seeds, never recorded.
**Expected outcome if true.** k-WTA ignites unlearned cues, recurrence runs away, and centred FFI passes C1-C3 at M = 1,000.
**Evidence for.**
- k-WTA at J_I = 0.3 mV: C3 0.04, median ignition 20. Recurrent links at J_rec 1.5-2 mV leave 2,889-3,969 cells active. Centred FFI at J = 2.0, M = 1,000: C1 0.995-1.0, C2 0.97-0.985, C3 0.99-1.0 (exploratory, seeds 1-2; `review/plant2/P2-E1/findings-direction.md:35-45, 59-63`).
**Evidence against.**
- None of this was recorded as results (`review/ledger.jsonl` rows 24, 25, 28).
- J_rec 1.0 completed assemblies at M = 250 without runaway, so runaway depends on J (exploratory; `review/plant2/P2-E1/findings-direction.md:44`).
**Tested by.** P2-E1 review only
**Experiment needed.** None for k-WTA, normalisation or inhibitory STDP, which were rejected. Centred FFI is deferred as a comparator. Recurrence needs its own contract with a stabiliser and a bar on spontaneous ignition (H-063).
**Notes.** For P2-E2 the owner rejected feedback k-WTA, recurrent links, synaptic-count normalisation and Vogels inhibitory STDP (`DECISIONS.md:269-273`). B-005 revisits learned inhibition with that ruling in view.

**H-009** C5 cannot fail for a real reason
**Statement.** As designed, C5 (C1-C3 hold again after 60 s of background-only activity) cannot fail for a real reason. Weights are frozen during the 60 s, and the dynamic state is either reset (`quiet()` in P2-E1) or re-equilibrates (v̄ in P2-E2). C5 is therefore C1 re-measured with a new noise draw and says nothing about persistence.
**Origin.** P2-E1 code F7 and methodology F2, addendum item 4 (`docs/plant2/P2-E1-btsp.md:300-305`); P2-E2 methodology F3, addendum item 5 (`docs/plant2/P2-E2-accommodation.md:396-399`), 2026-10-10.
**Status.** `mixed`
**Confidence.** High: it follows from the code, and C5 - C1 stays within about ±2 SE on every seed.
**Expected outcome if true.** C5 - C1 cannot be told apart from sampling noise.
**Evidence for.**
- P2-E1: the set of strong synapses was bit-identical after the 60 s on every seed, and the C5 FAIL simply repeats the C1 failure (gated; `docs/plant2/P2-E1-btsp.md:193, 300-305`).
- P2-E2: C5 - C1 lies between -0.035 and +0.03, about ±2 SE (gated; `docs/plant2/P2-E2-accommodation.md:396-399`). Seed-0 signed drift is about -0.04 mV per 10 s after 40 s of background (exploratory; `review/plant2/P2-E2/findings-methodology.md:26`).
**Evidence against.** none recorded
**Tested by.** P2-E1, P2-E2 (by analysis of the criterion)
**Experiment needed.** A persistence test with plasticity running or dynamic state carried over. P2-E4's O3 is that test online (H-019).
**Notes.** P2-E1's contract already called C5 "a property by construction" and predicted "C5 passes by construction" (`docs/plant2/P2-E1-btsp.md:118-121, 149`). That prediction is refuted in the source ledger: C5 failed on every seed (gated; `docs/plant2/P2-E1-btsp.md:177-178`). The failure only repeats the C1 failure, so it is consistent with this entry.

**H-010** Recall under degraded cues
**Statement.** For out-of-distribution probes, lures are recalled as the stored item, 30 % cues give C1 of about 0.2-0.5, and noisy half cues score below clean half cues.
**Origin.** P2-E4 contract, reported-arms table (`docs/plant2/P2-E4-online-memory.md:467`), 2026-10-10.
**Status.** `mixed`
**Confidence.** Medium: two of the three predicted parts held on every seed, and 30 % cues failed completely.
**Expected outcome if true.** Lures recalled as the stored item; C1 0.2-0.5 for 30 % cues; noisy half cues below clean half cues.
**Evidence for.**
- Lures are recalled as the stored item at 0.90-0.95. Noisy half cues (10 of 50 lines swapped) give C1 0.075-0.175 (reported-only; `docs/plant2/P2-E4-online-memory.md:728-730, 748`).
**Evidence against.**
- 30 % cues give C1 0.00 on all seeds, against a predicted 0.2-0.5 (reported-only; `docs/plant2/P2-E4-online-memory.md:728-730, 748`).
**Tested by.** P2-E4 (reported arm)
**Experiment needed.** A predeclared curve of recall against cue fraction (30-50 %), with and without a completion basin (H-063).
**Notes.** The constructive reviewer reads this as a missing completion basin (`review/plant2/P2-E4/results-northstar_constructive.md` NS4). A lure drives about 5 of the stored item's assembly cells to burst (exploratory; `docs/plant2/EVAL-after-P2-E4.md:110-160`).

## 2. Content completion and the feedback store

**H-011** A one-shot feedback path regenerates the missing half of an input
**Statement.** "A memory-to-reconstruction feedback path, written one-shot from the memory cells' own spikes while the experience is present, lets a half cue regenerate the missing half of the item's input features in a reconstruction layer, at 250, 500 and 1,000 stored items, with P2-E2's forward store unchanged."
**Origin.** Experimenter, P2-E3 contract, predeclared (`docs/plant2/P2-E3-content-completion.md:24-29`), 2026-10-10.
**Status.** `supported`
**Confidence.** High for independent random items under P2-E3's back-to-back settled protocol. The record scopes the claim to exactly that.
**Expected outcome if true.** The D1/D2 joint criterion, D3, D4 and D5 pass on every gated seed at every load, and the shuffled-feedback arm fails.
**Evidence for.**
- PASS on all five fresh gated seeds at every load, valid and not void: joint 0.955-1.000, D3 0.99-1.0, D4 0.940-1.000, D5 holds (gated; `docs/plant2/P2-E3-content-completion.md:331-348`).
- The shuffled-feedback arm gives joint 0.000 and D1 0.000 on every gated seed (gated void check; `docs/plant2/P2-E3-content-completion.md:361`).
- Regeneration latency is 23-28 ms, following memory's own first spikes (about 22 ms) within 1-6 ms (reported-only; `docs/plant2/P2-E3-content-completion.md:383-387`).
**Evidence against.**
- The shuffled control fails by construction, because each responder reaches about 13 % of lines, below g (`docs/plant2/P2-E3-content-completion.md:148-152, 563-567`).
- The 30-40 ms latency prediction was wrong. The revised 22-26 ms was slightly exceeded at M = 1,000 (25-28 ms) (reported-only; `docs/plant2/P2-E3-content-completion.md:228, 322-324, 383, 414`).
- Outside its scope it fails. Structured items give joint 0.147-0.167 at M = 500 (exploratory, seeds 97/99; `:483-503`). On an online timeline the responder store gives settled joint 0.81/0.89 (exploratory, seeds 42-43; `:612-642`). It collapses at M = 1,500 and 2,000 (reported-only; `:396-404`).
**Tested by.** P2-E3; its scope was tested by P2-E4 and P2-E5.
**Experiment needed.** Settled for independent items under the settled protocol; see P2-E3. Structured and online scopes are H-034 and H-031.
**Notes.** The reviews scope the claim to independent random items, with the verbatim input copied against a random assigned index and frozen copies read after a 50 s settle (`docs/plant2/P2-E3-content-completion.md:431-440`). According to `docs/plant2/STAGES.md:83`, it meets Stage 1's content clause and unlocks no later gate.

**H-012** A fixed-threshold readout has no window at M = 1,000; activity-proportional inhibition makes regeneration specific
**Statement.** A feedback readout with a fixed threshold has no working window at M = 1,000, and fixed activity-proportional inhibition is what makes the regeneration specific.
**Origin.** P2-E2 direction reviewer F2 (`review/plant2/P2-E2/findings-direction.md` F2; exploratory seeds 42-43), 2026-10-10. It became P2-E3's secondary, non-gated hypothesis with an owner-required matched comparison (`docs/plant2/P2-E3-content-completion.md:19-22, 31-32`), 2026-10-10.
**Status.** `mixed`
**Confidence.** Medium: true at M = 1,000 on every gated seed, false at M ≤ 500, and reversed at M = 1,500.
**Expected outcome if true.** The matched no-inhibition arm fails at every load, and inhibition helps at every load.
**Evidence for.**
- Without inhibition the joint best is 0.87, against 0.96-0.99 with inhibition at 0.3 J_fb at M = 1,000 (exploratory; `review/plant2/P2-E2/findings-direction.md` F2).
- g = 0 calibration passes 35, 19 and 0 J values at M = 250, 500 and 1,000. The matched g = 0 arm fails M = 1,000 on 5/5 gated seeds (joint 0.770-0.860 against main 0.955-0.985). g = 0 at J_fb* floods (joint 0.065-0.155) (reported-only; `docs/plant2/P2-E3-content-completion.md:297-304, 364-369, 411`).
**Evidence against.**
- The matched g = 0 arm passes at M ≤ 500 (0.92-0.965) (reported-only; `docs/plant2/P2-E3-content-completion.md:367-369, 521`).
- At M = 1,500, g = 0 beats the main arm on every seed (joint 0.245-0.345 against 0.185-0.290; D3 0.88-0.925 against 0.75-0.795) (reported-only; `docs/plant2/P2-E3-content-completion.md:514-528`).
- The reading was fixed at calibration (fallback J), so "unnecessary" could not have been returned (`review/plant2/P2-E3/findings-methodology.md` F4). Inhibition sets an operating band around 0.25 items per cell and is not a capacity mechanism (`review/plant2/P2-E3/findings-northstar_skeptic.md` NS6).
**Tested by.** P2-E3 (reported arm)
**Experiment needed.** Settled for the P2-E3 configuration; see P2-E3 addendum item 5 (`docs/plant2/P2-E3-content-completion.md:514-528`). Inhibition anywhere else needs its own matched comparison (H-062).
**Notes.** The owner allows fixed inhibition only as a declared extra element, and the P2-E3 coefficient is never carried over automatically (`DECISIONS.md:303-306, 326-331, 428-429`).

**H-013** P2-E3 is a spiking Willshaw-style hetero-associative memory
**Statement.** P2-E3 is a spiking Willshaw-style hetero-associative memory. The regenerated content is the input copied verbatim, stored against a random content-independent memory index, and the fixed inhibition implements the count threshold at about 30 % of the active memory cells.
**Origin.** P2-E3 methodology reviewer F1 and north-star skeptic NS2, adopted as Addendum item 2 (`docs/plant2/P2-E3-content-completion.md:474-482`; `review/plant2/P2-E3/findings-northstar_skeptic.md` NS2), 2026-10-10.
**Status.** `mixed`
**Confidence.** High: the record adopts it and counting arithmetic predicted the outcome, but the count-threshold part was never tested directly.
**Expected outcome if true.** The plateau-set store equals or beats the responder store, and label-permuted feedback regenerates π(x).
**Evidence for.**
- The plateau-set arm equals or beats the main arm, and label-permuted feedback regenerates π(x) at 0.968-0.982 (reported-only; `docs/plant2/P2-E3-content-completion.md:362-363, 457-482`).
- Counting arithmetic written before any code (about 2.2 responder inputs on a non-item line against about 19 on a missing item line) predicted the outcome (contract prediction; `docs/plant2/P2-E3-content-completion.md:209-213`).
**Evidence against.**
- The 1 ms inhibition lag makes the Willshaw-threshold description approximate (`docs/plant2/P2-E3-content-completion.md:83-85`), and the count-threshold sentence was not tested directly.
**Tested by.** P2-E3 (reported arms; post hoc reading)
**Experiment needed.** None required. A direct test would vary g and compare the result against the Willshaw count rule.
**Notes.** The description removes any claim that P2-E3 abstracts or learns structure in content.

**H-014** A cue regenerates its own item's lines, not store statistics
**Statement.** Label-permuted feedback regenerates π(x)'s lines and not x's (D1/2 for x about 0; π(x)'s missing lines at about the main D1). This would show that a cue regenerates the content filed under its key, not an artefact of store statistics.
**Origin.** Falsifiability red-team critic, adopted as a reported arm in the P2-E3 contract (`docs/plant2/P2-E3-content-completion.md:182-186`), 2026-10-10.
**Status.** `supported`
**Confidence.** High: the predeclared reported arm came out as predicted on all five fresh gated seeds.
**Expected outcome if true.** Joint and D1 for x are about 0, and π(x)'s lines are regenerated at about the main D1.
**Evidence for.**
- Joint and D1 for x are 0.000, and π(x)'s lines are regenerated at 0.968-0.982 (of about 99 lines) (reported-only; `docs/plant2/P2-E3-content-completion.md:362, 554-559`).
**Evidence against.**
- The result follows from the write rule (the output is whatever was filed under the key), so it shows no abstraction. The store preserves degrees only approximately (36 % of cells and 3.6 % of lines keep exactly the same degree) (exploratory, a reviewer's small check; `docs/plant2/P2-E3-content-completion.md:481-482, 554-559`).
**Tested by.** P2-E3
**Experiment needed.** Settled; see P2-E3.
**Notes.** none

**H-015** The responder write loses nothing against the plateau set
**Statement.** Writing feedback from the memory layer's own continuation responders R(x), rather than the plateau set A(x), "loses nothing", and "The extra responders write extra feedback but cost no measurable specificity."
**Origin.** Experimenter, P2-E3 Result (`docs/plant2/P2-E3-content-completion.md:363, 393-395`), 2026-10-10.
**Status.** `withdrawn`
**Confidence.** Low: the addendum found that the extra responders lower D2 on 5 of 5 seeds.
**Expected outcome if true.** The R(x) write matches or beats the A(x) write on both D1 and D2.
**Evidence for.**
- Jaccard(R, A) is 0.87-0.88, with |R| 23.3-24.0 against |A| 19.8-20.2, and the plateau-set arm is about equal to the main arm (reported-only; `docs/plant2/P2-E3-content-completion.md:393-395`).
**Evidence against.**
- Addendum item 1: R(x) adds nothing measurable over A(x). The plateau-set arm is equal or better on every seed, with D2 1.000 on 5/5 against main 0.970-0.995. The extra responders add a few intrusions (reported-only; `docs/plant2/P2-E3-content-completion.md:457-471`).
- The contract predicted a lower D1 for the plateau-set arm, which was wrong: D1 0.980-0.990 against 0.980-0.995 (reported-only; `docs/plant2/P2-E3-content-completion.md:359-363, 416`).
**Tested by.** P2-E3
**Experiment needed.** Settled; see P2-E3 Addendum item 1.
**Notes.** The Result and Addendum item 1 disagree on how to score the plateau-set prediction (`docs/plant2/P2-E3-content-completion.md:416, 457-473`). The cost of the responder write grows online (H-031) and on correlated items (H-036).

**H-016** Unlearned cues regenerate nothing
**Statement.** "Unlearned cues regenerate nothing."
**Origin.** P2-E3 Result, "What this shows" (`docs/plant2/P2-E3-content-completion.md:424`), 2026-10-10.
**Status.** `withdrawn`
**Confidence.** Low as written: the per-seed maximum reached 22 lines, and "almost nothing" replaced the sentence.
**Expected outcome if true.** Every novel cue regenerates 0 lines.
**Evidence for.**
- The novel-cue median is 0 lines and D3 is 0.99-1.0 (gated; `docs/plant2/P2-E3-content-completion.md:381, 413, 424`).
**Evidence against.**
- The per-seed maxima at M = 1,000 are 0, 1, 1, 2 and 22 lines, and D3 is 0.990 on seed 14 (gated; `docs/plant2/P2-E3-content-completion.md:548-549`; `review/plant2/P2-E3/findings-methodology.md` F3).
**Tested by.** P2-E3
**Experiment needed.** Settled; see the P2-E3 errata (`docs/plant2/P2-E3-content-completion.md:548-549`).
**Notes.** none

**H-017** The readout expresses at most about three co-active memories
**Statement.** With the g = 0.3 fractional vote, the reconstruction readout can express at most about three co-active memories.
**Origin.** P2-E3 constructive reviewer F9 (`review/plant2/P2-E3/findings-northstar_constructive.md` F9), 2026-10-10.
**Status.** `proposed`
**Confidence.** Medium: shown on a synthetic raster only.
**Expected outcome if true.** Regeneration stays near 1.0 for one to three co-active assemblies and drops at four.
**Evidence for.**
- Lines are regenerated at 1.00 with 1-2 co-active assemblies, 0.98 with 3 and 0.71-0.75 with 4. g = 0 floods with 560-3,533 intrusions (exploratory, synthetic raster; `review/plant2/P2-E3/findings-northstar_constructive.md` F9).
**Evidence against.** none recorded
**Tested by.** Untested in the network; synthetic raster only
**Experiment needed.** Measure regeneration against the number of co-active assemblies on persisted P2-E5 rasters (a reported replay).
**Notes.** Relevant to blending and the Stage 3 prototype question (H-070). Status corrected from `mixed` to `proposed` on 2026-10-22: a synthetic raster is not a run of the network, and the source ledger records it as untested.

**H-018** Content failures are reconstruction-layer silence in small plateau sets
**Statement.** Content failures are near-total silence in the reconstruction layer, concentrated in items with small plateau sets.
**Origin.** P2-E4 code reviewer F4 (`review/plant2/P2-E4/results-code.md` F4; `docs/plant2/P2-E4-online-memory.md:763-766`), 2026-10-11.
**Status.** `mixed`
**Confidence.** Medium: a strong post hoc association on gated-seed data, never predeclared.
**Expected outcome if true.** Content failure rate falls steeply with plateau-set size.
**Evidence for.**
- 79 of 2,762 cues regenerated 0 lines. Silence affects 64 % of cues for assemblies of 0-10 cells and under 0.5 % for 19 cells or more (post hoc; `review/plant2/P2-E4/results-code.md` F4).
**Evidence against.**
- It is post hoc and needs its own predeclared measure (`docs/plant2/P2-E4-online-memory.md:763-766`).
**Tested by.** P2-E4 (post hoc)
**Experiment needed.** Predeclare content failure rate by plateau-set size in the next content contract.
**Notes.** Plateau-set size comes from the experimenter's random draw (H-053).

## 3. Online memory and the encoding/retrieval trade-off

**H-019** Online index recall holds while learning continues
**Statement.** "The P2-E3 system keeps memory ... recall for recent and old items while it learns one item every 500 ms with no settle and no quiet(). Every parameter is frozen." This includes meeting Stage 1's clause "holds ... after 60 s of ongoing activity" online.
**Origin.** Owner's online-memory requirement, P2-E4 contract hypothesis (`docs/plant2/P2-E4-online-memory.md:57-59, 312-313`). Contract frozen 2026-10-10; run 2026-10-11.
**Status.** `refuted`
**Confidence.** Low: ONLINE INDEX FAIL at both loads on 5 of 5 fresh gated seeds.
**Expected outcome if true.** O1 C1, C2, C3 and O3 memory pass at M = 500 and 1,000 on every seed.
**Evidence for.**
- C2 and C3 are 1.0 on every seed and load. Online C1 of 0.87-0.93 at M = 500 passes on seeds 18-20 individually (gated; `docs/plant2/P2-E4-online-memory.md:639-672`).
- C1 at 75 ms is about 0.955-0.97 (post hoc; `docs/plant2/P2-E4-online-memory.md:753-761`).
**Evidence against.**
- O1 C1 fails at both loads (0.87-0.93 at M = 500; 0.68-0.74 at 1,000). O3 memory fails at both loads (0.83-0.94; 0.61-0.75), and recent items fail too (0.72-0.82). Verdict ONLINE INDEX FAIL (gated; `docs/plant2/P2-E4-online-memory.md:620-621, 639-672, 788`).
- The red team predicted P(PASS) < 0.05, and the real-driver prediction gave ONLINE INDEX FAIL with probability 1.00 (exploratory, seeds 42-43, and power record 2026-10-11T00:37:57Z; `docs/plant2/P2-E4-online-memory.md:489-504, 588-616`). Results at M = 1,000 fell below even the predicted ranges (C1 0.68-0.685 on 3 seeds; O3 memory 0.61-0.67) (gated; `docs/plant2/P2-E4-online-memory.md:739-749`).
**Tested by.** P2-E4
**Experiment needed.** Settled; see the P2-E4 verdict. The cause is examined in H-026 and H-028.
**Notes.** As predeclared, the claim that accommodation provides a usable online operating point is withdrawn at M = 500 and 1,000, and nothing is retuned (`docs/plant2/P2-E4-online-memory.md:785-792`). Several reported arms were left unscored. M = 250 rolling C1 was 0.75-1.0 (n 6-16) against a predicted 0.92-1.0. Efficiency at the gate was about 0.27 bits per feedback synapse (0.266-0.279) against a predicted 0.2. Recent items scored higher than uniform ones (C1 0.72-0.82 against 0.62-0.72). Probed against never-probed items was not reported (reported-only; `docs/plant2/P2-E4-online-memory.md:454-468`; `bench/results/plant2.jsonl` reported_arms records).

**H-020** Online content recall holds while learning continues
**Statement.** The P2-E3 system keeps content recall (at least 40 of 50 missing lines, fewer than 10 intrusions) for recent and old items while learning continues, and novel cues regenerate fewer than 10 lines.
**Origin.** P2-E4 contract hypothesis, the content part of O2 and O3 (`docs/plant2/P2-E4-online-memory.md:57-59`), 2026-10-10.
**Status.** `supported`
**Confidence.** Medium: it passes on 5 of 5 gated seeds at both loads, but at M = 1,000 the pass depends on the online state and one seed sits exactly on the bar.
**Expected outcome if true.** O2 and O3 content pass at both loads on every seed, and no ONLINE CONTENT FAIL is issued.
**Evidence for.**
- O2 joint is 0.93-0.995, D3 1.0 and O3 content 0.90-1.0 on all five seeds at both loads, with no ONLINE CONTENT FAIL (gated; `docs/plant2/P2-E4-online-memory.md:639-650, 697-703`).
**Evidence against.**
- At M = 1,000 the online-written store reads 0.82-0.905 on twin A, below P2-E3's 0.90 bar on 4 of 5 seeds, and content is 0.835-0.915 after a settle (reported-only; `docs/plant2/P2-E4-online-memory.md:697-703`; `review/plant2/P2-E4/results-methodology.md` F4).
- Seed 20's O3 content is exactly 90/100 (gated; `docs/plant2/P2-E4-online-memory.md:697-703`). The content half has no positive control (`docs/plant2/P2-E4-online-memory.md:337-349`).
**Tested by.** P2-E4
**Experiment needed.** Settled for the P2-E4 protocol; see P2-E4. Contamination of the online-written store is H-031.
**Notes.** The contract stated a single composite hypothesis. Its index half is H-019, and the composite verdict is FAIL. Content passes online partly because the online state slows index access and keeps writers few (H-029).

**H-021** Recall is caused by the cue
**Statement.** "The recall is caused by the cue." This is the owner's blank-cue control.
**Origin.** P2-E4 contract hypothesis, owner's blank-cue control (`docs/plant2/P2-E4-online-memory.md:59-60, 314-317`), 2026-10-10.
**Status.** `unresolved`
**Confidence.** High: no leak was seen, but this architecture has no gated control that can fail, so the check could not decide.
**Expected outcome if true.** Blank cues evoke nothing, and a control that can fail does fail.
**Evidence for.**
- The blank-slot leak check (validity 9) passed on all five seeds with blank leak 0 (gated validity check; `review/plant2/P2-E4/results-methodology.md` F8).
**Evidence against.**
- No gated control can fail in this architecture (contract and ledger M4, FID-7), so the check is a validity check and not evidence. The content half has no positive control (`docs/plant2/P2-E4-online-memory.md:337-349`).
**Tested by.** P2-E4
**Experiment needed.** A control that can fail, for example a cue-identity swap scored on index and content at matched drive.
**Notes.** none

**H-022** Accommodation at τ = 10 s does not habituate to a repeated cue
**Statement.** With τ_acc = 10 s, a repeated cue keeps recall no worse than a matched control. P2-E2 reported that at 1-3 s a repeated cue habituated (recall -0.03 to -0.10 over ten repeats) while at 10 s "it stayed flat". P2-E4's O4 required that, with learning paused and input duty held, a cue repeated 100 times over 50 s habituates at most 10 % of at least 25 eligible items.
**Origin.** Experimenter, from P2-E1 reviewer exploratory runs (`review/plant2/P2-E1/findings-direction.md` F7), written into the P2-E2 contract (`docs/plant2/P2-E2-accommodation.md:47-50`), 2026-10-10. Tested as P2-E4's secondary hypothesis under the owner's ruling 2 (`docs/plant2/P2-E4-online-memory.md:61-63`), 2026-10-10.
**Status.** `refuted`
**Confidence.** Low: HABITUATION FAIL, with 50-64 % of eligible items habituated on every estimable seed.
**Expected outcome if true.** O4 passes: at most 10 % of eligible items habituate.
**Evidence for.**
- P2-E2's repeated-cue arm (10 repeats, 20 items) went from recall 0.89-0.95 to 0.90-0.94, minimum 0.87: "mild habituation ... smaller than at 1-3 s" (reported-only; `docs/plant2/P2-E2-accommodation.md:287-290`).
**Evidence against.**
- P2-E4 O4: 50-64 % of eligible items habituated on seeds 17-19 at M = 500 (McNemar 23/0, 25/0, 18/0). Seeds 16 and 20 and all M = 1,000 seeds were not estimable (gated; `docs/plant2/P2-E4-online-memory.md:655-656, 690-696`).
- Every one of the 50 items recalls less in the repeated copy's last 10 repetitions on every seed and load, with a mean drop of 0.107-0.134 (post hoc; `docs/plant2/P2-E4-online-memory.md:804-814`; `review/plant2/P2-E4/results-northstar_constructive.md` NS6).
- A P2-E2 reviewer run (seed 6, 10 items, 100 repeats = 30 s) saw items with recall ≥ 0.8 fall from 0.99 to 0.79 and then 0.67, with the cued assembly's v̄ up 5.2 mV. The P2-E2 arm covered only 0.3 τ_acc (exploratory; `docs/plant2/P2-E2-accommodation.md:400-411`; `review/plant2/P2-E2/findings-code.md` F1).
- In diagnosis D4 the assembly offset rises 2.0-2.1 mV with repetition, net of the control copy (reported-only; `docs/plant2/P2-E4-diagnosis-plan.md:382-415, 432`; `docs/plant2/P2-E4-online-memory.md:808`).
**Tested by.** P2-E2 (reported arm), P2-E4 (gated O4)
**Experiment needed.** Settled; see the P2-E4 verdict.
**Notes.** Methodology F6 notes that O4 had little power at the realised control rates (a no-effect pass chance of 0.45-0.79, with 7-9 % habituating by chance), which "does not weaken a failure of this size" (post hoc; `review/plant2/P2-E4/results-methodology.md` F6). The constructive reviewer (NS6) finds habituation universal and graded, and asks that the continuous drop be reported beside O4. D4's item-level claim that habituated items accommodate more is withdrawn: both groups rise within 0.2 mV of each other (`docs/plant2/P2-E4-diagnosis-plan.md:299-310`). O4/O5 must be rescored (H-025). The reading of ruling 2 was flagged as one the owner may overrule.

**H-023** Recall recovers after repetition stops
**Statement.** "Recall recovers 10.5-14.5 s after the last repetition." O5 recovery requires that at least 90 % of items pass on the repeated copy, among at least 25 items that pass on the control copy.
**Origin.** P2-E4 contract, owner's recovery ruling (`docs/plant2/P2-E4-online-memory.md:62-63`), 2026-10-10.
**Status.** `refuted`
**Confidence.** Low: RECOVERY FAIL at M = 500, not estimable at 1,000, and a post hoc paired check of 57 against 2.
**Expected outcome if true.** O5 recovery passes on every estimable seed and load.
**Evidence for.**
- Recovery among habituated items is 0.75-1.0, and seeds 16, 17 and 19 pass at M = 500 (gated; `docs/plant2/P2-E4-online-memory.md:657-689`).
**Evidence against.**
- O5 recovery fails at M = 500 on seed 18 (p0 0.831, label RECOVERY FAIL) and seed 20 (p0 0.64), and is not estimable at M = 1,000 on any seed (p0 0.010-0.025) (gated; `docs/plant2/P2-E4-online-memory.md:641-650, 657-689`).
- A paired check gives 57 against 2 pooled, and 7-10 against 0-1 per seed at M = 1,000 (post hoc; `review/plant2/P2-E4/results-methodology.md` F2).
**Tested by.** P2-E4
**Experiment needed.** Settled; see the P2-E4 verdict.
**Notes.** The label rests on one seed and load (`docs/plant2/P2-E4-online-memory.md:657-689`). The real-driver predictions gave RECOVERY FAIL 0.36 against RECOVERY NOT ESTIMABLE 0.57 (power record; `docs/plant2/P2-E4-online-memory.md:588-616`). O4/O5 must be rescored on index alone (H-025).

**H-024** Repetition spares collateral items
**Statement.** Repeating an item spares the items whose assemblies overlap it: at least 90 % pass on the repeated copy among those that pass on the control copy (O5 collateral).
**Origin.** P2-E4 contract, O5 collateral clause (`docs/plant2/P2-E4-online-memory.md:227-231`), 2026-10-10.
**Status.** `supported`
**Confidence.** Medium: it passes on every seed and load, but the overlap between collateral assemblies is too small to test spread.
**Expected outcome if true.** O5 collateral passes on every seed and load.
**Evidence for.**
- O5 collateral passes on every seed and load (gated; `docs/plant2/P2-E4-online-memory.md:659`). The paired collateral count is 4 against 1 (post hoc; `docs/plant2/P2-E4-online-memory.md:687`).
**Evidence against.**
- The median maximum overlap is about 2 of 20 cells, so the test says little about spread to overlapping assemblies (exploratory, red-team m4; `docs/plant2/P2-E4-online-memory.md:230`).
**Tested by.** P2-E4
**Experiment needed.** A collateral cohort chosen for high assembly overlap.
**Notes.** none

**H-025** Feedback-only changes cannot alter O4/O5
**Statement.** Changing only the feedback store cannot alter P2-E4's O4/O5 outcomes: they were claimed bit-identical, so the inherited HABITUATION FAIL is guaranteed.
**Origin.** P2-E4 constructive reviewer (`review/plant2/P2-E4/results-northstar_constructive.md:36`) and `docs/plant2/EVAL-after-P2-E4.md:135`, 2026-10-11.
**Status.** `refuted`
**Confidence.** Low: O4/O5 score index and content together, and some presentations pass the index but fail the composite.
**Expected outcome if true.** O4/O5 counts are identical under every feedback swap.
**Evidence for.**
- Pure memory outputs and the underlying memory-recall decrement do not change under feedback swaps (reported-only; `review/plant2/P2-R1/findings-baseline-methodology.md:28-33`).
**Evidence against.**
- O4/O5 eligibility, late counts, recovery and collateral all use "both", meaning index AND content. 1,009 of 50,000 presentations pass the index but fail "both" (103 late, 6 first) (reported-only; `review/plant2/P2-R1/findings-baseline-methodology.md:28-33`).
**Tested by.** P2-R1 (baseline audit)
**Experiment needed.** Settled; see the P2-R1 baseline review. O4/O5 must be rescored.
**Notes.** The P2-R1 erratum is appended at `docs/plant2/EVAL-after-P2-E4.md:229-232`, dated 2026-10-12.

**H-026** Online index failure depends on state or protocol, not erasure
**Statement.** The high-load online index failure is not necessarily a failure to store (the owner's wording). At least 70 % of online index failures pass after a 50 s settle on the same stored synapses, so the failure depends on state or protocol rather than on erasure. The sharper research question is therefore how learning and recall are coordinated, ahead of more capacity.
**Origin.** P2-E2 methodology reviewer F4, on the need for rest after learning (`docs/plant2/P2-E2-accommodation.md:380-391`), 2026-10-10. Owner guidance and sharper research question (`DECISIONS.md:481-497, 605-611`), 2026-10-11. P2-E4 diagnosis D3 (`docs/plant2/P2-E4-diagnosis-plan.md:90-93, 153-160`), 2026-10-11.
**Status.** `supported`
**Confidence.** High for "not erasure" on independent items. Which state variable is responsible is not isolated.
**Expected outcome if true.** Most online index failures pass after a settle, with synapses unchanged.
**Evidence for.**
- 86-100 % of index failures pass after the settle at M = 1,000, and 89-100 % at M = 500 (reported-only predeclared diagnosis on gated seeds; `docs/plant2/P2-E4-diagnosis-plan.md:357-380`).
- Online index is 0.68-0.74 against 0.92-0.975 settled at M = 1,000, and 0.87-0.93 against 0.965-0.98 at M = 500 (reported-only; `docs/plant2/P2-E4-online-memory.md:712-713`).
- In P2-E2, C1 was 0.875 with no rest, 0.915 after 5 s and 0.94 after 50 s, and the v̄ offset was 9.1 mV straight after learning against 3.6 mV at equilibrium (exploratory, seed 0; `docs/plant2/P2-E2-accommodation.md:380-391`; `review/plant2/P2-E2/findings-methodology.md:32`).
- On correlated items, twin B memory is 0.81-0.89 online against 0.95-0.96 settled at M = 500, and 0.54-0.585 against 0.91-0.94 at M = 1,000 (reported-only; `docs/plant2/P2-E5-structured-items.md:966`).
**Evidence against.**
- Unpredicted: at M = 1,000, more cues pass content online and fail after the settle than the reverse (15-28 against 5-9) on all five seeds (reported-only; `docs/plant2/P2-E4-diagnosis-plan.md:430-431`). Settling also loses some earlier successes (seed 42, M = 500: seven cues) (exploratory; `DECISIONS.md:586-588`).
- Twin B changes the whole presentation regime (50 s settle, a separate input stream, P2-E3's rhythm, no learning episodes), so it does not show that the threshold offset alone is the cause (`DECISIONS.md:496-497`).
- Per-seed index gaps at M = 500 (0.085, 0.11, 0.05, 0.055, 0.055) and M = 1,000 (0.26, 0.21, 0.275, 0.225, 0.295) exceed the reported-arm prediction (0.03-0.08 and 0.15-0.25) on several seeds (post hoc, derived from the D3 McNemar counts; `docs/plant2/P2-E4-diagnosis-plan.md:359-370`).
**Tested by.** P2-E4 (diagnosis D3); P2-E5 (twin B, reported)
**Experiment needed.** A separately contracted intervention that changes one state variable (offset, schedule or probe load) at a time on unchanged synapses.
**Notes.** The closeout's wording, "The failure at high load is not a failure to store" (`DECISIONS.md:716`), is stronger than the owner's "not necessarily" (`DECISIONS.md:606`). The claim that the threshold offset couples access and contamination is withdrawn (H-027).

**H-027** The threshold offset couples online access and contamination
**Statement.** "The online state's high offset suppresses the intrusions": access and contamination are "coupled through the threshold offset", and "fixing the operating point alone would be expected to expose the contamination".
**Origin.** Experimenter's write-up of the P2-E4 diagnosis exploration, commit 614246b (`docs/plant2/P2-E4-diagnosis-plan.md:238-239, 266-278`), 2026-10-11.
**Status.** `withdrawn`
**Confidence.** Low: the gated diagnosis does not replicate the exploration's offset pattern.
**Expected outcome if true.** The assembly offset separates failing from passing cues consistently, and lowering the offset alone exposes contamination.
**Evidence for.**
- The exploration showed an offset correlate of +0.2-0.4 mV (exploratory, seeds 42-43; `docs/plant2/P2-E4-diagnosis-plan.md:194, 216-218, 266-278`).
**Evidence against.**
- The claim contradicts the owner's narrowing of D3. On gated seeds, D2's assembly offset difference of -0.15 to +0.57 mV is not consistent (reported-only; `docs/plant2/P2-E4-diagnosis-plan.md:280-297, 335-355`).
- The duty arm changes the schedule as well as the offset (`docs/plant2/P2-E4-diagnosis-plan.md:280-297`).
**Tested by.** P2-E4 (diagnosis)
**Experiment needed.** Settled as withdrawn. Any claim about the offset needs a single-variable intervention (H-026).
**Notes.** The owner's record: "Which state variable is responsible for the trade-off is not isolated. The gated data do not replicate the exploration's offset correlate." (`DECISIONS.md:720-721`).

**H-028** Online index failure is mostly slowed retrieval
**Statement.** ONLINE INDEX FAIL is mostly a failure to respond within 50 ms, not lost access. Cues that fail the index but pass content have assigned-assembly recall of 0.5-0.8 at 50 ms, later first spikes and a higher offset, and a 75 ms window rescues only a minority of them.
**Origin.** P2-E4 diagnosis D1/D2 (`docs/plant2/P2-E4-diagnosis-plan.md:76-88`), 2026-10-11. North-star skeptic NS-1, accepted in the Result (`docs/plant2/P2-E4-online-memory.md:753-761`; `review/plant2/P2-E4/results-northstar_skeptic.md` NS-1).
**Status.** `mixed`
**Confidence.** Medium: first spikes are later and most failures reach the bar by 75 ms, but D2's predeclared parts on R(x), offset and age went against it.
**Expected outcome if true.** Failing cues fire later but fire, a minority are rescued at 75 ms, and offset and item age separate failing from passing cues.
**Evidence for.**
- D1: cues that fail the index but pass content are 22.5-29.5 % of half cues at M = 1,000 on all five seeds; the reverse case is 0.5-2.5 % on four seeds (reported-only; `docs/plant2/P2-E4-diagnosis-plan.md:321-333`).
- D2: A(x) recall is 0.70-0.73, the first spike is 6.0-8.5 ms later, and the A(x) candidate share is 1.0 (reported-only; `docs/plant2/P2-E4-diagnosis-plan.md:335-355`).
- 0.89-0.93 of failing cues reach the bar within 75 ms, C1 at 75 ms is about 0.955-0.97, and joint_50ms is only 0.73-0.855 (post hoc; `docs/plant2/P2-E4-online-memory.md:753-761`).
**Evidence against.**
- D2 predicted that a 75 ms window rescues a minority, but it rescues 0.89-0.93. R(x) recall (0.59-0.68) is below A's, and the offset difference (-0.15 to +0.57 mV) and item age are not consistent (reported-only; `docs/plant2/P2-E4-diagnosis-plan.md:335-355, 423-429`).
- D1: on seed 20, index-without-content is exactly 3.0 % (6 of 200), failing "under 3 %" at the boundary (reported-only; `docs/plant2/P2-E4-diagnosis-plan.md:321-333`).
- Spurious responses and ignition at 75 ms were not measured, and the cue-level cause is not identified (`docs/plant2/P2-E4-online-memory.md:753-761`).
**Tested by.** P2-E4 (diagnosis and post hoc)
**Experiment needed.** Predeclared latency distributions with C2/C3 scored at 75 ms (H-006), and a per-item drive-margin measure (H-068).
**Notes.** No retrospective relaxation of latency bars; the owner ruled on 2026-10-12 that the 50 ms index and 75 ms content requirements stay as they are and that any end-to-end latency proposal is separate (`DECISIONS.md:789-790`). The exploration's D1 was withdrawn as an independent test because its prediction was made from the same numbers (`docs/plant2/P2-E4-diagnosis-plan.md:299-301`).

**H-029** The encoding/retrieval trade-off
**Statement.** "The conditions that improve access to stored memories appear to make those memories less reliable to write." On the main online timeline (higher offset), recall from the assigned assembly is weaker and the reconstruction store relatively clean. In the duty arm (lower offset), recall is stronger and the store much more contaminated. The same pattern appears on correlated items.
**Origin.** Owner's reading (`DECISIONS.md:567-582`), 2026-10-11, which the owner judged the most important finding so far. The correlated-item form comes from fix-check R1 (`docs/plant2/P2-E5-structured-items.md:129-142`), 2026-10-11.
**Status.** `mixed`
**Confidence.** Medium: the pattern holds across every responder-write condition measured, but no single state variable is isolated and one settled twin passes both measures.
**Expected outcome if true.** Across operating states, index access and store cleanliness are inversely related, and no state gives both.
**Evidence for.**
- At M = 1,000, online index is 0.68-0.74 with content 0.93-0.965, against settled index 0.92-0.975 with content 0.835-0.915 (reported-only; `docs/plant2/EVAL-after-P2-E4.md:33-35`; `docs/plant2/P2-E4-online-memory.md:712-713`).
- In the duty arm at M = 1,000, online C1 is 0.945-0.985 while twin A content is 0.175-0.245 (reported-only; `docs/plant2/P2-E4-online-memory.md:714-715`). |R| falls on one curve against continuation offset: 27.6-29.2 at about 8.4 mV, 41.2-44.5 at about 6.9 mV and 120.8-135.8 at about 4.1 mV (reported-only; `review/plant2/P2-E4/results-northstar_skeptic.md:26`; rounded to 28-29, 41-45 and 121-136 in `docs/plant2/EVAL-after-P2-E4.md:83-94`).
- On correlated items, online content is 0.525-0.58 against 0.035-0.055 settled, C1 0.77-0.82 against 0.955-0.965, and the offset 3.70-3.80 against 1.86-1.92 mV (exploratory, seeds 44-45, M = 500; `docs/plant2/P2-E5-structured-items.md:129-142`).
**Evidence against.**
- P2-R1 erratum: "'Never both' overstates the evidence": seed 18's settled twin B has index recall 0.955 and content joint 0.915 (reported-only; `docs/plant2/EVAL-after-P2-E4.md:227-228`).
- The pattern is shown for the responder write, not the architecture, and the duty arm changes the whole schedule (`docs/plant2/EVAL-after-P2-E4.md:223-230`).
- Skeptic NS4: the online C2 near 0.98 is unpaired and consistent with one global excitability shift along a sensitivity-specificity curve (seed 22: offset 8.2 mV online against 3.6 settled, rising from 7.3 to 9.2 mV within the block). "Specific but slow" is withdrawn (H-083) (post hoc; `review/plant2/P2-E5/results-northstar_skeptic.md:32-33`).
**Tested by.** P2-E4 (reported arms), P2-E5 (exploration and reported arms)
**Experiment needed.** A write whose eligibility does not share the read threshold (H-030), with a paired per-cue C1 × C2 analysis online against settled. B-009 is a speculative mode-switch remedy.
**Notes.** The owner advises against a threshold adjustment alone as the fix (H-067).

**H-030** The trade-off belongs to a write gated by the same threshold as reading
**Statement.** The encoding/retrieval trade-off belongs to a write gated by the same threshold that gates reading. Input duty, not retrieval, drives contamination.
**Origin.** P2-E4 north-star skeptic NS-3 (`review/plant2/P2-E4/results-northstar_skeptic.md` NS-3), 2026-10-11.
**Status.** `mixed`
**Confidence.** Medium: the twin that sees only novel input matches the main line, but the decisive test was not run.
**Expected outcome if true.** A write whose eligibility does not depend on the read threshold removes the trade-off.
**Evidence for.**
- The novel-duty twin never retrieves a stored item yet matches the main line's |R| (within 0.21) and twin-A joint (within 0.01). Its twin-A store reads 0.815-0.91 against the main line's 0.82-0.905 (reported-only; `review/plant2/P2-E4/results-northstar_skeptic.md:26`; `docs/plant2/P2-E4-online-memory.md:716, 733-735`).
- The reconstruction layer has no outputs, so the feedback store cannot move the memory operating point (`docs/plant2/P2-E4-online-memory.md:776-777`).
**Evidence against.**
- The decisive test, a write whose eligibility does not share the read threshold, was not run (`docs/plant2/P2-E4-online-memory.md:776-777`).
**Tested by.** P2-E4 (reported arms; post hoc reading)
**Experiment needed.** A live write whose eligibility is independent of the read threshold on P2-E4's online schedule. The burst-gated write (H-050) is one candidate.
**Notes.** none

**H-031** The responder-written store is contaminated on the online schedule
**Statement.** The responder-based write is specific only while back-to-back learning holds the continuation offset near 8.5 mV. On an online schedule R(x) grows and overlaps A(x) less, and the store carries more intrusions than P2-E3's protocol store (P2-E5 Part D required a ratio R ≥ 1.25).
**Origin.** P2-E4 contract red-team finding M1, confirmed by an independent refuter and recorded as P2-E3 Addendum 2 (`docs/plant2/P2-E3-content-completion.md:612-642`), 2026-10-10. P2-E4 reported-arms prediction (`docs/plant2/P2-E4-online-memory.md:455-459`), 2026-10-10. Owner request, tested as P2-E5 Part D (`docs/plant2/P2-E5-structured-items.md:445-480`), 2026-10-11.
**Status.** `mixed`
**Confidence.** High that the online-written store is worse, but the favourable evidence is reported arms and replays, and some predicted bounds were missed.
**Expected outcome if true.** Online-written stores have larger |R|, lower Jaccard with A and lower joint than protocol-written stores on the same raster.
**Evidence for.**
- On an online timeline the offset is 6.85 mV, |R| 45, Jaccard 0.49 and settled joint 0.81/0.89. With a 2 s interval, |R| is 133, Jaccard 0.18 and joint 0.165. The same raster through a P2-E3-protocol store gives 0.98/0.99 (exploratory, seeds 42-43; `docs/plant2/P2-E3-content-completion.md:612-642`).
- In P2-E4 at M = 1,000, |R| is 41-44.5 against 28-29, Jaccard 0.48-0.53 against 0.71-0.75, and the online offset 6.8-7.0 mV. Twin A through three stores reads 0.82-0.905, 0.96-1.0 and 0.985-1.0 (reported-only; `docs/plant2/P2-E4-online-memory.md:709-711, 745-748`).
- P2-E5 Part D: R is 1.66-1.95 at M = 500 and 1.69-1.84 at M = 1,000, read as WORSENS at both loads (reported-only; `docs/plant2/P2-E5-structured-items.md:920-921`).
**Evidence against.**
- The online offset of 6.8-7.0 mV falls just below the predicted 7-7.7 mV. The store-swap readings go past their predicted bounds (0.905 > 0.90; 0.96 < 0.97) (reported-only; `docs/plant2/P2-E4-online-memory.md:455-459, 709-711, 745-748`).
- Part D compares whole regimes (schedule, probes and offset are not separated). Joints are AT FLOOR at M = 1,000 and for seed 25 at M = 500, and the ratio was measured at saturation (median intrusions 1,745-3,043 of 4,000) (reported-only; `docs/plant2/P2-E5-structured-items.md:948-953`).
**Tested by.** P2-E4 (reported arms), P2-E5 Part D, exploration
**Experiment needed.** A single-variable contrast (schedule, offset or probes) on a live run. A live R_3 write (B-011, H-050) would test the remedy.
**Notes.** none

**H-032** The high-load failure decomposes into separable problems
**Statement.** The high-load failure "is not necessarily a failure to store". It comprises distinct problems that are not to be fixed together: (1) learning-time contamination of the content store by the responder write, and (2) operating-point instability of index access. P2-E5 added (3), forward-index cross-talk on correlated items. Together with statistical overlap and item age, these combine additively.
**Origin.** Owner guidance (`DECISIONS.md:481-495, 605-611`), 2026-10-11. The additive form is implicit in P2-E5's Part B loss rankings and was examined by P2-R1 (`docs/plant2/RESULTS-P2-R1.md:44-46`), 2026-10-12.
**Status.** `unresolved`
**Confidence.** Medium that the problems are separable targets for intervention; low that they combine additively.
**Expected outcome if true.** Fixing each problem in isolation recovers its own share of the loss, and the shares add up.
**Evidence for.**
- Twin A reads the same raster through three stores at 0.82-0.905, 0.96-1.0 and 0.985-1.0, a store problem independent of memory state. Index failures recover after a settle on unchanged synapses (reported-only; `docs/plant2/P2-E4-online-memory.md:709-711`; `docs/plant2/P2-E4-diagnosis-plan.md:357-380`).
- In P2-R1, duty/1,000 content rises from .205 to .995 on the matched raster with an R_3 store, and forward-index errors cannot be caused by the feedback store (reported-only replay, reused seed 90; `docs/plant2/RESULTS-P2-R1.md:36-38, 44-46`).
**Evidence against.**
- The P2-E4 diagnosis found no variable that couples the problems (`docs/plant2/P2-E4-diagnosis-plan.md:446-447`), which is not evidence that they are independent.
- "These are separable intervention targets, not proven independent causes." The losses are operational and depend on the readout (the ranking reverses under the frozen readout). Random writers reach .710 at duty/1,000, so part of the gain is sparsity (reported-only; `docs/plant2/RESULTS-P2-R1.md:36-38, 44-46`; `review/plant2/P2-R1/findings-baseline-methodology.md:60, 75`).
**Tested by.** P2-E4, P2-E5 Part B, P2-R1
**Experiment needed.** Factorial interventions (operating state × store) on one live run. No contract names one.
**Notes.** The closeout's "The failure at high load is not a failure to store" (`DECISIONS.md:716`) is stronger than the owner's "not necessarily" (`DECISIONS.md:606`).

**H-033** Writes during probe slots store the probes
**Statement.** Writes during probe slots store about 170 probes, nearly all "stored" by arithmetic, and older-item recall falls as it does at matched load.
**Origin.** P2-E4 contract, reported-arms table, stress test (`docs/plant2/P2-E4-online-memory.md:466`), 2026-10-10.
**Status.** `refuted`
**Confidence.** Low: only about a fifth of the written probes were later recallable.
**Expected outcome if true.** Nearly all of the roughly 170 probes written are later recallable.
**Evidence for.**
- About 163-173 probes were written (reported-only; `review/plant2/P2-E4/results-northstar_constructive.md:126`).
**Evidence against.**
- Only 0.165-0.20 were later recallable, a figure confounded by the online index failure. The arithmetic counted writes: a 100 ms slot makes a line eligible with P about 0.76, against 0.986 in a 200 ms encoding (reported-only; `docs/plant2/P2-E4-online-memory.md:727, 751`; `review/plant2/P2-E4/results-northstar_skeptic.md` NS-4).
**Tested by.** P2-E4 (reported arm)
**Experiment needed.** Settled; see the P2-E4 reported arms.
**Notes.** The owner ruled that past-capacity and no-oracle arms are reported stress tests, not gates (`DECISIONS.md:406-407`).

## 4. Structured (correlated) inputs and forward-index interference

**H-034** Related exemplars are stored item by item
**Statement.** The frozen P2-E3 system, under P2-E3's settled protocol, stores exemplars of related families item-specifically (about 16 % sibling overlap, F = 10 families, M = 500 and 1,000). From a half cue it regenerates the item's own missing lines with few intrusions from the prototype or siblings, its memory index stays specific, and criteria S1-S4 hold on every gated seed at both loads.
**Origin.** Owner-ordered gate (rulings of 2026-10-10; `DECISIONS.md:394-402`). Written into the P2-E5 contract as "the one the existing system is expected to fail" (`docs/plant2/P2-E5-structured-items.md:107-117`), 2026-10-11.
**Status.** `refuted`
**Confidence.** Low: STRUCTURED INDEX FAIL and STRUCTURED CONTENT FAIL on 5 of 5 valid fresh gated seeds.
**Expected outcome if true.** S1-S4 pass on every gated seed at M = 500 and 1,000.
**Evidence for.**
- At s = 100, P2-E3's result replicates (joint 0.97-1.0) (reported-only). S3 holds (0.965-1.0), C1, C3 and the C4 recall half hold, and S1 passes entirely on seeds 21, 22 and 24 at M = 500 (gated; `docs/plant2/P2-E5-structured-items.md:869-911, 1002`).
**Evidence against.**
- S2 is 0.095-0.18 and S4 0.04-0.08 at M = 500, and 0.0-0.005 at M = 1,000. At M = 1,000, C2 is 0.435-0.515 and C4 spurious 0.35-0.49. At M = 500, S1 fails on seeds 23 and 25 (gated; `docs/plant2/P2-E5-structured-items.md:869-911`).
- The contract predicted an index cap at M = 500 (C2 about 0.90; P(S1 holds on all five seeds) 0.0095-0.039). S1 did fail, but C2 held on 4 of 5 seeds (183-186 of 200) and the failure is narrow (gated; `docs/plant2/P2-E5-structured-items.md:602-604, 905-907, 1010`).
**Tested by.** P2-E5
**Experiment needed.** Settled; see the P2-E5 verdict (`docs/plant2/P2-E5-structured-items.md:869-871`).
**Notes.** Fix-check R1 scoped the claim: which criteria fail depends on the operating point. In the online block at M = 500, C1 is 0.81-0.89, C2 0.995-1.0 and joint 0.475-0.575, against settled twin-A C2 0.87-0.93 (reported-only, unpaired; `docs/plant2/P2-E5-structured-items.md:119-147, 960-977`). The owner rejected a new mechanism to rescue the structured-input result (`DECISIONS.md:385-386`), and familiarity-gated allocation stays deferred. The report's claim that no pass was observed in simulation is withdrawn (H-083).

**H-035** Forward-index cross-talk on correlated items
**Statement.** On correlated items the forward index itself fails at high load. Spurious memory cells under a half cue are siblings' plateau cells (C2 about 0.45-0.55 and C4 spurious 0.35-0.47 at M = 1,000). This is a third problem, outside the owner's two (H-032), that no change to the feedback write can affect.
**Origin.** P2-E5 exploration by the red team and verifiers; the contract's "Why this test" (`docs/plant2/P2-E5-structured-items.md:80-92`) and `DECISIONS.md:512-518`, 2026-10-11.
**Status.** `mixed`
**Confidence.** High at M = 1,000 for the qualitative claim. At M = 500 the index failure is entangled with the operating point.
**Expected outcome if true.** C2 well below 0.90 at M = 1,000 with siblings' cells making up the spurious responders, and the index unchanged by any feedback swap.
**Evidence for.**
- C2 is 0.435-0.515 and C4 spurious 0.35-0.49 on every seed at M = 1,000 (gated; `docs/plant2/P2-E5-structured-items.md:905-911`). There are 16.5-18.9 spurious cells per half cue, 98 % of them siblings' plateau cells (reported-only, gated seeds; `review/plant2/P2-E5/results-northstar_constructive.md:38`; `review/plant2/P2-E5/results-methodology.md:62`).
- P2-R1: correlated M = 1,000 C2 is .500 and unchanged by every feedback swap. The prediction that R_3 and A both stay below 0.90 with C2 below 0.65 held (R_3 .160, A .125) (reported-only replay, reused seed 44; `docs/plant2/RESULTS-P2-R1.md:13-18`; `docs/plant2/P2-R1-takeover-replay.md:44-45`).
- Baseline C2 at F10/M = 1,000 recurs in later experiments: .500 in P2-E6 (exploratory, seed 101; `docs/plant2/RESULTS-P2-E6.md:12-43`), .470 in P2-R2 seed 103 (reported-only; `docs/plant2/RESULTS-P2-R2.md:76`), and .485 and .455 in P2-R2b seeds 105 and 106 (reported-only; `docs/plant2/RESULTS-P2-R2b.md:29-31`).
**Evidence against.**
- The predicted ranges in the statement were narrowly missed: the record scores the C2 prediction "0.45-0.55" as failed (down to 0.435), and C4 spurious reached 0.49, above the exploration's 0.35-0.47 (gated; `docs/plant2/P2-E5-structured-items.md:62, 908, 1005`).
- Constructive NS5: the failure is partly per-line load, not only correlation (`review/plant2/P2-E5/results-northstar_constructive.md:38`); see H-043.
**Tested by.** P2-E5; baselines in P2-R1, P2-E6, P2-R2 and P2-R2b
**Experiment needed.** Settled as a description. Its causes are H-043 and H-044. Remedies tested or proposed are H-040, H-060 and H-061, and B-001 is a speculative retrieval-side remedy.
**Notes.** Owner ruling 3 makes forward-index interference the next primary mechanism target, one mechanism per contract (`DECISIONS.md:786-788`). Status corrected from `supported` to `mixed` on 2026-10-22: the qualitative failure held on 5 of 5 gated seeds, but the record itself scores the statement's predeclared C2 range as failed.

**H-036** The responder write spreads content between related items
**Statement.** On correlated items the responder write R(x) contains earlier siblings' cells as well as A(x). Those cells receive x's lines and later regenerate them into sibling y's readout. At M = 500 the content failure is therefore intrusions (D2) while D1 holds, and the plateau-set store does not collapse there.
**Origin.** P2-E3 north-star skeptic NS1, replicated by the author on seed 97 (`docs/plant2/P2-E3-content-completion.md:483-503`), 2026-10-10. Its direction was corrected by the EVAL erratum (`docs/plant2/EVAL-after-P2-E3.md:205-222`), 2026-10-11, and written into the P2-E5 contract's mechanism section (`docs/plant2/P2-E5-structured-items.md:64-79`), 2026-10-11.
**Status.** `mixed`
**Confidence.** Medium: it holds at M = 500 in reported replays, but the index is not sound at M = 500 on 2 of 5 seeds, and the pooled control's causal attribution is withdrawn.
**Expected outcome if true.** At M = 500 the responder store fails S2 through intrusions while the plateau-set store passes on the same raster.
**Evidence for.**
- Joint is 0.147 and 0.167 at M = 500 (seeds 99 and 97), against 0.94 and 0.94 for the plateau-set store on the same raster; |R(x)| is 50-52 against |A| of about 20 (exploratory; `docs/plant2/P2-E3-content-completion.md:483-503`).
- Part B reads CONTAMINATION-DOMINANT at M = 500 (L_c 54-74, L_i 0). The plateau-set store passes S2 at the frozen point (186-195 of 200 cues) against 19-36 for the main store (reported-only; `docs/plant2/P2-E5-structured-items.md:893-903, 915-918`; `review/plant2/P2-E5/results-methodology.md:26`).
- P2-R1, correlated M = 500: R_3 .965 against inherited .090 (reported-only replay; `docs/plant2/RESULTS-P2-R1.md:13-18`).
**Evidence against.**
- S1 still fails at M = 500 on 2 of 5 seeds (gated; `docs/plant2/P2-E5-structured-items.md:905-907`). P2-R1's errata withdraw the clean causal attribution of the pooled control (H-039).
- At M = 1,000 no store reaches the content bar, not even the plateau-set store (`docs/plant2/STAGES.md:85`).
**Tested by.** P2-E3 (exploration), P2-E5 (reported), P2-R1 (replay)
**Experiment needed.** A live intervention on the store writer for correlated items at M = 500 while S1 is sound. A live R_3 write (B-011) is one.
**Notes.** The EVAL erratum reversed the skeptic's original direction (later siblings write onto earlier items' cells). It also places the forward index's C2 of about 0.47-0.50 at M = 1,000 upstream of any feedback write (exploratory; `docs/plant2/EVAL-after-P2-E3.md:205-222`). The statement above is the corrected form. The named sources do not state the gated-seed Part F class means.

**H-037** The structured failure is the responder write, with the plateau-set store as a clean baseline
**Statement.** P2-E5's draft hypothesis held that the structured-input failure is the responder write, and that the plateau-set store is a clean baseline against which to investigate it.
**Origin.** P2-E5 draft contract e736e81 and DECISIONS ruling 4 (`DECISIONS.md:512-518`), drafted 2026-10-10 and rewritten 2026-10-11.
**Status.** `withdrawn`
**Confidence.** Low: at M = 1,000 the index fails and the plateau-set store fails at every point of a 72-point grid.
**Expected outcome if true.** The plateau-set store passes at both loads, and only the responder store fails.
**Evidence for.**
- It holds at M = 500 only, where the plateau-set store reads 0.92-0.94 at the frozen point (exploratory, seeds 44-45; `docs/plant2/P2-E5-structured-items.md:61`).
**Evidence against.**
- At M = 1,000, C2 is 0.465-0.495 (contract L61), reported as 0.465-0.48 by the owner-intent red team and 0.47-0.50 at `DECISIONS.md:513`. The plateau-set store reads 0.155-0.18 at the frozen point (0.12-0.18 in the contract's table) and fails at every point of a 72-point grid (best joint 0.60 on seed 44, 0.665 on seed 45). The draft stated the cause backwards (exploratory; `review/plant2/P2-E5/redteam-owner_intent.md:7`; `DECISIONS.md:512-518, 646-647`; `docs/plant2/P2-E5-structured-items.md:61, 80-92`).
**Tested by.** P2-E5 exploration
**Experiment needed.** Settled; the contract was rewritten (`docs/plant2/P2-E5-structured-items.md:80-92`).
**Notes.** none

**H-038** Contamination is the most consequential failure at both loads
**Statement.** Under P2-E5 Part B, contamination of the content store is the most consequential failure at both loads. The prediction was CONTAMINATION-DOMINANT, with M = 500 at about 0.7-0.96 or SPLIT given the measured L_o of 0.145-0.185.
**Origin.** Owner guidance of 2026-10-11 to rank the failures, and completeness critic C1; P2-E5 contract, Part B, 2026-10-11.
**Status.** `mixed`
**Confidence.** Medium at M = 500. Low at M = 1,000, where the reading depends on the readout convention.
**Expected outcome if true.** The predeclared reading is CONTAMINATION-DOMINANT at both loads under every readout convention.
**Evidence for.**
- The predeclared reading is CONTAMINATION-DOMINANT at both loads on 5 of 5 attributable seeds, and the M = 500 frozen-point L_c of 144-161 also points to contamination (reported-only; `docs/plant2/P2-E5-structured-items.md:915-918, 927-931`).
**Evidence against.**
- At M = 1,000 the reading holds only under the grid-best convention. The frozen readout reads INDEX-DOMINANT on 5 of 5 seeds, all three losses are material, and the grid best is edge-censored on some seed-loads (reported-only; `docs/plant2/P2-E5-structured-items.md:927-931`; `review/plant2/P2-E5/results-code.md:17-20`).
**Tested by.** P2-E5 Part B
**Experiment needed.** Settled under the owner's later ruling that the frozen readout is primary (`DECISIONS.md:793`; `docs/plant2/EVAL-after-P2-E5.md:144-145`). At M = 1,000 the index dominates (H-035).
**Notes.** P2-R1 found the losses operational and readout-dependent, not an additive decomposition (H-032).

**H-039** The pooled-input control isolates sibling organisation from marginal load
**Statement.** P2-E5's pooled-input arm (same per-line loads, no sibling correlation) isolates sibling organisation from the marginal load distribution, which justifies the label CORRELATION-ATTRIBUTABLE.
**Origin.** P2-E5's labelling (`docs/plant2/P2-E5-structured-items.md:194, 203`), 2026-10-11.
**Status.** `withdrawn`
**Confidence.** Low: the pooled arm flattens load hotspots and so does not hold each line's load fixed.
**Expected outcome if true.** The pooled arm matches every line's load exactly.
**Evidence for.**
- The pooled labels were calculated correctly, and the pooled control passes S2 on 5 of 5 seeds at M = 500 (reported-only; `docs/plant2/P2-E5-structured-items.md:994`).
**Evidence against.**
- The pooled arm matches hot and cold groups, not each line's frequency. Its maximum line load is 81-89 against 137-148, and the prototype-union load SD 7.17-7.65 against 13.36-15.45 at M = 1,000 (reported-only audit; `review/plant2/P2-R1/findings-baseline-methodology.md:4-26`).
**Tested by.** P2-R1 baseline audit
**Experiment needed.** Settled; replaced by the exact-degree null (H-043, H-044).
**Notes.** The erratum is appended at `docs/plant2/EVAL-after-P2-E5.md:126-131`, dated 2026-10-12.

**H-040** Load-gated encoding improves specificity on correlated items
**Statement.** "Frequent sensory lines acquire synapses into many assigned assemblies and therefore recruit siblings under partial cues; redistributing a fixed encoding budget toward less frequent eligible inputs (presynaptic-load-gated flip probabilities) should improve specificity without obtaining it by silencing the index."
**Origin.** P2-E6 contract (`docs/plant2/P2-E6-load-gated-encoding.md:9-19`), 2026-10-12, motivated by P2-E5 and by P2-R1's finding that the old pooled control did not match the load on frequently used lines.
**Status.** `mixed`
**Confidence.** Medium: the relative gains are large, but they come from one development seed, the frozen absolute bars failed, and the mechanism is rejected under its acceptance criteria.
**Expected outcome if true.** At F10/M = 1,000, C2 and oldest specificity reach at least 0.90 with C1 not regressing, and the candidate beats the matched random control by at least 0.10.
**Evidence for.**
- F10/1,000: C2 rises from .500 to .895 and joint from .440 to .865. Spurious responders fall from 16.970 to 3.145 while own responders rise from 18.585 to 18.925. F10/500: C2 rises from .885 to 1.000. Against matched random the candidate gains +.435 C2 and +.455 joint, with paired specificity gains/losses of 79/0 and 87/0 (exploratory, development seed 101, predeclared screen; `docs/plant2/RESULTS-P2-E6.md:12-43`).
- The contract predictions held: C2 .895 within 0.70-0.95, C1 .970 within 0.85-0.98, and content poor at M = 1,000 (exploratory; `docs/plant2/RESULTS-P2-E6.md:60-65`).
- Independent-input regression passed: C1 .975 against .980 and .935 against .960; content joint 1.000 against .995 and .975 against .975 (exploratory; `docs/plant2/RESULTS-P2-E6.md:55-58`).
- In the F = 40 transfer arm all six absolute index bars are met at both loads, with C2 at M = 1,000 rising from .820 to .950 (reported-only, seed 101; `docs/plant2/RESULTS-P2-E6.md:111-116`; `review/plant2/P2-E6/findings-results.md:57`).
**Evidence against.**
- FEASIBILITY FAIL: at F10/1,000, C2 is 179/200 (.895) and oldest specificity 89/100 (.890), each below 0.90. The "mechanism is rejected under its frozen acceptance criteria" (exploratory, seed 101; `docs/plant2/RESULTS-P2-E6.md:12-43`; `review/plant2/P2-E6/findings-results.md:3, 65`).
- Only one development seed was run; held-out seed 102 and gated seeds 111-115 were not (`docs/plant2/STAGES.md:117`).
- At F40/500 the candidate's joint is .920 against baseline .950, and recall discordance is 4:10 against baseline at M = 1,000 (reported-only; `docs/plant2/RESULTS-P2-E6.md:111-116`; `review/plant2/P2-E6/findings-results.md:57`).
**Tested by.** P2-E6
**Experiment needed.** Settled for this mechanism, which is not to be retuned; see `docs/plant2/RESULTS-P2-E6.md`. The remaining cross-talk goes to H-060 and H-061.
**Notes.** The oldest-item bar was predicted as the most likely failure, and it failed. The failures are not confined to old items, though: 11 oldest and 10 elsewhere, with age strata .8667, .9070 and .8944 (n = 15, 43, 142) (exploratory; `review/plant2/P2-E6/findings-results.md:28, 49`). The analytic rationale, flip probabilities of about 0.20 on frequently used lines and 0.70 on rarely used ones with 50 expected flips, is an approximation not checked against realised probabilities (`docs/plant2/P2-E6-load-gated-encoding.md:138-141`). Retuning E6 and combining R_3 with E6 without a new contract are not authorised (`DECISIONS.md:857, 872-878`).

**H-041** Presynaptic history matters beyond the flip budget
**Statement.** Assigning flip probabilities by history matters beyond the attempted flip budget. At F10/M = 1,000, separately on each seed, the candidate beats an exact flip-count-matched random control by at least 0.10 in C2 and in joint index, and beats the baseline by at least 0.20 in C2.
**Origin.** P2-E6 contract, with the control strengthened by a reviewer (`docs/plant2/P2-E6-load-gated-encoding.md:56-64, 110-117`), 2026-10-12.
**Status.** `mixed`
**Confidence.** Medium: every margin passed by a wide amount, but on one development seed only.
**Expected outcome if true.** All relative margins pass on every seed.
**Evidence for.**
- C2 is +.435 against random and +.395 against baseline; joint is +.455 against random and +.425 against baseline. Paired specificity is 87:0 against random and joint 94:3 (exploratory, seed 101; `docs/plant2/RESULTS-P2-E6.md:26-30`).
**Evidence against.**
- There is one seed only. The control does not match additions, depressions, density or adaptive threshold state, and the result "does not establish seed-general reliability" (`review/plant2/P2-E6/findings-results.md:28-30`).
**Tested by.** P2-E6
**Experiment needed.** A fresh-seed replication with a control matched on density and threshold state. None is contracted.
**Notes.** none

**H-042** Input-side gains in specificity do not come from silencing
**Statement.** When an input-side change raises specificity on correlated items, the gain comes from fewer spurious responders while own responders and recall are kept. P2-E6 required F10 C1 no more than 0.03 below baseline, plus paired response, threshold and density diagnostics. P2-R2b's prediction P6 required |mean Δown50| < 1.0 and mean Δspurious50 < -10.0 on both seeds.
**Origin.** P2-E6 methodology reviewer, finding 2 (`review/plant2/P2-E6/findings-contract-methodology.md:11`), 2026-10-12. P2-R2b frozen prediction P6 (`docs/plant2/P2-R2b-replication.md:131-136`), 2026-10-22.
**Status.** `mixed`
**Confidence.** Medium: own responders held on every seed measured, but P6's predeclared magnitude failed on seed 106 and E6's operating states differ.
**Expected outcome if true.** Own responders unchanged, spurious responders sharply fewer, and recall not lower.
**Evidence for.**
- In E6, own responders rise from 18.585 to 18.925, density from .055841 to .057623, and the threshold offset falls from 5.811 to 5.469 mV. Recall at M = 1,000 is .970 against .935, and C1 non-regression is met at both loads (exploratory, seed 101; `docs/plant2/RESULTS-P2-E6.md:17-18, 39-47`).
- P2-R2b seed 105: Δown50 -0.025 and Δspurious50 -10.46, which passes. Seed 106: Δown50 +0.265 (reported-only; `docs/plant2/RESULTS-P2-R2b.md:61, 105-108`).
- P2-R2 valid seed 103 at M = 1,000: own responders 18.990 to 18.660 and spurious 21.195 to 7.410, forward density .0569378 to .0569953 (reported-only; `docs/plant2/RESULTS-P2-R2.md:105-109`).
**Evidence against.**
- P6 failed on seed 106 with Δspurious50 -6.97. Spurious responders went from 15.47 to 8.50 (45 %) on 106, against 17.57 to 7.11 (59 %) on 105 (reported-only; `docs/plant2/RESULTS-P2-R2b.md:61, 105-108`).
- E6: "effective operating states nevertheless differ, so this does not isolate discrimination at matched neural state". At F10/500 recall is .945 against .960 (wins/losses 5/8 against baseline), and independent/1,000 recall is .935 against .960 (1:6) (exploratory; `docs/plant2/RESULTS-P2-E6.md:14-15, 106, 108`; `review/plant2/P2-E6/findings-results.md:32, 47`).
**Tested by.** P2-E6, P2-R2, P2-R2b
**Experiment needed.** A comparison at matched neural state, with threshold and density matched, in the next mechanism contract.
**Notes.** P2-R2b erratum 3: the reading that no global silencing occurred is descriptive, not a prediction outcome (`docs/plant2/RESULTS-P2-R2b.md:105-108`). P2-R2 likewise records that operating state is not held fixed (`docs/plant2/RESULTS-P2-R2.md:109`).

**H-043** Interference remains when each line's usage is held exactly fixed
**Statement.** Substantial F10/s60 index interference remains at M = 1,000 when every input line's usage is held exactly fixed within each 100-episode block but the grouping of lines into related episodes is randomised (the exact-degree null). The original family grouping is therefore not necessary for the high-load failure.
**Origin.** P2-E5 methodology M2, fix-check R2 and reviewers' NS5 on line load (`docs/plant2/P2-E5-structured-items.md:187-205`), 2026-10-11. P2-R2 contract question (`docs/plant2/P2-R2-degree-null.md:25-27`), 2026-10-12. P2-R2b prediction P3 (`docs/plant2/P2-R2b-replication.md:123-125`), 2026-10-22.
**Status.** `supported`
**Confidence.** High that grouping is not necessary. The record does not identify line frequency as the only remaining cause, and the design does not apportion the failure between line load and co-occurrence.
**Expected outcome if true.** Null-arm C2 and oldest specificity stay below 0.90 at M = 1,000 on every valid seed.
**Evidence for.**
- P2-R2 valid seed 103: null C2 .755 and oldest specificity .680 (reported-only; `docs/plant2/RESULTS-P2-R2.md:84-88`).
- P2-R2b prediction P3 held on both fresh seeds. Null C2 is .745 (105) and .720 (106), oldest specificity .710 and .680, and the fraction of the C2 bar deficit removed 0.62651 and 0.59551 (reported-only; `docs/plant2/RESULTS-P2-R2b.md:26-40, 58`).
- In P2-E5, the pooled arm at M = 1,000 gives joint 0.105-0.18 and plateau-set store 0.49-0.63. At F = 40 the plateau-set store reads 0.83-0.91 against 0.14-0.175 at F = 10. The frozen label was LINE LOAD SUFFICIENT, CORRELATION WORSENS (reported-only; `docs/plant2/P2-E5-structured-items.md:984-996`; `docs/plant2/EVAL-after-P2-E5.md:100-102`).
- P2-R2 seed 104: null C2 .715 and oldest specificity .670 (INVALID, post hoc reconstruction; `docs/plant2/RESULTS-P2-R2.md:78-82`).
**Evidence against.**
- The null is not a causal partition. Fine timing, cue composition, actual eligibility, coin alignment (BTSP coin draw counts differ on "713/722 episodes" in P2-R2, one figure per seed; the seed order is inferred, not verified) and adaptive state also change, so the result "does not show that line frequency is the sole residual cause" (`docs/plant2/P2-R2-degree-null.md:35-41`; `docs/plant2/RESULTS-P2-R2.md:111-116, 133-136`; `review/plant2/P2-R2/findings-results.md:72`; `docs/plant2/RESULTS-P2-R2b.md:48-50`).
- P2-E5's pooled control flattens hotspots and does not isolate load (H-039).
**Tested by.** P2-E5 (reported arms), P2-R2, P2-R2b
**Experiment needed.** Settled for "grouping not necessary"; see `docs/plant2/RESULTS-P2-R2b.md`. Apportioning the failure between load and co-occurrence needs a different design (P2-R2b erratum 1).
**Notes.** P2-R2's formal two-seed result is INVALID because seed 104's combined artifact was found empty at the paired read. The record declines to attribute the cause to concurrency, Git, the filesystem, a worker or an external actor, so that cause stays `unresolved` (`review/plant2/P2-R2/findings-integrity.md:5-25`; `docs/plant2/RESULTS-P2-R2.md:39-44`). P2-R2b removed git operations during runs as a confound and verified every artifact. P2-E5's broader form, that per-line load and not only correlation drives the M = 1,000 failure (P2-E5 hypothesis on line load, ledger status mixed), is not decided here: P2-R2b erratum 1 says "this design does not apportion the failure between line load and co-occurrence" (`docs/plant2/RESULTS-P2-R2b.md:96-101`). The draft statement's clause "per-line load contributes beyond sibling correlation" was removed on 2026-10-22 for that reason.

**H-044** Material structure sensitivity at high load
alias: H-R2
**Statement.** At M = 1,000, randomising which lines co-occur, while holding every line's count exact within each 100-episode block, improves C2 by at least 0.15 and joint index by at least 0.10 without losing more than 0.03 of C1 or oldest recall. This is the frozen label MATERIAL STRUCTURE SENSITIVITY: the high-load C2 deficit is materially sensitive to co-occurrence structure.
**Origin.** The P2-R1 baseline methodology reviewer proposed the exact-degree shuffle (`review/plant2/P2-R1/findings-baseline-methodology.md:77-79`), 2026-10-12. It was selected after P2-E6 (`DECISIONS.md:851-857`), 2026-10-12. It is the P2-R2 contract prediction (`docs/plant2/P2-R2-degree-null.md:227-229`), and P2-R2b replicated it as prediction P2 under the name H-R2 (`docs/plant2/P2-R2b-replication.md:12, 120-122`), 2026-10-22.
**Status.** `supported`
**Confidence.** High: the predeclared label held on P2-R2's valid seed 103 and on both fresh P2-R2b seeds, with verified evidence.
**Expected outcome if true.** The label MATERIAL STRUCTURE SENSITIVITY at M = 1,000 on every valid seed.
**Evidence for.**
- P2-R2 seed 103: ΔC2 +.285, Δjoint +.265, ΔC1 -.010 (reported-only; `docs/plant2/RESULTS-P2-R2.md:84-85`).
- P2-R2b prediction P2 held on seeds 105 and 106. ΔC2 is +0.260 and +0.265, Δjoint index +0.240 and +0.280, ΔC1 -0.010 and +0.035, and Δ oldest recall -0.020 and +0.030. Evidence verification passed (33 and 31 artifacts re-read and hash-checked) (reported-only; `docs/plant2/RESULTS-P2-R2b.md:11-18, 33-40`; `docs/plant2/P2-R2b-replication.md:166-172`).
- The structural decorrelation held: the overlap contrast D went from 14.45394 to 0.00248 on seed 103 (reported-only) and from 14.39250 to -0.00171 on seed 104 (INVALID; `docs/plant2/RESULTS-P2-R2.md:46-65`). The F10 structural checks passed on seeds 105 and 106 (reported-only; `docs/plant2/RESULTS-P2-R2b.md:16-18`).
- P2-R2 seed 104: ΔC2 +.255, Δjoint +.240, ΔC1 -.010, computed here from the table (INVALID, post hoc reconstruction; `docs/plant2/RESULTS-P2-R2.md:78-82`).
- As P2-R2 predicted, the gain is smaller at M = 500. Seed 103's joint gain is +.075 at M = 500 against +.265 at 1,000, and P2-R2b's ΔC2 at 500 is +0.045 (105) and +0.095 (106) (reported-only, LOW-LOAD DESCRIPTIVE; `docs/plant2/RESULTS-P2-R2.md:75-77, 84, 90-92`; `docs/plant2/RESULTS-P2-R2b.md:42-46`).
**Evidence against.**
- Heuristic checks on a finite chain do not certify uniform sampling or the removal of higher-order dependence (`docs/plant2/RESULTS-P2-R2.md:46-65`). Coin draw counts differ between arms, and eligibility differs by at most 2-3 episodes per block, so the sampling is paired, not identical spikes (`docs/plant2/RESULTS-P2-R2b.md:48-50`).
- P2-R2b ran on a different runtime from P2-R2 (CPython 3.11.17 and NumPy 2.4.6, against 3.12.14 and 2.3.5), which is confounded with seed (`docs/plant2/P2-R2b-replication.md:100-103`).
**Tested by.** P2-R2, P2-R2b
**Experiment needed.** Settled; see `docs/plant2/RESULTS-P2-R2b.md`.
**Notes.** P2-R2b erratum 1 bounds the wording: the C2 deficit "is materially sensitive to co-occurrence structure under block-constrained randomisation; this design does not apportion the failure between line load and co-occurrence" (`docs/plant2/RESULTS-P2-R2b.md:96-101`). This is an explanation result, not a capability, and it removes no experimenter supply. Erratum 5: meeting the capability review's condition (H-061) informs, and does not by itself authorise, the next mechanism contract. The riders are H-045 (refuted) and H-046 (supported).

**H-045** The exact-degree null's low-load gain costs oldest recall
**Statement.** At M = 500 the exact-degree null's index gain comes with a cost in oldest recall. P2-R2b's prediction P5 required, on at least one seed, Δ oldest recall ≤ -0.03 together with inherited ΔS2 ≥ 0.10. Put the other way, the low-load gain is not recall-preserving.
**Origin.** P2-R2's reporting flag (`docs/plant2/P2-R2-degree-null.md:221-223`), 2026-10-12, after seed 103 went from .980 to .910. Frozen as P2-R2b prediction P5 (`docs/plant2/P2-R2b-replication.md:128-130`), 2026-10-22.
**Status.** `refuted`
**Confidence.** Low: P5 failed on both fresh seeds, which leaves a single observation on seed 103.
**Expected outcome if true.** Oldest-recall delta ≤ -0.03 at M = 500 on at least one fresh seed.
**Evidence for.**
- Seed 103's oldest recall fell from .980 to .910 at M = 500, a loss of 0.070, so the recall-preserving flag was false (reported-only; `docs/plant2/RESULTS-P2-R2.md:75, 90-92`).
**Evidence against.**
- P2-R2b's P5 failed. Oldest-recall deltas were -0.010 (105) and +0.010 (106), alongside content gains of +0.845 and +0.825 (reported-only; `docs/plant2/RESULTS-P2-R2b.md:60, 63-68`).
- On seed 104 the flag was true (C1 .960 to .935, oldest recall .950 to .940) (INVALID; `docs/plant2/RESULTS-P2-R2.md:77, 80-82`).
**Tested by.** P2-R2, P2-R2b
**Experiment needed.** Settled; see `docs/plant2/RESULTS-P2-R2b.md:63-68`. The seed-103 result stays recorded as an observation.
**Notes.** This rider's failure is what lets the capability review's condition ("without the declared recall loss") count as met.

**H-046** Improving the forward index alone does not give clean content at M = 1,000
**Statement.** At M = 1,000 on F10 items, improving the forward index does not by itself give clean content: inherited content stays below 0.90 even when index specificity rises. P2-R2b's P4 required inherited joint < 0.15 and assigned-A < 0.40 on both arms.
**Origin.** P2-E6 contract prediction "content can still fail despite index gains" (`docs/plant2/P2-E6-load-gated-encoding.md:146`), 2026-10-12. P2-R2 prediction (`docs/plant2/P2-R2-degree-null.md:230-231`), 2026-10-12. P2-R2b prediction P4 (`docs/plant2/P2-R2b-replication.md:126-127`), 2026-10-22.
**Status.** `supported`
**Confidence.** High at M = 1,000. At M = 500, index improvement does bring content above the bar.
**Expected outcome if true.** Inherited content stays below its bar at M = 1,000 whenever the index improves.
**Evidence for.**
- P2-E6 at F10/1,000: the candidate's inherited content joint is .065, oldest D4 .020, and assigned-A .425 and .390. At F40/1,000 it is .200, with D4 .070 (exploratory, seed 101; `docs/plant2/RESULTS-P2-E6.md:51-53, 132-134`; `review/plant2/P2-E6/findings-results.md:55`).
- P2-R2 seed 103: null inherited content goes from .005 to .075, and assigned-A from .130 to .320 (reported-only; `docs/plant2/RESULTS-P2-R2.md:76, 92-101`).
- P2-R2b's P4 held. Inherited content goes from .000 to .065 and from .000 to .070; assigned-A from .175 to .315 and from .110 to .295 (reported-only; `docs/plant2/RESULTS-P2-R2b.md:26-40, 59`).
**Evidence against.**
- At M = 500, index gains do carry content. The E6 candidate's inherited content joint at F10/500 is .785 against a baseline .120 (`docs/plant2/RESULTS-P2-E6.md:14-15`). P2-R2b's null inherited content goes from .115 to .960 and from .140 to .965. P2-R2 seed 103's null reads .980 (exploratory and reported-only; `docs/plant2/RESULTS-P2-E6.md:51-53`; `docs/plant2/RESULTS-P2-R2b.md:42-46`; `docs/plant2/RESULTS-P2-R2.md:92-101`).
**Evidence (added 2026-10-22, P2-R3 exact replay on seed 121, reported-only).** The reading "index gains do not carry content at 1,000" holds for the point reconstruction store and is explained: every content failure but a handful at 1,000 is an intrusion failure by cross-episode writer summation (step 0: 97.8 % on the oracle, 100 % on gate_off). With K = 32 episode-clustered branches the content follows the index: gate_off (C2 .500) .005 → .345, candidate (C2 .745) .005 → .710, oracle (C2 .970) .310 → .985 (`docs/plant2/RESULTS-P2-R3.md`). Content at 1,000 is index-limited through the point store and summation-limited through the readout; H-085 carries the second half.
**Tested by.** P2-E6, P2-R2, P2-R2b, P2-R3 (replay)
**Experiment needed.** Settled at M = 1,000 for the point store; see `docs/plant2/RESULTS-P2-R2b.md`. Content-side directions are H-047, H-050 and H-085.
**Notes.** P2-R2b erratum 4: the assigned-A changes at M = 1,000 carry the label MATERIAL GAIN (+0.140, +0.185) (`docs/plant2/RESULTS-P2-R2b.md:109-111`).

**H-083** Online, the structured-item index is specific but slow, and no pass was observed in simulation
**Statement.** P2-E5's appended predictions and report to the owner said "Online, the index is specific but slow", and that "no pass was observed in simulation".
**Origin.** P2-E5 appended predictions section and report to the owner, corrected in the Result (`docs/plant2/P2-E5-structured-items.md:971-981`), 2026-10-11. Added to this ledger by the 2026-10-22 critic pass; the hypothesis was in the P2-E5 source record but missing from the first draft of this file.
**Status.** `withdrawn`
**Confidence.** Low as written: the C2 comparison was unpaired, latency was not measured, and no passes were simulated.
**Expected outcome if true.** A paired per-cue comparison on the same cues shows online C2 at least as high as settled C2 with later first spikes; and simulated runs of the structured gate exist and none pass.
**Evidence for.**
- In the online block at M = 500, C2 is 0.995-1.0 against settled twin-A C2 of 0.87-0.93 (reported-only, gated seeds, different cue sets; `docs/plant2/P2-E5-structured-items.md:964-965`).
**Evidence against.**
- The online and settled C2 come from different cue sets, so the comparison is unpaired; no 75 ms memory rate is recorded for the online arm, so "slow" was not measured; online the memory layer fires less, giving fewer spurious and fewer own cells, consistent with one shift along a sensitivity-specificity curve (`docs/plant2/P2-E5-structured-items.md:971-978`; `review/plant2/P2-E5/results-northstar_skeptic.md:32-33`).
- P(PASS) was an analytic binomial product evaluated on 400 posterior draws and was numerically zero; no passes were simulated, and it is not proof that a pass is impossible (`docs/plant2/P2-E5-structured-items.md:979-981`).
**Tested by.** P2-E5 (reported arms; skeptic review NS4)
**Experiment needed.** Settled as withdrawn. A paired per-cue C1 × C2 analysis on the same cues online and settled would decide the "specific" half (H-029).
**Notes.** The id is out of thematic order because the entry was added after H-082.

**H-084** The committed P2-E4 and P2-E5 counts support their reported failures
**Statement.** P2-R1 contract question 1: "Do committed P2-E4/E5 counts and verdicts support the reported failures?"
**Origin.** P2-R1 contract, question 1 (`docs/plant2/P2-R1-takeover-replay.md:8`), 2026-10-12. Added to this ledger by the 2026-10-22 critic pass; the hypothesis was in the P2-R1 source record but missing from the first draft of this file.
**Status.** `mixed`
**Confidence.** High for the frozen FAIL verdicts. The audit recomputed aggregates only, and it withdrew or refuted three interpretive claims built on the same records.
**Expected outcome if true.** Every committed criterion bit, per-cue count and derived value recomputes exactly, and every frozen verdict stands.
**Evidence for.**
- 80 criterion-vector bits, 20 per-cue joint counts, 10 histogram AUCs and 30 grid-loss values all matched (checks_passed true); P2-E4's embedded item summaries reproduce the O4/O5 counts; "frozen FAIL verdicts remain supported by the committed records" (reported-only audit; `bench/results/p2r1-audit.jsonl:1`; `review/plant2/P2-R1/findings-baseline-methodology.md:1, 69-72`).
**Evidence against.**
- Aggregate recomputation only: all 28 unique P2-E4/E5 cache paths referenced in the committed records were absent, so raw spike-level outcomes were not recomputed (`review/plant2/P2-R1/findings-baseline-methodology.md:41`). The same audit refuted or withdrew the claims recorded as H-025, H-039 and H-051 (`review/plant2/P2-R1/findings-baseline-methodology.md:4-38`).
**Tested by.** P2-R1 (baseline audit)
**Experiment needed.** None for the verdicts. The raw caches cannot be recomputed because they no longer exist.
**Notes.** Status is `mixed` rather than `supported` because an audit of committed aggregates is not a predeclared test on fresh seeds. The id is out of thematic order because the entry was added after H-083.

## 5. Writer identity and eligibility signals

**H-047** Being active during an experience should not by itself qualify a cell to write the content
**Statement.** "A memory cell being active during an experience should not automatically qualify it to write that experience's content." Eligibility must be derived locally. The owner's candidate is a local signal tied to a genuine plateau event. An activity form is the burst rule: a cell writes content only if it fires at least 3 spikes in the 50 ms continuation, with k = 3 fixed by P2-E5 Part C.
**Origin.** Owner's hypothesis after P2-E4 (`DECISIONS.md:590-598`), 2026-10-11, stated as "not permission to modify current experiments". The burst form came from the P2-E4 constructive reviewer (`docs/plant2/EVAL-after-P2-E4.md:110-118`), 2026-10-11.
**Status.** `proposed`
**Confidence.** Medium: replays show that burst-selected writers give clean stores, but no live mechanism exists, and in this model a plateau-event form reproduces the experimenter's key.
**Expected outcome if true.** A live local-eligibility write gives online content close to the assigned-assembly store, beats count-matched random writers, and removes the contamination described in H-031.
**Evidence for.**
- Burst-count AUC is 0.9999 on the main line and the duty arm. At M = 1,000, twin A reads the R_3 store at 0.995/0.995, against 0.83/0.205 for the online-written store and 0.885/0.71 for a size-matched random subset (exploratory, seed 90; `docs/plant2/EVAL-after-P2-E4.md:110-160`).
- Replay measurements: H-048 and H-049.
**Evidence against.**
- By construction it would inherit every index failure. It does not fix slow access, habituation or forward cross-talk: in P2-R1, correlated M = 1,000 content stays .160 with C2 .500. A lure drives about 5 of the stored item's assembly cells to burst (`docs/plant2/EVAL-after-P2-E4.md:110-160`; `docs/plant2/STAGES.md:116`).
- In the current model a write gated by the plateau trace reproduces the assigned-assembly store exactly and inherits the random, content-blind key (`DECISIONS.md:615, 624-626`).
**Tested by.** Untested live; the replay measurements are recorded under H-048 and H-049.
**Experiment needed.** B-011: a live contract for the burst-gated write on P2-E4's online schedule, with count-matched random and anti-selected writers. The owner's "reported replay first" condition is met.
**Notes.** P2-R1 errata: failure of one burst threshold would not prove the idea architecturally impossible. The owner ruled that burst-gated eligibility is a reported replay or diagnostic, not yet a gated mechanism (`DECISIONS.md:778-782`).

**H-048** The plateau key can be recovered from the network's activity
**Statement.** Cells with at least 3 continuation spikes (R_3) pick out the assigned plateau set A(x) (count AUC ≥ 0.95), and a store written from them equals the plateau-set store within 10 cues (AVAILABLE FROM ACTIVITY).
**Origin.** P2-E5 completeness critic C4, from the owner's research target. Contracted as P2-E5 Part C (`docs/plant2/P2-E5-structured-items.md:93-101, 421-443`), 2026-10-11, and re-measured in P2-R1 on 2026-10-12.
**Status.** `mixed`
**Confidence.** High as a measurement. It recovers the experimenter's key and is not a mechanism.
**Expected outcome if true.** Count AUC ≥ 0.95, and the R_3 store within 10 cues of the plateau-set store on every seed and load.
**Evidence for.**
- Count AUC is 0.9988-0.9995 at M = 500 and 0.9955-0.9971 at M = 1,000, and R_3 is within 0-7 cues of the plateau-set store on every gated seed and load (reported-only; `docs/plant2/P2-E5-structured-items.md:939-947`). Online count AUC is 0.998 on exploration seeds 44-45 (exploratory; `docs/plant2/P2-E5-structured-items.md:840`).
- In P2-R1, writer precision/recall against A is .9975/.9657 (correlated, 1,000), .9986/.9997 (duty, 1,000), .9987/.9933 (correlated, 500) and 1.0000/.9998 (duty, 500) (reported-only replay; `docs/plant2/RESULTS-P2-R1.md:25-30`; `bench/results/p2r1.jsonl:5, 7, 9, 11`).
**Evidence against.**
- Positives are defined by A(x), the experimenter's random content-blind key, and those cells burst because the plateau has just written them. First-spike AUC is only about 0.78-0.81, and k = 3 was fixed in advance (`docs/plant2/P2-E5-structured-items.md:937-947`; `docs/plant2/EVAL-after-P2-E5.md:36-38, 45`).
- "This is evidence for recovering an assigned key from activity, not selecting an autonomous representation." (`docs/plant2/RESULTS-P2-R1.md:25-30`)
**Tested by.** P2-E5 Part C, P2-R1
**Experiment needed.** Settled as a measurement; see P2-E5 and P2-R1.
**Notes.** The original framing, "own-cell identity is in the network's activity", is withdrawn (`docs/plant2/P2-E5-structured-items.md:939-947`). Choosing R_4 or R_6 after the fact would be parameter rescue.

**H-049** Which responders write matters beyond how many
**Statement.** Writer identity, meaning which observed responders write, matters beyond sparsity: on unchanged memory rasters an R_3 store beats count-matched random and anti-selected writers. The duty/1,000 prediction was R_3 joint ≥ 0.90, at least 0.10 above both controls, with inherited joint below 0.35.
**Origin.** P2-R1 contract, question 2 and predictions (`docs/plant2/P2-R1-takeover-replay.md:9, 43-47`), 2026-10-12.
**Status.** `mixed`
**Confidence.** Medium: every predeclared inequality held, but on a settled replay of reused exploratory seeds with one control realisation each.
**Expected outcome if true.** R_3 beats count-matched random and anti-selected writers on every raster.
**Evidence for.**
- Duty, M = 1,000: R_3 .995 against random .710 and anti .655, with inherited .205 and paired wins/losses of 57/0 and 68/0. Correlated, M = 500: R_3 .965 against random .300, anti .090 and inherited .090, with 133/0 and 175/0 (reported-only replay, reused seeds 90 and 44; `docs/plant2/RESULTS-P2-R1.md:13-18, 27-28, 36-38`; `review/plant2/P2-R1/findings-results-methodology.md:51`).
- The F10/M = 500 prediction (R_3 joint at least 0.85, inherited below 0.25, R_3 within 0.05 of A) held (reported-only replay; `docs/plant2/P2-R1-takeover-replay.md:43`; `review/plant2/P2-R1/findings-results-methodology.md:29`).
**Evidence against.**
- Store union sizes and degree distributions differ, and each control has one realisation. Random writers reach .710, so part of the gain is sparsity. Correlated M = 1,000 R_3 is only .160 and not monotonic item by item against R_1 (wins 32, losses 2). At duty M = 500 the inherited store is already .995 (reported-only; `review/plant2/P2-R1/findings-results-methodology.md:49-57`; `bench/results/p2r1.jsonl:7, 11`).
- Seed 90's twin-A R_3 (.995) and random (.71) values were recorded before the contract (exploratory; `docs/plant2/EVAL-after-P2-E4.md:120-127`).
**Tested by.** P2-R1
**Experiment needed.** A live burst-gated write on fresh seeds (B-011; H-050).
**Notes.** The P2-R1 entry at `docs/plant2/STAGES.md:116` reports no live R_3 result and no new gated capability.

**H-050** A live burst-gated write gives clean content online
**Statement.** A live burst-gated (R_3) feedback write during online learning gives clean content in online retrieval, as the settled replays suggest. The constructive reviewer proposed gating it on content at M = 500 and on P2-E4's online tests.
**Origin.** P2-E5 results reviewer, north-star constructive NS1 (`review/plant2/P2-E5/results-northstar_constructive.md:11-16`), 2026-10-11. The move from settled to live was examined in P2-R1 (`review/plant2/P2-R1/findings-results-methodology.md:37-39`), 2026-10-12.
**Status.** `proposed`
**Confidence.** Low: the live inherited duty/1,000 joint is .545, and continuation activity is noisier online, so the settled figure overstates the live one by construction.
**Expected outcome if true.** Live online content joint close to the settled replay value, with the index unchanged.
**Evidence for.**
- In settled replay, duty/1,000 reads .995 and correlated/500 .965 (reported-only replay; `docs/plant2/RESULTS-P2-R1.md:13-18`).
**Evidence against.**
- "It cannot replace .545 in an online result table" (`docs/plant2/RESULTS-P2-R1.md:39-41`). A burst is a forward-match signal after the write, so repeats and lures would write onto old cells. It cannot touch S1, and the skeptic expects it cannot reach S2 at M = 1,000 (`docs/plant2/EVAL-after-P2-E5.md:56-62, 132-133`).
**Tested by.** Untested
**Experiment needed.** B-011: a live R_3 contract on fresh seeds, not stacked with another unproven mechanism.
**Notes.** The owner's "R3 reported replay first" is done. A live R_3 write is credited as removing no supply, because it recovers the assigned key (`DECISIONS.md:778-782`; `docs/plant2/EVAL-after-P2-E5.md:144-145`).

**H-051** Settled-twin scores of the burst store are online retrieval
**Statement.** The burst-gated store's 0.93-0.97, against 0.05-0.10 for the current write, measures online retrieval.
**Origin.** `docs/plant2/EVAL-after-P2-E5.md:58`, 2026-10-11.
**Status.** `withdrawn`
**Confidence.** Low: those figures are settled twin-A readouts of online-written stores.
**Expected outcome if true.** Live online retrieval through the burst store reads about 0.93-0.97.
**Evidence for.**
- Cleaner writing under the online learning schedule is supported (reported-only; `review/plant2/P2-R1/findings-baseline-methodology.md:35-38`).
**Evidence against.**
- The figures are settled twin-A readouts. The online block joint at M = 500 is 0.475-0.575, and the live inherited duty/1,000 joint is .545 (reported-only; `review/plant2/P2-R1/findings-baseline-methodology.md:35-38`; `docs/plant2/RESULTS-P2-R1.md:39-41`).
**Tested by.** P2-R1 baseline audit
**Experiment needed.** Settled; see the erratum at `docs/plant2/EVAL-after-P2-E5.md:132-133`.
**Notes.** none

**H-052** The assigned-assembly store is an upper bound on content quality
**Statement.** The plateau-set (assigned-assembly) store is an upper bound on what any feedback writer can reach.
**Origin.** P2-E5 contract, Part A wording, and owner guidance calling it an "upper-bound diagnostic" (`DECISIONS.md:498-501`), 2026-10-11.
**Status.** `withdrawn`
**Confidence.** Low: sparser stores selected from activity beat it at M = 1,000.
**Expected outcome if true.** No writer beats the plateau-set store on the same raster.
**Evidence for.**
- The plateau-set store reads 0.985-1.0 on P2-E4's twin A at M = 1,000 (reported-only; `docs/plant2/P2-E4-online-memory.md:709-711`).
**Evidence against.**
- At the frozen point at M = 1,000, R_4 passes 51-63 cues and R_6 70-84 (constructive) or 68-84 (skeptic), against 28-35 for the plateau-set store (reported-only; `review/plant2/P2-E5/results-northstar_constructive.md:43-45`; `review/plant2/P2-E5/results-northstar_skeptic.md:26`). R_3 can exceed assigned A (`docs/plant2/RESULTS-P2-R1.md:25-30`).
**Tested by.** P2-E5 (reported), P2-R1
**Experiment needed.** Settled. The P2-R1 erratum calls the store a "diagnostic comparator, not a mathematical upper bound" (`docs/plant2/EVAL-after-P2-E5.md:137-139`).
**Notes.** The owner ruled that the assigned-assembly store is a diagnostic, not an acceptable solution: a correction mechanism must let the network find which of its own active cells represent the experience (`DECISIONS.md:498-501`). R_4 and R_6 lower D1 to about 0.84 and 0.40 (reported-only; `review/plant2/P2-E5/results-northstar_constructive.md:44`), and choosing a different k now would be parameter rescue (`docs/plant2/P2-E5-structured-items.md:946-947`).

## 6. Experimenter supply and self-generated keys

**H-053** Plateau keys generated by the network and gated by familiarity
**Statement.** Replace the experimenter's random plateau draw with plateaus elicited by the network, from the cell's own dendritic drive or from a mismatch between input and regeneration. Add allocation gated by familiarity or novelty, so that a familiar item does not re-allocate. This would remove the largest experimenter supply and give content-dependent keys that siblings partly share.
**Origin.** Proposals in `docs/plant2/EVAL-after-P2-E3.md:150-163`, 2026-10-10. P2-E4 constructive NS9 on mismatch-triggered plateaus (`docs/plant2/EVAL-after-P2-E4.md:174-190`), 2026-10-11. P2-E4 skeptic's next steps: plateau eligibility removes no supply until something other than the experimenter generates plateaus (`review/plant2/P2-E4/results-northstar_skeptic.md`), 2026-10-11.
**Status.** `proposed`
**Confidence.** Low: nothing has been tested, and content-dependent keys are exactly what Stage 1's specificity bar penalises.
**Expected outcome if true.** Keys produced without the experimenter's stream keep Stage 1 specificity on independent items and give siblings partly shared keys.
**Evidence for.**
- A familiarity signal exists: learned half cues regenerate at least 0.96 of lines, while novel cues regenerate a median of 0 (gated, P2-E3; `review/plant2/P2-E3/findings-northstar_constructive.md` F3).
**Evidence against.** none recorded
**Tested by.** Untested
**Experiment needed.** B-006, which is blocked pending an owner ruling.
**Notes.** The owner deferred familiarity-gated allocation until it is settled how a repeated item keeps distinct episode identities in different contexts (`DECISIONS.md:441-443, 767-768`). The P2-E1 review placed the choice of the network's own representations in Stage 3.

**H-054** A re-exposed item gets a second, unrelated memory
**Statement.** Because plateau allocation ignores familiarity, a re-exposed item gets a second, unrelated memory, which divides distinct capacity by the repeat count.
**Origin.** P2-E3 constructive F3 and skeptic NS3, from reading the code (`review/plant2/P2-E3/findings-northstar_constructive.md` F3; `review/plant2/P2-E3/findings-northstar_skeptic.md` NS3), 2026-10-10.
**Status.** `proposed`
**Confidence.** High that allocation ignores content, since the code shows it; the effect on capacity is unmeasured.
**Expected outcome if true.** Repeated items hold two disjoint assemblies, and distinct-item capacity falls in proportion to repeats.
**Evidence for.**
- Plateaus do not depend on content (code reading; `review/plant2/P2-E3/findings-northstar_constructive.md` F3).
**Evidence against.** none recorded
**Tested by.** Untested
**Experiment needed.** A reported re-exposure arm, proposed in `docs/plant2/EVAL-after-P2-E3.md:188-189` but never adopted. It is a prerequisite for B-006.
**Notes.** The owner deferred familiarity-gated allocation (`DECISIONS.md:441-443`).

**H-055** A feedback write that corrects errors from mismatch
**Statement.** A write driven by the mismatch between input and regenerated content would remove the experimenter-supplied value and write signal, bound the store, and make it a palimpsest.
**Origin.** `docs/plant2/EVAL-after-P2-E3.md:150-163` ("proposals, not results"), 2026-10-10. The owner approved the error-correcting write as a research direction (`DECISIONS.md:430-440, 455-456`), 2026-10-10.
**Status.** `proposed`
**Confidence.** Low: it is reasoned from P2-E3 alone, and the contaminated feedback store makes the error signal noisy.
**Expected outcome if true.** The feedback supplies useful error information, corrections preserve unrelated memories, and the store stays bounded under continued learning.
**Evidence for.**
- Reasoned from the P2-E3 findings only (`docs/plant2/EVAL-after-P2-E3.md:150-163`).
**Evidence against.**
- P2-E6 chose presynaptic load first because "P2-E5's inherited feedback is already badly contaminated, so its error signal is not a reliable starting teacher" (`docs/plant2/P2-E6-load-gated-encoding.md:15-19`).
**Tested by.** Untested
**Experiment needed.** Its own one-mechanism contract, testing whether the feedback supplies useful error information and whether corrections preserve unrelated memories (`DECISIONS.md:435-440`). The forward-eligibility form is H-060 (B-002).
**Notes.** Write-time regeneration replay was rejected in the P2-E5 contract and assigned to this mechanism's own contract (`DECISIONS.md:538-540`).

## 7. Capacity, retention and forgetting

**H-056** Specificity sets the capacity edge, and content fails at the same edge
**Statement.** With parameters fixed, C2 and C3 fail first as M grows, because cells accumulate strong synapses (hubs). The edge is at about 0.25-0.375 items per memory cell, and content completion fails at the same edge. P2-E2 predicted C2/C3 of 0.5-0.85 at M = 1,500 and at most 0.4 at 2,000; P2-E3 predicted that M = 1,500 fails D1/2.
**Origin.** P2-E1 contract, reported and not gated (`docs/plant2/P2-E1-btsp.md:160-163`). P2-E2 predictions (`docs/plant2/P2-E2-accommodation.md:156-157`). P2-E3 prediction table (`docs/plant2/P2-E3-content-completion.md:231`). All 2026-10-10.
**Status.** `mixed`
**Confidence.** Medium: the edge appears in every reported capacity arm, but the C3 predictions were exceeded and all the evidence is reported-only.
**Expected outcome if true.** Specificity collapses between about 0.25 and 0.375 items per cell, and content collapses at the same load.
**Evidence for.**
- P2-E1, seed 1: C2/C3 are 1.000 at M = 250 and 500, 0.925/0.955 at 1,000, and 0.000 at 2,000 and 4,000. Hub counts are 0, 0, 10, 756 and 3,797 (reported-only, n = 1; `bench/results/plant2.jsonl:7-11`).
- P2-E2: C2 is 0.715-0.775 at M = 1,500 and 0.30-0.37 at 2,000, placing the edge between 0.25 and 0.375 items per cell (reported-only; `docs/plant2/P2-E2-accommodation.md:292-301, 422`).
- P2-E3: at M = 1,500 joint is 0.185-0.290 with memory C2 0.68-0.73; at M = 2,000 joint is at most 0.015 (reported-only; `docs/plant2/P2-E3-content-completion.md:396-404`).
**Evidence against.**
- P2-E2's C3 is 0.74-0.865 at M = 1,500 (0.865 is above 0.85) and 0.43-0.46 at 2,000 (above the predicted 0.4) (reported-only; `docs/plant2/P2-E2-accommodation.md:313-314, 422-423`).
- P2-E1, not predicted: C1 is worse at low load (0.610 at 250, 0.635 at 500) (reported-only; `docs/plant2/P2-E1-btsp.md:210-211, 226-227`).
- P2-E3: content collapses more sharply than memory specificity, and D1 stays at 0.97-1.0 because the store saturates (reported-only; `docs/plant2/P2-E3-content-completion.md:504-513`).
**Tested by.** P2-E1, P2-E2, P2-E3 (reported arms)
**Experiment needed.** The capacity-scaling experiment (H-059, B-010).
**Notes.** P2-R1's scope statement: two fixed-size load checkpoints are not capacity growth, and successful store swaps cannot close Stage 1 (`docs/plant2/P2-R1-takeover-replay.md:48-49`; `docs/plant2/RESULTS-P2-R1.md:42-46`).

**H-057** Past capacity, the add-only feedback store blacks out instead of forgetting
**Statement.** Past capacity, the clipped add-only feedback store saturates and blacks out (joint below 0.3 by M = 1,500 and about 0 at 2,000) instead of forgetting old items gracefully.
**Origin.** P2-E3 north-star skeptic NS4 (`review/plant2/P2-E3/findings-northstar_skeptic.md` NS4), 2026-10-10. P2-E4 reported-arms prediction (`docs/plant2/P2-E4-online-memory.md:465`), 2026-10-10.
**Status.** `mixed`
**Confidence.** Medium: saturation is measured under the settled protocol, but online the predicted blackout loads were wrong.
**Expected outcome if true.** Store density and |R| climb with load until half cues light most lines and the joint falls to about 0.
**Evidence for.**
- Feedback density is 0.133, 0.23 and 0.36 at M = 1,000, 1,500 and 2,000, and |R| goes 23, 30, 41. At M = 2,000 a half cue lights a median of 2,983-3,545 of 4,000 lines, and novel cues up to 4,000 (reported-only; `docs/plant2/P2-E3-content-completion.md:504-513`).
- Online joint is 0.00 at M = 3,000 (reported-only; `docs/plant2/P2-E4-online-memory.md:719-723`; `review/plant2/P2-E4/results-northstar_skeptic.md` NS-7).
**Evidence against.**
- Online joint is 0.72-0.79 at M = 1,500 (predicted below 0.3) and 0.18-0.30 at 2,000 (predicted about 0) (reported-only; `docs/plant2/P2-E4-online-memory.md:719-723, 746`).
**Tested by.** P2-E3, P2-E4 (reported arms)
**Experiment needed.** A predeclared forgetting curve past capacity, with a bounded-store mechanism as comparator (H-055). B-012 is a related backlog idea.
**Notes.** The owner ruled that past-capacity learning (M = 3,000) is a reported stress test, not a gate (`DECISIONS.md:406-407`).

**H-058** Old items' written synapses do not decay within capacity
**Statement.** "An old item's written synapses are flipped by later plateaus on the same cell only through overlaps ... so they do not decay on average." The oldest items therefore pass the same completion and specificity bars as the rest (C4) at loads within capacity.
**Origin.** P2-E1 contract predictions (`docs/plant2/P2-E1-btsp.md:146-148`), 2026-10-10. C4 was carried into P2-E2's gate (`docs/plant2/P2-E2-accommodation.md`), 2026-10-10.
**Status.** `mixed`
**Confidence.** Medium: C4 passed on every gated P2-E2 seed under the settled protocol, but P2-E1's predeclared C4 failed and old-item recall fails online.
**Expected outcome if true.** Oldest-cohort recall within 0.03 of the rest, and C4 passing wherever C1-C3 pass.
**Evidence for.**
- P2-E1: old-item median recall is 0.907-0.946 against 0.915-0.929 for the rest, and the C4 spurious half is 0.920-0.950 (gated; `docs/plant2/P2-E1-btsp.md:146-148, 183-187, 209`).
- P2-E2: C4 passes at M = 250, 500 and 1,000 on gated seeds 6-10 (gated; `docs/plant2/P2-E2-accommodation.md:223-225`).
- Online index failures recover after a settle on unchanged synapses (reported-only; H-026). P2-E6's F10/1,000 age strata (.8667, .9070, .8944) show no monotonic gradient (exploratory; `review/plant2/P2-E6/findings-results.md:49`).
**Evidence against.**
- P2-E1's C4 recall half failed (0.820-0.890), because the oldest items miss completion at the same rate as the rest (gated; `docs/plant2/P2-E1-btsp.md:184-188`).
- P2-E4's O3 old-item memory fails online (0.61-0.75 at M = 1,000) (gated; `docs/plant2/P2-E4-online-memory.md:646-650`; H-019). The retention-against-age arm was predicted to fall but was not reported (`docs/plant2/P2-E4-online-memory.md:454-468`).
**Tested by.** P2-E1, P2-E2, P2-E4
**Experiment needed.** Settled for the settled protocol within capacity; see P2-E2. Graceful forgetting past capacity is H-057.
**Notes.** Status corrected from `supported` to `mixed` on 2026-10-22: the predeclared C4 criterion failed in P2-E1 (gated) and passed in P2-E2 (gated), which is the README's definition of `mixed`; the source ledger records P2-E1's form as tested_mixed.

**H-059** Capacity grows with cell count only when input and memory scale together
**Statement.** "Capacity grows with cell count" should be measured by scaling the input and memory populations together, with memory-only scaling as the control. A surrogate predicts that scaling n alone halves capacity, n with f_q halved gives ×1.7, and m and n together give ×2.2.
**Origin.** P2-E2 direction reviewer's surrogate (F5); owner question 2 and ruling 2 (`DECISIONS.md:293-301, 319-325`), 2026-10-10.
**Status.** `proposed`
**Confidence.** Low: only an exploratory surrogate supports it.
**Expected outcome if true.** At fixed items per cell, C2 holds when m and n scale together and falls when only memory scales.
**Evidence for.**
- Surrogate predictions only: "Exploratory surrogate predictions are not results." (exploratory; `review/plant2/P2-E2/findings-direction.md` F5)
**Evidence against.** none recorded
**Tested by.** Untested
**Experiment needed.** B-010, the predeclared capacity-scaling experiment, parked until Stage 1's structured-input clause has a mechanism.
**Notes.** none

## 8. Owner-raised and reviewer-raised directions not yet tested

The owner's north star (human-level learning as a horizon, never a claim; `DECISIONS.md:216-219`), the owner's preference for lasting, inspectable change over anatomical naming (`DECISIONS.md:241-242`), and the note on how the 2026-10-10 rulings were drafted (`DECISIONS.md:390-392`) are not falsifiable claims, so they have no entries.

**H-060** Error-gated forward eligibility reduces forward-index cross-talk
**Statement.** During encoding, an input line is eligible for BTSP only if the reconstruction layer did not regenerate it from the memory response to the item. Prototype lines that are already predicted stop being written after the first family members. Against a random-drop control, this reduces forward-index cross-talk on correlated items, and a predeclared contrast decides between error-gated and presynaptic-load-gated eligibility.
**Origin.** P2-E4 constructive NS8 (`docs/plant2/EVAL-after-P2-E4.md:174-190`), 2026-10-11. P2-E5 skeptic NS2 and NS8 (`review/plant2/P2-E5/results-northstar_skeptic.md:20-21, 55-65`), 2026-10-11. Owner ruling 3 (`DECISIONS.md:786-788`), 2026-10-12.
**Status.** `mixed` (P2-E7 development seed 121, 2026-10-22: the frozen feasibility screen failed on the absolute bars, informative; every comparative margin held; development seed only, so never `supported`)
**Confidence.** Low (one development seed, exploratory): the comparative evidence is consistent with an informative, co-occurrence-sensitive signal, and the rule as stated did not reach the bar; its onset is late by construction (a family's first four to thirteen members are written in full before the prediction engages).
**Expected outcome if true.** C2 and oldest specificity reach at least 0.90 at F10/M = 1,000 with recall preserved, beating a random-drop control. P2-E7's frozen predictions: F10/1,000 candidate C2 in [0.82, 0.97], C1 ≥ 0.91, joint index in [0.75, 0.93], C4_spurious in [0.70, 0.97]; random_drop C2 ≤ 0.55; candidate C2 ≥ history_drop + 0.10.
**Evidence for.**
- S1 fails whatever the feedback write is: at M = 500, C2 fails on seed 23 only (174 of 200) and C4 spurious fails on seeds 23 (86 of 100) and 25 (88 of 100) (gated; `review/plant2/P2-E5/results-northstar_skeptic.md:20`).
- P2-E5 exploration at M = 1,000 gives C2 0.465-0.495 with about 19 spurious cells per cue, 98 % of them siblings' plateau cells (exploratory, seeds 44-45; `docs/plant2/P2-E5-structured-items.md:61, 80-83`; `docs/plant2/EVAL-after-P2-E4.md:158-160`).
**Evidence against.**
- P2-E6 chose load first. The inherited feedback's error signal is not a reliable teacher, and adding a cleaned feedback path would "stack two unproven mechanisms" (`docs/plant2/P2-E6-load-gated-encoding.md:15-19`).
- P2-R1's results "do not discriminate error-gated from load-gated forward eligibility" (`review/plant2/P2-R1/findings-results-methodology.md:43`).
- Offline pre-screen on the baseline trajectory (seeds 105/106, proxy: continuation responders minus plateau cells, inhibition-aware count rule): the predicted set covers the prototype lines early (prototype predicted fraction 0.63-0.68 by block 3, 0.93-0.97 by block 5) and the non-prototype predicted fraction rises to 0.27 in block 8 and 0.53 in block 10, with veto precision falling to 0.56; over episodes 501-1,000 the non-prototype fraction is 0.29 against P2-E7's 0.25 kill threshold (offline, proxy; `docs/plant2/OFFLINE-SCREENS-20261022.md`, screen A). A warning, not a decision: the candidate trajectory writes a less contaminated store than the baseline's.
- P2-E7 development seed 121: F10/1,000 candidate C2 .745, C1 .895, C4_spurious .720, joint .645 against bars of .90/.90/.90/.85 (exploratory, development seed; `docs/plant2/RESULTS-P2-E7.md`). The veto engaged late (mean |V| 13.0 over episodes 1-500, 40.4 over 501-1,000; first engagement per family at episodes 44-138; p capped on 144 episodes); inherited content .005. The label oracle (true prototype lines vetoed from episode 1; it differs from the candidate in onset, coverage and precision at once) reached C2 .970 with C1 .920; which of these closes the gap is not separated by this design (P2-E7 erratum 4).
**Evidence for (added 2026-10-22, P2-E7 seed 121, exploratory).**
- Candidate C2 .745 against the count-matched random drop .480 (+0.265) and the history-weighted drop .635 (+0.110); joint .645 against .410 and .595; the co-occurrence-sensitive prediction adds beyond E6's hot-line marginal (kill e did not fire) (`docs/plant2/RESULTS-P2-E7.md`).
- Corrections preserved unrelated memories: zero vetoes on independent inputs (candidate identical to baseline); in the mixed store the independent subset moved by at most two index cues (joint +2; C1, C2 +1) and gained 14 content cues (34 → 48 of 95).
- The conserved budget is load-bearing on this seed: without it C2 .840 but C1 .680 and own50 15.8 (reported arm).
- The responder-written teacher gave a higher C2 than the clean plateau-set teacher (.745 against .645) with a higher mean |V| (40.4 against 27.9) at lower precision (.817 against .975); first engagement was the same in nine of ten families; no causal attribution follows (P2-E7 erratum 5).
**Tested by.** P2-E7 (development seed 121, 2026-10-22); P2-E6 tested the load-gated alternative (H-040).
**Experiment needed.** P2-E7 as frozen: development seed 121 under the structural kill and the E6-derived screen, with the count-matched random drop, the history-weighted drop, the gate-off integrity arm and the mixed-stream condition; held-out 122 and gated 131-135 only on committed passes.
**Notes.** The constructive reviewer asked for the burst-gated write first, as a clean comparator (`docs/plant2/EVAL-after-P2-E4.md:174-190`).

**H-061** Activity-driven pattern separation before storage
**Statement.** If P2-R2 shows replicated material structure sensitivity without the declared recall loss, then activity-driven pattern separation before storage (observed coactivation and learned competition, with no family labels or supplied prototypes) is the strongest next direction.
**Origin.** Independent capability review (`review/plant2/takeover-capability-review.md:15`), 2026-10-12.
**Status.** `proposed`
**Confidence.** Low: the review's condition is now met, but the fixed-random form failed its offline screen and the learned form is untested.
**Expected outcome if true.** The stored code's sibling overlap falls below the input's, and high-load C2 rises without recall loss.
**Evidence for.**
- The condition is met. H-044 replicated on two fresh seeds, and H-045's recall cost did not recur (reported-only; `docs/plant2/RESULTS-P2-R2b.md:72-82`).
**Evidence against.**
- B-004's offline screen (2026-10-22) gave own-to-sibling drive ratios of 5.9 for the raw lines; 7.7 for an expansion of n = 16,000 with fan-in 20 and k = 1 %; 9.0 for n = 32,000 with fan-in 50 and k = 0.5 %; and 3.2 for fan-in 10 with k = 2 %. A fixed random expansion buys at most 1.3-1.5× and doubles the diffuse drive from non-siblings (descriptive, a computation on item sets, not a simulation; `docs/research/BACKLOG.md:110-120`).
**Tested by.** Untested (offline screen only)
**Experiment needed.** B-004 in its learned-competitive form, as its own contract.
**Notes.** P2-R2b erratum 5: meeting the condition informs, and does not by itself authorise, the next mechanism contract (`docs/plant2/RESULTS-P2-R2b.md:112-114`).

**H-062** Fixed activity-proportional inhibition inside the memory layer
**Statement.** A fixed, activity-proportional inhibition on the memory layer acts as a soft k-winners-take-all: the most strongly driven assembly suppresses weakly driven siblings. This suppresses spurious sibling responders at retrieval without silencing everything or forcing an answer, and may let accommodation sit lower online.
**Origin.** Owner-approved directions: a declared stabilising element for Stage 2 (`DECISIONS.md:420-429`), 2026-10-10, and a Stage 1 recurrent-memory stabiliser (`DECISIONS.md:783-785`), 2026-10-12.
**Status.** `proposed`
**Confidence.** Low: global inhibition failed C3 in P2-E1's exploration, and own cells may lose the race to earlier sibling responses.
**Expected outcome if true.** C2 rises and C3 holds against no-inhibition, inhibition-only and shuffled controls, with no global silencing.
**Evidence for.**
- P2-E3's fixed inhibition on the feedback readout made regeneration specific at M = 1,000 (reported-only; H-012).
**Evidence against.**
- Global feedback inhibition or k-WTA at J_I = 0.3 mV gave C3 0.04 (exploratory; H-008). The owner rejected feedback k-WTA for P2-E2 (`DECISIONS.md:269-273`).
**Tested by.** Untested
**Experiment needed.** B-003 with no-inhibition, inhibition-only and shuffled or degree-matched controls, frozen parameters, and checks against silencing or forcing an answer.
**Notes.** It is never a learning mechanism and gets no capability credit on its own. P2-E3's coefficient is not carried over (`DECISIONS.md:428-429`).

**H-063** A recurrent completion basin gated by eligibility
**Statement.** Access fails because every cue sits near the bar with no completion basin. One-shot binary memory-to-memory synapses between cells that both burst, stabilised by fixed activity-proportional inhibition, would widen the basin.
**Origin.** P2-E4 constructive NS4 and NS5 (`review/plant2/P2-E4/results-northstar_constructive.md`; `docs/plant2/EVAL-after-P2-E4.md:162-173`), 2026-10-11.
**Status.** `proposed`
**Confidence.** Low: recurrence ran away above J_rec 1.0 in P2-E1's review, and it risks completing sibling assemblies on correlated items.
**Expected outcome if true.** C1 for degraded cues (30 % cues, noisy half cues) rises well above current values without spontaneous ignition.
**Evidence for.**
- With 10 of 50 cue lines swapped, C1 is 0.075-0.175, and 30 % cues give 0.00 (reported-only; `docs/plant2/P2-E4-online-memory.md:728-729`; H-010). J_rec 1.0 completed assemblies at M = 250 without runaway (exploratory; `review/plant2/P2-E1/findings-direction.md:44`).
**Evidence against.**
- J_rec 1.5 left 3,969 cells active after 2 s at M = 1,000 with accommodation (exploratory; `review/plant2/P2-E1/findings-direction.md:44`).
**Tested by.** Untested
**Experiment needed.** Its own contract with a stabiliser and a bar on spontaneous ignition. The stabiliser itself is authorised: the owner's 2026-10-12 ruling 2 allows fixed activity-proportional memory inhibition as a Stage 1 recurrent-memory stabiliser if justified, with no-inhibition, inhibition-only and shuffled or degree-matched controls (`DECISIONS.md:783-785`). The recurrent links were rejected for P2-E2 (`DECISIONS.md:269-273`), so the contract needs its own justification for them.
**Notes.** The first draft of this entry said the stabiliser needed an owner ruling because ruling 3 allows it for Stage 2 only. That repeated `docs/plant2/EVAL-after-P2-E4.md:168-169` (2026-10-11), which the owner's ruling 2 of 2026-10-12 superseded; corrected on 2026-10-22.

**H-064** Best-of-two plateau allocation balanced by load
**Statement.** For each plateau slot (Poisson(20) per episode), draw 2 candidate cells and plateau the one with fewer stored strong synapses. At J = 1.26 mV this is predicted to give C1 of about 0.95-0.99, C2 and C3 at least 0.98, and no hubs at M = 1,000.
**Origin.** P2-E1 code reviewer (`review/plant2/P2-E1/findings-code.md:61-66`), 2026-10-10.
**Status.** `proposed`
**Confidence.** Low: only a reviewer surrogate supports it, and it targets hub variance rather than slowness at low load.
**Expected outcome if true.** No hubs, and one J window that passes at both M = 250 and 1,000.
**Evidence for.**
- The surrogate cuts the sd of k to 0.95, removes hubs, and opens a J window of 1.2-1.4 at M = 1,000 and 1.3-1.4 at 250 (exploratory surrogate, ±0.05; `review/plant2/P2-E1/findings-code.md:61-66`).
**Evidence against.**
- Deferred because it "targets hub variance but not low-load slowness, and reads per-cell store load as an instructive selector" (`review/ledger.jsonl` row 19; `DECISIONS.md:257-260`).
**Tested by.** Untested
**Experiment needed.** None planned; it would need its own contract and an owner ruling.
**Notes.** none

**H-065** The memory operating point is tuned to one item size
**Statement.** J = 1.525 is tuned to items of a = 100 lines. A half cue of a 50-line item gives about 12 strong cue synapses, so C1 would fail, and 200-line items double the writes per plateau.
**Origin.** P2-E3 constructive reviewer F6 (`review/plant2/P2-E3/findings-northstar_constructive.md` F6), 2026-10-10.
**Status.** `proposed`
**Confidence.** Medium: the predictor's firing probability falls steeply below 25 synapses.
**Expected outcome if true.** C1 fails at a = 50, and specificity falls at a = 200, at the frozen J.
**Evidence for.**
- The probability that a written cell fires within 50 ms is 0.17 at 12 strong cue synapses, 0.47 at 15 and 0.997 at 25 (exploratory predictor; `review/plant2/P2-E3/findings-northstar_constructive.md` F6).
**Evidence against.** none recorded; there is no plant2 run at other item sizes.
**Tested by.** Untested
**Experiment needed.** Reported arms at a = 50 and 200 in any future contract that changes the item distribution.
**Notes.** none

**H-066** An accommodation time constant of 100 s or more separates load change from habituation
**Statement.** An accommodation time constant of at least 100 s would separate the timescale of online load change from that of habituation to a held cue.
**Origin.** P2-E3 constructive reviewer F10, labelled speculative (`review/plant2/P2-E3/findings-northstar_constructive.md` F10), 2026-10-10.
**Status.** `proposed`
**Confidence.** Low: it is speculative and in tension with the owner's advice against fixes that only adjust the threshold.
**Expected outcome if true.** At τ ≥ 100 s, held-cue habituation is negligible while load drift is still tracked.
**Evidence for.**
- At τ = 10 s a held cue raised v̄ by 5.2 mV over 30 s. Learning one item per 2.25 s adds about 4 % of M = 1,000 per 100 s (exploratory; `review/plant2/P2-E3/findings-northstar_constructive.md` F10).
**Evidence against.** none recorded
**Tested by.** Untested
**Experiment needed.** A new contract and an owner ruling would be needed.
**Notes.** The owner advises against a threshold adjustment alone (H-067).

**H-067** A threshold adjustment alone would trade one failure for another
**Statement.** A threshold adjustment alone, for example changing the accommodation time constant, might trade one failure for another, so it is not to be tried as the fix for the encoding/retrieval trade-off.
**Origin.** Owner's reading (`DECISIONS.md:580-582`), 2026-10-11; P2-E4 Result (`docs/plant2/P2-E4-online-memory.md:813-814`).
**Status.** `proposed`
**Confidence.** Medium: |R| follows offset on one curve across three regimes, and the duty arm regained access only with a collapsed store.
**Expected outcome if true.** Any offset change that restores online access also raises |R| and contamination.
**Evidence for.**
- |R| against continuation offset lies on one curve across the P2-E3 protocol, the main line and the duty arm. The duty arm restores online access but its store collapses (reported-only; `docs/plant2/EVAL-after-P2-E4.md:83-94`; H-029).
**Evidence against.**
- It has never been tested directly, and the duty arm confounds schedule with offset (`docs/plant2/P2-E4-online-memory.md:813-814`).
**Tested by.** Untested
**Experiment needed.** None planned; the owner's advice stands against running it as a fix.
**Notes.** none

**H-068** Slowed retrieval and habituation share a per-item drive margin
**Statement.** Slowed online index retrieval and habituation both reflect a per-item drive margin, and habituation plausibly shares accommodation dynamics with access failure.
**Origin.** P2-E4 skeptic NS-6 and the diagnosis plan (`docs/plant2/P2-E4-diagnosis-plan.md:255-258`), 2026-10-11. P2-R1 baseline reviewer, item 8 (`review/plant2/P2-R1/findings-baseline-methodology.md:75`), 2026-10-12.
**Status.** `proposed`
**Confidence.** Low: the one exploratory probe found the cue-synapse margin predicts failure only weakly.
**Expected outcome if true.** A predeclared per-item margin predicts both slow access and habituation well.
**Evidence for.**
- Being labelled habituated tracks the control copy's late recall: AUC 0.62-1.0 on 9 of 10 seed-loads (0.40 on seed 19 at M = 1,000, with 9 eligible items) (post hoc; `review/plant2/P2-E4/results-northstar_constructive.md:116`). Composite habituation labels depend on content as well as index (1,009 of 50,000) (reported-only; H-025).
**Evidence against.**
- A constructive probe on seed 90 found that the cue-synapse margin predicts failure only weakly (AUC 0.59-0.67) (exploratory; `review/plant2/P2-E4/results-northstar_constructive.md:79`). The margin itself "was not measured" (`docs/plant2/P2-E4-online-memory.md:815-817`). P2-R1 did not newly measure habituation or recovery (`docs/plant2/RESULTS-P2-R1.md:42-43`).
**Tested by.** Untested; the margin "was not measured".
**Experiment needed.** Its own predeclared per-item margin measure, with habituation rescored on index alone.
**Notes.** none

**H-069** Chaining through content alone is first-order Markov
**Statement.** Chaining through the reconstruction layer is first-order Markov. A shared item with b successors resolves at most 1/b of the time (0.5 at b = 2, against the 0.80 Stage 2 bar), so transitions between memory indices (memory-to-memory links) are needed.
**Origin.** P2-E3 constructive reviewer F2 (`review/plant2/P2-E3/findings-northstar_constructive.md` F2; `docs/plant2/EVAL-after-P2-E3.md:72-83`), 2026-10-10.
**Status.** `proposed`
**Confidence.** High as arithmetic; it is untested in a sequence task.
**Expected outcome if true.** Content-only chaining resolves at most 1/b of branch points.
**Evidence for.**
- Arithmetic, accepted in `review/ledger.jsonl` row 106 (`docs/plant2/EVAL-after-P2-E3.md:72-83`).
**Evidence against.**
- none recorded. Recurrence within an assembly ran to 2,889-3,969 active cells in P2-E1's review, which is a risk for the memory-to-memory alternative (exploratory; H-008).
**Tested by.** Untested
**Experiment needed.** Stage 2 sequence work, which is not authorised (`DECISIONS.md:857, 872-878`).
**Notes.** none

**H-070** Stage 3's prototype criterion can be passed by blending at retrieval
**Statement.** Averaging or superposition at retrieval alone produces a prototype effect without learned abstraction, and so can pass a prototype criterion.
**Origin.** P2-E3 constructive reviewer F7, by surrogate (`review/plant2/P2-E3/findings-northstar_constructive.md` F7; `docs/plant2/EVAL-after-P2-E3.md:97-114`), 2026-10-10.
**Status.** `proposed`
**Confidence.** Medium: a surrogate and an exploration with the plateau-set store both regenerate the unseen prototype.
**Expected outcome if true.** A half cue of an unseen prototype regenerates it from stored exemplars with no learning beyond storage.
**Evidence for.**
- An unseen prototype's half cue regenerates 1.00 of lines at d ≤ 0.3 and n ≥ 8. An exploration with the plateau-set store regenerates the whole prototype with 12-18 intrusions (exploratory surrogate; `review/plant2/P2-E3/findings-northstar_constructive.md` F7).
**Evidence against.**
- These are surrogate results, not a plant2 run (`review/plant2/P2-E3/findings-northstar_constructive.md` F7).
**Tested by.** Untested in plant2
**Experiment needed.** Settled as a question of gate design: the owner adopted a stronger Stage 3 gate in which averaging or superposition does not count (`DECISIONS.md:444-451`).
**Notes.** none

**H-071** BTSP's real window would saturate a Stage 2 store
**Statement.** Stage 2 with BTSP's real plasticity window (-3 to +2 s) on 200 ms items would saturate the store: 1 - 0.975^25 = 47 % of lines would be eligible per plateau, giving about 940 strong synapses per plateau against about 50.
**Origin.** P2-E2 direction reviewer F6 (`review/plant2/P2-E2/findings-direction.md` F6), 2026-10-10.
**Status.** `proposed`
**Confidence.** Medium: the arithmetic is simple.
**Expected outcome if true.** Writes per plateau rise by more than an order of magnitude, and specificity collapses at low load.
**Evidence for.**
- Reviewer arithmetic (`review/plant2/P2-E2/findings-direction.md` F6).
**Evidence against.** none recorded
**Tested by.** Untested
**Experiment needed.** A Stage 2 contract would have to address it; Stage 2 is not authorised.
**Notes.** none

## 9. Prior hypotheses from the recovered plant

The recovered plant is frozen research material (AGENTS.md invariant 4). These diagnoses were measured on it and motivated plant2's design. None can be retested there, so each is `mixed` (descriptive evidence, never a predeclared plant2 test) or `unresolved`.

**H-072** Pair STDP depresses the pathway in use
**Statement.** Pair STDP's uncorrelated fixed point (a_plus/(a_plus + a_minus) = 0.45 w_max) sits below the homeostatic rest weight, so co-activity depresses the pathway in use: "firing together weakens the synapse".
**Origin.** Recovered-plant diagnosis (`docs/plant2/STAGES.md:21-22`; `docs/plant2/AUDIT-2026-10-10.md:35-36`), consolidated in the audit of 2026-10-10.
**Status.** `mixed`
**Confidence.** High on the direction of the effect, though the sources disagree on the rest-weight range.
**Expected outcome if true.** One presentation weakens the driven pathway, and trained pathways sit below never-trained twins.
**Evidence for.**
- One presentation weakens the driven pathway by 6-14 % of w_max (P to W: -0.057, -0.102, -0.113; A-sense to P: -0.076, -0.136, -0.109), with background drift of -0.0014 to -0.0031 per second (descriptive, recovered plant, SPEC 8.20 R0; `SPEC.md:3558, 3562, 3567-3569`).
- The ctx E to W mean weight is 1.7 in the off arm against 1.9 in the never-presented twin (C3, seed 1, 127,000) (descriptive, SPEC 8.19; `SPEC.md:3470-3471`).
- The required causal-to-anticausal excess is 3.6 at a rest weight of 0.75 w_max, against 1.8 delivered by natural onsets and 3.0 by an imposed volley (SPEC 8.12). It is 2.9 at 0.71 w_max (SPEC 8.2) (descriptive; `SPEC.md:1405-1407, 2594-2598`).
**Evidence against.**
- The sources disagree on the rest weight: AUDIT 0.6-0.9, STAGES 0.6-0.75, SPEC 8.12 0.75, SPEC 8.19 0.6-0.7, and SPEC 8.23 0.65-0.85 (Why paragraph), 0.58-0.62 (measured) and 0.6 (descriptive; `docs/plant2/AUDIT-2026-10-10.md:35-36`; `docs/plant2/STAGES.md:21-22`; `SPEC.md:3466-3471, 3931, 4001-4002, 4016`).
**Tested by.** Recovered plant (SPEC 8.2-8.20)
**Experiment needed.** None possible on the frozen plant. Plant2 drops the rule (H-082).
**Notes.** none

**H-073** The seconds-scale rate homeostat erases one-shot writes
**Statement.** The rate homeostat runs on a seconds timescale and treats a stimulus as a rate error. Synaptic scaling and rate-driven structural elimination each erase a write within 1-3 sweeps, and they back each other up: removing one hands the erasure to the other.
**Origin.** Recovered-plant diagnosis (`docs/plant2/STAGES.md:23-25`; `docs/plant2/AUDIT-2026-10-10.md:37-38`), 2026-10-10.
**Status.** `mixed`
**Confidence.** High: repeated measurements from SPEC 8.3 to 8.49 agree.
**Expected outcome if true.** Written weights and wiring fall within a few sweeps whenever either process runs.
**Evidence for.**
- Within three sweeps of a 2 s presentation, scaling takes the answering cells' used inputs down about 18 % and pruning removes up to a quarter of excitatory wiring. Weights recover in about 15 s; wiring does not (descriptive, SPEC 8.18/8.19; `SPEC.md:3377-3379`).
- Mean weights fall 16-17 % during a 2 s encode (0.481 to 0.403) with elimination off, while assembly cells run at 5.3 Hz against a 1 Hz target (descriptive, SPEC 8.3; `SPEC.md:1490, 1502, 1509-1525`).
- At the first unprotected sweep, 44 of 987 donor-to-W and 15 of 47 W-to-W synapses are killed (SPEC 8.13). With elimination protected, survivors' mean goes 0.876, 0.790, 0.624, 0.771 against a bar of 0.82 (SPEC 8.14) (descriptive; `SPEC.md:2739-2758, 2833-2858`).
- Scaling is the largest single cause of the 10 s loss (72 %, 87 % and 51 % on seeds 1-3; 78 %, 67 % and 79 % on seeds 4-6), and the processes compound (ALL-OFF 111 % against 72 + 17 + 10) (descriptive, SPEC 8.49; `SPEC.md:6424-6492`).
**Evidence against.** none recorded
**Tested by.** Recovered plant
**Experiment needed.** None possible on the frozen plant. Plant2 keeps every homeostat off written synapses (H-082).
**Notes.** P2-E2's accommodation acts on thresholds, not synapses, and the owner ruled it distinct from K0.14 (H-004). B-005 and B-007 carry this risk.

**H-074** A dense, overlapping cortical code prevents selective writes
**Statement.** The cortical stimulus code is dense and overlapping, so local pre/post rules cannot separate inputs better than their rate ratio (about 2), and no rule can write selectively.
**Origin.** Recovered-plant diagnosis (`docs/plant2/STAGES.md:26-27`; `docs/plant2/AUDIT-2026-10-10.md:39`), 2026-10-10.
**Status.** `mixed`
**Confidence.** High: measured selectivity sits at 1.3-2.3 against a bar of 2.
**Expected outcome if true.** Selectivity of every local rule stays near the input rate ratio.
**Evidence for.**
- During stimulus A, other cortical E cells fire at 6.0-6.5 Hz against 3.8 at rest. A 40-cell sensory patch reaches 1,113 of the 1,600 cortical E cells (descriptive, SPEC 8.22; `SPEC.md:3905-3915`).
- Cortical E cells spiking within 50 ticks: 18-19 % with no stimulus, 24-25 % for a half cue, 33-34 % for full A and 31-38 % for B; 55-64 % of A's spikers also spike under B (descriptive, SPEC 8.23; `SPEC.md:3995-3998`).
- P-to-W against other ctx E-to-W is 2.3, 1.6 and 1.3 (bar 2), and R1 specificity is 0.023-0.073 (bar 0.10) (descriptive, SPEC 8.20 and 8.22; `SPEC.md:3575-3576, 3881`).
**Evidence against.** none recorded
**Tested by.** Recovered plant
**Experiment needed.** None possible. Plant2 uses sparse inputs (H-082), and on correlated items the problem returns as forward-index cross-talk (H-035).
**Notes.** none

**H-075** The wiring caps recall even with oracle weights
**Statement.** The recovered plant's wiring caps recall even with oracle weights: no arm completes a half cue in 50 ticks on that wiring, and no what-if plant tried lifts the 50-tick ceiling.
**Origin.** Recovered-plant diagnosis (`docs/plant2/STAGES.md:28-29`; `docs/plant2/AUDIT-2026-10-10.md:40`), 2026-10-10.
**Status.** `mixed`
**Confidence.** High for the configurations tried, which were few.
**Expected outcome if true.** With every strengthenable synapse at its bound, a half cue still recruits fewer than 13 of 16 cells within 50 ticks.
**Evidence for.**
- With every strengthenable synapse at its bound, a half cue recruits 8-11 of 16 within 50 ticks, not 13, and the same weights make cells answer B and fire with no stimulus (5.0, 2.0, 2.4). A W cell receives 2.1-2.5 synapses from other W cells (descriptive, SPEC 8.23; `SPEC.md:3973-4024`).
- W1 (recurrent in-degree raised from 20 to 80): no arm completes within 50 ticks (AaR 7.0, 5.6, 10.8), while 13-16 of 16 complete at 200 ticks. W2 and W3 are VOID (descriptive, SPEC 8.24; `SPEC.md:4038, 4074-4123`).
**Evidence against.** none recorded; only a few what-if plants were tried.
**Tested by.** Recovered plant
**Experiment needed.** None possible. Plant2 uses one input-to-memory synapse per pair, with about 25 written synapses active under a half cue (H-082).
**Notes.** none

**H-076** Readouts sit close to a never-trained twin
**Statement.** Recovered-plant readouts were often within a few cells of a never-trained twin, so raw half-cue counts are contaminated by generic responsiveness, and a never-trained twin is a required control.
**Origin.** Recovered-plant diagnosis (`docs/plant2/STAGES.md:28-29`; `docs/plant2/AUDIT-2026-10-10.md:41-42`; `docs/recovery/project-facts-2026-10-03.md:83-84`), 2026-10-10.
**Status.** `mixed`
**Confidence.** High: on one seed the twin reached 11.3 of 16.
**Expected outcome if true.** Trained and never-trained readouts overlap on raw counts.
**Evidence for.**
- With learning frozen, W cells under a half cue at 50 ticks number 1.2/1.6, 1.6/2.0 and 3.8/3.8 (trained/never-trained), and single readouts of one arm range from 1 to 7 spikes on seed 1 (descriptive, SPEC 8.22 Part A; `SPEC.md:3868-3874`).
- The twin's half-cue response is 6.4, 7.0, 7.8, 11.3, 9.2 and 8.7, against 11.5, 11.1, 14.9, 13.7, 14.1 and 13.3 trained (descriptive, SPEC 8.46; `SPEC.md:6124-6129`).
**Evidence against.** none recorded
**Tested by.** Recovered plant
**Experiment needed.** Settled as a rule of method: every capability claim needs a never-trained or shuffled control (`docs/research/README.md`).
**Notes.** none

**H-077** The assembly is a transient response, not a bound representation
**Statement.** In the master plant, the same 2 s of activity that defines an assembly removes its drive, so the assembly is a transient response, not a bound representation.
**Origin.** Recovered-plant diagnosis, SPEC 8.2 (`SPEC.md:1397-1411`).
**Status.** `mixed`
**Confidence.** Medium: it rests on one section's measurements.
**Expected outcome if true.** One second after presentation, the full pattern evokes no more assembly spikes than a copy that was never presented with it.
**Evidence for.**
- Assembly cells ran at 5.3 Hz against a 1 Hz target for two sweeps and lost 16 % of excitatory ctx-to-hpc and 37 % of recurrent hpc-to-hpc inputs. One second after presentation the full pattern evoked 2 assembly spikes, against 2 in the no-stimulus copy (descriptive; `SPEC.md:1397-1411`).
**Evidence against.** none recorded
**Tested by.** Recovered plant
**Experiment needed.** None possible on the frozen plant.
**Notes.** The rate EMA was still 2.3 Hz against the 1 Hz target, and the threshold was not elevated (θ 0.09 mV above rest), so the threshold is not the cause (descriptive; `SPEC.md:1397-1411`).

**H-078** The pending tag's recall was learned disinhibition
**Statement.** The pending tag's recall (SPEC 8.30) was learned disinhibition, not excitatory binding. Excitatory binding (8.46) then fails official K1.1 on assembly size and persistence.
**Origin.** Recovered-plant audit (`docs/plant2/AUDIT-2026-10-10.md:29-30`; `docs/recovery/project-facts-2026-10-03.md:88-96`), 2026-10-10.
**Status.** `mixed`
**Confidence.** Medium: the code of the best line (8.30, 8.46) was not recovered.
**Expected outcome if true.** Excitatory binding gives oversized assemblies whose gain decays within seconds.
**Evidence for.**
- In 8.46 the assembly is 40-61 cells against 20, and the gain is +4.7 at 1 s, +2.5 at 10 s and +2.8 at 37 s. In 8.31 the size was 86-134 against a maximum of 20 (descriptive; `SPEC.md:6134, 6216-6217, 6333-6338`; the 8.31 figure is from the secondary account, `docs/recovery/project-facts-2026-10-03.md:88`).
**Evidence against.** none recorded
**Tested by.** Recovered plant
**Experiment needed.** None possible; the code was not recovered.
**Notes.** none

**H-079** The Stage 0 operating point sets the noise floor
**Statement.** The problem of separating cue from background cannot be solved by moving one parameter. A quieter cortex needs noise and stimulus drive rebalanced, which is "a redesign of the Stage 0 operating point, not a parameter".
**Origin.** Recovered-plant diagnosis, SPEC 8.24 (`SPEC.md:4078-4087, 4115-4119`).
**Status.** `mixed`
**Confidence.** Medium: it rests on one what-if run.
**Expected outcome if true.** Lowering the cortical rate target alone voids the plant.
**Evidence for.**
- Noise alone gives about 0.7 Hz with no input. Lowering the cortical target to 1 Hz alone voids the plant: hpc E falls to 0.3-0.5 Hz, and 4-5 % of cortical E cells spike within 50 ticks with or without A (descriptive; `SPEC.md:4078-4087, 4115-4119`).
**Evidence against.** none recorded
**Tested by.** Recovered plant
**Experiment needed.** None possible; plant2 replaced the substrate.
**Notes.** none

**H-080** The plant cannot reach Stage 1 without changing plasticity and homeostasis together
**Statement.** The recovered plant line cannot reach Stage 1 without changing its plasticity and homeostasis together.
**Origin.** The audit's "Consequence" paragraph (`docs/plant2/AUDIT-2026-10-10.md:72-76`) and `DECISIONS.md:225-230`, 2026-10-10.
**Status.** `unresolved`
**Confidence.** Medium: it synthesises H-072 to H-079, but the best line's code was not recovered and the plant cannot be edited.
**Expected outcome if true.** No change to plasticity alone or to homeostasis alone passes Stage 1 on the plant.
**Evidence for.**
- H-072 through H-079.
**Evidence against.** none recorded
**Tested by.** Untested
**Experiment needed.** None possible: recovery is not closed and the plant is frozen (`DECISIONS.md:237-239`).
**Notes.** Editing the plant on a branch and continuing K1.1 on it were rejected (`DECISIONS.md:237-239`).

**H-081** A new substrate that drops the documented causes is cheaper and more honest
**Statement.** "A new substrate that drops those causes is cheaper and more honest than a fiftieth proxy on the old one."
**Origin.** Owner (`DECISIONS.md:214-230`), 2026-10-10.
**Status.** `unresolved`
**Confidence.** Medium: plant2 produced valid, fully recorded verdicts from its first day and passed two Stage 1 clauses on independent items, but no cost comparison was made.
**Expected outcome if true.** Plant2 reaches decisive, recorded results at lower cost than further proxies on the plant would have.
**Evidence for.**
- P2-E1 produced a valid, fully recorded FAIL with a diagnosis the same day. P2-E2 and P2-E3 passed on 5 fresh gated seeds each (gated; H-004, H-011).
**Evidence against.**
- P2-E1 itself failed the Stage 1 gate, and the record does not compare cost or honesty against the old plant (`docs/plant2/P2-E1-btsp.md:7-26`).
**Tested by.** P2-E1 onward (indirectly)
**Experiment needed.** None defined; this is a judgement about the programme, not an experiment.
**Notes.** none

**H-082** Plant2's design removes causes 1-4
**Statement.** Plant2 addresses the four documented causes by design: (1) no dependence on spike timing; (2) no homeostat touches written synapses; (3) sparse inputs (2.5 % active) and 0.5 % plateau cells; (4) one input-to-memory synapse per pair, with about 25 written synapses active under a half cue.
**Origin.** P2-E1 contract, "It addresses causes 1-4 as follows" (`docs/plant2/P2-E1-btsp.md:7-26`), 2026-10-10.
**Status.** `mixed`
**Confidence.** High that the design properties hold; the Stage 1 gate still failed, and a new load-dependent problem appeared.
**Expected outcome if true.** The design properties hold, and the plant's failure modes (H-072 to H-075) do not recur.
**Evidence for.**
- The design properties held. Written cells carry 24.69 cue synapses under a half cue on seed 1, close to the "about 25" of cause 4 (gated run, descriptive; `docs/plant2/P2-E1-btsp.md:42-44, 274-277`).
**Evidence against.**
- The Stage 1 gate failed, and a load-dependent operating-point problem appeared (gated; H-003). The capacity edge on seed 1 is between M = 1,000 and 2,000 (reported-only; `bench/results/plant2.jsonl:7-11`).
**Tested by.** P2-E1
**Experiment needed.** Settled for the design properties; see P2-E1.
**Notes.** Cause (3) returns in another form on correlated items (H-035). H-083 and H-084 sit in section 4 by theme but were numbered after this entry.

## Changelog

- 2026-10-22: File created from the hypotheses arrays of `.agent/ledger/P2-E1.json` to `P2-R2.json`, the owner hypotheses, approved directions and rejections in `owner-rulings.json`, and the diagnosed causes in `recovered-plant.json`. It has 82 entries, H-001 to H-082. H-044 carries the alias H-R2. The P2-R2b result of 2026-10-22 is recorded against H-042, H-043, H-044, H-045, H-046 and H-061.
- 2026-10-22, P2-E7 development seed 121 (`docs/plant2/RESULTS-P2-E7.md`): H-060 `under_test` to `mixed` (feasibility screen failed on the absolute bars, informative; comparative margins held on one development seed); evidence added to H-060. H-055's two ruling-4 tests came out favourable on the same seed (useful error information; unrelated memories preserved) and H-046's prediction held again (inherited content ≤ .055 at F10/1,000 on every non-oracle arm, .005 on candidate and baseline); their statuses are unchanged pending the next checkpoint's review of the whole record. Independent results review 2026-10-22: every number reproduces; twelve wording errata appended to `docs/plant2/RESULTS-P2-E7.md` and applied here (H-060 confidence stays low; erratum 4 and 5 wording).
- 2026-10-22, offline screens (`docs/plant2/OFFLINE-SCREENS-20261022.md`): H-060 gains the screen-A warning as offline proxy evidence against; B-008's timing-brake reading enters as offline evidence that a latency cut cannot clear C1 and C2 together (bears on H-062 and H-067; statuses unchanged).
- 2026-10-22, after the roadmap checkpoint: H-060 `proposed` to `under_test` (contract P2-E7 frozen at fede3c2); H-055 is tested through P2-E7's two ruling-4 controls and stays at its recorded status until the result. The intro's sentence "No entry is `under_test` at this date" no longer holds: H-060 is.
- 2026-10-22, critic pass against the same sources: added H-083 (P2-E5's withdrawn "specific but slow" and "no pass observed in simulation") and H-084 (P2-R1 question 1, the audit of committed P2-E4/E5 counts), both in the source hypothesis arrays but missing from the first draft; the file now has 84 entries. Statuses lowered: H-017 `mixed` to `proposed` (synthetic raster only), H-035 `supported` to `mixed` (the record scores its C2 range as failed), H-058 `supported` to `mixed` (predeclared C4 failed in P2-E1, passed in P2-E2). H-043's statement lost the clause that per-line load contributes beyond sibling correlation, which P2-R2b erratum 1 says the design cannot decide; H-026's statement now uses the owner's "not necessarily". H-063's note on the stabiliser ruling, H-028's note on the latency question and H-060's seed attribution were corrected. Citations were corrected to the lines that hold each number in H-001, H-003, H-008, H-010-H-013, H-015, H-016, H-020, H-022, H-023, H-027, H-029-H-031, H-033-H-037, H-040, H-042-H-046, H-048, H-049, H-052, H-056, H-058, H-063, H-068, H-072-H-076 and H-078; H-043's coin-draw figure is "713/722 episodes", one figure per seed, not "713 of 722". The README rule on `mixed` is now quoted as the README states it, with this ledger's extensions marked as its own.
