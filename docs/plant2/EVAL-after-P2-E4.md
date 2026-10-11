# Evaluation after P2-E4: what online memory showed, and what the next mechanism should be

Written 2026-10-11, after P2-E4's verdict, its post-verdict diagnosis and an independent results
review. It follows the owner's standing instruction to judge every experiment by whether it reduces
the cognition the experimenter supplies.

**Sources:**
- the P2-E4 Result (`docs/plant2/P2-E4-online-memory.md`);
- the gated diagnosis (`docs/plant2/P2-E4-diagnosis-plan.md`);
- four independent reviews (`review/plant2/P2-E4/results-*.md`): methodology, code, and two
  through a north-star lens, one constructive and one skeptical;
- P2-E5's exploration seeds 44-45 so far.

Exploratory numbers are labelled as such. They are not results.

## Short answer

**P2-E4 adds no capability and removes no supply at learning time. Its value is a supply nobody
had named.**

- **The verdict.** P2-E4 failed as predicted, on 5 of 5 valid fresh seeds: ONLINE INDEX FAIL +
  HABITUATION FAIL + RECOVERY FAIL.
- **The newly named supply.** P2-E3's PASS relied on the experimenter separating two states:
  - P2-E3 writes in a high-threshold state (continuation offset 8.35-8.56 mV);
  - it reads after a 50 s rest in a low-threshold state (3.65-3.74 mV).

  With one state, at M = 1,000 the system gives fast access or clean content, never both, on the
  same synapses.
- **The failure is narrower than its labels.**
  - Online, stored content still comes back on every seed.
  - What fails is reaching the memory code within 50 ms. Those retrievals are about 7 ms slow; 86-100 % of the failing cues pass after a rest, on unchanged synapses.
  - Habituation is every repeated assembly accommodating, as designed.
- **The owner's encoding-retrieval trade-off** is real, and it is the most important problem on
  the line. It is shown for the current write rule, which lets every cell above one shared
  threshold write content. It is not shown for the architecture.
- **The most efficient next test** is the owner's eligibility hypothesis in its activity form:
  only cells that fire a burst may write content. It is cheap, it is one mechanism, and
  exploratory evidence (one P2-E4 seed, two P2-E5 seeds) says it may separate write quality from
  the threshold state.

## What the experimenter supplies now

The list from `EVAL-after-P2-E3.md`, updated:

| # | supply | after P2-E4 |
|---|---|---|
| 1 | when to write (plateaus only inside marked encodings) | unchanged |
| 2 | the key (random plateau cells, content-blind) | unchanged |
| 3 | the value (input lines copied 1:1 into the reconstruction layer) | unchanged |
| 4 | the operating point (J, g, accommodation; rest before testing) | the rest before testing is removed for the test; it fails without it |
| 5 | the input statistics (independent random items, clean half cues) | unchanged (P2-E5 tests correlated items) |
| 6 | the test regime (frozen copies, plasticity off) | removed in P2-E4's main line; the habituation copies still use it |
| 7 | **new: separate encoding and retrieval states, set by the schedule** | named by P2-E4 |

So P2-E4 removed test-time scaffolding (items 4 and 6, partly) and found that the system fails without it. "Online" in P2-E4 means **recall while scheduled learning continues**, not online learning.

## What P2-E4 shows, read carefully

**Access fails by latency, not by loss.**
- At M = 1,000, index recall within 50 ms is 0.68-0.74, including the newest items (recent cues
  0.72-0.82).
- The failing cues' assembly fires 6-8.5 ms later than passing cues'. 89-93 % of them reach the
  recall bar within 75 ms. Post hoc, C1 at 75 ms is about 0.955-0.97 (recall only).
- 86-100 % pass after a settle on the same synapses.
- The cue-level cause is not identified. The onset threshold offset does not distinguish slowed
  cues in the gated data: the differences are -0.15 to +0.57 mV, of either sign. The exploration
  correlate did not replicate.

**The content store is contaminated, and the online regime hides it.**

| store, read on the same raster (twin A, M = 1,000) | joint |
|---|---|
| online-written | 0.82-0.905 |
| written under P2-E3's protocol | 0.96-1.0 |
| written from the plateau set (assigned assembly, an upper-bound diagnostic) | 0.985-1.0 |

- On the same synapses, content reads 0.93-0.965 online but 0.835-0.915 after a settle.
- The duty arm (I = 2,000 ms) runs at a lower offset. It restores online index access (C1
  0.945-0.985), but its store collapses (twin A 0.175-0.245; online joint 0.485-0.565).
- The novel-duty twin never retrieves anything, yet writes a store of the same quality as the
  main line. **Input duty drives contamination; retrieval does not.**

**Why the trade-off may belong to the write rule.** Every cell that fires even once in the 50 ms
continuation writes the item's content. The number of such cells falls on one curve of the
continuation offset:

| state | continuation offset | responders \|R\| |
|---|---|---|
| P2-E3 protocol | about 8.4 mV | 28-29 |
| P2-E4 main line | about 6.9 mV | 41-45 |
| duty arm | about 4.1 mV | 121-136 |

A lower threshold makes access easier and recruits more wrong writers. Any change to the
threshold or the accommodation time constant only slides along this curve, as the owner said.

**Habituation is graded and universal.**
- All 50 repeated items recall less than their controls, on every seed and load: a mean drop of
  0.11-0.13.
- Net of the control copy, the assembly offset rises 2.0-2.1 mV.
- O4 counts items near the bar.
- RECOVERY FAIL rests on one seed and load, one item short. A post-hoc paired check suggests
  recovery of the repeated item really is incomplete.

**Learning outside the write oracle mostly fails** (reported arms; the predictions failed):
- writes during probe slots: 0.165-0.20 are later recallable;
- 30 % cues: C1 0.0;
- noisy half cues: 0.075-0.175;
- lures sharing 50 lines are recalled as the stored item 0.90-0.95 of the time.

## The next mechanism: burst-gated feedback eligibility

**The owner's hypothesis** (2026-10-11): a memory cell being active during an experience should
not automatically qualify it to write that experience's content. Eligibility must be derived
locally.

**Its activity form** (constructive reviewer). A cell may write content only if it fires a short
burst: at least k spikes in the 50 ms continuation, with k = 3 fixed by P2-E5 Part C, not tuned.
The signal is the cell's own spike count, which is local.

**Exploratory evidence** (not results):

| probe | measure | result |
|---|---|---|
| P2-E4 seed 90, the reviewer's probe on the frozen driver | burst-count AUC, assembly cells against other responders | 0.9999 on the main line and in the duty arm |
| | twin A at M = 1,000, main / duty: R_3 store | 0.995 / 0.995 |
| | online-written store | 0.83 / 0.205 |
| | size-matched random subset | 0.885 / 0.71 |
| P2-E5 seeds 44-45 (correlated items), settled protocol | count AUC | 0.9994-0.9995 at M = 500; 0.995 at M = 1,000 |
| | R_3 store grid best, against the plateau-set store | 0.99-1.0 vs 0.99-1.0 at M = 500; 0.69-0.705 vs 0.665-0.69 at M = 1,000 |

The size-matched random subset reads 0.885 and 0.71 against R_3's 0.995. So the identity of the
writers, not their sparsity, carries the gain.

**What it would and would not do:**
- It touches only the content write. The memory raster does not depend on the feedback store, so
  every index criterion is bit-identical by construction: ONLINE INDEX FAIL, HABITUATION FAIL and
  P2-E5's index failures would be inherited. It must say so in advance and check a memory-raster
  digest.
- It removes one supply: the dependence of write quality on the schedule's state separation
  (item 7). It does not remove the write oracle, the key or the value (items 1-3).
- **Its decisive reading** is the duty arm. If the store written there reaches the P2-E3 bar
  while online index access holds, the trade-off belongs to the write rule. Then an access
  mechanism can follow without trading one failure for another. If the store stays low, cells that
  should not write also burst; the trade-off is then architectural, and the next mechanism must
  be an encode/retrieve state that the network generates itself.
- **Where it differs from the plateau-set store,** it differs in the direction that matters for
  familiarity (exploratory, seed 90). A lure drives about 5 of the stored item's assembly cells to
  burst, so it would write its new lines onto the old memory. An exact repeat bursts 99 % of the
  old assembly. A contract must predeclare reported arms for lures, repeats and s = 40, and use the
  "fresh items give about 0 eligible cells" sham as a validity check.
- **To make a pass mean something,** a contract needs a fails-if-false control: the size-matched
  random subset, predicted to lose by at least 20 cues in the duty arm, and an anti-selected
  subset.

**What it cannot do:**
- fix slow access;
- fix habituation;
- fix forward-index cross-talk on correlated items. In P2-E5's exploration at M = 1,000, the
  constructive reviewer counts about 19 spurious cells per cue, 98 % of them siblings' plateau
  cells, and the plateau-set store's grid best is only 0.665-0.69.

## After that

These are candidates, in the reviewers' order. Each is one contract, and some need a ruling.

1. **Access: an eligibility-gated recurrent completion basin.**
   - What it is: one-shot binary memory-to-memory synapses between cells that both burst, with a
     fixed activity-proportional inhibition in the memory layer as a stabiliser.
   - The stabiliser needs a ruling: your ruling 3 allows it for Stage 2 only. P2-E1's review
     found runaway at J_rec 1.5.
   - Controls: a no-recurrence twin with the same inhibition, an inhibition-only twin, and a
     degree-matched shuffled recurrent store. A gain that the shuffled store also produces is a
     lowered threshold.
2. **Index cross-talk on correlated items: error-gated forward eligibility.** This is from the
   approved error-correcting family. An input line is BTSP-eligible only if the reconstruction
   layer did not regenerate it, so new assemblies key on what memory did not predict. It needs
   the burst-gated write first, as a clean comparator. If P2-E5 reads INDEX-DOMINANT at both
   loads, it could come before the basin.
3. **Mismatch-triggered plateaus,** after your ruling on context identity. A plateau fires when
   input drive meets a local mismatch. This would remove the write oracle and the content-blind
   key, the largest supplies left (items 1-2). Familiarity-gated allocation stays deferred, per
   your ruling.

**Bearing on later stages** (constructive reviewer):
- **Sequences.** The burst signal, held as a decaying trace, is the natural pre-side signal for
  memory-to-memory transitions; without it each transition would link 41-136 cells.
- **Abstraction.** None of these mechanisms is abstraction.
- **Problem solving.** A planner replays while it perceives. Activity-based eligibility alone
  would let replay write the current input, so perception-triggered plateaus (3 above) are the
  guard.

## Risks to the line

- **Collecting diagnostics instead of capability** (skeptic). P2-E4 and P2-E5 carry no mechanism
  by design, and each went through three or four review rounds. P2-E5 will run exactly as
  frozen, with no new arms. Post-run diagnosis is limited to what decides the next contract. The
  next contract should be a mechanism with a predeclared capability gain and a named supply that
  it removes.
- **Stage 1 is several contracts away.** One system must pass P2-E3, P2-E4 and P2-E5, plus
  capacity and graceful forgetting. Past capacity the store blacks out (stress joint 0.00 at
  M = 3,000).
- **The memory layer is a feed-forward spiking Willshaw store with random keys.** Nothing yet
  chooses its own representations.

## Decisions for the owner

1. **May burst-gated feedback eligibility be the next contract,** after P2-E5's verdict? It would
   gate only its target (the online-written store's twin A joint at M = 500 and 1,000, on the
   main line and the duty arm, plus P2-E3's content gates on fresh seeds). It would re-run P2-E4
   and P2-E5 as reported comparisons, with k = 3 from P2-E5 Part C.
2. **May fixed, activity-proportional stabilising inhibition in the memory layer join a Stage 1
   recurrent completion mechanism,** under the conditions you set for Stage 2 (matched
   comparisons, frozen parameters, no silencing, no forced answer)?
3. **Where does forward-index cross-talk on correlated items go:** before or after the access
   mechanism? P2-E5's Part B reading will inform it.
4. **One latency bar.** Should future contracts use one window for both index and content? Index
   is 50 ms and content 75 ms today. The bar would be set before any data and tied to a
   downstream need, for example a Stage 2 chaining period.
5. **Optional.** Should seed 18's M = 500 habituation copies be replayed as a reported-only check?
   RECOVERY FAIL rests on that seed and load alone. The diagnosis replayed only the main line.
