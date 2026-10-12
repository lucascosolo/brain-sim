# Takeover handoff — 2026-10-12

Working handoff; final experimental outcomes are appended when the passes finish.

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
BRAINSIM_CACHE="$HOME/.cache/brain-sim/YOUR_FRESH_PERSISTENT_RUN" \
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

Append the remaining pass outcomes, final source hashes, reviewer dispositions, exact unrun
conditions and the next recommendation before treating this handoff as final.
