"""SPEC.md section 6 'One source of truth, enforced mechanically' + section 10 frame contract."""
import os
import re

from brainsim import telemetry
from brainsim.engine import Engine

APP_JS = open("ui/app.js").read()
EVIDENCE_JS_PATH = "ui/evidence.js"
EVIDENCE_JS = open(EVIDENCE_JS_PATH).read() if os.path.exists(EVIDENCE_JS_PATH) else ""
ACCESS_RE = re.compile(r"\b(?:msg|f|frame)\.([A-Za-z_][A-Za-z0-9_]*)")


def _allowed_keys():
    allowed = set(telemetry.FRAME_KEYS) | {"type"}
    for keys in telemetry.REPLY_KEYS.values():
        allowed |= set(keys)
    return allowed


def test_app_js_reads_only_declared_keys():
    allowed = _allowed_keys()
    used = set(ACCESS_RE.findall(APP_JS))
    offenders = used - allowed
    assert not offenders, f"ui/app.js reads undeclared keys: {sorted(offenders)}"


def test_evidence_js_exists_and_reads_only_declared_keys():
    assert EVIDENCE_JS, f"{EVIDENCE_JS_PATH} does not exist yet"
    allowed = _allowed_keys()
    used = set(ACCESS_RE.findall(EVIDENCE_JS))
    offenders = used - allowed
    assert not offenders, f"ui/evidence.js reads undeclared keys: {sorted(offenders)}"


def test_frame_keys_are_the_declaration():
    e = Engine(seed=1)
    e.step(100)
    f = e.frame()
    assert set(f) == set(telemetry.FRAME_KEYS)


def test_frame_fields_equal_engine_state():
    e = Engine(seed=1)
    e.step(1500)
    f = e.frame()
    assert f["phase"] == e.phase
    assert f["g"] == e.g
    assert f["g_struct"] == e.g_struct
    assert f["sense_gated"] == e.sense_gated
    assert f["n_syn_alive"] == e.net.n_alive
    assert f["t"] == e.t
    assert f["age_s"] == e.age_s

    e.set_sleep(True)
    e.step(100)
    f = e.frame()
    assert f["phase"] == "sleep"
    assert f["g"] == e.g
    assert f["sense_gated"] is True
    assert f["sense_gated"] == e.sense_gated


def test_k0_10c_frame_anti_windup_fields_equal_engine_state():
    e = Engine(seed=1)
    e.step(1500)
    f = e.frame()
    assert f["growth_halted"] == e.growth_halted
    assert f["store_clamped"] == e.store_clamped
    assert set(f["growth_halted"]) == {"sense_E", "ctx_E", "ctx_I", "hpc_E", "hpc_I"}


def test_frame_stim_fields_equal_engine_state_at_emission():
    import numpy as np

    e = Engine(seed=1)
    rec = e.inject(np.array([0]), 5.0, 10)
    e.step(1)
    f1 = e.frame()
    assert f1["seq"] == e._frame_seq
    assert f1["stim_active"] == e.stims_active()
    started = [ev for ev in f1["stim_events"] if ev["stim_id"] == rec["stim_id"]]
    assert started and started[0]["event"] == "started" and started[0]["t"] == rec["t_accept"]

    e.step(9)
    f2 = e.frame()
    assert f2["seq"] == f1["seq"] + 1
    assert f2["stim_active"] == e.stims_active()
    ended = [ev for ev in f2["stim_events"] if ev["stim_id"] == rec["stim_id"]]
    assert ended and ended[0]["event"] == "ended"
    assert not any(r["stim_id"] == rec["stim_id"] for r in f2["stim_active"])


def test_no_phase_literals_in_js():
    assert '"WAKE"' not in APP_JS
    assert '"SLEEP"' not in APP_JS


def test_born_per_s_comes_from_engine():
    e = Engine(seed=1)
    born_start = e.stats["syn_born_total"]
    died_start = e.stats["syn_died_total"]
    born_sum = died_sum = 0
    for _ in range(3):
        e.step(1000)
        f = e.frame()
        assert isinstance(f["born_per_s"], int) and f["born_per_s"] >= 0
        assert isinstance(f["died_per_s"], int) and f["died_per_s"] >= 0
        born_sum += f["born_per_s"]
        died_sum += f["died_per_s"]
    assert born_sum == e.stats["syn_born_total"] - born_start
    assert died_sum == e.stats["syn_died_total"] - died_start


def test_every_frame_key_has_a_gloss_in_app_js():
    """Diagnostics 'This run' glosses (KEY_GLOSS in ui/app.js) must cover every scalar frame key;
    growth_halted.* and regions.* get prefix glosses, born/died/regions are drawn, not tabled."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "app.js")).read()
    block = src[src.index("const KEY_GLOSS"):]
    block = block[:block.index("};")]
    glossed = set(re.findall(r'^\s*"?([A-Za-z_][A-Za-z0-9_]*)"?\s*:', block, re.M))
    tabled = set(telemetry.FRAME_KEYS) - {"regions", "growth_halted", "born", "died"}
    missing = tabled - glossed
    assert not missing, f"frame keys without a gloss in KEY_GLOSS: {sorted(missing)}"
