# P2-R1 results review: methodology and evidence

Independent review of `bench/results/p2r1.jsonl`, its four portable per-cue JSON files, the frozen `docs/plant2/P2-R1-takeover-replay.md`, and `analysis/p2r1_replay.py`. Both mandatory runs completed: correlated seed 44 and independent duty seed 90, each at M=500 and M=1000. Optional seeds 45 and 91 were not run. No experimental gate is reopened and this review assigns no PASS label.

**Assessment:** the recorded numerical conclusions are supported. No computation error was found in the required portable aggregates or writer selections. The main risk is overstating the causal and capability conclusions: these are selected-seed, settled feedback replays, including a replay of a store learned on an online duty schedule. They do not demonstrate R3's live online recall or identify a sufficient forward-index correction.

## Independent checks

- All four compact-artifact SHA-256 values and all four newly generated raw NPZ SHA-256 values match their records. The current driver and frozen-contract hashes match the recorded hashes. Each completed load agrees exactly between its progress record and final record.
- Recomputed **718 scalar/list aggregate comparisons**, all matching: C1–C4 counts, memory recall medians and latency; all five arms' required content counts, joint/D1/D2/D3/D4, 50-ms variants, intrusion summaries, reconstruction summaries and content latency; writer precision/recall and mean cardinality; and duty's live baseline rates. Content comparisons cover 12,000 portable rows; index comparisons use 2,400 cue rows.
- Independently regenerated **15,000 saved writer selections** across the four checkpoints from NPZ continuation cells/counts, assigned sets and the contract streams. R3 is exactly count >=3. Random and anti-selected writers have exactly R3 cardinality on every item and are subsets of the observed responders; neither selection reads A. Every saved writer intersection/cardinality row matches these reconstructed sets.
- Correlated seed 44's inherited R1 per-cue joint bit string matches the historical P2-E5 exploration record at both loads. Its R1/A/R3 frozen joint, D1–D4, and reported memory statistics also match. The historical runtime was Python 3.13.16 / NumPy 2.5.3; this run records Python 3.12.14 / NumPy 2.3.5. Matching these outputs is not a claim of historical raw-raster identity: those historical raw artifacts remain absent.
- This reviewer did not rerun neural simulation or replay the full readout dynamics. Raw checks here were hash verification and independent writer reconstruction; the aggregate checks used portable outcomes and source inspection. Store/raster digests and the simulation-preservation flags were not independently regenerated in this results review.

## Measurements and predictions

All content figures below use the **settled memory raster and fresh reconstruction-layer replay**, frozen J_fb=2.80, g=0.3, and the 75-ms content window. Index figures use 50 ms. Each content joint denominator is 200 cues.

| Regime, seed, load | R1 joint | A joint | R3 joint | Random joint | Anti joint | Index C1 / C2 | Oldest index specificity |
|---|---:|---:|---:|---:|---:|---:|---:|
| Correlated 44, 500 | .090 | .965 | .965 | .300 | .090 | .915 / .900 | .840 |
| Correlated 44, 1000 | .010 | .125 | .160 | .005 | .000 | .925 / .500 | .400 |
| Duty 90, 500 | .995 | .995 | .995 | .940 | .880 | .965 / 1.000 | 1.000 |
| Duty 90, 1000 | .205 | .995 | .995 | .710 | .655 | .955 / .970 | .970 |

R3's oldest-content joint is respectively .94, .12, 1.00 and 1.00; its novel-cue D3 is respectively 1.00, .995, 1.00 and 1.00.

Every predeclared quantitative prediction holds on its specified mandatory run:
- Correlated M500: R3=.965 >=.85; R1=.090 <.25; R3 equals A's joint, within .05.
- Correlated M1000: R3=.160 and A=.125 are below .90; C2=.500 <.65. Memory is shared across feedback swaps by design.
- Duty M1000: R3=.995 >=.90; gains over random and anti are .285 and .340, exceeding .10; R1=.205 <.35.

These inequalities hold. The contract's explanation “because index interference persists” is a causal interpretation, not an additional independently isolated finding of this replay.

## Findings

### M1 [major interpretational limit] Duty's R3=.995 is not online R3 retrieval

`analysis/p2r1_replay.py:236–265` settles a copied memory network and passes its raster to five separate, fresh readouts. Only inherited R1 has live online measurements (`:273–280`). At duty M1000, the actual live baseline has C1=.955, C2=.995, content joint=.545 and oldest-content joint=.480. The R3=.995 value is on the settled twin's different cue set and reconstruction state; it cannot replace .545 in an online result table or establish simultaneous online access and clean content. The driver and frozen contract label this correctly. Preserve that distinction in the Result and owner-facing summary. No new online R3 measurement is required to close this reported diagnostic.

### M2 [major interpretational limit] Content improvement does not clear even the lower-load structured gate

On correlated M500, R3's content joint=.965 and oldest-content joint=.94 are good, but the unchanged index fails oldest specificity at **84/100**, six cues below the historical bar. At M1000, index C2=100/200 and oldest specificity=40/100 are far below their bars, while R3 content=32/200 and oldest content=12/100 also fail. Do not describe M500 as a structured-memory solution or M1000 as only a content-write problem. The evidence supports retaining the authorized index-first direction, but does not discriminate error-gated from load-gated forward eligibility.

### M3 [major interpretational limit] This is a selected-seed reconstruction, not independent generalization evidence

Seeds 44 and 90 already informed the hypotheses and numerical expectations. No optional replication or fresh gated seed was run. The 200 cues within a seeded network share stores and training history; they are not 200 independent networks. Large paired gains support the intervention comparison on these rasters, not a five-seed pass probability or robustness across input distributions, rates and schedules. Keep “mandatory diagnostic runs completed” separate from “replicated across seeds.” No rerun is needed to acknowledge this scope.

### M4 [supported causal contrast, bounded] Writer identity matters beyond per-item cardinality, but R3 still reads an assigned key

Duty M1000's paired R3 improvements are **57 wins / 0 losses** against random, **68/0** against anti and **158/0** against R1. Correlated M500 gives **133/0** against random and **175/0** against anti. Equal per-item writer counts eliminate a mere number-of-writers explanation for those contrasts at the frozen readout.

They do not isolate a biological eligibility mechanism. Store union sizes and degree distributions differ, the comparisons use one control realization each, and the burst is measured after externally scheduled BTSP has written the random plateau key. At correlated M1000, R3's writer precision/recall against A is .9975/.9657; duty M1000 gives .9986/.9997. Marked write timing, assigned keys, sensory eligibility and one-to-one values remain supplied. An offline store assembled from those bursts is a measured mechanism candidate, not autonomous learning.

### M5 [minor] R3 is neither an exact plateau store nor an itemwise monotonic repair

At correlated M1000, R3 beats A on eight cues and loses one, giving 32 versus 25 passing cues. Against R1 it wins 32 and loses two. Thus “equals the plateau store,” “upper bound,” and “preserves every previously successful item” would be inaccurate. At M500, and on duty at both loads, R3 and A have identical joint-outcome bit strings, but their stored synapse digests differ. Say “matches the plateau comparator's content score where stated.” The R3 improvement at M1000 does not justify tuning the fixed k=3 or claiming the remaining failure is solely upstream.

### M6 [minor evidence scope] One supplementary counter remains raw-only

The retained `out_of_window_spikes` at `analysis/p2r1_replay.py:259–261` cannot be reconstructed from compact rows of unique regenerated-line counts. It requires the raw replay inputs and a dynamics replay. The latency gap identified in the earlier code review is fixed: per-cue latencies are present and their medians match. All required criterion aggregates used in this review are portable. Do not extend that statement to every stored diagnostic scalar; if out-of-window spike counts become a substantive claim, preserve portable supporting evidence or identify them as raw-replay-only. This does not change any result above.

## Suggested precise results summary

P2-R1 completed its two mandatory reported diagnostics. On correlated seed 44 at M500, burst-selected R3 feedback raised settled content completion from 9.0% to 96.5%, versus 30.0% for count-matched random writers. On the independent duty seed 90 at M1000, the online-written R3 store scored 99.5% on a settled replay, versus 20.5% for inherited R1, 71.0% for random and 65.5% for anti-selected writers. These controls show a writer-identity benefit beyond reducing writer count on the tested rasters. Correlated M1000 remains poor: R3 content is 16.0%, index specificity 50.0%, and oldest index specificity 40.0%. The lower correlated load also retains an oldest-index specificity failure. All quantitative predictions held, but these reused seeds and settled swaps establish neither live online R3 recall nor autonomous key selection, and they do not close Stage 1. The authorized forward-index correction remains the next gated mechanism.
