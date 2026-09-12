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
plasticity rule, is the owner's call.

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
  `dw < 0`. Population, **imposed-pairing protocol** (third pass, 2026-09-11): seed 1, exactly
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
to `theta` in the spike test (as first drafted; the candidate as built drops the `D_THETA_MV`
factor and uses the names below, see the record that follows); the synaptic scaling step is removed (its two clauses, frozen in
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
`STEP_H`, `H_MAX` (named `CLIP_H`, `THETA_H_MAX` in the first draft) and `HOMEOSTAT = "intrinsic"` (with `"scaling"` selecting today's
path so the branch can run both for comparison); `brainsim/net.py` gains `theta_h`
(float32 per neuron, 0); `brainsim/engine.py::_slow_sweep` applies the offset update where
the scaling block is, `_tick` compares `v >= theta + theta_h`, `frame()` emits
`theta_h` statistics (and `tests/test_ui_truth.py` pins them). Tests first, by a different
worker: K0.14 as above, K0.11 re-targeted, the K0.12-style determinism run across a step,
the K0.2/K0.6 records rerun; then K0.13 unchanged on the branch. Budget under 20 min wall.
Nothing here is implemented; the branch, the tests and the runs each wait for a yes.

**Intrinsic-homeostasis candidate: built, evaluated and rejected (2026-09-12, branch
`intrinsic-homeostasis` from a140bc0; master and the served simulation untouched).**
*Candidate as built (contract `~/.cache/scratch/brainsim-ih/contract.md`, written before
implementation):* mode switch `params.HOMEOSTAT` in {"scaling" (default; today's path,
byte-identical: K0.3 0.927473/0.869582 and K0.13 0.921950 reproduce on the branch, the
historical digest a839afcf... is untouched), "intrinsic"}. State `net.theta_h` (float32,
mV, 0 at start). Spike test `v >= theta + theta_h`; the fast adaptation `theta` is not read
or written by the slow controller. Once per sweep, wake only, `net.homeostasis` on, eligible
neurons only (ctx and hpc, E and I, r_target > 0; sense never, so the forced spontaneous
spike is unchanged): `e = clip((r_target - rate) / r_target, -1, 1)`, `delta = clip(-ETA_H
e, +-STEP_H)`, `theta_h = clip(theta_h + delta, +-H_MAX)`, with ETA_H = STEP_H = 0.25 mV,
H_MAX = 1.0 mV, no `D_THETA_MV` factor. In intrinsic mode the synaptic-scaling step does not
run. Sleep: no update, offset persists and stays applied. H_MAX from the K0.7 curve measured
first (isolated neuron at regional noise, threshold shifted by h, 30 s; ctx 0.73, 0.87,
1.03, 1.33 Hz at h = 0, 0.5, 1.0, 1.5 mV against the 1.2 Hz ceiling; hpc E 0.13, 0.17, 0.23,
0.27 against 0.3): 1.0 mV is the largest offset that keeps every group under 0.3 x
r_target, so the predicted rate authority was about x1.5 and anything needing more was
predicted bound-limited. Telemetry: frame keys `homeostat` and `theta_h` (per adapting
group mean/min/max/at-bound fraction, {} in scaling mode; the Diagnostics table flattens
them), config keys homeostat/eta_h/step_h/h_max, inspect `theta_h`; no UI redesign.
Tests (tests/test_intrinsic_homeostasis.py, written before the implementation): scaling
mode unchanged, direction and magnitude, per-sweep clip and bounds, eligibility (sense,
zero target, the mask itself), sleep freeze with persistence, disabled homeostasis, fast
adaptation independent, sensory interface identical across modes, K0.7 at -H_MAX (ctx and
hpc rig, existing ceiling), real-tick behaviour across four sweeps, candidate determinism
and telemetry neutrality across a `set_noise` step, candidate digest pinned separately
(3feda54f...), historical digest text unchanged. K0.2 and K0.6 pass in intrinsic mode (seed
1). Instrument: scaling prediction identically 0 in intrinsic mode, attribution closes,
ctx_A `theta_h` recorded per sweep; `--mode` flag on both drivers.
*K0.14 (tests/test_k014_recovery.py, 170 s runs, normal schedule; reference 90-100 s,
perturbation 100-120 s = W1, restore at 120 s, W2 120-140 s, sleep 140-160 s, W3 160-170 s;
P1 ctx noise 2.35 -> 2.0 mV, P2 2.35 -> 1.2 mV, P3 sense spontaneous 5 -> 0 Hz, each with
a complete regional map; band [0.75, 1.25] x target; recovered = >= 10 consecutive in-band
sweeps lasting to the window's end within 10 s):* the candidate fails before any
perturbation. Seed 1, intrinsic, mature wake: ctx E 2.59 Hz (0.65 x target) with mean
theta_h -0.98 mV and 88 % of ctx E at the -1.0 mV bound; ctx I 3.3 Hz (0.41), hpc E 0.48
(0.48), hpc I 1.2 (0.20), all at the bound; latch occupancy 100 %; reference in-band 0 %.
Sense->ctx rest weight 0.44 w_max (the prediction "falls from 0.75 toward 0.45" held; the
prediction "ctx E reaches 4 +- 0.5 Hz" did not: a 1 mV offset buys about x1.5 on an isolated
neuron and less in the network once the weights have relaxed). P1: W1 1.54 Hz, W2 2.51 Hz,
0 % in band, both windows bound-limited (mean |theta_h| >= 0.95 H_MAX in every sweep, rate
below band); burst 0.023, floor 0.30 Hz. P2: W1 0.25 Hz, floor safeguard fails (0.053 Hz);
bound-limited. P3: W1 1.31 Hz, bound-limited, safeguards hold. Seeds 2 and 3, intrinsic:
ctx E 1.73-1.74 Hz at rest (0.43), hpc I 0.31 Hz; every window bound-limited; the rate floor
fails in 90-140 s (0.14-0.17 Hz, hpc I) and the burst guard fails at 0.22-0.24 at t = 1 s,
the start-up transient before the first sweep, identical in both modes. Scaling mode, seed
1, for comparison: P1 recovers (8 s in W1, 1 s in W2; reference in band 100 %; the pruning
rule removes 38,000 synapses during W1-W2); P2 and P3 fail as controller failures (W1 1.44
and 1.53 Hz; W2 60-70 % in band but no 10-sweep run to the window's end); safeguards hold.
Per the contract, K0.13 was not run in intrinsic mode (gated on P1 ctx E recovery).
*Reading:* the K0.7 noise-alone ceiling (offset <= 1.0 mV) and the 4 Hz setpoint cannot
both be met by intrinsic excitability once STDP owns the weights and they settle near the
rule's fixed point; the bound and the recovery requirement conflict, as the contract said
to report rather than resolve by loosening K0.7 or retuning noise. The synaptic-scaling
baseline recovers only from the mild perturbation. The rest-weight half of the hypothesis
is confirmed; the rate half is refuted at this bound. No gain, A_plus or mechanism change
was made. Recommendation: reject the candidate; the branch and its records are kept.
K0.1, K0.3, K0.4 remain unresolved.

## 9. Files created in Stage 0

```
SPEC.md                    this file
requirements.txt           numpy, fastapi, uvicorn[standard], pytest
run.py                     starts the server on localhost:8000
brainsim/__init__.py
brainsim/params.py         every constant, region table, projection table, schedules, seed
brainsim/net.py            SoA arrays, immature wiring, CSR rebuild, grow/prune primitives
brainsim/engine.py         tick loop, ring buffer, STDP, slow sweep, sleep state machine, injection
brainsim/telemetry.py      frame assembly, inspect/region/layout queries
brainsim/worker.py         subprocess loop, queues, pacing
server/app.py              FastAPI static + /ws
ui/index.html  ui/app.js  ui/style.css  ui/evidence.js (pure client evidence state, node-testable)
ui/stage0_results.json     hand-maintained recorded results (test, outcome, commit, date, evidence)
mockups/index.html         approved UI mockup with a scripted demo feed (design record; not served)
tests/test_rules.py        K0.3 unit level and population (imposed pairing), K0.13 baseline, structural primitives
tests/k03_pairing.py       K0.3 population protocol, instrument and report (test-side; engine untouched)
tests/k03_brief_volley.py  brief-volley diagnostic alongside K0.3 (test-side; reuses the instrument; not a kill test)
tests/k013_onset.py        K0.13 baseline: autonomous onset learning, three arms and probes (test-side; engine untouched)
tests/test_intrinsic_homeostasis.py  intrinsic-homeostasis candidate unit tests (branch intrinsic-homeostasis only; candidate rejected)
tests/test_k014_recovery.py  K0.14 recovery contract, both homeostat modes (branch only; kill-marked)
tests/test_k03_instrument.py  pins the instrument generalisation: zero pulses inject nothing, default path numerically unchanged
tests/test_kill_stage0.py  K0.1, K0.2, K0.4, K0.5, K0.6
tests/test_ui_truth.py     frame keys vs app.js/evidence.js, frame fields vs engine attributes
tests/test_stim_bookkeeping.py  stimulus records, events, stimlog bound (observation only)
tests/test_engine_determinism.py digest pinned at 3060f23: equivalence with the pre-instrumentation engine for the tested schedule
tests/test_session_commands.py  worker Session: results, step FIFO, sleep ack, layout burst
tests/test_server_clients.py    per-socket client_id, req prefixing, malformed payloads
tests/test_results_record.py    stage0_results.json schema and test-node existence
tests/test_client_evidence.py + tests/js/evidence.test.mjs  client evidence rules (node --test)
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
    def step(self, n=1) -> None
    def inject(self, ids, amp_mv, ticks) -> dict | None   # adds amp_mv to v of ids every tick for `ticks` ticks (sense ids dropped while asleep);
                                   # returns the stim record {stim_id, n_cells, amp_mv, t_accept, t_end_planned, t_first_applied,
                                   # t_last_applied, delivered_ticks, gated_ticks, t_dropped, done} or None when nothing was queued
    def present(self, pattern_id, ticks, amp_mv=None) -> dict | None   # inject the fixed pattern onto sense; same return
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
    def layout(self) -> dict                         # regions {name: {"id", "n", "n_exc"}}, x, y, region, is_exc (lists), synapse_sample [[id, pre, post] x<=3000]
```

Frame dict (all JSON-serialisable; the key set is `telemetry.FRAME_KEYS`):
`t, phase, age_s, g, g_struct, sense_gated, ticks (ticks covered), n_syn_alive, syn_born_total,
syn_died_total, born_per_s, died_per_s, spike_total, syn_touched_mean, born_count, died_count, regions {name: {rate_hz, spikes_per_tick
[int] * ticks}}, spikes [[id, dt] ...] capped 4000, truncated bool, born [[pre, post]] capped
2000, died [[pre, post]] capped 2000, growth_halted {group: bool}, store_clamped bool,
wall_ratio (None from the engine; the worker fills it), seq (frame counter), stim_active [record ...],
stim_events [{stim_id, event: "started"|"ended", t, t_dropped?}]`.
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
`{"cmd":"stimlog"}`, `{"cmd":"status"}`; any command may carry `"req"` (the server rewrites it to `"<client_id>:<req>"`).
Server -> `{"type":"hello","client_id"}` (once per socket), `{"type":"frame", ...frame}`, `{"type":"inspect", ...}`,
`{"type":"region", ...}`, `{"type":"layout", ..., "patterns"}`, `{"type":"config", ...engine facts}`,
`{"type":"status","running":b,"speed":f,"t"}`, `{"type":"stimlog","entries","active"}`,
`{"type":"result","req","cmd","t","status": "rejected"|"accepted"|"executed", "reason", ...per-command fields}`,
`{"type":"error","cmd","msg","req"}`. Every worker message carries `run_id`. A `layout` command is
answered by layout, config, status, stimlog in that order. The exact key sets are `telemetry.REPLY_KEYS`.

top_in returns the 10 strongest excitatory plus the 10 strongest inhibitory incoming synapses (w < 0 marks an inhibitory source).
