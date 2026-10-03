# Carved brain-sim commit log (2026-10-03)

Every commit object carved from the deleted `.git` (bare repo `/mnt/sdcard/rebuilt/git-objects.git` on the recovery SD card) whose root tree contains `brainsim/`. 12 commits, sorted by committer date. For each: hash, author and committer dates, parents (and whether the parent object was carved), the full message, and every file the commit's tree lists with whether that blob was carved ("recovered") or lost. A file listed as recovered here is the version at that commit; the newest recovered version of each path is what `from-git/brain-sim/` materialised.

## 44a6a84a — 2026-09-13 15:19 UTC

- Commit: `44a6a84a79d42fa72b6359d07624a6796416c1a3`
- Author date: 2026-09-13 15:19:07 UTC (-0500)
- Committer date: 2026-09-13 15:19:07 UTC
- Parent: `4374ea6edd416b1cc9986235e2984be36026e5fc` (not carved)

```
K1.1 driver: labelled proxy "encode window on W only" (SPEC 8.9) on the 8.6 parent: ids on hpc_encode_window, identify_W (ID pass on a discarded deep copy under the default plant), W on sparse_cofire_write with W_source/real_top_k/overlap/donor_ids, W pins (mask_W_frac, a_minus_W, mask_hpc_e_not_W_frac, a_minus_hpc_e_not_W) folded into validity, window_on_w mode with guard, donor_to_W/other_ctx_e_to_W/hpc_hpc_within_W groups, --window-on-w flag. Engine untouched

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016BBQ2yyxkmvahFytndu5o4
```

Tree lists 35 entries; 1 blobs recovered, 34 lost.

| Path | Blob | Recovered |
|---|---|---|
| `.gitignore` | `965717a8d5` | no |
| `SPEC.md` | `f717d088ed` | no |
| `brainsim/ (tree object missing)` | `42585790dc` | no |
| `mockups/ (tree object missing)` | `2c58647adf` | no |
| `pytest.ini` | `a635c5c031` | no |
| `requirements.txt` | `4e94d2fda8` | no |
| `run.py` | `9af0f43f0e` | no |
| `server/ (tree object missing)` | `552f64ddb1` | no |
| `tests/conftest.py` | `1d464bb499` | no |
| `tests/js/ (tree object missing)` | `54d38f4c1c` | no |
| `tests/k013_onset.py` | `e2a0e4643b` | no |
| `tests/k03_brief_volley.py` | `d272115ccc` | no |
| `tests/k03_pairing.py` | `c6f781397b` | no |
| `tests/k11_binding.py` | `869aeb0f9c` | no |
| `tests/test_client_evidence.py` | `92d4c1d8b2` | no |
| `tests/test_engine_determinism.py` | `c5010b8b3d` | no |
| `tests/test_k03_instrument.py` | `a91f5f3783` | no |
| `tests/test_k11_binding.py` | `f0259ec899` | no |
| `tests/test_k11_encode_window.py` | `ccbd8cb481` | no |
| `tests/test_k11_sparse_write.py` | `6d73512e21` | no |
| `tests/test_k11_window_on_w.py` | `f767149448` | yes |
| `tests/test_kill_stage0.py` | `7d4019dc43` | no |
| `tests/test_results_record.py` | `f49dac54ab` | no |
| `tests/test_rules.py` | `3888793261` | no |
| `tests/test_server_clients.py` | `0fcfd3b63d` | no |
| `tests/test_session_commands.py` | `86c3885a7c` | no |
| `tests/test_stim_bookkeeping.py` | `d5e7f8283c` | no |
| `tests/test_ui_truth.py` | `d59eacc506` | no |
| `tools/ (tree object missing)` | `2a13108404` | no |
| `ui/app.js` | `ae7a806cc6` | no |
| `ui/evidence.js` | `c9e96e5ee0` | no |
| `ui/index.html` | `d851695044` | no |
| `ui/stage0_results.json` | `a00d7d0567` | no |
| `ui/stage1_results.json` | `ba6fc5296f` | no |
| `ui/style.css` | `8120c2169d` | no |

## 873a2c00 — 2026-10-01 04:50 UTC

- Commit: `873a2c001bba341c5d2fa0dec30efc1ceff7a683`
- Author date: 2026-10-01 04:50:27 UTC (-0500)
- Committer date: 2026-10-01 04:50:27 UTC
- Parent: `176d64c39eddad8b3b8a1a7d534aa97c2d913697` (carved)

```
SPEC 8.17 contract: inhibition as the hpc rate controller (Vogels inhibitory STDP in place of excitatory scaling and rate-driven elimination on hpc E), run together with the heterosynaptic write; kill test T5 with numbers fixed before any code; owner lifted the inhibitory-plasticity exclusion for this experiment

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: 08148fe4-5307-40f5-91b6-c865eff566f8
```

Tree lists 23 entries; 3 blobs recovered, 20 lost.

| Path | Blob | Recovered |
|---|---|---|
| `.gitignore` | `965717a8d5` | no |
| `SPEC.md` | `e7493e1797` | yes |
| `brainsim/__init__.py` | `c7cf194658` | no |
| `brainsim/encode.py` | `c91e744fc4` | no |
| `brainsim/engine.py` | `6cc75b35f5` | no |
| `brainsim/hetero.py` | `0d9854bf06` | no |
| `brainsim/net.py` | `619ed21132` | no |
| `brainsim/params.py` | `a971964bcd` | yes |
| `brainsim/telemetry.py` | `16986c08e6` | no |
| `brainsim/worker.py` | `dd4114e28c` | yes |
| `mockups/ (tree object missing)` | `2c58647adf` | no |
| `pytest.ini` | `a635c5c031` | no |
| `requirements.txt` | `4e94d2fda8` | no |
| `run.py` | `9af0f43f0e` | no |
| `server/ (tree object missing)` | `552f64ddb1` | no |
| `tests/ (tree object missing)` | `87058e6773` | no |
| `tools/ (tree object missing)` | `2a13108404` | no |
| `ui/app.js` | `56f37c4af0` | no |
| `ui/evidence.js` | `c9e96e5ee0` | no |
| `ui/index.html` | `be8ad0f263` | no |
| `ui/stage0_results.json` | `a00d7d0567` | no |
| `ui/stage1_results.json` | `927ee4cf66` | no |
| `ui/style.css` | `3e1b0749de` | no |

## 3adb30ea — 2026-10-01 05:06 UTC

- Commit: `3adb30eaa06aebb1c2dc8ec88ad4863fceb194a0`
- Author date: 2026-10-01 05:06:56 UTC (-0500)
- Committer date: 2026-10-01 05:06:56 UTC
- Parent: `888f60c3e4b9a81dfd34580c62609a90b2057999` (carved)

```
SPEC 8.17 result: REJECTED on c3 on seeds 1, 2 and 3 and on V2 on seed 1. The written contrast persists as amplitude (x0.83 through sleep and B against x0.17 on the default plant) but the trained cells answer A less than the never-trained ones (2/5/5 against 12/14/7); the inhibitory rule at this rate barely moves and hpc E sits at about half its target. Reviews recorded. Not merged

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: 08148fe4-5307-40f5-91b6-c865eff566f8
```

Tree lists 50 entries; 8 blobs recovered, 42 lost.

| Path | Blob | Recovered |
|---|---|---|
| `.gitignore` | `965717a8d5` | no |
| `SPEC.md` | `4a05d34402` | yes |
| `brainsim/__init__.py` | `c7cf194658` | no |
| `brainsim/encode.py` | `c91e744fc4` | no |
| `brainsim/engine.py` | `9975f9972b` | yes |
| `brainsim/hetero.py` | `0d9854bf06` | no |
| `brainsim/inhib.py` | `d178bba839` | yes |
| `brainsim/net.py` | `619ed21132` | no |
| `brainsim/params.py` | `029a158308` | yes |
| `brainsim/telemetry.py` | `16986c08e6` | no |
| `brainsim/worker.py` | `dd4114e28c` | yes |
| `mockups/ (tree object missing)` | `2c58647adf` | no |
| `pytest.ini` | `a635c5c031` | no |
| `requirements.txt` | `4e94d2fda8` | no |
| `run.py` | `9af0f43f0e` | no |
| `server/ (tree object missing)` | `552f64ddb1` | no |
| `tests/conftest.py` | `1d464bb499` | no |
| `tests/js/ (tree object missing)` | `54d38f4c1c` | no |
| `tests/k013_onset.py` | `e2a0e4643b` | no |
| `tests/k03_brief_volley.py` | `d272115ccc` | no |
| `tests/k03_pairing.py` | `c6f781397b` | no |
| `tests/k11_binding.py` | `790e6ccdd1` | no |
| `tests/k11_never_trained.py` | `b4e92110eb` | no |
| `tests/k815_selective_write.py` | `4b9daea93e` | no |
| `tests/k815_slot_reuse.py` | `dd94140da0` | no |
| `tests/k816_hetero_write.py` | `587891508e` | yes |
| `tests/k817_inh_homeostat.py` | `5f9478b8d5` | yes |
| `tests/test_client_evidence.py` | `92d4c1d8b2` | no |
| `tests/test_encode_mode.py` | `90d07b3430` | no |
| `tests/test_engine_determinism.py` | `dfa45f4a7d` | no |
| `tests/test_hetero_write.py` | `ce7609163b` | no |
| `tests/test_inh_homeostat.py` | `7aa739dca4` | yes |
| `tests/test_k03_instrument.py` | `a91f5f3783` | no |
| `tests/test_k11_binding.py` | `f0259ec899` | no |
| `tests/test_k11_encode_mode.py` | `5c2723d210` | no |
| `tests/test_kill_stage0.py` | `7d4019dc43` | no |
| `tests/test_results_record.py` | `f49dac54ab` | no |
| `tests/test_rules.py` | `3888793261` | no |
| `tests/test_selective_fixture.py` | `28b827db8d` | no |
| `tests/test_server_clients.py` | `0fcfd3b63d` | no |
| `tests/test_session_commands.py` | `86c3885a7c` | no |
| `tests/test_stim_bookkeeping.py` | `d5e7f8283c` | no |
| `tests/test_ui_truth.py` | `d59eacc506` | no |
| `tools/ (tree object missing)` | `2a13108404` | no |
| `ui/app.js` | `56f37c4af0` | no |
| `ui/evidence.js` | `c9e96e5ee0` | no |
| `ui/index.html` | `be8ad0f263` | no |
| `ui/stage0_results.json` | `a00d7d0567` | no |
| `ui/stage1_results.json` | `927ee4cf66` | no |
| `ui/style.css` | `3e1b0749de` | no |

## 5dbf34fd — 2026-10-01 05:12 UTC

- Commit: `5dbf34fdefc392d4d6bbb3e8ba35b95084df83dc`
- Author date: 2026-10-01 05:12:49 UTC (-0500)
- Committer date: 2026-10-01 05:12:49 UTC
- Parent: `3adb30eaa06aebb1c2dc8ec88ad4863fceb194a0` (carved)

```
SPEC 8.18 contract: a diagnostic of the 8.17 readout loss (where the excitatory drive onto the trained cells goes after A is presented); no mechanism, no engine change, no bar beyond reproducing T5's recorded arms

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GSRYDQcA8XBjUn2p5tj95P
```

Tree lists 50 entries; 7 blobs recovered, 43 lost.

| Path | Blob | Recovered |
|---|---|---|
| `.gitignore` | `965717a8d5` | no |
| `SPEC.md` | `7dc9cd3413` | no |
| `brainsim/__init__.py` | `c7cf194658` | no |
| `brainsim/encode.py` | `c91e744fc4` | no |
| `brainsim/engine.py` | `9975f9972b` | yes |
| `brainsim/hetero.py` | `0d9854bf06` | no |
| `brainsim/inhib.py` | `d178bba839` | yes |
| `brainsim/net.py` | `619ed21132` | no |
| `brainsim/params.py` | `029a158308` | yes |
| `brainsim/telemetry.py` | `16986c08e6` | no |
| `brainsim/worker.py` | `dd4114e28c` | yes |
| `mockups/ (tree object missing)` | `2c58647adf` | no |
| `pytest.ini` | `a635c5c031` | no |
| `requirements.txt` | `4e94d2fda8` | no |
| `run.py` | `9af0f43f0e` | no |
| `server/ (tree object missing)` | `552f64ddb1` | no |
| `tests/conftest.py` | `1d464bb499` | no |
| `tests/js/ (tree object missing)` | `54d38f4c1c` | no |
| `tests/k013_onset.py` | `e2a0e4643b` | no |
| `tests/k03_brief_volley.py` | `d272115ccc` | no |
| `tests/k03_pairing.py` | `c6f781397b` | no |
| `tests/k11_binding.py` | `790e6ccdd1` | no |
| `tests/k11_never_trained.py` | `b4e92110eb` | no |
| `tests/k815_selective_write.py` | `4b9daea93e` | no |
| `tests/k815_slot_reuse.py` | `dd94140da0` | no |
| `tests/k816_hetero_write.py` | `587891508e` | yes |
| `tests/k817_inh_homeostat.py` | `5f9478b8d5` | yes |
| `tests/test_client_evidence.py` | `92d4c1d8b2` | no |
| `tests/test_encode_mode.py` | `90d07b3430` | no |
| `tests/test_engine_determinism.py` | `dfa45f4a7d` | no |
| `tests/test_hetero_write.py` | `ce7609163b` | no |
| `tests/test_inh_homeostat.py` | `7aa739dca4` | yes |
| `tests/test_k03_instrument.py` | `a91f5f3783` | no |
| `tests/test_k11_binding.py` | `f0259ec899` | no |
| `tests/test_k11_encode_mode.py` | `5c2723d210` | no |
| `tests/test_kill_stage0.py` | `7d4019dc43` | no |
| `tests/test_results_record.py` | `f49dac54ab` | no |
| `tests/test_rules.py` | `3888793261` | no |
| `tests/test_selective_fixture.py` | `28b827db8d` | no |
| `tests/test_server_clients.py` | `0fcfd3b63d` | no |
| `tests/test_session_commands.py` | `86c3885a7c` | no |
| `tests/test_stim_bookkeeping.py` | `d5e7f8283c` | no |
| `tests/test_ui_truth.py` | `d59eacc506` | no |
| `tools/ (tree object missing)` | `2a13108404` | no |
| `ui/app.js` | `56f37c4af0` | no |
| `ui/evidence.js` | `c9e96e5ee0` | no |
| `ui/index.html` | `be8ad0f263` | no |
| `ui/stage0_results.json` | `a00d7d0567` | no |
| `ui/stage1_results.json` | `927ee4cf66` | no |
| `ui/style.css` | `3e1b0749de` | no |

## c1690030 — 2026-10-01 05:28 UTC

- Commit: `c16900306017e2813a234ad5a74e76bcdd48f076`
- Author date: 2026-10-01 05:28:03 UTC (-0500)
- Committer date: 2026-10-01 05:28:03 UTC
- Parent: `8fdf4bc705e105b6f15f93cf4dcf15a3277b7458` (not carved)

```
SPEC 8.19 driver tests/k819_homeostat_ablation.py: per-engine parameter overrides (asserted to take effect and to leave C0 bit-identical), probes by deep copy, decision-rule clauses printed per condition. No engine change

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GSRYDQcA8XBjUn2p5tj95P
```

Tree lists 24 entries; 5 blobs recovered, 19 lost.

| Path | Blob | Recovered |
|---|---|---|
| `.gitignore` | `965717a8d5` | no |
| `SPEC.md` | `21f8eda197` | yes |
| `brainsim/__init__.py` | `c7cf194658` | no |
| `brainsim/encode.py` | `c91e744fc4` | no |
| `brainsim/engine.py` | `9975f9972b` | yes |
| `brainsim/hetero.py` | `0d9854bf06` | no |
| `brainsim/inhib.py` | `d178bba839` | yes |
| `brainsim/net.py` | `619ed21132` | no |
| `brainsim/params.py` | `029a158308` | yes |
| `brainsim/telemetry.py` | `16986c08e6` | no |
| `brainsim/worker.py` | `dd4114e28c` | yes |
| `mockups/ (tree object missing)` | `2c58647adf` | no |
| `pytest.ini` | `a635c5c031` | no |
| `requirements.txt` | `4e94d2fda8` | no |
| `run.py` | `9af0f43f0e` | no |
| `server/ (tree object missing)` | `552f64ddb1` | no |
| `tests/ (tree object missing)` | `d0d2102336` | no |
| `tools/ (tree object missing)` | `2a13108404` | no |
| `ui/app.js` | `56f37c4af0` | no |
| `ui/evidence.js` | `c9e96e5ee0` | no |
| `ui/index.html` | `be8ad0f263` | no |
| `ui/stage0_results.json` | `a00d7d0567` | no |
| `ui/stage1_results.json` | `927ee4cf66` | no |
| `ui/style.css` | `3e1b0749de` | no |

## 647865d9 — 2026-10-01 05:37 UTC

- Commit: `647865d99739c96e1f9238e5195044b4e62ee123`
- Author date: 2026-10-01 05:37:19 UTC (-0500)
- Committer date: 2026-10-01 05:37:19 UTC
- Parent: `c16900306017e2813a234ad5a74e76bcdd48f076` (carved)

```
SPEC 8.19 result: VALID; no condition eligible on all three seeds, C3 (no rate-driven rewiring, scaling ten times slower) removes most of the suppression and stays in band to 300,000 but misses narrowly on seed 3. Main finding: even so the trained cells do not answer more than untrained ones, because on this plant the pair rule weakens co-active synapses that sit above 0.45 w_max

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GSRYDQcA8XBjUn2p5tj95P
```

Tree lists 24 entries; 4 blobs recovered, 20 lost.

| Path | Blob | Recovered |
|---|---|---|
| `.gitignore` | `965717a8d5` | no |
| `SPEC.md` | `865abd9f7a` | no |
| `brainsim/__init__.py` | `c7cf194658` | no |
| `brainsim/encode.py` | `c91e744fc4` | no |
| `brainsim/engine.py` | `9975f9972b` | yes |
| `brainsim/hetero.py` | `0d9854bf06` | no |
| `brainsim/inhib.py` | `d178bba839` | yes |
| `brainsim/net.py` | `619ed21132` | no |
| `brainsim/params.py` | `029a158308` | yes |
| `brainsim/telemetry.py` | `16986c08e6` | no |
| `brainsim/worker.py` | `dd4114e28c` | yes |
| `mockups/ (tree object missing)` | `2c58647adf` | no |
| `pytest.ini` | `a635c5c031` | no |
| `requirements.txt` | `4e94d2fda8` | no |
| `run.py` | `9af0f43f0e` | no |
| `server/ (tree object missing)` | `552f64ddb1` | no |
| `tests/ (tree object missing)` | `d0d2102336` | no |
| `tools/ (tree object missing)` | `2a13108404` | no |
| `ui/app.js` | `56f37c4af0` | no |
| `ui/evidence.js` | `c9e96e5ee0` | no |
| `ui/index.html` | `be8ad0f263` | no |
| `ui/stage0_results.json` | `a00d7d0567` | no |
| `ui/stage1_results.json` | `927ee4cf66` | no |
| `ui/style.css` | `3e1b0749de` | no |

## d227dd87 — 2026-10-01 17:10 UTC

- Commit: `d227dd875746a185a85feef76207d407bbfadc0e`
- Author date: 2026-10-01 17:10:16 UTC (-0500)
- Committer date: 2026-10-01 17:10:16 UTC
- Parent: `5c87af50a05f449d307d295661aff43191259d75` (not carved)

```
Record SPEC 8.27 (synapse-class transplant on gen2) from the unmerged branch deficit-diag: valid on three seeds; the pair-rule training deficit lives in the cortical E synapses onto W, which training weakens from about 0.92 to 0.70 of the bound. A diagnostic pass, not recall; K1.1 remains FAIL. Stage 1 record: entry 8.27. No engine or UI code change on master

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GSRYDQcA8XBjUn2p5tj95P
```

Tree lists 23 entries; 3 blobs recovered, 20 lost.

| Path | Blob | Recovered |
|---|---|---|
| `.gitignore` | `965717a8d5` | no |
| `SPEC.md` | `b4decde61c` | yes |
| `brainsim/__init__.py` | `c7cf194658` | no |
| `brainsim/encode.py` | `c91e744fc4` | no |
| `brainsim/engine.py` | `6cc75b35f5` | no |
| `brainsim/hetero.py` | `0d9854bf06` | no |
| `brainsim/net.py` | `619ed21132` | no |
| `brainsim/params.py` | `a971964bcd` | yes |
| `brainsim/telemetry.py` | `16986c08e6` | no |
| `brainsim/worker.py` | `dd4114e28c` | yes |
| `mockups/ (tree object missing)` | `2c58647adf` | no |
| `pytest.ini` | `a635c5c031` | no |
| `requirements.txt` | `4e94d2fda8` | no |
| `run.py` | `9af0f43f0e` | no |
| `server/ (tree object missing)` | `552f64ddb1` | no |
| `tests/ (tree object missing)` | `87058e6773` | no |
| `tools/ (tree object missing)` | `2a13108404` | no |
| `ui/app.js` | `56f37c4af0` | no |
| `ui/evidence.js` | `c9e96e5ee0` | no |
| `ui/index.html` | `be8ad0f263` | no |
| `ui/stage0_results.json` | `a00d7d0567` | no |
| `ui/stage1_results.json` | `1c01ec40a8` | no |
| `ui/style.css` | `3e1b0749de` | no |

## 3aac95b5 — 2026-10-01 17:46 UTC

- Commit: `3aac95b5529461c19ce87f5a48b9cffd013b31a2`
- Author date: 2026-10-01 17:46:24 UTC (-0500)
- Committer date: 2026-10-01 17:46:24 UTC
- Parent: `7e42c6c57d7e7f4d73d9693fc6e4e09adb2bc6bb` (carved)

```
SPEC 8.28: plateau-override proxy driver tests/k828_override.py

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GSRYDQcA8XBjUn2p5tj95P
```

Tree lists 48 entries; 5 blobs recovered, 43 lost.

| Path | Blob | Recovered |
|---|---|---|
| `.gitignore` | `965717a8d5` | no |
| `SPEC.md` | `f4abff01b6` | yes |
| `brainsim/ (tree object missing)` | `62bde9aaa6` | no |
| `mockups/ (tree object missing)` | `2c58647adf` | no |
| `pytest.ini` | `a635c5c031` | no |
| `requirements.txt` | `4e94d2fda8` | no |
| `run.py` | `9af0f43f0e` | no |
| `server/ (tree object missing)` | `552f64ddb1` | no |
| `tests/conftest.py` | `1d464bb499` | no |
| `tests/js/ (tree object missing)` | `54d38f4c1c` | no |
| `tests/k013_onset.py` | `e2a0e4643b` | no |
| `tests/k03_brief_volley.py` | `d272115ccc` | no |
| `tests/k03_pairing.py` | `c6f781397b` | no |
| `tests/k11_binding.py` | `790e6ccdd1` | no |
| `tests/k11_never_trained.py` | `b4e92110eb` | no |
| `tests/k815_selective_write.py` | `4b9daea93e` | no |
| `tests/k815_slot_reuse.py` | `dd94140da0` | no |
| `tests/k816_hetero_write.py` | `587891508e` | yes |
| `tests/k821_helpers.py` | `ab5771d840` | no |
| `tests/k821_triplet.py` | `986936d581` | no |
| `tests/k822_frozen_readout.py` | `83e02a5de1` | no |
| `tests/k822_rule_screen.py` | `0b8c0a1ade` | no |
| `tests/k822_rules.py` | `da27d02419` | no |
| `tests/k823_ceiling.py` | `e07246d972` | no |
| `tests/k824_whatif.py` | `1febd69f57` | no |
| `tests/k826_learned.py` | `4458f01ae5` | yes |
| `tests/k827_transplant.py` | `c9913a0a5f` | no |
| `tests/k828_override.py` | `2b2033b488` | yes |
| `tests/test_client_evidence.py` | `92d4c1d8b2` | no |
| `tests/test_encode_mode.py` | `90d07b3430` | no |
| `tests/test_engine_determinism.py` | `dfa45f4a7d` | no |
| `tests/test_gen2_profile.py` | `0b3a50aae0` | no |
| `tests/test_hetero_write.py` | `ce7609163b` | no |
| `tests/test_k03_instrument.py` | `a91f5f3783` | no |
| `tests/test_k11_binding.py` | `f0259ec899` | no |
| `tests/test_k11_encode_mode.py` | `5c2723d210` | no |
| `tests/test_k822_rules.py` | `428c95d41f` | no |
| `tests/test_kill_stage0.py` | `64c45f0982` | yes |
| `tests/test_results_record.py` | `f49dac54ab` | no |
| `tests/test_rules.py` | `3888793261` | no |
| `tests/test_selective_fixture.py` | `28b827db8d` | no |
| `tests/test_server_clients.py` | `0fcfd3b63d` | no |
| `tests/test_session_commands.py` | `86c3885a7c` | no |
| `tests/test_stim_bookkeeping.py` | `d5e7f8283c` | no |
| `tests/test_triplet.py` | `f378630d3c` | no |
| `tests/test_ui_truth.py` | `d59eacc506` | no |
| `tools/ (tree object missing)` | `2a13108404` | no |
| `ui/ (tree object missing)` | `42ab2f8f1a` | no |

## 67c8ddd0 — 2026-10-01 17:58 UTC

- Commit: `67c8ddd06070412e48837d4ff9e6d89ba3dce4aa`
- Author date: 2026-10-01 17:58:26 UTC (-0500)
- Committer date: 2026-10-01 17:58:26 UTC
- Parent: `d227dd875746a185a85feef76207d407bbfadc0e` (carved)

```
Record SPEC 8.28 (plateau override, a labelled test-side proxy on gen2) from the unmerged branch plateau-override: valid and pass on three seeds, trained minus never-trained on the half cue at 50 ticks +7.2 / +8.2 / +8.4 W cells with B and idle not raised. Proxy only; K1.1 remains FAIL. Stage 1 record: entry 8.28. No engine or UI code change on master

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GSRYDQcA8XBjUn2p5tj95P
```

Tree lists 23 entries; 3 blobs recovered, 20 lost.

| Path | Blob | Recovered |
|---|---|---|
| `.gitignore` | `965717a8d5` | no |
| `SPEC.md` | `290c1a74a3` | no |
| `brainsim/__init__.py` | `c7cf194658` | no |
| `brainsim/encode.py` | `c91e744fc4` | no |
| `brainsim/engine.py` | `6cc75b35f5` | no |
| `brainsim/hetero.py` | `0d9854bf06` | no |
| `brainsim/net.py` | `619ed21132` | no |
| `brainsim/params.py` | `a971964bcd` | yes |
| `brainsim/telemetry.py` | `16986c08e6` | no |
| `brainsim/worker.py` | `dd4114e28c` | yes |
| `mockups/ (tree object missing)` | `2c58647adf` | no |
| `pytest.ini` | `a635c5c031` | no |
| `requirements.txt` | `4e94d2fda8` | no |
| `run.py` | `9af0f43f0e` | no |
| `server/ (tree object missing)` | `552f64ddb1` | no |
| `tests/ (tree object missing)` | `87058e6773` | no |
| `tools/ (tree object missing)` | `2a13108404` | no |
| `ui/app.js` | `56f37c4af0` | no |
| `ui/evidence.js` | `c9e96e5ee0` | no |
| `ui/index.html` | `be8ad0f263` | no |
| `ui/stage0_results.json` | `a00d7d0567` | no |
| `ui/stage1_results.json` | `8d08f822dc` | yes |
| `ui/style.css` | `3e1b0749de` | no |

## 9c811c97 — 2026-10-01 23:22 UTC

- Commit: `9c811c974b60ddb189e55641d12399834a6d51e3`
- Author date: 2026-10-01 23:22:56 UTC (-0500)
- Committer date: 2026-10-01 23:22:56 UTC
- Parent: `e1685e879186c85542ffcf0ace8c7002c6cea881` (not carved)

```
SPEC 8.46 contract: rerun the 8.45 passing setting with 96 repeats on seeds 1 to 6, kill test fixed before the runs

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GSRYDQcA8XBjUn2p5tj95P
```

Tree lists 11 entries; 0 blobs recovered, 11 lost.

| Path | Blob | Recovered |
|---|---|---|
| `.gitignore` | `965717a8d5` | no |
| `SPEC.md` | `deb6392da3` | no |
| `brainsim/ (tree object missing)` | `977154dd3c` | no |
| `mockups/ (tree object missing)` | `2c58647adf` | no |
| `pytest.ini` | `a635c5c031` | no |
| `requirements.txt` | `4e94d2fda8` | no |
| `run.py` | `9af0f43f0e` | no |
| `server/ (tree object missing)` | `552f64ddb1` | no |
| `tests/ (tree object missing)` | `f5a9f64b76` | no |
| `tools/ (tree object missing)` | `2a13108404` | no |
| `ui/ (tree object missing)` | `42ab2f8f1a` | no |

## 5f427342 — 2026-10-01 23:27 UTC

- Commit: `5f4273423cb416ea1881e64dfa9ded5166d6e4a7`
- Author date: 2026-10-01 23:27:05 UTC (-0500)
- Committer date: 2026-10-01 23:27:05 UTC
- Parent: `8863d9aba5587f7b8fc1e870c7934967d9d6f8f4` (carved)

```
SPEC 8.47 result: valid on six seeds; K1.1 as coded NOT MET on the 8.46 setting. c1 fails everywhere (assembly 40 to 61), c2 0.72 / 0.57 / 0.86 / 0.92 / 0.78 / 0.90 (met on seeds 3, 4, 6), c3 met everywhere. K1.1 remains FAIL. Not merged

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GSRYDQcA8XBjUn2p5tj95P
```

Tree lists 11 entries; 0 blobs recovered, 11 lost.

| Path | Blob | Recovered |
|---|---|---|
| `.gitignore` | `965717a8d5` | no |
| `SPEC.md` | `cadf9507eb` | no |
| `brainsim/ (tree object missing)` | `977154dd3c` | no |
| `mockups/ (tree object missing)` | `2c58647adf` | no |
| `pytest.ini` | `a635c5c031` | no |
| `requirements.txt` | `4e94d2fda8` | no |
| `run.py` | `9af0f43f0e` | no |
| `server/ (tree object missing)` | `552f64ddb1` | no |
| `tests/ (tree object missing)` | `4b1406bd99` | no |
| `tools/ (tree object missing)` | `2a13108404` | no |
| `ui/ (tree object missing)` | `42ab2f8f1a` | no |

## f9411ab3 — 2026-10-01 23:27 UTC

- Commit: `f9411ab3f07645d84925c9a40eca6cf75ff987f1`
- Author date: 2026-10-01 23:27:05 UTC (-0500)
- Committer date: 2026-10-01 23:27:05 UTC
- Parent: `55a89444bb6f0cbe7944326f6d224baa37853ddb` (not carved)

```
Record SPEC 8.47 (the official K1.1 protocol on the 8.46 setting) from the unmerged branch official-on-joint: NOT MET; assembly 40 to 61 cells against 20 on every seed, completion 0.72 / 0.57 / 0.86 / 0.92 / 0.78 / 0.90 against 0.80, no other assembly on any seed. K1.1 remains FAIL. Stage 1 record: entry 8.47 (fail). No engine or UI code change on master

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GSRYDQcA8XBjUn2p5tj95P
```

Tree lists 23 entries; 2 blobs recovered, 21 lost.

| Path | Blob | Recovered |
|---|---|---|
| `.gitignore` | `965717a8d5` | no |
| `SPEC.md` | `007c087d21` | no |
| `brainsim/__init__.py` | `c7cf194658` | no |
| `brainsim/encode.py` | `c91e744fc4` | no |
| `brainsim/engine.py` | `6cc75b35f5` | no |
| `brainsim/hetero.py` | `0d9854bf06` | no |
| `brainsim/net.py` | `619ed21132` | no |
| `brainsim/params.py` | `a971964bcd` | yes |
| `brainsim/telemetry.py` | `16986c08e6` | no |
| `brainsim/worker.py` | `dd4114e28c` | yes |
| `mockups/ (tree object missing)` | `2c58647adf` | no |
| `pytest.ini` | `a635c5c031` | no |
| `requirements.txt` | `4e94d2fda8` | no |
| `run.py` | `9af0f43f0e` | no |
| `server/ (tree object missing)` | `552f64ddb1` | no |
| `tests/ (tree object missing)` | `87058e6773` | no |
| `tools/ (tree object missing)` | `2a13108404` | no |
| `ui/app.js` | `56f37c4af0` | no |
| `ui/evidence.js` | `c9e96e5ee0` | no |
| `ui/index.html` | `be8ad0f263` | no |
| `ui/stage0_results.json` | `a00d7d0567` | no |
| `ui/stage1_results.json` | `51ae71028f` | no |
| `ui/style.css` | `3e1b0749de` | no |

