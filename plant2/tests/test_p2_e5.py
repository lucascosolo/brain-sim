import copy
import json
from pathlib import Path

import numpy as np
import pytest

from plant2 import record
from plant2.experiments import p2_e1_btsp as e1
from plant2.experiments import p2_e3_completion as e3
from plant2.experiments import p2_e4_online as e4
from plant2.experiments import p2_e5_structured as e5
from plant2.tests.test_p2_e4 import TINY as E4_TINY

# seeds 90+ belong to no experiment
TINY = dict(e5.CONTRACT, m=1500, n=1500, f_q=0.0133, acc_tau=2000, settle=14000, converge_window=2000,
            n_old=20, n_rand=20, n_novel=20, gate_M=(120, 200), n_newex=6, n_proto=4, auc_items=40,
            grid_J=(2.0, 2.8), grid_g=(0.0, 0.3), mean_A_lo=10, mean_A_hi=30, overlap_lo=12.0, overlap_hi=22.0)


def test_contract_constants_are_the_frozen_ones():
    c = e5.CONTRACT
    assert (c["J_fb"], c["g"], c["J"], c["acc_tau"], c["t_cont"]) == (2.80, 0.3, 1.525, 10_000, 50)
    assert (c["s"], c["F"], c["gate_M"]) == (60, 10, (500, 1000))
    assert len(c["grid_J"]) * len(c["grid_g"]) == 72 and 2.8 in c["grid_J"] and 0.3 in c["grid_g"]
    assert c["R_k"] == (2, 3, 4, 6) and c["grid_k"] == 3
    assert (c["n_newex"], c["n_proto"], c["auc_items"]) == (100, 50, 200)
    assert (c["material_frac"], c["margin_frac"], c["worsens_ratio"], c["not_worse_ratio"]) == (0.10, 0.05, 1.25, 1.10)
    assert e5.GATED_SEEDS == (21, 22, 23, 24, 25) and e5.EXPLORE_SEEDS == (44, 45)
    assert e5.CONTRACT_FROZEN_AT == "bc28cd9"
    assert (e5.PROTO, e5.EXEMPLAR, e5.BLOCK_CUES, e5.POOLED, e5.PI) == (20, 21, 22, 23, 24)


def test_generator_follows_the_stream_table():
    c = e5.CONTRACT
    g = e5.FamilyGen(90, c["m"], c["a"], 60, 10)
    r = e1.stream(90, 20, 10)
    P = [np.sort(r.choice(4000, 100, replace=False)) for _ in range(10)]
    assert all(np.array_equal(a, b) for a, b in zip(g.protos, P))
    k = 7
    r = e1.stream(90, 21, 10, k)
    pp = r.permutation(P[k % 10])
    po = r.permutation(np.setdiff1d(np.arange(4000), P[k % 10]))
    assert np.array_equal(g.exemplar(k), np.sort(np.concatenate([pp[:40], po[:60]])))
    with pytest.raises(ValueError):
        g.exemplar(0)
    items = [g.choice(4000, 100, replace=False) for _ in range(300)]
    assert g.fam[:3] == [1, 2, 3] and g.fam[9] == 0 and g.k == 300
    assert all(x.size == 100 and np.unique(x).size == 100 for x in items)
    ov = e5.sibling_overlap(items, g.fam, 300)
    assert 15.5 < ov < 18.5  # about (100 - s)^2 / 100 + chance = 16.9
    # nested kept sets across s (same draws)
    g80 = e5.FamilyGen(90, 4000, 100, 80, 10)
    kept60 = np.intersect1d(g.exemplar(5), g.protos[5])
    kept80 = np.intersect1d(g80.exemplar(5), g80.protos[5])
    assert np.isin(kept80, kept60).all()
    # the pooled control: prototype share from the union, little sibling overlap
    gp = e5.FamilyGen(90, 4000, 100, 60, 10, pooled=True)
    pitems = [gp.choice(4000, 100) for _ in range(300)]
    assert all(np.isin(np.intersect1d(x, gp.union), gp.union).sum() >= 40 for x in pitems)
    assert e5.sibling_overlap(pitems, gp.fam, 300) < 6
    assert json.dumps(g.bit_generator.state)  # P2-E4's state_digest can hash it


def test_block_cues_order_and_families():
    c = dict(e5.CONTRACT, n_newex=12, n_proto=5)
    cues, r = e5.block_cues(c, 91, 500, 10, 60)
    assert [q["kind"] for q in cues] == ["newex"] * 12 + ["proto"] * 5
    assert [q["family"] for q in cues[:12]] == [j % 10 for j in range(12)]
    P = e5.prototypes(91, 4000, 100, 10)
    assert all(np.array_equal(q["item"], P[q["family"]]) for q in cues[12:])
    assert all(q["cue"].size == 50 and np.isin(q["cue"], q["item"]).all() for q in cues)
    cues2, _ = e5.block_cues(c, 91, 500, 10, 60)
    assert all(np.array_equal(a["cue"], b["cue"]) for a, b in zip(cues, cues2))


def _gen(seed, c=TINY):
    return e5.FamilyGen(seed, c["m"], c["a"], 60, 10)


def test_capture_wrapper_changes_nothing():
    a = e5.E5(TINY, 92, _gen(92))
    b = e3.E3(TINY, 92)
    b._pat = _gen(92)
    a.learn(40)
    b.learn(40)
    assert np.array_equal(a.store.keys, b.store.keys) and np.array_equal(a.fb.keys, b.fb.keys)
    assert np.array_equal(a.mem.vbar, b.mem.vbar) and a.net.t == b.net.t
    assert all(np.array_equal(x, y) for x, y in zip(a.R, b.R))
    assert e5.capture_ok(a, 40) and "step" not in vars(a.net)
    assert "step" not in vars(copy.deepcopy(a).net)
    assert all(r.size == 0 or (t >= 0).all() for r, t in zip(a.cont_cells, a.cont_first))
    assert e3.digest(e5.store_from(a, 40, k=1).keys) == e3.digest(a.fb.keys)
    assert sum(x.size for x in a.learn_raster) >= sum(int(c.sum()) for c in a.cont_counts)


def test_online_capture_wrapper_changes_nothing():
    c4 = E4_TINY
    a = e5.OnlineE5(c4, 93, e5.FamilyGen(93, c4["m"], c4["a"], 60, 10))
    b = e4.Online(c4, 93)
    b._pat = e5.FamilyGen(93, c4["m"], c4["a"], 60, 10)
    a.run_to(30)
    b.run_to(30)
    assert e4.state_digest(a) == e4.state_digest(b)
    assert e5.capture_ok(a, 30) and "step" not in vars(a.net)


def test_readout_full_matches_p2e3_readout_and_block_leaves_gated_scores():
    main = e5.E5(TINY, 94, _gen(94))
    main.learn(120)
    T = e5.test_copy(main, 120, e5.block_cues(TINY, 94, 120, 10, 60))
    T0 = e5.test_copy(main, 120, None)
    J, g = np.array([2.8, 2.0]), np.array([0.3, 0.0])
    ref = e3.readout(T0["e"], 120, T0["raster"], T0["n_ticks"], T0["onsets"], J, g)
    got = e5.readout_full(T["e"], 120, T["raster"], T["n_ticks"], T["onsets"], J, g)[0]
    assert json.dumps(ref, sort_keys=True) == json.dumps(got, sort_keys=True)
    assert T["unchanged"] and T["block"]["n_ticks"] > T["n_ticks"] and len(T["block"]["onsets"]) == 10
    # the trace sink: per-cue regenerated line counts equal the replay's totals
    fl = e5.FirstLines(T["onsets"], TINY["rec_window"], T["n_ticks"])
    arms, res, cues = e5.readout_full(T["e"], 120, T["raster"], T["n_ticks"], T["onsets"], J[:1], g[:1], trace=fl)
    assert all(fl.lines(k)[0].size == res["total"][k, 0] for k in range(len(cues)))


def test_n_in_sorted_matches_isin():
    rng = np.random.default_rng(90)
    keys = np.unique(rng.integers(0, 10**6, 50_000))
    for _ in range(20):
        q = np.unique(rng.integers(0, 10**6, 40))
        assert e5.n_in_sorted(q, keys) == int(np.isin(q, keys).sum())
    assert e5.n_in_sorted(np.array([10**7]), keys) == 0 and e5.n_in_sorted(np.empty(0, np.int64), keys) == 0


def test_auc():
    assert e5.auc([5, 5, 4], [1, 1]) == 1.0
    assert e5.auc([1], [1]) == 0.5
    assert e5.auc([2], [1, 3]) == 0.5
    assert e5.auc([0], [3], higher=False) == 1.0


def _gated_rec(seed, vec_ok=True, valid=True):
    v = {k: vec_ok for k in e5.VECTOR_PARTS}
    counts = {k: 190 if vec_ok else 20 for k in e5.VECTOR_PARTS}
    loads = {M: dict(vector=dict(v), counts=dict(counts), per_cue=dict(joint="1" * 200, index="1" * 200)) for M in ("500", "1000")}
    return dict(experiment="P2-E5", kind="kill_test_seed", gated=True, seed=seed, contract_digest=e5.DIGEST, valid=valid,
                vector={M: dict(v) for M in loads}, loads=loads)


def _diag(seed, ub, own, auc=0.999):
    G = lambda best, fro: dict(best_cues=best, frozen_cues=fro)
    L = dict(n_half=200, grid=dict(plateau=G(ub, 185), main=G(own, 20), R3=G(ub, 185)),
             activity=dict(count_auc=auc), contamination=dict(label_permuted=dict(main_spec=0.98, perm_spec=0.05)))
    return dict(experiment="P2-E5", kind="reported_arm", arm="gated_diagnostics", gated=True, seed=seed,
                contract_digest=e5.DIGEST, loads={"500": L, "1000": L})


def _arm(arm, seed, **load):
    return dict(experiment="P2-E5", kind="reported_arm", arm=arm, gated=True, seed=seed, contract_digest=e5.DIGEST,
                loads={M: dict(load) for M in ("500", "1000")})


def test_labels_and_readings_on_synthetic_records():
    seeds = e5.GATED_SEEDS
    recs = [_gated_rec(s, vec_ok=False) for s in seeds]
    recs += [_diag(s, ub=198, own=124) for s in seeds]
    recs += [_arm("s100", s, valid=True, p2e3_gate=True) for s in seeds]
    TA = dict(online=dict(joint=0.06), reference=dict(joint=0.12), plateau=dict(joint=0.93))
    recs += [_arm("online", s, valid=True, ratio=1.8, L_o=dict(loss=29), twin_A=TA) for s in seeds]
    recs += [_arm("pooled", s, valid=True, vector=dict(S2=True), counts=dict(C2=198), plateau_cues=197) for s in seeds]
    out = []
    v = e5.verdict(recs, results_path=record.cache_dir("test-runs") / "p2e5_synthetic_verdict.jsonl", log=out.append)
    assert v["verdict"] == "STRUCTURED INDEX FAIL + STRUCTURED CONTENT FAIL"
    rd = v["readings"]
    for M in ("500", "1000"):
        assert rd[M]["part_B"]["reading"] == "CONTAMINATION-DOMINANT"  # L_c 180 - 124 = 56 against L_o 29 and L_i 0
        assert rd[M]["part_D"]["reading"] == "WORSENS"
        assert rd[M]["part_D"]["joints"]["21"] == dict(online=12, reference=24, plateau=186, difference=-12, at_floor=False,
                                                       A_digest_matches_gated=None)
        assert rd[M]["pooled"]["reading"] == "CORRELATION-ATTRIBUTABLE"
    assert rd["s100"] == "REPLICATES" and rd["part_C"] == "AVAILABLE FROM ACTIVITY"
    # one seed's L_o close to L_c: no dominance there; four still dominate
    recs2 = [r for r in recs if not (r.get("arm") == "online" and r["seed"] == 21)]
    recs2.append(_arm("online", 21, valid=True, ratio=1.8, L_o=dict(loss=50), twin_A=TA))
    rd2 = e5.readings(e5.CONTRACT, e5.first_records(recs2, "kill_test_seed"),
                      e5.first_records(recs2, "reported_arm", arm="gated_diagnostics"),
                      {a: e5.first_records(recs2, "reported_arm", arm=a) for a in e5.P2E3_ARMS + ("online",)}, ["500"])
    assert rd2["500"]["part_B"]["per_seed"]["21"]["dominant"] is None
    assert rd2["500"]["part_B"]["reading"] == "CONTAMINATION-DOMINANT"
    # s100 failing on one valid seed-load: REPLICATION FAIL, and that seed is not attributable
    recs3 = [r for r in recs if not (r.get("arm") == "s100" and r["seed"] == 22)]
    recs3.append(_arm("s100", 22, valid=True, p2e3_gate=False))
    rd3 = e5.readings(e5.CONTRACT, e5.first_records(recs3, "kill_test_seed"),
                      e5.first_records(recs3, "reported_arm", arm="gated_diagnostics"),
                      {a: e5.first_records(recs3, "reported_arm", arm=a) for a in e5.P2E3_ARMS + ("online",)}, ["500"])
    assert rd3["s100"] == "REPLICATION FAIL" and not rd3["500"]["part_B"]["per_seed"]["22"]["attributable"]
    # an invalid gated seed makes the verdict INVALID
    recs4 = [_gated_rec(s, valid=(s != 23)) for s in seeds]
    v4 = e5.verdict(recs4, results_path=record.cache_dir("test-runs") / "p2e5_synthetic_verdict.jsonl", log=out.append)
    assert v4["verdict"] == "INVALID" and v4["invalid_seeds"] == [23]
    # missing online records: Part B NOT ATTRIBUTABLE and Part D NOT ESTIMABLE
    recs5 = [r for r in recs if r.get("arm") != "online"]
    rd5 = e5.readings(e5.CONTRACT, e5.first_records(recs5, "kill_test_seed"),
                      e5.first_records(recs5, "reported_arm", arm="gated_diagnostics"),
                      {a: e5.first_records(recs5, "reported_arm", arm=a) for a in e5.P2E3_ARMS + ("online",)}, ["500"])
    assert rd5["500"]["part_B"]["reading"] == "NOT ATTRIBUTABLE" and rd5["500"]["part_D"]["reading"] == "NOT ESTIMABLE"
    # a crashed arm that kept its M = 500 load: only M = 1,000 is void
    recs6 = [r for r in recs if not (r.get("arm") == "online" and r["seed"] == 21)]
    part = _arm("online", 21, valid=True, ratio=1.8, L_o=dict(loss=29), twin_A=TA)
    part["loads"].pop("1000")
    part["crashed"] = dict(after_loads=["500"], error="MemoryError()")
    recs6.append(part)
    rd6 = e5.readings(e5.CONTRACT, e5.first_records(recs6, "kill_test_seed"),
                      e5.first_records(recs6, "reported_arm", arm="gated_diagnostics"),
                      {a: e5.first_records(recs6, "reported_arm", arm=a) for a in e5.P2E3_ARMS + ("online",)}, ["500", "1000"])
    assert rd6["500"]["part_B"]["per_seed"]["21"]["attributable"] and not rd6["1000"]["part_B"]["per_seed"]["21"]["attributable"]
    assert rd6["1000"]["part_B"]["reading"] == "CONTAMINATION-DOMINANT"  # four attributable seeds remain


def test_guard_refuses_without_predictions(monkeypatch):
    monkeypatch.setattr(e5.record, "git_state", lambda: dict(plant2_dirty=False, plant2_tree="x"))

    class R:
        def __init__(self, code=0, out=""):
            self.returncode, self.stdout = code, out
    calls = {"show": R(0, "")}

    def fake_git(*a):
        if a[0] == "show" and a[1].endswith(e5.CONTRACT_PATH):
            return R(0, calls.get(a[1].split(":")[0], "frozen text\n"))
        if a[0] == "show":
            return calls["show"]
        if a[0] == "diff" and "--numstat" in a:
            return R(0, "5\t0\tdocs/plant2/P2-E5-structured-items.md")
        return R(0, "")
    monkeypatch.setattr(e5, "_git", fake_git)
    with pytest.raises(SystemExit, match="no committed P2-E5 power_predictions"):
        e5.guard([])
    calls["show"] = R(0, json.dumps(dict(experiment="P2-E5", kind="power_predictions", contract_digest=e5.DIGEST,
                                         plant2_tree="x")))
    assert e5.guard([]) == set()
    calls["HEAD"] = "frozen text\nappended\n"
    assert e5.guard([]) == set()
    calls["HEAD"] = "inserted\nfrozen text\n"
    with pytest.raises(SystemExit, match="prefix"):
        e5.guard([])
    calls.pop("HEAD")
    monkeypatch.setattr(e5.record, "git_state", lambda: dict(plant2_dirty=True, plant2_tree="x"))
    with pytest.raises(SystemExit, match="uncommitted"):
        e5.guard([])


@pytest.mark.slow
def test_tiny_seed_end_to_end(run_dir):
    path = run_dir / "results.jsonl"
    out = []
    e5.run_seed(TINY, 95, gated=False, results_path=path, log=out.append, c4=E4_TINY)
    recs = [json.loads(l) for l in path.read_text().splitlines()]
    kinds = [(r["kind"], r.get("arm")) for r in recs]
    assert kinds[0] == ("exploration_seed", None)
    assert ("reported_arm", "gated_diagnostics") in kinds
    for a in e5.P2E3_ARMS + ("online",):
        assert ("reported_arm", a) in kinds, (a, out)
    assert not any("crashed" in r for r in recs), [r.get("crashed") for r in recs]
    g = recs[0]
    v = g["validity"]
    for M in ("120", "200"):
        assert all(v[M].values()), v[M]
    assert v["shuffled_ok"] and v["overlap_ok"]
    import gzip
    import io
    blob = Path(g["persistence"]["path"]).read_bytes()
    assert __import__("hashlib").sha256(blob).hexdigest() == g["persistence"]["sha256_file"]
    z = np.load(io.BytesIO(gzip.decompress(blob)))
    assert {"cue_kind_200", "cue_missing_200", "half_recall50_200", "learn_raster", "test_raster_200"} <= set(z.files)
    assert z["cue_kind_200"].size == 100 and z["learn_raster_offsets"].size == 201
    d = [r for r in recs if r.get("arm") == "gated_diagnostics"][0]["loads"]["200"]
    assert d["activity"]["count_auc"] > 0.9
    assert set(d["grid"]) == {"main", "plateau", "R3"}
    on = [r for r in recs if r.get("arm") == "online"][0]["loads"]["200"]
    assert on["validity"]["capture_ok"] and on["validity"]["twins_untouched"] and on["L_o"]["n"] > 0


@pytest.mark.slow
def test_reported_arm_crash_at_second_load_keeps_the_first(run_dir, monkeypatch):
    path = run_dir / "results.jsonl"
    orig = e5.p2e3_gate
    calls = []

    def flaky(*a, **k):
        calls.append(1)
        if len(calls) == 2:
            raise MemoryError("synthetic")
        return orig(*a, **k)
    monkeypatch.setattr(e5, "p2e3_gate", flaky)
    out = e5.run_p2e3_arm("s100", TINY, 98, False, path, log=lambda m: None)
    assert list(out["loads"]) == ["120"] and out["crashed"]["after_loads"] == ["120"]
    assert "MemoryError" in out["crashed"]["error"]
    rec = json.loads(path.read_text().splitlines()[-1])
    assert rec["loads"]["120"]["valid"] and "1000" not in rec["loads"]
