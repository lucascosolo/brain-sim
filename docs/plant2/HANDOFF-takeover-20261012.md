# Takeover handoff — 2026-10-12

Final handoff for three authorized passes. Stage 1 remains incomplete; no fourth pass was started.

## Repository and authority

Actual starting remote `plant2-stage1` was `55e16ebff62a90d6402745f44fb860010741eba5`.
All takeover work is on `codex/plant2-takeover-20261012`; main and the starting branch are
unchanged. The owner authorized up to three passes and regular checkpoint pushes. Owner
rulings are recorded append-only in `DECISIONS.md`, before new mechanism experiments.

The recovered plant and historical experiments remain frozen. Never run filesystem deletion
commands or deletion APIs, automated temporary cleanup, destructive Git reset/cleanup, force
pushes, or history rewriting. Archive/quarantine instead and ask the owner to delete manually.
The owner's stricter prohibition overrides inherited instructions permitting sandbox deletion.
Do not spend on external APIs/infrastructure. No LLM is part of the simulated runtime mind.

## Checkpoints already published

| Commit | Checkpoint |
|---|---|
| `8002427` | Owner rulings and P2-R1 contract, before its implementation |
| `8b7c062` | Independent baseline audit, historical interpretation errata, reviewed replay code |
| `6733109` | Independently reviewed P2-E6 contract, before its implementation |
| `f1389b6` | Complete mandatory P2-R1 replays, portable per-cue evidence and results |
| `34f7b2c` | R1 independent results review and first handoff |
| `c4cc27b` | Reviewed E6 implementation, frozen parameters and tests |
| `57bec0d` | E6 canonical-input results backed up during remaining runs |
| `2454f06` | Complete E6 results and final R2 contract, before its implementation |
| `70844f3` | E6 independent results audit and decision closure |
| `24a0924` | Independent review of capability and remaining experimenter supply |
| `c7a5350` | Reviewed R2 implementation; 86 non-slow tests passed |
| `6d03724` | R2 exact-degree structural controls backed up during neural runs |
| `03d832e` | All surviving R2 measurements and the original INVALID/empty-file evidence |

Git shell fetch works here, but shell push lacks credentials. Checkpoints are published through
the connected GitHub Git-data API as normal single-parent commits, then fetched into the local
checkout. Ref updates use the expected old SHA and `force=false`. Confirm both local and remote
heads; never describe an unpushed commit as backed up. Large derived raw rasters remain in cache;
portable criterion evidence and reproducible drivers are committed.

## Environment and verification

Python 3.12.14, NumPy 2.3.5, eight effective CPU cores and an 8 GiB cgroup memory limit.
No GPU or paid compute was used. Limit simultaneous full simulations to four, and cap BLAS
threads at one. Each experiment has its own resource rule. Derived data uses
`~/.cache/brain-sim/`; no deletion-based cleanup was performed.

Baseline verification: 63 plant2 non-slow tests passed, seven deselected. The six new replay
tests also passed. The historical safety pytest wrapper was attempted but cannot collect:
the genuine sibling `reflex` package is absent. It was not replaced by a fake module.
The exact upstream standalone safety linter was fetched read-only from reflex-layer blob
`443d3c26ef8bdda42ef507eb1382d5c0fc9d915b`. It reports exactly the 12 grandfathered legacy
findings, with no new finding; independent evaluation of the wrapper's allowlist assertions
passes. This is a qualified alternative check, not a claim that the required wrapper passed.

Pytest's default descriptor capture and temporary-directory machinery are inappropriate under
the owner's absolute cleanup prohibition. After inspecting the tests, use:

```bash
PYTHONPATH="$HOME/.cache/brain-sim/takeover-deps" \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 \
BRAINSIM_CACHE="$HOME/.cache/brain-sim/YOUR_FRESH_PERSISTENT_RUN" OPENBLAS_NUM_THREADS=1 \
python3 -m pytest --capture=sys -p no:cacheprovider -p no:tmpdir --assert=plain -q plant2/tests -m 'not slow'
```

The local test dependency directory contains manually extracted, verified pytest 8.4.2,
iniconfig 2.1.0, pluggy 1.6 and pygments 2.19.2 wheels. Existing packaging is 25.0. No new
production dependency was introduced. Inspect unfamiliar scripts before executing them.

## Baseline corrections that matter for future work

The recorded E1/E4/E5 failures and narrow E2/E3 passes stand. Independent aggregate checks
verified all 80 E5 criterion-vector bits, 20 content counts, ten AUCs and 30 grid-loss values.
All 28 historical raw cache references were absent here. Do not describe the aggregate audit
as a historical raw-data replication. Newly reproduced replay evidence is independently
auditable from committed per-cue counters.

The old pooled input control does **not** preserve individual feature frequencies. Multiple
prototype membership creates much hotter lines in the canonical distribution than in pooled
inputs. Thus the historical correlation-attribution label is not clean causal isolation.
E4 habituation/recovery criteria combine index recall with content; preserving the index alone
does not preserve those labels. Quoted R3 online figures were settled replays of stores written
online, not live R3 readout. Frozen deployed readout is primary; a favorable best-grid outcome
cannot replace it. Assigned-assembly feedback is a reference, not an upper-bound theorem.
Full findings and append-only errata are in the E4/E5 evaluation documents, STAGES, and
`review/plant2/P2-R1/findings-baseline-methodology.md`.

## Pass 1: completed reported diagnostic

See `RESULTS-P2-R1.md`, its frozen contract, `bench/results/p2r1.jsonl` and
`bench/results/p2r1/`. Mandatory reused seeds 44 and 90 completed both loads. Optional 45/91
were not run. Independent results review reproduced 718 aggregate comparisons, 15,000 writer
selections and all eight artifact hashes. Code and methodology reviews are separate records.

At correlated 500 items, R3 content joint=.965 versus inherited=.090 and size-matched
random=.300, but oldest index specificity=.84 still fails. At correlated 1000, index
specificity=.50 and R3 content=.160: the high-load problem remains. In the longer-gap independent
duty case at1000, R3 settled content=.995 versus inherited=.205, random=.710 and anti=.655.
The inherited live duty content result is .545; no R3 live readout was measured.

R3's near-perfect identification of the assigned plateau key does not remove that external
key. No autonomous representation, abstraction, reasoning, capacity growth or graceful
forgetting was demonstrated. Writer contamination and forward-index selectivity are distinct
intervention targets, but their contributions are not an independent additive decomposition.

## Externally supplied structure remains

The experimenter still supplies discrete encoding boundaries, input statistics, random plateau
assemblies, eligibility timing, near-verbatim sensory values, rest/settle/test protocols and
scoring labels. Threshold accommodation uses activity, but this alone is not independent
cognition. Stage 1 remains incomplete unless a future exact contract demonstrates otherwise.

## Continuation discipline

Read the frozen P2-E6 contract before using its code or seeds. Development101, prospective
held-out102 and gated111–115 are separate. A failed development screen must be preserved;
do not tune its mechanism to pass or quietly spend held-out seeds. Any future genuinely
different mechanism needs its own committed contract. The ten-family stress test and separate
50 ms index/75 ms content windows remain canonical. Forty families are transfer only.

The implementation-checkpoint sections below preserve the chronology. Final disposition and
continuation instructions appear in the closure section at the end.

## P2-E6 implementation checkpoint

The complete non-slow plant2 suite passes:76 tests,7 deselected,57.77s. The final seven
E6 tests also passed after report-only field additions. Independent code review reconstructed
16 small learned stores from saved eligible inputs/plateaus and independent replay of the
coin/control rule. Three evidence/execution findings were fixed before full-size simulation.
No full-size outcome exists at this checkpoint. The mechanism and decision thresholds remain
exactly those frozen at6733109.

## Pass 2: complete feasibility failure, preserved without tuning

E6 implementation is c4cc27b; the F10 backup checkpoint is57bec0d; full results and the
next contract are2454f06. All16 checkpoints and both sanity controls finished in608.64s,
without interruption. The exact screen fails canonical F10/1000 specificity179/200 and
oldest specificity89/100. Every other mandatory comparison, independent regression, protocol
and sanity requirement passes. Source/evidence hashes and all70 decision-vector components
were independently checked; see RESULTS-P2-E6.md and findings-results.md.

At1000, specificity baseline/candidate/count-matched-random=.500/.895/.460; joint index
=.440/.865/.410. Candidate recall=.970 versus baseline=.935. The candidate increases own
responses and store density while reducing spurious responses, so this is more than simple
silencing or global sparsification. Adaptive threshold states also differ; no fixed-state
mediator isolation is claimed. Canonical inherited content remains.065 (assigned-A reference
.425). Independent content regression passes; F40 candidate index bars pass, but F40 is
transfer only and cannot rescue canonical failure. No R3 or new inhibition was deployed.

Held-out102 and gated111–115 are deliberately untouched. The driver refuses their use
without complete committed passing prerequisite evidence. Do not weaken the bars, tune
the failed candidate, or relabel this as a five-seed gated FAIL/PASS. A source repair does
not authorize scientific retuning. The useful observed effect remains one development seed.

## Pass 3 selection

P2-R2 final contract is docs/plant2/P2-R2-degree-null.md at2454f06. The separate DRAFT file
is retained only as preparation provenance. This is the third and final pass: a two-seed
exact-degree input null under unchanged E3 learning. It preserves row sizes and per-input
counts within every100-episode block while randomizing co-occurrence. Seeds103/104 are fixed.
It cannot prove a unique frequency/correlation causal decomposition because fine timing,
actual eligibility, coin alignment and operating state can change. It is not a new memory
capability or permission to start sequences. Full results will be appended after execution.


## Final pass 3 disposition and integrity limitation

See RESULTS-P2-R2.md, its frozen contract, bench/results/p2r2.jsonl and the independent
results/integrity reports. Two workers completed all eight neural checkpoints in about
3.3 minutes, well inside the20-minute ceiling. All structural and recorded neural protocol
checks hold. Both fixed input nulls preserve exact feature counts in every100-item block.
No F40 neural trajectories were run; its additional condition is structural-only.

Valid seed103 meets MATERIAL STRUCTURE SENSITIVITY at1000: C2 .470→.755, joint index
.410→.675, C1 .930→.920, oldest recall .930→.920. Inherited content .005→.075 and
assigned-A reference .130→.320 remain inadequate. At500, inherited content rises .115→.980,
but oldest recall falls .980→.910. The favorable content result does not hide that loss.

Seed104 is INVALID and so is the formal two-seed outcome. The final paired read found
bench/results/p2r2/seed104-ORIGINAL-M1000.json empty; two earlier journal progress events
are also absent. The recorded interruption stage names the last assigned-A replay, but
that replay had completed; the error arose during the subsequent paired JSON read.
No source-level truncation/overwrite path was found, and the persistence-loss cause remains
unresolved. Do not attribute it to Git, concurrency or the filesystem without evidence.

The independent auditor reconstructed exactly the originally recorded1,883,558 bytes and
SHA256 a16f1b9c209cccd202f3251ce7f931fe948f6284542ddc71d852ab7e47725a7d from saved
index/content components and timings. NEW artifacts in bench/results/p2r2-recovery contain
that reconstruction, its provenance and a post hoc paired comparison. The original empty
file, missing-event observation and INVALID result are preserved. Recovered104 specificity
.460→.715 and joint index .400→.640 are numerical corroboration, not valid replication.
No source repair, replacement seed, rerun or relaxed acceptance occurred after these results.

## What is now known, and what is not

- Feedback-writer identity matters beyond writer count on the tested settled rasters; R3
  largely identifies the externally assigned key. Live R3 online capability is untested.
- E6's history signal substantially reduces forward-index cross-talk on one development
  seed and beats an exact flip-count control. It still fails its frozen acceptance screen.
- The valid R2 null changes performance while holding coarse feature counts exact; high-load
  failure persists without the original family grouping. Fine timing, actual eligibility,
  variable-length coin alignment and adaptive state also change, so this is not a unique
  causal decomposition or proof that feature frequency alone causes residual failure.
- Online operating-point conflict, composite habituation/recovery, capacity growth and
  graceful forgetting remain unresolved. No fixed-size stress result establishes a scaling
  law. No autonomous memory allocation, abstraction, temporal sequences or reasoning was shown.

No experimenter supply was removed: random plateau keys, discrete encoding boundaries,
input/eligibility protocol, sensory coordinates/values, and externally arranged settle/test
conditions remain. R1 and E6 gains cannot be added into an unmeasured combined system.

## Final verification, evidence and continuation

The final unchanged source suite passes86 non-slow tests (7 deselected),57.67s; separate R2
reviewer tests pass10 in0.53s and reconstruct small raw raster/content evidence. E6's completed
results audit performs96,108 checks; R1's checks include718 aggregate comparisons and15,000
writer reconstructions. R2's independent results and integrity reports state their exact
verification scope. Reviews identified and fixed code defects before runs, corrected historical
interpretations, and preserved the new production-integrity finding afterward. All dispositions
are appended to review/ledger.jsonl. Required safety-wrapper collection remains blocked by
missing reflex; qualified standalone/allowlist verification finds no new safety finding.

Important pinned versions:

- E6 contract6733109, implementation c4cc27b; driver SHA256
  d1d63003896d10310adc7becdcf3e7cbd2c9d541c52aa481496ba70d8b4ccb51.
- R2 contract2454f06, implementation c7a5350; driver SHA256
  c562fe29bf01f315b8598a21503c2117262f513130ace839b2d4aabb5ce6eb19;
  source-manifest aggregate23d86d5af283aa3c5433ed4c4dc07b9207b27396b01c0b4f6361c7802279f3fc.
- Current branch tip contains final reviews, recovery evidence and this handoff; inspect
  git log for its publication SHA. Primary code/contracts and measured checkpoints are listed
  above and embedded in every experiment's provenance.

Commands actually used (do not blindly rerun spent seeds):

```bash
PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 OPENBLAS_NUM_THREADS=1 python3 -u -m plant2.experiments.p2_e6 run --seed 101 --attempt e6-s101-v1
PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 OPENBLAS_NUM_THREADS=1 python3 -u -m analysis.p2r2_degree_null run --seed 103
PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 OPENBLAS_NUM_THREADS=1 python3 -u -m analysis.p2r2_degree_null run --seed 104
PYTHONDONTWRITEBYTECODE=1 python3 -m analysis.p2r2_degree_null summary
```

The last command is read-only and reports INVALID. Production drivers preserve permanent
seed/resource reservations; do not reset them to obtain another result. R1 commands and
provenance are in its report. Optional R1 seeds45/91, E6 held-out102 and gates111–115 were
not run. R2 seeds103/104 are now spent for development informed by this evidence.

Portable per-cue tables, hashes, source, decisions and reviews are committed and pushed.
Large raw NPZ states/rasters remain only under ~/.cache/brain-sim/plant2/p2r1/, p2e6/ and
p2r2/; they are not remote backups. The frozen code/streams regenerate inputs and trajectories,
but reproduction must be explicitly distinguished from a new accepted attempt. Preserve
those caches if available; do not delete them. Historical28 missing caches remain unrecovered.
Execution sessions isolate process namespaces, so the lead manually coordinated global
concurrency; only two R2 workers ran after E6 finished. No process is left running.

Recommended next work: establish separately written, sequenced worker evidence, explicit
durability where supported, and size/hash/completeness verification before consuming results
or declaring completion. Checkpoint publication should use a verified quiescent snapshot.
Then predeclare fresh explanatory replication before choosing between activity-driven pattern
separation on the original F10 distribution and a narrower load/state experiment. Do not tune
E6's failed rule or use the easier input null as a capability pass. No Stage2 escalation.
Protected recovered paths, E1–E5 source/contracts, main and plant2-stage1 were not modified;
no destructive cleanup, history rewrite, force push, merge or paid call occurred.
