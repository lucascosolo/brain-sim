"""Reported P2-R1 audit of committed aggregates and independently regenerated inputs.

No experiment driver is imported or executed. Default input is baseline 55e16eb.
Print JSON; --append additionally appends one record to bench/results/plant2.jsonl.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess

import numpy as np

REPO = Path(__file__).resolve().parents[1]
RESULTS = "bench/results/plant2.jsonl"


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args], text=True).strip()


def committed(ref, path):
    return [json.loads(line) for line in git("show", f"{ref}:{path}").splitlines()]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def line_loads(seed, recorded_overlap):
    """Contract streams reimplemented without any plant2 imports, M=1000/F=10/s=60."""
    rng = np.random.default_rng([seed, 20, 10])
    protos = [np.sort(rng.choice(4000, 100, replace=False)) for _ in range(10)]
    union, all_lines = np.unique(np.concatenate(protos)), np.arange(4000)
    main, pooled = [], []
    for k in range(1, 1001):
        p = protos[k % 10]
        rng = np.random.default_rng([seed, 21, 10, k])
        pp = rng.permutation(p)
        po = rng.permutation(np.setdiff1d(all_lines, p))
        main.append(np.sort(np.concatenate([pp[:40], po[:60]])))
        rng = np.random.default_rng([seed, 23, k])
        d = rng.choice(union, 40, replace=False)
        pool = np.setdiff1d(all_lines, np.union1d(p, d))
        pooled.append(np.sort(np.concatenate([d, rng.choice(pool, 60, replace=False)])))
    membership = np.bincount(np.concatenate(protos), minlength=4000)
    # Count shared lines via column degrees within each family, avoiding pairwise simulation.
    shared = 0
    for f in range(10):
        a = np.bincount(np.concatenate([main[k - 1] for k in range(1, 1001) if k % 10 == f]), minlength=4000)
        shared += int(np.sum(a * (a - 1) // 2))
    overlap = shared / (10 * math.comb(100, 2))
    require(abs(overlap - recorded_overlap) < 1e-12, f"overlap mismatch seed {seed}")
    out = dict(sibling_overlap=overlap, overlap_matches_record=True, prototype_union_size=int(union.size))
    for name, items in [("main", main), ("pooled", pooled)]:
        loads = np.bincount(np.concatenate(items), minlength=4000)
        require(all(len(np.unique(i)) == 100 for i in items), "invalid item size")
        out[name] = dict(prototype_union_load_mean=float(loads[union].mean()),
                         prototype_union_load_sd=float(loads[union].std()), max_line_load=int(loads.max()),
                         multiple_prototype_load_mean=float(loads[membership >= 2].mean()),
                         outside_union_load_mean=float(loads[membership == 0].mean()))
    return out


def exact_recovery_p0(mean, icc=0.09):
    """Shared-beta no-effect model: 50 items, two 5-cue copies, >=3, >=25 eligible, >=90% recover."""
    concentration = 1 / icc - 1
    a, b = mean * concentration, (1 - mean) * concentration

    def moment(k, n):
        return math.exp(math.lgamma(a + k) + math.lgamma(b + n - k) - math.lgamma(a + b + n)
                        - math.lgamma(a) - math.lgamma(b) + math.lgamma(a + b))
    eligible = sum(math.comb(5, k) * moment(k, 5) for k in range(3, 6))
    both = sum(math.comb(5, k) * math.comb(5, j) * moment(k + j, 10)
               for k in range(3, 6) for j in range(3, 6))
    q = both / eligible
    return sum(math.comb(50, e) * eligible ** e * (1 - eligible) ** (50 - e)
               * sum(math.comb(e, k) * q ** k * (1 - q) ** (e - k)
                     for k in range(math.ceil(.9 * e - 1e-9), e + 1)) for e in range(25, 51))


def audit(ref):
    rows = committed(ref, RESULTS)
    e4 = {r["seed"]: r for r in rows if r["experiment"] == "P2-E4" and r["kind"] == "kill_test_seed"}
    e5 = {r["seed"]: r for r in rows if r["experiment"] == "P2-E5" and r["kind"] == "kill_test_seed"}
    diag = {r["seed"]: r for r in rows if r["experiment"] == "P2-E5"
            and r.get("arm") == "gated_diagnostics" and r.get("gated")}
    online = {r["seed"]: r for r in rows if r["experiment"] == "P2-E5" and r.get("arm") == "online" and r.get("gated")}
    verdict = next(r for r in rows if r["experiment"] == "P2-E5" and r["kind"] == "kill_test_verdict")
    require(sorted(e4) == list(range(16, 21)) and sorted(e5) == list(range(21, 26)), "unexpected gated seeds")
    checks, ranks, aucs = Counter(), {}, {}
    for seed, r in sorted(e5.items()):
        ranks[str(seed)], aucs[str(seed)] = {}, {}
        for load, data in r["loads"].items():
            counts = data["counts"]
            for name, value in counts.items():
                bar = 90 if name in ("C4_recall", "C4_spurious", "S4") else 180
                require(data["vector"][name] == (value >= bar), f"vector {seed}/{load}/{name}")
                checks["criterion_vector_bits"] += 1
            for name, bits in [("S2", data["per_cue"]["joint"]), ("S4", data["per_cue"]["joint"][:100])]:
                require(bits.count("1") == counts[name], f"joint bits {seed}/{load}/{name}")
                checks["per_cue_joint_counts"] += 1
            require(counts == verdict["per_seed"][str(seed)][load], "verdict count mismatch")
            a = diag[seed]["loads"][load]["activity"]
            pos, neg = np.array(a["count_hist_pos"], float), np.array(a["count_hist_neg"], float)
            auc = float(np.sum(pos * (np.cumsum(neg) - .5 * neg)) / (pos.sum() * neg.sum()))
            require(abs(auc - a["count_auc"]) < 1e-12, "AUC mismatch")
            aucs[str(seed)][load] = auc
            checks["histogram_aucs"] += 1
            grid = diag[seed]["loads"][load]["grid"]
            lo = online[seed]["loads"][load]["L_o"]["loss"]
            by_point = {}
            for point in ("best", "frozen"):
                ub, own = (grid[s][point + "_cues"] for s in ("plateau", "main"))
                losses = dict(L_c=max(0, min(ub, 180) - min(own, 180)), L_i=max(0, 180 - ub), L_o=lo)
                dominant = next((k for k, v in losses.items() if v >= 20
                                 and v - max(x for j, x in losses.items() if j != k) >= 10), None)
                by_point[point] = dict(**losses, dominant=dominant)
                if point == "best":
                    for k, value in losses.items():
                        require(value == verdict["readings"][load]["part_B"]["per_seed"][str(seed)][k], "loss mismatch")
                        checks["grid_loss_values"] += 1
            ranks[str(seed)][load] = by_point
    habituation, totals = {}, Counter()
    for seed, r in sorted(e4.items()):
        habituation[str(seed)] = {}
        for load, data in r["loads"].items():
            items, recorded = data["hab_items"], data["habituation"]
            eligible = [d for d in items if d["scored"] and d["L_ctl"] >= 8]
            hab = [d for d in eligible if d["L_rep"] <= d["L_ctl"] - 3]
            rec = [d for d in items if d["rec_ctl"] >= 3]
            recovered = [d for d in rec if d["rec_rep"] >= 3]
            require([len(eligible), len(hab)] == [recorded["n_eligible"], recorded["n_habituated"]], "O4 counts")
            require([len(rec), len(recovered)] == recorded["O5_recovery_n"], "O5 counts")
            require(recorded["O4"] == (len(eligible) >= 25 and len(hab) <= .1 * len(eligible) + 1e-9), "O4 flag")
            require(recorded["O5_recovery"] == (len(rec) >= 25 and len(recovered) >= math.ceil(.9 * len(rec) - 1e-9)), "O5 flag")
            limited = Counter()
            for d in items:
                totals["presentations"] += len(d["per_rep_both"])
                for i, (recall, both) in enumerate(zip(d["per_rep_recall"], d["per_rep_both"])):
                    if recall >= .8 and not both:
                        limited["all"] += 1
                        limited["late"] += i >= 90
                        limited["first"] += i == 0
                for part, prefix in [("recovery", "rec"), ("collateral", "col")]:
                    totals[part + "_ctl_only"] += d[prefix + "_ctl"] >= 3 > d[prefix + "_rep"]
                    totals[part + "_rep_only"] += d[prefix + "_rep"] >= 3 > d[prefix + "_ctl"]
            for key, value in limited.items():
                totals["content_limited_" + key] += value
            habituation[str(seed)][load] = dict(O4=[len(eligible), len(hab)], O5=[len(rec), len(recovered)], content_limited=dict(limited))
    paths = set()

    def collect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "path" and isinstance(item, str) and "cache" in item:
                    paths.add(item)
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)
    for r in rows:
        if r["experiment"] in ("P2-E4", "P2-E5"):
            collect(r)
    c75 = {}
    for r in rows:
        if r["experiment"] == "P2-E4" and r["kind"] == "diagnosis" and r.get("gated"):
            l = r["loads"]["1000"]
            d = l["D1"]
            c75[str(r["seed"])] = (d["both"] + d["index_only"] + sum(d[k] * l["D2"][k]["A75_rescues"]
                                                                         for k in ("content_only", "neither"))) / l["n_half"]
    return dict(checks=dict(checks), checks_passed=True, rank_losses=ranks, histogram_aucs=aucs,
                line_loads={str(s): line_loads(s, e5[s]["validity"]["sibling_overlap_mean"]) for s in sorted(e5)},
                habituation=habituation, habituation_totals=dict(totals), recombined_C1_75ms=c75,
                exact_recovery_p0={str(n): exact_recovery_p0(n / 250) for n in (203, 204, 205)},
                raw_paths=dict(referenced=len(paths), present=sum(Path(p).exists() for p in paths),
                               missing=sorted(p for p in paths if not Path(p).exists())),
                scope="Aggregate checks and independent input regeneration; no raw-data replication or new experiment.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="55e16eb", help="Committed baseline to audit")
    parser.add_argument("--append", action="store_true", help="Append summary to the append-only results file")
    args = parser.parse_args()
    ref = git("rev-parse", args.ref)
    out = dict(experiment="P2-R1", kind="baseline_methodology_audit", baseline_commit=ref,
               source_blob=git("rev-parse", f"{ref}:{RESULTS}"), timestamp=datetime.now(timezone.utc).isoformat(),
               runtime=dict(python=platform.python_version(), numpy=np.__version__),
               script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), **audit(ref))
    text = json.dumps(out, sort_keys=True)
    if args.append:
        data = (text + "\n").encode()
        fd = os.open(REPO / RESULTS, os.O_WRONLY | os.O_APPEND)
        try:
            require(os.write(fd, data) == len(data), "short append")
        finally:
            os.close(fd)
    print(text)


if __name__ == "__main__":
    main()
