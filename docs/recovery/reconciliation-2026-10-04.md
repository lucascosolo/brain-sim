# Plant reconciliation (2026-10-04)

Every plant file in the tree was checked against the blob ids that the 12 carved commits list
(`carved-commit-log-2026-10-03.md`), and against every recovered copy on the storage VPS: the 36
worktrees and the 42 `scratch/brainsim*` folders and files under `named-home/.cache/`, the SD-card rebuild
`sdcard-2026-10-04/rebuilt/Workspaces/brain-sim/`, and 1,381 photorec carves that the recovery
index matched on plant identifiers. A recovered file counts as a given committed version only when
its git blob id equals the one the commit lists. Per-path results:
`reconciliation-2026-10-04.tsv`. Carves that match no known blob: `carve-candidates-2026-10-04.tsv`.

## What changed

**Added, byte-exact (commit 4820805).** Nine paths that carved commits list but no earlier pass
had found: `brainsim/__init__.py` (master f9411ab3, from `~/.cache/scratch/brainsim-pend/old/`),
`tests/k821_helpers.py`, `k821_triplet.py`, `k823_ceiling.py`, `k824_whatif.py`,
`k827_transplant.py`, `test_gen2_profile.py` (3aac95b5), `test_k11_encode_window.py`,
`test_k11_sparse_write.py` (44a6a84a), all from photorec2 carves. Master's byte-exact
`brainsim/{engine,params,hetero,encode,net}.py`, which differ from the tree's branch-line copies,
are kept in `variants/master-f9411ab3/`.

**Replaced (commit 51efe68, revert it alone to undo).**
- `brainsim/net.py`: the tree's `engine.py` is the branch line (worktree rep: triplet, pending
  and hetero flags, all default off) and reads `Network.r1/o1/o2`, which master's `net.py` lacks.
  Replaced with the branch-line `net.py` from `brainsim-pend/old/` (master's plus three zeroed
  trace arrays).
- `ui/stage1_results.json`: the 2026-10-03 merge took worktree rs's copy, entries 8.0-8.20 only.
  Master f9411ab3's copy (blob 51ae71028f) holds those 21 entries unchanged plus 8.21-8.47.

## Why the 2026-10-03 merge picked wrong copies

It kept the newest mtime per path. In the journal recovery, mtimes record checkouts, not edits:
161 recovered files across six worktrees share `2026-10-02 00:24:43`, 142 share
`2026-10-01 06:28:01`, 123 share `2026-10-01 22:20:39`. Order by content instead: commit blob
ids, SPEC entry counts, record entries.

## Test suite, measured 2026-10-04

Plant suite, Python 3.11 venv with numpy 2.4.6 (`~/.cache/brain-sim/venv`), `tests/test_safety_lint.py`
excluded because reflex-layer is not reachable from this session's sandbox.

| tree | passed | failed | skipped |
|---|---|---|---|
| before (e37e735) | 257 | 111 | 1 |
| after (51efe68) | 325 | 77 | 1 |

No test went from pass to fail. `test_triplet.py` went from 43 failures to 0 and the recovered
`test_gen2_profile.py` passes 8/8. The 77 that remain:

- 73 are orphaned branch tests whose code was never merged and is not in the tree:
  `test_k11_window_on_w` 16, `test_s10_gated` 14, `test_k11_restricted_donors` 10,
  `test_inh_homeostat` 9 (8.17, REJECTED), `test_k11_prune_off` 6, `test_scaling_hold` 6,
  `test_k11_encode_window` 5, `test_k11_sparse_write` 4, `test_k03_instrument` 3 (the tree's
  copy is worktree ih's, 2026-09-12; master's blob a91f5f3783 is lost). The k11 proxy branches
  are closed hunts in owner policy, so their code is not to be merged back to make them pass.
- 4 are recorded outcomes, not recovery defects, and fail identically with master's own
  `brainsim/`: K1.1 (`test_k11_binding`, the standing FAIL), K0.1 and K0.4 (`test_kill_stage0`)
  and K0.13 (`test_rules`), listed red on both plants in SPEC 8.26's result, Part 1.

## Still missing

- Six of the twelve committed SPEC.md versions, master's (007c087d21) among them; the tree's
  SPEC.md (worktree serve, tops out at 8.49) has the newest content. Five others are in the
  carved object store (`rebuilt/git-objects.git`), and 67c8ddd0's (290c1a74a3) is in carve
  `photorec2/recup.336/f362884096.kept.txt`.
- `tests/k11_binding.py` at 44a6a84a (869aeb0f9c), `tests/test_k03_instrument.py` at 3aac95b5
  (a91f5f3783), and the contents of every tree object the carve lost (master's `tests/`,
  `server/`, `tools/`, `mockups/`).
- Branch code that never reached a carved commit. `carve-candidates-2026-10-04.tsv` lists 95
  carves with no blob to check them against, among them drivers for SPEC 8.14, 8.29, 8.32 and
  8.34-8.40 and a truncated `k847_official.py`; their paths come from their own docstrings,
  so they are leads, not recovered files. They stay on the storage VPS.
- The recorded results that several drivers and tests read from `~/.cache/scratch/brainsim-*`
  are on the storage VPS under `named-home/.cache/scratch/`; `~/.cache/scratch/` does not exist
  on this PC now.
- `__pycache__/*.pyc` in the worktrees (not used by any pass) record the sources compiled there,
  including `test_gen2_profile` and `k821_helpers`, and could date or identify lost versions.
