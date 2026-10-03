"use strict";
/* brain-sim client. Transport is the real WebSocket at /ws; every command
   result is reconciled by ui/evidence.js, which is the only thing allowed to
   decide what a command did. This file draws and nothing more: it never
   infers simulator state from the absence of a message. */

/* ---- Client display preferences — not simulator parameters ----------------
   Choices this page makes about how to draw and how long to wait. They never
   come from the worker and are never presented as engine facts.             */
const DISPLAY = {
  TIMELINE_WINDOW_S: 30,      // how much simulated time the timeline shows
  UNCONFIRMED_AFTER_MS: 1000, // when a sent command starts reading "unconfirmed"
  GLOW_MS: 150,               // spike glow fade, wall time
  STRUCT_FLASH_MS: 400,       // birth/death segment flash, wall time
  CARD_HISTORY_MAX: 6,        // rows kept in the Observe feedback list
  DETAILS_HISTORY_MAX: 64,    // rows kept in the Diagnostics command history
  EXPLAIN_STORE_PREFIX: "brainsim.explain."  // localStorage key per explainer panel
};

/* ---- How evidence reconciles (mirrored in Diagnostics) --------------------
   1. A `result` sets acceptance/rejection. Nothing else can.
   2. `stim_events` set start/end when observed. Absence from `stim_active`
      sets nothing.
   3. A gap (seq jump or t discontinuity) marks every card accepted and not
      ended as "unknown since t = <last observed tick>" and requests stimlog.
   4. A stimlog entry with a matching stim_id fills what is unknown; the row
      says "recovered from stimlog".
   5. If stimlog has no such stim_id (history expired, or a different run) the
      row reads "history expired; end never observed". Nothing is filled in.
   6. On reconnect in the same run: layout, config, status and stimlog are
      re-requested; the unobserved span is a gap; rules 3-5 apply.
   7. A result after the unconfirmed timeout replaces "unconfirmed"; nothing
      is ever resent automatically.                                          */

const WINDOW_S = DISPLAY.TIMELINE_WINDOW_S;

const EV = Evidence.create({ display: DISPLAY, now: () => performance.now() });
let VS = EV.state();                 // last evidence snapshot, refreshed on change

let C = null;                        // config message
let L = null;                        // layout message
const st = {
  conn: "connecting", lastFrameAt: 0, retryIn: 0, backoff: 500, retryAt: 0, ws: null,
  reqRun: null, reqSpeed: 1,
  lastFrame: null,
  bright: null, N: 0, px: null, py: null, boxes: {}, regionNames: [],
  selected: null, selectedRegion: null, cursor: null, topIn: [], hoverPattern: null,
  ripples: [], bornFlash: [], deathFlash: [],
  drag: null, selection: [], synOn: false, syn: null, structOn: false,
  log: [], tab: "observe", synHist: [], rowSig: null, fullSig: null, lineSegments: 0,
  records: { 0: null, 1: null }, explainOpen: Object.create(null), keyRows: null,
  wcardSig: null
};
const UI = Evidence.ui;   // pure display helpers, node-tested in tests/js/ui_helpers.test.mjs
const $ = s => document.querySelector(s);
const el = {
  connpill: $("#connpill"), simpill: $("#simpill"), phasebadge: $("#phasebadge"),
  hsimt: $("#hsimt"), hspeed: $("#hspeed"), cmdlist: $("#cmdlist"), framelabel: $("#framelabel"),
  runbtn: $("#runbtn"), runline: $("#runline"), speedline: $("#speedline"), measline: $("#measline"), sleepline: $("#sleepline"),
  schedline: $("#schedline"), patcaption: $("#patcaption"), patgrid: $("#patgrid"),
  synlabel: $("#synlabel"), sublabel: $("#sublabel"), tlnote: $("#tlnote"),
  drawer: $("#drawer"), drawerbody: $("#drawerbody"), drawertitle: $("#drawertitle"),
  legGlow: $("#leg-glow"), tllegend: $("#tllegend"), rasternote: $("#rasternote"),
  hg: $("#hg"), hgstruct: $("#hgstruct"), warnchip: $("#warnchip"), stagechip: $("#stagechip"),
  encodestage: $("#encodestage"), wcaption: $("#wcaption"), wcard: $("#wcard"),
  heterostats: $("#heterostats"), heteroCells: $("#heteroCells")
};
const map = $("#map"), mctx = map.getContext("2d");
const tlc = $("#timeline"), tctx = tlc.getContext("2d");
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

function fmtT(ticks) { return C ? (ticks * C.dt_ms / 1000).toFixed(2) + " s" : ticks + " ticks"; }
function tickWord(n) { return n === 1 ? "1 tick" : n.toLocaleString() + " ticks"; }
function msOf(n) { return C ? (n * C.dt_ms) : n; }
function letterOf(i) { return String.fromCharCode(65 + i); }
function secWord(ticks) { return C ? (msOf(ticks) / 1000) : null; }

/* ---- "What am I looking at?" explainers ------------------------------------
   Plain-words descriptions of what each readout IS, for a reader who does not
   know what a neuron, a spike, a synapse or a hertz is. Rules, same as the
   inspector's `measure` lines and `patcaption`:
   - the static text never states a value; every number inside one is
     interpolated from the config reply (`C`) or the layout reply (`L`);
   - nothing here claims the network learns, remembers, recognises or binds
     anything, and ctx/hpc are named after brain structures, not models of them.
   Each block is collapsed by default; whether it is open is a display
   preference of this page, kept in this browser's localStorage.            */
const EXPLAIN = {
  header: () => [
    "The top strip is this page's own status first, then the simulator's. “live” means data packets are " +
    "arriving in this browser right now; “stale” and “disconnected” describe the connection, not " +
    "the simulator. “running” or “paused” is the simulator's state, and it changes only when the " +
    "simulator says so.",
    "“simulated time” is how much time has passed inside the simulation since this run started. It is not " +
    "clock time: the simulator can run faster or slower than real life." +
    (C ? ` One step of simulated time is ${C.dt_ms} ms.` : ""),
    "“plasticity gain g” is how much a connection between two cells is allowed to change strength at each " +
    "event that changes it. “structural gain” is how fast connections are created and destroyed. Both are " +
    "the simulator's own numbers and both change during a run.",
    "“asked / accepted / measured” are three separate facts about speed, in simulated seconds per real " +
    "second: what this page asked for, what the simulator said it would do, and what it actually achieved. They can " +
    "disagree, and when they do the disagreement is the point.",
    "“sense gated” next to the phase means input from outside is being blocked right now, so a stimulus " +
    "sent now is refused. “engine last confirmed: …” is the simulated time of the last reply that " +
    "confirmed running or paused — it is a receipt for something that already happened, not a claim about this " +
    "instant. “Step” asks the simulator to advance one step of simulated time while it is paused.",
    "The chip on the right counts the recorded test results below on the Diagnostics tab; it never changes colour. " +
    "A separate amber chip appears to its left only while the simulator reports a halted group or a full " +
    "connection store (see the growth_halted and store_clamped rows under This run)."
  ],
  map: () => [
    "Every dot is one cell. The columns are the named groups of cells the simulator was built with, and the number " +
    "after a name is how many cells that group has.",
    "A dot brightens when its cell fired in the packet just received, then fades. The fade is this page drawing, " +
    "not the cell carrying on — its length is listed under Client display preferences.",
    "Blue dots are excitatory cells: when one fires it pushes the cells it connects to toward firing. Orange dots " +
    "are inhibitory: they push them away from firing. The amber ring marks the patch of cells a Stimulate button " +
    "drives.",
    "“sampled connections” draws a fixed random subset of the wires between cells" +
    (L && L.synapse_sample ? ` (${L.synapse_sample.length.toLocaleString()} of them)` : "") +
    " — a sample, never all of them. “structural changes” flashes a line wherever a connection was " +
    "just created or destroyed. The simulator rewires itself continuously, so seeing these constantly is normal and " +
    "not a fault.",
    "The line under the picture says which packet is being drawn, how much simulated time it covered, and how many " +
    "connections were created and destroyed inside it."
  ],
  timeline: () => [
    "One row per group of cells, reading left to right over the last " + DISPLAY.TIMELINE_WINDOW_S +
    " seconds of simulated time.",
    "Each bar is one data packet. Its height is that group's average number of spikes per second per cell during " +
    "that packet — in other words, how busy the group was. A spike is the brief event a cell produces when it " +
    "fires.",
    "The small number in the left gutter, printed as “max … Hz”, is the top of that row's scale, not " +
    "a reading and not a goal. Each row is scaled on its own, so two bars of the same height in different rows are " +
    "not the same rate.",
    "No target line is drawn. The simulator does keep a target rate per group internally, but it does not send one " +
    "in any reply this page receives, and the page will not draw a line it cannot source.",
    "The amber marks on the top strip are stimuli, drawn only as far as the simulator actually confirmed them. A " +
    "hatched band is simulated time this page did not see, and the wash of colour behind the bars is the wake or " +
    "sleep phase."
  ],
  stimulate: () => [
    "Each lettered button drives the same fixed patch of cells in the input group every time, with a small current, " +
    "for a fixed length of simulated time" +
    (C ? ` (${C.pattern_amp_mv} mV for ${msOf(C.pattern_ticks)} ms)` : "") + ". Those three things are the " +
    "simulator's own settings, not choices made here.",
    "A letter is a place to poke, nothing more. Nothing on this page claims the network recognises A, B, C or D, or " +
    "that presenting one stores anything.",
    "“Custom injection” lets you drag a rectangle on the map and drive whichever cells fall inside it. " +
    "Amplitude is how hard, in millivolts; duration is how long, in steps of simulated time. This page does not " +
    "limit what you type — the simulator applies its own limits and its reply says so when it refuses.",
    "While the simulator is in its sleep phase, input from outside is blocked and a stimulus aimed only at input " +
    "cells is refused outright. The refusal appears as a row under Command feedback."
  ],
  cmdfeedback: () => [
    "One row per command this page has sent, newest first, keeping the last " + DISPLAY.CARD_HISTORY_MAX + ".",
    "A row says only what a reply or an observed event established. “sent · no reply yet” means " +
    "exactly that. “accepted · waiting for ticks” means the simulator took the command but no " +
    "simulated time carrying it has been seen yet. “delivered” counts are the simulator's own.",
    "If this page missed data packets while a stimulus was running, the row says the end was not observed instead " +
    "of assuming it finished. That is deliberate: a gap is reported, never filled in.",
    "Open “details” on a row to see the raw fields the reply carried."
  ],
  schedule: () => [
    "The simulator switches between a wake phase and a sleep phase by itself, on a fixed timer" +
    (C ? ` of ${secWord(C.wake_ticks)} s awake and ${secWord(C.sleep_ticks)} s asleep` : "") + ".",
    "“g” is the plasticity gain: how much a connection's strength is allowed to change at each event that " +
    "changes it. It is higher awake and lower asleep" +
    (C ? ` (${C.g_wake} awake, ${C.g_sleep} asleep)` : "") + ". Both values come from the simulator's config reply.",
    "While asleep, input from outside is blocked. Sleep here is a phase with different settings and a blocked " +
    "input — nothing is replayed or rehearsed during it.",
    "“Sleep now” and “Wake now” switch the phase immediately and restart the phase timer. " +
    "Neither one latches: the timer takes over again from that moment."
  ],
  diagkeys: () => [
    "The contents of the newest data packet, one row per field, exactly as received. The “what it is” " +
    "column is a one-line description written by hand from the simulator's source code; the value column is the " +
    "packet's own.",
    "Rows never move. Every field a packet can carry has a row from the moment the layout arrives, in a fixed order, " +
    "and only the text inside a value cell changes — so a number growing a digit cannot push anything up or " +
    "down the page."
  ],
  raster: () => [
    "One strip per group of cells. Each thin column is one step of simulated time" +
    (C ? ` (${C.dt_ms} ms)` : "") + " and its brightness is how many cells of that group fired in that step.",
    "Brightness is scaled within each arriving packet, so a bright column means busy relative to the rest of that " +
    "packet, not a fixed number of spikes.",
    "It scrolls right to left, newest at the right. A dark hatched column marks simulated time this page did not " +
    "observe."
  ],
  config: () => [
    "The simulator's own parameters, exactly as it reported them when this page connected.",
    "This panel is the source of truth for every number on this page that describes how the simulator is set up. If " +
    "something elsewhere on the page disagrees with this panel, this panel is right and the other place is a bug."
  ],
  dispprefs: () => [
    "Choices this page makes about drawing and waiting: how long a dot's glow takes to fade, how much history to " +
    "keep, how long before an unanswered command is called unconfirmed.",
    "None of these come from the simulator and none of them change it. They are listed on their own so that no " +
    "drawing choice can be mistaken for a measurement.",
    "Whether each “What am I looking at?” block is open is also a display preference. It is remembered in " +
    "this browser only and is listed below."
  ],
  recon: () => [
    "This page never guesses what a command did.",
    "These rules say what is allowed to change a command's reported state, and in what order. In short: only a " +
    "reply can accept or reject a command; only an observed event can start or end a stimulus; and if this page " +
    "missed data packets, it reports the gap rather than filling it in.",
    "They are written out here so that you can check any row under Command feedback against them."
  ],
  rules: () => [
    "A description, written by hand, of the update rules the simulator runs. The simulator does not report these " +
    "rules, so this text can drift from the code; the keys named under each rule are there so you can check it.",
    "Rules 2 to 5 change the strength of existing connections. Rules 6 and 7 create and destroy connections and " +
    "decide when to stop. Strengths changing and wiring changing are what the simulator does; neither is a claim " +
    "that the network has learned or stored anything.",
    "Keys marked “config reply” can be checked against the Config panel above. Keys marked " +
    "“params.py, not reported” are real settings the simulator does not send, so this page cannot show " +
    "their values and does not invent them."
  ],
  recorded: () => [
    "Test outcomes copied here from runs performed outside this page. This page did not measure any of them, and a " +
    "live run that looks healthy on the Observe tab does not change a single row.",
    "Stage 0 rows come from the file ui/stage0_results.json and Stage 1 rows from ui/stage1_results.json. Each row " +
    "names the test, the exact commit it was run at, and where its evidence lives.",
    "“fail” means the test ran and its criterion was not met. “reject” means a candidate change " +
    "was tried and not adopted. Failures and rejects are listed first inside each group, so that a small number of " +
    "red rows cannot hide among green ones."
  ],
  inspector: () => [
    "Click a cell on the map, or a group name above it, to open the inspector on the right. It re-reads the " +
    "simulator a few times a second, and every number in it carries a line saying what it is.",
    "For one cell: its voltage right now and the threshold it must cross to fire, its recent firing rate, how many " +
    "connections come in and go out, and its strongest incoming connections — a subset of them, not all.",
    "For a group: how many cells, the average rate, connection counts, and two histograms. A histogram is a count " +
    "of how many things fall into each bucket: one counts connections by strength, the other counts cells by firing " +
    "rate. They describe the current state of the wiring and nothing more.",
    "The two boxes above show the last raw reply of each kind, unedited."
  ]
};

function explainStoreKey(key) { return DISPLAY.EXPLAIN_STORE_PREFIX + key; }
function readExplainPrefs() {
  for (const host of document.querySelectorAll(".explainhost")) {
    const key = host.dataset.explain;
    let v = null;
    try { v = localStorage.getItem(explainStoreKey(key)); } catch (err) { v = null; }
    st.explainOpen[key] = v === "open";
  }
}
function renderExplainers() {
  for (const host of document.querySelectorAll(".explainhost")) {
    const key = host.dataset.explain;
    const make = EXPLAIN[key];
    if (!make) continue;
    const open = !!st.explainOpen[key];
    const body = make().map(p => `<p class="measure">${E(p)}</p>`).join("");
    const sig = open + "|" + body;
    if (host.dataset.sig === sig) continue;
    host.dataset.sig = sig;
    host.innerHTML = `<details class="explain"${open ? " open" : ""}>` +
      `<summary>What am I looking at?</summary><div class="explainbody">${body}</div></details>`;
  }
  renderExplainPrefLine();
}
document.addEventListener("toggle", e => {
  const d = e.target;
  if (!d || d.tagName !== "DETAILS" || !d.classList.contains("explain")) return;
  const host = d.parentElement;
  if (!host || !host.dataset || !host.dataset.explain) return;
  const key = host.dataset.explain;
  st.explainOpen[key] = d.open;
  host.dataset.sig = d.open + "|" + host.dataset.sig.split("|").slice(1).join("|");
  try { localStorage.setItem(explainStoreKey(key), d.open ? "open" : "closed"); } catch (err) { /* private mode */ }
  renderExplainPrefLine();
}, true);
function renderExplainPrefLine() {
  const line = $("#explainprefline");
  if (!line) return;
  const open = Object.keys(st.explainOpen).filter(k => st.explainOpen[k]).sort();
  line.textContent =
    `"What am I looking at?" open/closed state, per panel, is a display preference of this page: ` +
    `stored in this browser's localStorage under ${DISPLAY.EXPLAIN_STORE_PREFIX}* and never sent anywhere. ` +
    `Open now: ${open.length ? open.join(", ") : "none"}.`;
}

/* ---- transport ---- */
function connect() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  let ws;
  try { ws = new WebSocket(proto + "//" + location.host + "/ws"); }
  catch (err) { socketClosed(); return; }
  st.ws = ws;
  ws.onopen = () => {
    st.backoff = 500;
    st.conn = "live"; EV.setConn("live");
    /* rule 6: prevT/prevSeq are kept, so the unobserved span becomes a gap */
    EV.reconnected();
    drainRequests();
    refresh();
  };
  ws.onmessage = e => {
    if (ws !== st.ws) return;
    let m; try { m = JSON.parse(e.data); } catch (err) { return; }
    onMessage(m);
  };
  ws.onclose = () => { if (ws === st.ws) socketClosed(); };
  ws.onerror = () => { if (ws !== st.ws) return; try { ws.close(); } catch (err) { socketClosed(); } };
}
function socketClosed() {
  if (st.conn === "disconnected") return;
  st.conn = "disconnected"; EV.setConn("disconnected");
  st.backoff = Math.min(8000, st.backoff || 500);
  st.retryAt = performance.now() + st.backoff;
  renderHeader(); renderRows();
}
function socketOpen() { return !!st.ws && st.ws.readyState === WebSocket.OPEN; }
function raw(obj) {
  if (!socketOpen()) return false;
  logMsg("out", obj);
  st.ws.send(JSON.stringify(obj));
  return true;
}
function drainRequests() { for (const cmd of EV.takeRequests()) raw({ cmd: cmd }); }
function sendTracked(cmd, fields, label, meta) {
  /* nothing may claim "sent" that was not written to an open socket */
  const open = socketOpen();
  const out = EV.send(cmd, fields,
    Object.assign({ label: label }, meta || {}, open ? {} : { status: "not_sent" }));
  if (open) raw(out); else logMsg("out", Object.assign({ not_sent: true }, out));
  refresh(); renderRows();
  return EV.card(out.req);
}

/* ---- the single entry point ---- */
function onMessage(msg) {
  logMsg("in", msg);
  const notes = EV.apply(msg);
  /* the same gap detection the timeline uses, so every observed-time view
     breaks in the same place */
  st.gapNow = notes.some(t => t.indexOf("observation gap") === 0);
  drainRequests();
  for (const n of notes) if (n.indexOf("simulator restarted") === 0) onRestart(n);
  refresh();

  if (msg.type === "config") { C = msg; applyConfig(); return; }
  if (msg.type === "layout") { L = msg; applyLayout(); return; }
  if (msg.type === "status") { renderHeader(); renderControls(); return; }
  if (msg.type === "frame") { applyFrame(msg); return; }
  if (msg.type === "inspect") { renderNeuron(msg); return; }
  if (msg.type === "region") { renderRegion(msg); return; }
  renderRows(); renderControls();
}
function refresh() { VS = EV.state(); }

/* evidence from a different run is never attached to existing state */
function onRestart(note) {
  st.ripples = []; st.bornFlash = []; st.deathFlash = []; st.synHist = [];
  st.lastFrame = null; st.rowSig = null; st.fullSig = null;
  st.wcardSig = null; el.wcard.innerHTML = "";
  sleepWatch = null; el.sleepline.textContent = "—";
  const b = $("#restartbanner");
  b.hidden = false;
  b.firstElementChild.textContent = note;
  renderRows(); renderHeader();
}

function applyConfig() {
  const patchN = L && L.patterns && L.patterns.length ? L.patterns[0].length : null;
  el.patcaption.textContent = patchN
    ? `each drives a fixed patch of ${patchN} sense cells at ${C.pattern_amp_mv} mV for ` +
    `${msOf(C.pattern_ticks)} ms; a stimulus location, not a learned concept`
    : "—";
  el.schedline.textContent =
    `Phase schedule is automatic: ${msOf(C.wake_ticks) / 1000} s wake, ${msOf(C.sleep_ticks) / 1000} s sleep. ` +
    `In sleep g = ${C.g_sleep} and sense input is gated. "Sleep now" enters sleep immediately and restarts the phase clock; it is not a latch.`;
  el.rasternote.textContent = `spikes per tick (dt = ${C.dt_ms} ms), scrolling`;
  $("#injdefaults").textContent =
    `amplitude is in millivolts, duration in ticks of ${C.dt_ms} ms. For comparison, the lettered buttons above use ` +
    `the simulator's own pattern settings: ${C.pattern_amp_mv} mV for ${C.pattern_ticks} ticks (${msOf(C.pattern_ticks)} ms).`;
  $("#rule-stimlogmax").textContent = C.stimlog_max;
  $("#heteroTrigger").textContent = C.hetero_trigger_spikes;
  $("#cfgjson").textContent = JSON.stringify(C, null, 1);
  renderPatterns(); renderControls(); renderExplainers(); renderEncodeButtons();
}

function applyLayout() {
  st.N = L.x.length;
  st.px = new Float32Array(st.N); st.py = new Float32Array(st.N);
  if (!st.bright || st.bright.length !== st.N) st.bright = new Float32Array(st.N);
  st.regionNames = Object.keys(L.regions);
  st.keyRows = null;
  /* a layout belongs to one run: chips drawn from an older run's W are dropped */
  st.wcardSig = null; el.wcard.innerHTML = "";
  layoutBoxes(); renderRegionHeads(); renderPatterns(); buildSyn(); buildRasters();
  renderExplainers(); renderCtxSampleLabel();
  if (st.lastFrame) buildKeyRows();
}

/* The 60-cell ctx set is chosen by this page, not defined by the simulator, and
   the button says which cells it is so it cannot read as a defined stimulus. */
const CTX_SAMPLE_STRIDE = 17, CTX_SAMPLE_MAX = 60;
function ctxSampleIds() {
  const ids = [];
  if (!L || !L.regions.ctx) return ids;
  const rid = L.regions.ctx.id;
  for (let i = 0; i < st.N && ids.length < CTX_SAMPLE_MAX; i++)
    if (L.region[i] === rid && i % CTX_SAMPLE_STRIDE === 0) ids.push(i);
  return ids;
}
function renderCtxSampleLabel() {
  const n = ctxSampleIds().length;
  $("#injctx").textContent = `Inject ${n} ctx cells`;
  $("#injctx").disabled = false;
  $("#injctxnote").textContent =
    `page-chosen sample: every ${CTX_SAMPLE_STRIDE}th ctx cell by id, up to ${CTX_SAMPLE_MAX}. ` +
    `The simulator does not define this set; this page picked it.`;
}

function layoutBoxes() {
  const w = map.width / dpr(), h = map.height / dpr();
  const weights = st.regionNames.map(n => Math.sqrt(L.regions[n].n));
  const tot = weights.reduce((a, b) => a + b, 0);
  let cx = 6;
  st.boxes = {};
  st.regionNames.forEach((n, i) => {
    const bw = (w - 12 - 8 * (st.regionNames.length - 1)) * weights[i] / tot;
    st.boxes[n] = { x: cx, y: 6, w: bw, h: h - 12 };
    cx += bw + 8;
  });
  for (let i = 0; i < st.N; i++) {
    const b = st.boxes[st.regionNames[L.region[i]]];
    if (!b) continue;
    st.px[i] = b.x + L.x[i] * b.w; st.py[i] = b.y + L.y[i] * b.h;
  }
  buildSyn();
}
function dpr() { return Math.min(2, window.devicePixelRatio || 1); }

function buildSyn() {
  if (!L || !st.px) return;
  const off = document.createElement("canvas");
  off.width = map.width; off.height = map.height;
  const o = off.getContext("2d"); o.scale(dpr(), dpr());
  o.strokeStyle = "rgba(106,168,224,0.11)"; o.lineWidth = 1; o.beginPath();
  for (const [, pre, post] of L.synapse_sample) {
    o.moveTo(st.px[pre], st.py[pre]); o.lineTo(st.px[post], st.py[post]);
  }
  o.stroke(); st.syn = off;
}

function applyFrame(f) {
  st.lastFrameAt = performance.now();
  if (st.conn !== "live") { st.conn = "live"; EV.setConn("live"); }
  st.lastFrame = f;

  if (st.bright) for (const [id] of f.spikes) if (id < st.N) st.bright[id] = 1;
  const nowW = performance.now();
  if (st.structOn) {
    for (const [pre, post] of f.born.slice(0, 300)) st.bornFlash.push({ pre, post, at: nowW });
    for (const [pre, post] of f.died.slice(0, 300)) st.deathFlash.push({ pre, post, at: nowW });
  }
  /* one authored motion moment: the patch a confirmed stimulus starts on */
  if (!reduced) for (const se of f.stim_events || []) {
    if (se.event !== "started") continue;
    const card = VS.stims[se.stim_id];
    if (card && card.cells && card.cells.length) st.ripples.push({ cells: card.cells, at: nowW });
  }

  renderHeader(); renderFrameLabel(f); renderRows(); renderEncode(f); renderHetero(f);
  if (st.tab === "diag") renderFrameKeys(f);
  pushRasters(f);
  st.gapNow = false;
}

/* ---- connection health ---- */
function connectionTick() {
  const nowW = performance.now();
  EV.tick(nowW);
  if (st.conn === "disconnected") {
    st.retryIn = Math.max(0, (st.retryAt - nowW) / 1000);
    if (st.retryIn <= 0) {
      st.backoff = Math.min(8000, (st.backoff || 500) * 2);
      st.retryAt = nowW + st.backoff;
      connect();
    }
  } else if (st.conn === "live" && st.lastFrameAt && nowW - st.lastFrameAt > 2000) {
    st.conn = "stale"; EV.setConn("stale");
  }
  refresh();
  renderHeader(); renderRows();
}
setInterval(connectionTick, 200);

/* ---- header ---- */
function renderHeader() {
  const f = st.lastFrame;
  const cp = el.connpill, t = cp.querySelector(".t");
  cp.className = "pill";
  if (st.conn === "live") { cp.classList.add("live"); t.textContent = "live"; }
  else if (st.conn === "stale") {
    cp.classList.add("warn");
    t.textContent = "stale " + Math.floor((performance.now() - st.lastFrameAt) / 1000) + " s";
  } else if (st.conn === "disconnected") {
    cp.classList.add("bad");
    t.textContent = "disconnected, retry in " + st.retryIn.toFixed(1) + " s";
  } else t.textContent = "connecting";

  const sp = el.simpill, s = sp.querySelector(".t");
  sp.className = "pill";
  if (VS.sim === "running") {
    sp.classList.add("live");
    s.textContent = (f && f.ticks === 0 && st.conn === "live")
      ? "running, 0 ticks in last frame" : "running";
  } else if (VS.sim === "paused") { s.textContent = "paused"; }
  else { s.textContent = "unknown"; }
  if (st.conn === "stale" || st.conn === "disconnected") {
    sp.classList.add("dimmed");
    if (VS.lastStatus) s.textContent += " · last status at t = " + fmtT(VS.lastStatus.t);
  }

  if (f && C) {
    const ph = f.phase === "sleep" ? "sleep" : (f.phase === "wake" ? "wake" : "");
    el.phasebadge.className = "badge " + ph;
    el.phasebadge.innerHTML = E(f.phase) + (f.sense_gated
      ? ' <svg width="10" height="11" viewBox="0 0 10 11" fill="none" aria-hidden="true"><rect x="1" y="4.5" width="8" height="6" rx="1.4" stroke="currentColor" stroke-width="1.2"/><path d="M3 4.5V3a2 2 0 1 1 4 0v1.5" stroke="currentColor" stroke-width="1.2"/></svg> sense gated'
      : "");
    /* age_s is t · dt_ms / 1000 computed by the engine itself, so the page shows
       the engine's own number once rather than recomputing the same quantity */
    el.hsimt.textContent = Number(f.age_s).toFixed(2);
    el.hg.textContent = String(f.g);
    el.hgstruct.textContent = Number(f.g_struct).toFixed(3);
    renderWarnChip(f);
  }
  const acc = VS.lastStatus ? (VS.lastStatus.speed === 0 ? "max" : VS.lastStatus.speed + "x") : "—";
  const meas = measuredThroughput();
  const rq = st.reqSpeed === 0 ? "max" : st.reqSpeed + "x";
  el.hspeed.innerHTML = `asked <b>${E(rq)}</b> · accepted <b>${E(acc)}</b> · measured <b>${E(meas)}</b>`;
  el.measline.textContent = meas === "—"
    ? "" : ` · measured ${meas} (simulated seconds per wall second, last ~1 s)`;
}

/* Anti-windup, in the header rather than only in the raw key dump: the plant
   can be saturating while the Observe tab still looks healthy. Both values are
   read straight off the frame; the words come from brainsim/engine.py. */
function renderWarnChip(f) {
  const halted = Object.keys(f.growth_halted || {}).filter(k => f.growth_halted[k]);
  const bits = [];
  if (halted.length) bits.push("growth halted: " + halted.join(", "));
  if (f.store_clamped) bits.push("connection store full");
  const t = el.warnchip.querySelector(".t");
  const text = bits.join(" · ");
  if (!bits.length) { el.warnchip.hidden = true; if (t.textContent !== "") t.textContent = ""; return; }
  el.warnchip.hidden = false;
  if (t.textContent !== text) t.textContent = text;
  el.warnchip.title = halted.length
    ? "growth halted: the simulator stopped creating connections for these groups because their mean rate error "
    + "stopped improving; it resumes when the error changes sign. store clamped: the connection store is nearly "
    + "full, so no new connections are created anywhere."
    : "connection store full: the store of connections is nearly at its cap, so the simulator is creating no new ones.";
}

/* Measured throughput comes from the newest frame only, and only while frames are
   arriving. The header and the control bar read this one value, so neither can go stale
   while the other keeps updating. Requested and accepted speed are separate facts. */
function measuredThroughput() {
  const f = st.lastFrame;
  if (st.conn !== "live" || !f || f.wall_ratio == null) return "—";
  return Number(f.wall_ratio).toFixed(2) + "x";
}

function renderFrameLabel(f) {
  const syn = ` · +${f.born_count} / −${f.died_count} synapses this frame`;
  if (f.ticks === 0) { el.framelabel.textContent = "heartbeat · 0 ticks" + syn; return; }
  el.framelabel.textContent =
    `frame #${f.seq} · ${tickWord(f.ticks)} · ${msOf(f.ticks)} ms` + syn +
    (f.truncated ? " · spike list capped, counts exact" : "");
}

/* ---- region heads + patterns ---- */
function renderRegionHeads() {
  const host = $("#regionheads"); host.innerHTML = "";
  for (const n of st.regionNames) {
    const r = L.regions[n];
    /* Role clauses are static: no reply this page receives carries the
       projections between regions (telemetry.REPLY_KEYS), so the text names
       only what the page itself can show. */
    const sub = n === "sense"
      ? "receives the stimuli · text-nerve prosthesis, no biological analog"
      : `recurrent pool, ${Number(r.n_exc).toLocaleString()} E + ${Number(r.n - r.n_exc).toLocaleString()} I` +
      ` · named after ${n === "ctx" ? "cortex" : n === "hpc" ? "the hippocampus" : n}, not a model of it`;
    const b = document.createElement("button");
    b.type = "button";
    b.innerHTML = `<span class="rt">${E(n)} (${E(Number(r.n).toLocaleString())})</span><span class="rs">${E(sub)}</span>`;
    b.onclick = () => selectRegion(n);
    host.appendChild(b);
  }
}

function renderPatterns() {
  if (!C || !L || !L.patterns) return;
  const host = el.patgrid;
  if (host.childElementCount === L.patterns.length) return;
  host.innerHTML = "";
  L.patterns.forEach((cells, i) => {
    const name = letterOf(i);
    const b = document.createElement("button");
    b.className = "patbtn"; b.type = "button"; b.dataset.pattern = i;
    b.innerHTML = `${E(name)}<span class="sub">present <kbd>${E("asdf"[i] || "")}</kbd></span>` +
      `<span class="tip">Pattern ${E(name)} drives a fixed patch of ${E(cells.length)} sense cells, ` +
      `${E(C.pattern_amp_mv)} mV for ${E(msOf(C.pattern_ticks))} ms. A stimulus location, not a learned concept.</span>`;
    b.onclick = () => presentPattern(i);
    b.onmouseenter = () => st.hoverPattern = i;
    b.onmouseleave = () => { if (st.hoverPattern === i) st.hoverPattern = null; };
    b.onfocus = () => st.hoverPattern = i;
    b.onblur = () => { if (st.hoverPattern === i) st.hoverPattern = null; };
    host.appendChild(b);
  });
}

/* ---- encode-mode panel (SPEC 8.12) ----------------------------------------
   The mode, the stage, W and which of W spiked are all read off the frame's
   `encode` key; nothing here infers any of them. The three buttons send only
   commands the page could already send. */
function renderEncodeButtons() {
  if (!C || !L) return;
  const a = L.patterns && L.patterns[0], half = L.half_patterns && L.half_patterns[0];
  $("#encPresentA").textContent = a ? `Present A · ${a.length} cells` : "Present A";
  $("#encHalfA").textContent = half ? `Present half-A · ${half.length} cells` : "Present half-A";
  $("#encNone").textContent = `No stimulus · advance ${tickWord(C.pattern_ticks)}`;
}

function renderEncode(f) {
  const enc = f.encode;
  if (!enc) return;
  const box = $("#encodeToggle");
  if (box.checked !== enc.mode) box.checked = enc.mode;   /* engine truth, not the click */
  const stage = enc.stage === "present"
    ? `presenting · window on W until t = ${enc.t_present_end}`
    : enc.stage === "grace" ? `grace · mask off at t = ${enc.t_grace_end}` : enc.stage;
  if (el.encodestage.textContent !== stage) el.encodestage.textContent = stage;
  const cap = enc.W.length
    ? `W · ${enc.W.length} hpc E cells from the identification pass; lit = spiked in the last ${enc.window_ticks} ticks`
    : "no W yet: turn encode-mode on and present A";
  if (el.wcaption.textContent !== cap) el.wcaption.textContent = cap;
  const sig = enc.W.join(",") + "|" + enc.spiked_last_50.join(",");
  if (st.wcardSig === sig) return;
  st.wcardSig = sig;
  const lit = {};
  for (const id of enc.spiked_last_50) lit[id] = true;
  el.wcard.innerHTML = enc.W
    .map(id => `<span class="wchip${lit[id] ? " lit" : ""}">${E(id)}</span>`).join("");
}

/* ---- heterosynaptic-write panel (SPEC 8.16): only the frame's `hetero` key. */
function renderHetero(f) {
  const h = f.hetero;
  if (!h) return;
  const box = $("#heteroToggle");
  if (box.checked !== h.on) box.checked = h.on;   /* engine truth, not the click */
  const d = v => v == null ? "—" : v;
  const d3 = v => v == null ? "—" : v.toFixed(3);
  const stats = `${h.on ? "on" : "off"} · ${d(h.sweeps)} sweeps · last: ${d(h.cells_last)} cells, ${d(h.syn_last)} synapses (${d(h.up_last)} up, ${d(h.down_last)} down) · ${d(h.cells_total)} cells in total · mean |dw| ${d3(h.mean_abs_dw_last)} · net dw ${d3(h.net_dw_last)} (of w_max) · at t ${d(h.t_last)}`;
  if (el.heterostats.textContent !== stats) el.heterostats.textContent = stats;
  const ids = h.cell_ids_last && h.cell_ids_last.length ? h.cell_ids_last.join(", ") : "—";
  const n = h.cell_ids_last ? h.cell_ids_last.length : 0;
  const line = h.cell_ids_truncated
    ? `cells at the last write · first ${n} ids of ${h.cells_last} cells · ${ids}`
    : `cells at the last write · ${ids}`;
  if (el.heteroCells.textContent !== line) el.heteroCells.textContent = line;
}

$("#heteroToggle").onchange = e => {
  sendTracked("hetero", { on: e.target.checked },
    "heterosynaptic write " + (e.target.checked ? "on" : "off"));
};

$("#encodeToggle").onchange = e => {
  sendTracked("encode", { on: e.target.checked },
    "encode-mode " + (e.target.checked ? "on" : "off"));
};
$("#encPresentA").onclick = () => presentPattern(0);
$("#encHalfA").onclick = () => {
  if (!C || !L || !L.half_patterns || !L.half_patterns[0]) return;
  const ids = L.half_patterns[0].slice();
  sendTracked("inject", { ids: ids, amp: C.pattern_amp_mv, ticks: C.pattern_ticks },
    `present half-A · ${ids.length} cells · ${msOf(C.pattern_ticks)} ms`, { cells: ids });
};
$("#encNone").onclick = () => {
  if (!C) return;
  sendTracked("step", { ticks: C.pattern_ticks }, `no stimulus · advance ${tickWord(C.pattern_ticks)}`);
};

function presentPattern(i) {
  if (!C || !L || !L.patterns || !L.patterns[i]) return;
  sendTracked("present", { pattern: i, ticks: C.pattern_ticks },
    `present ${letterOf(i)} · ${L.patterns[i].length} cells · ${msOf(C.pattern_ticks)} ms`,
    { cells: L.patterns[i], letter: letterOf(i), patternIndex: i });
}

/* ---- command feedback: one compact row per command ------------------------
   State comes only from results, stim_events and stimlog (see the
   reconciliation rules above). Nothing here infers state from absence.      */
function rowChip(c) {
  if (c.letter) return { label: c.letter, cls: "pchip" };
  if (c.cmd === "inject") return { label: "inj", cls: "pchip" };
  return { label: c.cmd, cls: "pchip cmd" };
}
function rowHTML(c, forceOpen) {
  const ch = rowChip(c);
  const open = forceOpen || !!expanded[c.req];
  return `<div class="cmdrow" data-req="${E(c.req)}">` +
    `<div class="line"><span class="${E(ch.cls)}">${E(ch.label)}</span>` +
    `<span class="otext ${E(c.cls)}">${E(c.text)}</span>` +
    (forceOpen ? "" : `<button class="detbtn" type="button" data-req="${E(c.req)}" aria-expanded="${open}">details</button>`) +
    `</div><div class="det"${open ? "" : " hidden"}>` +
    c.details.map(([k, v]) => `<div><span>${E(k)}</span><span>${E(v)}</span></div>`).join("") +
    `</div></div>`;
}
const expanded = Object.create(null);
function renderRows() {
  const list = VS.cards.slice(0, DISPLAY.CARD_HISTORY_MAX);
  const sig = list.map(c => c.req + "|" + c.text + "|" + (expanded[c.req] ? 1 : 0)).join("~");
  if (sig === st.rowSig) return;
  st.rowSig = sig;
  el.cmdlist.innerHTML = list.length
    ? list.map(c => rowHTML(c, false)).join("")
    : '<div class="empty" style="padding:10px">No commands sent yet.</div>';
}
el.cmdlist.addEventListener("click", e => {
  const b = e.target.closest(".detbtn"); if (!b) return;
  const req = b.dataset.req;
  expanded[req] = !expanded[req]; st.rowSig = ""; renderRows();
  const nb = el.cmdlist.querySelector(`.detbtn[data-req="${CSS.escape(req)}"]`);
  if (nb) nb.focus();
});
function renderCmdFull() {
  const list = VS.cards.slice(0, DISPLAY.DETAILS_HISTORY_MAX);
  const sig = list.map(c => c.req + "|" + c.text).join("~");
  if (sig === st.fullSig) return;
  st.fullSig = sig;
  $("#cmdfullcap").textContent =
    `every command this client sent, newest first · last ${DISPLAY.DETAILS_HISTORY_MAX} · details always expanded`;
  $("#cmdfull").innerHTML = list.length ? list.map(c => rowHTML(c, true)).join("")
    : '<div class="empty" style="padding:10px">No commands sent yet.</div>';
}
setInterval(() => { refresh(); renderRows(); if (st.tab === "diag") renderCmdFull(); }, 250);

/* ---- run controls ---- */
function renderControls() {
  const running = VS.sim === "running";
  el.runbtn.innerHTML = (VS.sim === "unknown" ? "Run" : (running ? "Pause" : "Run")) + "<kbd>space</kbd>";
  el.runbtn.setAttribute("aria-pressed", String(running));
  const conf = VS.lastStatus
    ? `engine last confirmed: ${running ? "running" : "paused"} at t = ${fmtT(VS.lastStatus.t)}`
    : "no status yet · simulator state unknown";
  el.runline.innerHTML = (st.reqRun != null && st.reqRun !== running)
    ? `<span class="pend">requested ${st.reqRun ? "run" : "pause"} → pending</span> · ${E(conf)}`
    : E(conf);
  const accepted = VS.lastStatus ? (VS.lastStatus.speed === 0 ? "max" : VS.lastStatus.speed + "x") : "—";
  const req = st.reqSpeed === 0 ? "max" : st.reqSpeed + "x";
  el.speedline.innerHTML = (VS.lastStatus && VS.lastStatus.speed !== st.reqSpeed)
    ? `<span class="pend">requested ${E(req)} → pending</span> · accepted ${E(accepted)}`
    : `requested ${E(req)} · accepted ${E(accepted)}`;
}

el.runbtn.onclick = () => {
  const running = VS.sim === "running";
  st.reqRun = !running;
  sendTracked(running ? "pause" : "run", {}, running ? "pause" : "run");
  renderControls();
};
$("#stepbtn").onclick = () => { sendTracked("step", { ticks: 1 }, "step 1 tick"); };
$("#speed").oninput = e => {
  if ($("#maxspeed").checked) return;
  st.reqSpeed = parseFloat(e.target.value);
  sendTracked("speed", { factor: st.reqSpeed }, "speed " + st.reqSpeed + "x");
  renderControls();
};
$("#maxspeed").onchange = e => {
  st.reqSpeed = e.target.checked ? 0 : parseFloat($("#speed").value);
  sendTracked("speed", { factor: st.reqSpeed }, "speed " + (st.reqSpeed === 0 ? "max" : st.reqSpeed + "x"));
  renderControls();
};
$("#sleepbtn").onclick = () => { sleepWatch = sendTracked("sleep", { on: true }, "sleep now"); };
/* the worker's sleep command takes on:false to leave the sleep phase
   (brainsim/worker.py:156-160); server/app.py forwards commands unchanged */
$("#wakebtn").onclick = () => { sleepWatch = sendTracked("sleep", { on: false }, "wake now"); };
let sleepWatch = null;
/* re-rendered from the card each frame, so the line follows the card's state
   instead of freezing whatever was true when the reply happened to land */
function renderSleepLine() {
  const c = sleepWatch;
  if (!c) return;
  let text = null;
  if (c.status === "accepted")
    text = `${c.phase_before} → ${c.phase_after} · changed: ${c.changed} · phase clock restarted · confirmed at t = ${fmtT(c.t)}`;
  else if (c.status === "not_sent") text = "not sent · disconnected";
  else if (c.status === "rejected") text = `rejected: ${String(c.reason || "")}`;
  if (text != null) {
    if (el.sleepline.textContent !== text) el.sleepline.textContent = text;
    return;
  }
  const pend = '<span class="pend">requested sleep → pending</span>';
  if (el.sleepline.innerHTML !== pend) el.sleepline.innerHTML = pend;
}
$("#injbtn").onclick = () => {
  if (!st.selection.length) return;
  const amp = parseFloat($("#injamp").value) || 0, ticks = parseInt($("#injticks").value, 10) || 0;
  sendTracked("inject", { ids: st.selection.slice(), amp, ticks },
    `inject ${st.selection.length} cells · ${amp} mV · ${msOf(ticks)} ms`,
    { cells: st.selection.slice() });
};
$("#injctx").onclick = () => {
  const ids = ctxSampleIds();
  if (!ids.length) return;
  const amp = parseFloat($("#injamp").value) || 0, ticks = parseInt($("#injticks").value, 10) || 0;
  sendTracked("inject", { ids, amp, ticks },
    `inject ${ids.length} ctx cells (page-chosen sample) · ${amp} mV · ${msOf(ticks)} ms`, { cells: ids });
};
$("#structToggle").onchange = e => {
  st.structOn = e.target.checked;
  if (!st.structOn) { st.bornFlash = []; st.deathFlash = []; }
};
$("#synToggle").onchange = e => {
  st.synOn = e.target.checked;
  el.synlabel.textContent = st.synOn && L && st.lastFrame
    ? `a fixed random sample of ${L.synapse_sample.length.toLocaleString()} of ${st.lastFrame.n_syn_alive.toLocaleString()} alive connections`
    : "off";
};

/* ---- map drawing ---- */
function resize() {
  for (const c of [map, tlc]) {
    const r = c.getBoundingClientRect();
    c.width = Math.max(1, Math.round(r.width * dpr()));
    c.height = Math.max(1, Math.round(r.height * dpr()));
  }
  for (const c of document.querySelectorAll("canvas.mini, canvas.raster")) {
    const r = c.getBoundingClientRect();
    c.width = Math.max(1, Math.round(r.width * dpr()));
    c.height = Math.max(1, Math.round(r.height * dpr()));
  }
  if (L) layoutBoxes();
}
window.addEventListener("resize", resize);

function drawMap() {
  const w = map.width / dpr(), h = map.height / dpr();
  mctx.setTransform(dpr(), 0, 0, dpr(), 0, 0);
  mctx.fillStyle = "#070a0e"; mctx.fillRect(0, 0, w, h);
  if (!L || !st.px) return;
  if (st.synOn && st.syn) { mctx.setTransform(1, 0, 0, 1, 0, 0); mctx.drawImage(st.syn, 0, 0); mctx.setTransform(dpr(), 0, 0, dpr(), 0, 0); }

  for (const n of st.regionNames) {
    const b = st.boxes[n];
    if (!b) continue;
    mctx.strokeStyle = "#1b222d"; mctx.lineWidth = 1;
    mctx.strokeRect(b.x + .5, b.y + .5, b.w, b.h);
  }
  const nowW = performance.now();
  let segs = 0;   // exposed for verification: long lines drawn this frame
  if (st.structOn) {
    st.bornFlash = st.bornFlash.filter(q => nowW - q.at < DISPLAY.STRUCT_FLASH_MS);
    st.deathFlash = st.deathFlash.filter(q => nowW - q.at < DISPLAY.STRUCT_FLASH_MS);
    mctx.lineWidth = 1.4;
    for (const [list, rgb] of [[st.bornFlash, "95,211,154"], [st.deathFlash, "255,112,112"]]) {
      for (const q of list) {
        mctx.strokeStyle = `rgba(${rgb},${(1 - (nowW - q.at) / DISPLAY.STRUCT_FLASH_MS) * 0.9})`;
        mctx.beginPath(); mctx.moveTo(st.px[q.pre], st.py[q.pre]); mctx.lineTo(st.px[q.post], st.py[q.post]); mctx.stroke();
        segs++;
      }
    }
  }
  if (st.synOn && st.syn) segs += L.synapse_sample.length;

  // the patch a pattern drives, on hover/focus and for its confirmed interval
  const marks = [];
  if (st.hoverPattern != null) marks.push({ p: st.hoverPattern, strong: true });
  for (const c of VS.cards) {
    if (c.patternIndex == null) continue;
    if (c.status === "running" || (c.status === "accepted" && c.stim_id != null))
      marks.push({ p: c.patternIndex, strong: false });
  }
  const donePatch = new Set();
  for (const mk of marks) {
    if (!L.patterns || !L.patterns[mk.p]) continue;
    if (donePatch.has(mk.p) && !mk.strong) continue;
    donePatch.add(mk.p);
    const cells = L.patterns[mk.p];
    let mx = 0, my = 0; for (const id of cells) { mx += st.px[id]; my += st.py[id]; }
    mx /= cells.length; my /= cells.length;
    let rad = 0; for (const id of cells) rad = Math.max(rad, Math.hypot(st.px[id] - mx, st.py[id] - my));
    mctx.fillStyle = mk.strong ? "rgba(255,180,84,0.15)" : "rgba(255,180,84,0.09)";
    mctx.beginPath(); mctx.arc(mx, my, rad + 7, 0, 6.283); mctx.fill();
    mctx.strokeStyle = mk.strong ? "rgba(255,180,84,0.95)" : "rgba(255,180,84,0.6)";
    mctx.lineWidth = 1; mctx.beginPath(); mctx.arc(mx, my, rad + 7, 0, 6.283); mctx.stroke();
    mctx.lineWidth = 1.2;
    for (const id of cells) { mctx.beginPath(); mctx.arc(st.px[id], st.py[id], 3.2, 0, 6.283); mctx.stroke(); }
    mctx.fillStyle = "rgba(255,196,120,0.95)";
    mctx.font = "600 13px system-ui, sans-serif"; mctx.textAlign = "center"; mctx.textBaseline = "middle";
    mctx.fillText(letterOf(mk.p), mx, my);
    mctx.textAlign = "start"; mctx.textBaseline = "alphabetic";
  }

  // ripple (one authored motion moment)
  st.ripples = st.ripples.filter(r => nowW - r.at < 400);
  for (const r of st.ripples) {
    if (!r.cells || !r.cells.length) continue;
    let mx = 0, my = 0; for (const id of r.cells) { mx += st.px[id]; my += st.py[id]; }
    mx /= r.cells.length; my /= r.cells.length;
    const k = (nowW - r.at) / 400, e = 1 - Math.pow(1 - k, 3);
    mctx.strokeStyle = `rgba(255,180,84,${(1 - k) * 0.85})`;
    mctx.lineWidth = 2.5 * (1 - k) + 0.5;
    mctx.beginPath(); mctx.arc(mx, my, 8 + e * 70, 0, 6.283); mctx.stroke();
  }

  // selection subset connections
  if (st.selected != null && st.topIn.length) {
    mctx.lineWidth = 1;
    for (const [pre, wv] of st.topIn) {
      if (pre >= st.N) continue;
      segs++;
      mctx.strokeStyle = wv >= 0 ? "rgba(106,168,224,.55)" : "rgba(224,138,106,.55)";
      mctx.beginPath(); mctx.moveTo(st.px[pre], st.py[pre]); mctx.lineTo(st.px[st.selected], st.py[st.selected]); mctx.stroke();
    }
  }

  const decay = reduced ? 0 : Math.pow(0.02, 16 / DISPLAY.GLOW_MS);
  for (let i = 0; i < st.N; i++) {
    const b = st.bright[i], exc = L.is_exc[i];
    const base = exc ? [106, 168, 224] : [224, 138, 106];
    const r = Math.round(base[0] + (255 - base[0]) * b), g = Math.round(base[1] + (255 - base[1]) * b), bl = Math.round(base[2] + (255 - base[2]) * b);
    mctx.fillStyle = `rgb(${r},${g},${bl})`;
    mctx.beginPath(); mctx.arc(st.px[i], st.py[i], exc ? 1.25 : 1.9, 0, 6.283); mctx.fill();
    if (b > 0.004) st.bright[i] = b * decay; else st.bright[i] = 0;
  }
  if (st.cursor != null && st.cursor !== st.selected) {
    mctx.strokeStyle = "rgba(234,244,255,.75)"; mctx.lineWidth = 1.2; mctx.setLineDash([2, 2]);
    mctx.beginPath(); mctx.arc(st.px[st.cursor], st.py[st.cursor], 5, 0, 6.283); mctx.stroke();
    mctx.setLineDash([]);
  }
  if (st.selected != null) {
    mctx.strokeStyle = "#eaf4ff"; mctx.lineWidth = 1.6;
    mctx.beginPath(); mctx.arc(st.px[st.selected], st.py[st.selected], 5.5, 0, 6.283); mctx.stroke();
  }
  if (st.drag) {
    mctx.strokeStyle = "rgba(234,244,255,.8)"; mctx.setLineDash([3, 3]); mctx.lineWidth = 1;
    mctx.strokeRect(st.drag.x, st.drag.y, st.drag.w, st.drag.h); mctx.setLineDash([]);
  }
  st.lineSegments = segs;
}

/* ---- timeline ---- */
function drawTimeline() {
  const w = tlc.width / dpr(), h = tlc.height / dpr();
  tctx.setTransform(dpr(), 0, 0, dpr(), 0, 0);
  tctx.fillStyle = "#070a0e"; tctx.fillRect(0, 0, w, h);
  const TL = VS.timeline;
  if (!C || !TL.frames.length) return;
  const winTicks = WINDOW_S * 1000 / C.dt_ms;
  const tmax = TL.frames[TL.frames.length - 1].t;
  const tmin = tmax - winTicks;
  const GUT = 68;   // room for the "max … Hz" scale label
  const X = t => GUT + (t - tmin) / winTicks * (w - GUT - 8);
  const stimH = 16, rowH = Math.max(16, (h - stimH - 16) / 3);

  // phase tint
  for (const fr of TL.frames) {
    if (fr.t < tmin) continue;
    tctx.fillStyle = fr.phase === "sleep" ? "rgba(150,120,220,.13)" : "rgba(106,168,224,.07)";
    tctx.fillRect(X(fr.t - fr.ticks), stimH + 4, Math.max(1, X(fr.t) - X(fr.t - fr.ticks)), rowH * 3);
  }
  // gaps
  for (const g of TL.gaps) {
    if (g.t1 < tmin) continue;
    const x0 = X(Math.max(g.t0, tmin)), x1 = X(g.t1);
    tctx.save();
    tctx.beginPath(); tctx.rect(x0, 0, Math.max(2, x1 - x0), h); tctx.clip();
    tctx.strokeStyle = "#3a4457"; tctx.lineWidth = 1;
    for (let x = x0 - h; x < x1 + h; x += 4) { tctx.beginPath(); tctx.moveTo(x, h); tctx.lineTo(x + h, 0); tctx.stroke(); }
    tctx.restore();
  }
  // stimulus bars
  for (const c of TL.stims) {
    if (c.t_accept == null || c.t_end_planned == null) continue;
    const y = 3, bh = stimH - 8;
    tctx.font = "9px ui-monospace, monospace";
    const barLetter = c.letter || (c.cmd === "inject" ? "i" : "");
    if (c.t_start == null) {
      // no confirmed start: outline only, never a filled span
      const x0 = X(c.t_accept), x1 = X(c.t_end_planned);
      tctx.strokeStyle = "#ffb454"; tctx.lineWidth = 1;
      tctx.strokeRect(x0 + .5, y + .5, Math.max(2, x1 - x0), bh);
      if (c.status === "unknown" || c.status === "expired") {
        tctx.fillStyle = "#ffb454";
        tctx.fillText("?", x0 + 2, y + bh - 1); tctx.fillText("?", Math.max(x0 + 9, x1 - 7), y + bh - 1);
      }
      if (barLetter) {
        tctx.fillStyle = "#ffd79a"; tctx.font = "600 9px system-ui, sans-serif";
        tctx.fillText(barLetter, x0 + 2, y - 1); tctx.font = "9px ui-monospace, monospace";
      }
    } else {
      // solid only as far as the stimulus was actually observed
      const openEnd = c.status === "unknown" || c.status === "expired";
      const lastObs = openEnd
        ? (c.lastSeenT != null ? c.lastSeenT : c.t_start)
        : (c.t_end != null ? c.t_end : Math.min(tmax, c.t_end_planned));
      const x0 = X(c.t_start), x1 = X(lastObs);
      tctx.fillStyle = "#ffb454"; tctx.fillRect(x0, y, Math.max(2, x1 - x0), bh);
      if (barLetter) {
        tctx.fillStyle = "#ffd79a"; tctx.font = "600 9px system-ui, sans-serif";
        tctx.fillText(barLetter, x0 + 1, y - 1); tctx.font = "9px ui-monospace, monospace";
      }
      if (openEnd) {
        tctx.fillStyle = "#0a0c10"; tctx.fillRect(x1 - 2, y, 2, bh);   // open right edge
        tctx.fillStyle = "#ffb454"; tctx.fillText("?", x1 + 3, y + bh - 1);
      }
    }
  }
  // region rate rows
  st.regionNames.forEach((n, i) => {
    const y0 = stimH + 4 + i * rowH, hh = rowH - 4;
    const vals = TL.frames.filter(fr => fr.t >= tmin).map(fr => fr.rates[n] || 0).sort((a, b) => a - b);
    // 95th percentile, so a single burst frame does not flatten the whole row
    const mx = Math.max(0.5, vals[Math.floor(vals.length * 0.95)] || 0.5);
    tctx.fillStyle = "#9aa8bb"; tctx.font = "10px system-ui, sans-serif";
    tctx.fillText(n, 4, y0 + 9);
    tctx.fillStyle = "#7a889b"; tctx.font = "9px ui-monospace, monospace";
    /* the gutter number is this row's scale top, not a reading: say so */
    tctx.fillText("max " + mx.toFixed(1) + " Hz", 4, y0 + hh - 1);
    for (const fr of TL.frames) {
      if (fr.t < tmin) continue;
      const x0 = X(fr.t - fr.ticks), bw = Math.max(1, X(fr.t) - x0);
      const v = Math.min(1, (fr.rates[n] || 0) / mx);
      tctx.fillStyle = i === 0 ? "rgba(255,180,84,.75)" : (i === 1 ? "rgba(106,168,224,.8)" : "rgba(180,160,230,.8)");
      tctx.fillRect(x0, y0 + hh * (1 - v), bw, Math.max(1, hh * v));
      if (fr.truncated && i === 0) {
        tctx.fillStyle = "#ffd79a"; tctx.fillRect(x0, stimH + 1, Math.max(2, bw), 2);
      }
    }
    tctx.strokeStyle = "#1b222d"; tctx.beginPath(); tctx.moveTo(GUT, y0 + hh + .5); tctx.lineTo(w - 8, y0 + hh + .5); tctx.stroke();
  });
  // x axis in simulated seconds
  tctx.fillStyle = "#7a889b"; tctx.font = "10px ui-monospace, monospace";
  tctx.fillText((tmin * C.dt_ms / 1000).toFixed(0) + " s", GUT, h - 2);
  const lbl = (tmax * C.dt_ms / 1000).toFixed(1) + " s";
  tctx.fillText(lbl, w - 8 - tctx.measureText(lbl).width, h - 2);
  const trunc = TL.frames.filter(fr => fr.t >= tmin && fr.truncated).length;
  const inWin = TL.gaps.filter(g => g.t1 >= tmin).length;
  el.tlnote.textContent = (inWin ? inWin + " observation gap(s) in this window · " : "") +
    (trunc ? trunc + " frame(s): spike list capped, counts exact" : "");
}

function raf() {
  drawMap(); drawTimeline(); renderSleepLine();
  requestAnimationFrame(raf);
}

/* ---- map interaction ---- */
function localPt(e) {
  const r = map.getBoundingClientRect();
  return { x: e.clientX - r.left, y: e.clientY - r.top };
}
map.addEventListener("keydown", e => {
  if (!st.N) return;
  const step = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: 40, ArrowUp: -40 }[e.key];
  if (step != null) {
    e.preventDefault(); e.stopPropagation();
    st.cursor = (((st.cursor == null ? 0 : st.cursor) + step) % st.N + st.N) % st.N;
  } else if (e.key === "Enter" && st.cursor != null) {
    e.preventDefault(); e.stopPropagation(); selectNeuron(st.cursor);
  }
});
let down = null;
map.addEventListener("pointerdown", e => { down = localPt(e); map.setPointerCapture(e.pointerId); });
map.addEventListener("pointermove", e => {
  if (!down) return;
  const p = localPt(e), dx = p.x - down.x, dy = p.y - down.y;
  if (Math.abs(dx) < 4 && Math.abs(dy) < 4) return;
  st.drag = { x: Math.min(p.x, down.x), y: Math.min(p.y, down.y), w: Math.abs(dx), h: Math.abs(dy) };
  st.selection = [];
  for (let i = 0; i < st.N; i++)
    if (st.px[i] >= st.drag.x && st.px[i] <= st.drag.x + st.drag.w && st.py[i] >= st.drag.y && st.py[i] <= st.drag.y + st.drag.h)
      st.selection.push(i);
  $("#injbtn").textContent = `Inject ${st.selection.length} cells`;
  $("#injbtn").disabled = !st.selection.length;
});
map.addEventListener("pointerup", e => {
  if (!down) return;
  const p = localPt(e);
  if (Math.hypot(p.x - down.x, p.y - down.y) < 4) {
    let best = -1, bd = 49;
    for (let i = 0; i < st.N; i++) {
      const d = (st.px[i] - p.x) ** 2 + (st.py[i] - p.y) ** 2;
      if (d < bd) { bd = d; best = i; }
    }
    if (best >= 0) selectNeuron(best);
  }
  st.drag = null; down = null;
});

function selectNeuron(id) {
  st.selected = id; st.selectedRegion = null;
  raw({ cmd: "watch", id }); raw({ cmd: "inspect", id });
  openDrawer("Neuron " + Number(id));
  el.sublabel.hidden = false;
  el.sublabel.textContent = "subset: 10 strongest excitatory + 10 strongest inhibitory inputs";
}
function selectRegion(name) {
  st.selectedRegion = name; st.selected = null; st.topIn = [];
  el.sublabel.hidden = true;
  raw({ cmd: "region", name });
  openDrawer("Region " + String(name));
}
setInterval(() => {
  if (st.selected != null) raw({ cmd: "inspect", id: st.selected });
  if (st.selectedRegion) raw({ cmd: "region", name: st.selectedRegion });
}, 600);

function openDrawer(title) {
  el.drawertitle.textContent = String(title);
  el.drawer.hidden = false;
  requestAnimationFrame(() => el.drawer.classList.add("open"));
  $("#drawerclose").focus();
}
function closeDrawer() {
  el.drawer.classList.remove("open");
  st.selected = null; st.selectedRegion = null; st.topIn = [];
  setTimeout(() => { el.drawer.hidden = true; }, 220);
}
$("#drawerclose").onclick = closeDrawer;

function field(k, v) { return `<div class="field"><span class="k">${E(k)}</span><span class="v">${E(v)}</span></div>`; }

function renderNeuron(msg) {
  if (st.selected !== msg.id || !C) return;
  st.topIn = msg.top_in;
  const wmax = Math.max(0.001, ...msg.top_in.map(t => Math.abs(t[1])));
  const bars = rows => rows.map(([pre, wv]) =>
    `<div class="bar${wv < 0 ? " inh" : ""}" style="width:${Math.max(6, Math.abs(Number(wv)) / wmax * 100)}%"><span>${E(pre)} · ${E(Number(wv).toFixed(2))}</span></div>`).join("");
  el.drawerbody.innerHTML =
    field("id", msg.id) + field("region", msg.region) + field("type", msg.is_exc ? "excitatory" : "inhibitory") +
    field("v", Number(msg.v).toFixed(2) + " mV") +
    `<p class="measure">Membrane potential right now, in millivolts.</p>` +
    field("theta", Number(msg.theta).toFixed(2) + " mV") +
    `<p class="measure">The adaptive firing threshold right now, in millivolts.</p>` +
    field("rate", Number(msg.rate_hz).toFixed(2) + " Hz") +
    `<p class="measure">Spike rate in hertz. EMA over sweeps, updated every ${E(C.sweep_ticks)} ticks; recent sweeps weighted more.</p>` +
    field("in degree", msg.in_deg) + field("out degree", msg.out_deg) +
    `<p class="measure">Alive incoming and outgoing synapses, counted now.</p>` +
    `<h3 style="margin-top:12px">Membrane trace</h3>` +
    `<p class="measure">Last ${E(C.v_trace_ticks)} ticks of membrane potential (${E(msOf(C.v_trace_ticks))} ms), only while this cell is watched.</p>` +
    `<canvas class="mini" id="vtrace"></canvas>` +
    `<h3 style="margin-top:12px">Strongest inputs</h3>` +
    `<p class="measure">Subset: the 10 strongest excitatory and 10 strongest inhibitory inputs, by weight. Not all ${E(msg.in_deg)} inputs.</p>` +
    `<div class="bars">${bars(msg.top_in.filter(t => t[1] >= 0))}${bars(msg.top_in.filter(t => t[1] < 0))}</div>`;
  const c = $("#vtrace");
  if (c) {
    const r = c.getBoundingClientRect();
    c.width = Math.round(r.width * dpr()); c.height = Math.round(r.height * dpr());
    const g = c.getContext("2d"); g.setTransform(dpr(), 0, 0, dpr(), 0, 0);
    const cw = c.width / dpr(), ch = c.height / dpr();
    g.fillStyle = "#070a0e"; g.fillRect(0, 0, cw, ch);
    const tr = msg.v_trace;
    if (tr.length > 1) {
      const mn = Math.min(...tr), mx = Math.max(...tr, mn + 1e-6);
      g.strokeStyle = "#6aa8e0"; g.lineWidth = 1; g.beginPath();
      tr.forEach((v, i) => {
        const x = i / (tr.length - 1) * cw, y = ch - (v - mn) / (mx - mn) * ch;
        i ? g.lineTo(x, y) : g.moveTo(x, y);
      });
      g.stroke();
    } else {
      g.fillStyle = "#7a889b"; g.font = "11px system-ui, sans-serif";
      g.fillText("no trace yet — watching started this moment", 8, ch / 2);
    }
  }
  if (st.tab === "diag") $("#inspjson").textContent = JSON.stringify(Object.assign({}, msg, { v_trace: `[${msg.v_trace.length} floats]` }), null, 1);
}

function renderRegion(msg) {
  if (st.selectedRegion !== msg.name || !C) return;
  const nb = msg.w_hist.edges.length - 1;
  el.drawerbody.innerHTML =
    field("cells", Number(msg.n).toLocaleString()) +
    field("rate", Number(msg.rate_hz).toFixed(2) + " Hz") +
    `<p class="measure">Mean spike rate in hertz. EMA over sweeps, updated every ${E(C.sweep_ticks)} ticks; recent sweeps weighted more.</p>` +
    field("synapses in", Number(msg.n_syn_in).toLocaleString()) + field("synapses out", Number(msg.n_syn_out).toLocaleString()) +
    `<p class="measure">Alive synapses ending in and starting from this region, counted now.</p>` +
    `<h3 style="margin-top:12px">Weight histogram</h3>` +
    `<p class="measure">|w| of alive incoming synapses, ${E(nb)} bins.</p><canvas class="mini" id="whist"></canvas>` +
    `<h3 style="margin-top:12px">Rate histogram</h3>` +
    `<p class="measure">Per-cell rate in hertz across this region, ${E(msg.rate_hist.edges.length - 1)} bins.</p><canvas class="mini" id="rhist"></canvas>` +
    `<h3 style="margin-top:12px">Alive synapses</h3>` +
    `<p class="measure">Network-wide alive synapse count over observed time, one point per frame.</p><canvas class="mini" id="spark"></canvas>`;
  hist("whist", msg.w_hist.counts, "#6aa8e0");
  hist("rhist", msg.rate_hist.counts, "#b4a0e6");
  spark("spark", st.synHist);
  if (st.tab === "diag") $("#regjson").textContent = JSON.stringify(msg, null, 1);
}
function sizeMini(id) {
  const c = $("#" + id); if (!c) return null;
  const r = c.getBoundingClientRect();
  c.width = Math.round(r.width * dpr()); c.height = Math.round(r.height * dpr());
  const g = c.getContext("2d"); g.setTransform(dpr(), 0, 0, dpr(), 0, 0);
  g.fillStyle = "#070a0e"; g.fillRect(0, 0, c.width / dpr(), c.height / dpr());
  return { c, g, w: c.width / dpr(), h: c.height / dpr() };
}
function hist(id, counts, color) {
  const o = sizeMini(id); if (!o) return;
  const mx = Math.max(1, ...counts), bw = o.w / counts.length;
  o.g.fillStyle = color;
  counts.forEach((v, i) => { const hh = v / mx * (o.h - 4); o.g.fillRect(i * bw, o.h - hh, Math.max(1, bw - 1), hh); });
}
function spark(id, arr) {
  const o = sizeMini(id); if (!o) return;
  const seen = arr.filter(v => v != null);
  if (seen.length < 2) { o.g.fillStyle = "#7a889b"; o.g.font = "11px system-ui,sans-serif"; o.g.fillText("collecting…", 8, o.h / 2); return; }
  const mn = Math.min(...seen), mx = Math.max(...seen, mn + 1);
  o.g.strokeStyle = "#ffb454"; o.g.lineWidth = 1; o.g.beginPath();
  let pen = false;   // a null is an observation gap: lift the pen, never interpolate across it
  arr.forEach((v, i) => {
    if (v == null) { pen = false; return; }
    const x = i / (arr.length - 1) * o.w, y = o.h - (v - mn) / (mx - mn) * (o.h - 4) - 2;
    pen ? o.g.lineTo(x, y) : o.g.moveTo(x, y);
    pen = true;
  });
  o.g.stroke();
}

/* ---- diagnostics ----------------------------------------------------------
   One line per frame key, written by hand from brainsim/telemetry.py
   make_frame() and brainsim/engine.py. A key that cannot be explained from the
   code gets a source reference, never a guess.                              */
const KEY_GLOSS = {
  t: "Simulated time so far, counted in the simulator's own steps since this run started.",
  age_s: "The same simulated time in seconds: t multiplied by dt_ms, divided by 1000.",
  phase: "Which phase the simulator is in now. It flips on its own after wake_ticks or sleep_ticks steps.",
  g: "Plasticity gain: the multiplier on every change to a connection's strength. g_wake awake, g_sleep asleep.",
  g_struct: "Structural gain: how fast connections are created and destroyed per sweep. Starts high and decays as age_s grows.",
  sense_gated: "True while input from outside is blocked. Set when the sleep phase begins; a stimulus aimed only at input cells is refused while it is true.",
  ticks: "How many steps of simulated time this one packet covered. Zero means a heartbeat packet: nothing advanced.",
  seq: "Packet counter for this run, going up by one each time. A jump means packets were lost on the way here.",
  wall_ratio: "Simulated seconds achieved per real second, measured by the simulator over roughly the last real second.",
  n_syn_alive: "How many connections exist right now.",
  syn_born_total: "Connections created since this run started.",
  syn_died_total: "Connections destroyed since this run started.",
  born_count: "Connections created during this packet.",
  died_count: "Connections destroyed during this packet.",
  born_per_s: "Connections created in the most recent structural sweep, which runs every sweep_ticks steps.",
  died_per_s: "Connections destroyed in the most recent structural sweep: the rate-driven ones plus those whose strength had fallen too low.",
  spike_total: "Total spikes by all cells since this run started.",
  syn_touched_mean: "Average number of connections the simulator handled per step in this packet. A cost measure of the simulation, not a property of the network.",
  store_clamped: "True when the connection store is nearly full (WINDUP_CAP_FRAC of S_MAX). While true, no new connections are created anywhere.",
  truncated: "True when the list of spiking cell ids hit frame_spike_cap. The per-step counts stay exact.",
  spikes: "Which cells fired and in which step of this packet. Capped at frame_spike_cap.",
  "born / died": "The pairs of cells whose connection was created or destroyed in this packet, capped at FRAME_STRUCT_CAP.",
  stim_active: "Stimuli the simulator still has running, each with its own count of steps delivered so far.",
  stim_events: "Started and ended events for stimuli in this packet. These, and only these, set a stimulus's start and end on this page.",
  hetero: "Heterosynaptic write (SPEC 8.16), a labelled proxy and not biology. on is the flag; sweeps is how many wake sweeps applied it; cells_last, syn_last, up_last and down_last are the cells and synapses touched at the last write and how many went up and down; cells_total is the running count; mean_abs_dw_last and net_dw_last are the mean absolute and the summed weight change as fractions of w_max; t_last is the tick of the last write and cell_ids_last the cells involved.",
  encode: "Encode-mode (SPEC 8.12), a labelled proxy schedule and not biology. mode is the flag; stage is off, idle, present or grace; W is the hpc excitatory cells the identification pass picked; spiked_last_50 is which of them fired in the last window_ticks steps; t_present_end and t_grace_end are the ticks the writes land and the mask comes off."
};
function glossFor(key) {
  if (KEY_GLOSS[key]) return KEY_GLOSS[key];
  if (key.indexOf("growth_halted.") === 0)
    return "True when the anti-windup check found this group's average rate error had stopped improving: the " +
      "rate-driven creating and pruning of excitatory inputs for its cells is suspended until the error changes sign; " +
      "inhibitory inputs toward the E/I ratio are still created. A group is a region plus E (excitatory) or I (inhibitory).";
  if (key.indexOf("regions.") === 0)
    return "Average spikes per second per cell in this group over this packet.";
  return "(see brainsim/telemetry.py make_frame)";
}

/* Rows are built once, in a fixed order, for every key a frame can carry; from
   then on only the text inside a value cell changes. Nothing is inserted,
   removed or reordered while frames arrive, so no section below can move. */
function buildKeyRows() {
  if (!L || !st.lastFrame) return;
  const order = UI.frameRowKeys({
    keys: Object.keys(st.lastFrame),
    growth: Object.keys(st.lastFrame.growth_halted || {}),
    regions: Object.keys(L.regions || {})
  });
  const body = $("#framekeys").querySelector("tbody");
  body.innerHTML = order.map(k =>
    `<tr class="${k === "stim_active" || k === "stim_events" || k === "encode" || k === "hetero" ? "json" : ""}"><td class="val kcell">${E(k)}</td><td class="val vcell"></td><td class="gcell">${E(glossFor(k))}</td></tr>`
  ).join("");
  st.keyRows = Object.create(null);
  order.forEach((k, i) => { st.keyRows[k] = body.rows[i].cells[1]; });
}
function keyValue(f, key) {
  if (key === "spikes")
    return f.spikes.length + " ids" + (f.truncated && C ? " (capped at " + C.frame_spike_cap + "; per-step counts exact)" : "");
  if (key === "born / died") return f.born.length + " / " + f.died.length + " pairs";
  if (key === "stim_active") return f.stim_active.length ? JSON.stringify(f.stim_active) : "[]";
  if (key === "stim_events") return f.stim_events.length ? JSON.stringify(f.stim_events) : "[]";
  if (key === "encode") return JSON.stringify(f.encode);
  if (key === "hetero") return JSON.stringify(f.hetero);
  if (key.indexOf("growth_halted.") === 0) return String(f.growth_halted[key.slice(14)]);
  if (key.indexOf("regions.") === 0) {
    const r = f.regions[key.slice(8, key.length - 8)];
    return r ? r.rate_hz + " Hz over this packet (" + tickWord(f.ticks) + ")" : "—";
  }
  return String(f[key]);
}
function renderFrameKeys(f) {
  if (!st.keyRows) buildKeyRows();
  if (!st.keyRows) return;
  for (const key of Object.keys(st.keyRows)) {
    const cell = st.keyRows[key], text = keyValue(f, key);
    /* the value cell has a fixed width and clips; the full value is on hover
       and, raw, in the Message log panel below */
    if (cell.textContent !== text) { cell.textContent = text; cell.title = text; }
  }
}
function buildRasters() {
  const host = $("#rasters"); host.innerHTML = "";
  for (const n of st.regionNames) {
    const wrap = document.createElement("div");
    wrap.innerHTML = `<div class="note tight" style="font-size:11px">${E(n)}</div><canvas class="raster" id="raster-${E(n)}"></canvas>`;
    host.appendChild(wrap);
  }
  resize();
}
const GAP_COLS = 3;   // width of the "no observation" break, in raster columns
function pushRasters(f) {
  if (st.gapNow) st.synHist.push(null);   // breaks the sparkline at the gap
  st.synHist.push(f.n_syn_alive);
  while (st.synHist.length > 600) st.synHist.shift();
  if (!f.ticks) return;
  for (const [n, r] of Object.entries(f.regions)) {
    const c = document.getElementById("raster-" + n); if (!c) continue;
    const g = c.getContext("2d");
    if (st.gapNow) {   // scroll in a blank, hatched column: nothing was observed here
      g.drawImage(c, -GAP_COLS, 0);
      g.fillStyle = "#070a0e"; g.fillRect(c.width - GAP_COLS, 0, GAP_COLS, c.height);
      g.fillStyle = "#3a4457"; g.fillRect(c.width - GAP_COLS + 1, 0, 1, c.height);
    }
    const spt = r.spikes_per_tick, k = spt.length;
    g.drawImage(c, -k, 0);
    g.fillStyle = "#070a0e"; g.fillRect(c.width - k, 0, k, c.height);
    const mx = Math.max(1, ...spt);
    for (let i = 0; i < k; i++) {
      const v = spt[i] / mx, hh = Math.round(v * c.height);
      g.fillStyle = `rgba(106,168,224,${0.2 + 0.8 * v})`;
      g.fillRect(c.width - k + i, c.height - hh, 1, hh);
    }
  }
}
function logMsg(dir, msg) {
  let text;
  if (dir === "out") text = "→ " + JSON.stringify(msg);
  else if (msg.type === "frame") text = `← frame seq ${msg.seq} t ${msg.t} ticks ${msg.ticks} spikes ${msg.spikes.length}${msg.truncated ? " TRUNCATED" : ""}`;
  else if (msg.type === "layout") text = `← layout (${msg.x.length} cells, ${msg.synapse_sample.length} sampled synapses, ${msg.patterns.length} patterns)`;
  else text = "← " + JSON.stringify(msg).slice(0, 400);
  st.log.unshift({ dir, text, err: msg.type === "error" });
  if (st.log.length > 200) st.log.pop();
}
setInterval(() => {
  if (st.tab !== "diag") return;
  $("#log").innerHTML = st.log.map(l => `<div class="${l.err ? "err" : (l.dir === "out" ? "out" : "")}">${escapeHtml(l.text)}</div>`).join("");
}, 400);
function escapeHtml(s) {
  return String(s).replace(/[&<>"'`]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;", "`": "&#96;" }[c]));
}
const E = escapeHtml;

/* ---- recorded results (real, hand-maintained, served as JSON) ---- */
function renderRecorded(rec, hostId) {
  const byCommit = [];
  for (const e of UI.failuresFirst(rec.entries)) {
    const key = (e.carried_forward ? "cf:" : "run:") + e.tested_commit;
    let g = byCommit.find(q => q.key === key);
    if (!g) {
      g = {
        key, commit: e.tested_commit, carried: !!e.carried_forward,
        date: e.date, rows: []
      };
      byCommit.push(g);
    }
    g.rows.push(e);
  }
  const carriedAny = byCommit.some(g => g.carried);
  const chipOf = o => o === "pass" ? ["pass", "pass"] : o === "reject" ? ["reject", "REJECT"] : ["fail", "FAIL"];
  $("#" + hostId).innerHTML = (rec.note ? `<p class="note tight">${E(rec.note)}</p>` : "") +
    (carriedAny ? "" : `<p class="note tight">No results carried forward from earlier commits.</p>`) +
    byCommit.map(g => {
    const head = g.carried
      ? `Carried forward from ${g.commit} (${g.date}), not rerun at ${rec.updated_commit}`
      : `Run at ${g.commit} (${g.date})`;
    const note = g.carried ? (g.rows[0].carried_note || null) : null;
    return `<h4>${E(head)}</h4>` +
      (note ? `<p class="note tight">${E(note)}</p>` : "") +
      `<div class="tblwrap"><table><thead><tr><th>outcome</th><th>test</th><th>node id</th><th>evidence</th></tr></thead><tbody>` +
      g.rows.map(e => {
        const [cls, word] = chipOf(e.outcome);
        return `<tr><td><span class="chip ${cls}">${E(word)}</span></td>` +
        `<td>${E(e.label)}${e.note ? `<div class="note tight" style="white-space:normal;max-width:46ch">${E(e.note)}</div>` : ""}</td>` +
        `<td class="val" style="color:var(--dim)">${E(e.test)}</td>` +
        `<td class="val evcell">${E(e.evidence)}</td></tr>`;
      }).join("") +
      `</tbody></table></div>`;
  }).join("");
}
/* The header chip is computed from the record files, never written by hand:
   whatever the record says is red is what the chip says. */
function renderStageChip() {
  el.stagechip.textContent = UI.stageChipText(st.records[0], st.records[1]);
}
function loadRecord(stage, file, hostId) {
  fetch(file)
    .then(r => r.json())
    .then(rec => { st.records[stage] = rec; renderRecorded(rec, hostId); renderStageChip(); })
    .catch(() => {
      $("#" + hostId).innerHTML = `<p class="note">${E(file)} could not be loaded.</p>`;
      renderStageChip();
    });
}
loadRecord(0, "stage0_results.json", "recgroups");
loadRecord(1, "stage1_results.json", "recgroups1");

/* ---- display-preference copy (never from the worker) ---- */
function renderDisplayPrefs() {
  el.legGlow.innerHTML =
    `<i class="swatch" style="background:#fff"></i>glow = display fade, ${E(DISPLAY.GLOW_MS)} ms`;
  el.legGlow.title =
    `measured spikes: the dot brightens and fades over ${DISPLAY.GLOW_MS} ms of wall time; display only, not continued firing`;
  const sl = $("#structlabel");
  sl.lastChild.textContent =
    ` structural changes (births/deaths, ${DISPLAY.STRUCT_FLASH_MS} ms flash, display)`;
  el.tllegend.textContent = `last ${DISPLAY.TIMELINE_WINDOW_S} s of simulated time`;
  $("#cmdcaption").textContent = `Newest first · last ${DISPLAY.CARD_HISTORY_MAX}`;
  $("#dispjson").textContent = JSON.stringify(DISPLAY, null, 1);
}

/* ---- tabs + keyboard ---- */
function setTab(name) {
  st.tab = name;
  $("#observe").hidden = name !== "observe";
  $("#diag").hidden = name !== "diag";
  $("#tab-observe").setAttribute("aria-selected", String(name === "observe"));
  $("#tab-diag").setAttribute("aria-selected", String(name === "diag"));
  if (name === "observe") requestAnimationFrame(resize);
  if (name === "diag") { renderCmdFull(); if (st.lastFrame) renderFrameKeys(st.lastFrame); }
}
$("#tab-observe").onclick = () => setTab("observe");
$("#tab-diag").onclick = () => setTab("diag");
$("#stagechip").onclick = () => { setTab("diag"); $("#recorded").scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" }); };

addEventListener("keydown", e => {
  const tag = (e.target.tagName || "").toLowerCase();
  const typing = tag === "input" || tag === "select" || tag === "textarea";
  if (e.key === "Escape") { closeDrawer(); return; }
  if (typing) return;
  if ((e.key === " " || e.key === "Enter") && (tag === "button" || tag === "summary" || tag === "a")) return;
  if (e.key === "1") { setTab("observe"); return; }
  if (e.key === "2") { setTab("diag"); return; }
  const pi = "asdf".indexOf(e.key.toLowerCase());
  if (pi >= 0 && L && C && L.patterns && L.patterns[pi]) { e.preventDefault(); presentPattern(pi); return; }
  if (e.key === " ") { e.preventDefault(); el.runbtn.click(); return; }
  if (e.key === ".") { e.preventDefault(); $("#stepbtn").click(); return; }
});

/* ---- boot: the page renders before anything has arrived ---- */
$("#regionheads").innerHTML = '<span class="note tight">waiting for the simulator\'s layout</span>';
el.patcaption.textContent = "waiting for the simulator's pattern layout";
renderDisplayPrefs();
readExplainPrefs();
renderExplainers();
renderHeader();
renderControls();
renderRows();
resize();
requestAnimationFrame(raf);
connect();
