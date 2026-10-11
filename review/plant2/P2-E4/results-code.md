# P2-E4 results review: code lens

Independent reviewer given only the files (HEAD bbeb25b, after the verdict and the post-verdict diagnosis). Run 2026-10-11. Recorded verbatim, before synthesis.

## Verdict

I found no bug in p2_e4_online.py that changes a gated number, label or validity flag. I recomputed the following independently, without the driver's functions:
- every gated seed-load (16-20) and exploration seed-load (42-43), from the per-slot logs and records;
- per-slot consistency: joint, both and spur_ok from the logged counts; recall equals hits/|A|; |R50| equals hits plus spurious;
- O1-O3 rates and vectors, the leak rule, and the O4/O5 counts and states from the per-step habituation logs;
- the verdict labels;
- a schedule rebuild: 0 plan mismatches, with cohort, c500 and age-0 rules all holding;
- sha256 of all 21 logs, and DIGEST;
- exact (non-Monte-Carlo) recovery estimability.

All match. Remaining issues are a tautological validity check, thin label margins and two nits.

## Findings

### F1 [minor] Validity 5 (proj_current, inh_ok) cannot fail by construction

- where: plant2/experiments/p2_e4_online.py:232, 280-286, 329, 368-369, 387-388
- evidence: proj_current compares fb_version with proj_version. Every fb_version += 1 is followed at once by reload_fb(), which sets proj_version = fb_version, so the two cannot differ. inh_ok compares the f32 weight set at construction with the same product. Neither compares the loaded CSR with fb.csr(). No harm found: twin A's live rec matches the replay from fb with 0/0 differing spikes at both loads on all five gated seeds (463k-665k spikes), and fb_union_ok is true. P2-E5 reuses slot_checks_ok as validity, so it inherits the tautology.
- recommendation: Describe validity 5 in the P2-E4 verdict text as met by construction, with twin A's zero replay mismatch as the evidence. For P2-E5, state the same in its record. Any added check, such as a digest of fb_proj.indptr/post against fb.csr() at block ends, goes through the owner, because P2-E5's contract is frozen.

### F2 [minor] RECOVERY FAIL and the absence of ONLINE CONTENT FAIL rest on 1-2 outcomes (computed correctly)

- where: hab_criteria p0 (lines 657-665); labels() (1073-1092); records for seeds 18 and 20
- evidence: RECOVERY FAIL comes only from seed 18 at M=500: 42 of 47 eligible items recovered, and 43 are needed. The control recovery rate is 205/250 = 0.82. My exact beta-binomial value is 0.831, against the driver's Monte Carlo 0.8289 and the 0.8 bar. At 204/250 it is 0.813; at 203/250 it is 0.794, which would give NOT ESTIMABLE. Separately, seed 20's M=1000 O3 content is exactly 90/100, so one more joint failure would add ONLINE CONTENT FAIL. Main-line slots were replayed exactly by the diagnosis; the habituation copies were not.
- recommendation: State these margins in the verdict text. If the owner wants the label-carrying copies reproduced, predeclare a reported-only replay of seed 18's M=500 habituation copies, in the same way as the diagnosis plan.

### F3 [nit] Validity 4's identity check relies on BinarySynapses always rebinding keys

- where: p2_e4_online.py:350; plant2/btsp.py add/toggle
- evidence: writes_ok tests `store.keys is onset_keys`. This is sound only because toggle() and add() always assign a new array; add() even rebinds when every key is already present, so false alarms are possible but misses are not. An in-place write would pass silently. The 'full digests at block ends' are recorded as fwd_digest/fb_digest but are not compared against any per-slot state. btsp.py is pinned by blob id for P2-E5, so this is safe now.
- recommendation: No action for P2-E4. Note the assumption beside validity 4 so a future change to btsp.py is checked against it.

### F4 [nit] Observation: content failures are near-total rec silence, tied to small plateau sets

- where: gated main-line per-slot logs, steps 1-1,000 (exploratory, post hoc)
- evidence: Across 2,762 recent, uniform, cohort and oldest cues on the gated main lines, 79 had 0 regenerated lines and only 3 had 1-39. Silence by assembly size: 0-10 cells 64 %, 11-14 cells 12 %, 15-18 cells 2.7 %, 19 or more cells under 0.5 %. Index recall (>= 0.8) stays at 0.78-0.83 across sizes. The 29 silent cues that still passed index recall have a median |A| of 11. This is consistent with the frozen code (fixed J_fb, global inhibition of g·J_fb per memory spike); it is not a bug.
- recommendation: Treat it as a hypothesis-generating reading only. If it matters for the local-eligibility hypothesis after P2-E5, it needs its own predeclared measure.

## Next steps

- Keep P2-E4's gated numbers, labels and validity flags as recorded; the code produced them correctly and nothing needs a re-run or correction.
- Add the margins to the verdict text: seed 18 at M=500 recovered 42 of 47 against 43 needed, with estimability 0.831 against the 0.8 bar; seed 20 at M=1000 has O3 content at exactly 90/100.
- Before P2-E5 runs, record that slot_checks_ok's proj_current and inh_ok parts are met by construction. Use twin A's replay mismatch as the evidence that the live projection is current.
- Optional, at the owner's discretion: predeclare a reported-only replay of seed 18's M=500 habituation copies, since the diagnosis reproduced only the main line.

## For the owner

P2-E4's code computed the gated result correctly. I checked every gated seed and load from the saved logs with my own code, and every number, label and validity flag matches. The log checksums match too, and an exact recalculation confirms the recovery-power call. The FAIL verdict stands as recorded. Two labels are close calls:
- RECOVERY FAIL rests on one seed and load, short by a single item.
- The absence of a content failure rests on one cohort score of exactly 90/100.

One validity check (live projection current) cannot fail as written. Other evidence shows the projection was current. P2-E5 reuses that check, so its record should say so.

Content failures were nearly always total silence, mostly in items with small plateau sets. This is exploratory and not a result.
