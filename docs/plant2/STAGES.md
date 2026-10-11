# plant2: staged path from the recovered plant toward the human-level horizon

Written 2026-10-10 under the owner's north star of that day: a spiking, brain-like system whose
learning and problem-solving capacity moves toward human level (flexible memory, sequential
structure, abstraction over experience, usable behaviour). Human level is the horizon, not a
claim. No LLM or transformer is the mind at runtime. No teacher current, no forced synchrony,
no bar lowered to pass. Every proxy is labelled; nothing is claimed as biology beyond its label.

## Where the recovered plant stands (audit of 2026-10-10)

The recovered plant (`brainsim/`, frozen) is a 2,600-cell LIF network with pair STDP, synaptic
scaling and rate-driven structural plasticity. Its record (SPEC 7-8.49) shows:

- Stage 0 is not complete by its own record: K0.1 (event cost) and K0.4 (immature pruning) are
  red in `ui/stage0_results.json`.
- Stage 1 (episode memory) never passed. K1.1 failed on the master plant (half cue recalled
  1 of 16 assembly cells) and under every labelled proxy stacked on it (8.3-8.12, best 5/16).
  The best later line (8.46, excitatory binding) reached 13 of 16 on four seeds of six, lost
  half its gain within 10 s (8.48), and its code was not recovered.
- The record diagnoses why, in its own measurements:
  1. Pair STDP's uncorrelated fixed point (0.45 `w_max`) sits below the homeostatic rest
     weight (0.6-0.75), so co-activity depresses the used pathway (K0.13 ratio 0.922; 8.19).
  2. The rate homeostat runs on a seconds timescale and treats a stimulus as a rate error:
     scaling and rate-driven elimination each erase a write within 1-3 sweeps and back each
     other up (8.3, 8.13, 8.14, 8.18); scaling caused 51-87 % of the 10 s loss (8.49).
  3. The cortical stimulus code is dense and overlapping, so local rules cannot separate inputs
     better than their rate ratio, about 2 (8.20, 8.22).
  4. Even with oracle weights at the bound, no arm completes a half cue in 50 ticks on that
     wiring (8.23); readouts were often within a few cells of a never-trained twin (8.15-D2).

The plant stays frozen at its recovered paths (`AGENTS.md` invariant 4). The new line, plant2,
is a separate package that keeps the plant's methods (predeclared kill tests, never-trained
controls, labelled proxies, one source of truth for results) and drops the three causes above
from its design: its first learning rule does not depend on postsynaptic spike timing, no
homeostat acts on written synapses, and codes are sparse.

## Stages and gates

Each stage's kill tests are written and committed before its code. One primary mechanism per
experiment. A stage passes only on predeclared numbers, on five of five seeds unless the
experiment's own contract says otherwise, against a never-trained or shuffled control.

| stage | capacity it adds | gate (all numeric bars predeclared per experiment) |
|---|---|---|
| 1 | one-shot episodic memory | Items shown once are stored so that a half cue re-evokes >= 80 % of the item's written assembly within 50 ms for >= 90 % of items at a load of >= 0.25 items per memory cell; unlearned cues ignite < half an assembly; holds for the oldest items and after 60 s of ongoing activity. Then: the half cue regenerates the missing half of the input (content completion), and capacity grows about linearly with cell count. Also (owner, 2026-10-10): recall holds online, while learning continues, with no settle (interference, oldest-item retention, repeated-cue habituation and recovery); and item-specific recall holds on correlated inputs (exemplars with about 16 % sibling overlap, existing content-completion and specificity criteria, M = 500 and ultimately 1,000, fresh seeds). |
| 2 | sequences | After one exposure, sequences of 8 items that share items with other sequences replay in order from their first item with >= 90 % correct transitions, >= 50 sequences stored, shared items disambiguated by context >= 80 %. |
| 3 | abstraction over experience | From exemplars of unseen prototypes, the never-seen prototype is recalled more completely than the seen exemplars (prototype effect), jointly with exemplar specificity (each seen exemplar keeps its own distinguishing features), and a fixed linear readout of the network state classifies held-out exemplars with at least 2x fewer labels than on raw input or on a never-trained twin, with meaningful absolute accuracy, at predeclared hard distortion levels (including about 0.8 where appropriate), also against nearest-centroid and k-nearest-neighbour baselines. Averaging or superposition at retrieval alone does not count (owner, 2026-10-10). |
| 4 | usable behaviour | Closed loop with a reward signal (three-factor rule; scalar neuromodulator, labelled proxy): bandit reversal re-learned within 20 trials; a delayed-reward T-maze (2 s delay) at >= 90 % within 200 trials; gridworld paths within 1.5x optimal within 100 episodes; compared with tabular Q-learning and a never-trained twin. |
| 5 | model-based problem solving | After reward-free exploration, routes to a newly announced goal are generated internally (replay or preplay of learned transitions) and succeed first try on >= 80 % of held-out start-goal pairs, including a detour when a learned path is blocked; transitive inference on a 6-item hierarchy >= 85 %. |
| 6 | working memory and binding | Four or more role-filler bindings held over 10 s and queried at >= 90 %; queries on novel role-filler combinations answered without retraining. |
| 7 | scale and integration | Sharded multi-process or multi-GPU engine. Gate: a stated Stage 1-6 metric improves with size along a curve predicted before the run. Size alone is never a gate. |
| 8 | symbol-like tokens (horizon) | Grounded token sequences learned from experience. Nothing language-like is attempted before Stages 1-6 pass. |

Notes from the P2-E1 review (`review/plant2/P2-E1/`):
- Stage 1 tests whether a code assigned by random plateaus can be read back from a partial
  cue. Choosing its own representations is Stage 3's question. A Stage 1 pass is not evidence
  of thinking power.
- Capacity that grows linearly with cell count needs a signal-to-noise mechanism of its own:
  sparser codes over more inputs, recurrent completion with a stabiliser, or matched
  inhibition. No operating-point mechanism gets credit for it.

Owner's requirements of 2026-10-10 (`DECISIONS.md`):
- Bounded capacity and graceful forgetting must be shown before any claim of robust, lifelong
  episodic memory.
- Stage 2 contracts may declare fixed, activity-proportional inhibition in the memory layer as a
  stabilising element when evidence justifies it, with a matched no-inhibition comparison,
  frozen parameters and tests that it neither silences all activity nor forces an answer. No
  coefficient carries over from P2-E3.
- Familiarity-gated allocation waits until it is settled how a repeated item keeps distinct
  episode identities in different contexts.
- Every experiment is judged by whether it reduces the cognition the experimenter supplies.

The old ladder maps onto this one: old 1 (episode memory) is 1, old 2 (sequences) is 2, old 3
(structure and scale) is 7, old 4 (symbol-like tokens) is 8. Abstraction, behaviour, planning
and working memory are the north star's additions.

## Experiment log

| id | stage | mechanism | contract | result |
|---|---|---|---|---|
| P2-E1 | 1 | behavioural-timescale plasticity (BTSP), binary synapses, random plateau gating | `docs/plant2/P2-E1-btsp.md` | **FAIL** on C1 (completion 0.81-0.86 against 0.90) on 5/5 seeds; specificity and the unlearned-cue control pass. Diagnosis: no load-independent operating point (C1 0.61 at M = 250; everything ignites at M = 2,000). |
| P2-E2 | 1 | slow threshold accommodation to each cell's own mean potential (labelled proxy), J calibrated on a held-out seed | `docs/plant2/P2-E2-accommodation.md` | **PASS** on 5/5 fresh gated seeds. C1 0.945-0.985, C2 0.965-1, C3 0.99-1 at M = 250, 500 and 1,000; C5 holds. The fixed-threshold control fails (C2 <= 0.015) and the random-store control fails (C1 0). Capacity edge between 0.25 and 0.375 items per cell. The owner accepted it as a distinct mechanism (K0.14 stays closed), with its limits retained. |
| P2-E3 | 1 | one-shot feedback from memory spikes to a reconstruction layer, plus fixed activity-proportional inhibition (owner-approved element) | `docs/plant2/P2-E3-content-completion.md` | **PASS** on 5/5 fresh gated seeds; meets Stage 1's content clause and unlocks no later gate. For independent random sparse items, tested on frozen copies after a 50 s settle, the half cue regenerates the missing half of the input: joint (>= 80 % missing lines, < 10 intrusions) 0.955-1.000 at M = 250-1,000; median reconstruction error 2 of 50 lines; latency 23-28 ms. Labels (review addendum): the store is verbatim and input-supervised, keyed by a random assigned code (spiking Willshaw hetero-association); writing from the plateau set does as well or better than writing from responders; no generalisation was tested. Inhibition is needed at M = 1,000 only (matched g = 0: 0.77-0.86; passes at M <= 500; beats main at 1,500). Shuffled feedback 0.000 (a leak check). Past 0.375 items per cell the feedback store saturates rather than forgets. Exploratory, not gated: with siblings sharing about 16 % of lines, joint falls to 0.15-0.17 at M = 500 (2 seeds). |
| P2-E4 | 1 | none (a test of the P2-E2 + P2-E3 system online: recall while scheduled learning continues, no settle) | `docs/plant2/P2-E4-online-memory.md` | **FAIL** on 5/5 fresh gated seeds (all valid): ONLINE INDEX FAIL + HABITUATION FAIL + RECOVERY FAIL; Stage 1's "after 60 s of ongoing activity" clause is not met online. Scope: independent random items; the write oracle, the random key and the verbatim value are still supplied, and P2-E4 removes nothing at learning time. Online index recall (50 ms) is 0.87-0.93 at M = 500 and 0.68-0.74 at M = 1,000, including the newest items; the failures are mostly slowed retrievals (post hoc: about 0.955-0.97 within 75 ms at M = 1,000), and 86-100 % pass after a settle on the same synapses. Online content passes on every seed, but at M = 1,000 only in the online state: the online-written store is contaminated (0.82-0.905 against 0.985-1.0 for the plateau-set store on the same raster). Newly named experimenter supply: P2-E3's pass relied on separate encoding and retrieval states set by the schedule; with one state, at M = 1,000 the system gives fast access or clean content, not both (shown for the responder write, not for the architecture). Every repeatedly driven assembly habituates (graded); RECOVERY FAIL rests on one seed and load, one item short. Learning outside the write oracle mostly fails (writes during probes: 0.165-0.20 recallable). |

## Owner's rulings (2026-10-10; `DECISIONS.md`, last entry)

1. P2-E2 is accepted as a distinct mechanism. K0.14 stays closed, and P2-E2's membership in the
   same homeostatic family is recorded.
2. Capacity: the primary experiment scales input and memory populations proportionally, with
   constant absolute active inputs and assembly size. Memory-only scaling is the control.
3. P2-E3 may use fixed, activity-proportional inhibition on its readout. It needs matched
   no-inhibition and shuffled-feedback comparisons, with parameters frozen before gating.

Stage 1 also needs a predeclared **online-memory** experiment: recall while learning continues,
with no 50 s settle, covering interference, retention and repeated-cue habituation. Order:
P2-E3 (content completion), then an evaluation against the north star, then online memory and
capacity. The evaluation after P2-E3 is `docs/plant2/EVAL-after-P2-E3.md`; the owner's rulings on it
(2026-10-10) set the order: P2-E4 (online memory), then the structured-input diagnostic and,
if it fails, a correction mechanism before any Stage 2 work; capacity scaling continues.
