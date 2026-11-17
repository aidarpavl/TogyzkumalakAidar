  // ================= KOKPAR UI =================
  const send = (type, data) => window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type }, data), "*");
  const $ = (id) => document.getElementById(id);
  const cs = $("cs").getContext("2d"), cf = $("cf").getContext("2d"), cr = $("cr").getContext("2d");
  const L = () => (args && args.labels) || {};
  const setH = () => send("streamlit:setFrameHeight", { height: Math.ceil($("wrap").getBoundingClientRect().height + 8) });
  let args = null, mode = "idle", run = null, pending = false, seen = null, first = true, joy = { x: 0, y: 0, on: false }, keys = {};

  const COL = {
    p0: { horse: ["#a0612f", "#7a4621", "#4e2b13"], mane: "#1c0f07", hoof: "#2a1a10", blaze: "#f3ece0",
          robe: "#1d5a8e", robe2: "#123449", dress: "#f2efe8", trim: "#e3b23c", hat: "#7a1b26", fur: "#3b2a1c", tokym: "#1f6f8b", skin: "#d8a578", hair: "#140c08" },
    a1: { horse: ["#d4d4d0", "#a8a8a3", "#7a7a75"], mane: "#2f2f2f", hoof: "#2a2a2a", blaze: null,
          robe: "#1d5a8e", robe2: "#123449", dress: "#f2efe8", trim: "#e3b23c", hat: "#1b3a7a", fur: "#4a3826", tokym: "#1f6f8b", skin: "#d8a578", hair: "#140c08" },
    a2: { horse: ["#6b4a2e", "#4b311c", "#2e1c0f"], mane: "#0f0905", hoof: "#2a1a10", blaze: null,
          robe: "#1d5a8e", robe2: "#123449", dress: "#f2efe8", trim: "#e3b23c", hat: "#1b3a7a", fur: "#3b2a1c", tokym: "#1f6f8b", skin: "#d8a578", hair: "#140c08" },
    b0: { horse: ["#2e2a28", "#1d1a18", "#111"], mane: "#0b0b0b", hoof: "#222", blaze: "#efe8dc",
          robe: "#a51d2a", robe2: "#6e0c1b", dress: "#f2efe8", trim: "#e3b23c", hat: "#2a2a2a", fur: "#2f2318", tokym: "#8e1b2c", skin: "#d8a578", hair: "#140c08" },
    b1: { horse: ["#b5652e", "#8e4a1e", "#5e2e10"], mane: "#5a2a10", hoof: "#2a1a10", blaze: "#f3ece0",
          robe: "#a51d2a", robe2: "#6e0c1b", dress: "#f2efe8", trim: "#e3b23c", hat: "#2a2a2a", fur: "#4a3826", tokym: "#8e1b2c", skin: "#d8a578", hair: "#140c08" },
    b2: { horse: ["#c9b28a", "#a68c62", "#7a6442"], mane: "#3a2a1a", hoof: "#2a1a10", blaze: null,
          robe: "#a51d2a", robe2: "#6e0c1b", dress: "#f2efe8", trim: "#e3b23c", hat: "#2a2a2a", fur: "#2f2318", tokym: "#8e1b2c", skin: "#d8a578", hair: "#140c08" },
  };
  const KEYS = ["p0", "a1", "a2", "b0", "b1", "b2"];

  __GL3D__

  const V3 = setup3d();

  // ---- көрініс
  const W2 = (x, y) => [x, 0, y - 50];
  function fieldScene(sim, t, phases) {
    const { P, CYL, SPH, BOX, CONE, I4 } = G3, m = I4();
    P(m, BOX, [100, -0.05, 0], null, [520, 0.1, 300], [0.66, 0.66, 0.34]);
    P(m, BOX, [100, 0.004, 0], null, [200, 0.01, 100], [0.55, 0.62, 0.3]);
    [[100, -50, 200, 0.25], [100, 50, 200, 0.25]].forEach(([x, z, w]) => P(m, BOX, [x, 0.02, z], null, [w, 0.02, 0.3], [0.95, 0.95, 0.9]));
    [[0, 0], [200, 0]].forEach(([x]) => P(m, BOX, [x, 0.02, 0], null, [0.3, 0.02, 100], [0.95, 0.95, 0.9]));
    P(m, BOX, [100, 0.02, 0], null, [0.25, 0.02, 100], [0.95, 0.95, 0.9]);
    K.TARGET.forEach(([x, y], ti) => {   // қазандар
      const z = y - 50;
      P(m, CYL, [x, 0.55, z], null, [K.KR, 1.1, K.KR], [0.55, 0.38, 0.22], 0.05);
      P(m, CYL, [x, 1.12, z], null, [K.KR * 1.02, 0.08, K.KR * 1.02], ti === 0 ? [0.75, 0.15, 0.2] : [0.15, 0.35, 0.65], 0.4);
      for (let k = 0; k < 10; k++) { const a = k / 10 * 6.283; P(m, SPH, [x + Math.cos(a) * K.KR, 0.7, z + Math.sin(a) * K.KR], null, [0.12, 0.12, 0.12], [0.89, 0.7, 0.24], 0.8); }
      P(m, CYL, [x, 2.4, z + K.KR + 1], null, [0.06, 4.8, 0.06], [0.42, 0.27, 0.14]);
      P(m, BOX, [x + 0.7, 4.3, z + K.KR + 1], null, [1.3, 0.8, 0.03], ti === 0 ? [0.75, 0.15, 0.2] : [0.15, 0.35, 0.65], 0.2);
    });
    for (let k = 0; k < 8; k++) [-1, 1].forEach((sd) => {   // киіз үйлер мен көрермендер
      const x = 15 + k * 25, z = sd * 62;
      P(m, CYL, [x, 1.0, z], null, [3.2, 2.0, 3.2], [0.95, 0.93, 0.88], 0.02);
      P(m, CONE, [x, 2.8, z], null, [3.4, 1.6, 3.4], [0.92, 0.9, 0.84], 0.02);
      P(m, CYL, [x, 3.7, z], null, [0.5, 0.15, 0.5], [0.75, 0.15, 0.2], 0.1);
      P(m, BOX, [x + 1.6, 1.0, z - sd * 2.9], null, [1.1, 1.8, 0.05], [0.65, 0.18, 0.2]);
    });
    // шабандоздар
    sim.riders.forEach((r, i) => {
      const k = COL[KEYS[i]], ang = Math.atan2(-r.hy, r.hx);
      const mm = G3.mul(G3.T(r.x, 0, r.y - 50), G3.RY(ang));
      const mh = horse3d(mm, k, phases[i]);
      rider3d(mh, k, "jigit", phases[i], 0, 0, r.whip > 0);
      if (i === 0) { P(mh, CONE, [0.0, 3.25 + Math.sin(t * 4) * 0.1, 0], [0, 0, 3.1416], [0.18, 0.35, 0.18], [0.97, 0.78, 0.2], 0.6); }
      if (sim.holder === i) {   // серке шабандоздың қолында
        P(mh, SPH, [0.35, 1.55, 0.62], [0.3, 0, 0.2], [0.55, 0.22, 0.24], [0.42, 0.28, 0.16], 0.1);
        P(mh, SPH, [0.0, 1.62, 0.6], null, [0.2, 0.14, 0.14], [0.36, 0.24, 0.13], 0.1);
      }
    });
    if (sim.holder < 0) {   // серке жерде
      P(m, SPH, [sim.sx, 0.22, sim.sy - 50], null, [0.6, 0.24, 0.28], [0.42, 0.28, 0.16], 0.1);
      P(m, SPH, [sim.sx - 0.5, 0.25, sim.sy - 50 + 0.1], null, [0.2, 0.16, 0.16], [0.36, 0.24, 0.13], 0.1);
      P(m, CONE, [sim.sx, 2.4 + Math.sin(t * 3) * 0.15, sim.sy - 50], [0, 0, 3.1416], [0.3, 0.5, 0.3], [0.98, 0.84, 0.25], 0.5);
    }
  }

  function minimap(ctx, sim, x0, y0, w) {
    const h = w / 2;
    ctx.save(); ctx.globalAlpha = 0.88; ctx.fillStyle = "#3f6b2a"; ctx.fillRect(x0, y0, w, h);
    ctx.strokeStyle = "#fff"; ctx.lineWidth = 1; ctx.strokeRect(x0, y0, w, h);
    ctx.beginPath(); ctx.moveTo(x0 + w / 2, y0); ctx.lineTo(x0 + w / 2, y0 + h); ctx.stroke();
    K.TARGET.forEach(([x, y], ti) => { ctx.fillStyle = ti === 0 ? "#c0392b" : "#2e86de"; ctx.beginPath(); ctx.arc(x0 + x / 200 * w, y0 + y / 100 * h, 4, 0, 7); ctx.fill(); });
    sim.riders.forEach((r, i) => { ctx.fillStyle = r.t === 0 ? "#5dade2" : "#e74c3c"; ctx.beginPath(); ctx.arc(x0 + r.x / 200 * w, y0 + r.y / 100 * h, i === 0 ? 4 : 3, 0, 7); ctx.fill();
      if (i === 0) { ctx.strokeStyle = "#f5c542"; ctx.lineWidth = 2; ctx.stroke(); } });
    ctx.fillStyle = "#f5c542"; ctx.fillRect(x0 + sim.sx / 200 * w - 2.5, y0 + sim.sy / 100 * h - 2.5, 5, 5);
    ctx.restore();
  }

  function render(sim, t, phases) {
    const me = sim.riders[0], cx = Math.min(165, Math.max(35, me.x * 0.75 + sim.sx * 0.25));
    const bob = Math.sin(phases[0] * 2) * 0.09 * Math.min(1, me.v / 8) + Math.abs(Math.sin(phases[0])) * 0.04;
    if (V3) {
      const list = G3.record(() => fieldScene(sim, t, phases));
      const fz = Math.min(30, Math.max(-30, me.y - 50));
      view3d(cs, V3.s, 600, 300, [cx, 12, fz + 36], [cx, 0.5, fz - 2], 0.62, list, cx * 3);
      V3.lab.clearRect(0, 0, 600, 300);
      minimap(V3.lab, sim, 600 - 168, 8, 160);
      const p = [me.x, 0, me.y - 50];
      view3d(cf, V3.f, 360, 300, [p[0] + me.hx * 7.2 - me.hy * 1.2, 2.2 + bob, p[2] + me.hy * 7.2 + me.hx * 1.2], [p[0], 1.5, p[2]], 0.8, list, me.x * 4);
      view3d(cr, V3.r, 360, 300, [p[0] - me.hx * 6.6, 3.0 + bob, p[2] - me.hy * 6.6], [p[0] + me.hx * 14, 1.1, p[2] + me.hy * 14], 0.8, list, me.x * 4);
    } else {
      [[cs, 600, 0, 200], [cf, 360, me.x - 30, 60], [cr, 360, me.x - 30, 60]].forEach(([c, w, x0, span]) => {
        c.fillStyle = "#6f8f3a"; c.fillRect(0, 0, w, 300);
        const sc = w / span, oy = 150 - (span === 200 ? 50 : me.y) * sc;
        c.save(); c.translate(-x0 * sc, oy);
        c.strokeStyle = "#fff"; c.strokeRect(0, 0, 200 * sc, 100 * sc);
        K.TARGET.forEach(([x, y], ti) => { c.fillStyle = ti === 0 ? "#c0392b" : "#2e86de"; c.beginPath(); c.arc(x * sc, y * sc, K.KR * sc, 0, 7); c.fill(); });
        sim.riders.forEach((r, i) => { c.fillStyle = r.t === 0 ? "#5dade2" : "#e74c3c"; c.beginPath(); c.arc(r.x * sc, r.y * sc, Math.max(3, 1.2 * sc), 0, 7); c.fill(); });
        c.fillStyle = "#f5c542"; c.beginPath(); c.arc(sim.sx * sc, sim.sy * sc, Math.max(3, 0.8 * sc), 0, 7); c.fill(); c.restore(); });
    }
    $("ls").textContent = L().side || ""; $("lf").textContent = L().front || ""; $("lr").textContent = L().rear || "";
  }

  function fmtT(sim) {
    const per = sim.periodSteps, n = sim.n, total = per * sim.periods;
    if (sim.golden) return "⚡ " + Math.max(0, Math.ceil((total + K.GOLDEN - n) * K.DT)) + " с";
    const pi = Math.min(sim.periods, Math.floor(n / per) + 1), left = Math.max(0, (per * pi - n) * K.DT);
    return pi + "/" + sim.periods + " · " + Math.floor(left / 60) + ":" + String(Math.floor(left % 60)).padStart(2, "0");
  }

  function hud(sim) {
    const me = sim.riders[0], pct = Math.max(0, Math.min(100, me.s / me.smax * 100));
    const st = sim.holder === 0 ? (L().youHave || "") : sim.holder < 0 ? (L().onGround || "") : (sim.riders[sim.holder].t === 0 ? (L().mateHas || "") : (L().oppHas || ""));
    $("hud").innerHTML = `<div>${L().score || ""}<b>${sim.score[0]} : ${sim.score[1]}</b></div><div>${L().time || ""}<b>${fmtT(sim)}</b></div>
      <div>${L().speed || ""}<b>${(me.v * 3.6).toFixed(0)} ${L().kmh || ""}</b></div>
      <div>${L().stamina || ""}<b>${Math.round(me.s)}</b><div class="meter"><i style="width:${pct}%"></i></div></div><div>${L().serke || ""}<b class="small">${st}</b></div>`;
  }

  // ---- басқару
  function controls() {
    const c = $("ctrl");
    if (mode === "ready") { c.innerHTML = `<button class="go" id="go">▶ ${L().start || "Start"}</button>`; $("go").onclick = start; }
    else if (mode === "run") {
      c.innerHTML = `<div id="joy"><div id="knob"></div></div><div class="btns"><button id="bg">🤲 ${L().grab || ""}</button>
        <button id="bp">💪 ${L().pull || ""}</button><button id="bw">🏇 ${L().whip || ""}</button></div>`;
      const pad = $("joy"), knob = $("knob");
      const upd = (ev) => { const r = pad.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
        let dx = (ev.clientX - cx) / (r.width / 2), dy = (ev.clientY - cy) / (r.height / 2); const l = Math.hypot(dx, dy);
        if (l > 1) { dx /= l; dy /= l; } joy = { x: dx, y: dy, on: l > 0.25 }; knob.style.transform = `translate(${dx * 40}px, ${dy * 40}px)`; };
      pad.addEventListener("pointerdown", (e) => { pad.setPointerCapture(e.pointerId); upd(e); });
      pad.addEventListener("pointermove", (e) => { if (e.buttons || e.pointerType === "touch") upd(e); });
      const end = () => { joy = { x: 0, y: 0, on: false }; knob.style.transform = ""; };
      pad.addEventListener("pointerup", end); pad.addEventListener("pointercancel", end);
      [["bg", "g"], ["bp", "p"], ["bw", "w"]].forEach(([id, k]) => $(id).addEventListener("pointerdown", (e) => { e.preventDefault(); act(k); }));
    } else c.innerHTML = "";
    setH();
  }
  document.addEventListener("keydown", (e) => { keys[e.code] = true;
    if (mode !== "run") return;
    if (e.code === "Space") { e.preventDefault(); act("w"); }
    if (e.code === "KeyE" || e.code === "Enter") { e.preventDefault(); act(run && run.sim.holder >= 0 && run.sim.riders[run.sim.holder].t !== 0 ? "p" : "g"); }
    if (e.code === "KeyQ") { e.preventDefault(); act("p"); } });
  document.addEventListener("keyup", (e) => { keys[e.code] = false; });

  function act(k) { if (run && !run.done) run.queue.push(k); }

  function keyDir() {
    let x = 0, y = 0;
    if (keys.KeyA || keys.ArrowLeft) x -= 1; if (keys.KeyD || keys.ArrowRight) x += 1;
    if (keys.KeyW || keys.ArrowUp) y -= 1; if (keys.KeyS || keys.ArrowDown) y += 1;
    return [x, y];
  }

  function start() {
    const s = args.state, me = args.me;
    const sim = new K.Sim(s.stats[me], s.level, s.periods, s.period_s, s.ai_stats);
    run = { sim, inputs: [], queue: [], lastDir: [0, 0], t0: performance.now() + 3000, done: false, phases: [0, 0, 0, 0, 0, 0], flash: "", flashT: 0, ev0: 0 };
    mode = "run"; controls();
  }

  function stepRun(now) {
    const r = run, sim = r.sim, t = (now - r.t0) / 1000;
    if (t < 0) { $("big").textContent = Math.ceil(-t); render(sim, now / 1000, r.phases); hud(sim); return; }
    const target = Math.floor(t / K.DT), lim = sim.periodSteps * sim.periods + K.GOLDEN + 5;
    let guard = 0;
    while (!r.done && sim.n < target && guard < 12) {
      const n = sim.n, ev = [];
      // бағыт: джойстик немесе пернетақта (экран: оңға = +x, төмен = +y алаңда)
      let [dx, dy] = keyDir(); if (joy.on) { dx = joy.x; dy = joy.y; }
      let d = [0, 0]; const l = Math.hypot(dx, dy);
      if (l > 0.2) d = [Math.round(dx / l * 1000) / 1000, Math.round(dy / l * 1000) / 1000];
      const ch = Math.abs(d[0] - r.lastDir[0]) + Math.abs(d[1] - r.lastDir[1]);
      if (ch > 0.05) { ev.push([n, "d", d]); r.lastDir = d; }
      const seenK = {};
      while (r.queue.length) { const k = r.queue.shift(); if (!seenK[k]) { ev.push([n, k, null]); seenK[k] = 1; } }
      ev.forEach((e) => r.inputs.push(e));
      sim.step(ev);
      sim.riders.forEach((rr, i) => { r.phases[i] += rr.v * K.DT * 0.62; });
      if (sim.over || sim.n >= lim) r.done = true;
      guard++;
    }
    // оқиғалар (гол, тартыс)
    while (r.ev0 < sim.events.length) { const e = sim.events[r.ev0++]; const lab = { goal: L().goal, steal: L().steal, keep: L().keep, foul: L().foul, grab: L().grabbed, duel: L().duel }[e[1]];
      if (lab) { r.flash = (e[1] === "goal" ? (sim.riders[e[2]] && e[2] < 3 ? "🎉 " : "😬 ") : "") + lab; r.flashT = now; } }
    const du = sim.duel;
    if (du && (du[0] === 0 || du[1] === 0)) $("big").innerHTML = `💪 ${L().pullNow || ""}<br><small>${du[0] === 0 ? du[3] : du[4]} : ${du[0] === 0 ? du[4] : du[3]}</small>`;
    else $("big").textContent = now - r.flashT < 1600 ? r.flash : "";
    render(sim, now / 1000, r.phases); hud(sim);
    if (r.done && !pending) {
      pending = true; mode = "wait"; controls();
      $("big").textContent = "🏁 " + sim.score[0] + " : " + sim.score[1];
      send("streamlit:setComponentValue", { value: { inputs: r.inputs, nonce: Date.now() + Math.random() }, dataType: "json" });
    }
  }

  let idleSim = null;
  function frame(now) {
    requestAnimationFrame(frame);
    if (!args) return;
    if (mode === "run" && run) { stepRun(now); return; }
    if (!idleSim) { const s = args.state, me = args.me == null ? 0 : args.me;
      idleSim = new K.Sim(s.stats[me], s.level, s.periods, s.period_s, s.ai_stats); }
    const t = now / 1000; render(idleSim, t, [t * 2, t * 2 + 1, t * 2 + 2, t * 2 + 3, t * 2 + 4, t * 2 + 5]); hud(idleSim);
  }

  function bar() {
    const a = args, s = a.state, rd = s.rides || [null, null];
    const res = (p) => rd[p] ? `${rd[p].gf} : ${rd[p].ga}` : (s.turn === p && !s.over ? "🐎 …" : "—");
    $("bar").innerHTML = s.solo
      ? `<span class="pl">🟦 ${a.names[a.me == null ? 0 : a.me]}</span><span class="res">${rd.find((x) => x) ? res(rd[0] ? 0 : 1) : "—"}</span><span class="pl">${a.ai_name || ""} 🟥</span>`
      : `<span class="pl">⚪ ${a.names[0]}</span><span class="res">${res(0)}</span><span class="res">${res(1)}</span><span class="pl">${a.names[1]} ⚫</span>`;
    $("msg").textContent = a.message || "";
  }

  function decide() {
    const s = args.state;
    if (args.clickable && !s.over && !pending) { if (mode !== "run") { mode = "ready"; run = null; } }
    else if (mode !== "run" || !args.clickable) mode = "idle";
    controls();
  }

  window.addEventListener("message", (ev) => {
    const d = ev.data;
    if (!d || d.type !== "streamlit:render") return;
    const prev = args; args = d.args;
    if (!prev || prev.state.turn !== args.state.turn || (prev.state.last || {}).id !== (args.state.last || {}).id) { pending = false; if (mode === "wait") mode = "idle"; idleSim = null; }
    bar(); first = false; decide(); setH();
  });
  window.addEventListener("resize", () => args && setH());
  requestAnimationFrame(frame);
  send("streamlit:componentReady", { apiVersion: 1 });
  // ================= KOKPAR UI соңы =================
