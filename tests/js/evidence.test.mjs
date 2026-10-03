// PRD section 5: ui/evidence.js contract. Pure module, no DOM — run with node's
// built-in test runner: node --test tests/js/ (cwd = repo root).
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

test("late result after timeout: unconfirmed then accepted, no resend", () => {
  const clockRef = { t: 0 };
  const { ev, disp } = makeEv(clockRef);
  const msg = ev.send("present", { pattern: 0, ticks: 50 });
  assert.equal(msg.req, "1");
  assert.equal(msg.cmd, "present");

  clockRef.t += disp.UNCONFIRMED_AFTER_MS + 1;
  const timeoutNotes = ev.tick(clockRef.t);
  assert.ok(timeoutNotes.some((n) => /unconfirmed/i.test(n)), timeoutNotes.join("|"));

  const before = hay(ev);
  const acceptNotes = ev.apply({
    type: "result", run_id: RUN_ID, req: `${CLIENT_ID}:${msg.req}`, cmd: "present",
    status: "accepted", reason: null, stim_id: 1, n_cells: 5, amp_mv: 1.3,
    t_accept: 0, t_end_planned: 50, t_target: null, phase_before: null,
    phase_after: null, changed: null, phase_clock_reset: null, factor: null, t: 0,
  });
  assert.ok(acceptNotes.some((n) => /accepted/i.test(n)), acceptNotes.join("|"));
  assert.ok(!/unconfirmed/i.test(hay(ev)), "resolved stim must not still read unconfirmed");

  // nothing is ever resent: a further tick past timeout produces no new send/note churn
  clockRef.t += disp.UNCONFIRMED_AFTER_MS * 2;
  const laterNotes = ev.tick(clockRef.t);
  assert.ok(!laterNotes.some((n) => /unconfirmed/i.test(n)));
});

test("result with foreign req prefix is logged only, ignored for state", () => {
  const clockRef = { t: 0 };
  const { ev } = makeEv(clockRef);
  const before = hay(ev);
  ev.apply({
    type: "result", run_id: RUN_ID, req: "someoneelse:9", cmd: "present",
    status: "accepted", reason: null, stim_id: 99, n_cells: 1, amp_mv: 1.0,
    t_accept: 0, t_end_planned: 50, t_target: null, phase_before: null,
    phase_after: null, changed: null, phase_clock_reset: null, factor: null, t: 0,
  });
  assert.ok(!ev.state().stims[99], "a foreign-prefixed result must not create state");
});

test("gap marks accepted-not-ended cards unknown and asks for stimlog", () => {
  const clockRef = { t: 0 };
  const { ev } = makeEv(clockRef);
  const msg = ev.send("present", { pattern: 0, ticks: 200 });
  ev.apply({
    type: "result", run_id: RUN_ID, req: `${CLIENT_ID}:${msg.req}`, cmd: "present",
    status: "accepted", reason: null, stim_id: 7, n_cells: 5, amp_mv: 1.3,
    t_accept: 0, t_end_planned: 200, t_target: null, phase_before: null,
    phase_after: null, changed: null, phase_clock_reset: null, factor: null, t: 0,
  });
  ev.apply({
    type: "frame", t: 10, seq: 1, phase: "wake", age_s: 0, g: 1, g_struct: 0.05,
    sense_gated: false, ticks: 10, n_syn_alive: 0, syn_born_total: 0, syn_died_total: 0,
    born_per_s: 0, died_per_s: 0, spike_total: 0, syn_touched_mean: 0, born_count: 0,
    died_count: 0, regions: {}, spikes: [], truncated: false, born: [], died: [],
    wall_ratio: 1, growth_halted: {}, store_clamped: false, stim_active: [{ stim_id: 7 }],
    stim_events: [], run_id: RUN_ID,
  });
  const gapNotes = ev.apply({
    type: "frame", t: 50, seq: 9, phase: "wake", age_s: 0, g: 1, g_struct: 0.05,
    sense_gated: false, ticks: 10, n_syn_alive: 0, syn_born_total: 0, syn_died_total: 0,
    born_per_s: 0, died_per_s: 0, spike_total: 0, syn_touched_mean: 0, born_count: 0,
    died_count: 0, regions: {}, spikes: [], truncated: false, born: [], died: [],
    wall_ratio: 1, growth_halted: {}, store_clamped: false, stim_active: [], stim_events: [],
    run_id: RUN_ID,
  });
  assert.ok(gapNotes.some((n) => /stimlog/i.test(n)), gapNotes.join("|"));
  assert.ok(/unknown since/i.test(hay(ev)), hay(ev));
});

test("a matching stimlog entry recovers an unknown stim", () => {
  const clockRef = { t: 0 };
  const { ev } = makeEv(clockRef);
  ev.apply({ type: "status", running: true, speed: 1, run_id: RUN_ID });
  const msg = ev.send("present", { pattern: 0, ticks: 20 });
  ev.apply({
    type: "result", run_id: RUN_ID, req: `${CLIENT_ID}:${msg.req}`, cmd: "present",
    status: "accepted", reason: null, stim_id: 3, n_cells: 5, amp_mv: 1.3,
    t_accept: 0, t_end_planned: 20, t_target: null, phase_before: null,
    phase_after: null, changed: null, phase_clock_reset: null, factor: null, t: 0,
  });
  ev.apply({
    type: "frame", t: 1, seq: 5, phase: "wake", age_s: 0, g: 1, g_struct: 0.05,
    sense_gated: false, ticks: 1, n_syn_alive: 0, syn_born_total: 0, syn_died_total: 0,
    born_per_s: 0, died_per_s: 0, spike_total: 0, syn_touched_mean: 0, born_count: 0,
    died_count: 0, regions: {}, spikes: [], truncated: false, born: [], died: [],
    wall_ratio: 1, growth_halted: {}, store_clamped: false, stim_active: [], stim_events: [],
    run_id: RUN_ID,
  });
  const recoverNotes = ev.apply({
    type: "stimlog", run_id: RUN_ID,
    entries: [{
      stim_id: 3, n_cells: 5, amp_mv: 1.3, t_accept: 0, t_end_planned: 20,
      t_first_applied: 0, t_last_applied: 19, delivered_ticks: 20, gated_ticks: 0,
      t_dropped: 20, done: true,
    }],
    active: [],
  });
  assert.ok(recoverNotes.some((n) => /recovered from stimlog/i.test(n)), recoverNotes.join("|"));
});

test("stimlog without the id at stimlog_max reads history expired", () => {
  const clockRef = { t: 0 };
  const { ev } = makeEv(clockRef);
  const msg = ev.send("present", { pattern: 0, ticks: 20 });
  ev.apply({
    type: "result", run_id: RUN_ID, req: `${CLIENT_ID}:${msg.req}`, cmd: "present",
    status: "accepted", reason: null, stim_id: 1, n_cells: 5, amp_mv: 1.3,
    t_accept: 0, t_end_planned: 20, t_target: null, phase_before: null,
    phase_after: null, changed: null, phase_clock_reset: null, factor: null, t: 0,
  });
  // the client may call history expired only when it knows the log's bound
  ev.apply({ type: "config", run_id: RUN_ID, stimlog_max: 64 });
  const entries = [];
  for (let i = 2; i < 66; i++) entries.push({ stim_id: i, done: true, t_dropped: i + 1 });
  const notes = ev.apply({ type: "stimlog", run_id: RUN_ID, entries, active: [] });
  assert.ok(notes.some((n) => /history expired; end never observed/i.test(n)), notes.join("|"));
});

test("run_id change clears cards/timeline/stims and notes the restart", () => {
  const clockRef = { t: 0 };
  const { ev } = makeEv(clockRef);
  ev.apply({ type: "status", running: true, speed: 1, run_id: RUN_ID });
  const msg = ev.send("present", { pattern: 0, ticks: 20 });
  ev.apply({
    type: "result", run_id: RUN_ID, req: `${CLIENT_ID}:${msg.req}`, cmd: "present",
    status: "accepted", reason: null, stim_id: 1, n_cells: 5, amp_mv: 1.3,
    t_accept: 0, t_end_planned: 20, t_target: null, phase_before: null,
    phase_after: null, changed: null, phase_clock_reset: null, factor: null, t: 0,
  });
  const newRun = "run-bbbbbb";
  const notes = ev.apply({ type: "status", running: true, speed: 1, run_id: newRun });
  assert.ok(notes.some((n) => /simulator restarted/i.test(n) && n.includes(newRun)), notes.join("|"));
  const s = ev.state();
  assert.equal(s.runId, newRun);
  assert.deepEqual(s.cards, []);
  assert.deepEqual(Object.keys(s.stims), []);
});

test("sim stays unknown until a status message arrives, then reflects it", () => {
  const clockRef = { t: 0 };
  const { ev } = makeEv(clockRef);
  assert.equal(ev.state().sim, "unknown");
  ev.apply({ type: "status", running: true, speed: 1, run_id: RUN_ID });
  assert.equal(ev.state().sim, "running");
  ev.apply({ type: "status", running: false, speed: 1, run_id: RUN_ID });
  assert.equal(ev.state().sim, "paused");
});

test("0-tick frames (heartbeats) do not advance the timeline", () => {
  const clockRef = { t: 0 };
  const { ev } = makeEv(clockRef);
  const before = ev.state().timeline.frames.length;
  ev.apply({
    type: "frame", t: 100, seq: 2, phase: "wake", age_s: 0, g: 1, g_struct: 0.05,
    sense_gated: false, ticks: 0, n_syn_alive: 0, syn_born_total: 0, syn_died_total: 0,
    born_per_s: 0, died_per_s: 0, spike_total: 0, syn_touched_mean: 0, born_count: 0,
    died_count: 0, regions: {}, spikes: [], truncated: false, born: [], died: [],
    wall_ratio: 1, growth_halted: {}, store_clamped: false, stim_active: [], stim_events: [],
    run_id: RUN_ID,
  });
  assert.equal(ev.state().timeline.frames.length, before);
});

test("ended event with partial delivery shows 'N of planned' and records source", () => {
  const clockRef = { t: 0 };
  const { ev } = makeEv(clockRef);
  const msg = ev.send("present", { pattern: 0, ticks: 200 });
  ev.apply({
    type: "result", run_id: RUN_ID, req: `${CLIENT_ID}:${msg.req}`, cmd: "present",
    status: "accepted", reason: null, stim_id: 11, n_cells: 5, amp_mv: 1.3,
    t_accept: 0, t_end_planned: 200, t_target: null, phase_before: null,
    phase_after: null, changed: null, phase_clock_reset: null, factor: null, t: 0,
  });
  ev.apply({
    type: "frame", t: 200, seq: 2, phase: "wake", age_s: 0, g: 1, g_struct: 0.05,
    sense_gated: false, ticks: 200, n_syn_alive: 0, syn_born_total: 0, syn_died_total: 0,
    born_per_s: 0, died_per_s: 0, spike_total: 0, syn_touched_mean: 0, born_count: 0,
    died_count: 0, regions: {}, spikes: [], truncated: false, born: [], died: [],
    wall_ratio: 1, growth_halted: {}, store_clamped: false, stim_active: [],
    stim_events: [{
      stim_id: 11, event: "ended", t: 199, t_dropped: 200,
      delivered_ticks: 120, gated_ticks: 80, partially_gated_ticks: 0,
    }],
    run_id: RUN_ID,
  });
  const s = ev.state();
  assert.ok(hay(ev).includes("120 of 200"), hay(ev));
  const card = s.cards.find((c) => c.stim_id === 11) || s.stims[11];
  assert.ok(card, "no card/stim record found for stim_id 11");
  assert.ok(JSON.stringify(card).toLowerCase().includes("ended"),
    "ended event should be recorded as the source: " + JSON.stringify(card));
});

test("ended event with full delivery shows 'N of N'", () => {
  const clockRef = { t: 0 };
  const { ev } = makeEv(clockRef);
  const msg = ev.send("present", { pattern: 0, ticks: 200 });
  ev.apply({
    type: "result", run_id: RUN_ID, req: `${CLIENT_ID}:${msg.req}`, cmd: "present",
    status: "accepted", reason: null, stim_id: 12, n_cells: 5, amp_mv: 1.3,
    t_accept: 0, t_end_planned: 200, t_target: null, phase_before: null,
    phase_after: null, changed: null, phase_clock_reset: null, factor: null, t: 0,
  });
  ev.apply({
    type: "frame", t: 200, seq: 2, phase: "wake", age_s: 0, g: 1, g_struct: 0.05,
    sense_gated: false, ticks: 200, n_syn_alive: 0, syn_born_total: 0, syn_died_total: 0,
    born_per_s: 0, died_per_s: 0, spike_total: 0, syn_touched_mean: 0, born_count: 0,
    died_count: 0, regions: {}, spikes: [], truncated: false, born: [], died: [],
    wall_ratio: 1, growth_halted: {}, store_clamped: false, stim_active: [],
    stim_events: [{
      stim_id: 12, event: "ended", t: 199, t_dropped: 200,
      delivered_ticks: 200, gated_ticks: 0, partially_gated_ticks: 0,
    }],
    run_id: RUN_ID,
  });
  assert.ok(hay(ev).includes("200 of 200"), hay(ev));
});

test("accepted-not-started card text depends on sim state", () => {
  for (const [running, phrase] of [[true, "waiting for ticks"], [false, "waiting for the simulator to run"]]) {
    const clockRef = { t: 0 };
    const { ev } = makeEv(clockRef);
    ev.apply({ type: "status", running, speed: 1, run_id: RUN_ID });
    const msg = ev.send("present", { pattern: 0, ticks: 20 });
    ev.apply({
      type: "result", run_id: RUN_ID, req: `${CLIENT_ID}:${msg.req}`, cmd: "present",
      status: "accepted", reason: null, stim_id: 1, n_cells: 5, amp_mv: 1.3,
      t_accept: 0, t_end_planned: 20, t_target: null, phase_before: null,
      phase_after: null, changed: null, phase_clock_reset: null, factor: null, t: 0,
    });
    assert.ok(hay(ev).includes(phrase), `${phrase} not found for running=${running}: ${hay(ev)}`);
  }

  const clockRef = { t: 0 };
  const { ev } = makeEv(clockRef);
  const msg = ev.send("present", { pattern: 0, ticks: 20 });
  ev.apply({
    type: "result", run_id: RUN_ID, req: `${CLIENT_ID}:${msg.req}`, cmd: "present",
    status: "accepted", reason: null, stim_id: 1, n_cells: 5, amp_mv: 1.3,
    t_accept: 0, t_end_planned: 20, t_target: null, phase_before: null,
    phase_after: null, changed: null, phase_clock_reset: null, factor: null, t: 0,
  });
  assert.ok(hay(ev).includes("simulator state unknown"), hay(ev));
});
