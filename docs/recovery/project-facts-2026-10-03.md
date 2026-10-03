# brain-sim: project facts as recorded by a second observer (Grok session, 2026-10-03)

Status of this document: a **secondary account**. It was written by a Grok session that
helped the owner steer the Claude sessions, from pasted reports only; it never had the
repository. It is kept because it records the owner's closed gates and standing decisions,
which no source file does, and it names the commits and branches the git recovery should
look for. Where it conflicts with recovered source or SPEC.md, the recovered file wins.

Recovery cross-check (2026-10-03): the recovered loose git objects contain commit `5f42734`
(2026-10-01, "SPEC 8.47 result ... K1.1 remains FAIL. Not merged"), consistent with the 8.47
entry below. Master tip `c9863d6` not yet found.

---

## Project intent (certain)

- Not a chatbot / not a frontier LLM as the mind.
- A small inspectable creature on a PC: experience on a sense nerve → inside changes in a
  measurable way → a human can see that change.
- Path A (late in the work): spike-first; language only as a late emergent capability after
  earlier stages; no transformer/LLM as the mind; no mini-AGI architecture inside the plant.
- Success = persisted memory + a way to see it, not fluency. No certificate of inner life.
- Hardware context: i5-12600KF, ~31 GB RAM, GTX 980 Ti treated as unusable for the plant;
  CPU NumPy, Python venv, FastAPI + vanilla JS UI.
- Scale target: thousands of neurons now (~2,600 cited), not 86 billion.

## Architecture (certain from reports)

Regions (Stage 0 plant): sense (prosthetic sheet, ~200 cells; patterns A–D as topographic
patches); ctx (cortex-like recurrent E/I); hpc (smaller sparse binder). Flow sense → ctx →
hpc; no direct sense→hpc. Absent by design: thalamus, basal ganglia, dopamine, cerebellum,
language areas.

Neuron/synapse model: LIF + adaptive threshold; delay ring; pair STDP on excitatory paths;
synaptic scaling, structural grow/prune; two-sign I structure, balance term, anti-windup;
sleep = schedule (gate sense, drop plasticity gain), not a separate organ.

Unknown to the observer: exact file layout beyond names mentioned, parameter values except
those quoted in results.

## Closed gates / rules (owner policy)

Not optional unless the owner explicitly reopens them:

- Sense→ctx population contrast / S1.0 as the boss key (pair STDP+scaling depressed used
  paths; triplet/gated STDP rejected for stated reasons).
- I_GAIN / rejected intrinsic homeostasis as previously run.
- Vogels iSTDP unless a new experiment is named.
- Spatial half-cue, local unmix, W→W amplitude ladder: closed hunts.
- Rejected k11-style branches not to be merged back as "the fix".
- K1.1 bar not to be lowered; official half-cue form tied to 13/16 at 50 ticks, 1.3 mV.
- No teacher current / I-off-on-W / engineered synchrony to force a pass.
- No hiding FAIL by floors/caps that redefine the test.
- Proxies labeled, not claimed as biology.

Later owner decisions:

- K1.1-top16: 13/16 of identified top cells @ 50 ticks, trained − never-trained, B/none
  bounds: primary episode-recall law.
- Official size ≤20 assembly clause stays FAIL / separate sparsity goal (gen2 assemblies were
  large: tens to 100+ cells).
- Sense→ctx wall = no S1.0 reopen; pair STDP may still touch those synapses as the engine
  always did.
- Learned disinhibition acceptable as a labeled Stage-1 memory kind; not described as E↔E
  binding.
- Primary line for "cells bound": 8.46 excitatory / joint-style setting with learning onto
  inhibitory cells off.
- 8.30 pending-express = labeled disinhibition baseline, not the primary binding line.

## Experimental arc (results as reported)

Early / encode-mode: master without exemptions forms an assembly that scaling+prune+LTD then
strip; encode-mode (unmerged) could stamp weights; K1.1 quiet half-cue repeatedly FAIL (e.g.
5/16 at 50 ticks); A-then-B: without protection B deleted A-only rows, with scaling+elim off
on exclusive W_A deletions → 0; weight books could coexist but the 50-tick readout did not
select the matching club; selective-write fixture: wiring contrast survived, weight contrast
equalized.

Learning-rule / ceiling (8.21–8.24): triplet and other rules gave little or no recall
advantage; hand-max weights still failed official 50-tick completion on the old graph; gen2
(denser hpc recurrence, quieter cortex) healthy after K0.10b storage limit scaled by rule;
learned half-cue on gen2 did not give clean trained ≫ never-trained; never-trained baselines
essential; K1.1-200 raw counts contaminated by generic responsiveness.

Seat of recall (8.27–8.37): 8.27 pair training hurt half-cue (cortex→W weakened); 8.28
plateau override gave the first trained ≫ twin; 8.29 engine pending-STDP: gain on some
seeds, seed 2 runaway; 8.30 pending-express: PASS trained−twin kill test on 3 seeds, no
runaway, not official K1.1; 8.31 official K1.1 on 8.30: FAIL on size (86–134 vs max 20);
8.33 fewer cortex→memory inputs did not shrink assemblies; 8.34–8.35 learned gain seated in
"rest", especially excitatory synapses onto inhibitory cells; transplant moved the gain;
8.37 disabling learning on the inhibitory-related path removed the gain.

Excitatory-binding line (8.40–8.48): 8.46 confirmed with I-learning off, trained beats twin
on six brains, not full 13/16 everywhere, thin idle margins on some; 8.47 official K1.1 still
FAIL on size (40–61); 8.48 persistence lost by the fixed bar (gain halves by ~10 s, holds
toward ~37 s, with or without sleep); A-then-B: B does not erase A; REJECTED on brain 2 under
the dual-pattern kill test (table in SPEC 8.48 / branch `persist-dual`).

Path A charter: reported committed on master (`c9863d6`): SPEC section 0 Path A + stage
ladder; primary line 8.46; 8.30 baseline only; UI note that text in/readout absent until
Stage 4. Stages: 1 episode → 2 sequences → 3 profiler growth → 4+ symbols; stages 2+ had no
contract or code.

## Names to look for in recovery

Repo `~/Workspaces/brain-sim`; worktrees `~/.cache/brain-sim-*`; logs
`~/.cache/scratch/brainsim-*`; files `SPEC.md`, `ui/stage1_results.json`, `tests/k8xx_*.py`,
`brainsim/`; branches `gen2`, `pending-express`, `plateau-override`, `deficit-diag`,
`joint-confirm`, `persist-dual`; one cited invocation shape `--k 1.25 --eta 0.30` (not a
full spec).

## Not achieved (certain)

Official K1.1 as coded (incl. size ≤20); stable long persistence on the 8.46 line at the
8.48 bar; clean dual-pattern pass on all brains; Stage 2 sequence memory; language.
