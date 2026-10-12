# Evaluation after P2-E5: correlated items, and what should come next

Written 2026-10-11, after P2-E5's verdict and an independent four-lens results review. P2-E5's
Decision sends any STRUCTURED INDEX FAIL to the owner before any mechanism contract. This document
is that report. It supplements `docs/plant2/EVAL-after-P2-E4.md`; that document's questions still
stand, and two of them are sharpened below.

**Sources:**
- the P2-E5 Result (`docs/plant2/P2-E5-structured-items.md`, last section);
- the four results reviews (`review/plant2/P2-E5/results-*.md`);
- the P2-E4 Result and its gated diagnosis.

## Short answer

**P2-E5 failed as predicted, on 5 of 5 valid fresh seeds: STRUCTURED INDEX FAIL + STRUCTURED
CONTENT FAIL.** Stage 1's structured-input clause is not met. Two independent reviewers recomputed
every count and reading from the persisted data and matched the records exactly.

What it settles:
- **Content collapses on correlated items** at both loads. The joint is 0.095-0.18 at 500 items and
  about 0 at 1,000, while the same system on independent items (s = 100) still passes,
  0.97-1.0.
- **The memory index itself fails** on correlated items. The failure is narrow at 500 items, on 2 of
  5 seeds and 2-6 cues short, and broad at 1,000 (specificity C2 0.435-0.515).
  **No feedback-write fix can change that,** because the memory layer's activity does not depend on
  the content store.
- **At 1,000 items, no content store reaches the bar on these rasters.** That includes the
  plateau-set store, the upper-bound diagnostic, even with the readout recalibrated optimistically.
  The per-line load on shared prototype lines contributes: with ten families (F = 10), each
  prototype line serves about 100 items.

Two of my earlier statements were wrong, and both are corrected in the Result:
- I said "online, the index is specific but slow". The online and settled specificity figures come
  from different cues, and P2-E5 never measured latency. What the data show is that online the
  memory layer fires less, giving both fewer wrong cells and fewer right ones.
- I said the burst signal "supports the activity form of your eligibility hypothesis". It recovers
  your experimenter-assigned plateau key from the network's activity. That is a measurement, not a
  mechanism, and it removes no supply.

## What the readings mean

| reading (frozen rule) | what it does show | what it does not show |
|---|---|---|
| Part B: CONTAMINATION-DOMINANT at both loads | At 500 items, the content write is the largest loss, under either readout convention. | At 1,000 items it holds only under the predeclared grid-best convention. At the frozen readout the same rule reads INDEX-DOMINANT on 5 of 5 seeds. |
| Part C: AVAILABLE FROM ACTIVITY | Cells firing 3 or more spikes in the 50 ms after an item are the plateau-written cells: AUC at least 0.995. A store written from them equals the plateau-set store. | That the network chooses its own writers. The positives are defined by your random key, and they burst because the plateau just wrote them. |
| Part D: WORSENS at both loads | The store written online, on P2-E4's schedule, carries more intrusions than P2-E3's protocol store. | Which part of the online regime causes it. Every store is near the floor at 1,000 items. |
| pooled control | At 500 items the content failure is caused by sibling correlation. | At 1,000 items line load alone already fails, so correlation is not the only cause there. |

## What the experimenter supplies now

P2-E5 removes nothing. It changes one supply, the item distribution, from independent to
correlated items. The list in `EVAL-after-P2-E4.md` (items 1-7) is unchanged.

## The next step: the two reviewers disagree

**The constructive reviewer: burst-gated feedback eligibility first.**
- Gate it on content at 500 items and on P2-E4's online tests, including the duty arm.
- At 500 items, a store written by bursting cells reads 0.93-0.97 of cues online, against
  0.05-0.10 for the current write.
- Predeclare that every index criterion is inherited unchanged.
- Then a recurrent completion basin for access, which needs your Q2 ruling.
- Then a forward-index mechanism.

**The skeptical reviewer: the forward index first.**
- Its first argument: the memory layer's activity does not depend on the content store. So any
  content-write rule can be evaluated exactly by replay on the persisted rasters. The
  burst-gated write's result is already largely known: it equals the plateau-set store.
- Its second argument: the write cannot touch the index failure, and that failure is what blocks
  Stage 1's structured clause.
- So spend the next gated contract on the forward index. The suggested mechanism is from your
  approved error-correcting family: during encoding, an input line is BTSP-eligible only if the
  reconstruction layer did not regenerate it. Its fails-if-false control drops the same number of
  lines per item at random.

**My recommendation: the skeptic's order, keeping the constructive reviewer's controls.**
1. **The burst-gated write, run cheaply.** Evaluate it as a predeclared, reported exact replay on
   the persisted P2-E4 and P2-E5 rasters, including P2-E4's duty arm, which was the decisive
   reading. A small fresh-seed confirmation would follow only if you want it gated. Because the
   index is unaffected, a gated run adds fresh seeds and nothing else.
2. **The forward index as the next gated mechanism.** It is the binding constraint for the
   structured clause, and possibly for P2-E4's access failure too.
   - The constructive reviewer's predeclared contrast would choose the variant: error-gated or
     presynaptic-load-gated eligibility, read against the pooled arm.
   - Target: C2 at least 0.9 and L_i under 20 cues at 1,000 items, with s = 100 unchanged.
3. **The access basin,** if you allow memory-layer inhibition (Q2). It must beat the
   no-recurrence system's own threshold curve, not slide along it.

## Decisions for you

The first four are from `EVAL-after-P2-E4.md`, updated by P2-E5:
1. **Burst-gated eligibility.** Gate it now, or run it as a reported replay only (recommended)?
   It removes no supply: the key, the value and the write timing are still yours. On repeats and
   lures, old cells would write new content. That collides with your deferred question of
   context identity.
2. **Stabilising inhibition in the memory layer** for a Stage 1 recurrent mechanism (unchanged).
3. **Forward-index cross-talk.** May the next gated contract target it (recommended)? Choose
   between error-gated eligibility, from your approved error-correcting family, and
   presynaptic-load gating, by a predeclared contrast.
4. **One latency bar** for index and content (unchanged).
5. **New: the line load in the structured clause.** F = 10 families, each prototype line shared
   by about 100 items, largely sets the content ceiling at 1,000 items: the plateau-set store reads
   0.14-0.175 at F = 10 against 0.83-0.91 at F = 40. Which F should the clause assume?
6. **New: the Part B convention.** At 1,000 items it reads contamination-dominant under grid-best
   readouts and index-dominant at the frozen readout. Which convention should rank losses in
   future contracts?

Optional, from `EVAL-after-P2-E4.md`: a reported replay of P2-E4 seed 18's habituation copies.

## Where the line stands

- **Stage 1 has:** one-shot index memory and content completion, on independent items, tested
  after a rest.
- **It does not have:**
  - recall while learning continues (P2-E4);
  - recall on correlated items (P2-E5);
  - capacity scaling or graceful forgetting.
- **The risk the skeptic names is real:** two experiments in a row have carried no mechanism by design.
  The next contract should be a mechanism with a predeclared capability gain and a named supply
  that it removes.


## P2-R1 independent audit errata (2026-10-12; append-only)

The frozen FAIL and predeclared operational labels stand. The independent baseline reviewer
matched80 criterion bits,20 content/oldest counts,10 histogram AUCs and30 grid-loss values.
The following causal/interpretive claims are withdrawn before new mechanism work:
- The pooled control approximately matches hot/cold groups, not each line's frequency. It
  flattens prototype multiplicity hotspots: at M1000 main maximum line loads are137–148,
  pooled81–89. Thus the main-versus-pooled improvement does not isolate sibling organization
  from the marginal load distribution. “Correlation-attributable” remains the frozen label,
  not a clean causal attribution.
- Quoted R3 joint0.93–0.97 against inherited0.05–0.10 is settled readout of online-written
  stores, not measured online retrieval. The inherited online block reads0.475–0.575 at500.
- Approximately100 is family size. Prototype-union lines average57.64–58.66 appearances at1000,
  with substantial variation and multi-prototype hotspots. Prototypes contain100 lines; each
  exemplar retains40 and replaces60.
- “No store” means none of the tested stores/readout points. Assigned-A feedback is a diagnostic
  comparator, not a mathematical upper bound. It remains true that feedback-only changes cannot
  repair the upstream index.
- Not every recommended replay input was persisted. E4 duty and E5 online need new capture in
  faithful inherited-driver reproductions. All28 referenced old cache paths are absent here.

Report and executable checks: review/plant2/P2-R1/findings-baseline-methodology.md and
analysis/p2r1_baseline_audit.py. The owner has now ruled: frozen readout primary; F10 canonical;
R3 reported replay first; forward-index mechanism next.
