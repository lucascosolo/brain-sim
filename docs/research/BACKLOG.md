# Speculative research backlog

Ideas that are not yet ready for a contract. An item here has no evidence behind it and
claims none; it is a direction with a sketch of the cheapest test that would tell us whether
it deserves a contract. An item graduates to `HYPOTHESES.md` when it gets a falsifiable
statement, a named control and a predeclared bar, and it is closed here with a pointer when
that happens or when a reason to drop it is found. Nothing here is described as new to
science; where a mechanism has a literature, the label says so, and the computational
proxy is ours.

Status values: `open`, `graduated` (to an H-id), `closed` (with reason), `blocked` (on an
owner ruling or a prerequisite).

Last reviewed 2026-10-22. See `ROADMAP.md` for which items are under active consideration.

## B-001 Conjunctive dendritic gating of memory cells (two-or-more-compartment AND) — `open`

**Limitation addressed.** Forward-index cross-talk on correlated items: a sibling assembly's
cells are recruited by the hot prototype lines alone (P2-E5 C2 0.435-0.515 at M = 1,000;
P2-E6 and P2-R2 both reduce but do not remove it).

**Sketch.** Each memory cell gets K (2-4) dendritic compartments; a cell's forward synapses
are assigned to compartments at creation by a fixed hash of the input line. A compartment is
a leaky integrator with its own threshold that emits a brief plateau-like event; the soma
fires only when at least two compartments are active within a few ms. An assembly cell whose
item drives ~50 lines spread over all compartments passes; a sibling cell driven by ~10-20
shared prototype lines concentrated in one or two compartments does not. The nonlinearity
is conjunctive rather than a single higher threshold, so a weakly driven own cell that is
driven *broadly* still fires. Nothing in the learning rule changes; the plateau key is still
assigned. Labelled proxy for dendritic NMDA/plateau nonlinearities (Major, Larkum & Schiller
2013; the BTSP substrate itself is dendritic).

**Why it might fail.** Compartment assignment is random, so hot lines can spread over
compartments too; the gain may be small at K = 2 and recall may drop at K = 4. Interacts
with threshold accommodation (which compartment adapts?). It is a retrieval-side fix and
does nothing for the feedback write unless the write also reads compartment events.

**Cheapest test.** Replay-only: the forward store from P2-E5 seeds 44/45 rasters is fixed;
re-simulate the memory layer with compartmentalised cells on the identical input streams and
score C1/C2 at M = 500/1,000 against the one-compartment baseline and a control with the
same total threshold but no conjunction. One development seed; under an hour.

## B-002 Mismatch-gated (error-gated) forward eligibility — `open`, owner-approved family

**Limitation addressed.** The same cross-talk, at its source: hot lines accumulate synapses
into every family member's assembly. P2-E6 bounded this with a presynaptic-history budget and
got C2 .500 → .895 on one seed, short of the .90 bar.

**Sketch.** During encoding, an input line is BTSP-eligible only if the reconstruction layer
did not regenerate it from the memory layer's response to the item before the write (the
"error-correcting write" the owner approved as a research direction, DECISIONS 2026-10-10,
ruling 4). Prototype lines of a known family are predicted, so they stop being written after
the first few members; unique lines are always written. Keep E6's fixed flip budget so the
expected synapse count per plateau cell is unchanged and recall is not traded for
specificity. Labelled proxy for mismatch- or novelty-driven plasticity; the comparator is a
circuit-level proxy, not a claim about CA1 physiology.

**Why it might fail.** Early family members are written in full, so the first ~5-10 items of
each family still create hot-line fan-out; recall of a half cue that is mostly prototype
lines falls; the rec layer's own contamination (P2-E5 Part B) makes the error signal noisy
at the start, which is exactly why P2-E6 chose presynaptic load first.

**Cheapest test.** A development seed of the P2-E6 driver's structure with the eligibility
rule swapped, scored against the frozen E6 bars and the E6 candidate itself.

## B-003 Fast activity-proportional inhibition inside the memory layer — `open`, owner-authorised as a stabiliser

**Limitation addressed.** Spurious responders at retrieval; possibly also the online
encoding/retrieval conflict (P2-E4), because a population-level brake would let the threshold
accommodation sit lower.

**Sketch.** One interneuron-pool proxy driven by memory spikes delivers -g_m x J to every
memory cell one tick later (the P2-E3 element, now on the memory layer). This is a soft
k-winners-take-all: the most strongly driven assembly suppresses weakly driven siblings.
Required by the ruling: a no-inhibition and an inhibition-only control, a shuffled/degree-
matched control, frozen parameters, and checks that it neither silences everything nor forces
an answer. It is not learning and gets no capability credit on its own.

**Why it might fail.** The own assembly is ~20 cells; siblings' partial responses may fire
*earlier* than own cells on some cues and win the race; the 50 ms index window leaves little
room for a settling competition.

**Cheapest test.** Replay-only on persisted rasters is impossible (the inhibition changes the
memory raster), so a small forward simulation on one P2-E5 development seed, g_m grid read as
an explicitly optimistic diagnostic, frozen value chosen on seed 44 and confirmed on 45.

## B-004 Expansion-and-competition layer before the memory layer (dentate-like pattern separation) — `open`

**Limitation addressed.** Correlated inputs are never decorrelated before indexing; the
independent capability review names an activity-driven separation mechanism as the strongest
next direction if structure sensitivity replicates.

**Sketch.** A sparse layer of ~16,000 cells with fixed random fan-in from the 4,000 lines and
strong lateral inhibition (k-WTA proxy) produces a much sparser code whose pairwise overlap
between siblings is lower than the input's (expansion plus thresholding reduces overlap,
Marr 1971; Babadi & Sompolinsky 2014). The memory layer indexes that code instead of the raw
lines. Optionally, the layer learns with a competitive Hebbian rule so that frequently
co-occurring prototype lines are absorbed into few cells. The plateau key is still assigned.

**Why it might fail.** A fixed random expansion separates only up to a limit set by the
sparsity; the feedback (content) path then has to map from the memory layer back to raw
lines, which the current one-shot Willshaw write can still do; but 16,000 cells quadruple the
simulation cost; and a learned competitive layer is a second mechanism in the same contract
unless split.

**Cheapest test.** Offline: compute sibling overlap statistics of the expanded code on the
P2-E5 generator's items for several sparsities, with no simulation; if overlap does not fall
below the independent-item level, drop the idea.

## B-005 Inhibitory plasticity that balances hot lines (E/I balance by learned inhibition) — `open`

**Limitation addressed.** Hot prototype lines deliver disproportionate drive; both E6 and R2
show line load matters beyond family grouping.

**Sketch.** An inhibitory pool receives the same input lines; its synapses onto memory cells
follow a symmetric inhibitory STDP that drives each memory cell toward a target rate
(Vogels et al. 2011 is the labelled proxy). Lines that fire in many episodes build up more
inhibitory weight, so their net drive is normalised without touching the excitatory store.

**Why it might fail.** It is a homeostat, and the audit's lesson from the recovered plant is
that homeostats on a seconds timescale erase one-shot writes; the owner's rule is that no
homeostat acts on written synapses. This one acts on inhibitory synapses only, but it still
changes the operating point under load and may collide with threshold accommodation.

**Cheapest test.** Simulation on one development seed; read whether C1 survives and C2
rises; compare against B-003's fixed inhibition, which is the simpler alternative.

## B-006 Self-generated keys: plateaus elicited by the network, not drawn by the experimenter — `blocked` (owner deferral)

**Limitation addressed.** The largest remaining experimenter supply: the random plateau
assembly. Every review lists it first.

**Sketch.** Replace `stream(seed, PLATEAU)` by a plateau rule driven by the memory cell's own
dendritic drive during the episode (for example the K-compartment events of B-001, or the
R_3 continuation signal measured in P2-E5 Part C), with a novelty gate so that a familiar
item does not re-allocate. Then a key is content-dependent and, for siblings, partly shared,
which is what the prototype effect of Stage 3 needs and what Stage 1's specificity bar
penalises.

**Why blocked.** The owner deferred familiarity-gated allocation until it is settled how a
repeated item keeps distinct episode identities in different contexts (DECISIONS 2026-10-10),
and the P2-E1 review notes that choosing its own representations is Stage 3's question. A
contract here needs an explicit ruling.

## B-007 Replay-based consolidation that redistributes hot-line fan-out offline — `open`

**Limitation addressed.** Cross-talk accumulated during learning.

**Sketch.** In quiet periods the network replays stored items (driven by their own stored
index) and applies a heterosynaptic rule: a line that drives many assemblies during replay
has its weakest synapses depressed and the item's unique lines potentiated, keeping each
cell's total synapse count fixed. Labelled proxy for sleep-dependent synaptic renormalisation
(Tononi & Cirelli 2014), used here as targeted pruning of promiscuous lines.

**Why it might fail.** This is the recovered plant's failure mode in a new coat: a rule that
depresses used pathways after the fact (SPEC 8.49). Old memories are the first to lose
synapses. It needs the replay to be self-generated, which the current system cannot do.

**Cheapest test.** Offline on a saved store: apply the renormalisation as a matrix operation
and replay the P2-E5 rasters through the new store; if specificity does not rise without a
recall loss on the oldest 100 items, close the item.

## B-008 Phase-of-cycle separation of siblings (temporal multiplexing) — `open`, unconventional

**Limitation addressed.** Siblings compete for the same 50 ms window.

**Sketch.** Impose a 50 ms oscillatory inhibitory bias on the memory layer; cells fire at the
phase where their drive first exceeds the moving threshold, so strongly driven own cells
fire early and weakly driven siblings late or not at all (phase precession as a labelled
proxy). The index readout keeps the 50 ms window but a second, earlier reading (first 25 ms)
is predicted to be far more specific than the full window. Cheap because the 25 ms recall
is already recorded (`recall[25]` in `p2_e1_btsp.evaluate`).

**Why it might fail.** The existing data may already show that spurious responders are not
systematically later than own cells; if first-spike latency does not separate them, the idea
is dead before any simulation.

**Cheapest test.** Offline on persisted P2-E5 rasters: compare first-spike latency
distributions of own versus spurious responders. One script, minutes.

## B-009 Two learning states, chosen by the network: encoding versus retrieval mode — `open`

**Limitation addressed.** The online encoding/retrieval trade-off the owner judged most
important (DECISIONS 2026-10-11): P2-E3's pass relied on separate states set by the schedule.

**Sketch.** A scalar state variable driven by a novelty signal (the mismatch of B-002, or the
fraction of input lines regenerated) sets the memory layer's operating point: high mismatch
lowers the plateau/eligibility gate and raises inhibition (encode), low mismatch raises the
gate and lowers inhibition (retrieve). Labelled proxy for acetylcholine-modulated
encoding/retrieval switching (Hasselmo 2006). The schedule's boundaries would then be
produced by the network, removing one experimenter supply.

**Why it might fail.** It stacks on a mismatch signal that does not exist yet (B-002) and on
memory inhibition (B-003); it is a third mechanism. The P2-E4 online failure may be
dominated by slowed retrieval, which a mode switch does not speed up.

## B-010 Sparser plateau sets with more memory cells per item at the same budget — `open`

**Limitation addressed.** Capacity scaling and the 0.25 items/cell edge; the P2-E1 review's
note that linear capacity growth needs a signal-to-noise mechanism.

**Sketch.** A pure parameter-structure question: with assembly size held at ~20 and f_q
scaled with n, does C2 at a fixed load fall or hold as n grows (the owner's capacity rule:
scale input and memory proportionally, memory-only as the control)? No mechanism; this is
the predeclared capacity-scaling experiment the rulings already require.

**Why it is here.** Not speculative; parked until Stage 1's structured clause has a
mechanism, because scaling a failing system measures the failure's scaling.

## B-011 Reading content from the memory layer's own continuation activity (R_3) as a live writer — `open`, owner-ruled "reported replay first"

**Limitation addressed.** Feedback-store contamination (P2-E5 Part B, P2-E4 Part D).

**Sketch.** The P2-R1 replay showed that writers chosen by at least three continuation spikes
produce a much cleaner settled store (duty/1,000 content .995 versus .205 inherited). A live
R_3 write is the deployment of that result. The owner's ruling: reported replay first, which
is done; live deployment needs a new contract, must not be stacked with another unproven
mechanism, and is credited as removing no supply (it recovers the assigned key).

**Why it might fail live.** Online, continuation activity is noisier (P2-E5 online arm fires
less); the settled replay figure overstates the live one by construction.

## B-012 A second, slower trace on forward synapses (two-timescale binary weights) — `open`

**Limitation addressed.** Graceful forgetting and old-item retention, which no current
mechanism addresses; BTSP's binary toggle depresses old synapses at p = 0.5.

**Sketch.** Each forward synapse carries a fast binary weight (today's) and a slow tag that
is set when a synapse has survived several episodes; BTSP's depression step applies to
untagged synapses only. Old memories become harder to overwrite; capacity saturates
gracefully instead of randomly. The recovered plant tried a two-timescale weight against a
homeostat (SPEC 8.13); here the opponent is the toggle itself, which is a different question.

**Why it might fail.** Protecting old synapses is exactly what makes hot-line fan-out
permanent; it works against B-002 and B-007. Needs the capacity experiment (B-010) to measure
anything.
