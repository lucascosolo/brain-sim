"""SPEC 8.25: the `gen2` plant profile. Anything needing gen2 runs in a subprocess,
because applying a profile mutates brainsim.params in place."""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UNCHANGED = """
from brainsim import params as p
unchanged = dict(
    sense=p.REGIONS["sense"], hpc=p.REGIONS["hpc"],
    ctx_rest={k: p.REGIONS["ctx"][k] for k in ("w_max", "a_plus", "a_minus", "n_exc", "n_inh")},
    noise_hpc=p.NOISE_SIGMA_MV["hpc"], noise_sense=p.NOISE_SIGMA_MV["sense"],
    proj=[list(x) for x in (p.PROJECTIONS[0], p.PROJECTIONS[1], p.PROJECTIONS[4])],
    scalars=[p.SENSE_SPONT_HZ, p.PATTERN_AMP_MV, p.I_GAIN, p.ETA_SCALING, p.STRUCT_BASE],
)
"""
FIVE = """
five = [p.REGIONS["ctx"]["r_target_exc"], p.REGIONS["ctx"]["r_target_inh"],
        p.NOISE_SIGMA_MV["ctx"], p.PROJECTIONS[2][2], p.PROJECTIONS[3][2]]
"""


def run(code, plant=None, check=True):
    env = {k: v for k, v in os.environ.items() if k != "BRAINSIM_PLANT"}
    env["PYTHONPATH"] = REPO
    if plant is not None:
        env["BRAINSIM_PLANT"] = plant
    r = subprocess.run([sys.executable, "-c", code], env=env, cwd=REPO,
                       capture_output=True, text=True, timeout=300)
    if check:
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    return r


def test_default_plant_untouched():
    out = run(UNCHANGED + FIVE + "import json; print(json.dumps(dict(a=p.ACTIVE_PROFILE, f=five)))")
    assert out["a"] is None
    assert out["f"] == [4.0, 8.0, 2.35, 30, 20]


def test_empty_env_var_is_default_plant():
    out = run(UNCHANGED + FIVE + "import json; print(json.dumps(dict(a=p.ACTIVE_PROFILE, f=five)))", plant="")
    assert out["a"] is None
    assert out["f"] == [4.0, 8.0, 2.35, 30, 20]


def test_gen2_values_and_rest_unchanged():
    code = UNCHANGED + FIVE + """
import json
base = dict(unchanged); print(json.dumps(dict(a=p.ACTIVE_PROFILE, f=five, u=unchanged,
    ctx=[p.PROJECTIONS[2][:2], p.PROJECTIONS[3][:2], p.PROJECTIONS[2][3], p.PROJECTIONS[3][3]])))
"""
    d = run(code, plant="gen2")
    base = run(UNCHANGED + "import json; print(json.dumps(dict(u=unchanged)))")  # default plant
    assert d["a"] == "gen2"
    assert d["f"] == [2.0, 4.0, 2.0, 60, 80]
    assert d["ctx"] == [["ctx", "hpc"], ["hpc", "hpc"], 0.25, 0.25]
    assert d["u"] == base["u"]
    assert d["u"]["noise_hpc"] == 1.8 and d["u"]["noise_sense"] == 0.0
    assert d["u"]["proj"] == [["sense", "ctx", 30, 0.12], ["ctx", "ctx", 40, 0.25], ["hpc", "ctx", 10, 0.25]]
    assert d["u"]["ctx_rest"] == dict(w_max=2.0, a_plus=0.01, a_minus=0.012, n_exc=1600, n_inh=400)


def test_gen2_built_engine_reads_profile():
    code = """
import json
import numpy as np
from brainsim import params as p
from brainsim.engine import Engine
e = Engine(seed=1)
net = e.net
ctx, hpc = net.region_slice["ctx"], net.region_slice["hpc"]
rt, ex = net.r_target, net.is_exc
sv = e._sigma_vec
exp_k = sum(k for _s, dst, k, _g in p.PROJECTIONS if dst == "hpc")
print(json.dumps(dict(
    ctxE=sorted(set(rt[ctx][ex[ctx]].tolist())), ctxI=sorted(set(rt[ctx][~ex[ctx]].tolist())),
    hpcE=sorted(set(rt[hpc][ex[hpc]].tolist())),
    sig_ctx=sorted(set(sv[ctx].tolist())), sig_hpc=sorted(set(sv[hpc].tolist())),
    allowed=[list(t) for t in net.allowed_src["hpc"]],
    k_hpc=sorted(set(e._k_target[hpc].tolist())), exp_k=exp_k,
    p_ok=[e.p.REGIONS["ctx"]["r_target_exc"], e.p.NOISE_SIGMA_MV["ctx"]],
)))
"""
    d = run(code, plant="gen2")
    assert d["ctxE"] == [2.0] and d["ctxI"] == [4.0] and d["hpcE"] == [1.0]
    assert [round(x, 5) for x in d["sig_ctx"]] == [2.0] and [round(x, 5) for x in d["sig_hpc"]] == [1.8]
    assert ["ctx", 60, 0.25] in d["allowed"] and ["hpc", 80, 0.25] in d["allowed"]
    assert d["exp_k"] == 140 and d["k_hpc"] == [140.0]
    assert d["p_ok"] == [2.0, 2.0]


def test_gen2_reaches_driver_params_copy():
    code = """
import json
from tests.k03_pairing import _deepcopyable_params
q = _deepcopyable_params()
print(json.dumps(dict(r=[q.REGIONS["ctx"]["r_target_exc"], q.REGIONS["ctx"]["r_target_inh"]],
    n=q.NOISE_SIGMA_MV["ctx"], k=[q.PROJECTIONS[2][2], q.PROJECTIONS[3][2]], a=q.ACTIVE_PROFILE)))
"""
    d = run(code, plant="gen2")
    assert d == {"r": [2.0, 4.0], "n": 2.0, "k": [60, 80], "a": "gen2"}


def test_unknown_plant_fails_at_import():
    r = run("import brainsim.params", plant="nonsense", check=False)
    assert r.returncode != 0 and "ValueError" in r.stderr


def test_default_plant_determinism_digest_still_passes():
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "tests/test_engine_determinism.py::test_schedule_digest_matches_reference"],
        env={**{k: v for k, v in os.environ.items() if k != "BRAINSIM_PLANT"}, "PYTHONPATH": REPO},
        cwd=REPO, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout[-800:]


def test_profile_api_exists_and_rejects_unknown_without_mutating():
    code = """
import json
from brainsim import params as p
assert callable(p.apply_profile) and "gen2" in p.PROFILES
before = (p.REGIONS["ctx"]["r_target_exc"], p.NOISE_SIGMA_MV["ctx"], list(p.PROJECTIONS))
try:
    p.apply_profile("nope"); raised = False
except ValueError:
    raised = True
after = (p.REGIONS["ctx"]["r_target_exc"], p.NOISE_SIGMA_MV["ctx"], list(p.PROJECTIONS))
print(json.dumps(dict(raised=raised, same=before == after, a=p.ACTIVE_PROFILE)))
"""
    assert run(code) == {"raised": True, "same": True, "a": None}
