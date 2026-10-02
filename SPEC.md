# brain-sim: architecture spec (v0, 2026-09-11)

Written by an LLM. That is a constraint on the design: no LLM is called at runtime, ever, for any
purpose. Every behaviour comes from the spiking network and its plasticity rules, or it is
absent and the UI says so. Every mechanism below is marked as biology-derived, a published
model, or a proxy chosen by me. Numbers marked "initial" are tuning guesses; the kill tests are
the arbiter, not my confidence.

## 1. Hardware and stack

Measured on this PC: Intel i5-12600KF, 16 threads, 31 GB RAM. A GTX 980 Ti is present but the
NVIDIA driver is in a mismatched state and the card is Maxwell-era; the sim is **CPU-only,
single-threaded NumPy** and stays that way until a kill test proves a wall. System Python is
3.14 with no NumPy installed; Stage 0 creates a `uv` venv (Python 3.12 if 3.14 wheels are
missing, checked at build time, not assumed).

Stack: Python, NumPy, FastAPI + uvicorn (WebSocket), static HTML/JS with Canvas 2D. No build
step, no npm, no Brian2/NEST (neither supports live structural rewiring cheaply). Numba is the
one escape hatch if the per-tick Python overhead blocks Stage 1; not used in Stage 0.

## 2. The model

### 2.1 Units: leaky integrate-and-fire with adaptive threshold

Discrete time, `dt = 1 ms` sim time. Per neuron: membrane `v` (mV), threshold `theta`,
`t_last_spike`, traces `x_pre`, `y_post`, rate estimate `rate` (EMA, tau 2 s).

```
v     <- v_rest + (v - v_rest) * exp(-dt/tau_m) + I_syn + I_inj + noise
theta <- theta_0 + (theta - theta_0) * exp(-dt/tau_theta)
spike if v >= theta and t - t_last_spike > t_ref
on spike: v <- v_reset, theta <- theta + d_theta, x_pre += 1, y_post += 1
```

Initial: `tau_m 20 ms, v_rest -70, v_reset -65, theta_0 -50, t_ref 2 ms, tau_theta 150 ms,
d_theta 1.5 mV`. Dale's law: a neuron is E or I; sign of all its outgoing weights is fixed.
E:I = 4:1 in every region.

**Intrinsic noise is sub-target (proxy, decided 2026-09-11).** `noise` is Gaussian current per
tick, a proxy for unmodelled background input, with a per-region `sigma` calibrated so that a
synaptically isolated neuron of that region fires at **no more than 0.3 x its E rate target**
(`r_iso <= 0.3 r_target_exc`; measured, not assumed; kill test K0.7). Below that ceiling a
neuron cannot satisfy its rate setpoint without synaptic input, so the rate-driven rules in
2.4 and 2.5 act on synapses rather than being satisfied by noise. The first Stage 0 build used
4.6 mV, which let cells meet target with zero E input; the prune rule then stripped them bare
and scaling equalised the survivors (K0.3 and K0.4 failed as one mechanism). The drive that
closes the gap comes from 2.1b and from recurrent input.

### 2.1b Spontaneous afferent activity (proxy)

In wake, each `sense` unit fires as an independent Poisson process at `SENSE_SPONT_HZ`
(5 Hz; 50 Hz was tried on 2026-09-11 before inhibition had a controller and is not an
acceptable value: spontaneous afferent activity must not be what holds cortex at its setpoint), implemented as a per-tick Bernoulli draw that forces a spike. This stands in
for spontaneous peripheral activity that drives developing sensory pathways (retinal waves,
spontaneous thalamic activity); the biology is real, the rate is a proxy. It is gated by the
same `sense_gated` variable that drops injected input, so in sleep `sense` is silent and
cortex runs on recurrence and intrinsic noise. `set_sense_spont(hz)` changes the rate at
runtime; K0.1's silent condition sets both it and `sigma` to 0.

Honesty note on "asynchronous": the neuron-vector update is a dense O(N) NumPy op each tick.
At N <= 10^4 that costs microseconds and is not where the state lives. The event-driven
guarantee is enforced at the synapse level: **a synapse is touched only when a spike traverses
it or when its post-neuron spikes.** Arrays are laid out so the neuron update can switch to
lazy analytic decay over the active set if N grows past ~10^5.

### 2.2 Synapses and delivery

Delta synapses: on delivery, `v[post] += w` (mV; negative for I sources). Integer delay
1..8 ms per synapse, drawn at creation from distance. Spikes are placed into a ring buffer of
`D_max + 1` buckets keyed by arrival tick; a tick delivers only its bucket. Cost per tick is
`O(spikes * fan_out + delivered_events)`.

### 2.3 Synaptic plasticity: pair-based STDP with soft bounds, gated by a scalar

Song, Miller & Abbott 2000 trace form; weight-dependent depression after van Rossum, Bi &
Turrigiano 2000. E->E and E->I synapses only in Stage 0. I-source synapses are fixed.
Untimed or paired population presentation is not a use-dependent contrast test for pair STDP
plus scaling: the rule reads spike order, not use, and scaling holds the rest weight where the
rule's multiplicative LTD needs a ~3.6:1 causal excess (section 7, K0.3, 2026-09-12). The
population contrast clause is retired as a Stage 0 kill test (owner decision, 2026-09-12); the
two-neuron test is the Stage 0 claim about this rule, and whether a used pathway can get
stronger is Stage 1's first question (section 8, S1.0).

```
traces: x_pre[j], y_post[i] decay with tau_plus = tau_minus = 20 ms
on delivery of j->i at tick t:  w -= g * A_minus * y_post[i] * w          (LTD, multiplicative)
on post spike of i:  for each incoming j->i:  w += g * A_plus * x_pre[j] * (w_max - w)   (LTP, soft-bound)
clip w to [0, w_max]
```

`g` is a global plasticity gain (the only "neuromodulator" in Stage 0): 1.0 in wake, 0.3 in
sleep. Measured 2026-09-11 (K0.3 population): repeatedly presenting a `sense` pattern
**depresses** its `sense->ctx` synapses relative to the others (ratio 0.91 from birth, 0.71
after a 120 s warm-up). This is the rule as published: with `A_minus > A_plus`, a presynaptic
input firing at ~50 Hz that does not itself cause postsynaptic spikes is net depressed (Song,
Miller & Abbott 2000). Each `ctx` cell receives ~2 synapses from a 40-unit pattern
(`sense->ctx` k_in 10 of 200), so the pathway cannot drive its targets and never earns LTP.
Open decision for the owner: convergence of the sense pathway, not the rule. Initial `A_plus 0.01, A_minus 0.012, w_max 2.0 mV (ctx), 3.0 mV (hpc)`. Per-region
rates: hpc 5x faster than ctx (the fast binder). LTD is applied at arrival time, LTP uses the
somatic pre-trace ignoring delay; error <= 8 ms, accepted.

**Measured 2026-09-11 at `I_GAIN = 2.5`, 120 s warm-up, then pattern A 20x:** K0.3 population
ratio 0.70 (baseline before presentation 0.99). The patch is loud this time, not quiet:
pattern-A sense cells fire at 49.6 Hz under the 1.9 mV drive and the ctx patch at 10.1 Hz
during a presentation (on this pre-fix commit; the section 7 table is post-fix and reads
12.5 Hz for the patch at the same drive), so the pathway now excites its target (the 3.0
round suppressed it to 1.3 Hz). These two rates were first recorded as 61 Hz and 14.6 Hz from a scratch measurement
whose window definition was not kept; re-measured on the same commit with the section 7
definition (spikes of the 40 pattern-A cells, and of the ctx patch cells, over the 20 x
300-tick windows) the same network, K0.3 ratio identical to the last digit, reads 49.6 and
10.1 Hz. The section 7 numbers are the ones of record.
The depression has two named causes, both in this rule as written: (1) after wake scaling
the sense->ctx weights sit at 0.95 `w_max` on average (33 % exactly at the ceiling), so
soft-bound LTP has ~5 % of headroom while multiplicative LTD acts on the full weight; (2) at
50 Hz presynaptic the pair rule is in its rate-depression regime (the equilibrium above,
`A- > A+`). Threshold unchanged. The next question is not the gain: it is either the
presentation drive (50 Hz is not a sensory rate), scaling's ceiling, or the rule's rate
dependence, and each is a spec decision for the owner.

**Measured 2026-09-11, second pass (scaling frozen in sleep and gated to used input, drive
1.3 mV):** ratio 0.81 with the weights at 0.755 `w_max` and 0.75 % at ceiling before the
presentations. Scaling's ceiling and the 50 Hz drive are both gone and the protocol still
depresses at every amplitude from 1.9 to 1.0 mV (section 7 table). What remains is the
rule's rate dependence: the rest weight scaling settles on is above the pair rule's
uncorrelated fixed point, so a presentation that does not produce a large causal-pair
excess is depressed. Reported, not patched.

**Measured 2026-09-11, third pass (imposed pairing, section 7 K0.3):** with post spikes
forced 10 ms after the synchronous A volleys (60 pairings, the two-neuron test's count),
pairing is established (1.25:1 causal excess in the pulse windows, peak at +8..+12 ms;
control 0.97:1) and the A inputs still net-depress: LTP +0.485 against LTD -0.657 and
scaling -0.286 per surviving synapse; ratio 0.927 (control 0.870). The attributed
contributions point at the pair rule's LTD/LTP asymmetry at 0.75 `w_max`, the next volley's
anticausal pairs, and down-scaling under the pulses; the "pathway too weak" diagnosis is
retired. This protocol produced temporal structure and did not reach the required
selectivity; it does not show that controlled pairing fails in general. Whether Stage 0
keeps pair STDP and retires this kill test, or a later Stage 1 decision changes the
plasticity rule, is the owner's call. Decided 2026-09-12: Stage 0 keeps pair STDP and
retires the population clause; the rule decision is Stage 1's (section 8, S1.0).

### 2.4 Homeostasis (three timescales)

**Measured 2026-09-11: scaling saturates the net during sleep.** Sleep gates `sense`, the
ctx rate error sits near 0.7 for the 20 s phase, and scaling at +7 %/s takes 98.7 % of the
sense->ctx weights (93.5 % of all E onto ctx) to `w_max` by the end of the first sleep. At
the wake transition the returning input lands on a maxed net: at `I_GAIN` 3.0, 2.75 and
2.25 a third of ctx fires in one tick and the net runs at 20 Hz for a second; at 2.5 it is
a 9.5 Hz transient. Scaling against a gated input is the same windup the structural rule
had, one level down. Superseded later the same day by item 2 below (scaling frozen in
sleep and gated to used input): measured on seeds 1-3, 0.8-6.7 % of sense->ctx sits at
`w_max` before wake and the transition peaks at 1.6-2.5 % of ctx with zero deaths. The
numbers in this paragraph are the pre-fix state, kept so the K0.2 window's silence about
t = 81 s is not mistaken for stability; K0.2 still does not look there.

1. Fast: adaptive threshold above (spike-frequency adaptation, Gerstner et al. textbook form).
2. Slow, every sim-second in the slow sweep: **synaptic scaling** (Turrigiano 1998, proxy form).
   Excitatory incoming weights of neuron i are multiplied by `1 + eta_s * (r_target - rate_i)/r_target`,
   `eta_s` initial 0.02 (measured 2026-09-11: 0.1 needed for the count to settle), clipped to `[-0.1, 0.1]`. `r_target`: ctx E 4 Hz, ctx I 8 Hz, hpc E 1 Hz, hpc I 6 Hz.
   **Scaling must not touch a synapse whose input is gated or silent** (decided 2026-09-11;
   the owner's words were "must not raise", and both clauses below are symmetric: a gated or
   silent input is neither raised nor lowered). Two clauses, one rule: (i) **frozen in sleep**: the scaling step does not run while
   `phase == "sleep"`; (ii) **used input only, in wake**: the factor is applied to an
   incoming E synapse only if its presynaptic neuron fired at least once in the sweep that
   just ended (the per-neuron spike count the sweep already computes). The gate is one
   sweep's count, not the EMA rate the factor uses, so a synapse is scaled only in the
   fraction of sweeps in which its presynaptic cell spikes: for a Poisson pre at rate `r`
   that is `1 - exp(-r * 1 s)`, 0.98 for a ctx E cell at its 4 Hz target and 0.63 for an
   hpc E cell at 1 Hz, so the effective `eta_s` on hpc E input is about two thirds of the
   nominal. Stated, not compensated; a per-region `eta_s` tune has to account for it. Why
   (ii) alone was
   not enough (measured 2026-09-11, seeds 1-3, 100 s): with the gated `sense` inputs
   excluded, the same sleep-time rate error (0.7, because the drive is gated, not because
   the cell's recurrent inputs are weak) pushed 48-60 % of all E synapses onto ctx to
   `w_max` by the end of the first sleep, and the wake transition seized exactly as before
   (34-36 % of ctx in one tick, 29-54k synapses pruned). The rate error during a gated phase
   is not a homeostatic signal for any synapse of the cell, so the whole scaling step is
   frozen for the phase. The freeze is scoped to scaling: structural plasticity still runs
   in sleep off the same error, held only by the 2.5 anti-windup latch, and whether it
   should is an open decision, not settled here. With (i) the transition is benign on all three seeds (1.6-2.5 % peak, zero
   deaths, ctx 4.6-4.8 Hz for a second, 4-13 % of E at `w_max` at wake). Clause (ii) keeps
   the rule honest in wake for an input that is silent rather than gated. Proxy:
   homeostasis on used input, in the phase whose setpoint applies. The classic form of
   synaptic scaling (Turrigiano 1998) is cell-wide and multiplicative; input-specific forms
   are reported but disputed, and sleep's own synaptic rule (SHY: down, not up) is Stage 1's,
   so this is a labelled proxy, not a claim. Use-it-or-lose-it pruning still sees every E
   synapse in every phase, so a silent weak synapse still dies.
   **Coverage gap, recorded 2026-09-12 (scaling-hold experiment, branch `k03-scaling-hold`
   at 42e93ea, rejected, not adopted).** Holding scaling for a latched group passed K0.2,
   K0.6, K0.11 and its own K0.12 tests and left the determinism digest unchanged, while ctx
   E's mature wake rate sat at 2.4 Hz on seed 1 and 1.5 Hz on seeds 2-3 against the 4 Hz
   setpoint, every group latched from 20 s and none released through 120 s: no controller
   acted on the rate at all, and no check said so. The current stability checks therefore
   do not establish adequate homeostatic recovery. K0.2 asserts a band ([1, 15] Hz), a
   burst guard and a floor over one window; none fails when a rate is held 40-60 % under
   its setpoint by an integrator that has stopped. Before the next homeostasis design
   decision (rest weight vs the pair rule's fixed point, the latch's scope, or any
   replacement for scaling), a recovery criterion has to be written and pinned first: for
   example the time for a group's EMA rate to return within a stated band of its setpoint
   after a step in drive, and a bound on the fraction of window sweeps a group may spend
   latched with a same-signed error. Until it exists, "passes K0.2/K0.6/K0.11" is not
   evidence that homeostasis works, and the scaling-hold result is the case that shows it.
3. Slowest: structural plasticity (2.5), driven by the same rate error.

### 2.5 Structural plasticity: grow and prune under a rate setpoint

Model: Butz & van Ooyen 2013 (synaptic-element formation driven by a calcium/activity
setpoint). Simplified to incoming elements only; runs in the slow sweep, once per sim-second.

For each neuron i with error `e_i = clip((r_target - rate_i)/r_target, -1, 1)` and current
in-degree `k_i`:

- **Grow** if `e_i > 0`: create `n_i ~ Poisson(G(age) * e_i * k_target_i)` new incoming synapses,
  where `k_target_i` is the sum of `k_in_mature` over the projections into i's region (60 for
  `ctx`, 50 for `hpc`). Corrected 2026-09-11 from `round(G * e_i * k_i)`: the current in-degree
  `k_i` as the base made zero an absorbing state and let over-connection feed more growth,
  and `round()` truncated small mature rates to nothing. Same rule, unbiased draw. Presynaptic
  candidates are drawn from populations allowed by the projection table, with probability
  `exp(-d^2 / 2 sigma^2) * (1 + beta * act_j)` where `act_j` is the candidate's slow activity
  trace (proxy: activity-dependent synapse formation; the biology is real, this rule is mine).
  New weight `w_init = 0.15 * w_max`, delay from distance. No duplicates, no autapses.
- **Prune** any E synapse with `w < w_prune = 0.05 * w_max` (use-it-or-lose-it, proxy). If
  `e_i < 0`, additionally remove `min(k_i, Poisson(P(age) * |e_i| * k_i))` of the weakest
  incoming E synapses.
- **Inhibitory synapses follow the same controller with the sign flipped, held to the E/I
  motif** (decided 2026-09-11; a proxy cousin of the E rule above, not a new theory and not a
  second controller). Per neuron: `kE_i`, `kI_i` alive incoming E and I counts;
  `motif_i = EI_MOTIF * kE_i` with `EI_MOTIF = 0.25` (the 4:1 wiring ratio);
  `deficit_i = max(0, motif_i - kI_i)`, `excess_i = max(0, kI_i - motif_i)`. The rate error
  `e_i` owns direction and magnitude; the balance error only shapes the I side:

  ```
  below target (e_i > 0):  grow E   Poisson(G(age) * e_i * k_target_i)
                           prune I  min(excess_i, Poisson(P(age) * e_i * excess_i))   weakest by |w|
                           grow I   Poisson(G(age) * e_i * deficit_i)
  above target (e_i < 0):  prune E  min(kE_i, Poisson(P(age) * |e_i| * kE_i))         weakest by w
                           grow I   Poisson(G(age) * |e_i| * (EI_MOTIF * k_target_i + deficit_i))
  ```

  Pruning of I is confined to the excess over the motif, so a neuron cannot reach its rate
  setpoint by deleting inhibition, and I is restored toward the motif whenever the rate error
  is non-zero, so I tracks E as E grows. Inhibitory candidates are drawn from the inhibitory
  neurons of the neuron's own region only (interneurons are local), with the same distance
  kernel and co-activity bias as E candidates. I weights are fixed in magnitude (`I_GAIN`-
  scaled draw at birth, as in the initial wiring); the use-it-or-lose-it rule does not apply
  to them. Why the sign flip: with excitation regulated and inhibition unregulated, growth
  cannot reach the setpoint and winds up to `S_max` (measured 2026-09-11: 400k, 99 % of E
  weights at `w_max`). Why the motif: without it the controller reached the setpoint by
  stripping inhibition to a median in-degree of 3 against 12 (measured 2026-09-11, E:I synapse
  ratio 22:1). The initial wiring's cross-region inhibitory sources are a Stage 0
  simplification; the rule prunes them and replaces them locally over time.
  **Measured 2026-09-11 with the motif held** (kI/kE 0.22, E:I synapses 4.4:1): ctx E plateaus
  at ~3.5 Hz against its 4 Hz setpoint, `e` stays positive, E grows with I following, and
  the store fills at 72 sim-s (598k). With inhibition kept at the motif and `I_GAIN = 3`
  (I weights 3x the E draw, chosen under the old 4.6 mV noise regime) and I cells at twice
  the E rate target, recurrent drive is net inhibitory, so adding synapses at the motif
  ratio cannot close the last 0.5 Hz and the integral action never stops. A presented patch
  landing ~15 synapses per ctx cell lowered those cells to 1.3 Hz (feedforward inhibition
  through the same nerve), so K0.3 read 1.001. Decision 2026-09-11: `I_GAIN` is lowered by
  calibration, not by hand (protocol and result in section 7, after K0.10), and the
  controller gets anti-windup (next bullet). **Measured 2026-09-11 at `I_GAIN = 2.5` with
  anti-windup, 240 s, seed 1:** alive 301k (1 s), 402k (10 s), 426k (30 s), 415k (60 s),
  323k (90 s, after the wake transition), 333k (120 s), 328k (180-240 s); peak 427k, 71 % of
  the store, clamp never fired; change over 190-220 s 0.0003 %. Latch: every group by
  11-13 s, released only at the wake transition (rates spike above target, sign flips) and
  re-latched by ~95 s. End state ctx: I in-degree median 36 vs motif 26 (kI/kE 0.34, above
  the motif because the wake transition pruned E), E:I synapses 2.95:1; hpc: 22 vs 17,
  3.2:1. E weights at `w_max`: 36 % of E onto ctx at 120 s in wake, 99 % at 240 s in sleep.
  ctx E 3.5 Hz, ctx I 7.0 Hz, hpc E 0.7-0.9 Hz, hpc I 4.5 Hz in the late wake windows.
- **Anti-windup** (decided 2026-09-11; conditional integration, the textbook clamp on an
  integrating controller, not a mechanism of the model). The grow and error-driven prune
  terms above are one integrator on synapse count; without a clamp an unreachable setpoint
  fills the store (measured above: 598k at 72 s). Two conditions hold it, both evaluated
  inside `structural_update` at the start of every call, so a synthetic `e` exercises them:
  1. **Stall latch, per group.** Groups are (region, E|I): `sense_E`, `ctx_E`, `ctx_I`,
     `hpc_E`, `hpc_I`; a group whose target is zero never latches (its required progress is
     `-inf`). Each group keeps the last `WINDUP_WINDOW_SWEEPS + 1` values of its
     mean clipped error `e_q`; `A` is the mean of the first `WINDUP_WINDOW_SWEEPS // 2` of
     them and `B` the mean of the last `WINDUP_WINDOW_SWEEPS // 2` (block means, so the
     compare sits above the sweep-to-sweep noise and spans the conduct and rate-EMA lag).
     The group latches when the window is full, `sign(A) == sign(B) != 0`, and
     `|B| > |A| - thr_q`: the integrator ran for a whole window and the error did not fall
     by `thr_q`. While latched, every rate-error term of the group's neurons is held, both
     signs: E growth and I-excess pruning below target, E pruning and I growth above target.
     The deficit (motif restoration) term and the use-it-or-lose-it rule are never held.
     Why both signs (measured 2026-09-11 with growth alone held): per-neuron errors straddle
     zero, 5-30 % of ctx E neurons sit above target at any sweep, their error-driven pruning
     ran on while their regrowth was held, and the count ratcheted down 2-3k/s (381k at 8 s
     to 280k at 60 s), every death an error-driven prune and none use-it-or-lose-it. A held
     integrator is held in both directions. Release is on sign flip only: the group's mean
     error crossed zero (a mean of exactly zero is not a crossing), so the held direction is
     no longer the error's direction; the window restarts. Why not release on a worsening error: sleep gates `sense` and lifts
     the ctx error from 0.15 to 0.75, and a worsening-release rule grew 40k synapses against
     a gated input in the first sleep (measured 2026-09-11), which is windup. Limitation,
     stated: a held group whose rate never crosses its target does not grow again, so it
     does not repair after a perturbation; that is a Stage 1 question.
     `thr_q = max(WINDUP_MIN_PROGRESS, WINDUP_NOISE_SIGMAS * sqrt(alpha / (2 - alpha)) / sqrt(r_target_q * n_q))`
     with `alpha = RATE_EMA_ALPHA`: the second term is the Poisson noise floor of a group's
     mean 1-s rate under the EMA (`ctx_E` 0.019 so the 0.020 floor applies, `ctx_I` 0.027,
     `hpc_E` 0.084, `hpc_I` 0.069, in units of clipped error). Measured 2026-09-11: the
     sweep-to-sweep standard deviation of `ctx_E`'s mean error at its plateau is 0.018,
     three times the Poisson figure, because network fluctuations are correlated across
     neurons; on the block difference the threshold is about 1.5 sigma of the measured
     noise. A false latch near the setpoint costs nothing and is released by the next zero
     crossing; a false latch far from it leaves the group where scaling and threshold
     adaptation put it, which is the conservative side. Why per group and not per neuron:
     one neuron's EMA rate has a standard deviation near 1 Hz against a genuine climb of
     ~0.07 Hz/s, so a per-neuron test sits under the noise floor. Corollary: inside `thr_q`
     of the setpoint the integrator is held, a deadband. Measured 2026-09-11 (every gain):
     the latch fires at 8-11 s, inside the immature transient, because the 1-2 s
     over-correction (45k pruned, I grown) carries the error away from target for the next
     sweeps while growth runs; by the rule that is growth not moving the rate toward
     target, and the record after the latch bears it out for ctx: with the integrator held
     from 8 s, scaling alone took ctx E from 2.3 Hz to the same 3.4-3.5 Hz plateau that
     550k synapses reached without anti-windup.
  2. **Store clamp.** No growth of any kind while `n_alive >= WINDUP_CAP_FRAC * S_max`.
     `WINDUP_CAP_FRAC = 0.9` is the same bound K0.4 asserts is never reached, so the clamp
     cannot satisfy K0.4; it turns an abort (`synapse store full`) into a measured failure.
  Both states are engine attributes (`growth_halted[group]`, `store_clamped`) and frame
  fields, and `stats` counts group-sweeps held (`stall_halt_sweeps`: one per group per sweep
  while latched) and sweeps clamped (`store_clamp_sweeps`).
  Growth room is `len(free) + (S_max - s_used)`, the number of ids `add_synapses` can hand
  out; the previous `S_max - n_alive` ignored ids withheld during the same update and was
  what raised at 72 s.
- **Development schedule**: `G(age) = P(age) = base * (1 + 9 * exp(-age / 60 s))`, `base 0.05`.
  Initial wiring is built at **2x the mature in-degree** (immature, overconnected), so the first
  minutes are dominated by pruning, and turnover cools by 10x over the first few sim-minutes.
  This is compressed development, not embryology.

**Birth and conduction are separate events.** A new synapse gets `born = t` and
`conduct = t + CONDUCT_DELAY_TICKS` (initial 1000, one sweep; proxy for the functional
maturation delay of nascent spines). Until `conduct <= t` it is alive, counted, visible as a
birth, and **absent from the delivery index**: the CSR rebuild includes only synapses with
`alive & (conduct <= t)`, so it receives no LTP and carries no current. Stage 1's replay must
not treat a nascent synapse as a usable weight. Initial wiring and `Network.tiny` synapses are
born conducting (`conduct = 0`). Dead synapses are zeroed immediately and dropped at the
rebuild. The rebuild runs every sweep for every network; `homeostasis = False` skips only the
scaling and structural rules.

### 2.6 Regions and wiring (Stage 0 scaffold)

Each region is a 2D sheet; neurons get random `(x, y)`; local connection probability decays
with distance (proxy for columnar locality).

| region | role | N (E+I) | plasticity |
|---|---|---|---|
| `sense` | sensory relay / future text-nerve; driven by injected patterns | 200 E | none onto it |
| `ctx` | cortex-like recurrent E/I net, slow learner | 1600 + 400 | slow STDP, scaling, structural |
| `hpc` | hippocampus-like sparse binder, fast learner, strong inhibition | 320 + 80 | fast STDP, structural |

Projections: `sense->ctx`, `ctx<->ctx` (EE, EI, IE, II), `ctx->hpc`, `hpc<->hpc`, `hpc->ctx`.
Total N = 2600. Each projection carries its own distance-kernel width.

**The text-nerve is convergent and topographic** (decided 2026-09-11). `sense->ctx` gives each
`ctx` neuron 30 inputs (was 10) drawn with a tight kernel (`sigma 0.12`, others 0.25), so a
`ctx` neuron listens to a compact patch of `sense`. The four fixed patterns are the 20 % of
`sense` units nearest each quadrant centre, not scattered random units, so a pattern is a
spatially coherent activation on the nerve and drives the `ctx` patch under it. Why: with 10
scattered inputs a 40-unit pattern landed ~2 synapses per `ctx` cell, could not cause a
postsynaptic spike, and was therefore depressed by pair STDP (K0.3 ratio 0.71, 2026-09-11).
A prosthetic nerve that cannot drive its target is not a pathway. Mature in-degree target:
`ctx` 80, `hpc` 50; immature 2x; S_immature ~ 360k; `S_max = 600k` (capacity, 11 MB; raised
from 400k so the immature init has headroom, not a guard). Sparsity in `hpc` comes from a low `r_target` and strong I gain, not a
hard-coded k-WTA. If that fails the Stage 1 sparsity test, an explicit k-WTA proxy is the
fallback and needs your OK.

### 2.7 Sleep, replay, consolidation (CLS)

Stage 0 ships the state machine and the flag; **Stage 1 ships the mechanisms.** Listed here
because the data layout must not need a migration.

Wake/sleep schedule: fixed `60 s wake / 20 s sleep` sim time, plus manual toggle, plus (Stage 1)
early sleep when `hpc` has bound more than K new patterns since the last sleep.

In sleep (Stage 0): `sense` input gated off; plasticity gain `g = 0.3`. That is all Stage 0 does
in sleep, and the UI says so.

Stage 1 mechanisms (theory: McClelland, McNaughton & O'Reilly 1995; Kumaran et al. 2016):

- **Two-timescale ctx weights** (model: Ziegler et al. 2015; Benna & Fusi 2016 in spirit).
  `ctx` synapses gain a slow weight `w_s`. STDP acts on the fast weight `w`. Always:
  `w -> w_s` with `tau_f = 300 s`. **Only during sleep**: `w_s += eta_c * (w - w_s)`. Effective
  weight is `w`. `hpc` has no `w_s`; its single weight decays toward `w_init` with `tau 200 s`,
  so the binder forgets on its own once cortex has taken over.
- **Metaplasticity** (model-derived proxy): STDP amplitudes on a `ctx` synapse are scaled by
  `(1 - w_s / w_max)`. Consolidated synapses are harder to overwrite.
- **Replay**: in sleep, noise drive to `hpc` rises; its recurrent attractors complete stored
  patterns (proxy for sharp-wave ripple reactivation; SWRs are real, this mechanism is a
  stand-in); `hpc->ctx` gain doubles in sleep (Hasselmo's ACh mode-switch model, proxy scalar).
  `ctx` also receives noise so its own older attractors reactivate. Interleaving of old and new
  is therefore emergent, and K1.3 tests whether it actually happens.
- Not included: synaptic downscaling in sleep (SHY, Tononi & Cirelli; disputed and not required).

## 3. Proxy vs biology

| mechanism | status |
|---|---|
| LIF with adaptive threshold | proxy for conductance-based neurons |
| delta synapses, integer delays | proxy |
| Gaussian noise current | proxy for background synaptic bombardment |
| pair STDP with traces, soft bounds | published model fitted to slice data; whether it is the in-vivo rule is disputed |
| synaptic scaling toward rate setpoint | biology-derived, simplified to a multiplicative sweep |
| structural growth/prune on rate setpoint | published model (Butz & van Ooyen 2013), simplified |
| co-activity bias on synapse formation | proxy, my rule |
| 2x-overconnected immature init + cooling turnover | proxy for developmental overproduction and pruning |
| global plasticity gain `g` | proxy for neuromodulatory systems |
| two-timescale weights, sleep-only consolidation | published models; the sleep-only gating is a design choice |
| replay via noise-driven attractor completion | proxy for SWR replay |
| E/I 4:1, Dale's law, 2D locality | biology-derived, coarse |
| `sense` as text-nerve | no biological analog; a prosthetic and labeled as such in the UI |

Absent on purpose: thalamus, basal ganglia and reward, dendrites, conductances, layers, glia,
neurogenesis, gap junctions, engineered oscillations. Nothing in the spec claims they are
there.

## 4. PC scale limits

| quantity | Stage 0 live | ceiling on this PC (estimate) |
|---|---|---|
| neurons | 2,600 | ~10^5 before lazy neuron update is required |
| synapses | 156k-312k, cap 400k | ~2 x 10^7 by RAM (18 B/synapse + indexes); throughput caps earlier |
| synaptic events/tick at 5 Hz mean | ~800-1,600 | ~10^5 at ~1 ms wall/tick |
| target speed | >= 0.5x real time in the UI, uncapped in tests | |

Per-tick cost is Python overhead (~30 NumPy calls) plus O(events). Slow sweep once per 1000
ticks is O(S) and rebuilds two CSR indexes (~10-30 ms at 300k). Memory at `S_max`: ~7 MB
synapse store, ~3 MB indexes, ~125 KB neuron arrays.

## 5. Data structures and the tick

Neurons: struct-of-arrays, length N: `region u8, is_exc bool, x,y f32, v f32, theta f32,
t_last_spike i32, x_pre f32, y_post f32, rate f32, act f32, spike_count u32`.

Synapses: struct-of-arrays, capacity `S_max`: `pre i32, post i32, w f32, delay u8, alive bool,
born i32, conduct i32`; free list of dead ids. Stage 1 adds one `w_s f32` column. Two CSR indexes over alive
synapses, `out` by `pre` and `in` by `post`, rebuilt in the slow sweep. Event ring: `D_max+1`
lists of int32 arrays of synapse ids.

Per tick `t`:

1. Pop ring bucket `t`: synapse ids `d`. Mask `alive`. `I_syn = bincount(post[d], w[d], N)`.
   LTD on `d`. Count `syn_touched += len(d)`.
2. Dense neuron update (2.1) with injected currents and noise. Spiking set `s`.
3. For `s`: reset, threshold bump, traces. Outgoing ids via `out` CSR, appended to ring
   buckets by delay. LTP over incoming ids via `in` CSR; `syn_touched += len(in ids)`.
4. Record spikes `(id, t)` into the frame buffer.

Every 1000 ticks (slow sweep): rate EMA and `act` update, synaptic scaling, structural
grow/prune, free-list maintenance, CSR rebuild, birth/death lists for telemetry.

`syn_touched` per tick is exported. It is the runtime witness that no dense weight pass exists.

## 6. Process split

- `brainsim/` (sim core): pure NumPy, no I/O, no server imports, deterministic under a seed.
  API: `step(n)`, `inject(ids, amp, ticks)`, `present(pattern_id, ticks)`, `set_sleep(bool)`,
  `frame()`, `inspect_neuron(id)`, `region_stats(name)`, `layout()`.
- `brainsim/worker.py`: `multiprocessing.Process` running the engine. Command queue in, frame
  queue out (maxsize 4, drop-oldest; cumulative counters ride in every frame so totals stay
  exact). Steps in batches of 50 ticks, paces to the requested speed factor.
- `server/app.py`: FastAPI. Serves `ui/`, one WebSocket `/ws` carrying frames down and commands
  up. Nothing in the server computes anything about the network.
- `ui/`: Canvas 2D. Draws only what a frame contains. No random numbers in the JS. If frames
  stop, the page shows "stale" with the age.

**One source of truth, enforced mechanically.** The variable that makes the network behave a
certain way is the variable the UI shows, with no re-derivation on the way:

- Every value on screen is a field of a frame or a query reply produced by `telemetry.py`
  from engine state, or a formatting of one. The JS does no arithmetic on frame fields, keeps
  no client-side accumulators that produce new quantities, and duplicates no constant from
  `params.py`. Plotting the history of a field (a sparkline, a raster) is rendering; computing
  a rate from two fields is not.
- Derived quantities are derived at the source and shipped: `born_per_s`, `died_per_s` (the
  last slow sweep's counts, which cover exactly one sim-second), `g` and `g_struct` (the
  plasticity gain and the current developmental structural rate that the sweep actually used),
  `sense_gated` (the boolean the engine uses to drop sense input), and `wall_ratio` from the
  worker, which is the only process that knows wall time.
- `telemetry.FRAME_KEYS` is the single declaration of the frame; `make_frame` asserts its
  output has exactly those keys. `tests/test_ui_truth.py` parses `ui/app.js` for every
  `msg.<key>` / `f.<key>` / `frame.<key>` access and asserts each is in `FRAME_KEYS` or a
  declared reply key, so a field the UI reads but the engine never emits fails the suite; and
  it asserts that a frame's `phase`, `g`, `g_struct`, `sense_gated`, `n_syn_alive`, `t`,
  `age_s` equal the engine's own attributes at the moment of emission.
- The phase label is the engine's `phase` string, upper-cased. The status bar shows `g` and
  `g_struct` next to it, so "sleep" and "immature" are visible as the numbers that drive the
  rules, not as captions.

Frame (JSON, one per 50-tick batch while running, heartbeats with `ticks = 0` while paused):
`t, phase, age_s, wall_ratio, g, g_struct, sense_gated, ticks, n_syn_alive, syn_born_total,
syn_died_total, born_per_s, died_per_s, spike_total, syn_touched_mean, born_count, died_count,
regions{name: {rate_hz, spikes_per_tick}}, spikes[[id, dt]...] (capped at 4000 with a truncated
flag), born[[pre,post]...], died[[pre,post]...], growth_halted, store_clamped, seq,
stim_active, stim_events, run_id`.

UI (third pass, 2026-09-11, built from the approved mockup in `mockups/index.html`): two tabs.
**Observe** (default): the network map (three region panels, E and I cells as dots, spikes as a
150 ms display glow labeled as such; synapse sample and birth/death flashes are optional layers,
both off by default), a pinned control bar (run/pause, step, speed with max, sleep now) that
shows the requested value next to the confirmed one, the Stimulate panel (present A-D, custom
injection into a dragged patch), a compact command-feedback list with plain-language outcomes
and a details disclosure carrying the raw evidence, an activity timeline on simulated time
(last 30 s observed; heartbeats add nothing; missed frames are drawn as gaps), and an inspector
drawer (neuron: 500-tick `v` trace, `theta`, EMA rate labeled as updated per sweep, in/out
degree, top-10 E + top-10 I incoming labeled as a subset; region: rate, synapse counts,
histograms). **Diagnostics**: every frame key, per-region rasters, raw replies, the message log,
the rule equations, the config reply, the client display preferences, "How evidence
reconciles", and the recorded results from `ui/stage0_results.json` (hand-maintained, dated,
per-commit, with carried-forward failures marked as not rerun). "Text in" and "Readout" remain
absent: no text pathway or readout population exists before Stage 2.

Command evidence (one source of truth extended to commands): every command carries a `req`
that the server prefixes with the socket's `client_id`; the worker answers with a `result`
(`rejected` with a reason, `accepted` at tick `t`, or `executed` for steps) and every message
carries the worker's `run_id`. Acceptance is not execution: a stimulus accepted while paused
has delivered no current. Execution is observed from the engine's own bookkeeping
(`stim_active` snapshot and `started`/`ended` events in frames, a bounded `stimlog` of the last
64 stimuli), never inferred from a planned end tick or from absence in a snapshot. The client
never resends on a timeout ("unconfirmed" is a display state), discards evidence from another
`run_id`, and shows history that has expired from the stimlog as unknown, not as ended.
Client display preferences (timeline window, unconfirmed timeout, glow and flash durations,
history sizes) live in `ui/app.js` under `DISPLAY`; every simulator fact the page shows comes
from the `config` and `layout` replies.

## 7. Stage 0: deliverable and kill tests

Deliverable: `python run.py` opens `localhost:8000` on a live 2,600-neuron network with visible
spikes, synapses being born and dying, a wake/sleep flag with its two real effects, injection
and pattern presentation. No language, no readout, no chat.

Kill tests, headless, seed fixed, `pytest -m kill` total under 10 minutes wall:

- **K0.1 event cost**: at nominal drive, mean `syn_touched` per tick < S/10 and wall per tick
  with zero input (silent net) <= 0.25 x wall per tick at nominal. Fail = the tick is dense.
- **K0.2 stability**: 120 sim-s. Over the wake window 100-120 s: ctx E mean rate in [1, 15] Hz,
  no tick with > 20 % of ctx spiking, no region under 0.2 Hz. Fail = runaway or dead net. The
  window sits after the developmental transient (`tau_dev` 60 s; structural rates are still
  2.7x mature at 100 s) because the first minute is an underdamped structural oscillation by
  design (measured 2026-09-11: 76k-300k synapses, hpc 0.1-0.3 Hz at 45 s). The early 40-60 s
  window is measured and reported in the assertion message, never hidden and never asserted.
  Pre-authorised fallback if it fails: Vogels et al. 2011 inhibitory STDP, added only after
  you say yes. Coverage gap (2026-09-12, see 2.4): a candidate that stopped rate control
  entirely (scaling held while latched; ctx E 1.5-2.4 Hz mature, latch never released) passes
  this test; K0.2 checks a band over one window, not recovery toward the setpoint.
- **K0.3 STDP**: two-neuron net, pre 10 ms before post x60 gives `dw > 0`; reversed gives
  `dw < 0`. **That two-neuron test is the Stage 0 claim about this pair rule and stays green.
  The population contrast clause below is retired as a Stage 0 kill test (owner decision,
  2026-09-12): it is not a Stage 0 requirement. The driver `tests/k03_pairing.py` and its
  pytest wrapper `test_k0_3_population_imposed_pairing` are kept as the record and as an
  optional run (`pytest --record -k k0_3_population`; the `record` marker deselects it
  otherwise); the 1.2 threshold and the result of record are unchanged. Result of record
  (deedcc8, recorded at 72f4145): valid protocol, ratio 0.861 (control 0.994); the
  causal:anticausal excess on the tracked A synapses was 1.04-1.13 against the ~3.6:1 that
  the multiplicative LTD needs at the 0.75 `w_max` rest weight. Untimed or paired population
  presentation is not a use-dependent contrast test for pair STDP plus scaling; whether a
  used pathway can get stronger is Stage 1's first question (section 8, S1.0).** Population,
  **weak-current pairing protocol (fourth pass, 2026-09-12, the last population protocol
  run; engine a140bc0 unchanged; `tests/k03_pairing.py`):** seed 1, exactly
  120,000 ticks of warm-up under the default schedule (one sleep at 60-80 s inside). Targets
  `ctx_A` as before (ctx cells with more than half of their alive incoming `sense` synapses
  from A, frozen before stimulation). Trial: present topographic patch A for 300 ticks at
  `PATTERN_AMP_MV` and, issued at the same tick, inject a weak sustained current into every
  `ctx_A` cell for the same 300-tick window (`Engine.inject(ctx_A, 0.2 mV, 300)`; 0.2 mV per
  tick, steady-state depolarisation 4.1 mV), then 700 ticks off; 20 trials, t = 120,000 to
  140,000, wake. The amplitude was fixed from spike statistics before any weight was read
  (rule W, `~/.cache/scratch/brainsim-k03-weak/protocol.md`): the largest of 0.05, 0.1, 0.2,
  0.3, 0.5 mV whose current-alone `ctx_A` E rate inside the window stays within 2x the
  no-current rate (6.55 vs 3.49 Hz; 0.3 mV gives 7.74, 0.5 mV 12.0) with no tick above 20 %
  of ctx. Measurement: mean alive `sense_A->ctx_A` weight over mean alive off-patch
  `sense->ctx_A` weight onto the same targets, raw; threshold >= 1.2 unchanged. Control:
  the same current schedule with no presentation, from a deepcopy of the same warm state.
  Predeclared validity, all met: every A cell spiked inside every window (1.00); 95 % of
  `ctx_A` cells spiked inside each window (control 88 %); window pair counts on the tracked
  A synapses causal > anticausal with the lag-histogram peak at +2 ms (post follows pre);
  largest single-tick ctx fraction 7.3 % (control 2.9 %); attribution residuals 0, pair
  counts cross-checked. **Result: ratio 0.861 (control 0.994); fails >= 1.2; red at 72f4145,
  and the clause was retired as a kill test the same day (above).**
  Pair counts on the tracked A synapses (10,785 at baseline): full interval causal
  1,107,369 vs anticausal 1,058,445 (1.046:1; trace-weighted 434,482 vs 383,762, 1.13:1);
  inside the current windows 996,029 vs 960,463 (1.037:1), per trial 1.01-1.07, causal lag
  median 24-25 ms; off-patch synapses 178,380 vs 171,983. Control: 286,187 vs 268,566
  (1.066:1). Per surviving A synapse: LTP +0.352, LTD -0.628, scaling -0.123 (A weights
  0.750 -> 0.572 `w_max`; off-patch 0.753 -> 0.664; control A 0.735, scaling +0.086). Rates
  inside the windows: A 26.6 Hz, `ctx_A` E 9.2 Hz and I 18.6 Hz (control 5.7 / 10.6 Hz).
  Reading: the current did what was asked (post spikes follow the pre input at 2 ms) but
  the input fires at 26.6 Hz for the whole window and the targets at 9-19 Hz, so pairs of
  both orders are dense and the causal excess is 4-13 %, against the 3.6:1 that the
  multiplicative LTD at 0.75 `w_max` requires; the extra post spikes add LTD on every one of
  the 26.6 Hz A deliveries faster than they add LTP, which is why the ratio is below the
  presentation-alone K0.13 arm (0.922). No constant was changed, nothing was retried, and
  the bar stays at 1.2. **Untimed presentation is not a use-dependent contrast test for this
  rule:** pair STDP moves a weight by the trace-weighted order of pre and post spikes, not by
  how much a pathway is used; presenting a pattern without controlling post timing (the
  K0.13 arms, the untimed protocols in the section 7 table) measures the rate covariance of
  the two populations and their habituation, and cannot report use-dependent contrast for
  this rule one way or the other.
  *Previous protocol (third pass, 2026-09-11), imposed pulses; superseded as the protocol on
  2026-09-12, results kept as history and still reproducible by overriding the three pulse
  constants:* seed 1, exactly
  120,000 ticks of warm-up under the default schedule (one sleep at 60-80 s inside). Targets:
  `ctx_A`, the ctx cells (E and I) with more than half of their alive incoming `sense`
  synapses from pattern A, frozen before stimulation, never selected by weight or by
  response. Stimulus: 20 trials of pattern A for 300 ticks at `PATTERN_AMP_MV`, then 700
  ticks off, unchanged. **Intervention**, labelled as such: a postsynaptic current pulse of
  30 mV for 1 tick to every `ctx_A` cell through `Engine.inject()` at 39, 69 and 101 ticks
  after each presentation onset, 10 ticks after the three synchronous A volleys measured on
  the warmed network (peaks 29, 59 and 91 ticks after onset; after ~110 ticks the A spikes
  are spread uniformly at ~25 Hz), the same lag and the same 60 pairings as the two-neuron
  test; the lag exceeds every A->ctx_A delay (1-4 ticks), so a paired pre spike is delivered
  before the induced post spike. The schedule was fixed before any ratio was examined and is
  not tuned; no other amplitude, lag, count or repetition is tried. Noise, spontaneous sense,
  scaling, structural turnover and the phase schedule all run; nothing is reset, forced or
  frozen; the trials end at t = 140,000, where the schedule enters sleep, and the final phase
  is reported as the engine leaves it. Measurement: mean alive `sense_A->ctx_A` weight over
  mean alive `non-A sense->ctx_A` weight, both groups onto the same fixed targets, raw, not
  normalised by the baseline; threshold >= 1.2 unchanged. Restricting both groups to the
  same targets changes the old all-ctx measurement (A vs non-A onto every ctx cell), which
  is still computed and reported for continuity. Baseline synapses are tracked by (slot,
  pre, post, born) because killed slots are reused; births, deaths and the weight change of
  survivors are reported separately from the primary endpoint over all alive synapses.
  Spike timing is recorded completely for the sense cells and `ctx_A`, and pairing is judged
  from measured spikes, never from commanded injection times: lag = t_post - t_pre (somatic;
  LTD is applied at delivery, which adds the 1-4 tick delay), window +-50 ms, causal 1..50,
  anticausal -50..-1, counted per baseline synapse; and the accumulated LTP, LTD and
  scaling contributions per synapse are attributed exactly per tick from the engine's own
  order (LTD at delivery with the post trace as it stood at the end of the previous tick;
  LTP at the post spike with the pre trace after that tick's decay and before the pre's own
  increment) and checked against the realised weight change, because raw pair counts do not
  explain a trace-based, weight-dependent rule. That order is the implementation's and is
  not corrected in this pass. Control: from an identical copy of the warmed state, the same
  targets, pulse count, amplitude, duration and trials, with the three pulse times per trial
  drawn uniformly in the 300-tick window with spacing >= 5 ticks from an independent RNG
  (seed 20260911, never the engine's). The control has no acceptance threshold; it is
  reported, and if it undermines the reading of a nominal pass, that is said. A pass
  demonstrates a response to imposed pairing, not autonomous sensory learning; nothing here
  claims that every untimed stimulus must depress or that externally controlled timing is
  necessary in general. Test: `tests/test_rules.py::test_k0_3_population_imposed_pairing`;
  protocol and instrument in `tests/k03_pairing.py` (test-side; the engine is unchanged and
  its RNG is never drawn from). **Result (2026-09-11, seed 1):
  pairing established, ratio fails.** `ctx_A` = 368 cells (287 E, 81 I); baseline 10,785
  A->ctx_A and 6,644 non-A->ctx_A synapses, both at 0.75 `w_max` with < 1 % at ceiling.
  Pulses fired 80 % of `ctx_A` per pulse tick (min 35 %); the largest single-tick ctx
  fraction in the run was 18.0 % at t = 123,101, a pulse tick (control 18.4 %, also a pulse
  tick), under K0.2's 20 % guard but a synchronous burst by construction. All 20 trials ran
  in wake (g 1.0); the run ends at t = 140,000 in sleep, sense gated, g 0.3, as the schedule
  says. Timing (A inputs, pulse-window pairs): the lag histogram peaks at +8..+12 ms, the
  intended relationship, with a second, anticausal peak at -18..-22 ms from the next volley
  30 ms later; causal 841,843 vs anticausal 675,740 (1.25:1; trace-weighted 1.55:1); median
  causal lag 17 ms because a volley's pre spikes spread over ~15 ms. Control: 691,494 vs
  714,840 (0.97:1), flat histogram, so the control did disrupt pairing. Non-A inputs are
  symmetric in both arms (83k vs 86k; 77k vs 83k). Weights: primary ratio 0.995 -> **0.927**
  (control 0.870; survivors-only 0.929 / 0.871; the retired all-ctx measure reads 0.783 /
  0.764). A fell 0.750 -> 0.539 `w_max` (control 0.514); non-A fell 0.753 -> 0.581 (0.591);
  nothing at ceiling at the end. A did not increase, and non-A did not fall relative to A:
  no selectivity by either route. Per surviving A synapse (w units, `w_max` 2.0), exactly
  attributed with zero residual: LTP +0.485 (control +0.416, so pairing raised LTP by 17 %),
  LTD -0.657 (control -0.663), scaling -0.286 (control -0.271); non-A: LTP +0.092, LTD
  -0.182, scaling -0.291. Turnover: A 915 deaths, 63 births (births at 0.25 `w_max`);
  non-A 509 deaths, 17 births; survivor and all-alive ratios agree to 0.002. Reading: with
  the weights at 0.75 `w_max`, one anticausal pair removes 3.7x what one causal pair adds
  (multiplicative LTD against soft-bound LTP), so a 1.25:1 causal excess still nets
  depression, and the volley 30 ms after each paired one supplies the anticausal pairs;
  scaling adds as much depression again, because the pulses and the drive hold `ctx_A` E
  at 11.5 Hz during presentations, above its 4 Hz target. Timing moved the ratio in the
  expected direction (+0.058 over the control) and did not come near 1.2. This
  imposed-timing protocol produced temporal structure but did not reach the required
  selectivity. It is not evidence that all controlled pairing fails: one schedule, one lag,
  one amplitude, 60 pairings, at this rest weight. No constant was changed and no rule
  added; the next decision belongs to the owner. Per-trial timing: the
  pulse-window causal:anticausal ratio for A is above 1 in every one of the 20 trials (min
  1.11, max 1.40), the per-trial median causal lag is 12-26 ms, pulses fire 69-87 % of
  `ctx_A` per trial, and the largest single-tick ctx fraction per trial is 14.8-18.0 %; the
  control's per-trial ratio ranges 0.57-1.42 around 1. Control timing, judged from spikes
  and not from weights: pulse-window causal:anticausal 0.97 against the pairing arm's 1.25,
  histogram peak/median 1.44 (at -48 ms) against 5.91 (at +8 ms).
  What the instrument verifies, and what it does not: the zero non-sweep residual checks
  the per-tick LTP and LTD attribution against the realised weights, given the engine's own
  delivery bucket; it is not an independent check of the whole instrument. Independently:
  (i) the scaling contribution is predicted from the sweep's own formula (post-EMA rate,
  +-0.1 clip, used-input mask from the instrument's own recorded spikes, wake only) and
  matches the sweep-tick residual exactly (max discrepancy 0.0 in both arms), so the
  sweep-tick attribution is checked, not assumed; (ii) the pair counts are recounted by
  brute force on 40 A and 40 non-A synapses through a separate code path and agree bin for
  bin; (iii) the delivery mask, read from the engine's own ring bucket, is compared with a
  prediction from recorded spikes and delays: one disagreeing tick of 20,000 in the pairing
  arm (t = 128,002, one slot, two ticks after a sweep: the engine fixes membership at the
  pre spike while the prediction uses the index at delivery), none in the control; (iv) the
  closure residual is, once sweep-tick residuals are booked to scaling, the signed sum of the
  non-sweep residuals and adds nothing beyond (i) and the per-tick check. Not independently
  verified: the traces (the instrument reads the engine's `x_pre` and `y_post` rather than
  recomputing them from spikes) and the LTP/LTD formulas themselves, which the check
  reproduces rather than tests.
  *Superseded (2026-09-11):* the untimed protocol (present A 20x, no injection) and its
  diagnosis "if it fails the pathway is too weak, not the rule". Its results stay as history:
  at 1.3 mV, ratio 0.81 (pattern cells 26.7 Hz, ctx patch 10.1 Hz against 5.5 Hz elsewhere,
  pattern-A weights 0.755 `w_max` before with 0.75 % at ceiling, 0.616 after), and at every
  drive and duration tried (section 7 table) the untimed protocol depressed with headroom on
  the weights. Further untimed amplitude or duration sweeps are closed.
  **Brief-volley diagnostic (2026-09-12, alongside K0.3; engine 83e44ad unchanged;
  `tests/k03_brief_volley.py`, protocol written and the schedule fixed from spike
  recordings before any weight was read).** Question: is the shortfall the protocol's
  uncorrelated load (the 300-tick presentation's ~100 rate-driven pre spikes and two later
  volleys per trial) or the rule's leverage at the rest weight? Same warmed seed-1 state,
  targets, instrument, threshold, pulse (30 mV x 1 tick at 39 ticks after onset) and pulse
  count (60); only the presentation is shortened to its first volley: `present(0, 40)` at
  `PATTERN_AMP_MV`, 60 trials of 333 ticks (19.98 simulated s, t = 120,000-139,980, all in
  wake, 19 sweeps; the reference has 20 x 1000). The 40-tick duration is the trough between
  the first volley (peak 29 ticks after onset, tail to 38) and the second (from 55), taken as
  the first zero of the 3-tick moving A-spike sum after the first peak; the literal
  per-tick minimum (tick 35, a single-tick zero inside the tail) was recorded and not run.
  Control: same presentations, one pulse per trial at a uniform offset in [0, 333) from
  the K0.3 control RNG (20260911). Delivered: 99.5 % (min 95 %) of the A cells spike inside each
  drive window (1.09 spikes per cell, min 0.98); outside it A runs at 4.98 Hz, the
  spontaneous rate; 153 pre spikes per A cell over the interval (reference ~230); pulses
  fire 74 % of `ctx_A` (min 50 %; control 88 %); ctx_A E 24.7 Hz inside the drive
  windows and 1.6 Hz outside (4.4 Hz over the trial, against 4.0 target). Timing (A, from
  spikes): pulse-window causal:anticausal 4.39 (reference 1.25; control 1.06), peak +11 ms,
  median lag 10 ms, per-trial minimum 2.64; over the FULL interval the trace-weighted
  causal:anticausal is 3.02 (reference 1.39): the anticausal trace sum fell 59 % and the
  causal sum 10 %. Weights: primary ratio 0.995 -> **1.048** (control 0.946; survivors
  1.048 / 0.946; all-ctx measure 0.879 / 0.833); FAILS the unchanged 1.2 threshold; gap to
  the control +0.102 (reference +0.058, scaling-hold candidate +0.070). A fell 0.750 ->
  0.641 `w_max` (control 0.573), non-A 0.753 -> 0.612 (0.606): the ratio rose only because
  A fell less than non-A; nothing potentiated in absolute terms and nothing is at ceiling.
  Attribution per surviving A synapse, zero residual, scaling prediction exact: LTP +0.355,
  LTD -0.364, scaling -0.226 (control +0.179 / -0.334 / -0.229; non-A +0.080 / -0.168 /
  -0.223). STDP is therefore neutral on A (-0.009; reference -0.172, control -0.155), and
  the group-blind scaling term (ctx_A E held 0.4 Hz over target by the pulses and the
  volleys) is now the largest term on both groups. Turnover: A 362 deaths / 32 births
  (reference 915 / 63), non-A 401 / 16. Burst: largest single-tick ctx fraction 16.5 %
  (control 18.2 %), pulse ticks, under K0.2's 20 % guard. Instrument checks: non-sweep
  residual 0, scaling-prediction residual 0, pair-count cross-check ok, two ring/spike
  disagreements in the pairing arm and one in the control, all within `D_MAX` ticks of a
  sweep boundary. Predeclared validity: all clauses pass except V4b, which required the
  control's full-interval trace ratio in [0.8, 1.25] and reads 1.37: the brief volley evokes
  the network's own `ctx_A` response 1-5 ticks after the volley peak (52 % of `ctx_A` in
  the spike-only measurement), a causal structure present in both arms that the clause,
  written from the reference control's 1.04, did not anticipate; the control's pulse-window
  ratio (1.06, flat) shows its pulse timing was decorrelated as intended. The intervention
  is therefore reported as valid on delivery and timing, and not valid by the letter of its
  own predeclared rule; the reading below is conditional on that. Reading: removing the
  uncorrelated load removed the net STDP depression on A (-0.172 -> -0.009), so the load
  explanation is supported as a contributor; it did not produce potentiation. The remaining
  LTD comes from the 88 spontaneous pre spikes per cell against ~4 Hz post activity and
  from the volley's own 10-ms dispersion against the fast natural response (non-pulse pairs
  1.59:1); the rule's equal-trace requirement at the measured weights is 3.6:1 at 0.75
  `w_max` falling to 2.1:1 at 0.64, against the 3.02:1 achieved, and the approximation
  predicts LTP/LTD 0.84-1.1 where 0.98 was measured. Load and leverage are not alternatives
  but factors of the same inequality, and this run cannot separate them further; it bounds
  them: even with the load removed, the network's own response (1.4-1.6:1) is far under
  what the rule needs at the scaling rest weight. This tested variant was insufficient. It
  is not a universal limit of pair STDP and does not select a triplet rule. **The
  imposed-timing investigation is closed** (2026-09-12): three protocols (untimed, paired
  volleys at 300 ms, paired brief volley) and one homeostasis candidate, none reaching 1.2;
  K0.3 stays red with its protocol, threshold and result of record unchanged. Log:
  `~/.cache/scratch/brainsim-k03-volley/brief_volley_seed1.log`; protocol as predeclared:
  `~/.cache/scratch/brainsim-k03-volley/protocol.md`. Durations: warm-up 120 simulated s
  (~53 s wall); the two instrumented arms 19.98 simulated s each, 108 s wall in total.
- **K0.4 structure**: 240 sim-s. Alive synapses fall >= 20 % from immature init within 90 s,
  births and deaths both > 0 in every 10 s window after the first, change over the last 30 s
  of the final wake phase (190-220 s; the count legitimately moves at the sleep switch because
  `g` drops) < 3 %, every E neuron outside `sense` keeps >= 5 incoming E synapses (`sense`
  has no inputs by design), count never reaches 0.9 `S_max`. Measured 2026-09-11 at
  `I_GAIN = 2.5` with anti-windup: fails on its first clause. The count never falls 20 %
  below the immature 360k, because growth at 10x base in the first ten seconds (301k at 1 s
  to 402k at 10 s) outruns the pruning phase; it reads 323k at 90 s, 10 % under init, and
  only because the wake-transition seizure pruned 90k. The clause assumed a first minute
  dominated by pruning; earlier runs never reached it (store-full abort at 72 s). Later
  clauses were not evaluated by the suite; the 240 s verification run gives peak 427k
  (71 % of `S_max`) and a 0.0003 % change over 190-220 s.
- **K0.5 UI truth**: frames produced directly from the engine over 10 s: summed spike lists
  equal `spike_total`, `n_syn_alive` equals `alive.sum()`, born/died lists match the counters.
  Plus the one-source-of-truth checks of section 6: every frame key the JS reads is emitted,
  and `phase`, `g`, `g_struct`, `sense_gated`, `n_syn_alive`, `t`, `age_s` in a frame equal the
  engine's attributes at emission.
- **K0.6 sleep**: in sleep, `sense` rate < 0.1 Hz, `g == 0.3` in frames, ctx stays > 0.2 Hz.
- **K0.7 proxy calibration**: a one-neuron network with no synapses, run 30 sim-s at the
  region's `sigma`, fires at <= 0.3 x `r_target_exc` for `ctx` and for `hpc`. Fail = noise can
  satisfy the setpoint and the rate-driven rules are decorative again.
- **K0.8 conduction delay**: a synapse added at tick 0 with a supra-threshold weight does not
  fire its post-neuron when the pre-neuron is driven at tick 500, and does at tick 1500.
- **K0.9 two-sign controller with motif**: on a fresh default network (wired at the motif),
  `structural_update(e)` with `e = +1` for every `ctx` neuron raises the summed E in-degree of
  `ctx` and does not lower any `ctx` neuron's I in-degree below `floor(EI_MOTIF * kE_before)`;
  with `e = -1` it lowers E and raises I; after killing every I synapse onto `ctx`, `e = +1`
  still raises `ctx` I in-degree (deficit restoration); after adding I synapses onto `ctx`
  beyond the motif, `e = +1` lowers I but leaves each neuron at or above its motif. Births are
  conduct-delayed and new I synapses have inhibitory presynaptic neurons from `ctx` only.
- **K0.10 anti-windup**: (a) on a fresh default network, `structural_update` called
  repeatedly with `e = +0.1` on every `ctx` neuron and `0` elsewhere (small enough that the
  calls stay far from the store clamp), with no stepping between calls so the error cannot move, grows E onto `ctx` on each of the first
  `WINDUP_WINDOW_SWEEPS` calls; on the next call `growth_halted["ctx_E"]` and
  `growth_halted["ctx_I"]` are True, no E synapse is born onto `ctx`, and I deficit
  restoration onto `ctx` still runs. A following call with `e = -0.1` on `ctx` (sign flip)
  releases both groups, and a later `e = +0.1` call grows E onto `ctx` again. (b) with `S_MAX`
  overridden so that `WINDUP_CAP_FRAC * S_MAX` lies below the immature wiring count, 30 sim-s
  run without `synapse store full`; in every frame where the sweep ran clamped
  (`store_clamped` True) `born_count` is 0, and `stats["store_clamp_sweeps"] > 0`.
  (c) frames carry `growth_halted` and `store_clamped` equal to the engine's attributes.
  (d) the hold covers the pruning side: on a fresh network, `e = -0.1` on every `ctx`
  neuron for `WINDUP_WINDOW_SWEEPS + 1` calls prunes E onto `ctx` on each of the first
  `WINDUP_WINDOW_SWEEPS` calls and, on the last call, latches and prunes no E onto `ctx`.
- **K0.11 scaling on used input, in wake**: (a) on a fresh default network with
  `set_sense_spont(0)` (sense has no noise, so every `sense` unit is silent) and `G_WAKE`
  overridden to 0 so STDP is silent and only scaling can move a weight, across the first
  sweep every surviving alive `sense->ctx` weight (alive with the same pre and post, since
  a killed slot can be reborn as another synapse) is bit-identical before and after the
  sweep while the alive `ctx->ctx` E weights onto the same ctx cells are not; (b) with
  `G_SLEEP` overridden to 0 so STDP is silent in sleep, after `set_sleep(True)` and one
  sweep to enter the regime, across two further sweeps inside sleep every surviving alive E
  weight onto `ctx` (any presynaptic region) is bit-identical, and `phase` is still
  `"sleep"` at the end. Fail = a gated input, or a gated phase, is being scaled.

**Presentation drive calibration (2026-09-11).** `PATTERN_AMP_MV` was 1.9 mV per tick, which
ran the pattern cells at 49.6 Hz (measured; first reported as 61 Hz, see 2.3), the pair
rule's depression band. It is set by
measurement: one network is warmed up exactly as K0.3 does (120 s, one sleep inside), then
copied once per candidate amplitude (1.9, 1.5, 1.3, 1.2, 1.1, 1.05, 1.0 mV), and pattern A is
presented on each copy with the K0.3 schedule (20 x 300 ticks on, 700 off). Per amplitude:
mean rate of the pattern-A sense cells during presentation, mean rate of the ctx patch cells
(ctx cells with more than half of their alive incoming `sense` synapses from pattern-A
units) during presentation, the K0.3 ratio, and the mean `w / w_max` of the pattern-A
synapses before and after. The selection rule as first written was: the amplitude with the
highest K0.3 ratio among those that keep the pattern cells at or under 30 Hz, ties to the
lower drive. Result (seed 1, pattern-A weights 0.755 `w_max` before every run, 0.75 % at
ceiling):

| amp mV | pattern Hz | patch Hz | other ctx Hz | K0.3 ratio | w / w_max after |
|---|---|---|---|---|---|
| 1.9 | 49.6 | 12.5 | 6.0 | 0.72 | 0.54 |
| 1.5 | 35.1 | 11.2 | 5.7 | 0.76 | 0.58 |
| 1.3 | 26.7 | 10.1 | 5.5 | 0.81 | 0.62 |
| 1.2 | 21.5 | 9.2 | 5.3 | 0.84 | 0.64 |
| 1.1 | 15.7 | 8.0 | 4.9 | 0.88 | 0.68 |
| 1.05 | 11.8 | 7.0 | 4.7 | 0.91 | 0.70 |
| 1.0 | 7.4 | 5.6 | 4.6 | 0.95 | 0.72 |

The ratio is monotone in drive and never reaches 1.0: every amplitude depresses, and less drive
only depresses less. The rule as first written therefore selects the weakest drive, 1.0 mV, at
which the pattern cells run 2.4 Hz above the 5 Hz spontaneous rate and the ctx patch is 1 Hz
above the rest of ctx; that is not a presentation, and choosing it would turn K0.3 into a test
of presenting nothing. Decision: `PATTERN_AMP_MV = 1.3`, the largest amplitude in the sweep
that keeps the pattern cells under 30 Hz, so the kill test runs against a real, sub-ceiling
presentation and its failure cannot be blamed on a silent stimulus. The 30 Hz cap is a chosen
number, not a derived one: under half of the 61 Hz figure the owner named as too loud
(49.6 Hz by the definition of record), and under the 35 Hz
the 1.5 mV run sits at; it is a labelled proxy for a sensory rate, and a different cap moves
the choice along the table by the same rule. Duration stays at 300 ticks on, 700 off: at 1.3 mV
on the same warm network, 100 ms on gives ratio 0.87 (patch 15.7 Hz, the onset transient), 300
ms 0.81, 600 ms 0.76 (patch 7.1 Hz, adapted), so less presentation only depresses less and no
duration potentiates either. Why it depresses at every drive, from the rule as written: the
weights rest at 0.755 `w_max` after wake scaling on used input, so one causal pair adds `A+
(w_max - w)` = 0.0025 `w_max` and one anticausal pair removes `A- w` = 0.0091 `w_max`;
potentiation needs 3.7 causal pairs per anticausal pair, and the pair rule's uncorrelated fixed
point is `A+ / (A+ + A-)` = 0.45 `w_max`, below where scaling holds the weights. No rule is
added for this; it is reported.

**`I_GAIN` calibration (2026-09-11).** `I_GAIN`, the inhibitory weight draw as a multiple of
the E draw (2.5), was 3.0, chosen under the retired 4.6 mV noise regime; with the motif held
it made recurrent drive net inhibitory (2.5, measured). It is set by measurement: from 3.0
downward in steps of 0.25, one 120 s default-schedule run per value at seed 1 with the
anti-windup in place. A value **holds** when, over the K0.2 window (100-120 s), ctx E mean
rate is within 5 % of its 4 Hz setpoint and the alive count changes by less than 1 % across
the window; the number of sweeps in the window with `growth_halted["ctx_E"]` set is reported
beside it, because a count can be flat for two reasons (the error closed, or the latch holds)
and the report has to say which. The burst guard is K0.2's: no tick anywhere in the run with
more than 20 % of `ctx` spiking. The sweep stops at the first value that bursts;
`I_GAIN` is then one increment above it whether or not that value holds, and the report says
which. Otherwise `I_GAIN` is the highest value that holds.

Result (2026-09-11, seed 1, 120 s each, anti-windup as in 2.5): **no value holds.** ctx E
sits at 3.3-3.5 Hz in the window at every gain from 3.0 to 2.25, and the count is flat
because the latch holds (20 of 20 window sweeps at every gain). The burst guard decides:

| `I_GAIN` | ctx E Hz | hpc E Hz | alive 100 s -> 120 s | max alive | tick > 20 % of ctx |
|---|---|---|---|---|---|
| 3.0 | 3.31 | 0.80 | 376,229 -> 376,267 | 451,806 | t = 81 s, 35 % |
| 2.75 | 3.46 | 0.86 | 364,326 -> 364,380 | 436,028 | t = 81 s, 34 % |
| **2.5** | 3.45 | 0.71 | 332,802 -> 332,820 | 427,351 | none (4.2 % at 81 s) |
| 2.25 | 3.31 | 0.76 | 264,664 -> 265,031 | 360,000 | t = 1 s, 28 %; t = 81 s, 33 % |
| 2.0 to 1.0 | 2.4-2.7 | 0.3-0.4 | 117k-185k, flat | 360,000 | t = 1 s, 28-37 % |

Two seizures, two causes. At 2.25 and below the immature wiring (2x in-degree) seizes in its
first second and loses 40-70 % of its synapses. At 3.0, 2.75 and 2.25 the net seizes at the
first wake transition, t = 81 s: sleep gates `sense`, the ctx error sits near 0.7 for 20 s,
scaling (+7 %/s, capped at +10 %) takes every E weight to `w_max` (98.7 % of sense->ctx
weights at 80 s, measured), the adaptive thresholds relax, and `sense` returns onto a maxed
net (20 Hz for a second, 50k synapses pruned). **`I_GAIN = 2.5`** is the one value with no
tick over 20 % anywhere in the seed-1 run; there the wake transition is a 9.5 Hz ctx E
transient with 21k synapses pruned. Seeds 2 and 3 at 2.5 seize at both t = 1 s (24 %, 22 %)
and t = 81 s (35 %, 34 %), so the seed-1 pass is a threshold phenomenon that landed on the
safe side by chance: the wake-transition seizure belongs to the net, not to a gain, and no
gain in the sweep is free of it. Superseded later the same day: the 2.4 scaling rule
removes the t = 81 s seizure on seeds 1-3 (1.6-2.5 % peak, zero deaths), so the table's
t = 81 s entries are pre-fix; the t = 1 s immature seizure on seeds 2 and 3 (22-24 %)
remains and `I_GAIN` was not revisited for it. K0.2's burst assertion covers only its
100-120 s window and never sees t = 81 s; the guard is left as specified and the gap is
stated here. The plateau is the same 3.4-3.5 Hz at 250k synapses
(growth held from 8 s), at 330k-450k (this sweep) and at 550k (no anti-windup), so synapse
count is not the lever for the last 0.5 Hz, and a lower gain buys seizures, not rate.

## 8. Stage 1 kill tests (designed now, built later)

### 8.0 Stage 1 contract (predeclared 2026-09-12, before any Stage 1 code)

**Stage 1 starts with the learning rule, not with replay.** Stage 1 needs a pathway that gets
stronger when it is used. On pair STDP plus scaling every population protocol nets LTD on the
used `sense->ctx` pathway (untimed onsets 0.922, K0.13; weak-current pairing 0.861, K0.3
fourth pass), so consolidation and replay (2.7, K1.1-K1.5), two-timescale weights and
metaplasticity all wait on a rule that passes S1.0. Nothing in this contract touches
`I_GAIN`, the E/I balance, anti-windup, the sleep scaling gate, `H_MAX`, K0.7, isolated
noise, K0.4 or the UI; the intrinsic-homeostasis branch stays unmerged. No LLM anywhere.

**Candidate, one, labelled proxy: triplet STDP (Pfister & Gerstner 2006), minimal all-to-all
form, on the engine's existing traces and soft bounds.** Not chosen: three-factor gating of
the existing pair rule (pair rule x `g`, or x an explicit pattern-on modulator, gate off = no
STDP change). Reason, from the record: a multiplicative gate cannot change the sign of the
change inside a presentation window, and the window itself nets LTD on the used pathway at
the rest weight (K0.3 fourth pass: window causal:anticausal 1.04 against 3.6 needed; K0.13:
LTP +0.193 against LTD -0.397 per A synapse). Gating STDP off outside the windows only
removes the between-window drift, so the predicted S1.0 ratio is below 1; running it would
be running a known failure. The triplet rule is the one of the two that changes the LTP/LTD
balance with the targets' rate, which is what "stronger when used" needs.

Rule (`params.STDP_RULE`, `"pair"` = today's path, byte-identical, digest unchanged;
`"triplet"` = the candidate; anything else raises):

```
o2_post[i]: slow post trace, tau_y = 114 ms (P&G 2006 Table 3, visual cortex, all-to-all
            minimal fit; tau_x unused because A3- = 0); decays each tick with x_pre and y_post,
            += 1 on i's spike after that spike's LTP has been applied
on delivery of j->i:   w -= g * A2- * y_post[i] * w                       (LTD, unchanged; A3- = 0)
on post spike of i:    w += g * (A2+ + A3+ * o2_post[i]) * x_pre[j] * (w_max - w)
                       with o2_post read before the spike's own increment (P&G's t - eps)
```

`A2+ = a_plus` (0.01) and `A2- = a_minus` (0.012) are the existing ctx constants, unchanged;
the soft bounds `(w_max - w)` and `w`, `w_max`, the clip and the absence of any floor are
unchanged and are not up for adjustment in this slice. With `A3+ = 0` the candidate is the
pair rule of record to the bit. `A3+` applies to synapses onto `ctx` only (`sense->ctx`,
`ctx->ctx`, `hpc->ctx`); `hpc` keeps the pair rule (`a3_plus` 0) because S1.0 evaluates the
`sense->ctx` pathway and the binder's rule is K1.1's question. P&G's pair time constants
(16.8 / 33.7 ms) are not adopted; the engine's 20 ms traces stay.

One new constant, fixed before any run by **rule T**: anchor the rule's uncorrelated fixed
point at the ctx E setpoint (4 Hz) to the measured rest weight (0.75 `w_max`, K0.13
arm_none), so that STDP and scaling agree at rest and the rate dependence does the work
above and below the setpoint. `(A2+ + A3+ rho_set tau_y)(w_max - w_rest) = A2- w_rest`
gives `A3+ = (A2- w_rest/(w_max - w_rest) - A2+) / (rho_set tau_y) = (0.036 - 0.01) /
(4 x 0.114) = 0.05702`. Consequences (uncorrelated Poisson pre and post, all-to-all
traces): fixed point `w*/w_max` 0.692 at 2.6 Hz post (outside K0.13's windows), 0.750 at
4.0, 0.853 at 9.2, 0.887 at 12.9 Hz (inside); the LTP coefficient relative to the pair rule
is 2.7x at 2.6 Hz, 3.6x at 4, 9.4x at 12.9. `A3+/A2-` = 4.75 against P&G's 0.92: the gap is
this engine's soft bounds (3:1 against LTP at 0.75 `w_max`) and its rates; P&G's own
amplitude ratio with `A2+ = 0` would put the fixed point at 0.75 only above 28.7 Hz post and
at 0.57 at 12.9 Hz, more depression than the pair rule, so it is predicted to fail and is
not run. No second value is run: a miss is a reject.

Predictions, written before the run: inside a 40-tick presentation the A targets fire at
~13 Hz, so the A synapses move toward 0.89 `w_max` at ~5x the speed of the off-patch
synapses (26.8 vs 4.9 Hz presynaptic); outside, both drift toward 0.69 at the same slow
speed; scaling holds the sum. Predicted S1.0 ratio 1.1-1.3 (marginal). Predicted risk:
rate-dependent LTP on the recurrent `ctx->ctx` synapses is positive feedback inside a sweep,
before scaling can act; K0.2 is the guard, and a K0.2 failure rejects the candidate (no gain,
bound, noise or setpoint change to rescue it).

**S1.0 (replaces population K0.3 as the contrast test; bar 1.2, unchanged).** Seed 1;
warm-up 120,000 ticks under the default schedule (one sleep at 60-80 s) in triplet mode;
targets `ctx_A` by the K0.3 selection rule, frozen before training. Present topographic
patch A with `present(A, 40)` at `PATTERN_AMP_MV`, 60 times at period 300 (K0.13's arm A
schedule, 18 s of wake), chosen because the baseline exists on it (0.922 under the pair rule)
and because a brief onset is where the targets' rate is transiently high, which is what the
triplet term reads. No current into `ctx` anywhere (every `inject` call audited sense-only);
arm B and arm none as in K0.13; probes as in K0.13. **Pass = mean alive `sense_A->ctx_A`
weight >= 1.2 x mean alive off-patch `sense->ctx_A` weight (raw), and the K0.13 gaps
>= 0.1 to arm B and to arm none** (a ratio the unstimulated arm also reaches is not
learning). Validity (fail = invalid run, not a result): K0.13's (a)-(d) with the instrument
extended to the triplet term (non-sweep residual exactly 0, scaling prediction exact, pair
counts cross-checked); largest single-tick ctx fraction <= 20 % in every arm; and K0.2,
the unchanged 120 s test, passing in triplet mode. Reported: causal and anticausal pair
counts and trace sums on the tracked synapses; LTP split into its pair-term and triplet-term
parts per surviving A and off-patch synapse, LTD and scaling likewise; weight headroom
(mean `w/w_max` and ceiling fraction, both groups, before and after); burst peak; rates (A
inside and outside the window, `ctx_A` E and I inside, outside and over the trial); the F1
probe result and selectivity, reported and not gated. Decision: pass -> the rule is accepted
for Stage 1 and the next slice is consolidation/replay under it; miss -> reject, pair STDP
stays on master, no third STDP variant, no amplitude sweep, stop. Budget: one S1.0 run
(~4 min wall), K0.2 in triplet mode (~1 min), unit tests; branch `stage1-triplet`
(worktree `~/.cache/brain-sim-s1`), master and the served simulation untouched until the
owner says merge.

Build order: tests first by a different worker (pair-mode digest unchanged; triplet mode
with `A3+ = 0` reproduces the pair-mode digest; `o2` decays with `tau_y` and increments
after LTP; LTP reads `o2` before the increment, so on a two-neuron rig a third post spike
inside `tau_y` earns more LTP than the first at equal `x_pre`; LTD unchanged; `g` scales the
triplet term in sleep; unknown rule raises; the K0.3 instrument's residual is exactly 0 in
triplet mode; S1.0 wrapper pins), then the implementation, then S1.0, then architecture and
security review. Files: `brainsim/params.py` (`STDP_RULE`, `TAU_Y_MS`, `a3_plus` per
region), `brainsim/net.py` (`o2_post`, `a3_plus_n`), `brainsim/engine.py` (`_tick`),
`tests/k03_pairing.py` (instrument LTP coefficient and pair/triplet split),
`tests/s10_triplet.py` (driver: mode switch, K0.13 run, K0.2 guard, report),
`tests/test_s10_triplet.py` (unit tests and the S1.0 wrapper, marker `s1`). K1.1-K1.5,
`w_s`, metaplasticity and replay are not implemented in this slice.

**S1.0 result (2026-09-12, branch `stage1-triplet` 12d2774, seed 1; log
`~/.cache/scratch/brainsim-s1/s10_full_seed1.log`, pytest `pytest_s10.log`): REJECT.** Valid
run: every A volley delivered, every probe delivered, instrument residuals exactly 0 in
triplet mode with the pair/triplet split closing, 160 inject calls all sense-only, largest
single-tick ctx fraction 5.5 % (arm B 7.1 %, arm none 1.8 %), and K0.2 (the unchanged 120 s
test) passes in triplet mode. Weight endpoint: ratio 1.029 in arm A (arm B 1.019, arm none
1.017; gaps 0.010 and 0.012) against 1.2 and 0.1. F1 fails the same way as under the pair
rule: evoked_A 0.751 before, 0.403 after A, 0.958 after B, 0.830 after none. What happened,
in the rule's own terms: rule T's premise did not survive the candidate. Under the triplet
rule the warm-up rest weight of `sense->ctx_A` is not 0.75 but 0.924 `w_max` with 30 % of the
synapses at the ceiling (pair rule: 0.750 and 0.75 %), the alive A->ctx_A count is 4,976
(pair rule 10,785), and ctx E EMA at 120 s is 3.44 Hz. With 0.08 `w_max` of headroom the
boosted LTP still loses: per surviving A synapse LTP +0.331 (pair term +0.088, triplet term
+0.243), LTD -0.406, scaling -0.084; A 0.924 -> 0.845 `w_max`, off-patch 0.906 -> 0.821;
causal:anticausal on the tracked A synapses 279,579 : 171,674 (1.63:1; trace-weighted
2.20) against 14.6 needed at the baseline weight and 6.5 at the final weight on the
pair-coefficient basis. Rates in arm A: A 27.0 Hz inside the 40-tick window and 4.95
outside; `ctx_A` E 12.7 / 2.8 Hz, I 23.4 / 4.4 Hz. Reading: the rate-dependent LTP term
raised the rest weight to the ceiling during the warm-up, before any presentation, so the
headroom the term needed was gone; the used pathway is still net-depressed and the
population's response to it still halves. The pre-run prediction ("A moves from 0.75 toward
0.89") was wrong because the baseline was already above 0.89. Decision, per the contract:
the triplet proxy is rejected at its predeclared amplitude; no second amplitude, no bound or
floor change, no third STDP variant; pair STDP stays on master; the branch is kept as the
record and is not merged. Consolidation and replay stay blocked on a rule that passes S1.0.
Reviews on the branch diff: security, no findings; architecture, no blocker and no contract
drift, the result judged a trustworthy evaluation of the contract (engine as written,
instrument residual 0 in triplet mode, K0.2 really run in triplet mode); two test-suite
fixes applied (the S1.0 wrapper now pins the protocol constants on the module the driver
ran; the driver's restore assertion compares with the captured value); noted, not changed:
`Network.tiny` reads `a3_plus` from the live params module as it already did for `a_plus`,
the pair/triplet LTP split closes to rounding rather than by construction, and the
brief-volley tool's analytic coefficient is pair-only and is not run in triplet mode.


**K0.13 baseline: autonomous onset learning (protocol predeclared and run 2026-09-12 on
the unchanged engine; `tests/k013_onset.py`, `tests/test_rules.py::test_k0_13_autonomous_onset_learning`;
instrument generalised to zero pulses in `tests/k03_pairing.py`, pinned by
`tests/test_k03_instrument.py`, and shown to reproduce the K0.3 result of record exactly,
0.927473 / 0.869582).** Learning from sensory input with no postsynaptic teaching pulse: every
stimulus is `present(pattern, 40)` at `PATTERN_AMP_MV` to sense cells only, audited per call.
It establishes the baseline against which engine changes are evaluated; it replaces none of
K0.1, K0.3, K0.4, and the imposed-timing investigation stays closed. Protocol: seed 1, the
K0.3 warm-up (120,000 ticks); targets `ctx_A` and, as a secondary population, `ctx_B`, both
by the K0.3 selection rule and frozen before training; three deepcopies of the one warmed
state: arm_A = 60 x pattern A for 40 ticks at period 300 (18 simulated s, t = 120,000 to
138,000, all wake, 18 sweeps), arm_B = the same with pattern B (alternative-exposure
control, not assumed equivalent), arm_none = nothing presented. The period is 300, not the
333 first proposed, because an after-training probe has to run in wake from each arm's end
state and at 333 only 20 wake ticks remained; trial count and presentation duration are
unchanged. Probes: from separate copies of the warmed state (before) and of each arm's end
state (after), five presentations of A and, on another copy, five of B, onsets at 20 + k x
300 ticks; the timing reference is the commanded onset tick and the windows never move with
the volley: response [onset+25, onset+45), pre-stimulus baseline [onset-20, onset), evoked =
(response - baseline) spikes per cell per presentation; selectivity S = (A - B)/(A + B),
defined only for non-negative values summing to >= 0.05, no epsilon. Predeclared: weight
endpoint = K0.3's ratio >= 1.2 in arm_A with gaps >= 0.1 to both controls; functional F1 =
evoked_A(after_A) exceeds evoked_A(after_none) and evoked_A(after_B) by >= 0.15 spikes per
cell per presentation (an absolute scale, ~30 % of the natural response); input validity
(volley delivered in training and probes, instrument residuals, sense-only injection) is
separate from network performance (natural response >= 0.05 before training). Overlap and
asymmetry on the warmed state: A and B share 1 of 40 sense cells; `ctx_A` (368) and `ctx_B`
share no cell; alive synapses A->ctx_A 10,785 at 0.750 `w_max`, B->ctx_A 1,654 at 0.771,
A->ctx_B 1,216 at 0.775, B->ctx_B 8,194 at 0.767; natural evoked responses before training
0.832 (ctx_A to A) and 0.885 (ctx_B to B), cross responses 0.099 and 0.055.
**Result (seed 1): valid, natural response present, weight endpoint fails, F1 fails, and
the two agree.** Validity: 99.75 % of A cells (min 97.5 %) and 99.6 % of B cells (min
95 %) spike inside their drive windows; every probe presentation >= 97.5 %; residuals 0
and cross-checks ok in all three arms; 160 inject calls, 0 to non-sense cells. Rates in
arm_A: A cells 26.8 Hz inside the window and 4.9 Hz outside; `ctx_A` E 12.9 Hz inside, 2.6
outside, 4.0 Hz over the trial, i.e. at its setpoint (arm_none 3.6-3.8 Hz). Largest
single-tick ctx fraction: arm_A 9.4 %, arm_B 8.5 %, arm_none 2.7 % (K0.2 guard 20 %).
Weights (fractions of `w_max`): arm_A A 0.750 -> 0.655, non-A 0.753 -> 0.710, ratio 0.995
-> **0.922**; arm_B A -> 0.772, non-A -> 0.766, ratio 1.008; arm_none A -> 0.755, non-A ->
0.759, ratio 0.995. Attribution per surviving A synapse (w units, zero residual, scaling
prediction exact): arm_A LTP +0.193, LTD -0.397, scaling +0.000; arm_none +0.044, -0.160,
+0.126; arm_B +0.046, -0.162, +0.156; non-A in arm_A +0.055, -0.158, +0.004. Turnover:
arm_A A 351 deaths / 38 births, non-A 171 / 10; arm_B 155 / 32, 74 / 23; arm_none none.
Trace-weighted causal:anticausal for A over the full interval in arm_A: 1.77, against the
rule's equal-trace requirement 3.60 at the baseline weight and 2.28 at the final weight.
Behaviour (ctx_A, spikes per cell per presentation): evoked_A before 0.832, after_A
**0.428**, after_B 0.849, after_none 0.863; evoked_B 0.099, 0.046, 0.060, 0.113; S 0.788,
0.807, 0.868, 0.769 (ΔS: A +0.020, B +0.081, none -0.018; S sits near its ceiling by
construction of the target set and is reported, not gated). F1: after_A - after_none =
-0.435, after_A - after_B = -0.421 (ratios 0.50, 0.50). The B pathway behaves the same way:
`ctx_B`'s response to B falls 0.885 -> 0.490 after B training, 0.986 with nothing
presented, 1.086 after A training. Descriptive, during training: `ctx_A` evoked per A
presentation, trials 2-6 vs 56-60: 0.732 -> 0.488 (arm_B, `ctx_B` to B: 0.755 -> 0.448).
Reading (predeclared case 4): the task fails on the unchanged engine, and the direction is
the finding: sixty brief onsets depress the presented pathway (A 0.750 -> 0.655 while the
controls hold 0.755-0.772) and halve the population's own evoked response to it, with the
same on the B pathway; repetition habituates. The attribution says why, in the rule's own
terms: relative to arm_none the volleys add +0.15 of LTP and -0.24 of LTD per A synapse,
and they also take away scaling's +0.126 lift by bringing `ctx_A` E to its setpoint, so
the group that is stimulated is the one that loses the homeostatic lift the others keep.
The measured natural causal excess (1.77) is below the requirement at the rest weight
(3.60) and above what the requirement would be at any rest weight under about 0.60
`w_max`, where 0.012 w = 1.77 x 0.01 (2 - w). That is consistent with the existing account
(rule fixed point 0.45 `w_max` against a homeostatic rest weight of 0.75) and does not by
itself single out homeostasis: the same inequality is satisfied by changing the rule's
constants. The recommendation, comparison, recovery contract and implementation slice are
recorded below the K1 list. Limitations: one seed; probe of five presentations from one
copy each (the first presentation's value is printed beside the mean); S near ceiling; B is
an exposure control with a different pathway (1,654 vs 10,785 synapses onto `ctx_A`); the
descriptive training measure excludes trial 1 (its baseline window precedes the recorded
ticks); `ui/stage0_results.json` was not extended (K0.13 is a baseline, not a kill test; the
owner decides whether it is recorded there). Durations: warm-up 120 simulated s (~53 s
wall); three arms of 18 simulated s and eight probe copies of 1.52 s, 166 s wall in total.
Log: `~/.cache/scratch/brainsim-k013/k013_seed1.log`; protocol as predeclared:
`~/.cache/scratch/brainsim-k013/protocol.md`.

### 8.1 Second Stage 1 candidate: gated plasticity, three-factor (predeclared 2026-09-12)

Owner's frame: the always-on triplet rule is rejected (8.0; branch `stage1-triplet` stays
unmerged) and master keeps pair STDP. One candidate, no new rule constant: the pair rule of
record gated by a stimulus-driven modulator, with STDP off at rest. If it rejects too, the
owner's stated conclusion is that this plant (these rates, this scaling, this nerve) does not
support unsupervised population contrast, and the next choice is an explicit teaching signal
(the measured pairing current, as a labelled proxy for neuromodulation plus post drive) or
memory tests that do not depend on S1.0; K1 replay waits for one of those. No third
candidate this round.

Rule (`params.PLASTICITY_MODE`: `"always"` = today's path, byte-identical, digest unchanged;
`"gated"` = the candidate; anything else raises):

```
gate (Engine.gate, 0 or 1), set at the start of every tick before any delivery:
    1  iff the sense input is not gated (wake) and at least one active stimulus is an
       all-sense stimulus (n_sense_cells == n_cells: what present() issues, and the
       K0.13 audit's own criterion for a presentation); global, not pathway-specific
    0  otherwise (rest in wake, and all of sleep)
gate 1:  LTD and LTP exactly as today (pair rule, A+ 0.01, A- 0.012, soft bounds, g)
gate 0:  no LTD, no LTP: the two update blocks are skipped, no weight is touched;
         x_pre and y_post keep evolving as state
scaling: in gated mode the sweep's scaling step excludes synapses whose pre is in sense
         (the nerve is frozen for scaling); every other E pathway scales as today;
         prune and grow untouched (births at W_GROW_FRAC = 0.15 w_max)
```

The gate is a labelled proxy for a neuromodulatory signal that follows attended sensory
input (three-factor plasticity: pre, post, modulator); it is not a claim about ACh or NE.
The on-update rule is the first of the owner's two options, pair STDP at the lower rest
weight; the second (an LTP-biased triplet while gated) is not built.

Why the nerve is frozen for scaling, not scaled: with STDP off at rest nothing opposes
scaling's lift on the nerve, and the ctx E rate sits under its 4 Hz target even at 0.92
`w_max` (8.0: 3.44 Hz EMA at 120 s), so an unopposed scaling on the nerve stops only at the
ceiling, which is reject criterion R1 by construction. Frozen, the nerve's rest weight is
what initialisation and growth leave it: init uniform 0.2-0.6 `w_max` (mean 0.40), births
at 0.15. The pair rule's equal-trace requirement `R(w) = A- w / (A+ (w_max - w))` is 0.21 at
0.15, 0.80 at 0.40, 1.20 at 0.50, 1.80 at 0.60, 3.60 at 0.75; the onset protocol delivered a
trace-weighted causal:anticausal of 1.77 at the 0.75 rest weight (K0.13), so if that excess
holds at the weaker drive the window nets LTP at any rest weight below 0.596 `w_max`.
Off-patch inputs see ~1:1 in the same windows and drift toward the rule's own fixed point
(0.455) at 5 Hz presynaptic while A moves at 27 Hz.

Predictions, written before the run: nerve rest weight 0.30-0.40 `w_max` at 120 s with a
ceiling fraction under 1 %; the gated window nets LTP on A; ratio 1.1-1.3 (marginal).
Risks: the natural response before training falls below K0.13's 0.05 precondition at the
weaker nerve (reported as the headline, not hidden); `ctx->ctx` scales toward its ceiling
to hold 4 Hz against a weaker nerve (reported: E->E mean `w/w_max` and ceiling fraction at
120 s; K0.2 is the guard); off-patch inputs potentiate too under the global gate.

Reject criteria, predeclared, each reported with its numbers:
- **R1, warm-up ceilings the nerve**: at t = 120,000 the alive `sense->ctx` synapses have
  mean `w/w_max` > 0.85 or a ceiling fraction (w >= 0.999 `w_max`) > 5 %.
- **R2, the on-window nets LTD at the measured rest weight**: in arm A, per surviving
  tracked A synapse, `ltp_mean + ltd_mean < 0` (all STDP is inside gated ticks by
  construction); reported beside R(w_rest) and the measured trace-weighted excess.
- **S1.0 unchanged** (8.0): ratio >= 1.2 in arm A and gaps >= 0.1 to arm B and arm none;
  no teacher current; validity = K0.13's (a)-(d) with the instrument mirroring the gate and
  the frozen nerve (residuals exactly 0), burst <= 20 % in every arm, K0.2 passing in gated
  mode; the natural response >= 0.05 is K0.13's performance precondition.
Additional reporting: gated ticks per arm and the fraction of A and `ctx_A` spikes inside
gated ticks; nerve statistics at 120 s (alive count, mean `w/w_max`, ceiling fraction) and
the same for `ctx->ctx` E->E; everything 8.0 reports (pair counts and trace sums, LTP, LTD,
scaling, headroom, burst peak, rates, F1 and S).

Build: branch `stage1-gated` (worktree `~/.cache/brain-sim-gated`) from master; tests first
by a different worker (always-mode digest unchanged; gate 0 at rest and 1 during a
presentation, 0 in sleep and for a non-sense injection; no weight change with gate 0 on a
two-neuron pairing rig and today's change with gate 1; scaling skips sense-pre synapses in
gated mode and touches them in always mode; unknown mode raises; instrument closes in gated
mode on the K0.3 rig with the gate mirrored; S1.0 wrapper with R1, R2 and the endpoint
separated from validity); then the implementation, S1.0, reviews. Files: `brainsim/params.py`
(`PLASTICITY_MODE`), `brainsim/engine.py` (`gate`, `_tick`, `_slow_sweep`),
`tests/k03_pairing.py` (gate-aware LTD/LTP prediction, nerve-frozen scaling prediction, gate
counters), `tests/k013_onset.py` (warm-end nerve and E->E statistics, `report()` factoring),
`tests/s10_gated.py`, `tests/test_s10_gated.py` (marker `s1`). Not touched: `I_GAIN`, the
E/I balance, anti-windup, the sleep scaling gate, `H_MAX`, K0.7, noise, K0.4, the UI, the
hpc rule; the intrinsic-homeostasis and triplet branches stay unmerged.

**S1.0 result (2026-09-12, branch `stage1-gated` 8a71d56, seed 1, 60 trials, K0.13 schedule):
REJECT (weight endpoint).** R1 not triggered: at t = 120,000 the 93,793 alive `sense->ctx`
synapses sat at 0.4167 `w_max` with 0.00 % at the ceiling (always mode, same seed: 0.7679 and
1.14 %). R2 not triggered: per surviving tracked A synapse in arm A, LTP +0.2285, LTD -0.1427,
net +0.0857 (+0.043 `w_max`), scaling 0 by construction; trace-weighted causal:anticausal 2.073
against 0.832 needed at the 0.4095 `w_max` rest weight (pairs 574,249 causal / 378,729
anticausal). Gate: 2,400 gated ticks in each presenting arm (60 x 40), 0 in arm none, 0 mirror
disagreements; 45.8 % of A spikes and 41.6 % of `ctx_A` spikes in arm A fell inside gated ticks.
Endpoint: ratio baseline 0.9749; final A 1.0200, B 0.9851, none 0.9749 (gaps 0.035 and 0.045
against 0.1; bar 1.2); survivors-only 1.026. Valid on (a)-(d); bursts 8.6 / 5.7 / 2.5 %; K0.2
passes in gated mode (60.8 s); natural response 0.817 before training. F1 `evoked_A` on
`ctx_A`: before 0.817, after A 0.308, after B 0.570, after none 0.735; S 0.777 -> 0.589 after A.
Warm-end rates (EMA): sense 4.98, ctx E 3.74 / I 7.58, hpc E 0.92 / I 6.05 Hz; `ctx->ctx` E->E
sat at 0.9065 `w_max` with 26.2 % at the ceiling (always mode: 0.6934, 1.3 %), the predicted
recurrent compensation for the weaker nerve.

What the numbers say. The gated window did what the contract predicted at the synapse: STDP off
at rest left the nerve at its initialisation weight, and inside the windows A potentiated
(+0.043 `w_max` per survivor over 60 trials) more than the off-patch inputs (+0.010 `w_max`),
a differential of 0.033 `w_max` per synapse, about a quarter of what the bar needs from a
0.975 baseline. The larger effect was structural: in arm A 31.4 % of the tracked A->`ctx_A`
synapses and 38.3 % of the non-A ones died during the 18 s of training (arm B: 18.4 % of
A->`ctx_A`; arm none: none). The engine's structural update prunes the weakest incoming
excitatory synapses of any cell running above its rate target (`_prune_incoming`, ordered by
|w|), and `ctx_A` E cells ran at 11.7 Hz inside the windows (2.6 Hz outside) against a 4 Hz
target; with the nerve frozen at 0.42 `w_max` under recurrents at 0.91 `w_max`, the nerve is
the weakest input on every driven cell and is what the rate-driven prune removes. The endpoint
ratio of 1.02 is mostly survivorship (the weakest A synapses died), and the evoked response
after training fell to 0.31 of its pre-training value, the same suppression K0.13 records in
always mode (0.43), now by pruning rather than by LTD. Predictions before the run: rest
weight 0.30-0.40 (measured 0.417), on-window nets LTP (confirmed), ratio 1.1-1.3 (measured
1.02; the prediction missed both the size of the per-trial differential and the structural
prune of the frozen nerve). No constant was changed, nothing was retried, no sweep was run.
Always-mode K0.13 on the branch reproduces master's report to every printed digit (ratio
0.921950), so the instrument changes did not alter the path of record. Branch `stage1-gated`
stays unmerged; master keeps pair STDP; `PLASTICITY_MODE` does not exist on master.

Conclusion, as the owner framed it before the run: with the always-on triplet (8.0) and the
gated pair rule (8.1) both rejected, this plant (these rates, this scaling and structural
turnover, this nerve) does not support unsupervised population contrast under the K0.13
schedule. The two options named in advance are (i) an explicit teaching signal, the pairing
current already measured in K0.3, as a labelled proxy for neuromodulation plus postsynaptic
drive, or (ii) dropping S1.0 and building memory tests that do not depend on it. Neither is
taken here; K1 replay stays blocked until one is accepted.

Reviews (branch `stage1-gated`; run at 8a71d56, result and review fixes recorded at 73e2eff): architecture OK with notes, two fixes applied after the run (the K0.2 guard now records any exception instead of discarding the k013 result; the instrument states that in gated mode the sweep's scaling arithmetic is not exercised on the tracked set, only the freeze); recorded caveats: R1 is near-deterministic by construction because the warm-up issues no presentation, so the nerve never sees STDP before t = 120,000; R2 is the survivor mean as predeclared, not a per-synapse count; the gate mirror in the instrument re-reads the engine's stimulus list and the load-bearing gate check is the driver's tick count (2,400 = 60 x 40 per presenting arm). Security: no findings. Logs: `~/.cache/scratch/brainsim-gated/s10_full_seed1.log`, `pytest_s1.log`, and the always-mode equivalence pair `k013_master.log` / `k013_branch_always.log`.

### 8.2 K1.1 hpc binding / pattern completion (predeclared 2026-09-12, before any code)

Owner's frame (2026-09-12): S1.0 is stopped. Neither `stage1-triplet` nor `stage1-gated` is
merged; no teacher current, no further STDP variant, no more chasing of `sense->ctx` weight
contrast: that gate is closed. Stage 0 stands as the running plant (pair STDP, scaling, prune,
sleep flag), population contrast on `sense->ctx` is not a Stage 1 requirement, and the next
slice is K1.1 only: does the binder form a sparse assembly for a pattern and complete it from a
half cue? No K1.2-K1.5, no replay, no two-timescale weights, no language. The master engine
stays pair/always and byte-identical; the cortex wiring stays as on master unless binding
needs a change, in which case the work stops and asks first. Nothing here touches port 8000.

Protocol (seed 1; everything is an ordinary `present()`/`inject()` on `sense`, nothing else
is injected anywhere; engine unchanged):

1. Warm-up: `k03_pairing.warm_engine` (120,000 ticks of the Stage 0 plant under its own
   schedule, nothing imposed). At t = 120,000 the plant is in wake with 20 s of wake left;
   the whole protocol below (5.2 s) runs inside that wake block.
2. Baseline: 2,000 ticks with no stimulus (t 120,000-122,000); per-cell spike counts.
3. Present topographic A: `present(0, 2000)` at `PATTERN_AMP_MV` 1.3 mV into the 40-cell A
   patch (t 122,000-124,000); per-cell counts. `hpc->hpc` and `ctx->hpc` weights are
   snapshotted at t = 122,000 and t = 124,000 to show whether anything bound.
4. The assembly: `hpc` E cells whose rate during A exceeds their own baseline rate by
   >= 4 Hz (>= 8 excess spikes in 2 s; the baseline is ~1 Hz, so this is several standard
   deviations of a 2 s count). I cells with the same excess are reported, not counted:
   the assembly is the excitatory set. **Criterion 1 (forms, sparse): 1 <= size <= 20**
   (5 % of the 400 `hpc` cells).
5. Delay: 1,000 ticks with no stimulus (t 124,000-125,000).
6. At t = 125,000 the engine state is copied three ways (deepcopy, as K0.13 does):
   - **cue**: `inject(cue_ids, 1.3 mV, 200)` where `cue_ids` are the 20 cells at even
     positions of the sorted A patch (a fixed half, spread over the patch); nothing into
     `hpc` or `ctx`;
   - **full**: `present(0, 200)`, the whole patch again, a latency reference only;
   - **none**: no stimulus, the background reference for the spurious count.
7. **Criterion 2 (completes): >= 80 % of the assembly cells spike at least once within 50
   ticks of cue onset** (t 125,000-125,050) in the cue arm.
8. **Criterion 3 (no other assembly ignites): in the same 50-tick window, the number of
   non-assembly `hpc` E cells that spike, minus the number expected from their own baseline
   rates (sum over cells of 1 - exp(-r_i * 0.05 s)), is < 0.5 x assembly size.** The none
   arm's count in the same window is the empirical check of that expectation.
9. Reported, not criteria: recall at 50, 100 and 200 ticks for the cue and full arms; the
   assembly formed by B (`present(1, 2000)` from a copy taken at t = 122,000, same rule,
   same baseline) and its overlap with A's assembly (the old K1.1 bullet's 20 % is the
   reference); rates at warm end (EMA) against targets (`hpc` E 1 Hz, I 6 Hz), during the
   baseline, during A (assembly vs other `hpc` E cells, `hpc` I, `ctx` E), and in the cue
   window; synapse counts and mean `w/w_max` for `sense->hpc` (no such projection exists on
   master: expected 0), `ctx->hpc` onto assembly cells vs onto other `hpc` E cells,
   `hpc->hpc` inside the assembly, assembly->others and others->assembly, each before and
   after A; in-degrees of assembly cells.
10. Validity (fail = invalid run, not a result): the run stays in wake; >= 70 % of the 40 A
    cells spike during the presentation and >= 70 % of the 20 cue cells spike during the
    cue (K0.13's volley fraction); every injection in the run is sense-only (inject log);
    the engine is the master engine (params pins; no `PLASTICITY_MODE` or `STDP_RULE`
    attribute exists).

Predictions, written before the run. The path is `sense->ctx->hpc`, two hops of 1-8 ms
delay, and a sense cell at 1.3 mV needs ~30 ms from rest to reach threshold, so the first
`hpc` spikes evoked by the cue are expected 35-50 ms after onset: criterion 2 at 50 ticks
is tight even for the full patch, and the full arm's recall is reported to separate a latency
failure from a completion failure. Sparsity in `hpc` is emergent (low `r_target`, strong I
gain, 2.6); with 30 `ctx->hpc` inputs at sigma 0.25 per cell and a `ctx` patch under A, the
assembly is predicted at 10-40 E cells, i.e. criterion 1 may fail on size. Completion needs
`hpc->hpc` recurrent weights among assembly cells to grow during the 2 s (hpc A+ 0.05,
A- 0.06, w_max 3.0); 2 s at assembly rates of 5-15 Hz is enough for a measurable change but
whether it carries a half cue to 80 % is the open question. If it fails, the report says
which of the four ways: no or too large an assembly (sparsity), latency (full A itself
does not reach 80 % in 50 ticks), completion (full does, cue does not), or spurious
ignition (criterion 3). No constant is changed to make it pass; `sense->ctx` STDP, `I_GAIN`
and the learning rules are not touched; a k-WTA fallback (2.6) needs the owner's yes.

Files: `tests/k11_binding.py` (driver: `run_experiment(seed=1)`, `report(out, wall)`,
`main()`), `tests/test_k11_binding.py` (marker `s1`, registered in `tests/conftest.py`),
this section. Engine, server and UI untouched.

**K1.1 result (2026-09-12, master fea6d10, seed 1): FAIL on criterion 2 (pattern completion);
criteria 1 and 3 pass; the run is valid.** Warm-end EMA rates at t = 120,000: `hpc` E 0.95 Hz
(target 1), I 5.25 (target 6), `ctx` E 3.89, I 7.47, `sense` 4.97. Assembly: 16 `hpc` E
cells (4.0 % of `hpc`; 27 I cells showed the same excess and are not counted), baseline
0.41 Hz, 5.28 Hz during the 2 s of A; other `hpc` E 0.99 -> 1.31 Hz, `hpc` I 5.48 -> 7.63,
`ctx` E 3.99 -> 6.07; all 40 A cells fired. Pattern B from the same state formed an assembly
of 6 cells overlapping A's by 1 (6 % of A; the old bullet's reference was < 20 %). Cue arm
(20 cells, all fired, 25 spikes in the first 50 ticks): recall of the assembly within 50
ticks 1/16 = 0.0625, within 100 and 200 ticks also 0.0625; full-A arm (47 stimulus spikes in
the first 50 ticks) 0.0625 / 0.125 / 0.125; no-stimulus arm 0.0625 / 0.125 / 0.125. In the
50-tick window `hpc` E ran at 0.81 / 0.88 / 0.88 Hz (cue / full / none), `hpc` I 5.25 / 6.00
/ 5.75, `ctx` E 3.96 / 4.46 / 3.75: the sense drive arrived and `ctx` moved a little, `hpc`
did not move at all, and the cue and the full pattern evoked nothing in the assembly beyond
the background the three arms share (same RNG stream from the copy). Spurious: 12
non-assembly `hpc` E cells spiked in the cue window against 14.5 expected from their
baseline rates (excess -2.5; none arm 13), so criterion 3 holds trivially. Synapses:
`sense->hpc` 0 (no projection on master); `ctx->hpc` from excitatory `ctx` onto assembly
cells 1,009 synapses at 0.708 `w_max` before A, 849 at 0.587 after (16 % pruned, mean down
17 %); onto other `hpc` E 16,950 at 0.684 -> 16,340 at 0.669 (4 %, 2 %); `hpc->hpc` within
the assembly 51 at 0.624 -> 32 at 0.600 (37 % pruned), assembly->others 281 -> 244,
others->assembly 322 -> 244; E in-degree 63 (assembly) vs 70 (others). By the predeclared
taxonomy this is the latency case (the full pattern itself does not reach 80 % in 50
ticks), but the time course (diagnostic `~/.cache/scratch/brainsim-k11/diag_timecourse.py`,
same seed and protocol) shows the cause is not latency: during the original presentation the
assembly fired 4.7 Hz in its first 200 ms (4 of 16 cells in the first 50 ticks, 11 of 16
within 200 ticks, and 4-6.6 Hz in every 200 ms bin of the 2 s), yet 1 s after the
presentation the full pattern re-presented for 200 ms evoked 2 assembly spikes against 2 in
the no-stimulus copy. The assembly's threshold was not elevated (theta 0.09 mV above rest,
others 0.19); its rate EMA was still 2.3 Hz against a 1 Hz target. In plant terms: the same
2 s of activity that defines the assembly removes its drive. Pair STDP at the 0.71 `w_max`
rest weight of `ctx->hpc` nets LTD on the inputs of the cells that fire most (the K0.3 /
K0.13 result on `sense->ctx`, now on the binder's afferents: the hpc rule needs a causal
excess of A- w/(A+ (w_max - w)) = 2.9 at that weight), and the structural update prunes the
weakest incoming synapses of any cell above its rate target (`_prune_incoming`, ordered by
|w|); assembly cells ran at 5.3 Hz against 1 Hz for two sweeps and lost 16 % of their
excitatory `ctx->hpc` inputs and 37 % of their recurrent `hpc->hpc` inputs. The assembly is
a transient response, not a bound representation, so there is nothing for a half cue to
complete. Sparsity itself is not the problem: the binder produced a 4 % assembly for A and a
1.5 % assembly for B with 6 % overlap, from `ctx->hpc` alone. Nothing was changed to make it
pass: `sense->ctx` STDP, `I_GAIN`, the hpc rule and the cortex wiring are as on master; no
k-WTA. Reviews: architecture, plant not driver (the three arms diverge only where the
stimulus reaches: 12 vs 13 spurious spikers, `ctx` E 4.46 vs 3.75 Hz), five report fixes
applied and rerun at fea6d10 (numbers above), three caveats recorded: the volley validity
items are satisfied by the 5 Hz spontaneous sense rate alone over 200-2,000 ticks and are
not load-bearing (the per-window stimulus spike counts are); `SLEEP_ONSET_TICK` is a pinned
constant, not derived from the engine; `assembly_from_counts` assumes equal baseline and
stimulus windows. Security: no findings. Logs: `~/.cache/scratch/brainsim-k11/
k11_seed1_fea6d10.log`, `pytest_s1_fea6d10.log` (1 failed on c2 after every validity
assert passed), `diag_timecourse.log`.

### 8.3 K1.1 rerun with one plant change: no rate-driven elimination of excitatory afferents in `hpc` (predeclared 2026-09-12)

Owner's reading of 8.2, accepted as the record: the assembly forms and is sparse; completion
fails because the 2 s encode window puts assembly cells at 5.3 Hz against the 1 Hz `hpc`
target, so the structural prune and pair LTD strip `ctx->hpc` and `hpc->hpc` onto that
assembly during the encode. "The clique is a flash, not a memory." One plant change is
allowed, chosen from two: (a) no structural prune on `hpc` incoming excitatory synapses, or
(b) prune in `hpc` only below the rest target or above a high burst cap. The `hpc` STDP
equation is not changed; if completion turns out to need that, the work stops and asks.
Not touched: `sense->ctx` STDP, `I_GAIN`, S1.0, no teacher current, no extra machinery
merged, no K1.2.

**Choice: (a).** It adds no number. (b) needs a burst cap whose value would be a tuning
choice made to fit this experiment (the only anchor on the plant is `ACT_REF_HZ` 10 Hz, and
a strong pattern would put assembly cells over it); (a) is the cleaner question: with the
rate-driven elimination of afferents off, does the encode still strip the drive?

**Proxy label:** *afferent-elimination exemption.* Excitatory synapses onto `hpc` cells are
not eliminated by the rate homeostat; the only elimination onto `hpc` is by weight
(`W_PRUNE_FRAC`, w < 0.05 `w_max`). Growth, the inhibitory prune when a cell is below
target, scaling, the E/I motif, the anti-windup and the STDP rules are unchanged, in every
region. This is a modelling choice standing in for the idea that hippocampal encoding-phase
activity is not a homeostatic error to be corrected by synapse elimination on the encode
timescale; it is not a claim about hippocampal biology.

Mechanism: a per-region parameter `REGIONS[name]["struct_prune_exc"]` (True in every region
on this branch's default, which is today's plant and stays byte-identical: the reference
digest is unchanged); in `Engine.structural_update` the excitatory prune's per-cell mean is
zeroed for cells whose region has the flag False (one mask on the existing expression; the
inhibitory prune, growth and everything downstream untouched). The K1.1 rerun sets
`hpc` False for the run through the driver (`tests/k11_binding.run_experiment(seed,
hpc_prune_exc=False)`, restoring the module afterwards). Flipping the default is the merge
decision and is not made here.

Rerun: the 8.2 protocol unchanged (seed 1, same timings, same rule, same cue, same
criteria), reported exactly as 8.2 plus the before/after `ctx->hpc` and `hpc->hpc` counts
onto the assembly as the owner asked. **Pass or fail on criterion 2 only** (>= 80 % of the
assembly within 50 ticks of the half cue); criteria 1 and 3 and validity are reported. Guard,
report-only: K0.2 (60 s wake stability) in the new mode, and the 8.2 run at fea6d10 is the
same-seed control (the flag True is byte-identical to it).

Predictions, before the run: the `ctx->hpc` count onto assembly cells stays near 1,009
(only weight-prune deaths remain) and `hpc->hpc` within the assembly near 51; the mean
`ctx->hpc` weight onto the assembly still falls, because the two other stripping paths are
untouched: synaptic scaling (assembly cells above target for two sweeps: factor 0.9 per sweep
on used inputs, about -19 %) and pair LTD at 0.71 `w_max` (the rule needs a causal excess
of 2.9 there). Predicted mean 0.708 -> 0.50-0.58 `w_max`. The full pattern is predicted to
re-evoke part of the assembly within 200 ticks (30-60 %), the half cue less, and criterion 2
at 50 ticks is predicted to FAIL; if so the honest reading is that elimination was the
smaller of the three stripping mechanisms and the decision about scaling and LTD on the
binder's afferents is the owner's, not taken here. If it passes, the exemption alone was
enough and the merge question is whether to flip the default.

Files: branch `k11-hpc-prune` (worktree `~/.cache/brain-sim-k11p`): `brainsim/params.py`
(the flag), `brainsim/engine.py` (`structural_update` mask, one per-cell boolean built at
init), `tests/k11_binding.py` (`hpc_prune_exc` argument, context manager, `--hpc-prune-off`
flag), `tests/test_k11_prune_off.py` (unit tests and the `s1` rerun wrapper). Master: this
section and the result.

**K1.1 rerun result (2026-09-12, branch `k11-hpc-prune` at 5099ad9, seed 1, `hpc`
`struct_prune_exc=False`): FAIL on criterion 2.** Valid run (wake throughout, A volley 1.00, cue
volley 1.00, 4 sense-only inject calls, engine pins ok, K0.2 60 s wake stability passes in the new
mode, the digest test passes with the default flag). Numbers the owner asked for: assembly 15 hpc E
cells (4.7 %; 0.50 -> 5.30 Hz during A); B assembly 25 cells, overlap with A 3 cells (20 % of A);
recall of the assembly at 50 / 200 ticks: half cue 0/15 / 0/15, full A 1/15 / 1/15, none 0/15 /
0/15; `ctx->hpc` (E sources) onto the assembly 1,857 synapses at 0.481 `w_max` before A -> 1,860 at
0.403 after; `hpc->hpc` within the assembly 103 at 0.440 -> 103 at 0.364. Elimination onto `hpc`
is gone, as the flag says (counts flat; the only deaths are weight-prune deaths, offset by growth),
and the mean weights still fall 16-17 % during the 2 s encode.

Two corrections to the contract as written. (1) The flag is latched at engine construction, so it
was off for the whole 120 s warm-up, not only the encode: this is a from-t=0 plant change, not a
same-seed control against fea6d10. Without rate-driven elimination the `hpc` E cells keep three
times the excitatory in-degree (189 vs 63 at fea6d10), so the assembly (15 vs 16 cells), the B
assembly (25 vs 6, overlap 20 % vs 6 %) and the counts (1,857 vs 1,009) are not like-for-like and
the numeric predictions of this section are moot; c1 still passes and c3 still passes, but neither
comparison across the two runs is a controlled one. (2) The prediction that the mean would fall to
0.50-0.58 `w_max` was for the fea6d10 network; here it fell 0.481 -> 0.403, the same 16 %.

Attribution, scratch diagnostics on deepcopies made at t = 122,000 (just before A), not contract
runs and not candidates (`~/.cache/scratch/brainsim-k11p/diag_attribution.py`, this branch's
plant; `diag_encode_only.py`, the default plant with the built mask, scaling (`ETA_SCALING`) and
the `hpc` STDP amplitudes switched off on the copies): on this branch's plant, switching scaling off on the copy holds the mean flat (0.464 -> 0.464 `w_max`, `hpc->hpc` 0.399 -> 0.394) while switching `hpc` STDP off leaves the full drop (0.500 -> 0.407); on the default plant, elimination switched off at t = 122,000 alone gives 0.705 -> 0.549 (counts flat, 642 -> 644), elimination plus scaling off 0.709 -> 0.661 (the pair-LTD share), elimination plus `hpc` STDP off 0.709 -> 0.584 (the scaling share), all three off 0.709 -> 0.709. Recall at 50 / 200 ticks for the half cue: as-is 1/16 / 1/16; elimination off 0 / 0.30; elimination and scaling off 0 / 0.22; all three off 0.08 / 0.54 (full pattern 0.38 / 0.69). The assemblies differ between variants (10-18 cells; switching a mechanism changes the RNG draw count), so these are single-seed indications, not like-for-like counts.

Reading, in plant terms: with elimination off the encode still strips the assembly's afferents,
and the stripping is synaptic scaling, not pair LTD: the sweep at t = 123,000 and 124,000 scales
the used inputs of every above-target cell by 0.9, and assembly cells run 5.3 Hz against a 1 Hz
target. Pair STDP onto `hpc` is close to neutral on this timescale in both directions: switching it
off changes neither the weight drop nor the recall. When scaling is switched off the weights hold
and the half cue evokes a quarter of the assembly within 50 ticks and about 60 % within 200, the
full pattern 60-65 % and 80-90 %; that recall is the same with `hpc` STDP off, so it is the
existing feedforward wiring answering the half cue, not a completed memory. Criterion 2 as
written (>= 80 % within 50 ticks) is not met by any variant, and the test cannot yet tell a
feedforward overlap from completion: a half-cue arm from a copy that never saw A is the missing
control (a test-design note, not built; no K1.2).

What this means for the owner's question: elimination was the smallest of the three stripping
paths; the plant's slow homeostat (synaptic scaling on used inputs of above-target cells) removes
the encode within two sweeps, and the pair rule does not write anything the scaling could preserve.
The STDP equation was not changed this turn. The decision about scaling on the binder's afferents
(and whether STDP must change for completion to exist) is the owner's; this round stops here.
Reviews (branch at 5099ad9): architecture found the mask exact and the default path bit-identical,
required the K0.2 guard (rerun, passes), the from-t=0 correction above, the fast-suite log and an
honest pin (the pin now reads the engine's built mask, and the report indexes the flag directly;
`_minimal_out` carries it); security: no findings. Logs: `~/.cache/scratch/brainsim-k11p/`
(`k11_prune_off_seed1.log`, `pytest_s1_prune_off.log` (1 failed on c2 after every validity
assertion passed), `pytest_fast_prune_off.log` (19 passed), `k02_guard_prune_off.log`,
`diag_attribution.log`, `diag_encode_only.log`). Master engine untouched; branch not merged.

### 8.4 K1.1 rerun with a labelled write proxy: `hpc`-afferent LTP-only during encode (predeclared 2026-09-12)

Owner's reading of 8.3 and of the four-arm attribution on the default plant (scratch,
`~/.cache/scratch/brainsim-attr-default/`, accepted as the record of this round): no arm
completes K1.1. Scaling off on the binder's afferents does not complete (half cue 3/19 at
50 ticks); scaling and `hpc` STDP both off does not complete (0/20); and pair STDP does not
raise the `ctx->hpc` mean onto the A assembly (0.700 -> 0.690 with scaling off). The missing
piece is a write on the binder's afferents, not another from-t=0 janitor flag. One slice, one
labelled proxy, default warm-up. Not touched: `sense->ctx`, S1.0, Vogels, replay, K1.2,
two-timescale weights, language, no merge of any Stage 1 branch, no K1.1 bar lowered, and
leftover feedforward is not a pass.

**Proxy label:** *`hpc`-afferent LTP-only during encode.* During the 2 s presentation of A,
and only then, the pair-STDP depression amplitude is zero on excitatory synapses whose
postsynaptic cell is an `hpc` excitatory cell (`ctx E -> hpc E` and `hpc E -> hpc E`; the
engine's per-cell `a_minus_n` for the 320 `hpc` E cells, which is exactly that synapse set
because only excitatory-presynaptic synapses are plastic). `a_plus` is unchanged. When A ends
(t = 124,000) `a_minus` is restored at once to the plant value (0.06). Scaling, elimination,
growth, delays, the inhibitory rules and every other projection stay default; nothing is
applied from t = 0 and the warm-up is the master plant (elimination on, scaling on, pair
amplitudes unchanged). The B arm, presented from the same t = 122,000 copy, gets the same
encode rule during its own 2 s so that "does B form a distinct assembly under the rule" is
like-for-like; the delay and the three recall arms run with the plant's amplitudes. This is a
modelling proxy for "encoding writes without erasing" on the binder's afferents; it is not a
claim that hippocampal LTD is switched off during encoding.

Mechanism: driver-level, engine and params untouched (the branch's engine is byte-identical
to master). `tests/k11_binding.run_experiment(seed, hpc_ltp_only_encode=False)`; with the
flag True the driver wraps each 2 s `present` of A (and of B on its copy) in a context
manager `hpc_ltd_off(eng)` that zeroes `net.a_minus_n` for the `hpc` E cells on that engine
and restores the saved values on exit (exception or not). The output carries
`hpc_ltp_only_encode` and, in `engine_pins`, the mean `hpc` E `a_minus_n` read before A,
during A (read inside the window) and after A: 0.06 / 0.0 / 0.06 in the rerun, 0.06 / 0.06 /
0.06 in the default. `main()` takes `--hpc-ltp-only`. The default path is unchanged: the same
call sequence as 8.2, so the fea6d10 numbers are the same-seed control.

Rerun: the 8.2 protocol unchanged (seed 1, copies at t = 122,000, same timings, same cue,
same criteria), one run. **Pass or fail on criterion 2 only**; criteria 1 and 3 and validity
are reported. Reported: A assembly size and percentage, B size and overlap, recall counts and
fractions at 50 and 200 ticks for half cue / full A / none, `ctx->hpc` and `hpc->hpc` onto
the A assembly (count and mean w/w_max before A -> after A) and, as a scratch diagnostic on
copies, the number of pair-STDP LTP and LTD applications on those synapses during the 2 s in
the rerun and in a default control.

Predictions, before the run: relative to the default (0.708 -> 0.587 on `ctx->hpc` onto the
assembly) the mean falls less or rises, because the pair rule's net effect on those synapses
in the default was depression; scaling (two sweeps at 0.9 on used inputs of above-target
cells) and elimination of the weakest still act during the encode and during the 1 s delay,
so a rise above the starting 0.708 requires the LTP term (soft-bounded, headroom about 0.3
`w_max`) to outrun about 0.12 of loss. The assembly is predicted to be larger than 16 cells
(LTD no longer limits recurrent recruitment) and criterion 1 (<= 20) may be at risk. If the
mean does not rise above its pre-A value, the reading is that pair timing produced no usable
LTP on the binder's afferents at this rate and the work stops without adding a second rule;
if it rises and the half cue still misses 80 % in 50 ticks, the write exists but is not
enough against the delay-period homeostasis, and that decision is the owner's.

Files: branch `k11-ltp-only` (worktree `~/.cache/brain-sim-k11ltp`): `tests/k11_binding.py`
(`hpc_ltp_only_encode` argument, `hpc_ltd_off` context manager, `--hpc-ltp-only` flag, pins),
`tests/test_k11_ltp_only.py` (unit tests and the `s1` rerun wrapper). Master: this section
and the result.

**K1.1 rerun result (2026-09-12, branch `k11-ltp-only` at 3210341, seed 1,
`hpc_ltp_only_encode=True`): FAIL on criterion 2, and the write did not appear.** Valid run
(wake throughout, A volley 1.00, cue volley 1.00, injections sense-only, engine pins ok
including the proxy pins read from the engine's array: `hpc` E `a_minus` 0.06 before A, 0.0 at
both ends of the A window and of the B window, 0.06 after each). Numbers: A assembly 20 `hpc`
E cells (6.2 %; 0.40 -> 5.95 Hz during A, criterion 1 at its edge as predicted); B assembly 12,
overlap with A 2 (10 % of A); recall of the assembly, count/size, within 50 / 200 ticks:
half cue 0/20 (0.00) / 0/20 (0.00), full A 1/20 (0.05) / 3/20 (0.15), none 0/20 / 0/20;
`ctx E -> hpc` onto the assembly 1,247 synapses at 0.712 `w_max` before A -> 1,092 at 0.657
after; `hpc -> hpc` within the assembly 68 at 0.628 -> 38 at 0.659. Default control (fea6d10,
reproduced exactly on the same seed path by the round-20 attribution): 16 cells, 1,009 at
0.708 -> 849 at 0.587, 51 at 0.624 -> 32 at 0.600, half cue 1/16.

Pair-STDP applications on the E -> `hpc` E synapse set during the 2 s (scratch diagnostic on
copies at t = 122,000, `~/.cache/scratch/brainsim-k11ltp/diag_ltp_ltd_counts.py`, exact
counts mirroring the engine's delivery bucket and incoming gather; magnitudes in weight units
summed over the set): default control, LTD applied 241,710 times (54,359 with a live
post-trace), total -1,169; LTP applied 75,970 times (41,298 with a live pre-trace), total
+558; the two sweeps (scaling and kills) -3,094. Proxy: LTD applied 243,048 times at zero
amplitude, total 0; LTP 82,009 (45,702), total +582; sweeps -3,524. So the pair rule's net
effect in the default was depression (-611 over the set) and removing it buys about +600,
while the two scaling sweeps during the encode remove five to six times that.

Reading: the `ctx -> hpc` mean onto the assembly did not rise (0.712 -> 0.657; the default
fell to 0.587), and the half cue evoked nothing (0/20 at 50 and at 200 ticks; the full pattern
3/20 at 200). Pair timing at this rate produced no usable LTP on the binder's afferents: the
potentiation that exists is small against synaptic scaling on the used inputs of a 6 Hz
assembly with a 1 Hz target, and the within-assembly rise (0.628 -> 0.659) is the elimination
of the weakest recurrents plus a little LTP, not a completed clique. Per the contract, no
second rule was added and the work stops here. Reviews at 17713cc/3210341: architecture OK
with notes (four taken: the proxy pins are folded into `engine_pins_ok`, read at both ends of
each window, the `hpc` E ids are asserted against the engine's `is_exc` mask, one helper; the
report line's `.get` and the duplicated digest guard noted, left); security: no findings.
Logs: `~/.cache/scratch/brainsim-k11ltp/` (`k11_ltp_only_seed1.log`, `pytest_s1_ltp_only.log`
(1 failed on criterion 2 after every validity assertion passed, 7 deselected, 61.7 s), `pytest_fast_ltp_only.log` (100 passed, 11 deselected, 55 s), `diag_ltp_ltd_counts.log`). Master
engine untouched (the branch's `brainsim/` is byte-identical to master); branch not merged.

### 8.5 K1.1 rerun with a labelled proxy: `hpc` encode window (predeclared 2026-09-13)

Owner's reading of 8.4, accepted as the record: LTP-only during encode is a FAIL, with a
correction to its one-sentence reading: pair timing DID produce LTP (about 82,000 applications,
+582 weight on the E -> `hpc` E set over the 2 s); it is not usable because the two scaling
and kill sweeps inside the window remove about six times that (+582 against -3,500), so the
`ctx->hpc` mean onto the assembly still fell (0.712 -> 0.657) and the half cue evoked 0/20.
Depression off alone cannot beat the mop. One slice, one labelled proxy, default warm-up. Not
touched: `sense->ctx`, S1.0, Vogels, organs, replay, K1.2, two-timescale weights, language;
no merge of any Stage 1 branch; no K1.1 bar lowered; `a_plus` not boosted; `hpc` rate targets
unchanged; a weight rise without half-cue completion is not a pass.

**Proxy label:** *`hpc` encode window.* During the 2 s presentation of A, and only then, on
the excitatory synapses whose postsynaptic cell is an `hpc` excitatory cell (`ctx E -> hpc E`
and `hpc E -> hpc E`, the only plastic synapses onto those cells): (1) the pair-STDP
depression amplitude is zero (`a_plus` unchanged), (2) synaptic scaling does not touch them
(the sweep's factor is not applied to used inputs of those cells), (3) the rate-driven
elimination does not run on them (the excitatory prune's per-cell mean is zero for those
cells; the weight prune at 0.05 `w_max`, which is not rate-driven, stays on, and with scaling
off it has nothing new to remove). When A ends (t = 124,000) all three are restored at once.
Nothing is latched at construction: the mask is runtime state, set and cleared by the driver.
Growth, the inhibitory rules, the anti-windup, delays, every other projection and the whole
warm-up stay default. The B arm, from the same t = 122,000 copy, gets the same window during
its own 2 s; the delay and the three recall arms run on the plain plant (the 125,000 sweep is
outside the window). This is a modelling proxy for "the binder's afferents are not mopped
while a pattern is being written"; it is not a claim about hippocampal biology.

Mechanism: `Engine.encode_mask`, a per-cell boolean array created all-False in `__init__`
and never set by the engine itself. `_slow_sweep` drops from the scaling set the used
synapses whose postsynaptic cell is masked; `structural_update` multiplies the excitatory
prune's per-cell mean by `~encode_mask`. With the mask all False both expressions are the
plant as it is today (the reference digest is unchanged, pinned by test). The driver
(`tests/k11_binding.run_experiment(seed, hpc_encode_window=False)`) wraps each 2 s
`present` of A (and of B on its copy) in a context manager `hpc_encode_window(eng)` that
sets `encode_mask` True for the 320 `hpc` E cells (ids asserted against the engine's
`is_exc`) and zeroes their `a_minus_n`, restoring both on exit (exception or not). The output
carries `hpc_encode_window` and, in `engine_pins["encode_window"]`, three series read from
the engine at the same seven moments (before A, start and end of the A window, after A, start
and end of the B window, after B): the mean `hpc` E `a_minus_n` (0.06 / 0 / 0 / 0.06 / 0 / 0
/ 0.06 when on, 0.06 throughout when off), the fraction of `hpc` E cells masked (0 / 1 / 1 /
0 / 1 / 1 / 0 when on, 0 throughout when off) and the fraction of all other cells masked (0
throughout, both modes). Those series are part of `engine_pins_ok`, so a run whose window
did not apply or did not clear is invalid, not a result. `main()` takes
`--hpc-encode-window`. The default path is the same call sequence as 8.2 (the fea6d10 run is
the same-seed control) and, if cheap, the control is rerun on the same seed alongside.

Rerun: the 8.2 protocol unchanged (seed 1, copies at t = 122,000, same timings, same cue,
same criteria), one run. **Pass or fail on criterion 2 only**; criteria 1 and 3 and validity
are reported. Reported: A assembly size and percentage, B size and overlap, recall counts and
fractions at 50 and 200 ticks for half cue / full A / none, `ctx->hpc` and `hpc->hpc` onto
the A assembly (count and mean w/w_max before A -> after A), and the same budget table as
8.4 (pair LTP and LTD applications and totals, and the sweep totals, on the E -> `hpc` E set
during the 2 s), proxy and default control.

Predictions, before the run: inside the window nothing removes weight from the set, so the
`ctx->hpc` count onto the assembly stays near its pre-A value (only weight-prune deaths,
which need a weight below 0.05 `w_max`) and the mean rises by the LTP budget alone, about
+0.02 to +0.05 `w_max` (from 0.71 to 0.73-0.76), with a similar rise within the assembly; the
assembly is predicted at or above 20 cells (criterion 1 at risk). The 1 s delay then runs on
the plain plant, with one sweep at t = 125,000 while the assembly's rate EMA is still above
target, so about a tenth of that is removed before the cue. Criterion 2 is predicted to FAIL:
in the round-20 attribution the half cue evoked 0/20 even when the weights were held at 0.78
`w_max`. If the mean does not rise, the window still produced no net write, and the work
stops without a co-firing rule; if it rises and the half cue misses, that is a scribble the
cue cannot read, and the work stops without retuning the recall windows.

Files: branch `k11-encode-window` (worktree `~/.cache/brain-sim-k11ew`): `brainsim/engine.py`
(`encode_mask`, two masked expressions), `tests/k11_binding.py` (`hpc_encode_window`
argument and context manager, `--hpc-encode-window`, pins), `tests/test_k11_encode_window.py`
(unit tests, digest guard and the `s1` rerun wrapper). Master: this section and the result.

**K1.1 rerun result (2026-09-13, branch `k11-encode-window` at 8fedf88, seed 1,
`hpc_encode_window=True`): FAIL on criterion 2; the write appeared, the cue cannot read it.**
Valid run (wake throughout, A volley 1.00, cue volley 1.00, injections sense-only, engine pins
ok including the window pins read from the engine: `hpc` E `a_minus` 0.06 / 0 / 0 / 0.06 / 0 /
0 / 0.06 and the `hpc` E mask fraction 0 / 1 / 1 / 0 / 1 / 1 / 0 at the seven moments, other
cells never masked). Same-seed default control rerun on this branch: identical to fea6d10 in
every number (assembly 16, 1,009 at 0.708 -> 849 at 0.587, half cue 1/16), which is the
byte-identity of the all-False mask shown on the real protocol, not only on the digest.
Numbers: A assembly 39 `hpc` E cells (12.2 %; 0.64 -> 7.28 Hz during A; criterion 1 fails,
39 > 20); B assembly 29, overlap with A 3 (7.7 % of A); recall of the assembly, count/size,
within 50 / 200 ticks: half cue 3/39 (0.08) / 13/39 (0.33), full A 5/39 (0.13) / 14/39
(0.36), none 2/39 (0.05) / 5/39 (0.13); `ctx E -> hpc` onto the assembly 2,378 synapses at
0.711 `w_max` before A -> 2,378 at 0.757 after; `hpc -> hpc` within the assembly 275 at
0.653 -> 275 at 0.701. Budget on the E -> `hpc` E set during the 2 s (scratch diagnostic on
copies, `~/.cache/scratch/brainsim-k11ew/diag_budget_encode_window.py`, same method as
8.4): default control, LTD 241,710 applications (54,359 with a live post-trace) total
-1,169, LTP 75,970 (41,298) total +558, two sweeps -3,094; window: LTD 251,181 applications at
zero amplitude, LTP 100,698 (59,280) total +726, two sweeps +1.8 (growth only; nothing
removed).

Reading: the `ctx -> hpc` mean onto the assembly ROSE (0.711 -> 0.757, and 0.653 -> 0.701
within the assembly, counts flat), so with the mop held off for 2 s the pair rule does write;
the prediction of +0.02 to +0.05 was met (+0.046). The half cue did not meet completion: 3 of
39 within 50 ticks, 13 of 39 within 200, against 2 and 5 with no stimulus. That is a scribble
the cue cannot read: the write is spread over a 39-cell assembly that recruited a further 23
cells once nothing was pruning the recurrents (criterion 1 fails too), the potentiation is a
uniform few per cent on every used afferent rather than a selective one on the cued half's
targets, and the 1 s delay on the plain plant then puts one sweep on it before the cue. Per the
contract, the recall windows were not retuned and no co-firing rule was added; the work stops
here. Reviews at 8fedf88: architecture OK with notes (taken: the scaling-exemption test now compares only slots that still hold the same synapse, bfd9c02; left, noted: no boundary tests that the weight prune, the inhibitory prune and growth still act on masked cells, and the `hpc_encode_window` kwarg shadows the context manager inside the driver, aliased); security: no findings. Logs: `~/.cache/scratch/brainsim-k11ew/`
(`k11_encode_window_seed1.log`, `k11_default_control_seed1.log`, `pytest_s1_encode_window.log`
(1 failed on criterion 2 after every validity assertion passed, 56.9 s), `pytest_fast_encode_window.log` (105 passed, 11 deselected, 61.8 s), `diag_budget_encode_window.log`).
Engine change confined to the branch (runtime mask, all False by default); master untouched;
branch not merged.

### 8.6 K1.1 rerun with a labelled proxy on top of the encode window: sparse co-fire write (predeclared 2026-09-13)

Owner's reading of 8.5, accepted as the record: the net write is real (`ctx->hpc` onto the
assembly 0.711 -> 0.757, counts flat, sweeps +1.8) and K1.1 still fails. Two facts are the
problem: (1) the assembly bloated from 16 to 39 cells because the recurrents were not pruned
during A; (2) the write is a uniform few per cent on every used afferent, so a half cue cannot
select the clique (3/39 at 50 ticks, 13/39 at 200, against 2/39 and 5/39 with nothing). One
slice, one labelled proxy, on top of the 8.5 window. Not touched: `sense->ctx` STDP, scaling
and S1.0; no merge of any Stage 1 branch; no Vogels, organs, replay, K1.2, two-timescale
weights, language; no K1.1 bar lowered, no recall window widened, no sweep over the write
size; 13/39 at 200 ticks is not a pass.

**Proxy label:** *sparse co-fire write.* During the 2 s presentation of A, and only then:
the `hpc` encode window of 8.5 is on exactly as at 8fedf88 (pair depression zero, scaling and
the rate-driven elimination off on the excitatory inputs of the `hpc` E cells, restored when A
ends). Once, at the end of A and before the window is restored: W = the 16 `hpc` E cells with
the highest spike count during A, taken from the engine's own per-cell counts over the 2 s
(fixed k = 16; ties broken by the lower cell id, deterministic), a proxy for "write the sparse
winners", not a teacher signal and not biology; donors = the `ctx` E cells that emitted at
least one spike during A; on the existing alive synapses donor -> W only, w += 0.15 `w_max`
(the postsynaptic cell's `w_max`), then clamped at `w_max`. No new synapses, no write onto
`hpc` cells outside W, no `hpc -> hpc` write, one write size, no search. The B arm, from the
same t = 122,000 copy, gets the same treatment with its own top 16 from the B presentation and
its own donors. The delay and the recall arms run on the plain plant.

Mechanism: driver-level on top of the branch engine's runtime mask (nothing latched at
construction, no further engine change). `tests/k11_binding.run_experiment(seed,
hpc_encode_window=False, sparse_write=False)`; `sparse_write=True` requires the window
(asserted). A pure helper `sparse_cofire_write(net, counts, hpc_e_ids, ctx_e_ids, k, delta_frac)`
selects W and the donors from the count vector, bumps the synapses and returns the record
(W, donor count, synapses bumped, synapses clamped, mean w/`w_max` onto W before and after
the bump); the driver calls it inside the A window after the presentation and before exit,
and again inside the B window on the B copy. The output carries `sparse_write` and
`sparse_write_B` (the record plus `applied_inside_window`, read from the engine at the write:
`hpc` E mask fraction 1 and `a_minus` 0), the 8.5 window pins, `synapses["ctx_to_hpc_onto_W"]`
and `synapses["ctx_to_hpc_onto_hpc_e_not_W"]` (count and mean before A -> after A), the
overlap of W with the assembly, and per arm `recall_W` at 50 / 100 / 200 ticks next to the
assembly's `recall`. `main()` takes `--sparse-write` (implies the window). The default path
is the same call sequence as 8.2, and the window-only path the same as 8.5.

Rerun: the 8.2 protocol unchanged (seed 1, copies at t = 122,000, same timings, same cue,
same criteria), one run; the same-seed default control rerun alongside. **Pass or fail on
criterion 2 only, as defined (>= 80 % of the assembly within 50 ticks of the half cue)**; the
same bar applied to W is reported as `c2_recall_50_W`, not asserted, and a W completion
without the assembly's is reported as what it is, not called a K1.1 pass. Reported: the
assembly as currently defined (size, percentage, B size, overlap) and W (overlap with that
assembly); recall of W and of the assembly at 50 and 200 ticks for half cue / full A / none;
`ctx->hpc` mean w/`w_max` before A -> after A onto W and onto `hpc` E not in W; synapse
counts onto W before -> after (expected flat: nothing is removed inside the window, growth
may add a few).

Predictions, before the run: W overlaps the 39-cell assembly heavily (the assembly is the
>= 4 Hz excess set and W its top 16 by count); about 2,000 donor -> W synapses at about 0.71
`w_max` rise to about 0.86 after the bump (some clamp), while `ctx->hpc` onto `hpc` E outside
W keeps the 8.5 behaviour (about +0.01 to +0.05 from LTP on the used ones, flat on the rest):
contrast is predicted to appear. The half cue is predicted to evoke more of W than of the rest
of the assembly, but criterion 2 at 50 ticks is still predicted to FAIL: the cue is 20 `sense`
cells whose `ctx` targets are a fraction of the donors, the 125,000 sweep on the plain plant
scales W's used inputs by 0.9 once before the cue, and the recurrent write that would let the
cued part of W recruit the rest is not made this slice. If contrast does not appear the write
size is not retuned; if it appears and the half cue still fails, no `ctx`-side cue is added;
either way the work stops here.

Files: branch `k11-sparse-write` (worktree `~/.cache/brain-sim-k11sw`, from
`k11-encode-window`): `tests/k11_binding.py` (`sparse_cofire_write`, `sparse_write` argument
and flag, records, `recall_W`, the two W synapse groups), `tests/test_k11_sparse_write.py`
(unit tests on the helper, digest guard, the `s1` rerun wrapper). Master: this section and the
result.

**K1.1 rerun result (2026-09-13, branch `k11-sparse-write` at 15ff858, seed 1,
`hpc_encode_window=True, sparse_write=True`): FAIL on criterion 2 (and on criterion 1);
contrast appeared, the half cue does not complete W within 50 ticks.** Valid run (wake
throughout, A volley 1.00, cue volley 1.00, injections sense-only, engine pins ok, the 8.5
window pins as at 8fedf88, both writes applied inside their windows with the mask at 1 and
`a_minus` at 0). The same-seed default control rerun on this branch is identical to fea6d10.
Numbers: assembly as defined 39 `hpc` E cells (12.2 %; criterion 1 fails), B 29, overlap 3
(7.7 % of A); W = the top 16 by A count, all 16 inside the assembly; donors 1,596 `ctx` E cells;
1,036 existing donor -> W synapses bumped, 356 of them clamped at `w_max`; B's own W: 1,598
donors, 969 bumped, 291 clamped. `ctx -> hpc` mean w/`w_max` before A -> after A: onto W 0.692
-> 0.874 (count 1,036 -> 1,036, flat); onto `hpc` E not in W 0.685 -> 0.686 (16,923 -> 17,165,
growth only); onto the 39-cell assembly 0.711 -> 0.810. Recall, count/size (fraction), within
50 / 200 ticks: W, half cue 1/16 (0.06) / 12/16 (0.75), full A 11/16 (0.69) / 14/16 (0.88),
none 0/16 (0.00) / 5/16 (0.31); assembly, half cue 3/39 (0.08) / 20/39 (0.51), full A 16/39
(0.41) / 23/39 (0.59), none 0/39 (0.00) / 7/39 (0.18). At 100 ticks: W half cue 6/16 (0.38).
Criterion 3 passes in the cue arm (7 non-assembly cells spiking in 50 ticks against 13.6
expected).

Reading: contrast appeared exactly where it was written (W up 0.18 `w_max`, the other 304
`hpc` E cells flat), and the readout follows the contrast: the full pattern now evokes 11 of
16 W cells within 50 ticks (none: 0) and the half cue 12 of 16 within 200 ticks (none: 5),
against 1 of 16 at 50. That is a written, selectively readable trace with a slow and partial
readout: the 20 cued `sense` cells drive a fraction of the donors, so W's summed drive under
the half cue is a fraction of what the full pattern gives, and the recruitment from the cued
part of W to the rest, which is what completion within 50 ticks needs, has no write behind it
(`hpc -> hpc` was not written this slice; within-assembly 0.653 -> 0.701 is the 8.5 LTP only).
Per the contract: the write size is not retuned, no `ctx`-side cue is added, the windows are
not widened, and 12/16 at 200 ticks is not a pass; the work stops here. Reviews at 11a3d79, run repeated at 15ff858 with identical numbers: architecture OK with notes (taken: `select_winners` casts counts to int64, one helper for the window-on pin, the W criterion is absent rather than False when W is not measured; left, noted: `n_clamped` counts synapses at `w_max` after the bump, including any already there, so it bounds the delivered write from above); security: no findings. Logs: `~/.cache/scratch/brainsim-k11sw/` (`k11_sparse_write_seed1.log`,
`k11_default_control_seed1.log`, `pytest_s1_sparse_write.log` (1 failed on criterion 2 after
every validity assertion passed, 63 s), `pytest_fast_sparse_write.log` (117 passed, 12
deselected, 62 s)). Engine identical to the parent branch (runtime mask only); master
untouched; branch not merged.

### 8.7 K1.1 rerun with a labelled proxy on top of 8.5 and 8.6: W recurrent co-fire (predeclared 2026-09-13)

Owner's reading of 8.6, accepted as the record: the contrast is real (donor -> W 0.692 ->
0.874, non-W flat 0.685 -> 0.686), the full pattern reads W (11/16 at 50 ticks against 0/16
with nothing) and the half cue does not complete W at 50 ticks (1/16). Working hypothesis:
the half cue drives only the reachable part of W, and W -> W was not written, so the clique
cannot finish. One slice, one labelled proxy, on top of the encode window (8.5) and the sparse
co-fire write (8.6), both unchanged (same window, same W = top 16 by the engine's own A
counts, same donors, same donor -> W write of 0.15 `w_max` clamped on existing synapses at the
end of A before the window is restored; k and the write size not changed). Not touched:
`sense->ctx`; no merge of any Stage 1 branch; no Vogels, organs, replay, K1.2, two-timescale
weights, language; no K1.1 bar lowered, no recall window widened, no write-size retune, no
`ctx`-side cue; 12/16 at 200 ticks is not a pass.

**Proxy label:** *W recurrent co-fire.* Exactly one thing is added, at the same moment as the
afferent write: on the existing alive `hpc` E -> `hpc` E synapses with both ends in W,
w += 0.15 `w_max` (the postsynaptic cell's), clamped at `w_max`. No synapse is grown; nothing
W -> non-W or non-W -> W is written; the B copy gets the same rule on its own W. One write size,
no search. This is a modelling proxy for "the winners that fired together are wired
together"; it is not a claim about hippocampal biology.

Mechanism: driver-level, engine identical to the parent branch (the runtime mask only).
`tests/k11_binding.run_experiment(seed, hpc_encode_window=False, sparse_write=False,
recurrent_write=False)`; `recurrent_write=True` requires `sparse_write` (asserted). A pure
helper `recurrent_cofire_write(net, W, delta_frac)` bumps the W -> W synapses and returns the
record (`n_existing` alive W -> W synapses, `n_synapses_bumped` (equal to it), `n_clamped` at
`w_max` after the bump, mean w/`w_max` over them before and after); the driver calls it right
after `sparse_cofire_write` inside the A window (and inside the B window on the copy), so the
`applied_inside_window` pin covers both. The output carries `recurrent_write`,
`recurrent_write_A`, `recurrent_write_B`, and three further synapse groups before A -> after A:
`donor_to_W`, `donor_to_hpc_e_not_W` (donors = the `ctx` E cells that spiked during A, applied
to both snapshots) and `hpc_hpc_within_W`. `main()` takes `--recurrent-write` (implies the
two proxies below it). The default, window-only and sparse-write paths keep their exact call
sequences.

Rerun: the 8.2 protocol unchanged, one run; the same-seed default control rerun alongside.
**Pass or fail on criterion 2 only, as defined**; the same bar on W is reported as
`c2_recall_50_W`, not asserted, and a W completion without the assembly's is reported as what
it is. Reported: assembly size and percentage, W, B size and overlap; recall of W and of the
assembly at 50 and 200 ticks for half cue / full A / none; mean w/`w_max` before A -> after A
for donor -> W, W -> W and donor -> non-W; how many W -> W synapses existed, were bumped and
hit `w_max`; validity with the window pins as before.

Predictions, before the run: at 8fedf88 the 39-cell assembly had 275 recurrent synapses
within it at 0.653 -> 0.701 `w_max`, so W -> W should hold on the order of 50 alive synapses
(16 cells, in-degree about 76 from about 400 `hpc` E sources), at about 0.70 before and about
0.85 after the bump, some clamped: the W -> W mean is predicted to rise. With about 3 W
inputs per W cell at 0.85 of a 3.0 mV `w_max`, the recurrent drive onto a W cell from the cued
part of W is a few mV per volley against a threshold that the half cue's feedforward drive
already brings the reachable cells to; the half cue is predicted to evoke more of W than the
1/16 of 8.6 within 50 ticks but not 80 %: FAIL on criterion 2 is still the prediction, and if
the W -> W mean does not rise, nothing is grown this turn; if it rises and the half cue still
fails, the window is not widened.

Files: branch `k11-recurrent-write` (worktree `~/.cache/brain-sim-k11rw`, from
`k11-sparse-write`): `tests/k11_binding.py` (`recurrent_cofire_write`, `recurrent_write`
argument and flag, records, the three synapse groups), `tests/test_k11_recurrent_write.py`
(unit tests on the helper, digest guard, the `s1` rerun wrapper). Master: this section and the
result.

**K1.1 rerun result (2026-09-13, branch `k11-recurrent-write` at e3cf583, seed 1, window +
sparse write + recurrent write): FAIL on criterion 2 (and on criterion 1); the W -> W mean
rose, and the trace now fires without a cue.** Valid run (wake throughout, A volley 1.00, cue
volley 1.00, injections sense-only, engine pins ok, the 8.5 window pins as before, both
writes inside their windows). Same-seed default control identical to fea6d10. Numbers:
assembly as defined 39 `hpc` E cells (12.2 %), B 29, overlap 3 (7.7 %); W = the same 16 as
8.6, all inside the assembly; donors 1,596; donor -> W 1,036 synapses bumped (356 at `w_max`
after); W -> W: 67 alive synapses existed, 67 bumped, 21 at `w_max` after; B's own W: 51
existed, 51 bumped, 19 at `w_max`. Mean w/`w_max` before A -> after A: donor -> W 0.692 ->
0.874 (1,036 -> 1,036); W -> W 0.672 -> 0.860 (67 -> 67); donor -> non-W `hpc` E 0.685 ->
0.686 (16,888 -> 17,130, growth only). Recall, count/size (fraction), within 50 / 200 ticks:
W, half cue 6/16 (0.38) / 9/16 (0.56), full A 8/16 (0.50) / 13/16 (0.81), none 6/16 (0.38) /
6/16 (0.38); assembly, half cue 8/39 (0.21) / 16/39 (0.41), full A 13/39 (0.33) / 24/39
(0.62), none 7/39 (0.18) / 11/39 (0.28). The first assembly spike comes at tick 9 in every
arm, including the one with no stimulus; `hpc` E fired at 1.3 Hz in the none arm's first 50
ticks against 0.5 Hz at 8.6.

Reading: the W -> W mean rose as predicted, and the half cue still does not complete W within
50 ticks (6/16). But the more important number is the none arm: with the recurrent write in
place the same 6 of 16 W cells fire within 50 ticks with no cue at all, and 7 of the 39
assembly cells, where at 8.6 it was 0. The 67 recurrent synapses at 0.86 `w_max` (about four
per W cell at about 2.6 mV) plus the 1,036 potentiated afferents from `ctx` cells at their
4 Hz background are enough for W to ignite on its own during the 1 s delay and after; the
half cue adds nothing at 50 ticks (6/16 with it, 6/16 without) and the full pattern only 2
more. The clique became a spontaneous attractor, not a cue-completed one: the cue no longer
reads the trace selectively, and criterion 3 is only saved by the assembly's size (25
non-assembly cells spiking in the cue arm against 13.6 expected, under the 19.5 cap). Per the
contract the window is not widened and nothing is grown; the work stops here. Reviews at
6afc35c, run repeated at e3cf583 with identical numbers: architecture OK with notes (taken: `sparse_cofire_write` returns the donor ids and the donor groups index the set actually written, the recurrent helper's docstring states the caller passes `hpc` E ids; left, noted: the fake nets in the unit tests use a uniform `w_max`, so the postsynaptic-`w_max` clause is unpinned there, and the three donor/W groups are emitted on the sparse-write path too, a reporting-only difference from the 8.6 output); security: no findings. Logs:
`~/.cache/scratch/brainsim-k11rw/` (`k11_recurrent_write_seed1.log`,
`k11_default_control_seed1.log`, `pytest_s1_recurrent_write.log` (1 failed on criterion 2 after every validity assertion passed, 90 s),
`pytest_fast_recurrent_write.log` (127 passed, 13 deselected, 85 s)). Engine identical to the parent branch;
master untouched; branch not merged.

### 8.8 K1.1 rerun with a labelled proxy on the selective parent: restricted donors (predeclared 2026-09-13)

Owner's reading of 8.7, accepted as the record: the W -> W mean rose (0.672 -> 0.860) and the
half cue does not complete W at 50 ticks (6/16); decisive, the none arm also gives 6/16 at 50
ticks, so the clique is a spontaneous attractor (`hpc` E 1.3 Hz in the none arm against
0.5 Hz on the sparse-write branch): 0.15 `w_max` on 67 W -> W synapses plus 1,036 donor -> W
synapses from 1,596 `ctx` cells is too much fan-in. `k11-recurrent-write` stays unmerged. This
slice goes back to the SELECTIVE parent (the sparse-write branch, 8.6 at 15ff858: encode
window plus the write onto W, k = 16, 0.15 `w_max` on existing synapses at the end of A,
clamped; no W -> W write) and changes only the donor set. Not touched: `sense->ctx`; no merge
of any Stage 1 branch; no Vogels, organs, replay, K1.2, two-timescale weights, language; no
K1.1 bar lowered, no recall window widened, no write-size sweep, no synapse grown, no W -> W.

**Proxy label:** *restricted donors.* The donors are the 64 `ctx` E cells with the highest
spike count during A (fixed k = 64, from the engine's own per-cell counts over the 2 s, ties
by the lower id), instead of every `ctx` E cell that spiked at least once (about 1,596). Same
bump, on the existing alive donor -> W synapses only. A modelling proxy for "the afferent
write goes to the strongly co-active inputs", not biology. The B copy uses its own top 64
from the B presentation.

Mechanism: driver-level, engine identical to the parent branch (the runtime mask only).
`DONOR_K = 64`; `sparse_cofire_write(net, counts, hpc_e_ids, ctx_e_ids, k, delta_frac,
donor_k=None)`: with `donor_k` None the 8.6 rule (every spiking `ctx` E cell), with
`donor_k` an integer the top-`donor_k` by `select_winners` over `ctx_e_ids`; the record
gains `donor_ids` and `donor_k`. `run_experiment(seed, hpc_encode_window=False,
sparse_write=False, restricted_donors=False)`; `restricted_donors=True` requires
`sparse_write` (asserted) and passes `donor_k=DONOR_K` to both writes. New synapse groups
before A -> after A, keyed on A's donors: `donor_to_W`, `other_ctx_e_to_W` (`ctx` E cells not
donors -> W), next to the existing `ctx_to_hpc_onto_W` and `ctx_to_hpc_onto_hpc_e_not_W`.
`main()` takes `--restricted-donors` (implies the two proxies below). The default,
window-only and 8.6 sparse-write paths keep their exact call sequences (`donor_k` None).

Rerun: the 8.2 protocol unchanged, one run; the same-seed default control rerun alongside.
**Pass or fail on criterion 2 only, as defined**; `c2_recall_50_W` reported, not asserted.
Reported: assembly size and percentage, W, B size and overlap; donor count and donor -> W
synapse count, how many hit `w_max`; mean w/`w_max` before A -> after A for donor -> W, other
`ctx` E -> W and `ctx` -> non-W; recall of W (and of the assembly) at 50 and 200 ticks for
half cue / full A / none; the `hpc` E rate in the none arm's first 50 ticks against 0.5 Hz
(8.6) and 1.3 Hz (8.7); the window pins as before.

Predictions, before the run: the 64 strongest `ctx` cells carry on the order of 60-100 alive
synapses onto the 16 W cells (about 1,036 from 1,596 donors at 8.6, so roughly 4 % of that),
which rise from about 0.70 to about 0.85 `w_max` with a few clamped; the other `ctx` E -> W
synapses keep the 8.5 behaviour (LTP only, a few per cent); `ctx` -> non-W flat. With the
write confined to under a hundred synapses the none arm is predicted back near 0/16 at 50
ticks and `hpc` E near 0.5 Hz (selectivity returns), the full pattern is predicted to read W
less well than at 8.6 (11/16 at 50 ticks there) because most of the 8.6 write is gone, and
the half cue is predicted to FAIL criterion 2 at 50 ticks: the cued `sense` half drives a
fraction of the 64 donors and there is no recurrent write to finish the clique. If the none
arm ignites W again, k is not cut further this turn; if selectivity returns and the half cue
still fails, W -> W is not re-added this turn.

Files: branch `k11-restricted-donors` (worktree `~/.cache/brain-sim-k11rd`, from
`k11-sparse-write`): `tests/k11_binding.py` (`DONOR_K`, `donor_k` on the write,
`restricted_donors` argument and flag, `donor_ids`, the two groups),
`tests/test_k11_restricted_donors.py` (unit tests on the donor rule, digest guard, the `s1`
rerun wrapper). Master: this section and the result.

**K1.1 rerun result (2026-09-13, branch `k11-restricted-donors` at bf01095, seed 1, window +
sparse write with donors = the top 64 `ctx` E cells by A count, no W -> W): FAIL on criterion
2 (and on criterion 1); the write landed where written, and selectivity did not return.**
Valid run (wake throughout, A volley 1.00, cue volley 1.00, injections sense-only, engine
pins ok, the 8.5 window pins as before, both writes inside their windows). Same-seed default
control identical to fea6d10. Numbers: assembly as defined 39 `hpc` E cells (12.2 %), B 29,
overlap 3 (7.7 %); W = the same 16 as 8.6, all inside the assembly; donors 64 (every one of
them spiked during A; the 8.6 rule gave 1,596); donor -> W: 156 alive synapses existed, 156
bumped, 63 at `w_max` after the bump, of which 13 were already there before it; B's own 64
donors: 114 bumped, 36 at `w_max` after (7 before). Mean w/`w_max` before A -> after A:
donor -> W 0.699 -> 0.899 (156 -> 156); other `ctx` E -> W (not donors) 0.690 -> 0.746
(880 -> 880, the window's own LTP, nothing bumped); all `ctx` E -> W 0.692 -> 0.769
(1,036 -> 1,036; 0.874 at 8.6); `ctx` -> non-W `hpc` E 0.685 -> 0.686 (16,923 -> 17,165,
growth only). Recall, count/size (fraction), within 50 / 200 ticks: W, half cue 0/16 (0.00)
/ 3/16 (0.19), full A 5/16 (0.31) / 10/16 (0.62), none 2/16 (0.12) / 3/16 (0.19); assembly,
half cue 6/39 (0.15) / 11/39 (0.28), full A 13/39 (0.33) / 23/39 (0.59), none 9/39 (0.23) /
11/39 (0.28). The first assembly spike comes at tick 1 in every arm, including the one with
no stimulus. `hpc` E in the none arm's first 50 ticks: 2.0 Hz (0.5 Hz at 8.6, 1.3 Hz at 8.7);
half cue 1.9 Hz, full A 3.0 Hz. For scale, the unstimulated default plant at the same seed
over the 2 s baseline (t 120,000 -> 122,000, forty 50-tick bins) gives 0.96 Hz mean, 0.26 sd,
0.50 min, 1.44 max (`diag_baseline_50tick_hpc_rate.log`): the 8.6 none arm sat at that
floor, the 8.7 one inside the top eighth, and this one above every baseline bin.

Reading: the write did what the contract said (156 synapses from the 64 strongest `ctx`
cells, 0.70 -> 0.90 `w_max`; the rest of `ctx` -> W only carries the window's LTP; non-W
flat), and the predictions for the write held (about 60-100 synapses predicted, 156 found;
"a few clamped" was wrong, 50 hit `w_max`). The predictions for the readout did not: the
none arm is not back near 0/16 (2/16 of W and 9/39 of the assembly within 50 ticks, the
whole `hpc` E population at 2.0 Hz, above any unstimulated 50-tick bin), full A reads W
worse than at 8.6 (5/16 against 11/16), and the half cue evokes 0/16 of W at 50 ticks. The
odd fact is that a smaller write (156 synapses, `ctx` -> W mean 0.769 against 0.874) is
followed by a louder unstimulated `hpc` than either the 8.6 write or the 8.7 clique; every
number up to the moment of the bump is identical to 8.6 (same assembly, same W, same
before-means), so the divergence starts at the bump and runs through the 1 s delay, which
holds one slow sweep. Why is not established here and is not guessed at. Per the contract
the none arm ignited W again, so k is not cut further and the work stops here. Reviews at
3d02f21, run repeated at bf01095 with identical numbers: architecture OK with notes (taken:
restricted donors are chosen among the `ctx` E cells that spiked during A, so a silent cell
can never be a donor; the two donor groups are emitted on every sparse-write path so the
8.6 control can be compared without a driver edit; `n_at_wmax_before` reported next to
`n_clamped` so the clamp count is not overstated; the `s1` test asserts the donor groups
partition `ctx` E -> W and that the donor count equals `DONOR_K`; left, noted: `donor_ids`
is emitted on the 8.6 path too, so a failing 8.6 assertion prints about 1,600 ids; only the
signature default of `donor_k` is pinned, not the call sites; `select_winners` keeps its
`hpc_e_ids` parameter name); security: no findings. Logs:
`~/.cache/scratch/brainsim-k11rd/` (`k11_restricted_donors_seed1.log`,
`k11_default_control_seed1.log`, `pytest_s1_restricted_donors.log` (1 failed on criterion 2
after every validity assertion passed, 82 s), `pytest_fast_restricted_donors.log` (129
passed, 13 deselected, 67 s), `diag_baseline_50tick_hpc_rate.py` and `.log`). Engine
identical to the parent branch; master untouched; branch not merged.

### 8.9 K1.1 rerun with a labelled proxy on the 8.6 parent: encode window on W only (predeclared 2026-09-13)

Owner's reading of 8.7 and 8.8 (both recorded on master), accepted as the record: 8.7's
clique was a spontaneous attractor; 8.8 wrote the contrast on 156 donor -> W synapses
(0.699 -> 0.899) but selectivity did not return (none 2/16 of W at 50 ticks, half cue 0/16,
full A 5/16, `hpc` E 2.0 Hz idle), a smaller write with a louder idle, and the 1 s delay is
not diagnosed this turn. The 8.6 run (15ff858, result 4ad8b5e) is the only one with none
0/16 and full A 11/16 at 50 ticks, so this slice starts from it and not from 8.7 or 8.8. The
8.6 writes are kept exactly: donors = every `ctx` E cell that spiked during the real A, one
end-of-A bump of 0.15 `w_max` on the existing alive donor -> W synapses, clamped, nothing
grown, no W -> W write. Not touched: `sense->ctx`; no merge of any Stage 1 branch; no Vogels,
organs, replay, K1.2, two-timescale weights, language; no K1.1 bar lowered, no recall window
widened, no donor cut, no W -> W, no write-size sweep.

**Proxy label:** *encode window on W only.* In 8.5 and 8.6 the encode window (pair-STDP
`A_minus` = 0, synaptic scaling skipped, rate-driven elimination skipped, all on the incoming
E synapses) covered every one of the 320 `hpc` E cells for the 2 s of A; that is what let
the assembly bloat from 16 to 39 cells and left every `hpc` recurrent unpruned. Here the
window covers only the 16 cells of W. The other 304 `hpc` E cells keep the default plant
(`A_minus`, scaling, elimination) for the whole 2 s. Restored when A ends; nothing latched at
construction; the engine is identical to the parent branch (the runtime `encode_mask` of
8.5, which is already per cell).

**Identification pass (a proxy, not biology, not a teacher current).** W has to be known
when A starts, and the 8.6 W is only known at the end of A. So: at t = 122,000 (A start) the
engine is deep-copied; the copy is shown A for the same 2,000 ticks under the default plant
(no window, no bump; its injections go to a discarded log); W = the copy's top 16 `hpc` E
cells by the engine's own spike count during A (`select_winners`, ties by the lower id); the
copy is discarded and nothing (weights, spikes, traces, counts) is copied back. The real
engine then sees A once, with the window on that W for the whole 2 s and the end-of-A
donor -> W bump onto that W, the donors taken from the real A's counts. The B copy (from the
same t = 122,000 state) gets the same procedure on its own discarded copy with pattern B.
The real run's own end-of-A top 16 is recorded and its overlap with the ID-pass W reported;
if that overlap is under 8/16 the run is still reported as it is, and no in-run
(progressive) mask is tried this turn.

Mechanism, driver-level only (`tests/k11_binding.py`):
- `hpc_encode_window(eng, ids=None)`: `ids` None keeps the 8.5 behaviour (every `hpc` E
  cell); otherwise the window covers exactly `ids`, which must be `hpc` E cells (asserted
  against `_hpc_e_ids`), and only those cells' `a_minus_n` and `encode_mask` entries are
  zeroed / set and restored (exception or not).
- `identify_W(eng, pattern_id, ticks, pattern_ids, hpc_e_ids, k=SPARSE_K)`: deep-copies
  `eng` (the copy gets its own discarded inject log), presents the pattern on the copy for
  `ticks` under the default plant (no window, no bump), returns `(W, record)` with `W` the
  sorted int64 top-`k` by the copy's counts and `record` = `{"W", "k", "ticks",
  "copy_t_start", "copy_t_end", "mean_count_W", "mean_count_hpc_e_not_W"}`; the copy is
  deleted before returning; `eng.t`, `eng.net.w`, `eng.net.spike_count`, `eng.encode_mask`
  and `eng.net.a_minus_n` are unchanged by the call (tests pin this).
- `sparse_cofire_write(net, counts, hpc_e_ids, ctx_e_ids, k, delta_frac, W=None)`: `W` None
  keeps the 8.6 rule (top-`k` by `counts`); otherwise the given `W` is used as is (sorted,
  asserted to be `k` distinct members of `hpc_e_ids`). The record gains `W_source`
  (`"counts"` or `"given"`), `real_top_k` (the top-`k` by `counts` regardless, sorted),
  `overlap_W_with_real_top_k` (int), and `donor_ids` (sorted). Donors unchanged (every
  `ctx_e_ids` member with `counts > 0`); the bump unchanged.
- `run_experiment(seed, hpc_encode_window=False, sparse_write=False, window_on_w=False)`;
  `window_on_w=True` requires `sparse_write` (raised before any engine work). When on: the
  ID pass runs on a copy taken right after the B copy at t = 122,000; the A window is
  `hpc_encode_window(eng, ids=W_id)`; the bump is `sparse_cofire_write(..., W=W_id)`; the B
  copy repeats both with its own ID pass on pattern B. Off: the default, window-only and
  8.6 paths keep their exact call sequences.
- Pins (validity): the existing seven moments keep `a_minus_hpc_e`, `mask_hpc_e_frac`,
  `mask_other_frac`; when `window_on_w` they also record `mask_W_frac`, `a_minus_W`,
  `mask_hpc_e_not_W_frac`, `a_minus_hpc_e_not_W`, each against that engine's own W (A's W
  for the A moments, B's for the B moments). `_encode_window_pins_ok(pins, on,
  window_on_w=False)`: with `window_on_w`, in the four in-window moments
  `mask_hpc_e_frac` == 16/320 exactly, `mask_W_frac` == 1.0, `a_minus_W` == 0.0,
  `mask_hpc_e_not_W_frac` == 0.0 and `a_minus_hpc_e_not_W` == the plant value; at
  before_A, after_A, after_B every mask fraction is 0.0 and every `a_minus` is the plant
  value; `mask_other_frac` 0.0 at every moment. `applied_inside_window` for both writes
  uses the W pins in this mode (`_window_on(m, window_on_w)`).
- Output: `window_on_w`, `id_pass_A`, `id_pass_B` (the records above), the 8.6
  `sparse_write_A/B` records with the new keys, and synapse groups before A -> after A keyed
  on A's W and A's donors: the existing `ctx_to_hpc_onto_W`, `ctx_to_hpc_onto_hpc_e_not_W`
  plus `donor_to_W`, `other_ctx_e_to_W`, `hpc_hpc_within_W` (count before and after, so a
  prune inside W is visible; there is no bump on it). `main()` takes `--window-on-w`
  (implies `--sparse-write` and `--hpc-encode-window`).

Rerun: the 8.2 protocol unchanged, one run; the same-seed default control alongside.
**Pass or fail on criterion 2 only, as defined**; `c2_recall_50_W` reported, not asserted.
Reported: assembly size and percentage (the criterion-1 check), W, B size, overlap; ID-pass
W against the real top 16; donor -> W synapse count and how many at `w_max`; mean w/`w_max`
before A -> after A for donor -> W, other `ctx` E -> W, `ctx` -> non-W and W -> W (count
before and after); recall of W and of the assembly at 50 and 200 ticks for half cue / full
A / none; `hpc` E in the none arm's first 50 ticks; the pins.

Predictions, before the run: with the mop kept on 304 of 320 cells the assembly is
predicted back near the 8.2 size (16 cells, 5 %) instead of 39; the ID-pass W is predicted
to overlap the real top 16 at 12/16 or better (the copy and the real engine share the state
and the RNG at t = 122,000 and differ only through the window on 16 cells); donor -> W about
1,000 synapses at about 0.69 -> about 0.87 as at 8.6; other `ctx` -> W is the same set
(every `ctx` E cell spikes); `ctx` -> non-W now falls a little (the 8.2 mop runs on those
cells: 0.708 -> 0.587 on the assembly at 8.2) instead of staying flat; W -> W: the
recurrents onto W are inside the window, so their count is predicted unchanged and their
mean up by the window's LTP only; the none arm is predicted near 0/16 at 50 ticks and `hpc`
E near the 8.6 idle (0.5 to 1.0 Hz); full A is predicted to read W as at 8.6 (about 11/16);
the half cue is predicted to FAIL criterion 2 at 50 ticks, there being no recurrent write.
If the assembly is still about 39 or the none arm ignites W, the mask is not enlarged this
turn; if the assembly is sparse and the half cue still fails, no recurrence is added this
turn.

Files: branch `k11-window-on-w` (worktree `~/.cache/brain-sim-k11wm`, from
`k11-sparse-write` 4ad8b5e): `tests/k11_binding.py` (`ids` on the window, `identify_W`,
`W` on the write, `window_on_w` argument and flag, the W pins, the groups),
`tests/test_k11_window_on_w.py` (unit tests on the window's `ids`, the ID pass's
no-side-effect contract, the write's `W`, the pins, digest guard, the `s1` rerun wrapper).
Master: this section and the result.

**K1.1 rerun result (2026-09-13, branch `k11-window-on-w` at 9af848e, seed 1, window on W only
+ 8.6 sparse write, W from the identification pass, no W -> W): FAIL on criterion 2; criterion 1
passes again (19 cells), the none arm is quiet, and the half cue completes nothing at 50
ticks.** Valid run (wake throughout, A volley 1.00, cue volley 1.00, injections sense-only,
engine pins ok: mask fraction 16/320 at the four in-window moments and 0 at before_A, after_A,
after_B; W fully masked with `a_minus` 0 inside the window; no non-W `hpc` E cell masked at any
moment and their `a_minus` at the plant value throughout; other regions never masked; both
writes inside their windows). Same-seed default control identical to fea6d10. Identification
pass: the copy at t = 122,000 ran A over 122,000 -> 124,000 under the default plant; its top 16
(mean count 10.6 against 2.6 for the other 304) overlaps the real run's own end-of-A top 16 at
15/16 (B: 12/16); the copy was discarded. Numbers: assembly as defined 19 `hpc` E cells (5.9 %,
criterion 1 passes; 39 at 8.5 to 8.8, 16 on the default plant), B 12, overlap 2 (10.5 %); W all
16 inside the assembly (B's W 11/16 inside B's); donors 1,599 (every `ctx` E cell that spiked on
the real A); donor -> W: 987 alive synapses existed, 987 bumped, 414 at `w_max` after the bump
(B: 975, 348). Mean w/`w_max` before A -> after A: donor -> W 0.720 -> 0.876 (987 -> 987; 8.6:
0.692 -> 0.874); other `ctx` E -> W: one synapse, from the one `ctx` E cell that did not spike,
1.00 -> 1.00; `ctx` -> non-W `hpc` E 0.684 -> 0.668 (16,971 -> 16,405: the default mop on those
304 cells removed 566 synapses during A, where at 8.6 it removed none and the mean stayed
flat); W -> W 47 -> 47 synapses (nothing pruned inside W; there is no bump on it) at 0.627 ->
0.673, the window's LTP only; `ctx` -> assembly 1,156 -> 1,132 at 0.714 -> 0.843; recurrents
within the assembly 56 -> 54 at 0.616 -> 0.665, assembly -> other `hpc` E 323 -> 279. Recall,
count/size (fraction), within 50 / 100 / 200 ticks: W, half cue 0/16 (0.00) / 3/16 / 7/16
(0.44), full A 3/16 (0.19) / 11/16 / 14/16 (0.88), none 0/16 (0.00) / 2/16 / 3/16 (0.19);
assembly, half cue 0/19 / 3/19 / 7/19, full A 3/19 / 11/19 / 14/19, none 0/19 / 2/19 / 3/19.
First assembly spike: half cue tick 53, full A 33, none 54. `hpc` E in the none arm's first 50
ticks 0.94 Hz (0.5 Hz at 8.6, 1.3 at 8.7, 2.0 at 8.8; unstimulated baseline bins 0.50 to 1.44
Hz, `~/.cache/scratch/brainsim-k11rd/diag_baseline_50tick_hpc_rate.log`); half cue 1.1 Hz,
full A 0.9 Hz. Criterion 3 holds (18 non-assembly spikes in the cue arm's first 50 ticks
against 14.4 expected, under the cap of 9.5 excess).

Reading: narrowing the window to W did what it was meant to do on the plant side: the assembly
is sparse again (19 cells, the first criterion-1 pass since the window was introduced), the
other 304 `hpc` E cells kept their mop (566 afferents pruned, mean down), the recurrents inside
W were left alone (47 -> 47), and the idle `hpc` is quiet (none 0/16 at 50 ticks, 0.94 Hz,
inside the unstimulated band). The write onto W is as large as at 8.6 (0.720 -> 0.876 on 987
synapses). The readout, though, is slower than at 8.6: the full pattern evokes 3/16 of W within
50 ticks (11/16 at 8.6) and reaches 11/16 only at 100 ticks; the half cue evokes 0/16 at 50
ticks and 7/16 at 200. So the predictions for sparsity, quiet and write size held, the
prediction that full A would read W as at 8.6 did not, and the half cue fails criterion 2 as
predicted. What differs from 8.6 lies outside W (the 304 cells under the mop and their
afferents and recurrents, and 25 rather than 28 `hpc` I responders); which of these slows the
readout is not established here and is not guessed at. Per the contract, the assembly being
sparse and the half cue failing at 50 ticks, no recurrence is added and the mask is not
enlarged; the work stops here. Reviews at 44a6a84, run repeated at 9af848e with identical
numbers: architecture OK with notes (taken: the validity check compared the float32 mean of the
plant `a_minus` over 16 or 304 cells with the mean over all 320 for exact equality and reported
the first, correct, run as INVALID, now each series is pinned against its own before_A value;
`identify_W` lifts the caller's inject wrapper off before the deep copy and puts the same object
back after, with a unit test; left, noted: in this mode every W-keyed quantity refers to the
ID-pass W, which overlaps the real top 16 at 15/16 here; the `hasattr` guard on the copy's
inject wrapper only fires for test fakes; the window-on-W branch of the pin check duplicates the
out-of-window logic; `donor_ids` is emitted on the 8.6 path too); security: no findings. Logs:
`~/.cache/scratch/brainsim-k11wm/` (`k11_window_on_w_seed1.log`, `k11_default_control_seed1.log`,
`pytest_s1_window_on_w.log` (1 failed on criterion 2 after every validity assertion passed,
84 s), `pytest_fast_window_on_w.log` (139 passed, 13 deselected, 80 s)). Engine identical to the
parent branch; master untouched; branch not merged.

### 8.10 K1.1 rerun with a labelled proxy on the 8.9 plant: small W -> W (predeclared 2026-09-13)

Owner's reading of 8.9, accepted as the record: criterion 1 passes (19 cells), the idle is
quiet (0.94 Hz), none 0/16 of W at 50 ticks, the donor -> W write as large as 8.6, the half
cue 0/16 at 50 ticks; full A slower than 8.6 (3/16 at 50, 11/16 at 100), and that halo is
not diagnosed this turn. One slice, one labelled proxy, on the 8.9 plant unchanged: the
identification pass, the window on those 16 cells only, the 8.6 donor rule, the donor -> W
bump of 0.15 `w_max` on existing synapses at the end of A, clamped, nothing grown. Not
touched: `sense->ctx`; no merge of any Stage 1 branch; no Vogels, organs, replay, K1.2,
two-timescale weights, language; no K1.1 bar lowered (7/16 at 200 or 11/16 at 100 is not a
pass), no recall window widened, no mask enlarged, no write-size sweep.

**Proxy label:** *small W -> W.* Exactly one thing is added, at the same moment as the
afferent bump (end of A, inside the window, before the window is restored): on the existing
alive `hpc` E -> `hpc` E synapses with both ends in the ID-pass W, w += 0.05 `w_max` (the
postsynaptic cell's), clamped at `w_max`. A third of the 8.7 size, which ignited at 0.15 on
the wide window. No synapse is grown; nothing W -> non-W or non-W -> W is written; the B
copy gets the same rule on its own ID-pass W. One write size, no search. A modelling proxy
for "the winners are wired a little more tightly", not a claim about biology.

Mechanism, driver-level only (`tests/k11_binding.py`), engine identical to the parent:
- `RECURRENT_DELTA_FRAC = 0.05`.
- `recurrent_cofire_write(net, W, delta_frac=RECURRENT_DELTA_FRAC)`: pure helper as in 8.7;
  `idx = alive & W_mask[pre] & W_mask[post]`; `w[idx] = min(w + delta_frac * w_max_n[post],
  w_max_n[post])`; returns `{"n_existing", "n_synapses_bumped" (equal to it), "n_increased"
  (strictly larger after), "n_clamped" (at `w_max` after), "n_at_wmax_before",
  "mean_w_over_wmax_within_W_before", "..._after", "delta_frac"}`. Synapses with one end outside W are untouched (tests pin this on a fake
  net with distinct per-cell `w_max_n`).
- `run_experiment(seed, hpc_encode_window=False, sparse_write=False, window_on_w=False,
  small_ww=False)`; `small_ww=True` requires `window_on_w` (raised before any engine work).
  When on, right after `sparse_cofire_write(..., W=W_id_A)` and inside the A window:
  `recurrent_write_A = recurrent_cofire_write(net, W_id_A)`, with
  `applied_inside_window = _window_on(_pin_moment(eng, W=W_id_A), window_on_w=True)`; the
  B copy the same with `W_id_B`. Off: the default, window-only, 8.6 and 8.9 paths keep
  their exact call sequences.
- Output: `small_ww`, `recurrent_write_A`, `recurrent_write_B`; the existing
  `hpc_hpc_within_W` group (before A -> after A) shows the same synapses over the whole
  presentation (the window's LTP plus the bump), and two boundary groups
  `hpc_hpc_W_to_not_W`, `hpc_hpc_not_W_to_W` show that nothing across the W boundary was
  written by the proxy (review addition). `main()` takes `--small-ww` (implies `--window-on-w`, `--sparse-write`,
  `--hpc-encode-window`).

Rerun: the 8.2 protocol unchanged, one run; the same-seed default control alongside.
**Pass or fail on criterion 2 only, as defined**; `c2_recall_50_W` reported, not asserted.
Validity: the 8.9 mask pins unchanged, both writes inside their windows. Reported: W -> W
count, bumped, at `w_max` (and how many were there before), mean before -> after; W recall at
50 / 100 / 200 for half cue / full A / none; assembly size; `hpc` E in the none arm's first
50 ticks; the donor -> W and `ctx` -> non-W groups as before.

Predictions, before the run: 47 alive W -> W synapses (8.9), at 0.673 `w_max` at the end of A
before the bump (the window's LTP), predicted to about 0.72 after, with few or none clamped;
each W cell then has about three W inputs at about 2.2 mV against a 3.0 mV `w_max`: a
smaller recurrent drive than 8.7's. The idle is predicted to stay quiet (none under 4/16 at
50 ticks, `hpc` E under 1.5 Hz), the full pattern to read W a little faster than 8.9's
3/16 at 50 ticks, and the half cue to evoke more than 0/16 within 50 ticks but not 80 %:
FAIL on criterion 2 is the prediction. If the none arm runs hot (over 1.5 Hz or 4/16 or
more of W at 50 ticks) the write size is not cut this turn; if the idle stays quiet and the
half cue still fails at 50 ticks the write size is not raised this turn.

Files: branch `k11-small-ww` (worktree `~/.cache/brain-sim-k11ww`, from `k11-window-on-w`
2eecf9a): `tests/k11_binding.py` (`RECURRENT_DELTA_FRAC`, `recurrent_cofire_write`,
`small_ww` argument and flag, the records), `tests/test_k11_small_ww.py` (unit tests on the
helper and its boundary, guard, flag, digest guard, the `s1` rerun wrapper). Master: this
section and the result.

**K1.1 rerun result (2026-09-13, branch `k11-small-ww` at 02b6fcb, seed 1, 8.9 plant + W -> W
0.05 `w_max`): FAIL on criterion 2; the W -> W mean rose at the write, the idle stayed quiet, and
every spike-derived number is the same as at 8.9.** Valid run (wake throughout, A volley 1.00,
cue volley 1.00, injections sense-only, engine pins ok with the 8.9 mask pins unchanged, both
writes inside their windows). Same-seed default control identical to fea6d10. The ID pass gave
the same W as at 8.9 (overlap with the real top 16 again 15/16). W -> W: 47 alive synapses
existed, 47 bumped, 44 increased (3 were already at `w_max`), 7 at `w_max` after; mean
w/`w_max` 0.673 -> 0.718 at the write (0.627 -> 0.718 over the whole presentation, the window's
LTP plus the bump); B's own W: 40 existed, 38 increased, 5 at `w_max`, 0.672 -> 0.718. Nothing
across the W boundary was written by the proxy: W -> non-W 280 -> 240 synapses at 0.658 ->
0.635 (the default mop on the non-W cells), non-W -> W 328 -> 328 at 0.659 -> 0.671 (the
window's LTP only). Donor -> W 987 at 0.720 -> 0.876 and `ctx` -> non-W 0.684 -> 0.668 as at
8.9. Assembly 19 (5.9 %), B 12, overlap 2. Recall of W within 50 / 100 / 200 ticks: half cue
0/16 / 3/16 / 7/16, full A 3/16 / 11/16 / 14/16, none 0/16 / 2/16 / 3/16; the assembly the same
counts over 19; first assembly spike at tick 53 / 33 / 54; `hpc` E in the none arm's first 50
ticks 0.94 Hz. These are, to the last digit, the 8.9 numbers.

Reading: the write happened where it was aimed and the half cue still evokes nothing from W
within 50 ticks; per the contract the write size is not raised and the work stops here. A
scratch check (`diag_ww_bump_raster.py`, the A path replayed with and without the W -> W bump,
then the delay and the none arm stepped one tick at a time) explains the identical numbers:
the bump moved exactly one `hpc` E spike by one tick (delay ticks 474 -> 475) and changed
nothing else in 1,200 ticks (337 `hpc` E spikes, 37 of them from W, in both). The same check
records what the plant did to the recurrents once the window closed: at the first slow sweep
after A (t = 125,000, mask off, W's rate EMA still high from the presentation) the mop
eliminated 19 of the 47 W -> W synapses without the bump and 15 of them with it, and the
survivors' means are 0.743 against 0.747; the bump was largely gone before the cue arrived.
Whether the afferent write onto W survives that same sweep was not measured and is the next
cheap check; it is outside this slice and is not guessed at. Reviews at 107770e, run repeated
at 02b6fcb with identical numbers: architecture OK with notes (taken: `hpc_hpc_W_to_not_W` and
`hpc_hpc_not_W_to_W` groups so the record itself excludes a stray write across the W boundary;
`n_increased` next to `n_synapses_bumped`; `applied_inside_window` forwards the window mode; a
test that the mode is inert when off and that the bumped set equals the within-W group; left,
noted: `hpc_hpc_within_W` over the presentation sums the window's LTP and the bump; `report()`
prints `small_ww=` on every path); security: no findings. Logs:
`~/.cache/scratch/brainsim-k11ww/` (`k11_small_ww_seed1.log`, `k11_default_control_seed1.log`,
`pytest_s1_small_ww.log` (1 failed on criterion 2 after every validity assertion passed, 86 s),
`pytest_fast_small_ww.log` (155 passed, 14 deselected, 65 s), `diag_ww_bump_raster.py`,
`diag_ww_bump_off.log`, `diag_ww_bump_on.log`, `diag_ww_bump_compare.log`). Engine identical to
the parent branch; master untouched; branch not merged.

### 8.11 K1.1 rerun with a labelled proxy on the 8.10 plant: post-write grace on W (predeclared 2026-09-13)

Owner's reading of 8.10, accepted as the record: the W -> W write landed (0.673 -> 0.718) and
the first slow sweep after the window closed (t = 125,000) eliminated 15 of the 47 W -> W
synapses because W's rate EMA was still high from the presentation; recall identical to 8.9;
the recurrent mark did not reach the cue; the afferent mark's survival on that sweep is
unmeasured. One slice, one labelled proxy, on the 8.10 plant unchanged: the identification
pass, the window on W during A, the donor -> W bump of 0.15 `w_max`, the W -> W bump of 0.05
`w_max`, nothing grown. Not touched: `sense->ctx`; no merge of any Stage 1 branch; no Vogels,
organs, replay, K1.2, two-timescale weights, language; no K1.1 bar lowered, no write raised,
no mask enlarged, and the mop is not down during the cue.

**Proxy label:** *post-write grace on W.* Exactly one thing changes: when the mop returns to
W. Until now scaling and rate-driven elimination came back on W's incoming E synapses the tick
A ended. Now they stay off on W through the 1 s post-A delay only (t 124,000 -> 125,000, which
holds the one slow sweep at 125,000) and are restored before the cue volley starts; the cue,
full and none arms run with the default mop on. Pair-STDP `A_minus` returns on W at the end of
A as today: the grace covers scaling and elimination, not a second LTP-only period. The other
304 `hpc` E cells never get grace. The B copy has no delay and gets no grace. A modelling proxy
for "a fresh mark is not swept for a second", not a claim about biology.

Mechanism, driver-level only (`tests/k11_binding.py`), engine identical to the parent (the
runtime `encode_mask` of 8.5 is per cell and gates synaptic scaling and the rate-driven
elimination of incoming E synapses; it does not gate the weak-weight prune, `w` under 0.05
`w_max`, which the marks at about 0.7 to 0.9 `w_max` are far from; review correction):
- `hpc_grace(eng, ids)`: context manager; `ids` must be `hpc` E cells (asserted against
  `_hpc_e_ids`); sets `eng.encode_mask[ids]` True on entry and False on exit (exception or
  not); does not touch `a_minus_n` or any other cell.
- `run_experiment(seed, hpc_encode_window=False, sparse_write=False, window_on_w=False,
  small_ww=False, grace=False)`; `grace=True` requires `small_ww` (raised before any engine
  work). When on: after the A window has exited (so `a_minus` on W is back at the plant value
  and the mask is off, with no tick in between), the delay runs inside `hpc_grace(eng,
  ids=W_id_A)`; the context exits before the three arm copies are taken. Off: the default,
  window-only, 8.6, 8.9 and 8.10 paths keep their exact call sequences.
- Pins: in `window_on_w` mode four more moments are recorded with A's W, with or without
  grace: `during_delay` (right after the delay context is entered, before any delay tick),
  `during_delay_end` (after the last delay tick, before the context exits), `before_cue`
  (after the context exits, t = 125,000, on `eng`), `cue_start` (on the cue arm's copy before
  its first tick). `_encode_window_pins_ok(pins, on, window_on_w=False, grace=False)`: in
  `window_on_w` mode, when the pins carry `during_delay`, `mask_W_frac` at `during_delay` and
  `during_delay_end` must equal 1.0 with grace and 0.0 without, and 0.0 at `before_cue` and
  `cue_start`; `a_minus_W` must equal its own `before_A` value at all four; `mask_hpc_e_not_W_frac`
  0.0 and `mask_other_frac` 0.0 at all four. The seven existing moments keep their 8.9 rules.
- Mark tracking at three times, in `window_on_w` mode, keyed on A's W and A's donors, with
  `_syn_group_stats` on snapshots: `marks = {"end_of_A": ..., "end_of_delay": ..., "cue_50":
  ...}`, each `{"donor_to_W": {n, mean_w_over_wmax}, "hpc_hpc_within_W": {...}}`; `end_of_A` from
  the snapshot right after A (bumps applied), `end_of_delay` from a snapshot of `eng` at
  t = 125,000 after the grace context exits, `cue_50` from a snapshot of the cue arm's copy
  after its 50th tick (`_run_arm` gains `snapshot_at=None`, returning `snapshot` in its
  result when set). `killed_in_delay = {"donor_to_W": n_end_of_A - n_end_of_delay,
  "hpc_hpc_within_W": ...}` reported next to them: with grace off this is what the 125,000
  sweep removed, with grace on it must be 0 (reported, and asserted in the `s1` test).
  Kills and births are counted by synapse identity (pre, post, born) between the two
  snapshots (`_mark_survival`), so a birth in the same sweep cannot hide a kill, and the
  end-of-delay and cue-50 means are also given over the survivors only (`mark_survival`,
  `born_in_delay`; review addition).
- Output: `grace`, `marks`, `killed_in_delay`. `main()` takes `--grace` (implies `--small-ww`
  and everything below it).

Rerun: the 8.2 protocol unchanged, one run with grace; the same plant without grace (the 8.10
path, `--small-ww`) rerun alongside as the matched control so `killed_in_delay` is measured on
the same seed, plus the same-seed default control. **Pass or fail on criterion 2 only, as
defined**; `c2_recall_50_W` reported, not asserted. Reported at the three times: donor -> W and
W -> W count and mean; what the first post-A sweep killed without grace; W recall at 50 / 100 /
200 for half cue / full A / none; assembly size; `hpc` E in the none arm's first 50 ticks; the
pins.

Predictions, before the run: with grace the 125,000 sweep leaves W's incoming synapses
alone, so at the end of the delay donor -> W stays at 987 and W -> W at 47, both at their
end-of-A means less whatever pair-STDP LTD does during the delay (small: W fires about 1 Hz);
without grace the sweep removes about 15 W -> W and some donor -> W synapses (unmeasured so
far). The cue arm then sees the intact marks with the default mop on (no sweep falls inside
its 200 ticks). Assembly 19 as at 8.9 (the A presentation is unchanged), none predicted still
0/16 at 50 ticks with `hpc` E near 0.9 Hz, full A predicted to read W at least as at 8.9
(3/16 at 50) and probably faster, and the half cue predicted to evoke more than 0/16 within
50 ticks but not 80 %: FAIL on criterion 2 is the prediction. If the mop still strips W
during the delay the grace is not lengthened; if the marks survive and the half cue still
fails the write is not raised; if the none arm ignites W the grace is called too long.

Files: branch `k11-grace` (worktree `~/.cache/brain-sim-k11gr`, from `k11-small-ww` 6308695):
`tests/k11_binding.py` (`hpc_grace`, `grace` argument and flag, the four delay/cue pins, the
three-time mark record, `snapshot_at` on `_run_arm`), `tests/test_k11_grace.py` (unit tests
on the context manager, the pin rules, the guard chain, the flag, digest guard, the `s1`
rerun wrapper). Master: this section and the result.

**K1.1 rerun result (2026-09-13, branch `k11-grace` at b841bc7, seed 1, 8.10 plant + grace on
W through the delay): FAIL on criterion 2; both marks reached the cue intact, the readout moved
for the first time, and the half cue evokes 5/16 of W at 50 ticks.** Valid run (wake throughout,
A volley 1.00, cue volley 1.00, injections sense-only, engine pins ok: W fully masked with
`a_minus` at the plant value at `during_delay` and `during_delay_end`, mask 0 on W at
`before_cue` and `cue_start`, no non-W `hpc` E cell masked at any of the eleven moments, other
regions never masked; the A-window pins as at 8.9; both writes inside their windows). Same-seed
default control identical to fea6d10. The matched control (the 8.10 path on the same seed,
`--small-ww`, identical to the 8.10 record) measures what the first post-A slow sweep does
without grace: by synapse identity it killed 44 of the 987 donor -> W synapses and 15 of the 47
W -> W, none born, and the survivors' means fell from 0.876 to 0.804 (donor -> W, scaling) and
rose from 0.718 to 0.746 (W -> W, the weakest removed). Marks at the three times, with grace:

| time | donor -> W n, mean w/`w_max` | W -> W n, mean |
|---|---|---|
| end of A, after the bumps | 987, 0.876 | 47, 0.718 |
| end of delay, last tick before the cue | 987, 0.871 | 47, 0.718 |
| cue arm, after its first 50 ticks | 987, 0.870 | 47, 0.717 |

killed in the delay 0 and 0, born 0 and 0 (44 and 15 without grace); the small drift is pair
LTD at the plant `A_minus`, which is back on W from the end of A. Numbers: assembly 19 (5.9 %),
B 12, overlap 2, W the same 16 (ID pass unchanged, overlap with the real top 16 15/16). Recall
of W, count/16, within 50 / 100 / 200 ticks: half cue 5 / 5 / 10, full A 10 / 13 / 14, none 2 /
4 / 8; assembly, count/19: half cue 5 / 5 / 10, full A 10 / 13 / 14, none 2 / 4 / 8 (8.10, same
plant, no grace: half cue 0 / 3 / 7, full A 3 / 11 / 14, none 0 / 2 / 3). The first assembly
spike is at tick 28 in all three arms: one spontaneous spike the three copies share. `hpc` E in
the none arm's first 50 ticks 1.06 Hz (0.94 at 8.9 and 8.10; unstimulated bins 0.50 to 1.44);
half cue 1.1 Hz, full A 2.1 Hz. Criterion 3 holds (13 non-assembly spikes in the cue arm's first
50 ticks against 14.4 expected).

Reading: the grace did exactly what it was for. Without it the first sweep after the window
strips both marks (44 afferent and 15 recurrent synapses gone, the afferent survivors scaled
down by 0.07 `w_max`); with it every one of the 987 + 47 synapses is still there at the cue,
within 0.006 of its written value. The cue then reads them: full A evokes 10/16 of W within 50
ticks (3/16 on the same plant without grace, 11/16 at 8.6), and the half cue evokes 5/16 (0/16
without grace), so the intact marks are readable and the half cue still does not complete W
(criterion 2 needs 80 % within 50 ticks). The none arm is not hot by the contract's thresholds
(2/16 of W at 50 ticks, under 4/16; 1.06 Hz, under 1.5) but it is not the 0/16 of 8.9 either,
and it climbs to 4/16 at 100 and 8/16 at 200 ticks with no stimulus, as does the assembly
(8/19 at 200): the intact trace drifts on by itself at 200 ticks even when the cue is absent.
Per the contract, the marks survived and the half cue failed at 50 ticks, so the write is not
raised and the grace is not lengthened; the work stops here. Reviews at b4c3b4a, run repeated
at b841bc7 with identical numbers: architecture OK with notes (taken: kills and births in the
delay counted by synapse identity with the survivors' mean, so a birth cannot hide a kill or
dilute the mean; the contract's claim that the mask gates "exactly scaling and elimination"
corrected, it gates scaling and the rate-driven elimination and not the weak-weight prune,
which the marks at 0.7 to 0.9 `w_max` are far from; left, noted: the delay and cue moments pin
`a_minus` on W but not on the other `hpc` E cells; no test pins the 8.10 trajectory against
6308695, the matched control's identity to the 8.10 record was checked by hand); security: no
findings. Logs: `~/.cache/scratch/brainsim-k11gr/` (`k11_grace_seed1.log`,
`k11_small_ww_nograce_seed1.log`, `k11_default_control_seed1.log`, `pytest_s1_grace.log` (1
failed on criterion 2 after every validity assertion passed, 89 s), `pytest_fast_grace.log`
(176 passed, 15 deselected, 85 s)). Engine identical to the parent branch; master untouched;
branch not merged.

### 8.12 Encode-mode: one labelled plant schedule (predeclared 2026-09-13)

**Status since 2026-09-30:** encode-mode is on master, off by default, merged as the parent
of the heterosynaptic write (8.16). The statements below that nothing merges describe this
section's own run.

Owner's framing, accepted as the record: five driver flags (`--hpc-encode-window
--sparse-write --window-on-w --small-ww --grace`) had accumulated on five branches, each a
context manager wrapped around the protocol from outside the engine. They are replaced here by
one labelled plant MODE, `Engine.encode_mode`, that runs the 8.11 schedule inside the tick
loop. Nothing about the mechanism changes: it is the same identification pass, the same window
on W, the same two bumps, the same grace. It is a proxy schedule, not biology, and K1.1 stays
recorded FAIL. Nothing merges to master this turn; the constants are not retuned.

**Proxy label:** *encode-mode.* Exactly one thing changes: where the 8.11 schedule lives. It
was five driver flags outside the engine; it is now one flag inside it, off by default.

**Off is today's plant, bit for bit.** With `encode_mode` False nothing below is read or
written and every number is master's. The `REFERENCE_DIGEST` test of
`tests/test_engine_determinism.py` still matches, and two further guards pin it: an
inject-only schedule run with the mode on must digest-equal the same schedule with the mode
off, and an off-path digest script (presents, an arbitrary inject, a sleep/wake, six slow
sweeps) must print master's digest from this branch with the mode both off and on.

Mechanism (engine, not driver):
- `brainsim/params.py`, appended block, values fixed: `ENCODE_K = 16`,
  `ENCODE_DELTA_FRAC = 0.15`, `ENCODE_RECURRENT_DELTA_FRAC = 0.05`,
  `ENCODE_GRACE_TICKS = 1000`. No other parameter changes; no new plasticity; STDP, scaling
  and the structural rule are untouched.
- `brainsim/encode.py` (new): the pure functions moved out of `tests/k11_binding.py` with
  their numerics unchanged: `hpc_e_ids`, `ctx_e_ids`, `cue_ids` (the cells at even positions
  of the sorted pattern, the K1.1 half cue), `select_winners` (ties to the lower id),
  `identify_W(eng, pattern_id, ticks, k)` (deep-copies the engine with the mode off, presents,
  steps, and returns the top-k `hpc` E cells by the copy's spike counts; the caller's engine
  is untouched in `t`, net arrays, rng state, `encode_mask` and queued stimuli, and any
  instance-level `inject` wrapper is lifted off before the copy and put back after),
  `sparse_cofire_write` and `recurrent_cofire_write` (one-shot `w += delta_frac * w_max_n[post]`,
  clamped, on existing alive synapses only; no synapse is grown).
- `Engine`: `encode_mode` (the flag, False), `encode_W` (W of the most recent schedule, kept
  after it ends), `encode_record` (its record), `encode_stage` (`"present"` or `"grace"` whenever a
  schedule is running, whatever the flag says; else `"idle"` with the mode on, `"off"` with it
  off), and a 50-tick history of which of `encode_W` spiked.
- `present(pattern_id, ticks)` arms the schedule only when the mode is on, no schedule is
  active, the engine is awake and `ticks > 0`; otherwise it is the plain path it has always
  been (so the cue, and a present during an active schedule, write nothing). Arming, before
  the presentation is queued: run the identification pass to get W; zero `a_minus_n` on W and
  set `encode_mask` on W, and on no other cell; record the schedule with `t_present_end` and
  `t_grace_end = t_present_end + ENCODE_GRACE_TICKS`; then queue the presentation exactly as
  today.
- The schedule advances at the very end of `Engine._tick`, after that tick's slow sweep, so a
  sweep falling on a boundary tick still runs under the mask, exactly as the driver's context
  managers did. At the end of the tick that brings `t` to `t_present_end`: the sparse
  donor -> W write, then the W -> W write, then `a_minus_n` restored on W; the mask stays on W
  and the stage becomes `"grace"`. At the end of the tick that brings `t` to `t_grace_end`:
  the mask comes off W, the record is marked done, the stage returns to `"idle"`. `encode_W`
  and `encode_record` persist.
- Telemetry: the frame gains `encode` (`mode`, `stage`, `W`, `spiked_last_50`, `window_ticks`,
  `t_present_end`, `t_grace_end`), config gains `encode_k`, `encode_delta_frac`,
  `encode_recurrent_delta_frac`, `encode_grace_ticks`, and the layout reply gains
  `half_patterns` (`cue_ids` of each pattern). Reading a frame consumes no RNG and does not
  clear the W spike history.
- Worker: `{"cmd": "encode", "on": bool}`; `on` must be a bool, else rejected
  `invalid: on must be a bool`. It sets the flag and reports `changed`; it never cancels a
  schedule already running. While `encode_stage` is `"idle"` a `present` of more than 2,000
  ticks is rejected, because arming runs the identification pass inline on a deep copy of the
  engine and a longer presentation would block the worker loop twice over; with the mode off
  the existing 100,000-tick bound stands.
- UI: an `Encode-mode` panel between `Stimulate` and `Phase schedule`, with a checkbox whose
  checked state is set from `f.encode.mode` on every frame (engine truth, never the click), a
  stage line built only from `f.encode`, a card of one chip per id in `f.encode.W` lit when
  that id is in `f.encode.spiked_last_50`, and three buttons that send only commands the page
  could already send: present A, inject `half_patterns[0]`, step. The gloss reads: *these
  cells were the A winners; lighting them after a hint is the scribble, not speech.* No W is
  inferred or drawn client-side.
- Driver (`tests/k11_binding.py`): `run_experiment(seed, encode_mode=False)` and
  `--encode-mode` replace the five kwargs and flags; `hpc_encode_window`, `hpc_grace`,
  `_hpc_encode_window_ctx`, `_window_on` and `_encode_window_pins_ok` are gone and the pure
  helpers are re-exported from `brainsim.encode`. The default path is the fea6d10 default
  plant, unchanged. The encode path sets `encode_mode` on the A engine and the B copy, lets
  `present()` arm the schedule, and turns the mode off before the three arm copies, so the
  cue, full and none arms run with the default mop. Pins (`engine_pins["encode"]`) record
  `stage`, `mask_W_frac`, `mask_hpc_e_not_W_frac`, `mask_other_frac`, `a_minus_W` and
  `a_minus_hpc_e_not_W` at eight moments: `before_A`, `during_A`, `during_A_end`,
  `during_delay`, `during_delay_end`, `cue_start`, `during_B`, `during_B_end`;
  `_encode_pins_ok(pins)` requires the stage sequence idle / present / grace / grace / idle /
  off / present / grace, the mask on W (1.0) exactly at the five masked moments and 0.0
  elsewhere, `a_minus_W` zero only while presenting and back at its own `before_A` value
  otherwise, and `mask_hpc_e_not_W_frac` and `mask_other_frac` 0.0 at every moment. The output
  keys of 8.11 are kept so `report()` prints the same tables.

Rerun: the 8.2 protocol unchanged, one run with `--encode-mode`, plus the same-seed default
control. **Pass or fail on criterion 2 only, as defined**; `c2_recall_50_W` reported, not
asserted.

Prediction, before the run: this is a move, not a change, so the encode-mode replay should
reproduce 8.11 exactly — W recall at 50 ticks 5/16 under the half cue, 10/16 under full A and
2/16 with no stimulus; assembly 19 cells; the marks reaching the cue intact at 987 donor -> W
synapses at 0.871 `w_max` and 47 W -> W at 0.718. That is FAIL on criterion 2: 5/16 is not
80 %, and K1.1 remains recorded FAIL on the quiet half cue. Any deviation from those numbers
means the move was not faithful and is a bug in the port, not a result.

Files: branch `encode-mode` (worktree `~/.cache/brain-sim-encode-mode`, from `k11-grace`
b841bc7): `brainsim/params.py` (the appended block), `brainsim/encode.py` (new),
`brainsim/engine.py` (the mode, the stage, the tick hook), `brainsim/telemetry.py` (the frame,
config and layout keys), `brainsim/worker.py` (the `encode` command), `tests/k11_binding.py`
(the rewrite above), `ui/index.html` `ui/app.js` `ui/style.css` (the panel),
`tests/test_encode_mode.py` and `tests/test_k11_encode_mode.py` (new), the two digest guards
in `tests/test_engine_determinism.py`, and the deletion of the five superseded flag tests.
Master: this section and the result.

Result (2026-09-13, branch `encode-mode` aa176fb, seed 1). Off path: the `REFERENCE_DIGEST`
test and the inject-only twin guard pass, and the off-path digest script prints master's digest
(`de63fa6f...`, t 5,600, 41,287 spikes, 309,292 alive synapses) from this branch with the mode
off and with it on. Encode path: the replay reproduces 8.11 exactly: the identification pass
returns the same W (2218 ... 2513, 15/16 with the real top 16), assembly 19, donor -> W 987
synapses 0.720 -> 0.876 at the write and 0.870 at the cue, W -> W 47 at 0.627 -> 0.718 and
0.717 at the cue, nothing killed or born in the delay; W recall half cue 5/16, full A 10/16,
none 2/16 at 50 ticks (5/13/4 at 100, 10/14/8 at 200); stage pins idle / present / grace /
grace / idle / off / present / grace with the mask on exactly W and on no other cell; validity
all PASS, criterion 1 True; VERDICT FAIL on criterion 2 (5/19 at 50 ticks). Default control
identical to fea6d10. Fast suite 141 passed; the `s1` replay wrapper passed. UI: on a served
copy of the branch the Encode-mode panel showed the checkbox following the engine's flag, the
stage line, a card of 16 `hpc` E ids read from the frame with the recent spikers lit, and the
three buttons landing as `encode`, `present`, `inject` and `step` results
(`~/.cache/scratch/brainsim-encode-mode/ui_encode_panel.png`). Not merged: K1.1 remains
recorded FAIL on the quiet half cue.

- **K1.1 binding**: present A for 2 s; the `hpc` assembly is <= 5 % of `hpc`; a 50 % cue of A
  recalls >= 80 % of the assembly within 50 ms; a novel B overlaps < 20 %.
- **K1.2 consolidation**: before sleep, silencing `hpc` output abolishes ctx recall of A; after
  one sleep, ctx recalls A with `hpc` silenced.
- **K1.3 interleaved replay**: during sleep, reactivations classified by overlap with stored
  assemblies include patterns learned >= 2 sleeps ago; new:old ratio within [0.2, 5].
- **K1.4 forgetting resistance with ablation**: learn A, sleep, B, sleep, C, sleep. Recall of A
  keeps >= 70 % of its post-consolidation level. Control run with `w_s` frozen must lose more.
  If the control does not differ, the mechanism is decorative and the test fails.
- **K1.5 engram survival**: synapses carrying A in ctx (strong weights between A-assembly
  pairs) lose < 30 % of their count across 3 sleeps of structural turnover.

**Recommended next engine change (2026-09-12, not implemented; needs a yes): move the
slow rate homeostat off the excitatory weights and onto intrinsic excitability, so that
STDP owns the weights and the rest weight settles at the rule's own fixed point.** In every
measurement since 2026-09-11 the failure reduces to one inequality: an input's trace-weighted
causal:anticausal excess must exceed A- w / (A+ (w_max - w)), and the homeostatic rest weight
(0.75 `w_max`, held there in arm_none by scaling's +0.126 lift against STDP's -0.116 drift)
puts that requirement at 3.6 while natural onsets deliver 1.8 and the imposed volley 3.0.
The rest weight is where a 4 Hz setpoint lands when the only slow lever is the E weight; it
is not a property of the rule. The change: per neuron a slow threshold offset `theta_h`
(initially 0), updated once per sweep in wake only, `theta_h += clip(ETA_H * (rate -
r_target) / r_target, +-CLIP_H) * D_THETA_MV`, bounded to [-THETA_H_MAX, +THETA_H_MAX], added
to `theta` in the spike test; the synaptic scaling step is removed (its two clauses, frozen in
sleep and used-input only, carry over as "frozen in sleep" for the offset). Proxy for
homeostatic intrinsic plasticity (Desai, Rutherford & Turrigiano 1999; Turrigiano 2011);
labelled, not a claim. Structural plasticity (2.5) and its latch are untouched and keep
reading the same rate error. Predictions, falsifiable: the sense->ctx rest weight falls from
0.75 toward 0.45 `w_max` within 60 s; ctx E reaches 4 +- 0.5 Hz and the latch releases;
K0.13 on the same protocol then passes both endpoints because 1.77 exceeds the requirement
at 0.45 (about 1.0); the natural response before training stays >= 0.5 spikes per cell per
presentation (weaker synapses, lower thresholds). If the rest weight falls but K0.13 still
fails, the rule's leverage is the next question, and the alternative below is then the
better-supported change.
*Strongest alternative, compared:* leave homeostasis alone and move the rule's fixed point
to the rest weight by raising `A_plus` to A- w_rest / (w_max - w_rest) = 0.036 at 0.75
`w_max` (one constant, derived, not searched). It satisfies the same inequality (requirement
1.0 at 0.75) and needs no recovery contract. Against it: LTP on every correlated input
becomes 3.6x stronger, so the ceiling fraction, the recurrent ctx weights and K0.2 are at
risk; and the fix couples the rule to a rest weight that itself moves with `I_GAIN`, the
setpoint and the network's gain, so it has to be re-derived after any of them changes. The
recommended change decouples them. Neither is Path 2 (a triplet rule): nothing measured
requires rate-dependent LTP.
*Recovery contract for the homeostasis change (must pass before K0.13 is rerun on it;
passing K0.2, K0.6, K0.11 alone is insufficient, per the coverage gap in 2.4):* K0.14, seed 1
and seeds 2-3 reported. Perturbation, using existing commands only: at t = 100 s (mature,
latched state) `set_noise` steps ctx sigma from 2.35 to 1.2 mV for 20 s, then back; a
second run steps `set_sense_spont` from 5 to 0 Hz for 20 s, then back. Recovery time: the
ctx E EMA rate returns to within +-25 %% of its setpoint within 15 s of each step and within
15 s of each restore, measured per sweep. Rate range: ctx E in [1, 15] Hz and no region under
0.2 Hz throughout t = 90-160 s (K0.2's band, now over the whole episode). Bursts: no tick
with > 20 %% of ctx spiking, anywhere in the run. Latch: `growth_halted["ctx_E"]` releases
within 10 sweeps of each step (the error changes sign) and the latched fraction of sweeps
over 140-160 s is <= 50 %% (today it is 100 %%). Weights: sense->ctx rest weight and ceiling
fraction reported at 100, 120 and 160 s; K0.6's sleep clause and K0.11's freeze clause,
re-targeted to the offset, must hold; the determinism digest is re-pinned with the reason.
Fail = any clause; the report says which and the candidate is not adopted.
*Implementation slice, one chunk, isolated branch:* `brainsim/params.py` gains `ETA_H`,
`CLIP_H`, `THETA_H_MAX` and `HOMEOSTAT = "intrinsic"` (with `"scaling"` selecting today's
path so the branch can run both for comparison); `brainsim/net.py` gains `theta_h`
(float32 per neuron, 0); `brainsim/engine.py::_slow_sweep` applies the offset update where
the scaling block is, `_tick` compares `v >= theta + theta_h`, `frame()` emits
`theta_h` statistics (and `tests/test_ui_truth.py` pins them). Tests first, by a different
worker: K0.14 as above, K0.11 re-targeted, the K0.12-style determinism run across a step,
the K0.2/K0.6 records rerun; then K0.13 unchanged on the branch. Budget under 20 min wall.
Nothing here is implemented; the branch, the tests and the runs each wait for a yes.

### 8.13 Two-timescale weights: a slow component the homeostat cannot erase (predeclared 2026-09-30)

Owner's framing, accepted as the record: one autonomous attempt at a different mechanism, a
new named experiment on branch `two-timescale` (from `encode-mode` dfcbc01), not a reopen of
closed work. Nothing merges to master. K1.1 is not redefined and not hunted. This is a proxy
mechanism, not biology, and no "inner life" is claimed.

**Why this one (A of the owner's A/B/C/D):** every write on the 8.4 to 8.12 branches was
carried by the fast weight alone, and the fast weight is exactly what the slow sweep scales,
prunes and LTD-erodes; 8.11 measured that the first unprotected sweep after the write killed
44 of 987 donor -> W synapses and 15 of 47 W -> W, so the prior branches could only keep the
trace by exempting W from the homeostat (mask, grace). A second weight component with its own
timescale lets the homeostat keep running on every synapse while the written value persists,
which is the question the owner asked: does interaction leave a change that survives the mop.

**Proxy label:** *two-timescale weight* (a floor latch; a Fusi/Zenke cascade in spirit,
not in form). Exactly one plant mechanism is added; the encode-mode write of 8.12 is the
interaction that produces the value it stores, and 8.12's post-write protection is turned off
in the kill test (`ENCODE_GRACE_TICKS = 0`) so the new mechanism is the only thing standing
between the write and the homeostat.

**Off is today's plant, bit for bit.** `params.SLOW_WEIGHTS = False` and
`Engine.slow_weights` False: the slow array stays all zeros, and the three places that read it
(the LTD floor, the scaling floor, the consolidation step) reduce to master's expressions
numerically. Guards: `REFERENCE_DIGEST` unchanged; the inject-only twin guard of 8.12; the
off-path digest script prints master's `de63fa6f...` from this branch with the flag off. There
is no on-path digest guard, because with the flag on every latched synapse changes the numbers
and that is the mechanism.

Mechanism (engine, not driver):
- `brainsim/params.py`, appended block, values fixed before the run and not retuned:
  `SLOW_WEIGHTS = False`, `SLOW_TAG_FRAC = 0.85` (a synapse whose fast weight is at or above
  this fraction of `w_max_n[post]` at a sweep is tagged; chosen from the gap between the
  rest weight of the pair rule, ~0.72 to 0.75 `w_max`, and the written value, 0.876 `w_max`;
  a value inside the rest distribution would floor the whole plant and a value above the
  write would floor nothing), `SLOW_TAU_SWEEPS = 300` (per-sweep decay of the slow component,
  `exp(-1/300)`, so a stored floor loses 3 % in ten sweeps and 63 % in 300 s: forgetting,
  not permanence).
- `Network.w_slow` (float32, one per synapse slot, zero at birth and zeroed on kill).
- The 8.12 identification pass runs its discarded copy with `slow_weights` off as well as
  `encode_mode` off (the default plant), so both twins of T1 pick the same W.
- Fast weight `net.w` is the transmitted weight and stays the only thing STDP potentiates,
  scaling scales and the two prunes read. Three changes, each a floor:
  (1) pair LTD in the tick: `w = max(w * (1 - g a_minus y_post), w_slow)` in place of
  `max(..., 0)`; (2) synaptic scaling: `w = clip(w * factor, w_slow, w_max)` in place of
  `clip(..., 0, w_max)`; (3) at the start of every slow sweep, before scaling and the prunes,
  with the flag on and on alive excitatory synapses only: `w_slow *= exp(-1/SLOW_TAU_SWEEPS)`,
  then for tagged synapses (`w >= SLOW_TAG_FRAC * w_max_n[post]`) `w_slow = max(w_slow, w)`.
  The weak-synapse prune (`w < 0.05 w_max`) and the rate-driven structural prune (weakest
  `|w|` among a cell's inputs) are not changed; a floored synapse escapes them only by being
  heavier, never by exemption. Sleep is not special-cased (no consolidation stub this turn).
- Engine bookkeeping: `stats["slow_tagged_last"]` (synapses tagged at the last sweep),
  `stats["slow_n"]` and `stats["slow_mean_frac"]` (alive excitatory synapses with a nonzero
  slow component and their mean `w_slow / w_max`), refreshed at the sweep.
- Telemetry: frame gains `slow` (`on`, `n`, `mean_frac`, `tagged_last`, and, when `encode_W`
  is nonempty, `w_onto_W`, `w_slow_onto_W`, `n_onto_W` over the alive ctx E -> W synapses:
  engine truth for the panel); config gains `slow_weights`, `slow_tag_frac`, `slow_tau_sweeps`.
  Reading a frame consumes no RNG.
- Worker: `{"cmd": "slow", "on": bool}` sets the flag (non-bool rejected `on must be a bool`).
- UI: a `Slow weights` panel under `Encode-mode`, checkbox set from `f.slow.on` every frame
  (engine truth, never the click), one line of the four counts, and the ctx -> W fast and
  slow means read from the frame. Gloss: *the slow number is the floor the mop cannot push
  the W inputs below; when it is zero there is no trace.*

Kill test T1 (predeclared): driver `tests/k813_slow_weights.py`, seed 1, the 8.2 warm-up to
t = 120,000 and baseline to 122,000, `encode_mode` on with `ENCODE_GRACE_TICKS = 0`, present
A for 2,000 ticks (the 8.12 write lands at t = 124,000, the mask comes off the same tick),
then 11 unprotected sweeps to t = 135,000, twice: `slow_weights` False (fast-only twin) and
True. Measured on the identity-tracked donor -> W and W -> W synapses of the write at
124,000, 125,000 (first unprotected sweep) and 135,000: survivors, killed, mean `w / w_max`
of the survivors. **T1 passes iff** with the flag on, killed = 0 in both groups at 125,000
and at 135,000 and the survivors' mean stays >= 0.85 `w_max` for donor -> W at 135,000, while
the fast-only twin loses synapses or falls below that at 125,000 (else the sweep did not
"wipe" and the test is void, recorded as such). Also recorded, not a pass bar: hpc E / ctx E
idle rates over 133,000 to 135,000 in both twins against the K0.2 band; A-then-B: from the
135,000 flag-on plant present B for 2,000 ticks (its own write, grace 0), then 5 sweeps, and
table donor_A -> W_A, W_A -> W_A, donor_B -> W_B, W_B -> W_B (n, mean fast, mean slow,
killed) with exclusive deletions (A synapses killed by B's epoch); and full A / half cue /
none 50-tick W_A spike counts at 142,000 as a diagnostic only. K1.1 proper is not run.

Prediction, before the run: fast-only twin: ~40 donor -> W and ~15 W -> W killed at 125,000
(8.11 measured 44 and 15 for the same seed and write) and the survivors' mean back near
0.80; flag on: 0 killed, donor -> W mean 0.876 -> ~0.85 by 135,000 (the floor decays 3 %,
scaling cannot go below it, LTP cannot lift it much past the ceiling), W -> W at 0.718 is
below the tag and is NOT floored, so it may be pruned exactly as in the twin: that is an
honest limit of a tag at 0.85, recorded not fixed. Idle rates unchanged to two decimals
(a few hundred floored synapses among ~300,000). Full A lights more of W_A than none; the
half cue is not expected to reach 13/16 and is not scored.

Result (2026-09-30, branch `two-timescale`, seed 1, log
`~/.cache/scratch/brainsim-tt/t1_seed1.log`, JSON `t1_seed1.json`). Off path: `REFERENCE_DIGEST`
and the inject-only twin guard pass, and the off-path digest script prints master's
`de63fa6f...` from this branch; the 16 new tests pass. **T1: FAIL.** The fast-only twin was
wiped as predicted: the first unprotected sweep killed 44 of 987 donor -> W and 15 of 47
W -> W synapses and scaling pulled the survivors from 0.876 to 0.804 `w_max`; by 135,000
244 donor -> W were dead (743 survivors at 0.873, so the mop erases by deletion, not by
scaling the survivors down). With the flag on the scaling half of the erosion was stopped
(survivors 0.862 at 125,000, 0.969 at 135,000, slow floor 0.910 on them) but the deletions
were not: the same 44 died at the first sweep, 340 by 135,000, and W -> W lost 33 of 47.
The rate-driven structural prune, which was deliberately left unchanged, removes the
weakest inputs of an over-target cell, and a floor makes nothing lighter. Worse, the tag
at 0.85 `w_max` sits inside the plant's own upper tail: 97,938 excitatory synapses (about a
third of all alive) carried a floor by 135,000 at a mean 0.957, 113,646 by 142,000, so the
latch ratchets the whole plant upward and the homeostat answers by killing synapses
(alive 373,078 vs 380,048 in the twin). Idle rates stayed in band (hpc E 0.842 Hz vs 0.863,
ctx E 3.23 Hz vs 3.31) but the 142,000 readout is dead: full A lit 0/16 of W_A, the half cue
0/16, none 0/16 (W_B 1/16 in every arm). A-then-B: B's own write landed (798 synapses
0.849 -> 0.919) and B's epoch deleted 20 donor_A -> W_A and 2 W_A -> W_A of A's marks. K1.1
not run. Nothing merged; the mechanism as tuned is rejected on its own kill test. The one
thing it did show, recorded for the next owner's call: on this plant the write is lost to
elimination, not to scaling, so a slow component that only floors the weight is aimed at
the wrong half of the homeostat.

### 8.14 Write-tagged protection from the rate-driven structural prune (predeclared 2026-09-30)

Owner's framing, accepted as the record: the standing charter (hard walls, sandbox, one
primary mechanism per branch, kill test stated before coding, REJECTED or PASS by that test).
Branch `protect-writes` from `encode-mode` dfcbc01 (not a child of `two-timescale`, whose
mechanism is rejected and not carried). Nothing merges to master. K1.1 is not redefined and
not hunted. This is a proxy mechanism, not biology, and no "inner life" is claimed.

**Hypothesis.** 8.13 showed the encode write dies to the rate-driven structural elimination,
not to scaling: W cells sit over target for several sweeps after the presentation, and
`_prune_incoming` kills their weakest `|w|` excitatory inputs, which after a uniform +0.15
`w_max` bump are the written rows themselves (donor -> W is nearly the whole ctx input of a W
cell: 987 synapses onto 16 cells against an in-degree near 63). A labelled write tag that
exempts only the written synapses from that prune, for a fixed window of `PROTECT_SWEEPS = 5`
sweeps, with synaptic scaling, pair LTD and the weak-synapse prune fully in force, lets
scaling settle W back to target inside the window, after which the rows survive on their own
at the plant's background churn rather than at the over-target kill rate.

**Kill test T2 (seed 1, `tests/k814_protect_writes.py`).** Same protocol as 8.13 T1: warm
to 120,000; twins from the 122,000 plant with the flag off and on, both encode-mode with
`ENCODE_GRACE_TICKS = 0`; A presented 122,000 to 124,000; the write lands at 124,000; the
protected window is the five sweeps 125,000 to 129,000; the sweep at 130,000 is the first
unprotected one; measured at 135,000 after six unprotected sweeps. PASS requires all of, on
the flag-on twin at 135,000, identity-tracked from the 124,000 marks:
donor -> W killed <= 98 of 987 (10 %); W -> W killed <= 10 of 47; donor -> W survivors'
mean >= 0.82 `w_max` (half the write delta retained above the 0.766 pre-write mean);
protected count 0 (the window ended, nothing ratchets); idle 133,000 to 135,000 hpc E in
[0.5, 1.5] Hz and ctx E in [3.0, 5.0] Hz. Valid only if the flag-off twin lost >= 20 % of the
donor -> W marks by 135,000 (8.13 measured 244 of 987). Any failed criterion is REJECTED.

**How it differs from closed work.** 8.3 exempted every hpc afferent from elimination,
permanently, plant-wide, and measured K1.1; this tags only the synapses the labelled write
touched, for five sweeps, and measures structural persistence after the window. 8.11's grace
and 8.12's `ENCODE_GRACE_TICKS` are a cell-level mask on W that also blocks scaling and LTD
and lasts one sweep; here scaling and LTD keep full authority over W, and the grace is set to 0
in the test. 8.13 was a weight floor that blocked scaling and LTD and tagged by threshold
(ratchet); this touches only elimination and tags only at the write. It is not a floor or a
cap on the test: the test is survival after the exemption has expired.

**Prediction, written before the run.** Inside the window the rows cannot be eliminated by
construction (only the weak-synapse prune can kill them, which scaling does not reach in five
sweeps), so 125,000 to 129,000 will show 0 killed. The honest question is 130,000 to
135,000. 8.3 measured that scaling alone strips 16 to 17 % of amplitude when elimination is
gone, so the survivors' mean criterion is at risk; and if W is still over target when the
window ends, elimination resumes at the 8.13 rate (about 44 at the first unprotected sweep)
and the killed criterion fails. I expect the second: rates settle slower than five sweeps.

**Off is today's plant, bit for bit.** `params.PROTECT_WRITES = False` and
`Engine.protect_writes` False: `Network.protect` stays all zeros, the prune mask is not
computed, the tag is never set. Guards: `REFERENCE_DIGEST` unchanged; the inject-only twin
guard of 8.12; the off-path digest script prints master's `de63fa6f...` from this branch with
the flag off (checked before the run). With the flag on but no write ever made the digest is
also unchanged (nothing to protect).

Mechanism (engine, not driver):
- `brainsim/params.py`: `PROTECT_WRITES = False`, `PROTECT_SWEEPS = 5`.
- `Network.protect` (int16 per synapse slot: sweeps of exemption left; 0 at birth, 0 on kill).
- `Engine._tag_written(W, donor_ids)` at the encode write tick (`_encode_tick` at
  `t_present_end`, after both writes): every alive synapse with post in W and pre in W or in
  the write's donor set gets `PROTECT_SWEEPS`; `stats["protect_tagged_last"]`.
- `_prune_incoming`: with the flag on, a cell's candidate inputs exclude `protect > 0`; the
  prune still takes its quota from the remaining inputs (`stats["protect_spared_last"]`
  counts the skipped protected candidates of the excitatory prune).
- `_protect_sweep_done` after `structural_update` in the sweep: every positive tag minus one;
  `stats["protect_n"]`.
- Not changed: synaptic scaling, pair LTD, the weak-synapse prune (`w < 0.05 w_max`), growth,
  sleep, the encode schedule itself. The identification copy runs with the flag off.
- Telemetry: frame `protect` (`on`, `n`, `sweeps_left_max`, `tagged_last`, `spared_last`,
  and over alive ctx E -> W synapses `n_onto_W`, `n_onto_W_protected`, `w_onto_W`); config
  `protect_writes`, `protect_sweeps`. Worker `{"cmd": "protect", "on": bool}`. UI panel
  `Protected writes` under `Encode-mode`, every number from the frame.
- Tests: `tests/test_protect_writes.py`.

**Result (2026-09-30, branch `protect-writes`, seed 1, `~/.cache/scratch/brainsim-pw/t2_seed1.log`):
REJECTED on the amplitude criterion; five of six criteria held and the test was valid.**
Flag-off twin at 135,000: donor -> W 244 of 987 killed (wiped, valid), W -> W 27 of 47.
Flag-on twin, identity-tracked from the 124,000 marks: donor -> W killed 0 at 125,000, 2 at
130,000, 4 at 135,000 (bar 98); W -> W killed 0, 1, 1 (bar 10); protected count 0 at 135,000
(1034 tagged at the write, spared per sweep 1034, 1034, 1034, 977, 614, then 0, so the
over-target prune pressure on W was already fading in the last two protected sweeps); idle
133,000 to 135,000 hpc E 0.769 Hz, ctx E 3.33 Hz (in band; twin 0.863 and 3.31); alive
379,902 against 380,048. The structural half of the hypothesis held: after the window the
rows died at background churn, not at the over-target rate. The amplitude did not: with
nothing to eliminate, synaptic scaling took the whole excess off every row, donor -> W
survivors' mean 0.876 at the write, 0.790 at 125,000, 0.624 at 130,000, 0.771 at 135,000
(bar 0.82; the pre-write mean was 0.766, so at 135,000 the write is gone in amplitude and
the rows sit at the plant's rest weight); W -> W 0.718 -> 0.654 -> 0.538 -> 0.580. The
prediction was wrong in the direction it feared and right in the outcome: elimination did not
resume, scaling did the stripping, exactly the 8.3 finding measured from the other side.
A-then-B diagnostic (flag on, at 142,000): W_A and W_B overlap 1 of 16; A marks killed in B's
epoch 52 donor -> W and 9 W -> W (the B presentation drove W_A over target and, unprotected,
its rows were pruned again); donor_B -> W_B 878 written 0.788 -> 0.880, 0 killed by 142,000,
mean 0.723 (scaled away in five sweeps, same as A). Readout at 142,000 (diagnostic only):
0 of 16 of W_A and of W_B under full A, half cue and none; hpc E 8 spikes in 50 ticks.
K1.1 not run. Not merged. The finding that survives: on this plant the two halves of the
homeostat are redundant against a uniform write; removing elimination hands the erasure to
scaling, and removing scaling (8.13) hands it to elimination. A write that persists through
both would have to be non-uniform across a cell's inputs (so the cell's rate can be
homeostated without flattening the written contrast), which is not a knob on this mechanism.

### 8.15 Selective-write contrast fixture: a diagnostic, not a mechanism (predeclared 2026-09-30)

Owner's direction after the outside read of 8.13 and 8.14 (Codex, recorded in the project
memory): the claim "the homeostat erases every write" is proven only for uniform writes. Branch
`selective-write-fixture` from `encode-mode` dfcbc01. **No engine file changes on this branch.**
Everything below is driver-level on the default plant (encode_mode off, no mask, no grace, no
protection). Not a mechanism, not an encode protocol, no K1.1 claim. Nothing merges.

**Hypothesis.** Under the current plant a selective within-cell write keeps its contrast
through 60 s, including the plant's own 20 s sleep and an intervening B presentation, while an
equal-sized uniform write on the same synapses does not keep its excess.

**Protocol (seed 1, `tests/k815_selective_write.py`).** Warm to 120,000; idle to 122,000;
present A 122,000 to 124,000 on the default plant (common to all arms, so the presentation's
rate excursion is in every arm including the sham). W = top-16 hpc E cells by spike count in
that presentation. Marks = every alive ctx E -> W synapse at 124,000, identity (pre, post,
born). Per W cell the marks are ranked by the donor's spike count during A (ties by synapse
id); the top half (ceil) is the up set U, the rest the down set D. Three deep copies at
124,000 (same RNG state):
- **selective**: U `+= 0.15 w_max` (clamped at `w_max`); per cell, D lowered equally by that
  cell's actual total increase divided by |D| (clamped at `0.10 w_max`, above the 0.05 prune
  line), so the cell's summed weight is unchanged up to the clamp residual, which is reported;
- **uniform**: U and D `+= 0.15 w_max` (clamped); the 8.6 write on ctx -> W;
- **sham**: nothing.
Then the plant runs untouched: wake to 140,000, its own sleep 140,000 to 160,000, wake,
B presented 162,000 to 164,000, measured at 184,000 (60 s after the write). Snapshots at
124,000 (after the write), 125,000, 130,000, 140,000, 160,000, 164,000, 184,000.

**Metric (defined before the run).** For each W cell, `C = mean(w / w_max over its U marks)
- mean(w / w_max over its D marks)`, a dead mark counted as weight 0; C is the mean over the
16 cells. `M` is the mean of `w / w_max` over all marks (U and D), dead as 0. Retention
against the sham twin: `R_C(arm, t) = (C_arm(t) - C_sham(t)) / (C_arm(124k) - C_sham(124k))`
and `R_M` likewise. Reported beside them, without a bar: the survivors-only `C`, the U-half
mean alone (dead as 0) and its retention, deaths in U and in D per arm, per-cell summed
weight, W-cell rates.

**Kill numbers, fixed now.** PASS iff at 184,000: selective `R_C >= 0.80` (the primary bar);
uniform `R_M < 0.80`; selective-arm idle 182,000 to 184,000 hpc E in [0.5, 1.5] Hz and ctx E
in [3.0, 5.0] Hz. Valid only if the selective written contrast
`C_sel(124k) - C_sham(124k) >= 0.20`. Otherwise REJECTED, with the failing clause named.
Because a dead D mark counts as 0 and so raises C, the U-half retention is printed next to
`R_C`; if `R_C` passes only through D deaths that is said in the result.

**Prediction, written before the run.** The selective arm will retain more than the uniform
arm, because its cells are not pushed over target and neither scaling nor elimination has an
error to correct. It will still fall short of 0.80, and the eraser will be the pair rule's own
drift toward its rest weight (0.72 to 0.75 `w_max`; hpc `a_plus` 0.05, `a_minus` 0.06 is the
fast learner), which pulls U down and D up regardless of rate. Guess: `R_C` 0.3 to 0.6.

**Diagnostics on the same branch, no bar.** (1) 50-tick readout at 184,000 per arm (full A,
half cue, none; W cells spiking). (2) `tests/k11_never_trained.py`: the K1.1 half cue on an
age-matched twin that never saw A, counted on the trained run's assembly cells; K1.1 remains
FAIL. (3) `tests/k815_slot_reuse.py`: how many queued delay-ring events belong to a synapse
slot that was killed and reused by growth in the same sweep (the master defect Codex found:
delivery checks `alive`, not identity or `conduct`); measurement only, master not fixed.

**Result (2026-09-30, branch `selective-write-fixture`, seed 1, logs
`~/.cache/scratch/brainsim-sw/`): PASS on the predeclared bar, and the predeclared caveat
applies: what is retained is structure (which synapses exist), not amplitude.**
W is the 8.2 assembly's 16 cells; marks 823 alive ctx E -> W at 124,000 (U 416, D 407; the
default-plant presentation had already stripped the rows, sham mean 0.596 `w_max`). Writes:
selective 1 clamped up, 5 clamped down, largest per-cell residual 0.112 (raw weight units);
uniform 6 clamped. Written selective contrast 0.303 (valid).

| arm, at 184,000 | C (dead = 0) | C survivors only | M | U mean | dead U / 416 | dead D / 407 |
|---|---|---|---|---|---|---|
| selective | 0.353 (0.273 at write) | 0.021 (0.273 at write) | 0.672 | 0.849 | 11 | 170 |
| uniform | -0.040 | -0.004 | 0.700 (0.746 at write) | 0.682 | 73 | 57 |
| sham | -0.039 | -0.011 | 0.695 (0.596 at write) | 0.677 | 94 | 81 |

Retention against the sham: selective `R_C` 1.189 at 125,000, 1.503 at 140,000, 1.482 after
the sleep, 1.305 after B, **1.292 at 184,000 (bar 0.80)**; selective U-half retention 1.148;
uniform `R_M` 1.057 at 125,000, 0.284 at 140,000, -0.003 after B, **0.031 at 184,000
(bar < 0.80)**. Selective-arm idle 182,000 to 184,000: hpc E 0.869 Hz, ctx E 3.55 Hz (in band;
sham 0.814 and 3.52). Both clauses of the hypothesis hold by the numbers fixed beforehand.

What the pass consists of, stated as the predeclaration required: among the marks that are
still alive, the amplitude contrast is gone (survivors-only C 0.273 -> 0.021; every surviving
mark in every arm sits near 0.87 `w_max`, U and D alike). The contrast that persists is who
is alive: the first sweeps after the presentation find W over target and the rate-driven
prune takes the weakest inputs, which in the selective arm are the lowered D rows (110 dead
at 125,000, 152 by 130,000, 170 at the end against 81 in the sham), while the raised U rows
are spared (11 dead against 94). The plant converted a weight contrast into a wiring
contrast within six sweeps and then kept it through sleep and B. `R_C` passes through both
halves, not through D deaths alone (U-half retention 1.148), but in both halves it is
survival, not weight. Per-cell summed mark weight ends equal across arms (1.13, 1.18, 1.17
of the sham's write-time sum): the homeostat normalised the total and left the pattern of
survivors. The prediction was wrong on the metric (guessed 0.3 to 0.6) and right on the
mechanism it named for amplitude: the surviving weights all relax to one value.
Readout at 184,000 (diagnostic only): selective full A 6 of 16, half cue 1, none 0; uniform
4, 0, 0; sham 2, 1, 0.

**Diagnostic (2), never-trained half-cue control (`tests/k11_never_trained.py`,
`never_trained.log`; trained replay equals `run_experiment` for both plants). K1.1 remains
FAIL; bar unchanged.** Cells counted are the trained run's assembly (and W).

| plant | row | half cue 50 / 100 / 200 | full A at 50 | none at 50 |
|---|---|---|---|---|
| default (8.2), assembly 16 | trained | 1 / 1 / 1 | 1 | 1 |
| default (8.2), assembly 16 | never trained | 2 / 5 / 11 | 12 | 0 |
| encode-mode (8.12), W 16 | trained | 5 / 5 / 10 | 10 | 2 |
| encode-mode (8.12), W 16 | never trained | 2 / 4 / 10 | 11 | 0 |

On the default plant the twin that never saw A answers the cue better than the trained plant:
the presentation strips the assembly's afferents and leaves it less responsive than it began.
Under encode-mode the trained plant is 3 cells ahead at 50 ticks under the half cue and level
or behind everywhere else (full A 10 against 11; half cue at 200 ticks 10 against 10). The
8.6 to 8.12 readout numbers are therefore within a few cells of untrained feedforward
responsiveness: the assembly is "the cells that A drives anyway", and no run so far has shown
recall above that.

**Diagnostic (3), delay-ring slot reuse (`tests/k815_slot_reuse.py`, `slot_reuse.log`).**
Standard run, seed 1, 0 to 135,000 with A at 122,000: 135 sweeps, 214,458 synapses killed,
**0 slots reused in the sweep that killed them, 0 stale events** among 4.09e8 delivered. An
independent hook on `kill_synapses` / `add_synapses` over the first 30 sweeps agrees, and
shows why: the weak-synapse prune, the only path that frees a slot before growth runs in the
same sweep, killed nothing (one kill call per sweep, the structural one, whose slots are held
back until after growth). The defect is real in the code and did not fire in this run; it
cannot have shaped the recorded results on this seed. Master not changed.

### 8.16 Sweep-level heterosynaptic write on hpc afferents: the engine's own selective write (predeclared 2026-09-30)

Follows from 8.15: a selective within-cell write survives as wiring, but there the driver
chose the cells and wrote the weights. Branch `hetero-write`, child of
`selective-write-fixture` 9bfcb43. One labelled proxy mechanism in the engine, no oracle:
no identification pass, no W handed in, encode_mode off, no mask, no grace, no protection.
Nothing merges. K1.1 is not run as a pass attempt and its bar is untouched.

**Hypothesis.** Driven cells select themselves by their own spike count in a sweep; a
sum-conserving redistribution of each such cell's ctx inputs toward the inputs that were
active in that sweep gives the rate-driven prune a contrast to carve; the carved wiring
persists through 60 s, the plant's own sleep and an intervening B.

**Calibration, read from the default plant before any threshold was fixed (seed 1, scratch):**
idle hpc E cells with >= 5 spikes in a sweep: mean 0.50 per sweep, max 2, over 22 sweeps
(>= 4: 5.45; >= 6: 0). During A: 15 and 24 cells at >= 5 in the two sweeps, and all 16 of the
top-16 cells reach 5 in at least one of them (14 of 16 at >= 6).

Mechanism (engine, flag `params.HETERO_WRITE = False` / `Engine.hetero_write`, off path
bit-identical to master: `REFERENCE_DIGEST`, off-path digest `de63fa6f...` checked):
- In a wake slow sweep, before scaling and the prunes (`Engine._hetero_sweep`): for every
  hpc E cell with `counts >= HETERO_TRIGGER_SPIKES = 5` this sweep, over its alive ctx E
  inputs: `z` = the input's presynaptic spike count this sweep as a z-score over that cell's
  inputs, clipped to `+- HETERO_Z_CLIP = 2`, re-centred to mean 0 per cell;
  `w += HETERO_ETA * w_max * z` with `HETERO_ETA = 0.15` (the 8.15 step at |z| = 1), clamped
  to `[min(w, HETERO_FLOOR_FRAC * w_max), w_max]`, floor 0.10 (above the 0.05 prune line; a
  weight already below the floor is not lifted to the floor by the clamp; it can still rise
  through its own positive step). The cell's summed weight is unchanged up to
  the clamps. No RNG, no synapse created or killed, nothing in sleep.
- Untouched: the pair rule, synaptic scaling, both prunes, growth, hpc -> hpc, ctx, sense.
- `Engine.hetero_last` (the last write: cells, synapse ids and identities, dw) for drivers;
  `stats` counters; frame key `hetero`; config keys; worker cmd `hetero`; UI panel
  `Heterosynaptic write` from the frame.

**Kill test T4 (`tests/k816_hetero_write.py`), numbers fixed now.** Per seed: warm to
120,000, idle to 122,000, then three deep copies: **on** (flag on from 122,000), **off**
(flag off, the twin), **never** (flag on, no A). on and off get A 122,000 to 124,000; all
get B 162,000 to 164,000; all run untouched through the plant's sleep 140,000 to 160,000 to
184,000. W = the 16 hpc E cells with the highest A count in the on arm. Marks = the ctx E
-> W synapses the engine wrote at the sweeps 123,000 and 124,000 on W cells, identity
(pre, post, born); U = net dw > 0, D = net dw < 0. Metric exactly as 8.15 (`contrast`,
dead marks as 0), retention against the off twin with the 124,000 values as the denominator.
All required on seed 1 for PASS:
- c1 self-selection: >= 12 of the 16 W cells triggered a write in the A sweeps;
- c2 written contrast: `C_on(124k) - C_off(124k) >= 0.20`;
- c3 retention: `R_C(184k) >= 0.80`;
- c4 idle 182,000 to 184,000 in the on arm: hpc E in [0.5, 1.5] Hz, ctx E in [3.0, 5.0] Hz;
- c5 background: mean triggered cells per wake sweep over the sweeps 126,000 to 140,000 and
  166,000 to 184,000 in the on arm <= 2.0 (calibrated idle value 0.50).
Any miss is REJECTED with the clause named. Seeds 2 and 3 run the same protocol and are
reported with the same criteria as replication; the verdict is seed 1's, the record's seed,
because the other seeds' plants have never been checked against the Stage 0 tests.
Reported without a bar: survivors-only contrast, U-half retention, deaths in U and D, A marks
lost in B's epoch, alive synapse count against the twin, and the 50-tick readout at 184,000
on W for on, off and never (full A, half cue, none), so every readout number has its
never-trained baseline beside it.

**Prediction, written before the run.** c1 and c5 will hold (the calibration says so, unless
the write itself raises firing). c2 is the doubtful one: the default-plant presentation
strips W's inputs in the same sweeps, and the write is graded, so the written contrast may
land under 0.20 after one prune. If c2 holds I expect c3 to hold, because 8.15 showed the
prune carves whatever ordering it is given. B will write onto any W cell it also drives
and that will cost A contrast.

**Result (2026-09-30, branch `hetero-write`, logs `~/.cache/scratch/brainsim-hw/t4_seed{1,2,3}.log`):
PASS on seed 1, and the same five criteria hold on seeds 2 and 3.** What persists is wiring,
as in 8.15; the readout does not follow reliably.

| criterion | bar | seed 1 (verdict) | seed 2 | seed 3 |
|---|---|---|---|---|
| c1 W cells that wrote during A | >= 12 of 16 | 16 | 16 | 16 |
| c2 written contrast at 124,000 | >= 0.20 | 0.309 | 0.273 | 0.271 |
| c3 contrast retention at 184,000 | >= 0.80 | 1.221 | 1.240 | 1.259 |
| c4 idle hpc E / ctx E (Hz) | 0.5-1.5 / 3-5 | 0.913 / 3.61 | 0.884 / 3.34 | 0.875 / 3.50 |
| c5 background cells per wake sweep | <= 2.0 | 0.82 | 0.79 | 0.45 |

Seed 1 detail: 15 and 19 hpc E cells wrote at the two A sweeps; marks 1032 (U 488, D 544);
contrast 0.292 at 124,000 -> 0.425 at 140,000 -> 0.427 after the sleep -> 0.408 after B ->
0.370 at 184,000 (off twin -0.017 -> -0.008); U-half retention 1.138; dead at the end U 54
of 488, D 296 of 544 (off twin 168 and 189 of the same identities); survivors-only contrast
0.153 -> 0.026 (weights equalise again, as in 8.15); alive synapses 358,971 against 358,788
in the twin. B's two sweeps: 1 W cell wrote again, 44 mark identities rewritten (seed 2: 3
cells, 117; seed 3: none). Seeds 2 and 3: marks 791 and 652, U-half retention 1.261 and
1.362, survivors-only contrast at the end 0.004 and 0.002.

The prediction named c2 as the doubtful criterion; it held on all three seeds. The rest went
as predicted: the prune carved the ordering the write gave it, and B cost some A contrast
where it drove the same cells.

Readout at 184,000, 50 ticks, W cells spiking of 16 (DIAGNOSTIC ONLY, K1.1 not run, bar
unchanged), with the never-trained arm beside it:

| seed | arm | full A | half cue | none |
|---|---|---|---|---|
| 1 | on | 10 | 3 | 0 |
| 1 | off | 2 | 1 | 0 |
| 1 | never | 4 | 2 | 1 |
| 2 | on | 6 | 2 | 0 |
| 2 | off | 7 | 2 | 1 |
| 2 | never | 4 | 0 | 0 |
| 3 | on | 4 | 1 | 0 |
| 3 | off | 5 | 3 | 0 |
| 3 | never | 7 | 1 | 1 |

Seed 1 shows the first full-A readout clearly above both the twin and the never-trained
baseline a minute after the presentation (10 against 2 and 4); seeds 2 and 3 do not (6
against 7 and 4; 4 against 5 and 7). The half cue is at baseline on every seed. So: the
engine can now leave a stimulus-specific, inspectable, persistent change in its own wiring
with no oracle, on three seeds; that change does not yet make the cells answer the stimulus
reliably, and pattern completion is untouched. K1.1 remains FAIL.

Guards: `REFERENCE_DIGEST` and the off-path digest script (`de63fa6f...`) hold with the flag
off; 17 tests in `tests/test_hetero_write.py`; fast suite as master's (the three standing
red kill tests only).

Reviews before any merge (2026-09-30, read-only): security clean. Architecture OK with notes,
recorded here as the pre-merge list, not applied after the kill test so the tested commit
stays exact: (1) the write ignores `encode_mask`, so encode-mode and this flag together are
an unrecorded plant: make them mutually exclusive in the worker or skip masked cells;
(2) the panel gloss hard-codes "5 times" while `hetero_trigger_spikes` is in the config:
render it from the config; (3) `cell_ids_last` is cut to 32 silently: say so in the frame;
(4) `hetero_last` holds one sweep, the driver relies on stepping exactly one sweep at a time:
keep a short bounded history or assert the alignment; (5) move the z-score and clamp maths
to a pure helper beside `encode.py`'s; (6) read the `HETERO_*` constants with defaults.
The branch descends from `encode-mode` (8.12), which is itself unmerged, so folding this into
master is a decision about that lineage too.

**Merged to master (2026-09-30), owner's decision under the merge policy: work that passed
its predeclared test and reasonably belongs in the sim may be folded in; the no-merge rule
protects master from unproven spikes.** What merged, all off by default, with the default
plant bit-identical to the Stage 0 plant (`REFERENCE_DIGEST` and the off-path digest
`de63fa6f...` hold on the merged tree): this mechanism (`HETERO_WRITE`), its parent
encode-mode (8.12, `Engine.encode_mode`; K1.1 still fails under it, it comes along as a
labelled mode and not as a proven mechanism), and the 8.15 diagnostics (test-side only).
8.13, 8.14 and every branch before 8.12 stay unmerged. K1.1 remains FAIL and its bar is
untouched.

The pre-merge list was applied first, tests written before the code by a different worker:
(1) the worker refuses to turn on the heterosynaptic write while an encode schedule is live
(`encode_stage != "off"`) and refuses encode-mode while the write is on, and the engine never
writes onto an encode-masked cell (a no-op with the mask all False); (2) the panel gloss takes
the trigger count from the config; (3) the frame's `hetero` key carries `cell_ids_truncated`
(cap `hetero.FRAME_CELL_CAP = 32`); (4) the T4 driver raises if two hetero sweeps land in one
chunk; (5) the redistribution maths lives in the pure helper `brainsim/hetero.py`
(`redistribute`), moved unchanged and pinned by a sha256 of the weights taken at the tested
commit 81f5a36; (6) the `HETERO_*` constants are read through `hetero.constants(p)` with
defaults. T4 seed 1 rerun on the merged tree gives a result file identical to the recorded
one (`t4_seed1_final.json` against `t4_seed1.json`).

Reviews of the merged tree: security clean. Architecture: the first pass found that the
worker's exclusion tested the mode flag and not the live schedule (encode on, present, encode
off, hetero on was accepted); fixed as in (1). Recorded and not changed here: `brainsim/encode.py`
reads the global `params` module for region sizes and default arguments instead of the
engine's own `p`, so a driver with a different region table is not supported; the `HETERO_*`
defaults are written both in `params.py` and in `hetero.constants` while `ENCODE_*` has none;
the frame field `spiked_last_50` hard-codes its window in its name; a driver that sets both
flags by hand runs the identification pass under the write (the worker cannot reach that
state). The served simulation keeps running the pre-merge engine until it is restarted,
which resets the running network and is the owner's call.

### 8.17 Inhibition as the hippocampal rate controller, with the heterosynaptic write (predeclared 2026-09-30)

Recorded here from the unmerged branch `inh-homeostat` (3adb30e); the code is not on master.

Owner's decision (2026-09-30): the standing exclusion of inhibitory plasticity (Vogels) is
lifted for one experiment in which several mechanisms run together, as the published
recipes do. Branch `inh-homeostat` from master 176d64c. A spike: nothing merges unless it
passes and the owner says so. K1.1 is not run as a pass attempt and its bar is untouched.

**Why this, in plant terms.** 8.13 to 8.16 showed that on this plant the two excitatory
stabilisers (synaptic scaling and the rate-driven elimination of a cell's weakest inputs)
act within one sweep and flatten any written weight contrast; 8.16's write survives only as
wiring and the readout does not follow on seeds 2 and 3. In the published assembly models
(Vogels et al. 2011; Zenke, Agnes and Gerstner 2015) the firing rate of excitatory cells is
held by plastic inhibition, and the excitatory weights are left to carry the memory. That is
the one change here: on `hpc` excitatory cells the rate controller becomes inhibitory
plasticity instead of the two excitatory stabilisers. It reuses the two exemptions 8.5 built
(`encode_mask`), now for the whole population and without an oracle.

**Hypothesis.** With inhibition holding the rate of `hpc` E cells, the heterosynaptic write's
contrast persists as weight amplitude, not only as wiring, and the cells that wrote answer
the written stimulus above the never-trained baseline on every seed.

**Mechanism (engine, one labelled mode, flag `params.INH_HOMEOSTAT = False` /
`Engine.inh_homeostat`, runtime switch, off path bit-identical to master).** While on, for
postsynaptic `hpc` E cells only:
- Inhibitory STDP on their alive inhibitory inputs, the rule of Vogels et al. 2011 as in the
  ModelDB 143751 / Brian2 port (shape checked against that code on 2026-09-30; the paper
  text itself was not readable): with `m = -w` the inhibitory magnitude, at the delivery of
  an inhibitory spike `m += g * INH_ETA * m_max * (y_post[post] - alpha[post])`, at a
  postsynaptic spike `m += g * INH_ETA * m_max * x_pre[pre]` for each inhibitory input,
  `m` clamped to `[0, m_max]`, `m_max = w_max_n[post] * I_GAIN` (the engine's existing
  inhibitory scale; initial weights are 0.2 to 0.6 of it), `alpha = 2 * r_target[post] *
  TAU_TRACE_MS / 1000` (0.04 at the 1 Hz target), traces = the engine's existing 20 ms
  `x_pre` / `y_post`, `g` = the engine's existing plasticity gate (1 awake, 0.3 asleep).
  No RNG, no synapse created or killed by the rule.
- `INH_ETA = 0.004` per unit trace, as a fraction of the bound. Marked **initial and mine**:
  the published learning rates are in conductance units that do not transfer; this value is
  the order of the Brian2 port's (1e-2 on weights of order one) expressed against our
  typical weight, and it is not searched. Rate arithmetic at this value: with ~6 Hz
  inhibitory inputs a cell `d` Hz above target gains `0.004 * 0.24 * d` of the bound per
  second per synapse, i.e. about 0.4 % per second at 5 Hz. So the rule cannot silence a
  2 s presentation and takes tens of seconds to correct a sustained error.
- Excitatory synaptic scaling and the rate-driven elimination of excitatory inputs skip
  these cells (one exemption rule shared with `encode_mask`).
- Untouched: the pair rule, the weak-weight prune, growth, the structural rules on
  inhibitory synapses, every other region, sleep, the heterosynaptic write itself.
- Pure maths in `brainsim/inhib.py`; `Engine.inh_view()` for drivers (flag, synapse count,
  mean magnitude, fractions at each bound). No worker command, frame key or UI panel on
  the branch: nothing is shown that the page could misreport; they come with a merge.

**Kill test T5 (`tests/k817_inh_homeostat.py`), numbers fixed now.** Per seed: warm the
default plant to 120,000. Copy: the **ref** lineage stays on the default plant; the **inh**
lineage switches the mode on at 120,000. Both idle to 122,000, then deep copies:
`on` (inh, write on, A), `off` (inh, write off, A), `never` (inh, write on, no A), `ref`
(default plant, write on, A: the recorded 8.16 on arm, rerun as the same-seed control).
A 122,000 to 124,000; the plant's sleep 140,000 to 160,000; B 162,000 to 164,000; readout
at 184,000 exactly as 8.16 (deep copies, 50 ticks, full A / half cue / none, W = the arm's
own top 16 by A count; `off` and `never` read on the `on` arm's W). Marks, contrast and
retention exactly as 8.16. The `on` arm then runs on, untouched, to 300,000 (a second
sleep 220,000 to 240,000).
All required for PASS, on each of seeds 1, 2 and 3 (the claim is reliability across seeds,
so one seed is not a verdict here):
- V1 control: on seed 1 the `ref` arm reproduces the recorded 8.16 values (c2 0.309,
  c3 1.221, readout 10 / 3 / 0);
- V2 rates: `on` arm idle 182,000 to 184,000 and 298,000 to 300,000: hpc E in [0.5, 1.5] Hz,
  ctx E in [3.0, 5.0] Hz; no tick after 120,000 with more than 20 % of hpc E spiking;
- V3 the controller is not pinned: at 184,000 and 300,000 at most 20 % of the inhibitory
  synapses onto hpc E sit at either bound;
- c1 the write lands: 8.16's c1 and c2 in the `on` arm (>= 12 of 16; written contrast
  >= 0.20 against the `off` twin);
- c2 amplitude persists: survivors-only contrast at 184,000 >= 0.5 x its value at 124,000
  (default plant, recorded: 0.153 -> 0.026, a factor 0.17);
- c3 the readout follows: full A at 184,000, W cells spiking in 50 ticks: `on` >= `never`
  + 4 and `on` >= `off` + 4 (of 16; the default plant meets this on seed 1 only).
Any miss is REJECTED with the clause and the seed named. Reported without a bar: the half
cue, the summed excitatory weight delivered onto W in the 50 ticks of each readout arm
(does the trace deliver more push under its stimulus), inhibitory weight means and in-degree
on W and on the rest, deaths among marks, contrast at 300,000, hpc E rate per sweep.

**Prediction, written before the run.** V2 is the doubtful clause: with both fast
excitatory stabilisers off and a controller that needs tens of seconds, the sleep to wake
transitions and B may take hpc out of band, and the pair rule's depression at these weights
will slowly lower the afferents while inhibition falls to compensate (V3 may follow). If V2
holds I expect c2 to hold, since nothing else flattens the contrast in a minute. c3 is a
coin flip per seed: a preserved amplitude contrast should deliver more drive under A, but
+4 cells on all three seeds is a high bar and the half cue will stay at baseline (no
recurrent write exists).

**Result (2026-10-01, branch `inh-homeostat` at 888f60c, one run per seed, logs
`~/.cache/scratch/brainsim-inh/t5_seed{1,2,3}.log` and `.json`): REJECTED on c3 on all three
seeds, and on V2 on seed 1. The amplitude half of the hypothesis held on every seed; the
readout half failed on every seed, in the wrong direction.**
Driver note: a fifth arm `refoff` (default plant, write off, A) is the write-off twin that
V1's contrast and retention need; it is 8.16's `off` arm and was not named in the contract.
V3 was measured as zero-fraction plus max-fraction <= 0.20 (stricter than written).

| clause | seed 1 | seed 2 | seed 3 |
|---|---|---|---|
| V1 `ref` reproduces 8.16 (c2, c3, readout) | 0.309, 1.221, 10/3/0: yes | (0.273, 1.240, 6/2/0) | (0.271, 1.259, 4/1/0) |
| V2 hpc E Hz at 184,000 / 300,000 (band 0.5 to 1.5) | **0.436** / 0.594 | 0.605 / 0.613 | 0.564 / 0.520 |
| V2 ctx E Hz at 184,000 / 300,000 (band 3 to 5) | 3.73 / 3.76 | 3.39 / 3.69 | 3.57 / 3.67 |
| V2 max fraction of hpc E in one tick (bar 0.20) | 0.056 | 0.050 | 0.128 |
| V3 inhibitory synapses at a bound, 184,000 / 300,000 | 0 / 0 | 0 / 0 | 0 / 0 |
| c1 cells triggered (of 16), written contrast (bar 0.20) | 16, 0.294 | 16, 0.359 | 16, 0.261 |
| c2 survivors-only contrast 124,000 -> 184,000 (bar x0.5) | 0.269 -> 0.222 (x0.83) | 0.319 -> 0.269 (x0.84) | 0.265 -> 0.221 (x0.83) |
| c3 full A, W cells spiking: on / off / never | **2 / 1 / 12** | **5 / 3 / 14** | **5 / 4 / 7** |

What held. With the two excitatory stabilisers off on hpc E, the written contrast persists
as weight amplitude: a factor 0.83 to 0.84 through sleep and B on every seed, against 0.17
on the default plant (0.153 -> 0.026), and it is still 0.128 / 0.163 / 0.138 at 300,000.
Activity never ran away: the worst tick had 12.8 % of hpc E spiking.

What failed. (1) The readout: the trained cells answer A less than the never-trained ones
on every seed. The excitatory weight delivered onto W under full A says where: `never`
1872 / 1772 / 991, `off` (A presented, no write) 981 / 725 / 881, `on` 1160 / 909 / 1038.
The write adds about 160 to 180 over its write-off twin, but on seeds 1 and 2 the
presentation of A itself, with or without the write, roughly halves what W receives under A
60,000 ticks later. Not diagnosed in this run; the reading I would test first is that the
pair rule is net depressing on the inputs of strongly driven cells and that scaling was
masking this on the default plant. (2) The rate: the controller is too slow at this
learning rate to be a controller. hpc E sat at 0.44 to 0.61 Hz against the 1 Hz target for
the whole 180,000 ticks while the mean inhibitory weight moved from 0.45 to 0.49 of its
bound down to 0.41 to 0.45; no synapse reached a bound. The architecture review notes that
V3 can read low by construction (the inhibitory structural prune removes the weakest
inhibitory inputs of under-active cells, which are the ones this rule drives toward zero);
here the mean barely moved, so the clause passed because the rule did little, not because
it was hidden.

Prediction check: V2 doubtful, right on seed 1 only and for the opposite reason (too little
activity, not too much); c2 holds if V2 holds, right; c3 a coin flip per seed, wrong: it
failed on all three, below the untrained baseline; half cue at baseline, right
(1 / 3 / 0 against never 6 / 1 / 2).

Reviews: security clean (no worker, frame or UI surface changed). Architecture: the rule,
scope, trace order and exemption match the contract and the off path is bit-identical; to
fix before any merge: build the hpc E mask from the engine's own net rather than
`encode.hpc_e_ids` (it asserts against the global `params.REGIONS`), guard c2 against a
non-positive denominator, report inhibitory births and deaths beside `inh_view`, and give
the flag the same worker guard as the heterosynaptic write.
K1.1 not run. Not merged. `INH_ETA` was not searched and is not to be tuned on this branch
(one run); a faster controller or a different excitatory rule is a new contract.

### 8.18 Where the drive goes: a diagnostic of the 8.17 readout loss (predeclared 2026-10-01)

Recorded here from the unmerged branch `drive-loss-diag` (c41f5d2); the driver is not on master.

Owner's instruction (2026-10-01): keep running the experiment loop without asking each round.
Branch `drive-loss-diag` from `inh-homeostat` 3adb30e. A diagnostic, not a mechanism: no
engine change, no pass bar, nothing to merge. It needs the 8.17 mode, so it sits on that
branch's code; 8.17 is not rerun as a pass attempt.

**Question.** In 8.17 the cells W received about half the excitatory weight under full A at
184,000 when A had been presented at 122,000 (`off` 981 / 725, `never` 1872 / 1772 on seeds
1 and 2), write or no write. The marked synapses' weights barely moved in the `off` arm
(mean 0.654 -> 0.626 of w_max, none died), so the loss is not on those weights. Where is it:
fewer presynaptic spikes reaching W (the cortex answering A less), fewer synapses, or
smaller weights elsewhere, and when does it appear (right after A, in sleep, after B)?

**Driver `tests/k818_drive_loss.py`.** Per seed 1, 2, 3: warm and fork exactly as T5. Arms,
all deep copies at 122,000: on the inh lineage `off` (A, write off), `never` (no A, write
on, as T5), `neveroff` (no A, write off: separates the A presentation from the write during
B); on the default lineage `refoff` (A, write off) and `refneveroff` (no A, write off: does
the default plant do the same). W = the T5 `on` arm's W for the seed (recomputed the same
way). P = the 100 ctx E cells with the most spikes in a 50-tick full-A probe on a deep copy
of the inh lineage at 122,000 (the cortical cells that answer A, fixed before any arm).
At 122,000 (before the fork), 124,000, 125,000, 140,000, 160,000, 164,000 and 184,000, on
a deep copy of each arm (so the arm itself is never perturbed), a 50-tick full-A probe with
the write off, recording:
- spikes: A's sense cells, ctx E total, P, ctx I total, hpc E total, W cells spiking;
- deliveries onto W in the 50 ticks: count, summed weight and mean weight per delivery,
  split by source (ctx E, hpc E), and the inhibitory deliveries onto W (count, summed
  magnitude);
- state, no probe needed: onto P, the alive excitatory in-degree and mean weight split by
  source (sense, ctx, hpc), the inhibitory in-degree and mean magnitude, mean threshold
  `theta` and the rate estimate `net.rate`; from P onto W and from all ctx E onto W, the
  alive count and mean weight; onto W, the inhibitory in-degree and mean magnitude.
Validity (the only bar): on each seed the `off` and `never` arms at 184,000 reproduce T5's
recorded full-A readout and delivered weight (seed 1: 1 and 981.14, 12 and 1871.7).
Output: one table per measure, arms as columns, times as rows, and a JSON record.

**What would each answer mean.** Fewer P spikes with unchanged ctx -> W weights: the loss
is upstream, in the cortex's own stabilisers reacting to A (then no hippocampal rule can fix
the readout and the cortex needs the same treatment). Same spikes, fewer or weaker
deliveries: the loss is on the hippocampal afferents outside the marks. More inhibition
onto W: the inhibitory rule or the inhibitory structural rule is doing it. If `refoff`
against `refneveroff` shows the same loss, it is the plant, not the 8.17 mode.

**Result (2026-10-01, branch `drive-loss-diag` at the driver commit, seeds 1, 2, 3, logs and
JSON `~/.cache/scratch/brainsim-diag/d_seed{1,2,3}.{log,json}`): VALID on every seed (the
`off` and `never` arms reproduce T5's readout and delivered weight exactly). The loss is
upstream, in the cortex, and it is the plant, not the 8.17 mode.**
Seeds 1 / 2 / 3. A's sense cells fire the same in every arm and at every time (43 to 54
spikes in 50 ticks). The cortical cells that answer A (P) do not:

| P spikes in the 50-tick A probe | 122,000 | 125,000, A presented | 125,000, A never presented |
|---|---|---|---|
| inh lineage (`off` / `neveroff`) | 187 / 213 / 229 | 24 / 28 / 17 | 69 / 124 / 91 |
| default plant (`refoff` / `refneveroff`) | 69 / 105 / 137 | 29 / 39 / 43 | 88 / 112 / 69 |

One second after a 2 s presentation the cortex answers A with 0.19 to 0.35 of what the
never-presented twin gives (0.62 on seed 3 of the default plant), in both lineages; the
cortex runs the default rules in both. The excitatory weight delivered onto W follows it
(125,000, presented / never: 457 / 1424, 452 / 1433, 298 / 1051 on the inh lineage;
324 / 1566, 380 / 1183, 325 / 950 on the default plant) through the number of deliveries
(ctx E -> W count 209 against 611 on seed 1), not their size (mean weight per delivery
1.96 against 2.09).
The state of P says what did it (seed 1, seeds 2 and 3 alike): P's rate estimate went to
7.8 Hz against the 4 Hz target during A, and within three sweeps the homeostat scaled P's
excitatory inputs down (sense -> P mean weight 1.54 -> 1.26, ctx -> P 1.38 -> 1.25), pruned
them (sense -> P in-degree 42.6 -> 39.0, ctx -> P 72.4 -> 55.8, hpc -> P 11.5 -> 9.0) and
grew inhibition onto P (35.9 -> 38.5). By 140,000 the weights are back above their start
(1.67, 1.53) and the inhibitory in-degree is back; the excitatory in-degree is not (39.4,
60.3). At 184,000 P still gives 0.72 / 0.36 / 1.07 of the never-presented twin on the inh
lineage and 0.89 / 0.75 / 0.73 on the default plant.
On the default plant the same over-correction lands on W itself (ctx E -> W count 933 -> 741
and mean weight 2.09 -> 1.65 by 125,000 on seed 1), which is the erasure 8.13 to 8.16
measured; with the 8.17 mode W keeps its inputs (count 933, mean 1.96) but still receives a
third of the deliveries because the cortex is answering less.
Reading: the homeostat treats two seconds of stimulus-evoked activity as a rate error and
corrects it within seconds, by about 20 % of the driven cells' input weight and up to a
quarter of their wiring. Every Stage 1 readout so far was taken through that. The 8.17
readout loss is this cortical suppression, not a hippocampal rule; no rule confined to
`hpc` can fix it. The hippocampal half of 8.17 (amplitude persists) stands as recorded.
Not diagnosed here: why P at 122,000 is so much higher than the never-presented twin
later (187 against 69 to 124); P was chosen as the top 100 of one probe, so part of it is
selection on noise.
Nothing to merge; no engine change.

### 8.19 Which half of the homeostat suppresses a seen stimulus: an ablation diagnostic (predeclared 2026-10-01)

Recorded here from the unmerged branch `homeostat-ablation`; the driver is not on master.

Branch `homeostat-ablation` from `drive-loss-diag` c41f5d2. A diagnostic: no engine change
(the driver overrides parameters on its own engines), no pass bar, nothing to merge. Its
purpose is to choose the one mechanism change the next contract makes.

**Background.** 8.18: within three sweeps of a 2 s presentation the homeostat scales the
answering cortical cells' used inputs down about 18 % and prunes up to a quarter of their
excitatory wiring; the weights recover in about 15 s, the wiring does not. Biology does not
do this on a seconds timescale: synaptic scaling is measured over hours to days (Turrigiano
et al. 1998) and most spines in adult cortex persist for months (Grutzendler et al. 2002;
Trachtenberg et al. 2002). Second opinion (Codex, 2026-10-01, `codex_818.md` in the scratch
directory; its claims about the code checked against `engine.py`): scaling acts only on
inputs whose presynaptic cell fired in the sweep, so it targets the stimulated pathway;
the structural gain is `STRUCT_BASE * (1 + 9 exp(-age/60 s))`, about 0.11 per sweep at
122 s, not 0.05; the group latch can hold regrowth. It advises isolating the structural
rule first and warns that lowering gains may only postpone the erasure. I add the scaling
arm so one run separates the two.

**Conditions (default plant warmed to 120,000, then per-engine parameter overrides):**
`C0` none (the default plant); `C1` `STRUCT_BASE = 0` (no rate-driven pruning or growth; the
weak-weight prune stays); `C2` `ETA_SCALING` and `SCALING_CLIP` divided by 10 (0.01, 0.01);
`C3` both. The 8.17 mode is off everywhere.
**Arms per condition, deep copies at 122,000 after a common idle from 120,000:** `on` (A at
122,000 for 2,000 ticks, heterosynaptic write on), `off` (A, write off), `neveroff` (no A,
write off). All get the plant's sleep 140,000 to 160,000 and B 162,000 to 164,000, as T5.
The `on` arm of each condition runs on to 300,000.
**Measures (driver `tests/k819_homeostat_ablation.py`), per seed 1, 2, 3:**
- P and W as 8.18 (P = top 100 ctx E in a 50-tick A probe at 122,000 on the common engine;
  W = the condition's own `on` arm's top 16 hpc E by spikes during A).
- Probes on deep copies, write off, 50 ticks, at 125,000, 126,000, 127,000 (reported
  singly and as a mean), 140,000, 160,000, 164,000, 184,000: under full A: P spikes, ctx E
  spikes, W cells spiking, W spikes, hpc E spikes, excitatory deliveries onto W (count,
  sum); under the half cue: W cells spiking, W spikes; under B (the novel-stimulus
  control): P spikes, W cells spiking, W spikes; under no stimulus: W cells spiking.
- State at the same times: onto P the excitatory in-degree and mean weight by source and the
  inhibitory in-degree; ctx E -> W count and mean weight; the marks' contrast and
  survivors-only contrast (as 8.16) in the `on` arm; alive synapse total; which groups have
  growth latched.
- Rates: idle hpc E and ctx E Hz at 182,000 to 184,000 in every arm and at 298,000 to
  300,000 in the `on` arms; per-sweep hpc E and ctx E Hz in the `on` arms; the largest
  fraction of ctx E and of hpc E spiking in one tick after 120,000.
Validity: `C0` `off` and `neveroff` reproduce 8.18's `refoff` and `refneveroff` P spikes and
delivered weight at 125,000 and 184,000 on each seed.

**Decision rule, fixed now.** A condition is *eligible* if on all three seeds its rates are
in band (ctx E 3 to 5 Hz, hpc E 0.5 to 1.5 Hz) at both windows, no tick has more than 20 %
of ctx E or hpc E spiking, P under A in `off` is at least 0.7 of `neveroff` on the
125,000 to 127,000 mean and at least 0.85 at 184,000. The next contract takes the eligible
condition that changes least (`C1` or `C2` before `C3`); between `C1` and `C2`, the one with
the higher survivors-only contrast at 184,000 in `on`. If none is eligible the result says
which clause each misses and the next step is decided from that, not from this rule.

**Prediction.** `C1` removes the lasting loss (the wiring) but not the acute one (scaling),
so it misses the 125,000 clause and may pass 184,000. `C2` removes most of the acute weight
loss but still prunes, so it misses both. `C3` passes both suppression clauses; its risk is
the rate band, since the pair rule alone pulls weights toward its own fixed point (8.17:
hpc E at half target with no scaling). I expect `C3` eligible on rates at 184,000 and
doubtful at 300,000.

**Result (2026-10-01, branch `homeostat-ablation`, seeds 1, 2, 3, logs and JSON
`~/.cache/scratch/brainsim-abl/a_seed{1,2,3}.{log,json}`): VALID on every seed (`C0`
reproduces 8.18 exactly). No condition is eligible on all three seeds; `C3` is eligible on
seeds 1 and 2 and misses the two suppression clauses narrowly on seed 3. Both halves of the
homeostat suppress; removing both removes most of it and the plant stays in band to 300,000.**

| seeds 1 / 2 / 3 | `C0` default | `C1` no rewiring | `C2` scaling / 10 | `C3` both |
|---|---|---|---|---|
| P, presented / never, mean of 125 to 127k (bar 0.7) | 0.27 / 0.28 / 0.22 | 0.51 / 0.34 / 0.32 | 0.37 / 0.40 / 0.27 | 0.95 / 0.95 / **0.68** |
| P, presented / never, 184,000 (bar 0.85) | 0.72 / 0.57 / 0.62 | 0.95 / 0.97 / 0.90 | 1.27 / 0.45 / 0.46 | 0.89 / 0.85 / **0.77** |
| ctx E Hz at 184k -> 300k (band 3 to 5) | 3.61 -> 3.82, 3.34 -> 3.85, 3.50 -> 3.60 | 3.78 -> 3.93, 3.88 -> 3.77, 3.96 -> 3.77 | 3.12 -> 3.11, 3.07 -> **2.93**, 3.15 -> 3.09 | 3.54 -> 3.33, 3.40 -> 3.16, 3.48 -> 3.17 |
| hpc E Hz at 184k -> 300k (band 0.5 to 1.5) | 0.91 -> 0.98, 0.88 -> 0.97, 0.88 -> 0.90 | 0.95 -> 0.96, 0.98 -> 0.96, 1.02 -> 0.91 | 0.72 -> 0.78, 0.74 -> 0.78, 0.75 -> 0.84 | 0.87 -> 0.82, 0.91 -> 0.82, 0.81 -> 0.80 |
| largest fraction in one tick, ctx E / hpc E (bar 0.20) | 0.09 / 0.15 | 0.10 / 0.09 | 0.05 / 0.08 | 0.08 / 0.09 |
| survivors-only contrast in `on`, 124k -> 184k | 0.118 -> 0.026, 0.118 -> 0.004, 0.104 -> 0.002 | 0.22 -> 0.17, 0.24 -> 0.17, 0.21 -> 0.14 | (184k) 0.13, 0.16, 0.16 | 0.35 -> 0.26, 0.34 -> 0.24, 0.35 -> 0.29 |

(First contrast value is the first probe, 125,000. Tick fractions are the worst seed.)
Prediction check: `C1` misses the acute clause and passes 184,000, right. `C2` misses both,
right on the acute clause on every seed and on 184,000 on two of three; it also leaves the
band (ctx E 2.93 Hz on seed 2 at 300,000). `C3` passes both, right on seeds 1 and 2; its
rates are in band at both windows as hoped, but ctx E is falling on every seed (3.5 -> 3.2
between 184,000 and 300,000), so the band is not shown to hold beyond 300,000.

What the run adds beyond the rule.
(1) With the homeostat out of the way the written contrast is the largest and longest-lived
of any round (0.35 at the write, 0.24 to 0.29 at 184,000), but it still decays: 0.155 /
0.141 / 0.182 at 300,000. Slower, not stopped, as the second opinion warned.
(2) The readout still does not follow, and this is the main finding. In `C3` at 184,000,
W cells spiking under full A, `on` / `off` / never-presented: 8 / 7 / 9, 12 / 11 / 11,
13 / 8 / 13; half cue 0 / 0 / 2, 2 / 2 / 3, 2 / 2 / 4; under the novel stimulus B 0 or 1
everywhere (the cells are selective for A, trained or not). The excitatory weight delivered
onto W under A: `on` 1263 / 1059 / 1315, `off` 1167 / 908 / 992, never-presented 1310 /
1138 / 1350. So seeing A still costs the pathway 10 to 25 % of its drive even with the
homeostat slowed, and the heterosynaptic write, which only moves weight between a cell's
inputs, wins back about that much and no more. Nothing on this plant makes a seen stimulus
drive its cells harder than an unseen one.
(3) Why seeing A costs drive without the homeostat: the pair rule. With LTP proportional to
`a_plus (w_max - w)` and LTD to `a_minus w`, co-active inputs are pulled toward
`a_plus / (a_plus + a_minus) = 0.45 w_max`, and the plant's weights sit at 0.6 to 0.7
`w_max` (held there by scaling). On this plant, firing together weakens the synapse. The
ctx E -> W mean weight is consistent with it (`C3`, seed 1, 127,000: 1.7 in `off` against
1.9 in the never-presented twin; by 184,000 both are at 1.7, the twin having seen B by then).
(4) The probe at 300,000 is void: 300,000 is the first tick of a sleep phase. The 298,000
to 300,000 idle rates are valid.
Decision: by the rule no condition is eligible, so the rule does not choose. What the
result calls for is not a third homeostat variant but the missing piece (3) names: an
excitatory rule under which co-activity at stimulus-evoked rates potentiates. The published
candidate is the triplet rule (Pfister and Gerstner 2006), whose LTP grows with the
postsynaptic rate. The next round measures, offline on this plant's own spike trains, what
that rule would do before anything is built. `C3`'s two overrides are the homeostat setting
that round and its successor use as their base, labelled a proxy for "homeostasis is slow
in the adult" and not yet shown stable beyond 300,000.
Nothing to merge; no engine change.

### 8.20 What the published triplet rule would do on this plant's own spike trains: an offline evaluation (predeclared 2026-10-01)

Recorded here from the unmerged branch `rule-eval`; the driver is not on master.

Branch `rule-eval` from `homeostat-ablation`. A diagnostic: no engine change, no weights
touched, nothing to merge. It decides whether a triplet term is worth building and fixes
its constants by a stated criterion before any kill test sees them.

**Why.** 8.19: on this plant co-activity weakens the synapse (the pair rule's fixed point
is 0.45 `w_max`, the weights sit at 0.6 to 0.7), so nothing makes a seen stimulus drive
its cells harder. In the triplet rule of Pfister and Gerstner (2006, J Neurosci 26:9673,
equations and Tables 3 and 4 read on PMC6674434 on 2026-10-01) LTP at a postsynaptic spike
is `r1 (A2+ + A3+ o2)`, with `o2` a slow postsynaptic trace, so potentiation grows with the
postsynaptic rate; LTD at a presynaptic spike is `o1 (A2- + A3- r2)`. Minimal all-to-all
sets (A2+, A3+, A2-, A3-, tau+, tau-, tau_y): hippocampal culture 5.3e-3, 8e-3, 3.5e-3, 0,
16.8 ms, 33.7 ms, 40 ms; visual cortex 0, 6.5e-3, 7.1e-3, 0, 16.8 ms, 33.7 ms, 114 ms.
LTD-to-LTP crossing for Poisson firing, `(A2- tau- - A2+ tau+) / (A3+ tau+ tau_y)`: 5.4 Hz
and 19 Hz (my arithmetic from those tables).

**Method.** Plant: 8.19's `C3` (no rate-driven rewiring, scaling / 10), seeds 1, 2, 3,
heterosynaptic write off, 8.17 mode off. A shadow observer rides the running engine and
never writes to it: each tick it reads the deliveries (the ring bucket, before the step) and
the spikes (after), keeps its own traces, and accumulates per synapse the weight change each
rule would have made, in units of `w_max`, with weights frozen for the triplet sets
(first-order, open-loop: it ignores that potentiation would change the activity). Event
conventions are the engine's: LTD at the delivery of a presynaptic spike, LTP at the
postsynaptic spike reading the undelayed presynaptic trace, traces read before their own
increment.
- `R0` the engine's own pair rule, exactly as coded, read against the live weights.
- `R1` triplet, hippocampal-culture set, additive, amplitudes as published (fraction of
  `w_max`). `R2` triplet, visual-cortex set, the same.
Windows: `A` = the presentation of A, 122,000 to 124,000; `bg` = idle, 124,000 to 139,000.
Synapse classes, fixed at 122,000 (P and W as 8.19, W from a separate `on`-style copy that
is not the observed engine): onto W from P; onto W from other ctx E; onto W from hpc E;
onto other hpc E from ctx E; onto P from A's sense cells; onto P from other sense cells;
onto P from ctx E; onto other ctx E from ctx E.
Reported per rule, class and window: mean and the 10th / 50th / 90th percentile of the
accumulated change, per presentation for `A` and per second for `bg`; the postsynaptic and
presynaptic mean rates of each class in each window; for the triplet sets the mean of `o2`
at postsynaptic spikes.
Validity: over ticks 122,001 to 122,999 (no sweep inside) `R0`'s accumulated change equals
the engine's actual weight change on every alive excitatory synapse onto ctx and hpc cells
to 1e-4 `w_max`.

**Decision rule, fixed now.** For a triplet set and a scale `k` (one number multiplying all
its amplitudes), define on each seed: `gain` = mean `A`-window change of P -> W and of
A-sense -> P at scale `k`; `drift` = the largest absolute `bg` change per second over the
eight classes at scale `k`; `sel` = `gain` over the mean `A`-window change of the other
inputs to the same cells (other ctx E -> W; other sense -> P). Choose `k` so that the
smaller of the two gains, on the worst seed, is +0.10 `w_max` per presentation. The set is
*worth building* if at that `k`, on all three seeds, both gains are positive, `drift` is at
most 0.003 per second (a third of what the slowed scaling can move in a second), and `sel`
is at least 2 on both pathways, or the other inputs' change is not positive. If both sets
qualify, take the one with the smaller `drift`. If neither does, the result says which
clause fails and the triplet term is not built in this form.

**Prediction.** `R0` shows the A-window change of P -> W negative (the 8.19 reading). The
hippocampal set's crossing at 5.4 Hz sits between this plant's background (ctx 4 Hz, hpc
1 Hz) and its evoked rates, so I expect a positive gain at published amplitude but a small
one (order 1e-3 to 1e-2), needing `k` of 10 to 100, and I expect the drift clause to be the
one at risk in cortex, whose background rate is close to the crossing. The visual-cortex
set's 19 Hz crossing is above most evoked rates here; I expect it to fail on gain sign.

**Result (2026-10-01, branch `rule-eval`, seeds 1, 2, 3, logs and JSON
`~/.cache/scratch/brainsim-rule/r_seed{1,2,3}.{log,json}`): VALID on every seed (the shadow
pair rule matches the engine's actual weight change to 4e-7 `w_max` on 243,000 to 313,000
synapses). By the predeclared rule neither set is worth building as a stand-alone selective
write: the visual-cortex set fails on the sign of the gain, the hippocampal set passes gain
and drift and fails the selectivity clause on the hippocampal pathway on seeds 2 and 3.**

Mean change over one 2 s presentation of A, in `w_max`, seeds 1 / 2 / 3:

| class | `R0` the plant's pair rule | `R1` triplet, hippocampal set, as published | `R2` triplet, visual set |
|---|---|---|---|
| P -> W | -0.057 / -0.102 / -0.113 | +0.0060 / +0.0107 / +0.0062 | -0.030 / -0.035 / -0.032 |
| other ctx E -> W | -0.041 / -0.069 / -0.066 | +0.0026 / +0.0065 / +0.0048 | negative |
| hpc E -> W | -0.014 / +0.002 / -0.001 | +0.0003 / +0.0008 / +0.0007 | |
| ctx E -> other hpc E | -0.011 / -0.011 / -0.013 | +0.0004 / +0.0005 / +0.0005 | |
| A's sense cells -> P | -0.076 / -0.136 / -0.109 | +0.029 / +0.041 / +0.034 | -0.051 / -0.036 / -0.044 |
| other sense -> P | -0.013 / -0.019 / -0.017 | +0.0036 / +0.0031 / +0.0039 | negative |
| ctx E -> P | -0.025 / -0.052 / -0.037 | +0.009 / +0.017 / +0.010 | |
| ctx E -> other ctx E | -0.011 / -0.016 / -0.014 | +0.0021 / +0.0028 / +0.0025 | |

- `R0` confirms 8.19's reading by direct measurement: one presentation weakens the driven
  pathway by 6 to 14 % of `w_max` (P -> W, A-sense -> P), more than any other class, and the
  pair rule's background drift is -0.0014 to -0.0031 per second on cortical synapses.
- `R1`: every gain is positive on every seed. Rates in the A window: P 12 to 14 Hz, A's
  sense cells 24 Hz, W 5.8 to 8.1 Hz, other hpc E 1.4 to 1.7 Hz; `o2` at postsynaptic spikes
  0.15 to 0.21 on W, 0.44 to 0.50 on P. Scale for +0.10 on the smaller gain: 16.5 / 9.3 /
  16.1, so `k` = 16.5 (worst seed). At `k` the background drift is 0.0013 / 0.0020 / 0.0017
  per second (bar 0.003), passing. Selectivity: A-sense -> P against other sense -> P is
  8.0 / 13.3 / 8.6 (bar 2), passing; P -> W against other ctx E -> W is 2.3 / **1.6** /
  **1.3**, failing on two seeds.
- `R2`: negative gains on both pathways on every seed (its crossing at 19 Hz is above this
  plant's evoked rates), as predicted.
Prediction check: `R0` negative, right. `R1` positive and small at published amplitude,
`k` of 10 to 100, right; the clause at risk was predicted to be cortical drift, wrong: the
drift passes and the failing clause is hippocampal selectivity. `R2` fails on sign, right.

Reading. The selectivity clause fails for a reason the measurement makes plain: during A
the rest of the cortex is not quiet (other ctx E inputs to W fire at 9 to 11 Hz against P's
13 to 16 Hz), and a Hebbian rule potentiates every input in proportion to its own activity.
The triplet rule is selective for *which cells* potentiate (W gains 15 times what other hpc
E cells gain) and only weakly for *which of their inputs*. Choosing among a cell's inputs is
what the heterosynaptic write (8.16, on master) already does, and the published recipe
(Zenke, Agnes and Gerstner 2015) uses exactly that pair: a triplet term for potentiation
and a heterosynaptic term for competition. So the rule's verdict stands, the triplet term
is not built as a selective write on its own, and the next contract builds it as the
potentiation source beside the existing heterosynaptic write, with a kill test that
measures the trained cells' answer to the trained stimulus against an untrained twin and
against another stimulus.
One number the single-scale rule hides: at `k` = 16.5 the cortical pathway would gain 0.47
to 0.68 `w_max` per presentation (A-sense -> P), which saturates it. The plant already
makes the hippocampus a five times faster learner than the cortex (`a_plus` 0.05 against
0.01); the next contract keeps that ratio (`k` 16.5 on `hpc`, 3.3 on `ctx`, giving A-sense
-> P +0.09 to +0.14) and says so as its own choice.
Nothing to merge; no engine change.

### 8.21 Triplet potentiation beside the heterosynaptic write, on the slowed homeostat (predeclared 2026-10-01)

Branch `triplet` from master b750638. A spike: nothing merges unless it passes. K1.1's bar
is untouched; K1.1 is run under this plant only if T6 passes.

**Why, from the measurements.** 8.18: the homeostat suppresses a seen stimulus within
seconds. 8.19: with rate-driven rewiring off and scaling ten times slower the suppression
mostly goes and the plant stays in band to 300,000, but trained cells answer no more than
untrained ones. 8.20: the plant's pair rule weakens the driven pathway by 6 to 14 % of
`w_max` per presentation; the hippocampal triplet set of Pfister and Gerstner (2006) would
strengthen it on every seed, selectively for the driven cells, with safe background drift.

**Hypothesis.** With the triplet rule as the excitatory rule, the heterosynaptic write for
competition among a cell's inputs and the slowed homeostat, a stimulus seen once drives its
hippocampal cells harder than it drives the same cells in a twin that never saw it, the
gain is specific to that stimulus, and the plant stays in its rate bands.

**Mechanism (engine, one labelled mode, flag `params.TRIPLET_STDP = False` /
`Engine.triplet_stdp`, off path bit-identical to master).** While on, on every alive
excitatory synapse whose postsynaptic cell is in a region with `a_plus > 0` (`ctx`, `hpc`),
the pair rule's two updates are replaced by the minimal all-to-all triplet rule, hippocampal
culture set (Pfister and Gerstner 2006, Table 4: A2+ 5.3e-3, A3+ 8e-3, A2- 3.5e-3, A3- 0,
tau+ 16.8 ms, tau- 33.7 ms, tau_y 40 ms), additive, hard bounds `[0, w_max_n[post]]`:
- three new per-neuron traces `r1` (decay tau+), `o1` (tau-), `o2` (tau_y), each +1 at the
  cell's own spike, decayed every tick where the engine decays `x_pre` / `y_post`;
- at the delivery of a presynaptic spike: `w -= g * K * A2- * o1[post] * w_max_n[post]`,
  `o1` read before this tick's decay (the engine's own order for `y_post`);
- at a postsynaptic spike: `w += g * K * r1[pre] * (A2+ + A3+ * o2[post]) * w_max_n[post]`,
  `r1` and `o2` read after this tick's decay and before this tick's increment;
- `g` is the engine's plasticity gate (1 awake, 0.3 asleep); no RNG; no synapse is created
  or killed by the rule (the weak-weight prune still removes what falls under its line).
- `K` per postsynaptic region, `TRIPLET_K = {"hpc": 16.5, "ctx": 3.3}`. The hpc value is
  8.20's measured scale (the worst seed's scale for +0.10 `w_max` on P -> W in one
  presentation); the ctx value keeps the plant's existing ratio of five between the two
  regions' learning amplitudes (`a_plus` 0.05 against 0.01) and is **my choice**: 8.20's
  single scale would move the cortical input pathway by half of `w_max` in one presentation.
  Neither is searched.
- Untouched: the heterosynaptic write, scaling, structural rules, sleep, inhibitory
  synapses, `sense`. The existing traces `x_pre` / `y_post` keep running (other code reads
  them). Pure maths in `brainsim/triplet.py`. `Engine.triplet_view()` for drivers (flag, the
  constants, mean `o2`). No worker command, frame key or UI on the branch.
**Homeostat for the experiment (parameters only, per engine, as 8.19's `C3`):**
`STRUCT_BASE = 0`, `ETA_SCALING = 0.01`, `SCALING_CLIP = 0.01`. A labelled proxy for "the
adult homeostat is slow"; 8.19 did not show it stable beyond 300,000 and this test runs it
to 440,000.

**Kill test T6 (`tests/k821_triplet.py`), numbers fixed now.** Per seed 1, 2, 3: warm the
default plant to 120,000; apply the homeostat overrides; fork: `pair` lineage (triplet off)
and `tri` lineage (triplet on from 120,000). Idle to 122,000. Arms, deep copies:
`on` (tri; A at 122,000 for 2,000 ticks, heterosynaptic write on), `nowrite` (tri; A, write
off), `never` (tri; no A, write on), `pair_on` (pair; A, write on: 8.19's `C3` `on`, the
same-seed control). All: the plant's sleep 140,000 to 160,000, B at 162,000 for 2,000
ticks. `on` and `never` run to 440,000. W = the `on` arm's top 16 hpc E by spikes during A;
every arm is read on that W. Readouts are deep copies with the write off, 50 ticks, at five
times 1,000 apart, their mean taken: the *early* set 180,000 to 184,000 (all arms), the
*late* set 434,000 to 438,000 (`on`, `never`). Each readout: W spikes and excitatory weight
delivered onto W under full A; W spikes under the half cue; W spikes under B.
Required on each of seeds 1, 2 and 3:
- V1 control: `pair_on` at 184,000 reproduces 8.19's `C3` `on` (W cells spiking under full
  A and the survivors-only contrast: seed 1 8 and 0.258, seed 2 12 and 0.239, seed 3 13 and
  0.293, as recorded in `a_seed{1,2,3}.json`);
- V2 rates: `on` idle at 182,000 to 184,000, 298,000 to 300,000 and 438,000 to 440,000:
  hpc E in [0.5, 1.5] Hz and ctx E in [3.0, 5.0] Hz; no tick after 120,000 with more than
  20 % of ctx E or of hpc E spiking, in any arm;
- V3 no saturation: in `on` at 184,000 and 440,000 at most 20 % of the alive excitatory
  synapses onto ctx E, and at most 20 % of those onto hpc E, are at or above 0.98 `w_max`,
  and at most 20 % of each have died since 122,000;
- c1 the trained stimulus drives its cells harder: early set, mean excitatory weight
  delivered onto W under full A: `on` >= 1.20 x `never`; and mean W spikes under full A:
  `on` >= 1.20 x `never` (8.19 `C3`, single readout: 0.96 / 0.93 / 0.97 on delivered weight);
- c2 the gain is for that stimulus: early set, with `S = A / (A + B)` on mean W spikes,
  `S(on) >= S(never) - 0.05`, and mean W spikes under B: `on` <= 1.20 x `never` + 1;
- c3 it lasts: late set, mean excitatory weight delivered onto W under full A:
  `on` >= 1.10 x `never`.
Any miss is REJECTED with the clause and the seed named. Reported without a bar: the half
cue in every arm and set (the pattern-completion readout K1.1 judges), `nowrite` against
`on` (what the heterosynaptic write adds under the triplet rule), `pair_on` against `on`,
the marks' contrast over time, mean weight and saturated fraction per projection, P's
answer to A (as 8.19), hpc E and ctx E Hz per sweep, the mean `o2`.

**Prediction, written before the run.** V1 holds (it is a rerun). The risk is V2 and V3 in
cortex: the triplet rule's background drift is upward (8.20: +0.00002 to +0.0001 per second
at published amplitude, three times that at `K` 3.3), the only brake is scaling at a tenth
of its old gain, and potentiated cortical cells answering A harder is a positive feedback
that B and the sleeps will exercise. If cortex holds, c1 passes on delivered weight (the
measured +0.10 on P -> W is about a sixth of those weights) and is doubtful on spikes,
which are few. c2 passes. c3 is the open question: nothing here protects the gain except
that the slowed homeostat no longer attacks it. The half cue stays near baseline: the
recurrent pathway gains almost nothing (8.20: hpc E -> W +0.0003 to +0.0008 before scaling).

**Result (2026-10-01, branch `triplet` at the implementation commit, one run per seed, logs
and JSON `~/.cache/scratch/brainsim-tri/t6_seed{1,2,3}.{log,json}`): REJECTED on every seed:
V3 (saturation) and c1 (delivered weight) on seeds 1, 2 and 3, c3 on seed 3. V1, V2 and c2
pass on every seed. It is the first plant on which the trained cells out-fire the untrained
twin on all three seeds, and it holds its rate bands to 440,000; the gain is too small, too
unspecific and the weights pile up at the bound.**

| clause | seed 1 | seed 2 | seed 3 |
|---|---|---|---|
| V1 `pair_on` reproduces 8.19 `C3` `on` | 8, 0.258: yes | 12, 0.239: yes | 13, 0.293: yes |
| V2 hpc E Hz at 184k / 300k / 440k | 0.66 / 0.87 / 0.89 | 0.85 / 0.93 / 0.91 | 0.85 / 0.94 / 0.95 |
| V2 ctx E Hz at 184k / 300k / 440k | 3.21 / 3.56 / 3.61 | 3.49 / 3.46 / 3.47 | 3.46 / 3.53 / 3.62 |
| V2 largest fraction in one tick, ctx E / hpc E | 0.09 / 0.08 | 0.06 / 0.08 | 0.05 / 0.03 |
| V3 at or above 0.98 `w_max`, onto ctx E, 184k / 440k (bar 0.20) | 0.16 / **0.29** | **0.28** / **0.38** | **0.24** / **0.35** |
| V3 the same onto hpc E | **0.24** / **0.25** | 0.15 / 0.19 | 0.17 / 0.20 |
| V3 died since 122,000, worst of the two, 440k (bar 0.20) | 0.07 | 0.15 | 0.13 |
| c1 delivered onto W under A, `on` / `never` (bar 1.20) | **1.04** | **1.14** | **1.07** |
| c1 W spikes under A, `on` / `never` (bar 1.20) | 1.26 (4.8 / 3.8) | 1.27 (11.4 / 9.0) | 1.30 (21.0 / 16.2) |
| c2 W spikes under B, `on` / `never` | 1.2 / 1.4 | 1.2 / 1.0 | 0.8 / 1.6 |
| c3 late, delivered onto W under A, `on` / `never` (bar 1.10) | 1.33 | 1.15 | **1.02** |

Reported without a bar (early set, seeds 1 / 2 / 3): half cue, W spikes, `on` against
`never`: 1.2 / 1.6, 1.8 / 2.0, 4.2 / 4.2 (no pattern completion). The heterosynaptic write
under the triplet rule, delivered weight `on` against `nowrite`: 861 / 804, 1214 / 997,
1668 / 1633. The pair-rule plant read on the same cells (`pair_on`): 724, 830, 1072, below
every triplet arm including the never-trained one (829, 1064, 1566): under the triplet rule
the whole pathway carries more. Late against early in the never-trained arm: 829 -> 1298,
1064 -> 1163, 1566 -> 1713: the drive rises with time whether or not A was seen.
Prediction check: V1 holds, right. V2 was the declared risk and it holds, with rates
steadier than the pair-rule plant's (ctx E 3.2 to 3.6 Hz and not falling); V3 fails as
feared, in cortex most. c1 was predicted to pass on delivered weight and be doubtful on
spikes: backwards, the spikes clause passes on every seed and the delivered weight fails.
c2 passes, right. c3 was the open question: two seeds pass, one fails. Half cue at
baseline, right.

Reading. (1) The additive rule with hard bounds drives the synapses that carry correlated
activity to the bound and scaling pulls the rest down; a quarter to a third of the cortical
excitatory synapses sit at the bound by 440,000 and the share is still rising. That is the
known behaviour of additive STDP (Song, Miller and Abbott 2000) and it is why the gain is
unspecific: ongoing activity and B potentiate the same pathways A did, in the trained and
the untrained arm alike, so the difference between them is a few per cent of a total that
is climbing. (2) What the rule adds is real and has the right sign for the first time, and
the plant is stable under it; what is missing is a potentiation that stays where the
stimulus put it. (3) Reviews: security clean; architecture, the rule, scope, order, off
path and the T6 clauses match the contract, with merge notes (assert every plastic region
has a `K`; reset the cached `K` vector and the traces when the flag or the parameters
change; keep the constants in one place; fold the copied test helpers into one module). The
review also notes excitatory synapses onto inhibitory cells are in scope, as the contract's
wording has it.
K1.1 not run. Not merged. The constants are not to be tuned on this branch.

### 8.22 Readouts with learning frozen, and an offline screen of two further published rules (predeclared 2026-10-01)

Branch `rule-screen` from `triplet` fb9bade. A diagnostic: no engine change, nothing merges.
K1.1's bar is not lowered. Two corrections come first, both from an outside read of 8.21
(Codex, `~/.cache/scratch/brainsim-next/codex_821.md`, each checked against the source):

- The T6 readout copies switched the heterosynaptic write off but left the triplet rule on.
  At `K` 16.5 one pairing moves a hippocampal synapse by up to 0.09 `w_max`, so the weights
  changed inside the 50-tick readout itself, in every arm. Part A measures how much of the
  8.21 spike gain is in the weights.
- The 8.20 decision rule bounded the baseline drift at 0.003 `w_max` per second. Over the 62
  seconds between the presentation and the readout that allows 0.19 `w_max`, twice the gain
  it asked for (0.10). The bar was mine and it was too loose; T6 then showed the projections'
  mean weight rise by about 0.18 `w_max` in those 62 seconds in the trained and the
  never-trained arm alike. Part B replaces it with bars read at the readout time.

Noted, not changed: the rule applies depression when the presynaptic spike arrives (after
the axonal delay) and potentiation from a presynaptic trace started at the soma (no delay).
The plant's pair rule has had the same convention since Stage 0 and the 8.21 contract kept
it; the published rule has no delay, so this is a difference from it.

**Part A, T6 read again with learning frozen (driver `tests/k822_frozen_readout.py`).** The
T6 plant and schedule unchanged (8.21: C3 homeostat from 120,000, triplet rule and
heterosynaptic write on, A at 122,000 for 2,000 ticks, sleep 140,000 to 160,000, B at
162,000), arms `on` and `never`, seeds 1, 2, 3, run to 184,000 only. At each early readout
time (180,000 to 184,000, five times) two readouts are taken from separate deep copies:
the T6 readout as recorded, and a frozen one in which no weight can change (triplet scale
zero for every cell, heterosynaptic write off; the driver asserts the copy's weights are
bit-identical before and after). Frozen readouts are taken at 50 and at 200 ticks, for full
A, the half cue and B.
Validity: the unfrozen rows reproduce the T6 early rows of the same seed exactly.
Reading rule, fixed now: if the frozen W spikes under A, `on` / `never`, are at least 1.20 on
every seed, the 8.21 gain stands as a property of the weights; if not, it was made inside
the readout and the 8.21 reading is corrected. No other bar.

**Part B, offline screen (driver `tests/k822_rule_screen.py`, pure rule functions in
`tests/k822_rules.py` with their own tests written first by a different worker).** The 8.20
method: a shadow observer rides an engine it never writes to and accumulates, per synapse,
what each candidate rule would have done. The engine observed is the pair-rule plant on the
C3 homeostat (the plant a new rule would be installed on), heterosynaptic write off, A at
122,000 for 2,000 ticks, then left alone through the sleep and B at 162,000 to 184,000.
Seeds 1, 2, 3. W, P and the synapse classes as 8.20, plus one class, P onto hippocampal E
cells outside W. Snapshots at 124,000 (end of A), 140,000, 160,000, 184,000.
Validity as 8.20: the shadow's copy of the engine's own rule reproduces the engine's weight
change over the first sweep-free stretch to 1e-4 `w_max`.

Rules screened, each on its published form:

- `R1`, reference: the triplet rule as built in 8.21 (additive, `K` hpc 16.5, ctx 3.3).
- `R3`, the triplet rule with a sliding depression threshold (the Bienenstock, Cooper and
  Munro 1982 threshold in the form Pfister and Gerstner 2006 give for their rule and Zenke,
  Hennequin and Gerstner 2013 show a network needs: the depression amplitude is multiplied
  by the square of the postsynaptic cell's running mean rate over a reference rate). Same
  `K`. Running mean rate: a low-pass of the cell's spikes with a 10 s time constant (Zenke
  2013 find the detector must be seconds to tens of seconds for stability; 10 s is my
  choice, not searched). An offline screen cannot close the loop, so the converged state is
  emulated and labelled as such: for each postsynaptic cell the depression multiplier is
  `c_j * (rate_j(t) / base_j)^2`, `base_j` the cell's running rate at 122,000, and `c_j` the
  constant that makes the cell's summed change over a baseline stretch (112,000 to 122,000,
  no stimulus) zero. Cells with no depression or no potentiation in that stretch keep
  `c_j` = 1 and are counted.
- `R4`, the calcium-threshold rule of Graupner and Brunel 2012, hippocampal slice parameter
  set as published: calcium time constant 48.8373 ms, presynaptic delay 18.8008 ms (19
  ticks), `C_pre` 1, `C_post` 0.275865, thresholds 1 (depression) and 1.3 (potentiation),
  rates `gamma_d` 313.0965 and `gamma_p` 1645.59, `tau` 688.355 s, `rho_star` 0.5. The
  efficacy variable `rho` in [0, 1] is read as the weight in units of `w_max` and starts at
  the plant's weight at 122,000. The noise term is left out (a deterministic screen; said
  here because the published rule has it). No scale factor.

Amendment before any full run (2026-10-01): the harness smoke run showed the `R3` emulation
is ill-conditioned for a cell whose running rate at 122,000 is close to zero (the squared
ratio explodes at its next spike). `base_j` is floored at one spike per filter time constant
(0.1 Hz), the lowest rate the detector can resolve; the number of floored cells is printed.
The drift classes are the two that involve neither P nor W: other cortical E onto
hippocampal E outside W, and other cortical E onto cortical E outside P.

Measures, per seed, in units of `w_max`, cumulative from 122,000 and read at 184,000 unless
said: `spec` = mean change of P onto W minus mean change of other cortical E onto W;
`drift` = the largest absolute mean change among the classes that involve neither P nor W;
`kept` = `spec` at 184,000 over `spec` at 124,000. Reported without a bar: every class at
every snapshot, P onto hippocampal cells outside W (whether the rule writes onto the cells
that fired or onto every cell P reaches), the fraction of class synapses that would sit at a
bound, and for `R3` the distribution of `c_j`.

Decision rule, fixed now. A rule qualifies if on every seed `spec` >= 0.10, `drift` <= 0.05
and `kept` >= 0.5. If one qualifies the next contract builds it in the engine (tests first,
flag off by default, kill test with on / never arms and frozen readouts). If both do, the
one with the larger smallest `spec`. If neither does, nothing is built from this screen and
the next contract starts from the measured budget: which window (A, wake, sleep, B) takes
the specific gain away, and whether a gate on plasticity (a neuromodulatory third factor,
which needs a source the network itself computes) or a quieter hippocampal baseline is the
missing piece. `R1` is the reference and is expected to fail `drift`.

Predictions, written before the run. Part A: the frozen ratio is lower than 1.26 to 1.30
but still above 1 on every seed; whether it clears 1.20 I do not know. Part B: `R1` fails
`drift` (0.1 to 0.2). `R3` passes `drift` on hippocampal cells by construction but fails
`spec`: a rule whose sign is set by the postsynaptic cell changes all of that cell's inputs
in the same direction, in proportion to their presynaptic rates, so its selectivity among a
cell's inputs is the presynaptic rate ratio (measured 1.3 to 2.3 in 8.20). `R4` is the open
one: its potentiation threshold is crossed by presynaptic spikes that come close together,
so inputs firing at 12 to 20 Hz should gain much more than inputs at 3.5 Hz; I expect it to
write P onto every hippocampal cell P reaches rather than onto W only, and I do not know
whether its drift at the cortical baseline rate stays inside the bar.

Standing exclusions unchanged: no teacher current, no change to the K1.1 bar, no constant
tuned after the run.

**Result (2026-10-01, branch `rule-screen` at 3d565aa, one run per seed, logs and JSON
`~/.cache/scratch/brainsim-next/k822_seed{1,2,3}.*` and `screen822_s{1,2,3}.*`): both parts
VALID on every seed. Part A: the 8.21 spike gain STANDS with learning frozen. Part B: no rule
qualifies, so nothing is built from this screen. The budget shows why: the gain is never
specific at the moment it is written, because the stimulus drives the whole cortex.**

Part A (seeds 1 / 2 / 3; the unfrozen rows reproduce the T6 early rows exactly):

| frozen readout, `on` / `never` | seed 1 | seed 2 | seed 3 |
|---|---|---|---|
| W spikes under A, 50 ticks (reading rule, 1.20) | 1.26 (4.8 / 3.8) | 1.29 (10.8 / 8.4) | 1.30 (20.0 / 15.4) |
| W spikes under A, 200 ticks | 1.12 | 1.35 | 1.10 |
| delivered weight onto W under A, 50 ticks | 1.03 | 1.12 | 1.06 |
| delivered weight, 200 ticks | 0.98 | 1.04 | 0.98 |
| half cue, W cells, 50 ticks, `on` against `never` | 1.2 / 1.6 | 1.6 / 2.0 | 3.8 / 3.8 |
| half cue, W cells, 200 ticks | 3.6 / 4.4 | 7.0 / 8.0 | 10.2 / 9.8 |

By the reading rule the gain is a property of the weights, not of the readout. It is small:
single readouts of the same arm range from 1 to 7 spikes on seed 1, the 200-tick ratio is
1.1 on two seeds, and the delivered weight is within a few per cent of the twin's. Prediction
(lower than 8.21 but above 1): the 50-tick ratio did not fall at all.

Part B (validity: the shadow's copy of the pair rule within 4e-7 `w_max` on every seed; W
matches the T6 pair arm's own W on every seed; the `R3` floor touched no cell):

| | seed 1 | seed 2 | seed 3 |
|---|---|---|---|
| `R1` `spec` at 124,000 / 184,000 (bar 0.10 at 184,000) | 0.057 / 0.073 | 0.070 / 0.069 | 0.023 / 0.029 |
| `R1` `drift` (bar 0.05) | 0.058 | 0.083 | 0.079 |
| `R1` `kept` (bar 0.5) | 1.29 | 0.99 | 1.23 |
| `R3` `spec` at 184,000 | -0.21 | -0.26 | -0.19 |
| `R3` `drift` | 0.16 | 0.44 | 0.24 |
| `R4` `spec` at 124,000 / 184,000 | 0.023 / 0.007 | 0.007 / -0.004 | -0.024 / -0.049 |
| `R4` `drift` | 0.083 | 0.177 | 0.162 |
| rates during A, Hz: P / other cortical E / W / other hpc E | 12.0 / 6.5 / 5.8 / 1.4 | 13.8 / 6.3 / 8.1 / 1.7 | 12.2 / 6.0 / 6.4 / 1.7 |
| rates in the wake after A, Hz: P / other cortical E | 3.8 / 3.8 | 3.4 / 3.9 | 3.6 / 3.8 |

`R1` (the reference): P onto W gains 0.10 / 0.18 / 0.10 during A and other cortical cells
onto W gain 0.04 / 0.11 / 0.08; nothing afterwards takes the difference away (`kept` about
1), and the drift classes rise 0.06 to 0.08 over the 62 seconds, so it fails `spec` and
`drift` as 8.21 did in closed loop. `R3`: the 10 s rate detector rises during the 2 s
presentation and turns the write into a depression (P onto W -0.71 on seed 1, more than
other inputs); it fails everything, and the emulated balance does not hold outside the
baseline stretch. `R4`: about +0.04 / +0.01 / -0.03 on P onto W during A and a steady
depression of every class at the cortical baseline rate afterwards (-0.07 to -0.18 over 62
seconds); nothing sits at a bound; it fails everything. It does not write onto W only: P
onto hippocampal cells outside W moves like every other class.
Prediction check: `R1` fails `drift`, right (smaller than predicted, 0.06 to 0.08). `R3`
fails `spec`, right, but it does not pass `drift` either, wrong. `R4`, the open one: fails;
its drift is outside the bar and its write under A is no larger than the triplet rule's.

Reading. The budget question the decision rule asked (which window takes the specific gain
away) has the answer "none": the gain is not specific when it is made. During A the cortical
cells outside P fire at 6.0 to 6.5 Hz against 3.8 at rest, and P, the 100 most responsive
cells, at 12 to 14 Hz: the stimulus raises the whole cortex and its best cells stand only
twice above the rest. A rule that reads presynaptic and postsynaptic activity at one synapse
cannot separate inputs better than their rates differ, so every rule screened here, and the
pair and triplet rules before them, is bounded near that factor of two (8.20 measured 1.3 to
2.3). Round 29 had already counted the cause: a 40-cell sensory patch reaches 1,113 of the
1,600 cortical E cells, and half of it reaches 93 % of those. The cortical code for a
stimulus is dense and stimuli overlap almost entirely, so the missing piece is upstream of
the learning rule: how selectively a stimulus is represented before the hippocampus sees it.
The next contract measures that directly (how separate the cortical and hippocampal
responses to A and to B are) before any wiring is changed. No gate and no rule is built
from this screen. K1.1 not run. Not merged.

## 9. Files created in Stage 0

```
SPEC.md                    this file
requirements.txt           numpy, fastapi, uvicorn[standard], pytest
run.py                     starts the server on localhost:8000
brainsim/__init__.py
brainsim/params.py         every constant, region table, projection table, schedules, seed
brainsim/net.py            SoA arrays, immature wiring, CSR rebuild, grow/prune primitives
brainsim/engine.py         tick loop, ring buffer, STDP, slow sweep, sleep state machine, injection, encode-mode schedule (8.12)
brainsim/encode.py         encode-mode pure helpers: hpc/ctx E ids, half cue, winner selection, identification pass, the two one-shot co-fire writes (8.12)
brainsim/telemetry.py      frame assembly, inspect/region/layout queries
brainsim/worker.py         subprocess loop, queues, pacing
server/app.py              FastAPI static + /ws
ui/index.html  ui/app.js  ui/style.css  ui/evidence.js (pure client evidence state, node-testable)
ui/stage0_results.json     hand-maintained recorded results (test, outcome, commit, date, evidence)
mockups/index.html         approved UI mockup with a scripted demo feed (design record; not served)
tests/test_rules.py        K0.3 two-neuron STDP (the Stage 0 claim), K0.3 population (retired kill test, record only, `--record`), K0.13 baseline, structural primitives
tests/k03_pairing.py       K0.3 population protocol record (weak-current pairing; imposed pulses reachable by override), instrument and report; optional run, not a Stage 0 kill test (test-side; engine untouched)
tests/k03_brief_volley.py  brief-volley diagnostic alongside K0.3 (test-side; reuses the instrument; not a kill test)
tests/k013_onset.py        K0.13 baseline: autonomous onset learning, three arms and probes (test-side; engine untouched)
tests/test_k03_instrument.py  pins the instrument generalisation: zero pulses inject nothing, default path numerically unchanged
tests/test_kill_stage0.py  K0.1, K0.2, K0.4, K0.5, K0.6
tests/test_ui_truth.py     frame keys vs app.js/evidence.js, frame fields vs engine attributes
tests/test_stim_bookkeeping.py  stimulus records, events, stimlog bound (observation only)
tests/test_engine_determinism.py digest pinned at 3060f23: equivalence with the pre-instrumentation engine for the tested schedule
tests/test_session_commands.py  worker Session: results, step FIFO, sleep ack, layout burst
tests/test_server_clients.py    per-socket client_id, req prefixing, malformed payloads
tests/test_results_record.py    stage0_results.json schema and test-node existence
tests/test_client_evidence.py + tests/js/evidence.test.mjs  client evidence rules (node --test)
tests/conftest.py          markers kill / record (deselected unless --record) / s1 (Stage 1 runs, minutes)
tests/k11_binding.py       K1.1 hpc binding / pattern completion driver (SPEC 8.2; `--encode-mode`, SPEC 8.12; the 8.3 to 8.11 mode flags stay on their branches); test-side
tests/test_k11_binding.py  K1.1 pins and the s1 wrapper (red: recorded FAIL, SPEC 8.2)
tests/test_k11_ltp_only.py K1.1 rerun, hpc-afferent LTP-only-during-encode proxy (SPEC 8.4; branch k11-ltp-only, unmerged): driver-mode pins and the s1 wrapper
tests/test_k11_encode_window.py K1.1 rerun, hpc encode window proxy (SPEC 8.5; branch k11-encode-window, unmerged): Engine.encode_mask exemptions, driver-mode pins and the s1 wrapper
tests/test_k11_sparse_write.py K1.1 rerun, sparse co-fire write proxy on top of the encode window (SPEC 8.6; branch k11-sparse-write, unmerged): winner selection, the write on a hand-built net, driver-mode and the s1 wrapper
tests/test_k11_recurrent_write.py K1.1 rerun, W recurrent co-fire proxy on top of 8.5 and 8.6 (SPEC 8.7; branch k11-recurrent-write, unmerged): the W->W write on a hand-built net, driver mode and the s1 wrapper
tests/test_k11_restricted_donors.py K1.1 rerun, restricted donors proxy on the selective parent (SPEC 8.8; branch k11-restricted-donors, unmerged): the top-k donor rule on a hand-built net, driver mode and the s1 wrapper
tests/test_k11_window_on_w.py K1.1 rerun, encode window on W only with the identification pass (SPEC 8.9; branch k11-window-on-w, unmerged): ids on the window, the ID pass's no-side-effect contract, W on the write, the W pins, driver mode and the s1 wrapper
tests/test_k11_small_ww.py K1.1 rerun, small W->W proxy on the 8.9 plant (SPEC 8.10; branch k11-small-ww, unmerged): the recurrent helper and its W boundary on a hand-built net, guard chain, flag, inert-when-off, the s1 wrapper
tests/test_k11_grace.py K1.1 rerun, post-write grace on W proxy on the 8.10 plant (SPEC 8.11; branch k11-grace, unmerged): the grace context manager, the delay/cue pin rules, snapshot_at, guard chain, flag, the s1 wrapper
brainsim/encode.py         encode-mode pure helpers: hpc/ctx E ids, half cue, winner selection, identification pass, the two one-shot co-fire writes (SPEC 8.12; on master since the 8.16 merge, mode off by default)
tests/test_encode_mode.py  encode-mode: params, engine schedule, brainsim/encode.py, frame/config/layout keys, the worker command, UI source (SPEC 8.12)
tests/test_k11_encode_mode.py  K1.1 rerun under encode-mode: driver signature, flag, pins, and the s1 replay wrapper pinned to the 8.11 numbers (SPEC 8.12)
tests/k815_selective_write.py  selective-write contrast fixture T3: selective / uniform / sham arms, identity-tracked contrast (SPEC 8.15; diagnostic driver, engine untouched)
tests/k815_slot_reuse.py   slot-reuse counter: reused slots and stale queued events per sweep (SPEC 8.15; diagnostic)
tests/k11_never_trained.py never-trained half-cue control for the K1.1 readout (SPEC 8.15; diagnostic driver)
tests/test_selective_fixture.py  pins for the 8.15 fixture helpers and the never-trained control
brainsim/hetero.py         heterosynaptic write pure helpers: constants with defaults, the per-cell redistribution (SPEC 8.16)
tests/k816_hetero_write.py kill test T4 for the heterosynaptic write: on / off / never arms, marks, contrast retention, readout with the never-trained arm (SPEC 8.16)
tests/test_hetero_write.py heterosynaptic write: params, the sweep rule, record and stats, frame/config keys, the worker command and its exclusion with encode-mode, UI source (SPEC 8.16)
ui/stage1_results.json     hand-maintained record of Stage 1 candidates and tests (rejected ones stay on unmerged branches)
tests/js/ui_helpers.test.mjs  pure client helpers (record chips, failures-first, stable key order, partial gating)
tools/sync_serve.sh        post-commit hook: the served worktree follows master when only ui/ and tests changed
pytest.ini                 pythonpath = .
```

Nothing else. No README, no config framework, no database, no save/load until a stage needs it.

## 10. Stage 0 API contract (tests and implementation build against this)

Python 3.12 venv at `.venv/`; run everything as `.venv/bin/python` / `.venv/bin/pytest`.
Tick = 1 ms sim time. All ids are int32 indices into the neuron arrays. All public array
attributes are NumPy arrays, never copies unless stated.

```python
# brainsim/params.py : module-level constants, plain dicts/lists, no classes
SEED, DT_MS = 1, 1
D_MAX = 8                       # max delay in ticks
S_MAX = 600_000
REGIONS = {                     # ordered; index in this dict is the region id
  "sense": dict(n_exc=200,  n_inh=0,   r_target_exc=2.0, r_target_inh=0.0, w_max=2.0, a_plus=0.0,  a_minus=0.0),
  "ctx":   dict(n_exc=1600, n_inh=400, r_target_exc=4.0, r_target_inh=8.0, w_max=2.0, a_plus=0.01, a_minus=0.012),
  "hpc":   dict(n_exc=320,  n_inh=80,  r_target_exc=1.0, r_target_inh=6.0, w_max=3.0, a_plus=0.05, a_minus=0.06),
}
PROJECTIONS = [ (src, dst, k_in_mature, sigma) ... ]   # ("sense","ctx",30,0.12), ("ctx","ctx",40,0.25), ("ctx","hpc",30,0.25), ("hpc","hpc",20,0.25), ("hpc","ctx",10,0.25)
EI_MOTIF = 0.25                 # 2.5: target I:E incoming ratio
K_IN_IMMATURE_FACTOR = 2.0
G_WAKE, G_SLEEP = 1.0, 0.3
WAKE_TICKS, SLEEP_TICKS = 60_000, 20_000
NOISE_SIGMA_MV = {"sense": 0.0, "ctx": <calibrated>, "hpc": <calibrated>}   # per region, K0.7 pins the ceiling
SENSE_SPONT_HZ = 5.0            # 2.1b; 50 Hz was tried on 2026-09-11 and is not allowed to be what holds cortex up
CONDUCT_DELAY_TICKS = 1000      # 2.5
PATTERNS = 4                    # the 20 % of sense units nearest each quadrant centre (0.25/0.75 grid); fixed
PATTERN_AMP_MV = 1.3            # mV added to each pattern cell's v per tick while presenting; set by the section 7 calibration (was 1.9)
I_GAIN = 2.5                    # 2.5: I weight draw as a multiple of the E draw; set by the section 7 calibration (was 3.0)
WINDUP_WINDOW_SWEEPS = 10       # 2.5 anti-windup: window length; the compare is between the means of its first and last halves
WINDUP_MIN_PROGRESS = 0.02      # 2.5: floor on the required fall of a group's mean |e| across the window
WINDUP_NOISE_SIGMAS = 3.0       # 2.5: progress must also exceed this many Poisson noise sigmas of the group mean
WINDUP_CAP_FRAC = 0.9           # 2.5: no growth at or above this fraction of S_MAX; equals K0.4's bound on purpose
# plus every constant named in SPEC sections 2.1-2.5 (tau_m, thresholds, STDP, scaling, structural, schedule)
```

```python
# brainsim/net.py
class Network:
    # neuron SoA (length n): region uint8, is_exc bool, x float32, y float32 (both in [0,1] within the
    # region's own unit square), v, theta, x_pre, y_post, rate, act float32, t_last_spike int32, spike_count uint32
    # synapse SoA (capacity s_max): pre int32, post int32, w float32, delay uint8, alive bool, born int32, conduct int32
    n: int; s_max: int
    region_names: list[str]                       # index = region id
    region_slice: dict[str, slice]                # contiguous neuron ranges per region
    @classmethod
    def build(cls, params_module, rng) -> "Network"      # immature Stage 0 net per params
    @classmethod
    def tiny(cls, n, is_exc, synapses, w_max=2.0) -> "Network"
        # n neurons in one region "tiny"; is_exc list[bool]; synapses list of (pre, post, w, delay). For unit tests.
        # Sets homeostasis = False: the slow sweep skips scaling and structural plasticity, because a
        # hand-built fixture has no population setpoints. build() sets it True. Not a model mechanism.
    homeostasis: bool
    @property
    def n_alive(self) -> int
    def in_degree(self, ids, exc_only=True) -> np.ndarray   # alive incoming count per id
    def rebuild_index(self, t) -> None            # rebuilds out/in CSR over synapses with alive & conduct <= t
    def add_synapses(self, pre, post, w, delay, t) -> np.ndarray   # born=t, conduct=t+CONDUCT_DELAY_TICKS; uses free list; raises if full
    def kill_synapses(self, ids) -> None          # alive=False, w=0, push to free list
```

```python
# brainsim/engine.py
class Engine:
    def __init__(self, seed=SEED, net=None, noise_sigma=None, params=params)
        # net=None builds the default Stage 0 network; a Network from Network.tiny is accepted as-is.
        # noise_sigma None -> params.NOISE_SIGMA_MV per region; a float -> every neuron; a dict -> per region
    t: int                         # current tick
    age_s: float                   # sim seconds since construction
    phase: str                     # "wake" | "sleep"
    g: float                       # current plasticity gain
    g_struct: float                # current developmental structural rate G(age) used by the last sweep
    sense_gated: bool              # True while sense input is dropped (asleep)
    net: Network
    stats: dict                    # spike_total, syn_born_total, syn_died_total, syn_touched_last, syn_touched_sum, ticks,
                                   # stall_halt_sweeps, store_clamp_sweeps (2.5 anti-windup: group-sweeps held, sweeps clamped)
    growth_halted: dict[str, bool] # 2.5 anti-windup latch per group ("sense_E", "ctx_E", "ctx_I", "hpc_E", "hpc_I"), as of the last structural_update
    store_clamped: bool            # 2.5 store clamp as of the last structural_update
    encode_mode: bool              # 8.12 encode-mode: the labelled plant schedule, False (today's plant) unless flipped
    encode_stage: str              # "present" | "grace" whenever a schedule is running, else "idle" (mode on) | "off" (mode off)
    def encode_view(self) -> dict  # exactly the frame's `encode` dict; read-only, consumes no RNG
    encode_W: np.ndarray           # int64 ids of the most recent schedule's W; empty until one runs, kept after it ends
    encode_record: dict | None     # {id_pass, W, pattern_id, t_start, t_present_end, t_grace_end, sparse_write, recurrent_write, done}
    def step(self, n=1) -> None
    def inject(self, ids, amp_mv, ticks) -> dict | None   # adds amp_mv to v of ids every tick for `ticks` ticks (sense ids dropped while asleep);
                                   # returns the stim record {stim_id, n_cells, amp_mv, t_accept, t_end_planned, t_first_applied,
                                   # t_last_applied, delivered_ticks, gated_ticks, t_dropped, done} or None when nothing was queued
    def present(self, pattern_id, ticks, amp_mv=None) -> dict | None   # inject the fixed pattern onto sense; same return
                                   # 8.12: with encode_mode on, awake, idle and ticks > 0 this also arms the encode schedule
                                   # (identification pass -> W, a_minus_n zeroed and encode_mask set on W, writes at t_present_end,
                                   # mask off at t_grace_end); every other call is the plain path above
    def stims_active(self) -> list[dict]             # snapshot of records still queued; stimlog: deque(maxlen=STIMLOG_MAX) of finished ones
    def set_sleep(self, on: bool) -> None            # manual override; schedule resumes from here
    def set_noise(self, sigma_mv) -> None            # float for all neurons, or dict per region
    def set_sense_spont(self, hz: float) -> None     # 2.1b spontaneous rate; 0 silences it
    def spike_counts(self) -> np.ndarray             # copy of net.spike_count
    def structural_update(self, e: np.ndarray) -> tuple[np.ndarray, np.ndarray]
        # the 2.5 grow/prune rule (both signs) applied once for the given per-neuron clipped error at the current tick;
        # returns (born_ids, died_ids). The slow sweep calls this with the error it computed; tests call it with a synthetic e.
        # Updates the anti-windup latch and clamp (2.5) from e and n_alive first, then applies them to this call's growth.
    def frame(self) -> dict                          # section 6 frame; clears the per-frame buffers
    def watch(self, neuron_id) -> None               # start recording v for one neuron (500-tick ring)
    def inspect_neuron(self, neuron_id) -> dict      # id, region, is_exc, v, theta, rate_hz, in_deg, out_deg, top_in [[pre, w] x<=20], v_trace list
    def region_stats(self, name) -> dict             # n, rate_hz, n_syn_in, n_syn_out, w_hist {edges, counts}, rate_hist {edges, counts}
    def layout(self) -> dict                         # regions {name: {"id", "n", "n_exc"}}, x, y, region, is_exc (lists), synapse_sample [[id, pre, post] x<=3000],
                                                     # patterns, half_patterns (8.12: cue_ids of each pattern)
```

Frame dict (all JSON-serialisable; the key set is `telemetry.FRAME_KEYS`):
`t, phase, age_s, g, g_struct, sense_gated, ticks (ticks covered), n_syn_alive, syn_born_total,
syn_died_total, born_per_s, died_per_s, spike_total, syn_touched_mean, born_count, died_count, regions {name: {rate_hz, spikes_per_tick
[int] * ticks}}, spikes [[id, dt] ...] capped 4000, truncated bool, born [[pre, post]] capped
2000, died [[pre, post]] capped 2000, growth_halted {group: bool}, store_clamped bool,
wall_ratio (None from the engine; the worker fills it), seq (frame counter), stim_active [record ...],
stim_events [{stim_id, event: "started"|"ended", t, t_dropped?}],
encode {mode, stage, W [id], spiked_last_50 [id], window_ticks, t_present_end, t_grace_end} (8.12)`.
Config adds `encode_k, encode_delta_frac, encode_recurrent_delta_frac, encode_grace_ticks` (8.12).
`rate_hz` is spikes in the frame / n / (ticks / 1000). Counters are cumulative and exact even
when lists are capped.

Sleep semantics in Stage 0: `phase == "sleep"` sets `g = G_SLEEP` and `sense_gated = True`,
which silences the spontaneous `sense` activity of 2.1b and drops `inject`/`present` calls
targeting `sense`. Nothing else. The schedule alternates
`WAKE_TICKS`/`SLEEP_TICKS` automatically; `set_sleep` overrides and the schedule continues
from the override.

Worker/WebSocket messages (JSON): client -> `{"cmd": "run"|"pause"|"step"}`, `{"cmd":"speed","factor":f}`,
`{"cmd":"sleep","on":b}`, `{"cmd":"inject","ids":[...],"amp":a,"ticks":n}`, `{"cmd":"present","pattern":p,"ticks":n}`,
`{"cmd":"watch","id":i}`, `{"cmd":"inspect","id":i}`, `{"cmd":"region","name":s}`, `{"cmd":"layout"}`,
`{"cmd":"stimlog"}`, `{"cmd":"status"}`, `{"cmd":"encode","on":b}` (8.12; `on` must be a bool; while `encode_stage` is `"idle"` a `present` of more than 2,000 ticks is rejected, since arming runs the identification pass inline); any command may carry `"req"` (the server rewrites it to `"<client_id>:<req>"`).
Server -> `{"type":"hello","client_id"}` (once per socket), `{"type":"frame", ...frame}`, `{"type":"inspect", ...}`,
`{"type":"region", ...}`, `{"type":"layout", ..., "patterns", "half_patterns"}`, `{"type":"config", ...engine facts}`,
`{"type":"status","running":b,"speed":f,"t"}`, `{"type":"stimlog","entries","active"}`,
`{"type":"result","req","cmd","t","status": "rejected"|"accepted"|"executed", "reason", ...per-command fields}`,
`{"type":"error","cmd","msg","req"}`. Every worker message carries `run_id`. A `layout` command is
answered by layout, config, status, stimlog in that order. The exact key sets are `telemetry.REPLY_KEYS`.

top_in returns the 10 strongest excitatory plus the 10 strongest inhibitory incoming synapses (w < 0 marks an inhibitory source).
