"""SPEC 8.24 what-if ceilings: the 8.23 diagnostic on a plant built with construction parameters overridden.
Run: PYTHONPATH=<worktree> python tests/k824_whatif.py --seed N --whatif {W0,W1,W2,W3} [--json out.json] [--smoke]
W1: hpc->hpc in-degree 20 -> 80.  W2: ctx E rate target 4 -> 1 Hz.  W3: both.  W0: nothing (must reproduce 8.23).
GEN2 (SPEC 8.25): no override; run with BRAINSIM_PLANT=gen2; health clause H2 (targets from the plant); W0 comparison skipped.
Overrides are applied to the params module before the engine is built and never restored (one process per run).
Diagnostic only. Exit 0 normally, 2 if W0 differs from the recorded 8.23 numbers, 1 on assertion failure.
"""
import json
import math
import os
import sys

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import k03_pairing as k03
import k11_binding as k11
import k823_ceiling as c823
from brainsim import encode, params
from brainsim.engine import Engine

RECORDED = os.path.expanduser("~/.cache/scratch/brainsim-ceil/ceil_seed%d.json")
ARMS = ("N", "Aa", "R", "AaR")
HEALTH_FROM, HEALTH_TOL, HEALTH_MAX_FRAC = 110_000, 0.25, 0.20
ORIG = {"hpc_hpc_k_in": 20, "ctx_r_target_exc": 4.0}


def apply_overrides(whatif):
    if whatif == "GEN2":
        assert params.ACTIVE_PROFILE == "gen2", "GEN2 needs BRAINSIM_PLANT=gen2 in the environment"
        return
    assert params.ACTIVE_PROFILE is None, ("W0..W3 refuse to run with a plant profile active", params.ACTIVE_PROFILE)
    """Mutate the params module in place, before any Engine exists. REGIONS is one shared dict and PROJECTIONS one
    shared list, so every reader (net.py build, engine._k_target, homeostat r_target, structural growth) sees it."""
    if whatif in ("W1", "W3"):
        i = next(i for i, p in enumerate(params.PROJECTIONS) if p[:2] == ("hpc", "hpc"))
        src, dst, k_in, sigma = params.PROJECTIONS[i]
        assert (k_in, sigma) == (20, 0.25), params.PROJECTIONS[i]
        params.PROJECTIONS[i] = (src, dst, 80, sigma)
    if whatif in ("W2", "W3"):
        assert params.REGIONS["ctx"]["r_target_exc"] == 4.0
        params.REGIONS["ctx"]["r_target_exc"] = 1.0


def effective(eng, whatif):
    """What the built engine really uses; asserted against the override."""
    net = eng.net
    hpc, ctx = encode.hpc_e_ids(net), encode.ctx_e_ids(net)
    hh = [k for s, k, _ in net.allowed_src["hpc"] if s == "hpc"]
    assert len(hh) == 1
    alive = net.alive
    pre_e = alive & net.is_exc[net.pre]
    m = pre_e & np.isin(net.pre, hpc) & np.isin(net.post, hpc)
    indeg = float(m.sum()) / len(hpc)
    eff = {"whatif": whatif, "hpc_hpc_k_in_allowed_src": hh[0],
           "hpc_k_target": float(eng._k_target[hpc].mean()),
           "hpc_E_from_hpc_E_mean_alive_indegree": indeg,
           "ctx_E_r_target_homeostat": float(net.r_target[ctx].mean()),
           "ctx_E_r_target_min_max": [float(net.r_target[ctx].min()), float(net.r_target[ctx].max())],
           "hpc_E_r_target_homeostat": float(net.r_target[hpc].mean()),
           "params_REGIONS_ctx_r_target_exc": params.REGIONS["ctx"]["r_target_exc"],
           "eng_p_REGIONS_ctx_r_target_exc": eng.p.REGIONS["ctx"]["r_target_exc"]}
    k_hh = 80 if whatif in ("W1", "W3", "GEN2") else 20
    r_ctx = 1.0 if whatif in ("W2", "W3") else 2.0 if whatif == "GEN2" else 4.0
    assert hh[0] == k_hh, ("allowed_src hpc->hpc", hh[0], k_hh)
    if whatif == "GEN2":
        ch = [k for s, k, _ in net.allowed_src["hpc"] if s == "ctx"]
        assert ch == [60], ("allowed_src hpc<-ctx", ch)
        r_i = net.r_target[net.region_slice["ctx"]][~net.is_exc[net.region_slice["ctx"]]]
        assert set(r_i.tolist()) == {4.0}, set(r_i.tolist())
        assert eng.p.NOISE_SIGMA_MV["ctx"] == 2.0 and params.NOISE_SIGMA_MV["ctx"] == 2.0
        assert math.isclose(eff["hpc_k_target"], 60 + 80, rel_tol=1e-6), eff["hpc_k_target"]
        assert eff["ctx_E_r_target_min_max"] == [2.0, 2.0] and eff["hpc_E_r_target_homeostat"] == 1.0
        assert eff["eng_p_REGIONS_ctx_r_target_exc"] == 2.0
        eff["ctx_hpc_k_in_allowed_src"] = ch[0]
        eff["ctx_noise_mv"] = params.NOISE_SIGMA_MV["ctx"]
        eff["ctx_I_r_target_homeostat"] = 4.0
        eff["active_profile"] = params.ACTIVE_PROFILE
        return eff
    assert math.isclose(eff["hpc_k_target"], k_hh + 30, rel_tol=1e-6), eff["hpc_k_target"]
    assert eff["ctx_E_r_target_min_max"] == [r_ctx, r_ctx], eff["ctx_E_r_target_min_max"]
    assert eff["eng_p_REGIONS_ctx_r_target_exc"] == r_ctx
    return eff


def proj_stats(net):
    """Alive excitatory synapses per (src region, dst region) and mean w / w_max, at the moment of the call."""
    out = {}
    names = list(net.region_names)
    for si, sn in enumerate(names):
        for di, dn in enumerate(names):
            m = net.alive & net.is_exc[net.pre] & (net.region[net.pre] == si) & (net.region[net.post] == di)
            if m.any():
                out[f"{sn}->{dn}"] = {"n": int(m.sum()),
                                      "mean_w_frac": float((net.w[m] / net.w_max_n[net.post[m]]).mean())}
    return out


def make_warm(whatif, health_from, store):
    """k03.warm_engine, line for line, with the health window recorded; same step sizes, so same trajectory."""
    def warm(seed):
        eng = Engine(seed=seed, params=k03._deepcopyable_params())
        net = eng.net
        hpc, ctx = encode.hpc_e_ids(net), encode.ctx_e_ids(net)
        masks = {}
        for key, ids in (("ctx", ctx), ("hpc", hpc)):
            masks[key] = np.zeros(net.n, bool)
            masks[key][ids] = True
        peak = {"ctx": 0.0, "hpc": 0.0}
        c0 = None

        def collect():
            for s in eng._buf_spikes:
                for key in peak:
                    peak[key] = max(peak[key], np.count_nonzero(masks[key][s]) / np.count_nonzero(masks[key]))

        remaining = k03.WARMUP_TICKS - k03.D_MAX
        while remaining:
            chunk = min(1000, remaining)
            if eng.t == health_from:
                c0 = eng.spike_counts().astype(np.int64)
            eng.step(chunk)
            if c0 is not None:
                collect()
            remaining -= chunk
            k03._drain_telemetry(eng)
        assert c0 is not None, "health window never started"
        for _ in range(k03.D_MAX):
            eng.step(1)
            collect()
            k03._drain_telemetry(eng)
        assert eng.t == k03.WARMUP_TICKS, eng.t
        assert eng.phase == "wake", eng.phase
        win = int(eng.t) - health_from
        cnt = eng.spike_counts().astype(np.int64) - c0
        h = {"window": [health_from, int(eng.t)]}
        tgt = {"ctx": params.REGIONS["ctx"]["r_target_exc"], "hpc": params.REGIONS["hpc"]["r_target_exc"]}
        fails = []
        for key, ids in (("ctx", ctx), ("hpc", hpc)):
            hz = float(cnt[ids].sum()) * 1000.0 / (len(ids) * win)
            h[key] = {"mean_hz": hz, "target_hz": tgt[key], "rel_err": hz / tgt[key] - 1.0,
                      "peak_frac_one_tick": peak[key], "zero_spike_frac": float((cnt[ids] == 0).mean())}
            if abs(hz / tgt[key] - 1.0) > HEALTH_TOL:
                fails.append(f"{key} E rate {hz:.3f} Hz not within 25% of target {tgt[key]}")
            if peak[key] > HEALTH_MAX_FRAC:
                fails.append(f"{key} E peak one-tick fraction {peak[key]:.3f} > 0.20")
        for name in net.region_names:
            sl = net.region_slice[name]
            h.setdefault("zero_spike_frac_all_cells", {})[name] = float((cnt[sl.start:sl.stop] == 0).mean())
        h["projections_at_120000"] = proj_stats(net)
        h["healthy"] = not fails
        h["failing"] = fails
        store["health"] = h
        store["effective"] = effective(eng, whatif)
        return eng
    return warm


def print_health(h, smoke):
    print(f"\nHEALTH over {h['window'][0]}..{h['window'][1]}" + ("  [SMOKE window]" if smoke else ""))
    for key in ("ctx", "hpc"):
        r = h[key]
        print(f"  {key} E: {r['mean_hz']:.3f} Hz vs target {r['target_hz']} ({r['rel_err'] * 100:+.1f}%), "
              f"peak one-tick fraction {r['peak_frac_one_tick']:.3f}, zero-spike cells {r['zero_spike_frac'] * 100:.1f}%")
    print("  zero-spike fraction, all cells by region:", {k: round(v, 3) for k, v in h["zero_spike_frac_all_cells"].items()})
    print("  alive E synapses at the end of warm-up (n, mean w/w_max):")
    for k, v in h["projections_at_120000"].items():
        print(f"    {k:>10}: {v['n']:7d}  {v['mean_w_frac']:.3f}")
    print("HEALTHY" if h["healthy"] else "UNHEALTHY: " + "; ".join(h["failing"]))


def first_mismatch(a, b, path=""):
    if isinstance(a, dict):
        for k in a:
            if k not in b:
                return f"{path}/{k} missing in recorded"
            r = first_mismatch(a[k], b[k], f"{path}/{k}")
            if r:
                return r
        return None
    if isinstance(a, float) and math.isnan(a) and isinstance(b, float) and math.isnan(b):
        return None
    return None if a == b else f"{path}: now {a!r} recorded {b!r}"


def w0_validity(rec, seed):
    old = json.load(open(RECORDED % seed))
    mm = first_mismatch({"part1": rec["mean_part1"], "part2": {a: rec["mean_part2"][a] for a in ARMS}},
                        {"part1": old["mean_part1"], "part2": {a: old["mean_part2"][a] for a in ARMS}})
    return mm


def gen2_readings(rec):
    """Per arm, from the means over states. K1.1-200 is a separate diagnostic, never a K1.1 result."""
    n_idle = {t: rec["mean_part2"]["N"][f"none_{t}"]["W_cells"] for t in c823.TICKS}
    out = {}
    for a in ARMS:
        m = rec["mean_part2"][a]
        r = {"K1.1 clause (half cue, 50 ticks, >= 13 of 16)": m["half_50"]["W_cells"] >= c823.DONE_MIN,
             "K1.1-200 (diagnostic, 200 ticks, >= 13 of 16)": m["half_200"]["W_cells"] >= c823.DONE_MIN}
        for t in c823.TICKS:
            half, b, idle = m[f"half_{t}"]["W_cells"], m[f"B_{t}"]["W_cells"], m[f"none_{t}"]["W_cells"]
            r[f"half_{t}_W_cells"] = half
            r[f"idle_{t}_W_cells"] = idle
            r[f"idle_{t}_arm_N_W_cells"] = n_idle[t]
            r[f"B_{t}_W_cells"] = b
            r[f"B_vs_half_{t}"] = {"B": b, "half": half, "B_le_half_of_half": b <= c823.SELECT_MUL * half}
        r["idle_50_quiet (<= 3)"] = r["idle_50_W_cells"] <= c823.QUIET_MAX
        out[a] = r
    return out


def print_gen2_readings(g, smoke):
    print("\nGEN2 readings per arm (means over states)" + ("  [SMOKE: meaningless]" if smoke else ""))
    for a, r in g.items():
        print(f"{a:>4}: K1.1 clause (half cue, 50 ticks, >= 13 of 16): "
              f"{'met' if r['K1.1 clause (half cue, 50 ticks, >= 13 of 16)'] else 'not met'} ({r['half_50_W_cells']:.2f})")
        print(f"      K1.1-200 (diagnostic, 200 ticks, >= 13 of 16; NOT K1.1): "
              f"{'met' if r['K1.1-200 (diagnostic, 200 ticks, >= 13 of 16)'] else 'not met'} ({r['half_200_W_cells']:.2f})")
        print(f"      idle W cells: 50 ticks {r['idle_50_W_cells']:.2f} (<= 3: {r['idle_50_quiet (<= 3)']}, "
              f"arm N {r['idle_50_arm_N_W_cells']:.2f}); 200 ticks {r['idle_200_W_cells']:.2f} (arm N {r['idle_200_arm_N_W_cells']:.2f})")
        for t in c823.TICKS:
            v = r[f"B_vs_half_{t}"]
            print(f"      B vs half cue at {t}: {v['B']:.2f} vs {v['half']:.2f} (B <= half of half cue: {v['B_le_half_of_half']})")


def main():
    smoke = "--smoke" in sys.argv
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1
    whatif = sys.argv[sys.argv.index("--whatif") + 1]
    assert whatif in ("W0", "W1", "W2", "W3", "GEN2"), whatif
    apply_overrides(whatif)
    health_from = HEALTH_FROM
    if smoke:
        health_from = 3000
        k03.WARMUP_TICKS = 4000
    store = {}
    print(f"{whatif} seed {seed}" + ("  [SMOKE]" if smoke else ""))
    rec = c823.run(seed, smoke, ARMS, make_warm(whatif, health_from, store), compare_recorded=whatif != "GEN2")
    # run() prints the 8.23 seed line and tables after warming; health and effective values printed here
    print("\nEFFECTIVE parameters of the built engine:")
    for k, v in store["effective"].items():
        print(f"  {k}: {v}")
    print_health(store["health"], smoke)
    rec.update({"whatif": whatif, "health": store["health"], "effective": store["effective"], "arms": list(ARMS)})
    code = 0
    if whatif == "W0" and not smoke:
        mm = w0_validity(rec, seed)
        rec["w0_validity"] = "MATCH" if mm is None else "DIFFERENT"
        rec["w0_first_mismatch"] = mm
        print("W0 MATCH (Part 1 means and Part 2 means of N, Aa, R, AaR identical to 8.23)" if mm is None
              else f"W0 DIFFERENT, first mismatch {mm}")
        code = 0 if mm is None else 2
    else:
        print("W0 validity: skipped" + (" (SMOKE)" if smoke else f" ({whatif} is not the plant of 8.23)"))
    if whatif == "GEN2":
        rec["gen2_readings"] = gen2_readings(rec)
        print_gen2_readings(rec["gen2_readings"], smoke)
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as f:
            json.dump(rec, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("EXIT SMOKE" if smoke else f"EXIT {code}")
    sys.exit(code)


if __name__ == "__main__":
    main()
