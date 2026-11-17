  // ================= AUDARYSPAK UI =================
  const send = (type, data) => window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type }, data), "*");
  const $ = (id) => document.getElementById(id);
  const cs = $("cs").getContext("2d"), cf = $("cf").getContext("2d"), cr = $("cr").getContext("2d");
  const L = () => (args && args.labels) || {};
  const setH = () => send("streamlit:setFrameHeight", { height: Math.ceil($("wrap").getBoundingClientRect().height + 8) });
  let args = null, mode = "idle", run = null, pending = false, joy = { x: 0, y: 0, on: false }, keys = {};

  const COL = {
    me: { horse: ["#a0612f", "#7a4621", "#4e2b13"], mane: "#1c0f07", hoof: "#2a1a10", blaze: "#f3ece0",
          robe: "#1d5a8e", robe2: "#123449", dress: "#f2efe8", trim: "#e3b23c", hat: "#7a1b26", fur: "#3b2a1c", tokym: "#1f6f8b", skin: "#d8a578", hair: "#140c08" },
    op: { horse: ["#2e2a28", "#1d1a18", "#111"], mane: "#0b0b0b", hoof: "#222", blaze: "#efe8dc",
          robe: "#a51d2a", robe2: "#6e0c1b", dress: "#f2efe8", trim: "#e3b23c", hat: "#2a2a2a", fur: "#2f2318", tokym: "#8e1b2c", skin: "#d8a578", hair: "#140c08" },
  };

  __GL3D__

  const V3 = setup3d();
  const ACT_NAME = () => ({ pull: L().pull, push: L().push, twist: L().twist });

  // ---- шабандоздардың көріністегі орны мен бағыты
  function poses(sim, t, fall) {
    const a = sim.p[0], b = sim.p[1];
    if (sim.grip) {
      const mx = (a.x + b.x) / 2, mz = (a.y + b.y) / 2, th = t * 0.35, hx = Math.cos(th), hz = Math.sin(th);
      const px = -hz, pz = hx;   // оң жақ (+z) векторы
      return [{ x: mx - px * 0.8, z: mz - pz * 0.8, hx, hz, side: 1 }, { x: mx + px * 0.8, z: mz + pz * 0.8, hx, hz, side: -1 }];
    }
    const dx = b.x - a.x, dz = b.y - a.y, d = Math.hypot(dx, dz) || 1;
    return [{ x: a.x, z: a.y, hx: dx / d, hz: dz / d, side: 1 }, { x: b.x, z: b.y, hx: -dx / d, hz: -dz / d, side: 1 }];
  }

  function arenaScene(sim, t, phases, fall) {
    const { P, CYL, SPH, BOX, CONE, I4 } = G3, m = I4();
    P(m, BOX, [0, -0.05, 0], null, [300, 0.1, 300], [0.66, 0.66, 0.34]);
    P(m, CYL, [0, 0.01, 0], null, [A.ARENA, 0.02, A.ARENA], [0.78, 0.66, 0.45]);
    for (let k = 0; k < 36; k++) { const ang = k / 36 * 6.2832, x = Math.cos(ang) * A.ARENA, z = Math.sin(ang) * A.ARENA;
      P(m, CYL, [x, 0.5, z], null, [0.06, 1.0, 0.06], [0.42, 0.27, 0.14]);
      P(m, SPH, [x, 1.0, z], null, [0.09, 0.09, 0.09], k % 2 ? [0.75, 0.15, 0.2] : [0.95, 0.85, 0.3], 0.5); }
    for (let k = 0; k < 9; k++) { const ang = k / 9 * 6.2832 + 0.3, x = Math.cos(ang) * 34, z = Math.sin(ang) * 34;
      P(m, CYL, [x, 1.0, z], null, [3.2, 2.0, 3.2], [0.95, 0.93, 0.88], 0.02);
      P(m, CONE, [x, 2.8, z], null, [3.4, 1.6, 3.4], [0.92, 0.9, 0.84], 0.02);
      P(m, CYL, [x, 3.7, z], null, [0.5, 0.15, 0.5], [0.75, 0.15, 0.2], 0.1); }
    const ps = poses(sim, t, fall);
    ps.forEach((q, i) => {
      const r = sim.p[i], k = COL[i === 0 ? "me" : "op"], ang = Math.atan2(-q.hz, q.hx);
      const mm = G3.mul(G3.T(q.x, 0, q.z), G3.RY(ang));
      const ph = phases[i] + (sim.grip ? t * 3 : 0);
      const mh = horse3d(mm, k, ph);
      let lean = 0, side = q.side;
      if (sim.grip) {
        lean = 0.18 + (1 - r.b / r.bmax) * 0.55;
        if (r.wind > 0) lean += r.act === "pull" ? -0.12 : r.act === "push" ? 0.22 : 0.12;
        if (r.hold === 1) lean *= 0.5;
      }
      if (fall && fall.who === i) { const f = Math.min(1, fall.t / 1.2); lean = 0.4 + f * 1.25; side = q.side * (sim.grip ? -1 : 1); }
      rider3d(mh, k, "jigit", ph, Math.max(0, lean), side, false);
      if (i === 0) P(mh, CONE, [0.0, 3.25 + Math.sin(t * 4) * 0.1, 0], [0, 0, 3.1416], [0.18, 0.35, 0.18], [0.97, 0.78, 0.2], 0.6);
      if (!sim.grip && r.dx * r.dx + r.dy * r.dy > 0.01) for (let d = 0; d < 3; d++) {   // шаң
        const f = ((t * 2 + d * 0.33 + i * 0.5) % 1); P(m, SPH, [q.x - q.hx * (0.8 + f * 1.2), 0.15 + f * 0.4, q.z - q.hz * (0.8 + f * 1.2)], null, [0.25 + f * 0.4, 0.2 + f * 0.3, 0.25 + f * 0.4], [0.8, 0.7, 0.55], 0, 0.45 * (1 - f)); }
    });
    return ps;
  }

  function render(sim, t, phases, fall) {
    const list = G3.record(() => { G3.__ps = arenaScene(sim, t, phases, fall); });
    const ps = G3.__ps, me = ps[0], op = ps[1];
    const bob = Math.sin(phases[0] * 2) * 0.06 + (sim.grip ? Math.sin(t * 9) * (1 - sim.p[0].b / sim.p[0].bmax) * 0.08 : 0);
    if (V3) {
      const mx = (me.x + op.x) / 2, mz = (me.z + op.z) / 2, ax = op.x - me.x, az = op.z - me.z, al = Math.hypot(ax, az) || 1;
      let nx = -az / al, nz = ax / al; if (sim.grip) { nx = me.hx; nz = me.hz; }
      const sd = sim.grip ? 9 : Math.max(10, al * 0.8 + 6);
      view3d(cs, V3.s, 600, 300, [mx + nx * sd, 3.2, mz + nz * sd], [mx, 1.6, mz], 0.62, list, mx * 6);
      V3.lab.clearRect(0, 0, 600, 300);
      // алдынан: ойыншының бетіне
      view3d(cf, V3.f, 360, 300, [me.x + me.hx * 5.2 + (sim.grip ? -me.hz * 1.4 : 0), 2.3 + bob, me.z + me.hz * 5.2 + (sim.grip ? me.hx * 1.4 : 0)], [me.x, 2.0, me.z], 0.8, list, me.x * 4);
      // артынан: иықтың үстінен қарсыласқа
      const tx = sim.grip ? op.x : op.x, tz = sim.grip ? op.z : op.z;
      const bx = me.x - (sim.grip ? me.hx * 4.5 + (op.x - me.x) * 0.9 : ax / al * 5.5), bz = me.z - (sim.grip ? me.hz * 4.5 + (op.z - me.z) * 0.9 : az / al * 5.5);
      view3d(cr, V3.r, 360, 300, [bx, 3.0 + bob, bz], [tx, 1.8, tz], 0.8, list, me.x * 4);
    } else {
      [cs, cf, cr].forEach((c, k) => { const w = k ? 360 : 600; c.fillStyle = "#c7a46a"; c.fillRect(0, 0, w, 300);
        const sc = 300 / 44; c.save(); c.translate(w / 2, 150); c.strokeStyle = "#7a4419"; c.beginPath(); c.arc(0, 0, A.ARENA * sc, 0, 7); c.stroke();
        sim.p.forEach((r, i) => { c.fillStyle = i ? "#c0392b" : "#2e86de"; c.beginPath(); c.arc(r.x * sc, r.y * sc, 10, 0, 7); c.fill(); }); c.restore(); });
    }
    $("ls").textContent = L().side || ""; $("lf").textContent = L().front || ""; $("lr").textContent = L().rear || "";
  }

  function hud(sim) {
    const me = sim.p[0], op = sim.p[1], left = Math.max(0, (sim.roundSteps - sim.rn) * A.DT);
    const bar = (v, mx, c) => `<div class="meter"><i style="width:${Math.max(0, Math.min(100, v / mx * 100))}%;background:${c}"></i></div>`;
    const warn = op.wind > 0 ? `⚠ ${ACT_NAME()[op.act] || ""}!` : (sim.grip ? (L().gripOn || "") : (L().approach || ""));
    $("hud").innerHTML = `<div>${L().rounds || ""}<b>${sim.rounds[0]} : ${sim.rounds[1]}</b><small>${L().round || ""} ${sim.round}/3 · ${Math.ceil(left)} с</small></div>
      <div>${L().myBal || ""}<b>${Math.round(me.b)}</b>${bar(me.b, me.bmax, "#2e86de")}</div>
      <div>${L().opBal || ""}<b>${Math.round(op.b)}</b>${bar(op.b, op.bmax, "#c0392b")}</div>
      <div>${L().stamina || ""}<b>${Math.round(me.s)}</b>${bar(me.s, me.smax, "linear-gradient(90deg,#e74c3c,#f1c40f,#2ecc71)")}</div>
      <div class="${op.wind > 0 ? "alert" : ""}">${L().state || ""}<b class="small">${warn}</b></div>`;
  }

  // ---- басқару
  function controls() {
    const c = $("ctrl");
    if (mode === "ready") { c.innerHTML = `<button class="go" id="go">▶ ${L().start || "Start"}</button>`; $("go").onclick = start; }
    else if (mode === "run") {
      c.innerHTML = `<div id="joy"><div id="knob"></div></div><div class="btns">
        <button id="b_pull">⬅ ${L().pull}</button><button id="b_push">${L().push} ➡</button>
        <button id="b_twist">🔄 ${L().twist}</button><button id="b_hold" class="hold">🛡 ${L().hold}</button>
        <button id="b_x" class="x">🐎 ${L().free}</button></div>`;
      const pad = $("joy"), knob = $("knob");
      const upd = (ev) => { const r = pad.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
        let dx = (ev.clientX - cx) / (r.width / 2), dy = (ev.clientY - cy) / (r.height / 2); const l = Math.hypot(dx, dy);
        if (l > 1) { dx /= l; dy /= l; } joy = { x: dx, y: dy, on: l > 0.25 }; knob.style.transform = `translate(${dx * 34}px, ${dy * 34}px)`; };
      pad.addEventListener("pointerdown", (e) => { pad.setPointerCapture(e.pointerId); upd(e); });
      pad.addEventListener("pointermove", (e) => { if (e.buttons || e.pointerType === "touch") upd(e); });
      const end = () => { joy = { x: 0, y: 0, on: false }; knob.style.transform = ""; };
      pad.addEventListener("pointerup", end); pad.addEventListener("pointercancel", end);
      [["b_pull", "pull"], ["b_push", "push"], ["b_twist", "twist"]].forEach(([id, a]) => $(id).addEventListener("pointerdown", (e) => { e.preventDefault(); act(["a", a]); }));
      $("b_x").addEventListener("pointerdown", (e) => { e.preventDefault(); act(["x", null]); });
      const hb = $("b_hold");
      hb.addEventListener("pointerdown", (e) => { e.preventDefault(); hb.setPointerCapture(e.pointerId); act(["h", 1]); });
      ["pointerup", "pointercancel"].forEach((t) => hb.addEventListener(t, () => act(["h", 0])));
    } else c.innerHTML = "";
    setH();
  }
  document.addEventListener("keydown", (e) => { if (keys[e.code]) return; keys[e.code] = true; if (mode !== "run") return;
    const map = { KeyJ: ["a", "pull"], KeyK: ["a", "push"], KeyL: ["a", "twist"], KeyQ: ["a", "twist"], KeyE: ["a", "twist"], KeyX: ["x", null] };
    if (map[e.code]) { e.preventDefault(); act(map[e.code]); }
    if (e.code === "Space") { e.preventDefault(); act(["h", 1]); } });
  document.addEventListener("keyup", (e) => { keys[e.code] = false; if (mode === "run" && e.code === "Space") act(["h", 0]); });

  function act(a) { if (run && !run.done) run.queue.push(a); }
  function keyDir() { let x = 0, y = 0;
    if (keys.KeyA || keys.ArrowLeft) x -= 1; if (keys.KeyD || keys.ArrowRight) x += 1;
    if (keys.KeyW || keys.ArrowUp) y -= 1; if (keys.KeyS || keys.ArrowDown) y += 1; return [x, y]; }

  function start() {
    const s = args.state, me = args.me;
    const sim = new A.Sim(s.stats[me], s.level, s.round_s, s.ai_stats);
    run = { sim, inputs: [], queue: [], lastDir: [0, 0], t0: performance.now() + 3000, done: false, phases: [0, 0], ev0: 0, flash: "", flashT: 0, fall: null };
    mode = "run"; controls();
  }

  function stepRun(now) {
    const r = run, sim = r.sim, t = (now - r.t0) / 1000;
    if (t < 0) { $("big").textContent = Math.ceil(-t); render(sim, now / 1000, r.phases, null); hud(sim); return; }
    if (r.pause && now < r.pause) { if (r.fall) r.fall.t = (now - r.fallStart) / 1000; render(r.frozen || sim, now / 1000, r.phases, r.fall); return; }
    if (r.pause) { r.t0 += now - r.pauseFrom; r.pause = 0; r.fall = null; r.frozen = null; }
    const target = Math.floor(((now - r.t0) / 1000) / A.DT), lim = sim.roundSteps * 3 + 10;
    let guard = 0;
    while (!r.done && sim.n < target && guard < 12) {
      const n = sim.n, ev = [];
      let [dx, dy] = keyDir(); if (joy.on) { dx = joy.x; dy = joy.y; }
      let d = [0, 0]; const l = Math.hypot(dx, dy);
      if (l > 0.2) d = [Math.round(dx / l * 1000) / 1000, Math.round(dy / l * 1000) / 1000];
      if (Math.abs(d[0] - r.lastDir[0]) + Math.abs(d[1] - r.lastDir[1]) > 0.05) { ev.push([n, "d", d]); r.lastDir = d; }
      while (r.queue.length) { const q = r.queue.shift(); ev.push([n, q[0], q[1]]); }
      ev.forEach((e) => r.inputs.push(e));
      const before = JSON.parse(JSON.stringify(sim.p)), wasGrip = sim.grip;
      sim.step(ev);
      sim.p.forEach((pp, i) => { r.phases[i] += (sim.grip ? 0.02 : 0.25); });
      if (sim.over || sim.n >= lim) r.done = true;
      guard++;
      // раунд аяқталды — құлау анимациясы
      if (sim.lastRound && sim.lastRound.n === n) {
        const fallEv = sim.events.filter((e) => e[0] === n && e[1] === "fall")[0];
        const frozen = { p: before, grip: wasGrip, rounds: sim.rounds.slice(), round: sim.round, roundSteps: sim.roundSteps, rn: sim.roundSteps, sx: 0 };
        r.fall = fallEv ? { who: fallEv[2], t: 0 } : null; r.frozen = fallEv ? frozen : null;
        r.fallStart = now; r.pauseFrom = now; r.pause = now + 2200;
        const w = sim.lastRound.winner;
        r.flash = w === 0 ? "🏆 " + (L().roundWon || "") : w === 1 ? "😣 " + (L().roundLost || "") : "🤝 " + (L().roundDraw || ""); r.flashT = now;
        break;
      }
    }
    while (r.ev0 < sim.events.length) { const e = sim.events[r.ev0++];
      const lab = { counter: L().counter, grip: L().gripOn, free: L().freed, warn: L().warnOut }[e[1]];
      if (lab && !(e[1] === "counter" && e[2] !== 0)) { r.flash = lab; r.flashT = now; }
      if ((e[1] === "pull" || e[1] === "push" || e[1] === "twist") && e[2] === 0) { r.flash = "💥 " + ACT_NAME()[e[1]]; r.flashT = now; } }
    $("big").textContent = now - r.flashT < 1300 ? r.flash : "";
    render(r.fall && r.frozen ? r.frozen : sim, now / 1000, r.phases, r.fall); hud(sim);
    if (r.done && !r.pause && !pending) {
      pending = true; mode = "wait"; controls();
      $("big").textContent = "🏁 " + sim.rounds[0] + " : " + sim.rounds[1];
      send("streamlit:setComponentValue", { value: { inputs: r.inputs, nonce: Date.now() + Math.random() }, dataType: "json" });
    }
  }

  let idleSim = null;
  function frame(now) {
    requestAnimationFrame(frame);
    if (!args) return;
    if (mode === "run" && run) { stepRun(now); return; }
    if (!idleSim) { const s = args.state, me = args.me == null ? 0 : args.me; idleSim = new A.Sim(s.stats[me], s.level, s.round_s, s.ai_stats); }
    const t = now / 1000; render(idleSim, t, [t * 1.5, t * 1.5 + 1], null); hud(idleSim);
  }

  function bar() {
    const a = args, s = a.state, rd = s.rides || [null, null];
    const res = (p) => rd[p] ? `${rd[p].rw} : ${rd[p].rl}` : (s.turn === p && !s.over ? "🐎 …" : "—");
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
    bar(); decide(); setH();
  });
  window.addEventListener("resize", () => args && setH());
  requestAnimationFrame(frame);
  send("streamlit:componentReady", { apiVersion: 1 });
  // ================= AUDARYSPAK UI соңы =================
