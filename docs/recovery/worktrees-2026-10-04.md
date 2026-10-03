# brain-sim worktrees recovered from the ext4 journal (2026-10-04)

Source: `/mnt/sdcard/rebuilt/home/.cache/brain-sim-<name>/` (each was a worktree of `/home/lucas/Workspaces/brain-sim/.git`).
Times are file mtimes in UTC from the journal inode records. Skipped: `__pycache__`, `.pytest_cache`, `*.pyc`, the `.git` pointer file.
`altN` = another recovered copy of the same path; in these worktrees nearly all alt copies are byte-identical to the primary with the same mtime (duplicate journal records), and none differs from the chosen copy within the same minute. Files marked JUNK failed a content check (binary / wrong file type) and were not used.
Every `.py` file (all versions) passes `ast.parse`; every `.json` parses.

| worktree | files (primary) | alt versions | newest mtime (UTC) | likely SPEC / K-test | branch |
|---|---|---|---|---|---|
| asd | 1 | 0 | 2026-10-01 21:10 | SPEC.md tops out at 8.32 Why is the memory so large? Assembly size by plant and by rule (prede | - |
| diag (deficit-diag) | 4 | 0 | 2026-10-01 05:45 | SPEC.md tops out at 8.20 What the published triplet rule would do on this plant's own spike tr; tests: 8.18 (k818_drive_loss.py), 8.19 (k819_homeostat_ablation.py), 8.20 (k820_rule_eval.py) | recovered/diag |
| encode-mode | 1 | 0 | 2026-09-13 18:10 | SPEC.md tops out at 8.12 Encode-mode: one labelled plant schedule (predeclared 2026-09-13) | - |
| eta | 1 | 0 | 2026-10-01 22:53 | SPEC.md tops out at 8.39 A stronger heterosynaptic write, with room under the bound (predeclar | - |
| gated | 4 | 0 | 2026-09-13 00:48 | SPEC.md tops out at 8.1 Second Stage 1 candidate: gated plasticity, three-factor (predeclared; tests: s10_gated.py, test_s10_gated.py | recovered/gated |
| gen2 (gen2) | 1 | 0 | 2026-10-01 16:36 | tests: 8.26 (k826_learned.py) | - |
| head | 1 | 0 | 2026-10-01 22:50 | SPEC.md tops out at 8.38 Room to strengthen: a higher weight bound on the memory region's exci | - |
| hw | 2 | 0 | 2026-10-01 03:41 | - | - |
| ih | 7 | 0 | 2026-09-12 09:48 | SPEC.md tops out at 2.7 Sleep, replay, consolidation (CLS); tests: k013_onset.py, k03_brief_volley.py, k03_pairing.py, test_k03_instrument.py | recovered/ih |
| inh | 6 | 4 | 2026-10-01 05:12 | SPEC.md tops out at 8.17 Inhibition as the hippocampal rate controller, with the heterosynapti; tests: 8.17 (k817_inh_homeostat.py) | recovered/inh |
| jb | 0 | 0 | - | - | - |
| jc (joint-confirm) | 1 | 0 | 2026-10-01 23:25 | SPEC.md tops out at 8.46 Does the 8.45 pass hold on fresh draws and fresh seeds (predeclared 2 | - |
| k03-hold | 5 | 0 | 2026-09-12 07:19 | - | recovered/k03-hold |
| k11ew | 0 | 0 | - | - | - |
| k11ltp | 3 | 1 | 2026-09-13 04:48 | SPEC.md tops out at 8.4 K1.1 rerun with a labelled write proxy: `hpc`-afferent LTP-only durin | recovered/k11ltp |
| k11o | 0 | 0 | - | - | - |
| k11p | 4 | 0 | 2026-09-13 02:40 | tests: k11_binding.py, test_k11_prune_off.py | recovered/k11p |
| k11rd | 5 | 4 | 2026-09-13 14:49 | SPEC.md tops out at 8.8 K1.1 rerun with a labelled proxy on the selective parent: restricted; tests: test_k11_restricted_donors.py | recovered/k11rd |
| k11rw | 2 | 1 | 2026-09-13 14:34 | SPEC.md tops out at 8.7 K1.1 rerun with a labelled proxy on top of 8.5 and 8.6: W recurrent c | - |
| k11wm | 4 | 7 | 2026-09-13 15:28 | SPEC.md tops out at 8.9 K1.1 rerun with a labelled proxy on the 8.6 parent: encode window on | recovered/k11wm |
| k11ww | 1 | 0 | 2026-09-13 15:53 | SPEC.md tops out at 8.10 K1.1 rerun with a labelled proxy on the 8.9 plant: small W -> W (pred | - |
| oj | 0 | 0 | - | - | - |
| pd (persist-dual) | 2 | 0 | 2026-10-02 00:33 | SPEC.md tops out at 8.48 Persistence and a second pattern on the 8.46 setting (predeclared 202; tests: 8.48 (k848_persist_dual.py) | - |
| pend (pending-express) | 0 (+6 junk) | 1 | - | - | - |
| pw | 1 | 0 | 2026-09-30 23:20 | SPEC.md tops out at 8.14 Write-tagged protection from the rate-driven structural prune (predec | - |
| rec | 0 | 0 | - | - | - |
| rep | 4 | 5 | 2026-10-02 00:24 | SPEC.md tops out at 8.44 The same write measured with 32 repeats (predeclared 2026-10-01) | recovered/rep |
| rof | 1 | 0 | 2026-10-01 22:23 | SPEC.md tops out at 8.34 Is the recall recurrent? Memory-to-memory links switched off at recal | - |
| rs | 11 | 29 | 2026-10-02 00:24 | SPEC.md tops out at 8.22 Readouts with learning frozen, and an offline screen of two further p; tests: 8.22 (k822_frozen_readout.py), 8.22 (k822_rule_screen.py), 8.22 (k822_rules.py), test_k822_rules.py | recovered/rs |
| s1 | 2 (+1 junk: SPEC.md is binary) | 0 | 2026-09-12 19:47 | tests: k03_pairing.py | - |
| seat | 5 | 27 | 2026-10-01 23:16 | SPEC.md tops out at 8.35 Where is the learned recall stored? Seat-finding transplants (predecl | recovered/seat |
| serve | 8 | 36 | 2026-10-02 00:56 | SPEC.md tops out at 8.49 Why the excitatory-binding memory halves in ten seconds: a diagnosis; tests: 8.15 (k815_slot_reuse.py), 8.16 (k816_hetero_write.py), k013_onset.py | recovered/serve |
| shi | 2 | 4 | 2026-10-01 22:50 | SPEC.md tops out at 8.33 Fewer cortex inputs per memory cell: an in-degree sweep (predeclared | - |
| sw | 5 | 44 | 2026-10-02 00:24 | SPEC.md tops out at 8.15 Selective-write contrast fixture: a diagnostic, not a mechanism (pred; tests: 8.15 (k815_selective_write.py), k11_never_trained.py | recovered/sw |
| tt | 35 | 190 | 2026-10-02 00:24 | SPEC.md tops out at 8.13 Two-timescale weights: a slow component the homeostat cannot erase (p; tests: k03_brief_volley.py, k03_pairing.py, k11_binding.py, test_k11_binding.py, test_k11_encode_mode.py | recovered/tt |
| zs | 0 | 0 | - | - | - |

36 worktree directories were found (no `brain-sim-po`); `brain-sim-serve.pid` is a plain file (6 bytes, 2025-09-11), not a worktree.

## Main = best union

59 paths written to main from worktrees (newest valid version of each path); 9 paths kept the clone (git-carved) copy because it was newer or same-minute.

| path | from worktree | file | mtime (UTC) |
|---|---|---|---|
| .gitignore | sw | .gitignore | 2026-10-02 00:24:43 |
| SPEC.md | serve | SPEC.md | 2026-10-02 00:56:06 |
| brainsim/encode.py | tt | brainsim/encode.py | 2026-09-30 22:15:36 |
| brainsim/engine.py | rep | brainsim/engine.py | 2026-10-02 00:24:43 |
| brainsim/hetero.py | rep | brainsim/hetero.py | 2026-10-02 00:24:43 |
| brainsim/net.py | serve | brainsim/net.py | 2026-10-01 05:12:49 |
| brainsim/params.py | rep | brainsim/params.py | 2026-10-02 00:24:43 |
| brainsim/telemetry.py | seat | brainsim/telemetry.py | 2026-10-01 23:16:04 |
| brainsim/triplet.py | seat | brainsim/triplet.py | 2026-10-01 23:16:04 |
| mockups/index.html | tt | mockups/index.html | 2026-10-01 23:16:04 |
| pytest.ini | tt | pytest.ini | 2026-10-01 22:20:39 |
| requirements.txt | tt | requirements.txt | 2026-10-01 22:20:39 |
| run.py | tt | run.py | 2026-10-01 22:20:39 |
| server/app.py | tt | server/app.py | 2026-10-01 22:20:39 |
| tests/conftest.py | tt | tests/conftest.py | 2026-10-01 22:20:39 |
| tests/js/evidence.test.mjs | rs | tests/js/evidence.test.mjs | 2026-10-01 22:20:39 |
| tests/js/ui_helpers.test.mjs | serve | tests/js/ui_helpers.test.mjs | 2026-10-01 22:20:39 |
| tests/k013_onset.py | serve | tests/k013_onset.py | 2026-10-01 22:20:39 |
| tests/k03_brief_volley.py | tt | tests/k03_brief_volley.py | 2026-10-01 22:20:39 |
| tests/k03_pairing.py | tt | tests/k03_pairing.py | 2026-10-01 22:20:39 |
| tests/k11_binding.py | tt | tests/k11_binding.py | 2026-10-01 22:20:39 |
| tests/k11_never_trained.py | sw | tests/k11_never_trained.py | 2026-10-01 22:20:39 |
| tests/k815_selective_write.py | sw | tests/k815_selective_write.py | 2026-10-01 22:20:39 |
| tests/k815_slot_reuse.py | serve | tests/k815_slot_reuse.py | 2026-10-01 06:28:01 |
| tests/k818_drive_loss.py | diag | tests/k818_drive_loss.py | 2026-10-01 05:14:24 |
| tests/k819_homeostat_ablation.py | diag | tests/k819_homeostat_ablation.py | 2026-10-01 05:26:59 |
| tests/k820_rule_eval.py | diag | tests/k820_rule_eval.py | 2026-10-01 05:41:32 |
| tests/k822_frozen_readout.py | rs | tests/k822_frozen_readout.py | 2026-10-01 06:28:01 |
| tests/k822_rule_screen.py | rs | tests/k822_rule_screen.py | 2026-10-01 06:28:01 |
| tests/k822_rules.py | rs | tests/k822_rules.py | 2026-10-01 06:28:01 |
| tests/k848_persist_dual.py | pd | tests/k848_persist_dual.py | 2026-10-02 00:25:44 |
| tests/s10_gated.py | gated | tests/s10_gated.py | 2026-09-13 00:47:05 |
| tests/test_client_evidence.py | tt | tests/test_client_evidence.py | 2026-10-01 06:28:01 |
| tests/test_encode_mode.py | tt | tests/test_encode_mode.py | 2026-10-01 06:28:01 |
| tests/test_engine_determinism.py | tt | tests/test_engine_determinism.py | 2026-10-01 06:28:01 |
| tests/test_hetero_write.py | serve | tests/test_hetero_write.py | 2026-10-01 06:28:01 |
| tests/test_k03_instrument.py | ih | tests/test_k03_instrument.py | 2026-09-12 09:15:21 |
| tests/test_k11_binding.py | tt | tests/test_k11_binding.py | 2026-10-01 06:28:01 |
| tests/test_k11_encode_mode.py | tt | tests/test_k11_encode_mode.py | 2026-10-01 06:28:01 |
| tests/test_k11_prune_off.py | k11p | tests/test_k11_prune_off.py | 2026-09-13 02:28:33 |
| tests/test_k11_restricted_donors.py | k11rd | tests/test_k11_restricted_donors.py | 2026-09-13 14:44:03 |
| tests/test_k822_rules.py | rs | tests/test_k822_rules.py | 2026-10-01 06:28:01 |
| tests/test_results_record.py | tt | tests/test_results_record.py | 2026-10-01 06:28:01 |
| tests/test_rules.py | tt | tests/test_rules.py | 2026-10-01 06:28:01 |
| tests/test_s10_gated.py | gated | tests/test_s10_gated.py | 2026-09-13 00:47:05 |
| tests/test_scaling_hold.py | k03-hold | tests/test_scaling_hold.py | 2026-09-12 07:19:25 |
| tests/test_selective_fixture.py | sw | tests/test_selective_fixture.py | 2026-10-01 06:28:01 |
| tests/test_server_clients.py | tt | tests/test_server_clients.py | 2026-10-01 06:28:01 |
| tests/test_session_commands.py | tt | tests/test_session_commands.py | 2026-10-01 06:28:01 |
| tests/test_stim_bookkeeping.py | tt | tests/test_stim_bookkeeping.py | 2026-10-01 06:28:01 |
| tests/test_triplet.py | rs | tests/test_triplet.py | 2026-10-01 06:28:01 |
| tests/test_ui_truth.py | tt | tests/test_ui_truth.py | 2026-10-02 00:24:43 |
| tools/sync_serve.sh | tt | tools/sync_serve.sh | 2026-10-02 00:24:43 |
| ui/app.js | rs | ui/app.js | 2026-10-02 00:24:43 |
| ui/evidence.js | tt | ui/evidence.js | 2026-10-02 00:24:43 |
| ui/index.html | rs | ui/index.html | 2026-10-02 00:24:43 |
| ui/stage0_results.json | tt | ui/stage0_results.json | 2026-10-02 00:24:43 |
| ui/stage1_results.json | rs | ui/stage1_results.json | 2026-10-02 00:24:43 |
| ui/style.css | tt | ui/style.css | 2026-10-02 00:24:43 |

Kept from clone: `brainsim/inhib.py`, `brainsim/worker.py`, `tests/k816_hetero_write.py`, `tests/k817_inh_homeostat.py`, `tests/k826_learned.py`, `tests/k828_override.py`, `tests/test_inh_homeostat.py`, `tests/test_k11_window_on_w.py`, `tests/test_kill_stage0.py`

## Same-minute variants (differ from the chosen copy, mtime within 60 s)

Stored as `docs/recovery/variants/<worktree>/<path>`.

- none

## Truncated / unparsable `.py`

- none

## Junk (misidentified, not committed)

- pend `tools/served-media.test.ts.alt1` 53184326 B: NUL bytes (binary/misidentified)
- pend `tools/served-media.test.ts` 53184326 B: NUL bytes (binary/misidentified)
- pend `tools/validate.test.ts` 191 B: content is JSON/shell, not TypeScript (misidentified)
- pend `tools/public-url.test.ts` 1081 B: content is JSON/shell, not TypeScript (misidentified)
- pend `tools/unsubscribe.ts` 60417480 B: NUL bytes (binary/misidentified)
- pend `tools/payment-mail.ts` 3022 B: content is JSON/shell, not TypeScript (misidentified)
- pend `tools/payment-mail.test.ts` 400 B: content is JSON/shell, not TypeScript (misidentified)
- s1 `SPEC.md` 105064 B: NUL bytes (binary/misidentified)

## Files per worktree

### asd

- `SPEC.md` 2026-10-01 21:10:00 393818 B

### diag (deficit-diag)

- `SPEC.md` 2026-10-01 05:45:08 296051 B
- `tests/k818_drive_loss.py` 2026-10-01 05:14:24 10093 B
- `tests/k819_homeostat_ablation.py` 2026-10-01 05:26:59 16124 B
- `tests/k820_rule_eval.py` 2026-10-01 05:41:32 14414 B

### encode-mode

- `SPEC.md` 2026-09-13 18:10:10 201144 B

### eta

- `SPEC.md` 2026-10-01 22:53:19 423371 B

### gated

- `SPEC.md` 2026-09-13 00:48:15 115734 B
- `brainsim/params.py` 2026-09-13 00:26:10 1589 B
- `tests/s10_gated.py` 2026-09-13 00:47:05 9371 B
- `tests/test_s10_gated.py` 2026-09-13 00:47:05 18088 B

### gen2 (gen2)

- `tests/k826_learned.py` 2026-10-01 16:36:58 9278 B

### head

- `SPEC.md` 2026-10-01 22:50:07 419154 B

### hw

- `brainsim/params.py` 2026-09-30 23:51:32 2466 B
- `brainsim/worker.py` 2026-10-01 03:41:05 10735 B

### ih

- `SPEC.md` 2026-09-12 09:48:46 94534 B
- `brainsim/engine.py` 2026-09-12 09:38:26 23370 B
- `tests/k013_onset.py` 2026-09-12 09:26:37 29004 B
- `tests/k03_brief_volley.py` 2026-09-12 09:15:21 18597 B
- `tests/k03_pairing.py` 2026-09-12 09:20:21 36872 B
- `tests/test_k03_instrument.py` 2026-09-12 09:15:21 6830 B
- `tests/test_results_record.py` 2026-09-12 09:15:21 2751 B

### inh

- `SPEC.md` 2026-10-01 05:06:55 272116 B
- `brainsim/engine.py` 2026-10-01 05:12:49 32996 B
- `brainsim/engine.py.alt1` 2026-10-01 05:12:49 32996 B
- `brainsim/inhib.py` 2026-10-01 05:12:49 584 B
- `brainsim/inhib.py.alt1` 2026-10-01 05:12:49 584 B
- `brainsim/params.py` 2026-10-01 05:12:49 2747 B
- `brainsim/params.py.alt1` 2026-10-01 05:12:49 2747 B
- `tests/k817_inh_homeostat.py` 2026-10-01 04:57:35 14170 B
- `tests/test_inh_homeostat.py` 2026-10-01 05:12:49 13889 B
- `tests/test_inh_homeostat.py.alt1` 2026-10-01 05:12:49 13889 B

### jb

(empty: only `__pycache__`/cache files or nothing survived)

### jc (joint-confirm)

- `SPEC.md` 2026-10-01 23:25:05 459269 B

### k03-hold

- `tests/test_scaling_hold.py` 2026-09-12 07:19:25 15834 B
- `ui/evidence.js` 2026-09-12 07:05:36 20458 B
- `ui/index.html` 2026-09-12 07:05:36 9901 B
- `ui/stage0_results.json` 2026-09-12 07:05:36 31310 B
- `ui/style.css` 2026-09-12 07:05:36 16113 B

### k11ew

(empty: only `__pycache__`/cache files or nothing survived)

### k11ltp

- `SPEC.md` 2026-09-13 04:48:39 143329 B
- `brainsim/engine.py` 2026-09-13 04:30:08 22560 B
- `tests/test_engine_determinism.py` 2026-09-13 04:30:08 1925 B
- `tests/test_engine_determinism.py.alt1` 2026-09-13 04:30:08 1925 B

### k11o

(empty: only `__pycache__`/cache files or nothing survived)

### k11p

- `brainsim/engine.py` 2026-09-13 02:30:46 22819 B
- `brainsim/params.py` 2026-09-13 02:30:35 1574 B
- `tests/k11_binding.py` 2026-09-13 02:40:41 23944 B
- `tests/test_k11_prune_off.py` 2026-09-13 02:28:33 10419 B

### k11rd

- `SPEC.md` 2026-09-13 14:49:21 169809 B
- `tests/test_k11_restricted_donors.py` 2026-09-13 14:44:03 13352 B
- `ui/app.js` 2026-09-13 14:34:41 72757 B
- `ui/app.js.alt1` 2026-09-13 14:34:41 72757 B
- `ui/app.js.alt2` 2026-09-13 14:34:41 72757 B
- `ui/index.html` 2026-09-13 14:34:41 15180 B
- `ui/index.html.alt1` 2026-09-13 14:34:41 15180 B
- `ui/style.css` 2026-09-13 14:34:41 19072 B
- `ui/style.css.alt1` 2026-09-13 14:34:41 19072 B

### k11rw

- `SPEC.md` 2026-09-13 14:25:19 168865 B
- `brainsim/engine.py` 2026-09-13 14:34:41 22964 B
- `brainsim/engine.py.alt1` 2026-09-13 14:34:41 22964 B

### k11wm

- `SPEC.md` 2026-09-13 15:28:46 174393 B
- `brainsim/params.py` 2026-09-13 15:08:23 1505 B
- `brainsim/params.py.alt1` 2026-09-13 15:08:23 1505 B
- `brainsim/params.py.alt2` 2026-09-13 15:08:23 1505 B
- `brainsim/telemetry.py` 2026-09-13 15:08:23 6742 B
- `brainsim/telemetry.py.alt1` 2026-09-13 15:08:23 6742 B
- `brainsim/telemetry.py.alt2` 2026-09-13 15:08:23 6742 B
- `brainsim/worker.py` 2026-09-13 15:08:23 9493 B
- `brainsim/worker.py.alt1` 2026-09-13 15:08:23 9493 B
- `brainsim/worker.py.alt2` 2026-09-13 15:08:23 9493 B
- `brainsim/worker.py.alt3` 2026-09-13 15:08:23 9493 B

### k11ww

- `SPEC.md` 2026-09-13 15:53:35 182788 B

### oj

(empty: only `__pycache__`/cache files or nothing survived)

### pd (persist-dual)

- `SPEC.md` 2026-10-02 00:33:08 473131 B
- `tests/k848_persist_dual.py` 2026-10-02 00:25:44 13002 B

### pend (pending-express)

- `tools/payment-mail.test.ts` 2026-10-01 19:04:19 400 B **JUNK: content is JSON/shell, not TypeScript (misidentified)**
- `tools/payment-mail.ts` 2026-10-01 19:04:19 3022 B **JUNK: content is JSON/shell, not TypeScript (misidentified)**
- `tools/public-url.test.ts` 2026-10-01 19:04:26 1081 B **JUNK: content is JSON/shell, not TypeScript (misidentified)**
- `tools/served-media.test.ts` 2026-10-01 19:04:35 53184326 B **JUNK: NUL bytes (binary/misidentified)**
- `tools/served-media.test.ts.alt1` 2026-10-01 19:04:35 53184326 B **JUNK: NUL bytes (binary/misidentified)**
- `tools/unsubscribe.ts` 2026-10-01 19:04:55 60417480 B **JUNK: NUL bytes (binary/misidentified)**
- `tools/validate.test.ts` 2026-10-01 19:04:48 191 B **JUNK: content is JSON/shell, not TypeScript (misidentified)**

### pw

- `SPEC.md` 2026-09-30 23:20:41 209020 B

### rec

(empty: only `__pycache__`/cache files or nothing survived)

### rep

- `SPEC.md` 2026-10-01 23:18:44 448827 B
- `brainsim/engine.py` 2026-10-02 00:24:43 36118 B
- `brainsim/engine.py.alt1` 2026-10-02 00:24:43 36118 B
- `brainsim/engine.py.alt2` 2026-10-02 00:24:43 36118 B
- `brainsim/hetero.py` 2026-10-02 00:24:43 1054 B
- `brainsim/hetero.py.alt1` 2026-10-02 00:24:43 1054 B
- `brainsim/hetero.py.alt2` 2026-10-02 00:24:43 1054 B
- `brainsim/params.py` 2026-10-02 00:24:43 4719 B
- `brainsim/params.py.alt1` 2026-10-02 00:24:43 4719 B

### rof

- `SPEC.md` 2026-10-01 22:23:05 394906 B

### rs

- `SPEC.md` 2026-10-01 06:26:28 319895 B
- `brainsim/params.py` 2026-10-01 06:28:01 2774 B
- `brainsim/params.py.alt1` 2026-10-01 06:28:01 2774 B
- `brainsim/params.py.alt2` 2026-10-01 06:28:01 2774 B
- `tests/js/evidence.test.mjs` 2026-10-01 22:20:39 12920 B
- `tests/js/evidence.test.mjs.alt1` 2026-10-01 22:20:39 12920 B
- `tests/js/evidence.test.mjs.alt2` 2026-10-01 22:20:39 12920 B
- `tests/js/evidence.test.mjs.alt3` 2026-10-01 22:20:39 12920 B
- `tests/js/evidence.test.mjs.alt4` 2026-10-01 22:20:39 12920 B
- `tests/js/evidence.test.mjs.alt5` 2026-10-01 22:20:39 12920 B
- `tests/js/evidence.test.mjs.alt6` 2026-10-01 22:20:39 12920 B
- `tests/js/evidence.test.mjs.alt7` 2026-10-01 22:20:39 12920 B
- `tests/js/evidence.test.mjs.alt8` 2026-10-01 22:20:39 12920 B
- `tests/k822_frozen_readout.py` 2026-10-01 06:28:01 8381 B
- `tests/k822_frozen_readout.py.alt1` 2026-10-01 06:28:01 8381 B
- `tests/k822_rule_screen.py` 2026-10-01 06:28:01 20529 B
- `tests/k822_rule_screen.py.alt1` 2026-10-01 06:28:01 20529 B
- `tests/k822_rules.py` 2026-10-01 06:28:01 1964 B
- `tests/k822_rules.py.alt1` 2026-10-01 06:28:01 1964 B
- `tests/test_k822_rules.py` 2026-10-01 06:28:01 6294 B
- `tests/test_k822_rules.py.alt1` 2026-10-01 06:28:01 6294 B
- `tests/test_triplet.py` 2026-10-01 06:28:01 18037 B
- `tests/test_triplet.py.alt1` 2026-10-01 06:28:01 18037 B
- `tests/test_triplet.py.alt2` 2026-10-01 06:28:01 18037 B
- `ui/app.js` 2026-10-02 00:24:43 77949 B
- `ui/app.js.alt1` 2026-10-02 00:24:43 77949 B
- `ui/app.js.alt2` 2026-10-02 00:24:43 77949 B
- `ui/app.js.alt3` 2026-10-02 00:24:43 77949 B
- `ui/app.js.alt4` 2026-10-02 00:24:43 77949 B
- `ui/app.js.alt5` 2026-10-02 00:24:43 77949 B
- `ui/index.html` 2026-10-02 00:24:43 16965 B
- `ui/index.html.alt1` 2026-10-02 00:24:43 16965 B
- `ui/index.html.alt2` 2026-10-02 00:24:43 16965 B
- `ui/index.html.alt3` 2026-10-02 00:24:43 16965 B
- `ui/index.html.alt4` 2026-10-02 00:24:43 16965 B
- `ui/index.html.alt5` 2026-10-02 00:24:43 16965 B
- `ui/stage1_results.json` 2026-10-02 00:24:43 16496 B
- `ui/stage1_results.json.alt1` 2026-10-02 00:24:43 16496 B
- `ui/stage1_results.json.alt2` 2026-10-02 00:24:43 16496 B
- `ui/stage1_results.json.alt3` 2026-10-02 00:24:43 16496 B

### s1

- `SPEC.md` 2026-09-12 20:01:28 105064 B **JUNK: NUL bytes (binary/misidentified)**
- `brainsim/net.py` 2026-09-12 19:45:52 7209 B
- `tests/k03_pairing.py` 2026-09-12 19:47:18 39521 B

### seat

- `SPEC.md` 2026-10-01 22:35:07 404230 B
- `brainsim/params.py` 2026-10-01 22:50:54 4406 B
- `brainsim/params.py.alt1` 2026-10-01 22:50:54 4406 B
- `brainsim/params.py.alt2` 2026-10-01 22:50:54 4406 B
- `brainsim/params.py.alt3` 2026-10-01 22:50:54 4406 B
- `brainsim/telemetry.py` 2026-10-01 23:16:04 7467 B
- `brainsim/telemetry.py.alt1` 2026-10-01 23:16:04 7467 B
- `brainsim/telemetry.py.alt2` 2026-10-01 23:16:04 7467 B
- `brainsim/telemetry.py.alt3` 2026-10-01 23:16:04 7467 B
- `brainsim/telemetry.py.alt4` 2026-10-01 23:16:04 7467 B
- `brainsim/telemetry.py.alt5` 2026-10-01 23:16:04 7467 B
- `brainsim/telemetry.py.alt6` 2026-10-01 23:16:04 7467 B
- `brainsim/telemetry.py.alt7` 2026-10-01 23:16:04 7467 B
- `brainsim/telemetry.py.alt8` 2026-10-01 23:16:04 7467 B
- `brainsim/telemetry.py.alt9` 2026-10-01 23:16:04 7467 B
- `brainsim/telemetry.py.alt10` 2026-10-01 23:16:04 7467 B
- `brainsim/triplet.py` 2026-10-01 23:16:04 567 B
- `brainsim/triplet.py.alt1` 2026-10-01 23:16:04 567 B
- `brainsim/triplet.py.alt2` 2026-10-01 23:16:04 567 B
- `brainsim/triplet.py.alt3` 2026-10-01 23:16:04 567 B
- `brainsim/triplet.py.alt4` 2026-10-01 23:16:04 567 B
- `brainsim/triplet.py.alt5` 2026-10-01 23:16:04 567 B
- `brainsim/triplet.py.alt6` 2026-10-01 23:16:04 567 B
- `brainsim/worker.py` 2026-10-01 23:16:04 10858 B
- `brainsim/worker.py.alt1` 2026-10-01 23:16:04 10858 B
- `brainsim/worker.py.alt2` 2026-10-01 23:16:04 10858 B
- `brainsim/worker.py.alt3` 2026-10-01 23:16:04 10858 B
- `brainsim/worker.py.alt4` 2026-10-01 23:16:04 10858 B
- `brainsim/worker.py.alt5` 2026-10-01 23:16:04 10858 B
- `brainsim/worker.py.alt6` 2026-10-01 23:16:04 10858 B
- `brainsim/worker.py.alt7` 2026-10-01 23:16:04 10858 B
- `brainsim/worker.py.alt8` 2026-10-01 23:16:04 10858 B

### serve

- `SPEC.md` 2026-10-02 00:56:06 498646 B
- `brainsim/engine.py` 2026-10-01 04:37:10 30811 B
- `brainsim/engine.py.alt1` 2026-10-01 04:37:10 30811 B
- `brainsim/net.py` 2026-10-01 05:12:49 7011 B
- `brainsim/net.py.alt1` 2026-10-01 05:12:49 7011 B
- `brainsim/net.py.alt2` 2026-10-01 05:12:49 7011 B
- `brainsim/net.py.alt3` 2026-10-01 05:12:49 7011 B
- `brainsim/net.py.alt4` 2026-10-01 05:12:49 7011 B
- `brainsim/net.py.alt5` 2026-10-01 05:12:49 7011 B
- `brainsim/net.py.alt6` 2026-10-01 05:12:49 7011 B
- `tests/js/ui_helpers.test.mjs` 2026-10-01 22:20:39 12284 B
- `tests/js/ui_helpers.test.mjs.alt1` 2026-10-01 22:20:39 12284 B
- `tests/js/ui_helpers.test.mjs.alt2` 2026-10-01 22:20:39 12284 B
- `tests/js/ui_helpers.test.mjs.alt3` 2026-10-01 22:20:39 12284 B
- `tests/js/ui_helpers.test.mjs.alt4` 2026-10-01 22:20:39 12284 B
- `tests/js/ui_helpers.test.mjs.alt5` 2026-10-01 22:20:39 12284 B
- `tests/js/ui_helpers.test.mjs.alt6` 2026-10-01 22:20:39 12284 B
- `tests/js/ui_helpers.test.mjs.alt7` 2026-10-01 22:20:39 12284 B
- `tests/k013_onset.py` 2026-10-01 22:20:39 28045 B
- `tests/k013_onset.py.alt1` 2026-10-01 22:20:39 28045 B
- `tests/k013_onset.py.alt2` 2026-10-01 22:20:39 28045 B
- `tests/k013_onset.py.alt3` 2026-10-01 22:20:39 28045 B
- `tests/k013_onset.py.alt4` 2026-10-01 22:20:39 28045 B
- `tests/k013_onset.py.alt5` 2026-10-01 22:20:39 28045 B
- `tests/k013_onset.py.alt6` 2026-10-01 22:20:39 28045 B
- `tests/k013_onset.py.alt7` 2026-10-01 22:20:39 28045 B
- `tests/k815_slot_reuse.py` 2026-10-01 06:28:01 5761 B
- `tests/k815_slot_reuse.py.alt1` 2026-10-01 06:28:01 5761 B
- `tests/k815_slot_reuse.py.alt2` 2026-10-01 06:28:01 5761 B
- `tests/k815_slot_reuse.py.alt3` 2026-10-01 06:28:01 5761 B
- `tests/k815_slot_reuse.py.alt4` 2026-10-01 06:28:01 5761 B
- `tests/k816_hetero_write.py` 2026-10-01 06:28:01 10284 B
- `tests/k816_hetero_write.py.alt1` 2026-10-01 06:28:01 10284 B
- `tests/k816_hetero_write.py.alt2` 2026-10-01 06:28:01 10284 B
- `tests/k816_hetero_write.py.alt3` 2026-10-01 06:28:01 10284 B
- `tests/k816_hetero_write.py.alt4` 2026-10-01 06:28:01 10284 B
- `tests/k816_hetero_write.py.alt5` 2026-10-01 06:28:01 10284 B
- `tests/test_hetero_write.py` 2026-10-01 06:28:01 19464 B
- `tests/test_hetero_write.py.alt1` 2026-10-01 06:28:01 19464 B
- `tests/test_hetero_write.py.alt2` 2026-10-01 06:28:01 19464 B
- `tests/test_hetero_write.py.alt3` 2026-10-01 06:28:01 19464 B
- `tests/test_hetero_write.py.alt4` 2026-10-01 06:28:01 19464 B
- `tests/test_hetero_write.py.alt5` 2026-10-01 06:28:01 19464 B
- `tests/test_hetero_write.py.alt6` 2026-10-01 06:28:01 19464 B

### shi

- `SPEC.md` 2026-10-01 21:15:50 398759 B
- `brainsim/engine.py` 2026-10-01 22:50:54 35506 B
- `brainsim/engine.py.alt1` 2026-10-01 22:50:54 35506 B
- `brainsim/engine.py.alt2` 2026-10-01 22:50:54 35506 B
- `brainsim/engine.py.alt3` 2026-10-01 22:50:54 35506 B
- `brainsim/engine.py.alt4` 2026-10-01 22:50:54 35506 B

### sw

- `.gitignore` 2026-10-02 00:24:43 41 B
- `.gitignore.alt1` 2026-10-02 00:24:43 41 B
- `.gitignore.alt2` 2026-10-02 00:24:43 41 B
- `.gitignore.alt3` 2026-10-02 00:24:43 41 B
- `.gitignore.alt4` 2026-10-02 00:24:43 41 B
- `.gitignore.alt5` 2026-10-02 00:24:43 41 B
- `.gitignore.alt6` 2026-10-02 00:24:43 41 B
- `.gitignore.alt7` 2026-10-02 00:24:43 41 B
- `.gitignore.alt8` 2026-10-02 00:24:43 41 B
- `.gitignore.alt9` 2026-10-02 00:24:43 41 B
- `.gitignore.alt10` 2026-10-02 00:24:43 41 B
- `.gitignore.alt11` 2026-10-02 00:24:43 41 B
- `.gitignore.alt12` 2026-10-02 00:24:43 41 B
- `.gitignore.alt13` 2026-10-02 00:24:43 41 B
- `.gitignore.alt14` 2026-10-02 00:24:43 41 B
- `.gitignore.alt15` 2026-10-02 00:24:43 41 B
- `.gitignore.alt16` 2026-10-02 00:24:43 41 B
- `.gitignore.alt17` 2026-10-02 00:24:43 41 B
- `.gitignore.alt18` 2026-10-02 00:24:43 41 B
- `.gitignore.alt19` 2026-10-02 00:24:43 41 B
- `.gitignore.alt20` 2026-10-02 00:24:43 41 B
- `.gitignore.alt21` 2026-10-02 00:24:43 41 B
- `.gitignore.alt22` 2026-10-02 00:24:43 41 B
- `.gitignore.alt23` 2026-10-02 00:24:43 41 B
- `.gitignore.alt24` 2026-10-02 00:24:43 41 B
- `.gitignore.alt25` 2026-10-02 00:24:43 41 B
- `SPEC.md` 2026-09-30 23:44:50 209820 B
- `tests/k11_never_trained.py` 2026-10-01 22:20:39 8134 B
- `tests/k11_never_trained.py.alt1` 2026-10-01 22:20:39 8134 B
- `tests/k11_never_trained.py.alt2` 2026-10-01 22:20:39 8134 B
- `tests/k11_never_trained.py.alt3` 2026-10-01 22:20:39 8134 B
- `tests/k11_never_trained.py.alt4` 2026-10-01 22:20:39 8134 B
- `tests/k11_never_trained.py.alt5` 2026-10-01 22:20:39 8134 B
- `tests/k11_never_trained.py.alt6` 2026-10-01 22:20:39 8134 B
- `tests/k11_never_trained.py.alt7` 2026-10-01 22:20:39 8134 B
- `tests/k815_selective_write.py` 2026-10-01 22:20:39 13891 B
- `tests/k815_selective_write.py.alt1` 2026-10-01 22:20:39 13891 B
- `tests/k815_selective_write.py.alt2` 2026-10-01 22:20:39 13891 B
- `tests/k815_selective_write.py.alt3` 2026-10-01 22:20:39 13891 B
- `tests/k815_selective_write.py.alt4` 2026-10-01 22:20:39 13891 B
- `tests/k815_selective_write.py.alt5` 2026-10-01 22:20:39 13891 B
- `tests/k815_selective_write.py.alt6` 2026-10-01 22:20:39 13891 B
- `tests/test_selective_fixture.py` 2026-10-01 06:28:01 7978 B
- `tests/test_selective_fixture.py.alt1` 2026-10-01 06:28:01 7978 B
- `tests/test_selective_fixture.py.alt2` 2026-10-01 06:28:01 7978 B
- `tests/test_selective_fixture.py.alt3` 2026-10-01 06:28:01 7978 B
- `tests/test_selective_fixture.py.alt4` 2026-10-01 06:28:01 7978 B
- `tests/test_selective_fixture.py.alt5` 2026-10-01 06:28:01 7978 B
- `tests/test_selective_fixture.py.alt6` 2026-10-01 06:28:01 7978 B

### tt

- `SPEC.md` 2026-09-30 22:17:30 210050 B
- `brainsim/encode.py` 2026-09-30 22:15:36 7116 B
- `brainsim/engine.py` 2026-09-30 22:11:52 29543 B
- `brainsim/net.py` 2026-09-30 22:11:52 7222 B
- `brainsim/params.py` 2026-09-30 22:11:52 2267 B
- `brainsim/telemetry.py` 2026-09-30 22:11:52 7422 B
- `brainsim/worker.py` 2026-09-30 22:11:52 10633 B
- `mockups/index.html` 2026-10-01 23:16:04 103321 B
- `mockups/index.html.alt1` 2026-10-01 23:16:04 103321 B
- `mockups/index.html.alt2` 2026-10-01 23:16:04 103321 B
- `mockups/index.html.alt3` 2026-10-01 23:16:04 103321 B
- `mockups/index.html.alt4` 2026-10-01 23:16:04 103321 B
- `mockups/index.html.alt5` 2026-10-01 23:16:04 103321 B
- `mockups/index.html.alt6` 2026-10-01 23:16:04 103321 B
- `mockups/index.html.alt7` 2026-10-01 23:16:04 103321 B
- `mockups/index.html.alt8` 2026-10-01 23:16:04 103321 B
- `mockups/index.html.alt9` 2026-10-01 23:16:04 103321 B
- `mockups/index.html.alt10` 2026-10-01 23:16:04 103321 B
- `mockups/index.html.alt11` 2026-10-01 23:16:04 103321 B
- `mockups/index.html.alt12` 2026-10-01 23:16:04 103321 B
- `pytest.ini` 2026-10-01 22:20:39 24 B
- `pytest.ini.alt1` 2026-10-01 22:20:39 24 B
- `pytest.ini.alt2` 2026-10-01 22:20:39 24 B
- `pytest.ini.alt3` 2026-10-01 22:20:39 24 B
- `pytest.ini.alt4` 2026-10-01 22:20:39 24 B
- `pytest.ini.alt5` 2026-10-01 22:20:39 24 B
- `pytest.ini.alt6` 2026-10-01 22:20:39 24 B
- `pytest.ini.alt7` 2026-10-01 22:20:39 24 B
- `pytest.ini.alt8` 2026-10-01 22:20:39 24 B
- `pytest.ini.alt9` 2026-10-01 22:20:39 24 B
- `requirements.txt` 2026-10-01 22:20:39 79 B
- `requirements.txt.alt1` 2026-10-01 22:20:39 79 B
- `requirements.txt.alt2` 2026-10-01 22:20:39 79 B
- `requirements.txt.alt3` 2026-10-01 22:20:39 79 B
- `requirements.txt.alt4` 2026-10-01 22:20:39 79 B
- `requirements.txt.alt5` 2026-10-01 22:20:39 79 B
- `requirements.txt.alt6` 2026-10-01 22:20:39 79 B
- `requirements.txt.alt7` 2026-10-01 22:20:39 79 B
- `requirements.txt.alt8` 2026-10-01 22:20:39 79 B
- `requirements.txt.alt9` 2026-10-01 22:20:39 79 B
- `run.py` 2026-10-01 22:20:39 667 B
- `run.py.alt1` 2026-10-01 22:20:39 667 B
- `run.py.alt2` 2026-10-01 22:20:39 667 B
- `run.py.alt3` 2026-10-01 22:20:39 667 B
- `run.py.alt4` 2026-10-01 22:20:39 667 B
- `run.py.alt5` 2026-10-01 22:20:39 667 B
- `run.py.alt6` 2026-10-01 22:20:39 667 B
- `run.py.alt7` 2026-10-01 22:20:39 667 B
- `run.py.alt8` 2026-10-01 22:20:39 667 B
- `server/app.py` 2026-10-01 22:20:39 2421 B
- `server/app.py.alt1` 2026-10-01 22:20:39 2421 B
- `server/app.py.alt2` 2026-10-01 22:20:39 2421 B
- `server/app.py.alt3` 2026-10-01 22:20:39 2421 B
- `server/app.py.alt4` 2026-10-01 22:20:39 2421 B
- `server/app.py.alt5` 2026-10-01 22:20:39 2421 B
- `server/app.py.alt6` 2026-10-01 22:20:39 2421 B
- `server/app.py.alt7` 2026-10-01 22:20:39 2421 B
- `tests/conftest.py` 2026-10-01 22:20:39 889 B
- `tests/conftest.py.alt1` 2026-10-01 22:20:39 889 B
- `tests/conftest.py.alt2` 2026-10-01 22:20:39 889 B
- `tests/conftest.py.alt3` 2026-10-01 22:20:39 889 B
- `tests/conftest.py.alt4` 2026-10-01 22:20:39 889 B
- `tests/conftest.py.alt5` 2026-10-01 22:20:39 889 B
- `tests/conftest.py.alt6` 2026-10-01 22:20:39 889 B
- `tests/conftest.py.alt7` 2026-10-01 22:20:39 889 B
- `tests/k03_brief_volley.py` 2026-10-01 22:20:39 19173 B
- `tests/k03_brief_volley.py.alt1` 2026-10-01 22:20:39 19173 B
- `tests/k03_brief_volley.py.alt2` 2026-10-01 22:20:39 19173 B
- `tests/k03_brief_volley.py.alt3` 2026-10-01 22:20:39 19173 B
- `tests/k03_brief_volley.py.alt4` 2026-10-01 22:20:39 19173 B
- `tests/k03_brief_volley.py.alt5` 2026-10-01 22:20:39 19173 B
- `tests/k03_brief_volley.py.alt6` 2026-10-01 22:20:39 19173 B
- `tests/k03_brief_volley.py.alt7` 2026-10-01 22:20:39 19173 B
- `tests/k03_brief_volley.py.alt8` 2026-10-01 22:20:39 19173 B
- `tests/k03_pairing.py` 2026-10-01 22:20:39 38228 B
- `tests/k03_pairing.py.alt1` 2026-10-01 22:20:39 38228 B
- `tests/k03_pairing.py.alt2` 2026-10-01 22:20:39 38228 B
- `tests/k03_pairing.py.alt3` 2026-10-01 22:20:39 38228 B
- `tests/k03_pairing.py.alt4` 2026-10-01 22:20:39 38228 B
- `tests/k03_pairing.py.alt5` 2026-10-01 22:20:39 38228 B
- `tests/k03_pairing.py.alt6` 2026-10-01 22:20:39 38228 B
- `tests/k11_binding.py` 2026-10-01 22:20:39 39202 B
- `tests/k11_binding.py.alt1` 2026-10-01 22:20:39 39202 B
- `tests/k11_binding.py.alt2` 2026-10-01 22:20:39 39202 B
- `tests/k11_binding.py.alt3` 2026-10-01 22:20:39 39202 B
- `tests/k11_binding.py.alt4` 2026-10-01 22:20:39 39202 B
- `tests/k11_binding.py.alt5` 2026-10-01 22:20:39 39202 B
- `tests/k11_binding.py.alt6` 2026-10-01 22:20:39 39202 B
- `tests/k11_binding.py.alt7` 2026-10-01 22:20:39 39202 B
- `tests/test_client_evidence.py` 2026-10-01 06:28:01 1084 B
- `tests/test_client_evidence.py.alt1` 2026-10-01 06:28:01 1084 B
- `tests/test_client_evidence.py.alt2` 2026-10-01 06:28:01 1084 B
- `tests/test_client_evidence.py.alt3` 2026-10-01 06:28:01 1084 B
- `tests/test_client_evidence.py.alt4` 2026-10-01 06:28:01 1084 B
- `tests/test_client_evidence.py.alt5` 2026-10-01 06:28:01 1084 B
- `tests/test_client_evidence.py.alt6` 2026-10-01 06:28:01 1084 B
- `tests/test_encode_mode.py` 2026-10-01 06:28:01 21674 B
- `tests/test_encode_mode.py.alt1` 2026-10-01 06:28:01 21674 B
- `tests/test_encode_mode.py.alt2` 2026-10-01 06:28:01 21674 B
- `tests/test_encode_mode.py.alt3` 2026-10-01 06:28:01 21674 B
- `tests/test_encode_mode.py.alt4` 2026-10-01 06:28:01 21674 B
- `tests/test_encode_mode.py.alt5` 2026-10-01 06:28:01 21674 B
- `tests/test_encode_mode.py.alt6` 2026-10-01 06:28:01 21674 B
- `tests/test_encode_mode.py.alt7` 2026-10-01 06:28:01 21674 B
- `tests/test_engine_determinism.py` 2026-10-01 06:28:01 2966 B
- `tests/test_engine_determinism.py.alt1` 2026-10-01 06:28:01 2966 B
- `tests/test_engine_determinism.py.alt2` 2026-10-01 06:28:01 2966 B
- `tests/test_engine_determinism.py.alt3` 2026-10-01 06:28:01 2966 B
- `tests/test_engine_determinism.py.alt4` 2026-10-01 06:28:01 2966 B
- `tests/test_engine_determinism.py.alt5` 2026-10-01 06:28:01 2966 B
- `tests/test_engine_determinism.py.alt6` 2026-10-01 06:28:01 2966 B
- `tests/test_k11_binding.py` 2026-10-01 06:28:01 11707 B
- `tests/test_k11_binding.py.alt1` 2026-10-01 06:28:01 11707 B
- `tests/test_k11_binding.py.alt2` 2026-10-01 06:28:01 11707 B
- `tests/test_k11_binding.py.alt3` 2026-10-01 06:28:01 11707 B
- `tests/test_k11_binding.py.alt4` 2026-10-01 06:28:01 11707 B
- `tests/test_k11_binding.py.alt5` 2026-10-01 06:28:01 11707 B
- `tests/test_k11_binding.py.alt6` 2026-10-01 06:28:01 11707 B
- `tests/test_k11_binding.py.alt7` 2026-10-01 06:28:01 11707 B
- `tests/test_k11_encode_mode.py` 2026-10-01 06:28:01 7735 B
- `tests/test_k11_encode_mode.py.alt1` 2026-10-01 06:28:01 7735 B
- `tests/test_k11_encode_mode.py.alt2` 2026-10-01 06:28:01 7735 B
- `tests/test_k11_encode_mode.py.alt3` 2026-10-01 06:28:01 7735 B
- `tests/test_k11_encode_mode.py.alt4` 2026-10-01 06:28:01 7735 B
- `tests/test_k11_encode_mode.py.alt5` 2026-10-01 06:28:01 7735 B
- `tests/test_k11_encode_mode.py.alt6` 2026-10-01 06:28:01 7735 B
- `tests/test_k11_encode_mode.py.alt7` 2026-10-01 06:28:01 7735 B
- `tests/test_kill_stage0.py` 2026-10-01 06:28:01 11268 B
- `tests/test_kill_stage0.py.alt1` 2026-10-01 06:28:01 11268 B
- `tests/test_kill_stage0.py.alt2` 2026-10-01 06:28:01 11268 B
- `tests/test_kill_stage0.py.alt3` 2026-10-01 06:28:01 11268 B
- `tests/test_kill_stage0.py.alt4` 2026-10-01 06:28:01 11268 B
- `tests/test_kill_stage0.py.alt5` 2026-10-01 06:28:01 11268 B
- `tests/test_kill_stage0.py.alt6` 2026-10-01 06:28:01 11268 B
- `tests/test_kill_stage0.py.alt7` 2026-10-01 06:28:01 11268 B
- `tests/test_results_record.py` 2026-10-01 06:28:01 5708 B
- `tests/test_results_record.py.alt1` 2026-10-01 06:28:01 5708 B
- `tests/test_results_record.py.alt2` 2026-10-01 06:28:01 5708 B
- `tests/test_results_record.py.alt3` 2026-10-01 06:28:01 5708 B
- `tests/test_results_record.py.alt4` 2026-10-01 06:28:01 5708 B
- `tests/test_results_record.py.alt5` 2026-10-01 06:28:01 5708 B
- `tests/test_results_record.py.alt6` 2026-10-01 06:28:01 5708 B
- `tests/test_rules.py` 2026-10-01 06:28:01 26378 B
- `tests/test_rules.py.alt1` 2026-10-01 06:28:01 26378 B
- `tests/test_rules.py.alt2` 2026-10-01 06:28:01 26378 B
- `tests/test_rules.py.alt3` 2026-10-01 06:28:01 26378 B
- `tests/test_rules.py.alt4` 2026-10-01 06:28:01 26378 B
- `tests/test_rules.py.alt5` 2026-10-01 06:28:01 26378 B
- `tests/test_rules.py.alt6` 2026-10-01 06:28:01 26378 B
- `tests/test_rules.py.alt7` 2026-10-01 06:28:01 26378 B
- `tests/test_server_clients.py` 2026-10-01 06:28:01 6402 B
- `tests/test_server_clients.py.alt1` 2026-10-01 06:28:01 6402 B
- `tests/test_server_clients.py.alt2` 2026-10-01 06:28:01 6402 B
- `tests/test_server_clients.py.alt3` 2026-10-01 06:28:01 6402 B
- `tests/test_server_clients.py.alt4` 2026-10-01 06:28:01 6402 B
- `tests/test_server_clients.py.alt5` 2026-10-01 06:28:01 6402 B
- `tests/test_server_clients.py.alt6` 2026-10-01 06:28:01 6402 B
- `tests/test_server_clients.py.alt7` 2026-10-01 06:28:01 6402 B
- `tests/test_session_commands.py` 2026-10-01 06:28:01 7647 B
- `tests/test_session_commands.py.alt1` 2026-10-01 06:28:01 7647 B
- `tests/test_session_commands.py.alt2` 2026-10-01 06:28:01 7647 B
- `tests/test_session_commands.py.alt3` 2026-10-01 06:28:01 7647 B
- `tests/test_session_commands.py.alt4` 2026-10-01 06:28:01 7647 B
- `tests/test_session_commands.py.alt5` 2026-10-01 06:28:01 7647 B
- `tests/test_session_commands.py.alt6` 2026-10-01 06:28:01 7647 B
- `tests/test_session_commands.py.alt7` 2026-10-01 06:28:01 7647 B
- `tests/test_stim_bookkeeping.py` 2026-10-01 06:28:01 7227 B
- `tests/test_stim_bookkeeping.py.alt1` 2026-10-01 06:28:01 7227 B
- `tests/test_stim_bookkeeping.py.alt2` 2026-10-01 06:28:01 7227 B
- `tests/test_stim_bookkeeping.py.alt3` 2026-10-01 06:28:01 7227 B
- `tests/test_stim_bookkeeping.py.alt4` 2026-10-01 06:28:01 7227 B
- `tests/test_stim_bookkeeping.py.alt5` 2026-10-01 06:28:01 7227 B
- `tests/test_stim_bookkeeping.py.alt6` 2026-10-01 06:28:01 7227 B
- `tests/test_stim_bookkeeping.py.alt7` 2026-10-01 06:28:01 7227 B
- `tests/test_ui_truth.py` 2026-10-02 00:24:43 4344 B
- `tests/test_ui_truth.py.alt1` 2026-10-02 00:24:43 4344 B
- `tests/test_ui_truth.py.alt2` 2026-10-02 00:24:43 4344 B
- `tests/test_ui_truth.py.alt3` 2026-10-02 00:24:43 4344 B
- `tests/test_ui_truth.py.alt4` 2026-10-02 00:24:43 4344 B
- `tests/test_ui_truth.py.alt5` 2026-10-02 00:24:43 4344 B
- `tests/test_ui_truth.py.alt6` 2026-10-02 00:24:43 4344 B
- `tests/test_ui_truth.py.alt7` 2026-10-02 00:24:43 4344 B
- `tests/test_ui_truth.py.alt8` 2026-10-02 00:24:43 4344 B
- `tools/sync_serve.sh` 2026-10-02 00:24:43 2180 B
- `tools/sync_serve.sh.alt1` 2026-10-02 00:24:43 2180 B
- `tools/sync_serve.sh.alt2` 2026-10-02 00:24:43 2180 B
- `tools/sync_serve.sh.alt3` 2026-10-02 00:24:43 2180 B
- `tools/sync_serve.sh.alt4` 2026-10-02 00:24:43 2180 B
- `tools/sync_serve.sh.alt5` 2026-10-02 00:24:43 2180 B
- `tools/sync_serve.sh.alt6` 2026-10-02 00:24:43 2180 B
- `tools/sync_serve.sh.alt7` 2026-10-02 00:24:43 2180 B
- `tools/sync_serve.sh.alt8` 2026-10-02 00:24:43 2180 B
- `tools/sync_serve.sh.alt9` 2026-10-02 00:24:43 2180 B
- `tools/sync_serve.sh.alt10` 2026-10-02 00:24:43 2180 B
- `ui/app.js` 2026-09-30 22:13:01 77584 B
- `ui/evidence.js` 2026-10-02 00:24:43 24349 B
- `ui/evidence.js.alt1` 2026-10-02 00:24:43 24349 B
- `ui/evidence.js.alt2` 2026-10-02 00:24:43 24349 B
- `ui/evidence.js.alt3` 2026-10-02 00:24:43 24349 B
- `ui/evidence.js.alt4` 2026-10-02 00:24:43 24349 B
- `ui/evidence.js.alt5` 2026-10-02 00:24:43 24349 B
- `ui/evidence.js.alt6` 2026-10-02 00:24:43 24349 B
- `ui/evidence.js.alt7` 2026-10-02 00:24:43 24349 B
- `ui/evidence.js.alt8` 2026-10-02 00:24:43 24349 B
- `ui/evidence.js.alt9` 2026-10-02 00:24:43 24349 B
- `ui/index.html` 2026-09-30 22:12:56 16285 B
- `ui/stage0_results.json` 2026-10-02 00:24:43 28033 B
- `ui/stage0_results.json.alt1` 2026-10-02 00:24:43 28033 B
- `ui/stage0_results.json.alt2` 2026-10-02 00:24:43 28033 B
- `ui/stage0_results.json.alt3` 2026-10-02 00:24:43 28033 B
- `ui/stage0_results.json.alt4` 2026-10-02 00:24:43 28033 B
- `ui/stage0_results.json.alt5` 2026-10-02 00:24:43 28033 B
- `ui/stage0_results.json.alt6` 2026-10-02 00:24:43 28033 B
- `ui/stage0_results.json.alt7` 2026-10-02 00:24:43 28033 B
- `ui/stage0_results.json.alt8` 2026-10-02 00:24:43 28033 B
- `ui/stage1_results.json` 2026-09-30 22:09:49 2813 B
- `ui/stage1_results.json.alt1` 2026-09-30 22:09:49 2813 B
- `ui/stage1_results.json.alt2` 2026-09-30 22:09:49 2813 B
- `ui/style.css` 2026-10-02 00:24:43 19510 B
- `ui/style.css.alt1` 2026-10-02 00:24:43 19510 B
- `ui/style.css.alt2` 2026-10-02 00:24:43 19510 B
- `ui/style.css.alt3` 2026-10-02 00:24:43 19510 B
- `ui/style.css.alt4` 2026-10-02 00:24:43 19510 B
- `ui/style.css.alt5` 2026-10-02 00:24:43 19510 B
- `ui/style.css.alt6` 2026-10-02 00:24:43 19510 B

### zs

(empty: only `__pycache__`/cache files or nothing survived)
