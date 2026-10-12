# P2-R2 results: one complete contrast, one preserved invalid attempt

Measured 2026-10-12. Contract `2454f06`; implementation `c7a5350`; structural backup
`6d03724`; all original surviving records, including the empty artifact, backed up at
`03d832e`. This is the third and final takeover pass, an explanation test under unchanged
E3 learning. It is not a new mechanism or Stage 1 capability gate.

**Formal overall status: INVALID.** Seed 103 completed and meets the predeclared
MATERIAL STRUCTURE SENSITIVITY effect-size criterion. Seed 104 completed its neural
measurements but failed the final paired-evidence read. It remains INVALID, with no
replacement, rerun, modified threshold or valid two-seed replication claim. All eight
seed/arm/load neural measurements exist; the original seed-104 paired/1000 artifact does not.

## Execution and integrity incident

Two workers started at 04:37:19 UTC, after E6 and all tests had finished. Seed 103 completed
in 194.49 seconds; seed 104 recorded INVALID and a forensic checkpoint in 198.32 seconds.
Both were well within the shared 20-minute ceiling. Source files were committed before
execution, inherited sources remained byte-identical, and no paid compute was used.
The frozen small original/sham check passed. All recorded neural protocol checks hold:
eligibility means 0.98738–0.98810, mean assigned assembly sizes 20.132 (seed 103) and 20.003 (seed 104) at 1000,
and settle drift at most 0.10894 mV. These do not override the integrity failure.

`bench/results/p2r2/seed104-ORIGINAL-M1000.json` is zero bytes. The worker's retained
descriptor records 1,883,558 bytes and SHA-256
`a16f1b9c209cccd202f3251ce7f931fe948f6284542ddc71d852ab7e47725a7d`.
The journal also lacks seed 104's ORIGINAL/1000 `load_complete` and DEGREE_NULL/500
`load_started` events, although later records and the final in-memory load inventory survive.
The failure occurred when `paired_evidence` read the empty file. The interruption record's
stage field retains the last assigned-A replay label; that replay had already completed.

Independent reconstruction from the saved index component, both content components and final
replay timings reproduces the recorded byte count and SHA-256 exactly. It is saved separately
under `bench/results/p2r2-recovery/`, together with a post hoc paired comparison and a provenance
manifest. The original empty file and invalid record remain untouched. Recovery validates
the recoverable numerical evidence; it does not convert the failed prospective attempt into
a valid replication.

The source uses exclusive artifact creation, rereads bytes for its descriptor and has no
identified path that truncates this saved file. Journal appends use one checked O_APPEND write,
but provide no fsync or independent durability acknowledgement. No deletion or overwrite was
performed to repair this incident. Its cause remains unresolved; neither concurrency, Git,
nor the underlying filesystem is established as the cause. See the independent integrity
review. Future execution should establish durable evidence handling before spending new seeds.

## The input intervention worked as specified

Both seeds' F10 and F40 structural checks hold at both loads on both chains. Every binary
row size and every feature count within every 100-item block is exact; 500/1000 prefix
marginals and overall mean pair overlap agree. Chain 0 alone reaches the learner. Chain 1
is diagnostic. Fixed 10,000 attempted trades per block were not extended or selected by
neural outcomes. F40 is structural-only; no F40 neural transfer result exists.

At F10/1000, delivered-chain measurements are:

| Seed | Original D | Null D | Original Q | Null Q | Active lines replaced | Max within-block count deviation |
|---|---:|---:|---:|---:|---:|---:|
| 103 | 14.45394 | 0.00248 | 36.73036 | 18.90274 | 95.257% | 7 |
| 104 | 14.39250 | -0.00171 | 36.83363 | 19.15428 | 95.217% | 9 |

D is the same-original-family minus other-family mean overlap; Q is mean squared overlap.
Passing the finite-chain checks is not a uniform-sampling certificate. Binary changed-entry
fractions near 4.76% divide by all 4000 coordinates; they must not conceal the approximately
95% replacement of active lines. Within-block cumulative-count RMS deviations are 0.86565
and 0.86611. Coarse counts are preserved; fine timing, cue identities and co-occurrence change.

## Index and content are separate outcomes

O = original; N = fixed-degree null. Content is the frozen 75-ms joint missing-recovery and
intrusion criterion; index retains its 50-ms window. The assigned-A column is a supplied
reference store, not a deployed writer or mathematical upper bound.

| Seed / load | C1 O→N | C2 O→N | Joint index O→N | Old recall O→N | Old specificity O→N | Inherited content O→N | Assigned-A content O→N |
|---|---|---|---|---|---|---|---|
| 103 / 500 | .960→.930 | .895→1.000 | .855→.930 | .980→.910 | .880→1.000 | .115→.980 | .945→.990 |
| 103 / 1000 | .930→.920 | .470→.755 | .410→.675 | .930→.920 | .410→.680 | .005→.075 | .130→.320 |
| 104 / 500† | .960→.935 | .900→1.000 | .860→.935 | .950→.940 | .870→1.000 | .120→.995 | .925→.995 |
| 104 / 1000† | .935→.925 | .460→.715 | .400→.640 | .930→.920 | .400→.670 | .000→.125 | .150→.325 |

† Seed 104 is an INVALID attempt. Its recoverable values are descriptive; its 1000-item
paired comparison was reconstructed independently after the failure, not produced by the
successful prospective driver. They cannot establish formal replication.

On valid seed 103 at 1000, specificity gains 0.285 and joint index gains 0.265, while both
overall and oldest recall lose 0.010. The frozen ordered effect label therefore holds.
Specificity discordance is 74 null-only versus 17 original-only cues; joint index is 75
versus 22. The raw C2 bar-deficit fraction removed is 0.66279, a score ratio rather than
a causal share. Null C2=.755 and oldest specificity=.680 still fail their absolute .90 bars.

Seed 103 at 500 has a 0.070 oldest-recall loss, so its index gain does not meet the
predeclared recall-preserving low-load interpretation despite ceiling specificity. This
cost must accompany the favorable .980 inherited content reading. At 1000 the valid seed's
inherited content gain .070 is below the declared .10 material-content margin; assigned-A
gains .190 but remains at .320. Joint index-and-inherited-content improves only .005→.045.
For seed 104's invalid attempt, the corresponding content gain is .125 and the recovered
C2 bar-deficit ratio is .57955; neither upgrades the formal result.

Index novel rejection is .99/.99 at 1000 on seed 103 and 1.00/1.00 on seed 104. At 500 it
is 1.00 throughout. All 1000-item content oldest scores remain far below .90: inherited
O→N is .00→.07 and .00→.09; assigned-A is .11→.20 and .07→.27. High-load content failure
therefore remains visible independently of index gains.

## What changed besides the measured overlap structure

At 1000 on seed 103, own responders change 18.990→18.660 and spurious responders
21.195→7.410; forward density is .0569378→.0569953. The favorable specificity is not
global silencing or a much smaller store. Assigned-cell onset threshold offset changes
5.89956→5.95175 mV. The corresponding seed-104 descriptive values are own 18.495→18.500,
spurious 20.405→7.685 and density .0565785→.0565686. Operating state is not held fixed.

Plateau sets, episode indices, positional cue masks, novel cues and schedules match. Actual eligibility
column counts differ despite exact input counts (per-block maximum differences up to three
eligible episodes). Variable-size inherited BTSP coin draws also desynchronize; seed 103's
final draw-count difference is +338. This is paired common-seed sampling, not identical
spikes or identical candidate coin outcomes. The intervention does not identify an additive
frequency-versus-correlation causal decomposition, nor isolate fine timing or adaptive state.

## Predictions, review and next decision

The structural decorrelation prediction held. Valid seed 103 supports the predicted high-load
C2 and joint-index gains without the declared recall loss, and the predictions of residual
interference and inherited content below .90. Its lower-load oldest-recall cost is a material
limitation. The planned two-seed prospective confirmation is unverified because seed 104
is invalid. Its reconstructed numerical agreement is explicitly post hoc.

Independent contract and code reviews preceded execution. Two interruption/evidence findings
were fixed before running; the final full suite passed 86 tests, with seven slow tests
deselected. Independent results and integrity reviews are retained in `review/plant2/P2-R2/`;
the former recomputes structural, raw/hash, per-cue, store and RNG evidence without rerunning
neural dynamics. The safety wrapper remains blocked by missing genuine reflex; the exact
standalone scan finds only the 12 grandfathered findings, with no new findings.

The valid contrast reduces uncertainty: original family grouping is not necessary for
high-load failure, and the fixed-degree input intervention materially changes performance.
It does not show that line frequency is the sole residual cause or that the plant learned
pattern separation. No experimenter-supplied structure is removed. Stage 1 remains incomplete.

Next: first validate durable, separately written worker evidence and quiescent checkpoint
verification, then predeclare fresh replication of the explanatory contrast before selecting
activity-driven pattern separation or a narrower load/state intervention. Do not retune E6,
silently deploy R3, or begin sequences. This takeover stops after its three authorized passes.
