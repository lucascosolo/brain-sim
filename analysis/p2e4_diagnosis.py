"""P2-E4 post-run diagnosis (plan: docs/plant2/P2-E4-diagnosis-plan.md, predeclared before any gated seed).

A reported analysis, not a gate. It lives outside plant2/ so the gated code tree stays as frozen. It re-simulates a
seed's main timeline with the frozen driver, adding read-only measurements at slot time (no random draws), and is
void for that seed unless every logged gated-block slot outcome is reproduced exactly.

    PYTHONPATH=. python3 analysis/p2e4_diagnosis.py --seed 42            # exploration record
    PYTHONPATH=. python3 analysis/p2e4_diagnosis.py --seed 16 --gated    # after the P2-E4 verdict
"""
import argparse
import copy
import gzip
import json
import sys
import time

import numpy as np

from plant2 import record
from plant2.experiments import p2_e4_online as e4

HALF3 = ("recent", "uniform", "cohort")
COMPARE = ("kind", "target", "block", "age", "recall", "spurious", "missing", "intrusions", "joint", "n_R50", "n_rec",
           "ignition", "lines", "leak_A", "leak_C")
_orig_score_slot = e4.score_slot


class DiagOnline(e4.Online):
    """The frozen Online network plus a copy of mem vbar at each probe slot's onset (read only)."""

    _capture = False
    _onset_vbar = None
    diag_main = True

    def _rates(self, active):
        if active is not None and self._capture:
            self._onset_vbar = self.mem.vbar.copy()
            self._capture = False
        return super()._rates(active)

    def run_slot(self, s, bg, sl, post):
        self._capture = True
        try:
            return super().run_slot(s, bg, sl, post)
        finally:
            self._capture = False


def diag_score_slot(e, s, fm, fr):
    d = _orig_score_slot(e, s, fm, fr)
    if getattr(e, "diag_main", False) and s.get("block") in e.c["gate_M"] and s["kind"] in HALF3:
        c, t, m = e.c, s["target"], e.c["m"]
        A, R, item = e.A[t - 1], e.R[t - 1], e.items[t - 1]
        sp50 = (fm >= 0) & (fm < c["win_mem"])
        sp75 = (fm >= 0) & (fm < c["win_rec"])
        rec = np.flatnonzero((fr >= 0) & (fr < c["win_rec"]))
        missing = np.setdiff1d(item, s["cue"])
        regen = np.intersect1d(missing, rec)
        lat = lambda cells: float(np.median(fm[cells][sp75[cells]])) if cells.size and sp75[cells].any() else None
        cand = None
        if regen.size:
            # candidate inputs: feedback synapses from memory cells whose first spike (k = 0..74) came at least one tick
            # (the feedback delay) before the line's first spike. A candidate is a possible contributor, not a proven one.
            pre, post = e.fb.keys // m, e.fb.keys % m
            sel = np.isin(post, regen) & sp75[pre]
            sel &= fm[pre] <= fr[post] - 1
            RnA = np.setdiff1d(R, A)
            lines_A = np.unique(post[sel & np.isin(pre, A)])
            lines_RnA = np.unique(post[sel & np.isin(pre, RnA)])
            lines_other = np.unique(post[sel & ~np.isin(pre, A) & ~np.isin(pre, RnA)])
            cand = classify_lines(regen, lines_A, lines_RnA, lines_other)
        v = e._onset_vbar
        d["diag"] = dict(
            A_recall75=float(sp75[A].mean()) if A.size else 0.0, R_recall50=float(sp50[R].mean()) if R.size else None,
            R_size=int(R.size), R_and_A=int(np.intersect1d(R, A).size), latency_A=lat(A), latency_R=lat(R),
            regen_candidates=cand,
            offset_global=None if v is None else float(v.mean() - float(e.mem.v_rest)),
            offset_assembly=None if v is None or not A.size else float(v[A].mean() - float(e.mem.v_rest)))
    return d


CANDIDATE_CLASSES = ("with_A_candidate", "only_R_not_A_candidates", "only_other_candidates", "mixed_non_A_candidates",
                     "no_earlier_candidate")


def classify_lines(regen, lines_A, lines_RnA, lines_other):
    """Exhaustive, exclusive classes of regenerated lines by their earlier candidate inputs (fractions sum to 1)."""
    regen = np.asarray(regen)
    a, r, o = np.isin(regen, lines_A), np.isin(regen, lines_RnA), np.isin(regen, lines_other)
    cls = dict(with_A_candidate=a, only_R_not_A_candidates=~a & r & ~o, only_other_candidates=~a & ~r & o,
               mixed_non_A_candidates=~a & r & o, no_earlier_candidate=~a & ~r & ~o)
    n = max(1, regen.size)
    return dict(n_regen=int(regen.size), **{k: float(v.sum() / n) for k, v in cls.items()})


def twin_B_pairs(B, S, M):
    """e4.twin_B, statement for statement, returning the per-cue pairs (validated against the recorded aggregates)."""
    c = B.c
    r = e4.stream(S.seed, e4.ARMS, e4.ARM_TWIN_B, M)
    B._rates(None)
    for _ in range(200):
        B.net.step(r)
    online = [d for d in S.log if d["block"] == M and d["kind"] in HALF3]
    pairs = []
    for d in online:
        k = d["step"]
        sl = dict(S.sched.slot(k), step=k)
        sl["cue"] = B.items[sl["target"] - 1][sl["mask"]]
        B._rates(sl["cue"])
        fm = np.full(c["n"], -1, np.int64)
        fr = np.full(c["m"], -1, np.int64)
        for t in range(c["t_cue"]):
            sp = B.net.step(r)
            m_s, r_s = sp["mem"], sp["rec"]
            if m_s.size:
                m_s = m_s[fm[m_s] < 0]
                fm[m_s] = t
            if r_s.size:
                r_s = r_s[fr[r_s] < 0]
                fr[r_s] = t
        B._rates(None)
        for _ in range(c["t_gap"]):
            B.net.step(r)
        s_ = _orig_score_slot(B, sl, fm, fr)
        pairs.append(dict(step=k, kind=d["kind"], index_online=d["recall"] >= c["recall_bar"], index_settled=s_["recall"] >= c["recall_bar"],
                          content_online=d["joint"], content_settled=s_["joint"], recall_settled=s_["recall"]))
    return pairs


def twin_B_matches(pairs, recorded):
    """Every recorded twin-B aggregate (per kind: n, the four pass fractions, both McNemar counts) must be reproduced.
    The record holds no per-cue pairs, so this is the strongest check available; no record means not verified."""
    if recorded is None:
        return None
    for kd, r in recorded.items():
        P = [p for p in pairs if kd == "all" or p["kind"] == kd]
        mine = dict(n=len(P), memory_online=frac([p["index_online"] for p in P]), memory_settled=frac([p["index_settled"] for p in P]),
                    content_online=frac([p["content_online"] for p in P]), content_settled=frac([p["content_settled"] for p in P]),
                    mcnemar_memory=[sum(p["index_online"] and not p["index_settled"] for p in P),
                                    sum(not p["index_online"] and p["index_settled"] for p in P)],
                    mcnemar_content=[sum(p["content_online"] and not p["content_settled"] for p in P),
                                     sum(not p["content_online"] and p["content_settled"] for p in P)])
        for k, v in r.items():
            if isinstance(v, float) and abs(v - mine[k]) > 1e-12 or not isinstance(v, float) and v != mine[k]:
                return False
    return True


def frac(x):
    return float(np.mean(x)) if len(x) else None


def med(x):
    x = [v for v in x if v is not None]
    return float(np.median(x)) if x else None


def summarise(cues, pairs, hab_items, main_log, c):
    cells = {}
    for name, ip, cp in (("both", True, True), ("content_only", False, True), ("index_only", True, False), ("neither", False, False)):
        sub = [d for d in cues if (d["recall"] >= c["recall_bar"]) == ip and d["joint"] == cp]
        D = [d["diag"] for d in sub]
        cells[name] = dict(
            n=len(sub), by_kind={k: sum(d["kind"] == k for d in sub) for k in HALF3},
            A_recall50=med([d["recall"] for d in sub]), A_recall75=med([x["A_recall75"] for x in D]),
            A75_rescues=frac([x["A_recall75"] >= c["recall_bar"] for x in D]) if sub and name in ("content_only", "neither") else None,
            R_recall50=med([x["R_recall50"] for x in D]), R_size=med([x["R_size"] for x in D]), R_and_A=med([x["R_and_A"] for x in D]),
            latency_A=med([x["latency_A"] for x in D]), latency_R=med([x["latency_R"] for x in D]),
            regen_with_A_candidate=med([x["regen_candidates"]["with_A_candidate"] for x in D if x["regen_candidates"]]),
            regen_only_R_not_A_candidates=med([x["regen_candidates"]["only_R_not_A_candidates"] for x in D if x["regen_candidates"]]),
            regen_only_other_candidates=med([x["regen_candidates"]["only_other_candidates"] for x in D if x["regen_candidates"]]),
            regen_mixed_non_A_candidates=med([x["regen_candidates"]["mixed_non_A_candidates"] for x in D if x["regen_candidates"]]),
            regen_no_earlier_candidate=med([x["regen_candidates"]["no_earlier_candidate"] for x in D if x["regen_candidates"]]),
            age=med([d["age"] for d in sub]),
            offset_global=med([x["offset_global"] for x in D]), offset_assembly=med([x["offset_assembly"] for x in D]))
    n = len(cues)
    d3 = {}
    if pairs:
        fi = [p for p in pairs if not p["index_online"]]
        fc = [p for p in pairs if not p["content_online"]]
        d3 = dict(index_fail_online=len(fi), index_recovered_settled=frac([p["index_settled"] for p in fi]),
                  content_fail_online=len(fc), content_recovered_settled=frac([p["content_settled"] for p in fc]),
                  mcnemar_index=[sum(p["index_online"] and not p["index_settled"] for p in pairs),
                                 sum(not p["index_online"] and p["index_settled"] for p in pairs)],
                  mcnemar_content=[sum(p["content_online"] and not p["content_settled"] for p in pairs),
                                   sum(not p["content_online"] and p["content_settled"] for p in pairs)])
    # D4: habituation against each item's online index pass rate over every main-line probe
    per_item = {}
    for d in main_log:
        if d.get("kind") in ("recent", "uniform", "cohort", "oldest") and "recall" in d:
            per_item.setdefault(d["target"], []).append(d["recall"] >= c["recall_bar"])
    rows = []
    for h in hab_items:
        rows.append(dict(habituated=h["scored"] and h["L_ctl"] >= c["late_need"] and h["L_rep"] <= h["L_ctl"] - c["max_drop"] - 1,
                         eligible=h["scored"] and h["L_ctl"] >= c["late_need"], drop=h["L_ctl"] - h["L_rep"],
                         offset_rise=h["info_rep"]["assembly_offset_rep_end"] - h["info_rep"]["assembly_offset_first"],
                         online_index=frac(per_item.get(h["x"], [])), recovered=h["rec_rep"] >= c["recovery_need"]))
    el = [r for r in rows if r["eligible"]]
    hab = [r for r in el if r["habituated"]]
    non = [r for r in el if not r["habituated"]]
    probes = {h["x"]: len(per_item.get(h["x"], [])) for h in hab_items}
    d4 = dict(n_eligible=len(el), n_habituated=len(hab),
              n_matched_online_habituated=sum(r["online_index"] is not None for r in hab),
              n_matched_online_not=sum(r["online_index"] is not None for r in non),
              online_probes_per_item_median=med(list(probes.values())),
              offset_rise_habituated=med([r["offset_rise"] for r in hab]), offset_rise_not=med([r["offset_rise"] for r in non]),
              corr_drop_offset_rise=float(np.corrcoef([r["drop"] for r in el], [r["offset_rise"] for r in el])[0, 1]) if len(el) > 2 else None,
              online_index_habituated=med([r["online_index"] for r in hab]), online_index_not=med([r["online_index"] for r in non]),
              recovery_among_habituated=frac([r["recovered"] for r in hab]))
    return dict(n_half=n, D1={k: v["n"] for k, v in cells.items()},
                D1_frac={k: (v["n"] / n if n else None) for k, v in cells.items()}, D2=cells, D3=d3, D4=d4)


def load_main_log(rec):
    path = rec["logs"]["main"]["path"]
    with gzip.open(path, "rb") as f:
        return [json.loads(l) for l in f.read().decode().splitlines()]


def run(seed, gated, results_path=record.RESULTS, log=print, c=None):
    t0 = time.time()
    c = e4.CONTRACT if c is None else c
    recs = e4.load_records(results_path)
    kind = "kill_test_seed" if gated else "exploration_seed"
    src = [r for r in recs if r.get("experiment") == "P2-E4" and r.get("kind") == kind and r.get("seed") == seed
           and r.get("contract_digest") == record.digest(c)]
    if not src:
        raise SystemExit(f"no P2-E4 {kind} record for seed {seed}")
    src = src[0]
    rep = [r for r in recs if r.get("experiment") == "P2-E4" and r.get("kind") == "reported_arms" and r.get("seed") == seed
           and r.get("gated") == gated]
    logged = {d["step"]: d for d in load_main_log(src)}
    e4.score_slot = diag_score_slot
    try:
        main = DiagOnline(c, seed)
        out = dict(experiment="P2-E4", kind="diagnosis", seed=seed, gated=gated, source_timestamp=src["timestamp"],
                   plan="docs/plant2/P2-E4-diagnosis-plan.md", loads={})
        mismatches, checked = 0, set()
        for M in c["gate_M"]:
            main.run_to(M)
            for d in main.log:
                if d["step"] in checked:
                    continue
                checked.add(d["step"])
                ref = logged.get(d["step"])
                if ref is None or any(d.get(k) != ref.get(k) for k in COMPARE):
                    mismatches += 1
            cues = [d for d in main.log if d.get("block") == M and d["kind"] in HALF3]
            twin = copy.deepcopy(main)
            twin.diag_main = False
            twin.settle_drift(M, 1)
            pairs = twin_B_pairs(twin, main, M)
            tb_ok = twin_B_matches(pairs, rep[0]["loads"][str(M)]["twin_B"] if rep else None)
            out["loads"][str(M)] = dict(**summarise(cues, pairs, src["loads"][str(M)]["hab_items"], main.log, c),
                                        twin_B_matches_record=tb_ok)
            log(f"seed {seed} M={M}: D1 {out['loads'][str(M)]['D1']} D3 {out['loads'][str(M)]['D3']} ({time.time() - t0:.0f} s)")
        missing_steps = sorted(set(logged) - checked)
        out["reproduction_mismatches"] = mismatches + len(missing_steps)
        out["steps_compared"] = len(checked)
        out["valid"] = out["reproduction_mismatches"] == 0  # D1, D2 and D4 rest on this
        out["D3_verified"] = all(v["twin_B_matches_record"] is True for v in out["loads"].values())
    finally:
        e4.score_slot = _orig_score_slot
    out.update(timestamp=record.now(), git=record.git_state(), runtime=record.runtime(), wall_s=round(time.time() - t0, 1))
    record.append(out, results_path)
    log(f"seed {seed}: diagnosis valid={out['valid']} (mismatches {mismatches})")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--gated", action="store_true")
    a = ap.parse_args(argv)
    if a.gated and a.seed not in e4.GATED_SEEDS:
        raise SystemExit("not a gated seed")
    if a.gated and not [r for r in e4.load_records() if r.get("experiment") == "P2-E4" and r.get("kind") == "kill_test_verdict"]:
        raise SystemExit("the gated diagnosis runs only after the P2-E4 verdict is recorded")
    run(a.seed, a.gated, log=lambda m: print(f"[{record.now()}] {m}", flush=True))


if __name__ == "__main__":
    sys.exit(main())
