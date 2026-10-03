"""K1.1 age-matched never-trained control (DIAGNOSTIC ONLY; K1.1 remains FAIL, bar unchanged).

For seed 1 and both plants (default, SPEC 8.12 encode mode): fork the engine at the
tick before A's presentation, run the trained path on one copy and an idle twin (no
present(), same ticks) on the other, then give both the identical arms and count
how many of the TRAINED run's assembly (and W) cells spike within 50/100/200 ticks.
"""

import copy
import json
import os
import sys
import time

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import k03_pairing as k03
import k11_binding as k11
from brainsim import encode, params

WINS = k11.REPORT_WINDOWS
ARMS = ("cue", "full", "none")
HEADER = "DIAGNOSTIC ONLY: K1.1 remains FAIL; bar unchanged"


def _arm(eng, name, A_ids, cue, watch_ids, hpc_e_ids):
    """Same stepping as k11._run_arm, plus hpc E cumulative spikes at each window."""
    if name == "cue":
        eng.inject(cue, params.PATTERN_AMP_MV, k11.CUE_TICKS)
    elif name == "full":
        eng.present(k11.PATTERN_A, k11.CUE_TICKS)
    n = eng.net.n
    wm = k11._mask(watch_ids, n)
    first = np.full(n, -1, np.int64)
    e_mask = k11._mask(hpc_e_ids, n)
    hpc_e_total = {}
    run = 0
    for k in range(k11.CUE_TICKS):
        eng.step(1)
        s = eng._buf_spikes[-1]
        newly = s[wm[s] & (first[s] < 0)]
        first[newly] = k
        run += int(e_mask[s].sum())
        k03._drain_telemetry(eng)
        if (k + 1) in WINS:
            hpc_e_total[k + 1] = run
    return first, hpc_e_total


def _score(firsts, hpc_e_total, assembly, W):
    fs = firsts[assembly]
    out = {
        "assembly_count": {w: int(np.count_nonzero((fs >= 0) & (fs < w))) for w in WINS},
        "hpc_e_spikes": hpc_e_total,
        "first_assembly_spike_tick": int(fs[fs >= 0].min()) if (fs >= 0).any() else None,
    }
    if W is not None:
        fw = firsts[W]
        out["W_count"] = {w: int(np.count_nonzero((fw >= 0) & (fw < w))) for w in WINS}
    return out


def _arms_from(eng, A_ids, cue, assembly, W, hpc_e_ids):
    watch = np.union1d(assembly, W) if W is not None else assembly
    if "inject" in eng.__dict__:
        del eng.inject
    res = {}
    for name in ARMS:
        e = copy.deepcopy(eng)
        first, tot = _arm(e, name, A_ids, cue, watch, hpc_e_ids)
        res[name] = _score(first, tot, assembly, W)
    return res


def _trained(fork, encode_mode):
    """Trained path on a copy of the fork; returns engine at cue time, assembly, W."""
    eng = copy.deepcopy(fork)
    net = eng.net
    hpc_e_ids = encode.hpc_e_ids(net)
    A_ids = np.sort(np.asarray(eng.patterns[k11.PATTERN_A], np.int64))
    base_counts = fork._base_counts
    if encode_mode:
        eng.encode_mode = True
    a_counts, _ = k11._present_recording_volley(eng, k11.PATTERN_A, k11.A_TICKS, A_ids)
    W = eng.encode_W.copy() if encode_mode else None
    assembly = k11.assembly_from_counts(base_counts, a_counts, hpc_e_ids, k11.A_TICKS)
    if encode_mode:
        eng.step(1)
        k03._drain_telemetry(eng)
        k11._step_chunked_counting(eng, k11.DELAY_TICKS - 1)
        eng.encode_mode = False
    else:
        k11._step_chunked_counting(eng, k11.DELAY_TICKS)
    return eng, assembly, W, A_ids


def _twin(fork, encode_mode):
    eng = copy.deepcopy(fork)
    if encode_mode:
        eng.encode_mode = True
    k11._step_chunked_counting(eng, k11.A_TICKS + k11.DELAY_TICKS)
    eng.encode_mode = False
    return eng


def build_fork(seed):
    eng, _ = k03.warm_engine(seed)
    if "inject" in eng.__dict__:
        del eng.inject
    base_counts = k11._step_chunked_counting(eng, k11.BASE_TICKS)
    eng._base_counts = base_counts
    return eng


def run_plant(fork, encode_mode, seed, smoke):
    hpc_e_ids = encode.hpc_e_ids(fork.net)
    tr_eng, assembly, W, A_ids = _trained(fork, encode_mode)
    cue = k11.cue_ids(A_ids)
    trained = _arms_from(tr_eng, A_ids, cue, assembly, W, hpc_e_ids)
    # determinism replay of the trained path (second fork copy)
    tr2, asm2, W2, _ = _trained(fork, encode_mode)
    assert np.array_equal(assembly, asm2)
    trained2 = _arms_from(tr2, A_ids, cue, assembly, W, hpc_e_ids)
    assert trained2 == trained, "trained replay not deterministic"
    twin = _arms_from(_twin(fork, encode_mode), A_ids, cue, assembly, W, hpc_e_ids)

    eq = {"vs_run_experiment": None}
    if smoke:
        eq["note"] = ("SKIPPED in smoke: k11.run_experiment asserts absolute t=120000; "
                      "replaced by a two-replay determinism check (passed)")
    else:
        ref = k11.run_experiment(seed, encode_mode=encode_mode)
        ok = list(ref["assembly"]["ids"]) == assembly.tolist()
        for name in ARMS:
            for w in WINS:
                n_ref = round(ref["arms"][name]["recall"][w] * assembly.size) if assembly.size else 0
                ok = ok and n_ref == trained[name]["assembly_count"][w]
                if encode_mode:
                    nW = round(ref["arms"][name]["recall_W"][w] * W.size)
                    ok = ok and nW == trained[name]["W_count"][w]
            ok = ok and ref["arms"][name]["first_assembly_spike_tick"] == \
                trained[name]["first_assembly_spike_tick"]
        if encode_mode:
            ok = ok and list(ref["sparse_write_A"]["W"]) == W.tolist()
        eq["vs_run_experiment"] = bool(ok)
        assert ok, "replay does not equal run_experiment"
    return {"encode_mode": encode_mode, "assembly_ids": assembly.tolist(),
            "assembly_size": int(assembly.size),
            "W_ids": W.tolist() if W is not None else None,
            "trained": trained, "never_trained": twin, "equality": eq}


def _frac(c, n):
    return f"{c:>3d} ({c / n:5.1%})" if n else f"{c:>3d} (  n/a)"


def table(r):
    n = r["assembly_size"]
    enc = r["encode_mode"]
    print(f"\n=== plant: {'encode_mode=True (SPEC 8.12)' if enc else 'encode_mode=False (default)'}"
          f"   assembly size {n}" + (f"   W size {len(r['W_ids'])}" if enc else "") + " ===")
    print(HEADER)
    print(f"equality with run_experiment: {r['equality']}")
    for label, key, ncell in (("assembly", "assembly_count", n),
                              ("W", "W_count", len(r["W_ids"]) if enc else 0)):
        if label == "W" and not enc:
            continue
        print(f"\n[{label} cells, n={ncell}]")
        print(f"{'row':<14}{'half@50':>13}{'half@100':>13}{'half@200':>13}"
              f"{'fullA@50':>13}{'none@50':>13}{'diff@50':>9}")
        for row, nm in (("trained", "trained"), ("never-trained", "never_trained")):
            d = r[nm]
            diff = ""
            if row == "trained":
                diff = f"{r['trained']['cue'][key][50] - r['never_trained']['cue'][key][50]:+d}"
            print(f"{row:<14}" + "".join(_frac(d['cue'][key][w], ncell).rjust(13) for w in WINS)
                  + _frac(d['full'][key][50], ncell).rjust(13)
                  + _frac(d['none'][key][50], ncell).rjust(13) + f"{diff:>9}")
    print("\n[hpc E total spikes, half cue @50/100/200 | first assembly spike tick (half cue)]")
    for row, nm in (("trained", "trained"), ("never-trained", "never_trained")):
        d = r[nm]["cue"]
        print(f"{row:<14}" + " ".join(f"{d['hpc_e_spikes'][w]:>6d}" for w in WINS)
              + f"   first={d['first_assembly_spike_tick']}")


def main():
    args = sys.argv[1:]
    smoke = "--smoke" in args
    jpath = args[args.index("--json") + 1] if "--json" in args else None
    if smoke:
        k03.WARMUP_TICKS = 4000
    seed = k11.SEED
    t0 = time.time()
    fork = build_fork(seed)
    results = {}
    for enc in (False, True):
        r = run_plant(fork, enc, seed, smoke)
        results["encode" if enc else "default"] = r
        table(r)
        sys.stdout.flush()
    print(f"\nwall {time.time() - t0:.0f} s")
    if jpath:
        with open(jpath, "w") as f:
            json.dump({"note": HEADER, "smoke": smoke, "results": results}, f, indent=1)


if __name__ == "__main__":
    main()
