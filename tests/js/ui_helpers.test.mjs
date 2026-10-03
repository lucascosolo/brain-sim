// Pins the contract for Evidence.ui, a new namespace of pure UI helpers on
// ui/evidence.js (outcomeCounts, stageChipText, failuresFirst, frameRowKeys),
// plus two evidence.js behaviour changes: "partially gated" headline wording
// and applyStimlog carrying partially_gated_ticks. Run with node's built-in
// test runner: node --test tests/js/*.test.mjs (cwd = repo root; a bare directory
// argument is MODULE_NOT_FOUND on this node, see tests/test_client_evidence.py).
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const Evidence = require("../../ui/evidence.js");

const CLIENT_ID = "abc123";
const RUN_ID = "run-aaaaaa";

function display() {
  return { UNCONFIRMED_AFTER_MS: 1000, TIMELINE_WINDOW_S: 30 };
}

function makeEv(clockRef) {
  const disp = display();
  const ev = Evidence.create({ display: disp, now: () => clockRef.t });
  ev.apply({ type: "hello", client_id: CLIENT_ID });
  return { ev, disp };
}

function hay(ev) {
  return JSON.stringify(ev.state());
}

/* ---------------------------------------------------------------------- */
/* 1. ui.outcomeCounts                                                     */
/* ---------------------------------------------------------------------- */

test("outcomeCounts: null/undefined/no-entries record -> all zero", () => {
  for (const rec of [null, undefined, {}, { entries: null }]) {
    assert.deepEqual(Evidence.ui.outcomeCounts(rec), { pass: 0, fail: 0, reject: 0, other: 0, total: 0 });
  }
});

test("outcomeCounts: tallies pass/fail/reject/other and total", () => {
  const rec = {
    entries: [
      { outcome: "pass" }, { outcome: "pass" }, { outcome: "fail" },
      { outcome: "reject" }, { outcome: "reject" }, { outcome: "reject" },
      { outcome: "weird" },
    ],
  };
  assert.deepEqual(Evidence.ui.outcomeCounts(rec), { pass: 2, fail: 1, reject: 3, other: 1, total: 7 });
});

/* ---------------------------------------------------------------------- */
/* 2. ui.stageChipText                                                     */
/* ---------------------------------------------------------------------- */

test("stageChipText: not-loaded segments when stage records are null/undefined", () => {
  assert.equal(
    Evidence.ui.stageChipText(null, undefined),
    "Stage 0 · record not loaded · Stage 1 · record not loaded"
  );
});

test("stageChipText: worked example with plural forms", () => {
  const stage0 = { entries: [
    ...Array(72).fill({ outcome: "pass" }),
    ...Array(2).fill({ outcome: "fail" }),
  ] };
  const stage1 = { entries: [
    { outcome: "fail" },
    { outcome: "reject" }, { outcome: "reject" },
  ] };
  assert.equal(
    Evidence.ui.stageChipText(stage0, stage1),
    "Stage 0 · 2 kill tests red · Stage 1 · 1 fail 2 rejects"
  );
});

test("stageChipText: singular forms for 1 kill test and 1 reject", () => {
  const stage0 = { entries: [{ outcome: "fail" }] };
  const text0 = Evidence.ui.stageChipText(stage0, null);
  assert.ok(text0.includes("Stage 0 · 1 kill test red"), text0);

  const stage1 = { entries: [{ outcome: "reject" }] };
  const text1 = Evidence.ui.stageChipText(null, stage1);
  assert.ok(text1.includes("Stage 1 · 1 reject") && !text1.includes("1 rejects"), text1);
});

test("stageChipText: stage0 with no kill test red is not a constant string", () => {
  const allPass = { entries: [{ outcome: "pass" }, { outcome: "pass" }] };
  const text = Evidence.ui.stageChipText(allPass, null);
  assert.ok(text.includes("Stage 0 · no kill test red"), text);
  assert.ok(!text.includes("kill tests red"), text);
});

test("stageChipText: stage1 with zero fail/reject and some pass reports pass count", () => {
  const stage1 = { entries: [{ outcome: "pass" }, { outcome: "pass" }, { outcome: "pass" }] };
  const text = Evidence.ui.stageChipText(null, stage1);
  assert.ok(text.includes("Stage 1 · 3 pass"), text);
});

test("stageChipText: stage1 with no results at all", () => {
  const stage1 = { entries: [] };
  const text = Evidence.ui.stageChipText(null, stage1);
  assert.ok(text.includes("Stage 1 · no results recorded"), text);
});

/* ---------------------------------------------------------------------- */
/* 3. ui.failuresFirst                                                     */
/* ---------------------------------------------------------------------- */

test("failuresFirst: orders fail before reject before other before pass, stable within rank", () => {
  const input = [
    { id: 1, outcome: "pass" },
    { id: 2, outcome: "fail" },
    { id: 3, outcome: "other" },
    { id: 4, outcome: "reject" },
    { id: 5, outcome: "fail" },
    { id: 6, outcome: "pass" },
    { id: 7, outcome: "reject" },
  ];
  const inputCopy = JSON.parse(JSON.stringify(input));
  const out = Evidence.ui.failuresFirst(input);
  assert.deepEqual(out.map((e) => e.id), [2, 5, 4, 7, 3, 1, 6]);
  assert.notEqual(out, input, "must return a new array, not the same reference");
  assert.deepEqual(input, inputCopy, "input array must not be mutated");
});

test("failuresFirst: empty array and non-array input both return []", () => {
  assert.deepEqual(Evidence.ui.failuresFirst([]), []);
  assert.deepEqual(Evidence.ui.failuresFirst(null), []);
  assert.deepEqual(Evidence.ui.failuresFirst(undefined), []);
  assert.deepEqual(Evidence.ui.failuresFirst("not an array"), []);
});

/* ---------------------------------------------------------------------- */
/* 4. ui.frameRowKeys                                                      */
/* ---------------------------------------------------------------------- */

// Mirrors brainsim/telemetry.py FRAME_KEYS exactly.
const FRAME_KEYS = [
  "t", "phase", "age_s", "g", "g_struct", "sense_gated", "ticks", "n_syn_alive",
  "syn_born_total", "syn_died_total", "born_per_s", "died_per_s", "spike_total",
  "syn_touched_mean", "born_count", "died_count", "regions", "spikes", "truncated",
  "born", "died", "wall_ratio", "growth_halted", "store_clamped",
  "stim_active", "stim_events", "seq",
];

test("frameRowKeys: missing/non-array fields treated as empty", () => {
  assert.deepEqual(Evidence.ui.frameRowKeys({}), ["spikes", "born / died", "stim_active", "stim_events"]);
  assert.deepEqual(
    Evidence.ui.frameRowKeys({ keys: "nope", growth: null, regions: 5 }),
    ["spikes", "born / died", "stim_active", "stim_events"]
  );
});

test("frameRowKeys: excludes structural keys, sorts scalars, appends growth/regions/tail in order", () => {
  const out = Evidence.ui.frameRowKeys({
    keys: ["t", "g", "type", "run_id", "regions", "spikes", "born", "died", "stim_active", "stim_events", "growth_halted", "age_s"],
    growth: ["ctx_E", "hpc_E"],
    regions: ["hpc", "ctx"],
  });
  assert.deepEqual(out, [
    "age_s", "g", "t",
    "growth_halted.ctx_E", "growth_halted.hpc_E",
    "regions.ctx.rate_hz", "regions.hpc.rate_hz",
    "spikes", "born / died", "stim_active", "stim_events",
  ]);
});

test("frameRowKeys: de-duplicates scalar, growth and region keys", () => {
  const out = Evidence.ui.frameRowKeys({
    keys: ["g", "g", "t"],
    growth: ["ctx_E", "ctx_E"],
    regions: ["ctx", "ctx"],
  });
  assert.deepEqual(out, ["g", "t", "growth_halted.ctx_E", "regions.ctx.rate_hz", "spikes", "born / died", "stim_active", "stim_events"]);
});

test("frameRowKeys: deterministic regardless of input member order", () => {
  const a = Evidence.ui.frameRowKeys({
    keys: ["t", "g", "age_s", "phase"],
    growth: ["hpc_E", "ctx_E", "sense_E"],
    regions: ["hpc", "sense", "ctx"],
  });
  const b = Evidence.ui.frameRowKeys({
    keys: ["phase", "age_s", "g", "t"],
    growth: ["sense_E", "hpc_E", "ctx_E"],
    regions: ["ctx", "hpc", "sense"],
  });
  assert.deepEqual(a, b);
});

test("frameRowKeys: realistic frame with real FRAME_KEYS, growth and region groups", () => {
  const out = Evidence.ui.frameRowKeys({
    keys: FRAME_KEYS,
    growth: ["sense_E", "ctx_E", "ctx_I", "hpc_E", "hpc_I"],
    regions: ["sense", "ctx", "hpc"],
  });
  assert.ok(out.includes("growth_halted.ctx_E"), out.join(","));
  assert.ok(out.includes("regions.hpc.rate_hz"), out.join(","));
  assert.deepEqual(out.slice(-4), ["spikes", "born / died", "stim_active", "stim_events"]);
  assert.ok(!out.includes("growth_halted"), out.join(","));
  assert.ok(!out.includes("regions"), out.join(","));
  assert.ok(!out.includes("type"), out.join(","));
});

/* ---------------------------------------------------------------------- */
/* 5. evidence.js: "partially gated" headline                             */
/* ---------------------------------------------------------------------- */

function acceptedCard(ev, clockRef, stimId, ticks) {
  const msg = ev.send("present", { pattern: 0, ticks });
  ev.apply({
    type: "result", run_id: RUN_ID, req: `${CLIENT_ID}:${msg.req}`, cmd: "present",
    status: "accepted", reason: null, stim_id: stimId, n_cells: 5, amp_mv: 1.3,
    t_accept: 0, t_end_planned: ticks, t_target: null, phase_before: null,
    phase_after: null, changed: null, phase_clock_reset: null, factor: null, t: 0,
  });
}

function endFrame(ev, stimId, delivered, gated, partiallyGated, ticks) {
  return ev.apply({
    type: "frame", t: ticks, seq: 2, phase: "wake", age_s: 0, g: 1, g_struct: 0.05,
    sense_gated: false, ticks, n_syn_alive: 0, syn_born_total: 0, syn_died_total: 0,
    born_per_s: 0, died_per_s: 0, spike_total: 0, syn_touched_mean: 0, born_count: 0,
    died_count: 0, regions: {}, spikes: [], truncated: false, born: [], died: [],
    wall_ratio: 1, growth_halted: {}, store_clamped: false, stim_active: [],
    stim_events: [{
      stim_id: stimId, event: "ended", t: ticks - 1, t_dropped: ticks,
      delivered_ticks: delivered, gated_ticks: gated, partially_gated_ticks: partiallyGated,
    }],
    run_id: RUN_ID,
  });
}

test("ended event with partially_gated_ticks > 0 mentions 'partially gated' and 'N of planned'", () => {
  const clockRef = { t: 0 };
  const { ev } = makeEv(clockRef);
  acceptedCard(ev, clockRef, 21, 200);
  endFrame(ev, 21, 150, 0, 50, 200);
  const text = hay(ev);
  assert.ok(text.includes("partially gated"), text);
  assert.ok(text.includes("150 of 200"), text);
});

test("ended event with partially_gated_ticks === 0 does not mention 'partially gated'", () => {
  const clockRef = { t: 0 };
  const { ev } = makeEv(clockRef);
  acceptedCard(ev, clockRef, 22, 200);
  endFrame(ev, 22, 200, 0, 0, 200);
  assert.ok(!hay(ev).includes("partially gated"), hay(ev));
});

test("ended event with both gated and partially_gated_ticks reports both counts", () => {
  const clockRef = { t: 0 };
  const { ev } = makeEv(clockRef);
  acceptedCard(ev, clockRef, 23, 200);
  endFrame(ev, 23, 100, 80, 20, 200);
  const text = hay(ev);
  assert.ok(text.includes("80 gated"), text);
  assert.ok(text.includes("20 partially gated"), text);
});

/* ---------------------------------------------------------------------- */
/* 6. evidence.js: applyStimlog carries partially_gated_ticks              */
/* ---------------------------------------------------------------------- */

test("stimlog entry fills in partiallyGated on the card and its details", () => {
  const clockRef = { t: 0 };
  const { ev } = makeEv(clockRef);
  ev.apply({ type: "status", running: true, speed: 1, run_id: RUN_ID });
  const msg = ev.send("present", { pattern: 0, ticks: 20 });
  ev.apply({
    type: "result", run_id: RUN_ID, req: `${CLIENT_ID}:${msg.req}`, cmd: "present",
    status: "accepted", reason: null, stim_id: 31, n_cells: 5, amp_mv: 1.3,
    t_accept: 0, t_end_planned: 20, t_target: null, phase_before: null,
    phase_after: null, changed: null, phase_clock_reset: null, factor: null, t: 0,
  });
  ev.apply({
    type: "stimlog", run_id: RUN_ID,
    entries: [{
      stim_id: 31, n_cells: 5, amp_mv: 1.3, t_accept: 0, t_end_planned: 20,
      t_first_applied: 0, t_last_applied: 19, delivered_ticks: 20, gated_ticks: 0,
      partially_gated_ticks: 20, t_dropped: 20, done: true,
    }],
    active: [],
  });
  const card = ev.state().cards[0];
  assert.equal(card.partiallyGated, 20);
  assert.ok(card.details.some(([, v]) => String(v).includes("20 partly gated")), JSON.stringify(card.details));
});
