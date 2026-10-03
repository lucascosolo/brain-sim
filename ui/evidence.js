"use strict";
/* Evidence reconciliation for the brain-sim client.
   Pure: no DOM, no timers, no clocks of its own. The caller passes `now`.
   Dual-exported so `node --test` can require it and the page can script-tag it.

   How evidence reconciles (the rules this module implements):
   1. A `result` sets acceptance/rejection. Nothing else can. A result whose
      `req` does not start with clientId + ":" is logged only.
   2. `stim_events` set start/end when observed. Absence from `stim_active`
      sets nothing.
   3. A gap (seq jump or t discontinuity) marks every card accepted and not
      ended as "unknown since t = <last observed tick>" and asks for stimlog.
   4. A stimlog entry with a matching stim_id fills what is unknown; the row
      says "recovered from stimlog".
   5. If stimlog has no such stim_id (history expired, or a different run) the
      row reads "history expired; end never observed". Nothing is filled in.
   6. On reconnect in the same run: layout, config, status and stimlog are
      re-requested; the unobserved span is a gap; rules 3-5 apply.
   7. A result after the unconfirmed timeout replaces "unconfirmed"; nothing
      is ever resent automatically. */

(function () {

  function create(opts) {
    opts = opts || {};
    const display = opts.display || {};
    const nowOpt = opts.now;
    const nowFn = typeof nowOpt === "function"
      ? nowOpt
      : function () { return typeof nowOpt === "number" ? nowOpt : 0; };

    const UNCONFIRMED_MS = num(display.UNCONFIRMED_AFTER_MS, 1000);
    const WINDOW_S = num(display.TIMELINE_WINDOW_S, 30);
    const HISTORY_MAX = num(display.DETAILS_HISTORY_MAX, 64);

    const S = {
      clientId: null, runId: null, sim: "unknown", conn: "connecting",
      config: null, layout: null, lastStatus: null,
      t: null, prevT: null, prevSeq: null,
      cards: [], byReq: new Map(), byStim: new Map(), earlyEvents: [],
      frames: [], gaps: [], requests: [], reqSeq: 0
    };

    /* ---- formatting (every displayed constant comes from `config`) ---- */
    function dtMs() { return S.config ? S.config.dt_ms : null; }
    function secs(ticks) {
      const dt = dtMs();
      return dt == null ? String(ticks) : (ticks * dt / 1000).toFixed(2);
    }
    function fmtT(ticks) {
      const dt = dtMs();
      return dt == null ? ticks + " ticks" : (ticks * dt / 1000).toFixed(2) + " s";
    }
    function fmtTk(ticks) {
      const dt = dtMs();
      return dt == null ? ticks + " ticks"
        : Number(ticks).toLocaleString() + " ticks (" + (ticks * dt / 1000).toFixed(3) + " s)";
    }
    function msOf(ticks) { const dt = dtMs(); return dt == null ? ticks : ticks * dt; }

    /* ---- sending ---- */
    function send(cmd, fields, meta) {
      const req = String(++S.reqSeq);
      const out = Object.assign({ cmd: cmd }, fields || {}, { req: req });
      const card = Object.assign({
        req: req, cmd: cmd, label: cmd, status: "pending",
        sentAt: nowFn(), ageMs: 0, stim_id: null, delivered: null,
        t_start: null, t_end: null, t_accept: null, t_end_planned: null,
        lastSeenT: null, cells: null, letter: null, patternIndex: null
      }, meta || {});
      S.cards.unshift(card);
      S.byReq.set(req, card);
      evict();
      return out;
    }

    /* cards past the history bound are gone: drop their lookup keys too, so a
       late result or stim event for an evicted card finds nothing */
    function evict() {
      for (const c of S.cards.splice(HISTORY_MAX)) {
        S.byReq.delete(c.req);
        if (c.stim_id != null) S.byStim.delete(c.stim_id);
      }
    }

    /* ---- timeouts ---- */
    function tick(nowMs) {
      const notes = [];
      for (const c of S.cards) {
        c.ageMs = nowMs - c.sentAt;
        if (c.status === "pending" && c.ageMs > UNCONFIRMED_MS) {
          c.status = "unconfirmed";
          notes.push(name(c) + " unconfirmed after " + (c.ageMs / 1000).toFixed(1) + " s");
        }
      }
      return notes;
    }

    /* ---- the single entry point ---- */
    function apply(msg) {
      const notes = [];
      if (!msg || typeof msg !== "object") return notes;

      if (msg.type === "hello") { S.clientId = msg.client_id; return notes; }

      if (msg.run_id) {
        if (S.runId == null) S.runId = msg.run_id;
        else if (msg.run_id !== S.runId) {
          restart(msg.run_id, notes);
          if (msg.type !== "layout" && msg.type !== "config" && msg.type !== "status") return notes;
        }
      }

      if (msg.type === "config") { S.config = msg; trimWindow(); return notes; }
      if (msg.type === "layout") { S.layout = msg; return notes; }
      if (msg.type === "status") {
        S.lastStatus = { running: !!msg.running, speed: msg.speed, t: msg.t };
        S.sim = msg.running ? "running" : "paused";
        if (msg.t != null) S.t = msg.t;
        return notes;
      }
      if (msg.type === "frame") return applyFrame(msg, notes);
      if (msg.type === "result") return applyResult(msg, notes);
      if (msg.type === "stimlog") return applyStimlog(msg, notes);
      if (msg.type === "error") {
        notes.push("error on " + String(msg.cmd) + ": " + String(msg.msg));
        return notes;
      }
      return notes;
    }

    /* Rule: evidence from a different run is never attached to existing state. */
    function restart(newRun, notes) {
      S.runId = newRun;
      S.cards = []; S.byReq = new Map(); S.byStim = new Map(); S.earlyEvents = [];
      S.frames = []; S.gaps = []; S.prevT = null; S.prevSeq = null; S.t = null;
      S.sim = "unknown"; S.lastStatus = null;
      notes.push("simulator restarted: new run " + newRun + ", previous evidence cleared");
      request("layout");
      request("stimlog");
    }

    function request(cmd) { if (S.requests.indexOf(cmd) < 0) S.requests.push(cmd); }
    function takeRequests() { const r = S.requests; S.requests = []; return r; }

    function applyFrame(f, notes) {
      if (S.prevT != null && (f.seq !== S.prevSeq + 1 || f.t - f.ticks !== S.prevT)) {
        const t0 = S.prevT, t1 = f.t - f.ticks;
        if (t1 > t0) S.gaps.push({ t0: t0, t1: t1 });
        notes.push("observation gap: no frames between t = " + fmtT(t0) + " and t = " + fmtT(t1)
          + "; asking for stimlog");
        request("stimlog");
        markUnknown(notes);
      }
      S.prevT = f.t; S.prevSeq = f.seq; S.t = f.t;

      /* heartbeats never advance the timeline */
      if (f.ticks > 0) {
        const rates = {};
        for (const rn of Object.keys(f.regions || {})) rates[rn] = f.regions[rn].rate_hz;
        S.frames.push({
          t: f.t, ticks: f.ticks, seq: f.seq, phase: f.phase,
          truncated: !!f.truncated, rates: rates
        });
      }
      trimWindow();

      for (const se of f.stim_events || []) {
        const card = S.byStim.get(se.stim_id);
        if (!card) { S.earlyEvents.push(se); continue; }
        applyStimEvent(card, se, notes);
      }
      for (const sa of f.stim_active || []) {
        const card = S.byStim.get(sa.stim_id);
        if (!card) continue;
        if (sa.delivered_ticks != null) {
          card.delivered = sa.delivered_ticks;
          card.deliveredFrom = "stim_active in frames";
        }
        card.lastSeenT = f.t;
        if (sa.t_first_applied != null && card.t_start == null) card.t_start = sa.t_first_applied;
      }
      return notes;
    }

    function applyStimEvent(card, se, notes) {
      if (se.event === "started") {
        if (card.status !== "ended") card.status = "running";
        card.t_start = se.t;
        notes.push(name(card) + " started at t = " + secs(se.t) + " s");
      } else if (se.event === "ended") {
        card.status = "ended";
        card.t_end = se.t != null ? se.t : card.t_end;
        card.t_dropped = se.t_dropped;
        /* the ended event carries the engine's own counts at drop; take them
           from the message rather than from what frames happened to show */
        if (se.delivered_ticks != null) {
          card.delivered = se.delivered_ticks;
          card.gated = se.gated_ticks;
          card.partiallyGated = se.partially_gated_ticks;
          card.deliveredFrom = "stim_events ended event";
        }
        notes.push(name(card) + " ended at t = " + secs(card.t_end != null ? card.t_end : se.t_dropped) + " s");
      }
    }

    /* Rule 3: a gap marks every card that was accepted and not yet ended
       "unknown since t = <last observed tick>". The start may also have been
       lost, so t_start is left alone. */
    function markUnknown(notes) {
      for (const c of S.cards) {
        if (c.stim_id == null) continue;
        if (c.status !== "accepted" && c.status !== "running") continue;
        c.status = "unknown";
        c.unknownSince = c.lastSeenT != null ? c.lastSeenT
          : (c.t_start != null ? c.t_start : c.t_accept);
        notes.push(name(c) + " unknown since t = " + fmtT(c.unknownSince));
      }
    }

    function applyResult(msg, notes) {
      /* Rule 1: another client's result is evidence about the simulator, not
         about this client's commands. It is logged and nothing else. */
      const prefix = S.clientId == null ? null : S.clientId + ":";
      if (typeof msg.req !== "string" || prefix == null || msg.req.indexOf(prefix) !== 0) return notes;
      const c = S.byReq.get(msg.req.slice(prefix.length));
      if (!c) return notes;

      c.t = msg.t;
      c.reason = msg.reason;
      if (msg.status === "rejected") {
        c.status = "rejected";
        notes.push(name(c) + " rejected: " + String(msg.reason));
        return notes;
      }
      if (msg.status === "executed") {
        c.status = "executed"; c.t_exec = msg.t;
        notes.push(name(c) + " executed at t = " + secs(msg.t) + " s");
        return notes;
      }
      c.status = "accepted";
      c.t_accept = msg.t_accept;
      c.t_target = msg.t_target;
      c.factor = msg.factor;
      c.phase_before = msg.phase_before;
      c.phase_after = msg.phase_after;
      c.changed = msg.changed;
      c.phase_clock_reset = msg.phase_clock_reset;
      if (msg.stim_id != null) {
        c.stim_id = msg.stim_id;
        c.n_cells = msg.n_cells;
        c.amp_mv = msg.amp_mv;
        c.t_end_planned = msg.t_end_planned;
        S.byStim.set(msg.stim_id, c);
        for (const se of S.earlyEvents.filter(x => x.stim_id === msg.stim_id)) applyStimEvent(c, se, notes);
        S.earlyEvents = S.earlyEvents.filter(x => x.stim_id !== msg.stim_id);
      }
      notes.push(name(c) + " accepted");
      return notes;
    }

    function applyStimlog(msg, notes) {
      const seen = new Set();
      const rows = (msg.entries || []).concat(msg.active || []);
      for (const rec of rows) {
        seen.add(rec.stim_id);
        const c = S.byStim.get(rec.stim_id);
        if (!c) continue;
        if (rec.t_first_applied != null && c.t_start == null) c.t_start = rec.t_first_applied;
        if (rec.delivered_ticks != null) {
          c.delivered = rec.delivered_ticks;
          c.gated = rec.gated_ticks;
          c.partiallyGated = rec.partially_gated_ticks;
          c.deliveredFrom = "stimlog entry";
        }
        if (rec.t_end_planned != null && c.t_end_planned == null) c.t_end_planned = rec.t_end_planned;
        if (rec.done && c.status !== "ended") {
          c.status = "ended";
          c.t_end = rec.t_last_applied != null ? rec.t_last_applied : rec.t_dropped;
          c.t_dropped = rec.t_dropped;
          c.fromLog = true;
          notes.push(name(c) + " recovered from stimlog");
        }
      }
      /* Rule 5: absent from a history that is already at its bound -> the end
         is gone for good. If we have not been told the bound we cannot claim
         that, so the card says only that the end was not observed. */
      const entries = msg.entries || [];
      const cap = S.config ? S.config.stimlog_max : null;
      const bounded = cap != null && entries.length >= cap;
      for (const c of S.cards) {
        if (c.stim_id == null || seen.has(c.stim_id)) continue;
        if (["unknown", "unsized", "accepted", "running"].indexOf(c.status) < 0) continue;
        c.historySize = entries.length;
        if (bounded) {
          c.status = "expired";
          notes.push(name(c) + ": history expired; end never observed");
        } else if (cap == null) {
          c.status = "unsized";
          notes.push(name(c) + ": end not observed (history size unknown)");
        }
      }
      return notes;
    }

    function trimWindow() {
      if (!S.config || !S.frames.length) {
        if (S.frames.length > 1200) S.frames.splice(0, S.frames.length - 1200);
        return;
      }
      const winTicks = WINDOW_S * 1000 / S.config.dt_ms;
      const cut = S.frames[S.frames.length - 1].t - winTicks;
      while (S.frames.length && S.frames[0].t < cut) S.frames.shift();
      S.gaps = S.gaps.filter(g => g.t1 >= cut);
    }

    /* ---- card copy ---- */
    function name(c) {
      return c.letter || (c.cmd === "inject" ? "Injection" : c.cmd);
    }
    function verbFor(c) {
      return c.cmd === "present" ? "presented" : (c.cmd === "inject" ? "injected" : "done");
    }
    function plannedTicks(c) {
      return (c.t_end_planned != null && c.t_accept != null) ? c.t_end_planned - c.t_accept : 0;
    }
    function plannedMs(c) {
      return msOf((c.t_end_planned != null && c.t_accept != null) ? c.t_end_planned - c.t_accept : 0);
    }
    function outcome(c) {
      const nm = name(c);
      if (c.status === "not_sent") return { cls: "bad", text: nm + " not sent · disconnected" };
      if (c.status === "pending") return { cls: "", text: nm + " sent · no reply yet" };
      if (c.status === "unconfirmed")
        return { cls: "warn", text: nm + " sent · unconfirmed after " + (c.ageMs / 1000).toFixed(1) + " s · still waiting" };
      if (c.status === "rejected") {
        const head = c.cmd === "present" ? "Not presented" : (c.cmd === "inject" ? "Not injected" : "Rejected");
        const why = c.reason === "sense_gated" ? "sensory input is gated during sleep"
          : c.reason === "no_cells" ? "no cell survived the sense gate"
            : String(c.reason || "").replace(/^invalid:\s*/, "");
        return { cls: "bad", text: head + ": " + why };
      }
      if (c.status === "expired")
        return { cls: "warn", text: nm + " " + verbFor(c) + " · history expired; end never observed" };
      if (c.status === "unsized")
        return { cls: "warn", text: nm + " " + verbFor(c) + " · end not observed (history size unknown)" };
      if (c.status === "unknown")
        return {
          cls: "warn", text: c.t_start == null
            ? nm + " " + verbFor(c) + " · start and end not observed"
            : nm + " " + verbFor(c) + " · end not observed (frames missed)"
        };
      if (c.status === "ended") {
        const started = c.t_start != null ? " · started " + secs(c.t_start) + " s" : "";
        if (c.delivered == null) return { cls: "ok", text: nm + " " + verbFor(c) + " · " + plannedMs(c) + " ms" + started };
        const span = plannedTicks(c);
        /* every qualifier the engine reported, in the headline: a stimulus that
           straddled a phase flip must not read as cleanly delivered */
        const bits = [c.delivered + " of " + span + " ticks delivered"];
        if (c.gated) bits.push(c.gated + " gated");
        if (c.partiallyGated) bits.push(c.partiallyGated + " partially gated");
        return { cls: "ok", text: nm + " " + verbFor(c) + " · " + bits.join(", ") + started };
      }
      if (c.status === "running")
        return {
          cls: "ok", text: nm + " " + (c.cmd === "inject" ? "injecting" : "presenting")
            + " · " + msOf(c.delivered || 0) + " of " + plannedMs(c) + " ms observed"
        };
      if (c.status === "executed")
        return { cls: "ok", text: nm + " executed at " + secs(c.t_exec) + " s" };
      if (c.status === "accepted") {
        if (c.stim_id != null) {
          if (S.sim === "paused") return { cls: "", text: nm + " accepted · waiting for the simulator to run" };
          if (S.sim === "unknown") return { cls: "warn", text: nm + " accepted · simulator state unknown" };
          return { cls: "", text: nm + " accepted · waiting for ticks" };
        }
        if (c.cmd === "sleep")
          /* the same command enters and leaves the sleep phase (on:true/false),
             so the row is named by what was asked for, not by the command name */
          return {
            cls: "ok", text: (c.label || "sleep") + " · " + c.phase_before + " → " + c.phase_after
              + " · changed: " + c.changed + " · phase clock restarted"
          };
        if (c.cmd === "speed")
          return { cls: "ok", text: "speed accepted · " + (c.factor === 0 ? "max" : c.factor + "x") };
        if (c.cmd === "step") return { cls: "", text: "step accepted · not executed yet" };
        return { cls: "ok", text: nm + " accepted at " + secs(c.t) + " s" };
      }
      return { cls: "", text: nm + " sent" };
    }

    function details(c) {
      const d = [
        ["req", (S.clientId ? S.clientId + ":" : "") + c.req],
        ["run_id", S.runId || "—"],
        ["command", c.label]
      ];
      if (c.stim_id != null) {
        d.push(["stim_id", c.stim_id]);
        d.push(["cells after gate", c.n_cells]);
        d.push(["amp_mv", c.amp_mv]);
        d.push(["accepted tick", fmtTk(c.t_accept)]);
        d.push(["planned end", fmtTk(c.t_end_planned)]);
        d.push(["observed start", c.t_start != null ? fmtTk(c.t_start) : "not observed"]);
        d.push(["observed end", c.t_end != null ? fmtTk(c.t_end) : "not observed"]);
        d.push(["delivered", (c.delivered != null ? c.delivered : 0) + " of " + plannedTicks(c) + " ticks"
          + (c.gated ? ", " + c.gated + " gated" : "")
          + (c.partiallyGated ? ", " + c.partiallyGated + " partly gated" : "")]);
        d.push(["delivered reported by", c.deliveredFrom || "nothing yet"]);
        if (c.lastSeenT != null) d.push(["last seen at", fmtTk(c.lastSeenT)]);
        if (c.status === "unknown")
          d.push(["unknown since", fmtTk(c.unknownSince != null ? c.unknownSince : c.t_accept)]);
        if (c.status === "expired")
          d.push(["recovery", "stimlog returned " + c.historySize
            + " entries, none for this stim_id; nothing filled in"]);
        else if (c.fromLog) d.push(["recovery", "end recovered from stimlog"]);
        else if (c.status === "ended") d.push(["recovery", "start and end observed in stim_events"]);
      } else {
        if (c.t_accept != null) d.push(["accepted tick", fmtTk(c.t_accept)]);
        if (c.t_target != null) d.push(["target tick", fmtTk(c.t_target)]);
        if (c.t_exec != null) d.push(["executed tick", fmtTk(c.t_exec)]);
        else if (c.t != null) d.push(["result tick", fmtTk(c.t)]);
        if (c.cmd === "step" && c.t_exec == null) d.push(["note", "a status reply never confirms a step"]);
      }
      d.push(["raw status", c.status + (c.reason ? " / " + c.reason : "")]);
      return d;
    }

    function state() {
      const cards = S.cards.map(function (c) {
        const o = outcome(c);
        return Object.assign({}, c, { outcome: o, text: o.text, cls: o.cls, details: details(c) });
      });
      const stims = {};
      for (const c of cards) if (c.stim_id != null) stims[c.stim_id] = c;
      return {
        runId: S.runId, sim: S.sim, conn: S.conn, t: S.t,
        clientId: S.clientId, config: S.config, layout: S.layout,
        lastStatus: S.lastStatus, requests: S.requests.slice(),
        cards: cards, stims: stims,
        timeline: {
          frames: S.frames.slice(),
          gaps: S.gaps.slice(),
          stims: cards.filter(c => c.stim_id != null)
        }
      };
    }

    const ev = {
      send: send, apply: apply, tick: tick, state: state,
      takeRequests: takeRequests,
      card: function (req) { return S.byReq.get(String(req)) || null; },
      setConn: function (s) { S.conn = s; return S.conn; },
      /* a reconnect in the same run: the unobserved span becomes a gap on the
         next frame, so prevT/prevSeq are deliberately kept (rule 6). */
      reconnected: function () { S.conn = "live"; S.sim = "unknown"; request("layout"); request("stimlog"); },
      fmtT: fmtT, fmtTk: fmtTk, msOf: msOf, secs: secs
    };
    Object.defineProperty(ev, "clientId", {
      enumerable: true,
      get: function () { return S.clientId; },
      set: function (v) { S.clientId = v; }
    });
    return ev;
  }

  function num(v, d) { return typeof v === "number" && isFinite(v) ? v : d; }

  /* ---- pure display helpers -------------------------------------------------
     No DOM, no clock, no mutation of their arguments. They live in this file
     because it is the only client file both the page and `node --test` load;
     they are not part of evidence reconciliation and read no engine message. */

  function outcomeCounts(rec) {
    const out = { pass: 0, fail: 0, reject: 0, other: 0, total: 0 };
    const rows = rec && Array.isArray(rec.entries) ? rec.entries : [];
    for (const ent of rows) {
      const o = ent && ent.outcome;
      if (o === "pass") out.pass++;
      else if (o === "fail") out.fail++;
      else if (o === "reject") out.reject++;
      else out.other++;
      out.total++;
    }
    return out;
  }

  /* Header chip text. Never a constant: every word is a count of
     entries[].outcome in the record files the page fetched. */
  function stageChipText(stage0, stage1) {
    let seg0;
    if (stage0 == null) seg0 = "Stage 0 · record not loaded";
    else {
      const c0 = outcomeCounts(stage0);
      const red = c0.fail + c0.reject + c0.other;
      seg0 = red > 0
        ? "Stage 0 · " + red + " kill test" + (red === 1 ? "" : "s") + " red"
        : "Stage 0 · no kill test red";
    }
    let seg1;
    if (stage1 == null) seg1 = "Stage 1 · record not loaded";
    else {
      const c1 = outcomeCounts(stage1);
      const bits = [];
      if (c1.fail > 0) bits.push(c1.fail + " fail");
      if (c1.reject > 0) bits.push(c1.reject + " reject" + (c1.reject === 1 ? "" : "s"));
      seg1 = "Stage 1 · " + (bits.length ? bits.join(" ")
        : (c1.pass > 0 ? c1.pass + " pass" : "no results recorded"));
    }
    return seg0 + " · " + seg1;
  }

  /* Failures and rejects first, original order kept inside each rank, so a
     handful of red rows cannot hide among dozens of green ones. */
  function failuresFirst(entries) {
    if (!Array.isArray(entries)) return [];
    const rank = ent => {
      const o = ent && ent.outcome;
      return o === "fail" ? 0 : o === "reject" ? 1 : o === "pass" ? 3 : 2;
    };
    return entries
      .map((ent, i) => [ent, i])
      .sort((a, b) => (rank(a[0]) - rank(b[0])) || (a[1] - b[1]))
      .map(p => p[0]);
  }

  const ROW_SKIP = ["type", "run_id", "regions", "spikes", "born", "died",
    "stim_active", "stim_events", "growth_halted"];
  const ROW_TAIL = ["spikes", "born / died", "stim_active", "stim_events"];

  function uniqSorted(list) {
    const seen = Object.create(null), out = [];
    for (const s of (Array.isArray(list) ? list : [])) {
      const k = String(s);
      if (seen[k]) continue;
      seen[k] = 1; out.push(k);
    }
    return out.sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  }

  /* The Diagnostics key table's row order, computed once from the key sets
     rather than from whatever order a frame's keys happen to arrive in: rows
     are then created once and only their text changes, so nothing moves. */
  function frameRowKeys(spec) {
    const s = spec || {};
    const scalars = uniqSorted(s.keys).filter(k => ROW_SKIP.indexOf(k) < 0);
    const growth = uniqSorted(s.growth).map(g => "growth_halted." + g);
    const regions = uniqSorted(s.regions).map(n => "regions." + n + ".rate_hz");
    return scalars.concat(growth, regions, ROW_TAIL);
  }

  const Evidence = {
    create: create,
    ui: {
      outcomeCounts: outcomeCounts, stageChipText: stageChipText,
      failuresFirst: failuresFirst, frameRowKeys: frameRowKeys
    }
  };
  if (typeof module !== "undefined" && module.exports) module.exports = Evidence;
  if (typeof window !== "undefined") window.Evidence = Evidence;
})();
