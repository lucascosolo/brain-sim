# P2-R2b results: the exact-degree contrast replicates on two fresh seeds

Measured 2026-10-22, 17:06-17:09 UTC, on this PC (CPython 3.11.17, NumPy 2.4.6). Contract
`docs/plant2/P2-R2b-replication.md`, frozen at `4cd865b`; wrapper driver and tests at
`e2548cb`; the frozen P2-R2 driver executed byte-identical to `c7a5350`. Records:
`bench/results/p2r2b.jsonl` (64 rows); portable per-cue, structural and paired evidence under
`bench/results/p2r2b/`; per-worker hash-chained journals `seed105.journal.jsonl` and
`seed106.journal.jsonl`. This is a reported replication of an explanation test. It is not a
capability gate, not a new mechanism, and it removes no experimenter supply.

**Formal status: COMPLETE on both seeds; replicated label at M = 1,000: MATERIAL STRUCTURE
SENSITIVITY.** Both seeds' `seed_complete` records read COMPLETE with no missing stage; both
`evidence_verification` records passed (33 and 31 artifacts re-read and hash-checked, journals
intact, no failure). Wall time 154.5 s (seed 105) and 152.0 s (seed 106), two workers started
together, inside the 20-minute ceiling. No `git` command ran between the workers' start and
their exit. The frozen small original/sham parity check passed; F10 and F40 structural checks
passed at both loads on both seeds; every protocol check (eligibility, mean |A| at 1,000,
settle drift) holds.

## Index and content, per seed and load

O = original F10/s60 inputs; N = exact-degree null (chain 0). Index window 50 ms; content is
the frozen 75 ms joint criterion through the inherited responder-written store and the
assigned-A diagnostic store on each arm's own raster.

| seed / load | C1 O→N | C2 O→N | joint index O→N | oldest recall O→N | oldest specificity O→N | inherited content O→N | assigned-A content O→N |
|---|---|---|---|---|---|---|---|
| 105 / 500 | .985→.965 | .945→.990 | .930→.955 | .980→.970 | .960→.990 | .115→.960 | .950→.985 |
| 105 / 1000 | .925→.915 | .485→.745 | .420→.660 | .930→.910 | .500→.710 | .000→.065 | .175→.315 |
| 106 / 500 | .965→.960 | .905→1.000 | .870→.960 | .960→.970 | .900→1.000 | .140→.965 | .905→.980 |
| 106 / 1000 | .915→.950 | .455→.720 | .390→.670 | .930→.960 | .420→.680 | .000→.070 | .110→.295 |

Novel-cue rejection (C3) is .990-1.000 everywhere. At M = 1,000 the frozen `classify` gives
MATERIAL STRUCTURE SENSITIVITY on both seeds: Delta C2 = +0.260 (105) and +0.265 (106),
Delta joint index = +0.240 and +0.280, Delta C1 = -0.010 and +0.035, Delta oldest recall =
-0.020 and +0.030. The raw C2 bar-deficit fraction removed is 0.62651 (105) and 0.59551
(106); `half_bar_deficit_removed_on_both` is true. Null C2 (.745, .720) and null oldest
specificity (.710, .680) still fail their absolute .90 bars, as predicted. Inherited content
at 1,000 is .065 and .070 on the null (INTERMEDIATE/SMALL CHANGE, +0.065 and +0.070);
assigned-A content .315 and .295.

At M = 500 the labels are LOW-LOAD DESCRIPTIVE by construction. Inherited content rises
.115→.960 and .140→.965 (MATERIAL GAIN, +0.845 and +0.825). Seed 106 meets the reported
low-load material index gain (Delta C2 +0.095, joint +0.090, recall deltas -0.005 and +0.010);
seed 105 does not (Delta C2 +0.045). Neither seed shows an oldest-recall loss at 500
(-0.010 and +0.010).

Paired sampling caveats are as in P2-R2: coin draw counts differ between arms on both seeds
(`coin_draw_counts_equal` false), and actual eligibility column counts differ by at most 2-3
episodes per block. This is common-seed paired sampling, not identical spikes.

## The six frozen predictions

| prediction | outcome | evidence |
|---|---|---|
| P1 complete, structurally sound | **held** | both seeds COMPLETE, `missing_stages` empty, F10 `decision.ok` true at 500 and 1,000 |
| P2 MATERIAL STRUCTURE SENSITIVITY on both seeds at 1,000 | **held** | labels above |
| P3 null C2 < .90 and bar-deficit fraction in [0.50, 0.80] on both | **held** | .745/.720; 0.62651/0.59551 |
| P4 inherited content < .15 and assigned-A < .40 at 1,000, both arms, both seeds | **held** | max inherited .070; max assigned-A .315 |
| P5 on at least one seed at 500: oldest-recall delta <= -0.03 and inherited Delta S2 >= 0.10 | **failed** | oldest-recall deltas -0.010 (105) and +0.010 (106); content gains +0.845 and +0.825 |
| P6 mean Delta own50 within 1.0 and mean Delta spurious50 < -10 on both seeds | **failed on seed 106** | 105: -0.025 / -10.46 (passed); 106: +0.265 / -6.97 (spurious fell by 7, not 10) |

P5's failure matters: the low-load oldest-recall cost seen on P2-R2's valid seed 103
(.980→.910) did not recur on either fresh seed, so that cost is not a reliable feature of the
contrast; it stays recorded as a seed-103 observation. P6's magnitude was mis-set for seed
106, whose original arm had fewer spurious responders to remove; the qualitative reading (own
responders unchanged, spurious responders fewer, so the specificity gain is not global
silencing) holds on both seeds. No prediction is revised; both failures are recorded.

## What this establishes, and what it does not

With P2-R2's valid seed 103, three valid seeds now show that randomising which lines co-occur,
while holding every line's count within each 100-episode block exact, removes about 60 % of
the measured C2 bar deficit at M = 1,000 and leaves high-load specificity and content below
their bars. The original family grouping is therefore not necessary for high-load failure,
and co-occurrence structure is a material part of it; line load alone does not explain the
residual failure, and the finite block-constrained randomisation is not a causal partition.
The condition the independent capability review set for selecting a co-occurrence-sensitive
mechanism ("replicated material structure sensitivity without the declared recall loss") is
now met on two fresh seeds. Nothing here is a memory capability; the random plateau keys,
episode boundaries, eligibility timing, verbatim values and settle/test schedule remain
supplied.

Evidence handling worked as contracted: every artifact was created exclusively, fsynced,
read back and hashed at the write, and re-verified before `paired_evidence` and again after
`run()` returned; the P2-R2 empty-artifact failure mode would have been caught at the first
verification with the recorded size and hash.
