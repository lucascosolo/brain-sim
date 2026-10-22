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

Last reviewed 2026-10-22, after the first roadmap checkpoint (judge panel wf_848f4c6e-5b0).
See `ROADMAP.md` for which items are under active consideration. Panel cross-references added
that day: B-002 graduated to the P2-E7 contract; B-013, B-014 and B-015 added from the panel;
B-003 (the panel's E%-max variant returns only as a recurrence stabiliser, H-008's C3 warning
stands), B-006 (mismatch-gated plateau initiation needs the familiarity ruling), B-008 (the
own-versus-spurious first-spike latency split on persisted `index_cues` rows is its cheapest
test and rides every P2-E7 arm) and B-011 (the passive R_3 store rides P2-E7's baseline-arm
raster as a reported diagnostic) are updated by reference here rather than rewritten.

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

## B-002 Mismatch-gated (error-gated) forward eligibility — `graduated` (H-060; contract P2-E7 selected 2026-10-22)

**Graduation note (2026-10-22).** Selected at the first roadmap checkpoint as the next
contract, P2-E7, merging the panel's engineering and supply-reduction versions: the
prediction set is read from the frozen readout arithmetic on the encoding-phase memory
raster, the veto removes predicted eligible lines, the flip budget is conserved, and the
controls are the count-matched random drop, the history-weighted drop (E6's counts, control
only), a gate-off integrity arm and a label-oracle comparator. See `ROADMAP.md` and the
2026-10-22 `DECISIONS.md` entry. The sketch below is kept as written.

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

**Offline screen run 2026-10-22** (`~/.cache/brain-sim/plant2-research-20261022/offline/
b004_halfcue_overlap.py`; seed-44 F10/s60 items, 200 random half cues, fixed random fan-in,
k-WTA by top-k drive; a computation on item sets, not a simulation). Half-cue drive as a
fraction of the target code, own / sibling / non-sibling: raw lines 0.500 / 0.085 / 0.0125
(own:sibling 5.9); expansion n = 16,000 fan-in 20 k = 1 %: 0.516 / 0.067 / 0.025 (7.7);
n = 32,000 fan-in 50 k = 0.5 %: 0.534 / 0.059 / 0.024 (9.0); fan-in 10 k = 2 %: 0.762 /
0.235 / 0.119 (3.2). A fixed random expansion buys at most a 1.3-1.5x own-to-sibling ratio
and doubles the diffuse non-sibling drive, so the aggregate cross-talk over 999 other items
does not fall. **Reading:** the fixed-random form is not promising; the item stays open only
in its learned-competitive form (a layer that absorbs frequently co-occurring prototype lines
into few cells), which is a different and larger mechanism.

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

## B-008 Phase-of-cycle separation of siblings (temporal multiplexing) — `closed` as a standalone mechanism (2026-10-22, offline screen C)

**Closure note (2026-10-22).** Screen C of `docs/plant2/OFFLINE-SCREENS-20261022.md` (offline,
descriptive): own cells' first spikes have median 22-24 ms and 90th percentile 40-44 ms;
spurious cells' first spikes have median 66-69 ms but a 10th percentile of 36-41 ms, so no
latency cut from 20 to 50 ms reaches C1 ≥ 0.90 and C2 ≥ 0.90 together at either load on
seeds 105/106 (best joint at M = 1,000 about 0.47-0.48 at a 40 ms cut, against the recorded
0.42/0.39). A timing brake alone slides along H-067's curve. Reopen only as a component of a
recurrence contract (H-063). The sketch below is kept as written.

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

## B-013 Branch-segregated (episode-clustered) dendritic storage with an OR soma — `blocked` (owner question (a) of the 2026-10-22 checkpoint)

**Origin.** The circuit-biology, theory and contrarian primaries of the 2026-10-22 judge
panel converged on one mechanism (`ROADMAP.md`, checkpoint 2026-10-22, candidate 2; panel
sum 55-60 of 90, second behind P2-E7). Distinct from B-001: B-001 is a retrieval-side
conjunction (the soma fires only when two or more compartments agree); this is a storage-side
segregation (each plateau writes onto one fresh branch; the soma fires when any single branch
crosses the frozen threshold).

**Limitation addressed.** The same forward-index cross-talk as B-001 and B-002, located by
the panel in the point-neuron summation: a memory cell holds about five items at f_q 0.005
and M = 1,000 and sums a half cue's overlap with all of them.

**Sketch.** Each memory cell gets K = 8 branch units (the smallest power of two at or above
the expected plateaus per cell at M = 1,000), each an LIF with the frozen memory constants
and its own accommodation. The inp→branch synapses are binary at J = 1.525 mV. Each plateau
writes item x onto branch c_i mod K, where c_i is a cell-local round-robin counter; the BTSP
toggle, eligibility and coin order are unchanged, so plateau sets and coin streams stay
aligned with the point-cell arm. A branch spike drives the soma through a fixed coupling of
(v_th − v_rest) + 5 = 25 mV at delay 1, so the soma is an OR over branches. Index scoring,
R(x), the feedback write and the readout are unchanged. Labelled proxy: dendritic branches as
independent nonlinear storage subunits with branch-restricted plasticity (Poirazi & Mel 2001;
Losonczy, Makara & Magee 2008); not a claim that CA1 plateaus are branch-restricted. A pass is
a per-soma storage-capacity and specificity mechanism, not pattern separation and not a
supply reduction.

**Controls the panel named.** A dilution-equivalence control (32,000 point cells at f_q/8,
unpooled) so a pass is labelled "per-integrator episode load" if it matches; a per-synapse
branch-scrambled control; a linear-dendrite union-store point control (same synapse set,
point integration), which can fail; a B = 1 twin whose forward store must equal E3's sha256;
a reported fixed-threshold-branch arm; a reported K = 4 dose arm; a stream-3 coin-rebuild
integrity gate as a precondition for citing any offline screen.

**Why it might fail.** Branches differ from point cells in noise, not in mean offset (per-
branch accommodation cancels each branch's background), so the static count's separation may
not survive the branch firing curve; the constructive judge's rerun shows the non-own count
at 0.76 for ≥ 12 synapses, 10.1 at ≥ 10 and 32.29 at ≥ 9 (offline, judge-computed,
unrecorded). An unbounded-branch variant conflicts with bounded forgetting and is not run.

**Cheapest test.** Done 2026-10-22 as screen B of `docs/plant2/OFFLINE-SCREENS-20261022.md`
(offline static count, integrity gate passed on both seeds): non-own cells per half cue at
≥ 12 cue synapses 91.9 / 86.9 point against 0.76 / 0.62 at K = 8 (3.0 / 2.9 at K = 4); at
≥ 9, 426 / 411 against 31.5 / 29.7; own cells 20.3 of about 20 at every threshold, point and
branch alike. The separation is real at every T from 9 to 14; the branch firing point is
unmeasured. Next, if the owner admits the mechanism: one development seed (107, reserved)
under its own contract.

## B-014 Non-plateau responder depression (false-positive correction on the forward store) — `open`

**Origin.** Theory secondary of the 2026-10-22 panel (sum 56 of 90).

**Sketch.** During encoding, a memory cell that responds to the item without a plateau has
its active cue synapses depressed (an Artola-Brocher-Singer-style rule: moderate depolarisation
depresses, plateau potentiates), so the synapses that made it a false positive are removed.
Labelled proxy for depolarisation-dependent LTD. The key remains the teacher of what counts
as "correct", which the owner-intent judge flagged as a key-as-teacher conflict.

**Why it might fail.** Its author predicts it misses the bar; depression on reused cells can
cost oldest recall; the judges found its offset arithmetic wrong (the 4.70 mV write/read gap
is 3.08 synapses at J 1.525, not 3.85).

**Cheapest test.** The in-scope local-error fallback if P2-E7 dies and B-013 is not admitted:
one development seed under its own contract, E6 bars verbatim.

## B-015 Episode-clustered reconstruction store (rec-line dendritic branches per episode) — `graduated` to the P2-R3 reported replay (2026-10-22, checkpoint 2)

**Graduation note (2026-10-22).** Ranked first by both judges of the checkpoint-2 panel
(25 / 24 of 30) in its bounded form: K = 32 line-local branches filled round-robin by
episode (K fixed by the B-013 rule from M·a/m = 25), K = 1 equal to the frozen readout as a
parity gate, a per-synapse scramble control, the assigned-A store under the same rule, dose
arms K = 8 and unbounded (reported only), replayed exactly on the persisted P2-E7 seed-121
rasters of gate_off, label_oracle, candidate (reported), independent and mixed, preceded by
an intrusion-span decomposition. Contract: `docs/plant2/P2-R3-branch-reconstruction-replay.md`.
The sketch below is kept as written.

**Origin.** Contrarian secondary of the 2026-10-22 panel (sum 61 of 90, third overall; the
only proposal aimed at H-046).

**Sketch.** Each continuation write puts R(x)'s synapses onto a fresh dendritic branch of
every eligible rec line instead of the single Willshaw matrix; at readout a rec line
regenerates when one stored episode's writers dominate on one branch, so contamination from
other episodes' writers no longer sums. Labelled proxy: branch-clustered plasticity on the
reconstruction side. Reported replay first on persisted rasters (P2-R2b artifacts and
P2-E7's baseline-arm raster), with a parity gate (the one-branch form must equal the frozen
readout bit for bit) and a shuffled-compartment control.

**Why it might fail.** Branch count per rec line grows with load (bounded forgetting);
the writer set R(x) is itself contaminated at F10, so clustering contaminated writers may
regenerate siblings' content on their own branches.

**Cheapest test.** The exact replay on the persisted P2-R2b artifacts; no seed.

## B-016 Graded prediction-error weighting of the conserved flip budget (P2-E8 candidate) — `open`; screen F survived on 2026-10-22 (AUC 0.858; flip ratio 0.44 steady state, 0.75 ramp), contract P2-E8 in drafting with predictions set from screens F and E′

**Origin.** Engineering primary of the checkpoint-2 panel (2026-10-22; judges 20 / 22 of
30, second overall); the graded continuation of B-002 after P2-E7's informative
FEASIBILITY FAIL (`docs/plant2/RESULTS-P2-E7.md`; screen E).

**Limitation addressed.** The two parts of the P2-E7 residual: the late-episode leak (about
one prototype line in six escapes the ≥ 1-spike prediction and is written at p ≈ 0.84) and
the slow onset (a family's first four to thirteen members written in full). Both are
invisible to a binary spike criterion and should show as subthreshold depolarisation of
the line's reconstruction unit.

**Sketch.** P2-E7's learn_one with only the per-line flip probability changed: run the same
lockstep reconstruction readout on the 75-tick encoding raster (its spike set must equal
P2-E7's predict_set every episode); for each eligible line read the peak depolarisation
d_j over ticks 0-74; w_j = 0 if the line spiked (the binary veto nested), else
w_j = 1 − clip(d_j / 20 mV, 0, 1); p_j = min(1, λ·w_j) with λ the exact water-filling
solution of Σ_j p_j = 0.5·|E| (no bisection tolerance; cap flagged); coins exactly as
`btsp_update`. No new constant: 20 mV is the rec layer's v_th − v_rest. Labelled proxy:
graded mismatch-scaled plasticity in the comparator view (circuit-level proxy). Controls that
can fail: graded_shuffled (the episode's w multiset permuted over unpredicted lines, stream
(seed, 37, k)) and history_rank (the same multiset assigned by E6 usage, most-used line the
smallest w), plus the P2-E7 binary rule on the same seed, gate_off (p = 0.5, forward SHA
equal to the baseline's), the label oracle, independent and mixed non-regression,
surplus-only as a reported arm.

**Why it might fail.** No separation under late inhibition (AUC near 0.5); drive tracks
writer count (a load marginal: history_rank matches); recall cost on near-predicted own
unique lines; independent perturbation (the rule changes veto-free episodes); the early and
other-family floor (about 2.4 spurious per cue) leaving C2 at .82-.87; a self-defeating
teacher.

**Rescue question.** Both judges: no P2-E7 constant is retuned; the rule functionally
softens the spike criterion, so it is admitted as "a different rule with a reason" only with
the binary same-seed comparator, a kill-only offline screen, a fresh seed and explicit
acceptance (owner question (f)).

**Cheapest test.** Screen F (`docs/plant2/OFFLINE-SCREENS-20261022c.md`), zero seed: AUC of
d_j separating missed prototype lines from unpredicted unique lines on the persisted
candidate trajectory; counterfactual expected prototype flips per plateau cell under
binary, graded and surplus-only; the ramp on gate_off. Kill if AUC < 0.70 over episodes
501-1,000 or the graded/binary flip ratio > 0.6. Then seed 123 (registered) under its own
contract.

## B-017 Error-gated eligibility taught by an unselective twin store — `closed` (2026-10-22; screen F recorded gate_off's own coverage over episodes 101-500 as 0.513 against the proposal's own kill of 0.595)

**Origin.** Theory secondary of the checkpoint-2 panel (judges 14 / 18 of 30, last).

**Sketch.** Break the self-taught fixed point by reading the prediction from an unselective
twin feedback store that does not depend on the student's cross-talk, with an earliest-spike
truncation to an exact budget bound.

**Why closed.** The skeptic judge computed from the persisted gate_off gate log (the
baseline trajectory's own gate, which the twin teacher equals) a prototype coverage of 0.513
over episodes 101-500, below the proposal's own kill of 0.595, and noted that the twin
teacher starts outside P2-E7's kill envelope (precision .685, non-prototype predicted .291
over 501-1,000). Two changes in one contract (teacher swap plus truncation). Screen F
appends the coverage line as a recorded offline result; the item then closes for good.
