  // ================= HANTALAPAY UI =================
  const send = (type, data) => window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type }, data), "*");
  const $ = (id) => document.getElementById(id);
  const cs = $("cs").getContext("2d"), cf = $("cf").getContext("2d"), cr = $("cr").getContext("2d");
  const L = () => (args && args.labels) || {};
  const setH = () => send("streamlit:setFrameHeight", { height: Math.ceil($("wrap").getBoundingClientRect().height + 8) });
  let args = null, mode = "idle", run = null, pending = false, keys = {};

  __GL3D__
  // асықтың 8 суреті (1 алшы, 2 тәйке, 3 бүк, 4 шік, 5–6 алшы үстінен, 7 омпы, 8 шоңқай) — бір атлас
  const ATL = new Image(); ATL.src = "data:image/webp;base64,__ATLAS__"; G3.setAtlas(ATL, 8);

  const V3 = setup3d();
  const clamp01 = (x) => Math.max(0, Math.min(1, x)), ease = (x) => x * x * (3 - 2 * x);
  const hexc = (h) => { const n = parseInt(h.slice(1), 16); return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255]; };
  const SIDE = () => [L().alshy || "Алшы", L().taike || "Тәйке", L().buk || "Бүк", L().shik || "Шік", L().ompy || "Омпы", L().shonkai || "Шоңқай"];

  // ---- балалар: ұлттық киім (ұлдар — көк камзол, қыздар — қызыл камзол, ақ көйлек, тақия)
  const BOY = (o) => Object.assign({ jacket: "#f7f5ef", jacket2: "#e8e4da", trim: "#d9a520", belt: null, pants: "#1b2f57", boot: "#1b1612",
    vest: "#1c3f7a", cap: "#1c3f7a", gold: "#d9a520", skin: "#e0aa82", skin2: "#c98f68", hair: "#1a120d", lip: "#b5655a", S: 0.94, head: 1.16 }, o || {});
  const GIRL = (o) => Object.assign({ jacket: "#f7f5ef", jacket2: "#e8e4da", trim: "#d9a520", belt: null, pants: "#f2efe8", boot: "#3a1f14",
    vest: "#b3202e", skirt: "#f7f5ef", cap: "#b3202e", gold: "#d9a520", braids: true, uki: true, ribbon: "#b3202e",
    skin: "#e6b38e", skin2: "#cf9a75", hair: "#20140d", lip: "#c06a62", S: 0.92, head: 1.16 }, o || {});
  const KIDS = [BOY(), GIRL(), BOY({ skin: "#d39c74", skin2: "#bb875f", vest: "#16336a", cap: "#16336a" }), GIRL({ vest: "#9e1b2a", cap: "#9e1b2a", skin: "#dba984" }),
    BOY({ vest: "#24508f", cap: "#24508f", skin: "#e4b18c" }), GIRL({ skin: "#d8a07a", vest: "#c0392b", cap: "#c0392b" }), BOY({ vest: "#1d3a6e", cap: "#1d3a6e", skin: "#cf9670" })];
  const CHIP = ["#2e86de", "#e74c3c", "#27ae60", "#8e44ad", "#e67e22", "#16a085", "#d6336c"];

  const BEND = { hip: [-0.06, 0.84, 0], pel: 0.42, pitch: 0.5, roll: 0, yaw: 0, hp: -0.75, hy: 0, hr: 0,
    feet: [[0.0, 0.08, 0.2], [0.05, 0.08, -0.2]], hands: [[0.22, 0.52, 0.17], [0.22, 0.52, -0.17]], toe: [0, 0] };
  const CROUCH = { hip: [-0.08, 0.5, 0], pel: 0.55, pitch: 0.5, roll: 0, yaw: 0, hp: -0.55, hy: 0, hr: 0,
    feet: [[0.14, 0.08, 0.24], [-0.04, 0.08, -0.24]], hands: [[0.3, 0.45, 0.2], [0.2, 0.8, -0.18]], toe: [0, 0], kp: [1, 1.4] };
  const KNEEL = { hip: [-0.05, 0.5, 0], pel: 0.4, pitch: 0.75, roll: 0, yaw: 0, hp: -0.6, hy: 0, hr: 0,
    feet: [[0.28, 0.08, 0.2], [-0.38, 0.06, -0.18]], hands: [[0.45, 0.3, 0.2], [0.5, 0.12, -0.1]], toe: [0, 0] };
  const WIN = { hip: [0, 0.9, 0], pel: 0, pitch: -0.05, roll: 0, yaw: 0, hp: -0.25, hy: 0, hr: 0,
    feet: [[0, 0.08, 0.18], [0.03, 0.08, -0.18]], hands: [[0.05, 2.0, 0.35], [0.05, 2.0, -0.35]], toe: [0, 0] };

  // ---- сахна: көгал, тақыр, киіз, киіз үй, қоршау, тау
  function stage(m, t) {
    const { P, BOX, CYL, CONE, SPH, seg } = G3;
    P(m, BOX, [0, -0.05, 0], null, [300, 0.1, 300], [0.42, 0.62, 0.25]);
    for (let k = 0; k < 60; k++) { const a = k * 2.399, r = 2.8 + (k * 37 % 90) / 10; P(m, SPH, [Math.cos(a) * r, 0.0, Math.sin(a) * r], null, [0.35, 0.06, 0.35], [0.36, 0.56, 0.2]); }
    P(m, CYL, [0, 0.0, 0], null, [2.3, 0.02, 2.3], [0.72, 0.6, 0.42], 0.02);            // тақыр
    P(m, CYL, [0, 0.015, 0], null, [1.0, 0.012, 1.0], [0.6, 0.15, 0.15], 0.05);         // киіз шеті
    P(m, CYL, [0, 0.02, 0], null, [0.92, 0.012, 0.92], [0.93, 0.87, 0.74], 0.03);        // киіз
    for (let k = 0; k < 16; k++) { const a = k / 16 * 6.2832; P(m, BOX, [Math.cos(a) * 0.82, 0.028, Math.sin(a) * 0.82], [0, -a + 0.785, 0], [0.07, 0.006, 0.07], [0.72, 0.2, 0.18], 0.1); }
    P(m, CYL, [0, 0.027, 0], null, [0.3, 0.004, 0.3], [0.2, 0.35, 0.6], 0.05);
    P(m, CYL, [0, 0.029, 0], null, [0.24, 0.004, 0.24], [0.93, 0.87, 0.74], 0.03);
    // киіз үй
    const yx = -5.5, yz = -7.5;
    P(m, CYL, [yx, 1.0, yz], null, [2.6, 2.0, 2.6], [0.96, 0.94, 0.9], 0.03);
    P(m, CYL, [yx, 1.5, yz], null, [2.62, 0.22, 2.62], [0.75, 0.15, 0.15], 0.1);
    P(m, CONE, [yx, 2.75, yz], null, [2.8, 1.5, 2.8], [0.95, 0.93, 0.88], 0.03);
    P(m, CYL, [yx, 3.45, yz], null, [0.45, 0.1, 0.45], [0.75, 0.15, 0.15], 0.1);
    P(m, BOX, [yx + 1.3, 0.75, yz + 2.25], [0, -0.52, 0], [0.9, 1.5, 0.08], [0.72, 0.22, 0.12], 0.1);
    // ағаш қоршау
    for (let k = 0; k < 14; k++) { const x = 1.5 + k * 0.9, z = -6.5 + k * 0.25;
      P(m, CYL, [x, 0.5, z], null, [0.06, 1.0, 0.06], [0.55, 0.38, 0.22]);
      if (k < 13) { seg(m, [x, 0.75, z], [x + 0.9, 0.75, z + 0.25], 0.035, [0.62, 0.44, 0.26], "CYL"); seg(m, [x, 0.4, z], [x + 0.9, 0.4, z + 0.25], 0.035, [0.62, 0.44, 0.26], "CYL"); } }
    // ағаштар
    [[-9, -11], [9, -12], [13, -6], [-13, -4], [4, -14]].forEach(([x, z], i) => {
      P(m, CYL, [x, 1.0, z], null, [0.18, 2.0, 0.18], [0.45, 0.3, 0.18]);
      P(m, SPH, [x, 2.6 + (i % 2) * 0.3, z], null, [1.4, 1.5, 1.4], [0.24, 0.48, 0.2], 0.05);
      P(m, SPH, [x + 0.5, 2.2, z + 0.4], null, [0.9, 1.0, 0.9], [0.28, 0.54, 0.22], 0.05); });
  }

  // асық: SDF-тен жасалған шынайы пішін (asyk_mesh.js), ойықтары көлеңкелі (AO)
  const BONE = [0.9, 0.79, 0.52], KH = [0.8, 0.13, 0.12], GOLD = [0.92, 0.72, 0.2], AU = 0.0175;
  // боялған асықтар (5-сурет): Хан — жалғыз қызыл, қалғандары әр түсті
  const PAINT = [[0.9, 0.79, 0.52], [0.86, 0.6, 0.12], [0.95, 0.8, 0.22], [0.33, 0.58, 0.2], [0.47, 0.52, 0.56],
    [0.92, 0.5, 0.12], [0.55, 0.33, 0.2], [0.93, 0.87, 0.72], [0.62, 0.62, 0.26], [0.4, 0.5, 0.48], [0.8, 0.66, 0.2]];
  function asyk3d(x, y, z, yaw, roll, pitch, col, sc) {
    const { P, mul, T, RY, RX, RZ } = G3, s = (sc || 1) * AU;
    const M = mul(mul(mul(mul(T(x, y, z), RY(yaw)), RZ(pitch || 0)), RX(roll)), G3.Sc(s, s, s));
    const c = col === true ? KH : (col || BONE);
    P(M, "ASYK", [0, 0, 0], null, [1, 1, 1], c, col === true ? 0.6 : (col && col !== BONE ? 0.5 : 0.3));
  }
  // қалыптар: 0 алшы, 1 тәйке, 2 бүк, 3 шік, 4 омпы, 5 шоңқай
  const ROLL = [Math.PI / 2, -Math.PI / 2, 0, Math.PI, 0, 0]   /* алшы −z, тәйке +z, бүк +y, шік −y жоғары */, PITCH = [0, 0, 0, 0, -Math.PI / 2, Math.PI / 2], FELT = 0.026, AS = 1.6;
  // 4 омпы — домалақ басы жоғары (7-сурет), 5 шоңқай — айыр басы жоғары (8-сурет)
  const LIFT = [0, 0, 0, 0, 0, 0], SZ = 0.092;   // асық суретінің өлшемі (м)
  const CELL = [0, 1, 2, 3, 6, 7];               // қалып → сурет нөмірі (0-ден)
  let SPR = [];
  function asykSpr(x, y, z, side, col, flip, rot, sc) { SPR.push({ x, y, z, side, tint: col === true ? KH : (col || BONE), flip, rot: rot || 0, sc: sc || 1 }); }
  function sprList(steep) { return SPR.map((a) => { const w = SZ * a.sc, c = (steep && a.side === 0) ? (a.flip ? 5 : 4) : CELL[a.side];
    return { p: [a.x, a.y + w * 0.42, a.z], w, h: w, cell: c, tint: a.tint, rot: a.rot, flip: a.flip }; }); }   // әр қырында жатқандағы биіктік

  // ---- ойын күйі (клиент)
  const seatW = (g, j, r) => [g.seats[j][0] * (r || 1.48), g.seats[j][1] * (r || 1.48)];   // көрініс үшін сәл кеңірек
  function mkScatter() {   // ойын басында асықтар ортада бей-берекет шашылып жатады
    const out = [];
    for (let i = 0; i < H.N_ASYK; i++) {
      let x, z, ok, tries = 0;
      do { const a = Math.random() * 6.2832, rr = Math.sqrt(Math.random()) * 0.32; x = Math.cos(a) * rr; z = Math.sin(a) * rr;
        ok = out.every((o) => (o.x - x) ** 2 + (o.z - z) ** 2 > 0.0045); tries++; } while (!ok && tries < 60);
      const u = Math.random(), side = u < 0.17 ? 0 : u < 0.34 ? 1 : u < 0.66 ? 2 : u < 0.97 ? 3 : u < 0.985 ? 4 : 5;
      out.push({ x, z, y: FELT, side, roll: ROLL[side], pitch: PITCH[side], yaw: Math.random() * 6.2832 });
    }
    return out;
  }
  function mkColors() { const p = PAINT.slice(); for (let i = p.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [p[i], p[j]] = [p[j], p[i]]; } return p; }
  function newRound(r) { r.ast = []; for (let i = 0; i < H.N_ASYK; i++) r.ast.push({ owner: -1, tOwn: 0 }); r.piles = new Array(r.g.n).fill(0); }

  function start() {
    const s = args.state, me = args.me;
    const g = new H.Game(s.stats[me], s.n_ai, s.level, s.target, s.seed, s.ai_stats);
    run = { g, inputs: [], phase: "draw", t0: performance.now(), done: false, out: null, taps: [], shout: null, falsePress: null, scatter: mkScatter(), cols: mkColors(),
      flickN: 0, flickRes: [], msg: "", shoutP: -1, endT: 0, lastTap: -1000 };
    newRound(run);
    window.__hRun = run; mode = "run"; controls();
  }
  const names = () => { const g = run ? run.g : null, n = g ? g.n : 4, out = [args.names[args.me == null ? 0 : args.me]];
    const kid = (L().kids || "Айдана,Нұрлан,Аружан,Ерасыл,Інжу,Дәулет").split(","); for (let j = 1; j < n; j++) out.push("🤖 " + kid[(j - 1) % kid.length]); return out; };

  function setPhase(p) { run.phase = p; run.t0 = performance.now(); controls(); }
  function nextThrow() {
    const r = run, g = r.g;
    g.endThrow();
    if (g.over) { setPhase("end"); r.endT = performance.now(); return; }
    const nw = performance.now();   // келесі шашуға дейін асықтар сол жатқан жерінен жиналады
    if (r.out) r.scatter = r.out.pos.map((p, i) => { const a = asykPos(i, nw); return { x: a[0], z: a[2], y: a[1], side: r.out.sides[i], roll: a[3], pitch: a[4], yaw: r.yaw[i] }; });
    r.out = null; r.taps = []; r.shout = null; r.falsePress = null; r.flickN = 0; r.flickRes = []; r.shoutP = -1; r.lastTap = -1000;
    newRound(r); setPhase("aim");
  }
  function doThrow(ms) {
    const r = run, g = r.g;
    if (ms != null) r.inputs.push([g.k, "p", ms]);
    r.out = g.throw(ms); r.yaw = r.out.pos.map((p, i) => (i * 1.7 + p[0] * 13.1 + p[1] * 7.3) % 6.2832);
    setPhase("fly");
  }
  // ағымдағы уақыттағы бөлу (алдын ала көрсету — ойын есебіне әсер етпейді)
  function preview() {
    const g = run.g, sv = g.scores.slice(), ne = g.events.length, so = Object.assign({}, g.out);
    g.talapai(run.taps, run.shout); const order = g.out.order, fs = g.out.shout;
    g.scores = sv; g.events.length = ne; g.out = so; return { order, fs };
  }
  function msNow() { return performance.now() - run.t0; }
  function grab(idx) {   // ойыншы асыққа ұмтылды
    const r = run; if (!r || mode !== "run") return;
    const ms = Math.round(msNow());
    if (r.phase === "talapai") {
      if (ms - r.lastTap < 110 || ms > H.GRAB_MS) return;
      const pv = preview(), taken = new Set(pv.order.filter((o) => o[0] <= ms).map((o) => o[2]));
      if (idx == null) { const g = r.g; let b = -1, bd = 0; for (let i = 0; i < H.N_ASYK; i++) if (!taken.has(i)) { const d = g.reach(0, i) + (i === H.KHAN ? -200 : 0); if (b < 0 || d < bd) { b = i; bd = d; } } idx = b; }
      if (idx < 0 || taken.has(idx)) return;
      r.taps.push([ms, idx]); r.inputs.push([r.g.k, "g", [ms, idx]]); r.lastTap = ms;
    } else if (r.phase === "watch" && r.falsePress == null) { r.falsePress = ms; r.inputs.push([r.g.k, "s", Math.max(0, ms)]); }
  }
  function shoutNow() {
    const r = run; if (!r || mode !== "run") return;
    const ms = Math.round(msNow());
    if (r.phase === "talapai" && r.shout == null) { r.shout = ms; r.inputs.push([r.g.k, "s", ms]); }
    else if (r.phase === "watch" && r.falsePress == null) { r.falsePress = ms; r.inputs.push([r.g.k, "s", Math.max(0, ms)]); }
  }
  function mainPress() {   // Space: шашу / сырту
    const r = run; if (!r || mode !== "run") return;
    const ms = Math.round(msNow());
    if (r.phase === "aim" && r.g.turn() === 0) doThrow(ms);
    else if (r.phase === "flick" && r.out.t === 0 && !r.flickAnim) doFlick(ms);
  }
  function doFlick(ms) {
    const r = run, g = r.g;
    if (ms != null) r.inputs.push([g.k, "f", ms]);
    const more = g.flick(ms); r.flickRes = g.out.flicks.slice(); r.flickAnim = performance.now(); r.flickMore = more;
    const last = r.flickRes[r.flickRes.length - 1];
    if (last) { last.forEach((i) => { r.ast[i].owner = g.out.t; r.ast[i].tOwn = performance.now() + 450; }); r.msg = "✅ " + (L().hit || "") + ` +${(last[0] === H.KHAN || last[1] === H.KHAN) ? 6 : 2}`; }
    else r.msg = "✖ " + (L().miss || "");
  }

  // ---- кадр сайын логика
  function tick(now) {
    const r = run, g = r.g, el = now - r.t0;
    if (r.phase === "draw") { r.msg = `🎲 ${L().drawLot || ""}: ${names()[g.first]}`; if (el > 1800) { newRound(r); setPhase("aim"); } return; }
    if (r.phase === "aim") {
      const t = g.turn();
      r.msg = t === 0 ? (L().yourThrow || "") : `${names()[t]} ${L().throws || ""}`;
      if (t !== 0 && el > 1100) doThrow(null);
      else if (t === 0 && el > 12000) { r.out = g.throw(null); r.yaw = r.out.pos.map((p, i) => (i * 1.7 + p[0] * 13.1 + p[1] * 7.3) % 6.2832); setPhase("fly"); }
      return;
    }
    if (r.phase === "fly") {
      if (el > 1050) {
        const k = r.out.khan; r.msg = `👑 ${L().khan || "Хан"}: ${SIDE()[k].toUpperCase()}!`;
        setPhase(k === 0 ? "talapai" : "watch");
      }
      return;
    }
    if (r.phase === "talapai") {
      const pv = preview(); r.pv = pv; r.shoutP = pv.fs;
      pv.order.forEach((o) => { const a = r.ast[o[2]]; if (o[0] <= el) { if (a.owner !== o[1]) { a.owner = o[1]; a.tOwn = now; } } else if (a.owner >= 0 && a.owner !== o[1]) a.owner = -1; });
      const allDone = pv.order.length === H.N_ASYK && pv.order.every((o) => o[0] <= el);
      if (el > H.GRAB_MS + 200 || (allDone && el > Math.max(...pv.order.map((o) => o[0])) + 700)) {
        const before = g.scores.slice(); g.talapai(r.taps, r.shout);
        g.out.owner.forEach((p, i) => { r.ast[i].owner = p; });
        r.msg = `📣 ${L().talapai || "ТАЛАПАЙ"}! ${names()[g.out.shout] || ""} +1 · ` + names().map((n, j) => g.scores[j] - before[j] ? `${n.replace("🤖 ", "")} +${g.scores[j] - before[j]}` : "").filter(Boolean).join(", ");
        setPhase("result");
      }
      return;
    }
    if (r.phase === "watch") {
      if (el > 1300) {
        const bad = g.falseStarts(r.falsePress != null);
        if (bad.length) r.msg = `⛔ ${L().falseStart || ""}: ` + bad.map((j) => names()[j].replace("🤖 ", "")).join(", ") + " −2";
        if (r.out.khan >= 4) {   // Хан тік тұрып қалды
          const pts = g.special(), t = r.out.t;
          if (r.out.khan === 4) for (let i = 0; i < H.N_ASYK; i++) { r.ast[i].owner = t; r.ast[i].tOwn = performance.now() + 300 + i * 60; }
          else { r.ast[H.KHAN].owner = t; r.ast[H.KHAN].tOwn = performance.now() + 300; }
          r.msg = `${r.out.khan === 4 ? "🌟" : "⭐"} ${SIDE()[r.out.khan].toUpperCase()}! ${names()[t].replace("🤖 ", "")} +${pts}`;
          setPhase("result"); return;
        }
        if (r.out.khan === 1) { g.flickStart(); r.flickRes = []; r.flickAnim = 0; setPhase("flick"); }
        else { if (!bad.length) r.msg = `${SIDE()[r.out.khan]} — ${L().nextTurn || ""}`; setPhase("result"); }
      }
      return;
    }
    if (r.phase === "flick") {
      if (r.flickAnim) { if (now - r.flickAnim > 900) { r.flickAnim = 0; if (!r.flickMore) { setPhase("result"); } else r.t0 = now; } return; }
      if (r.out.t === 0) { r.msg = L().yourFlick || ""; if (el > 6000) doFlick(null); }
      else { r.msg = `${names()[r.out.t]} ${L().flicks || ""}`; if (el > 900) doFlick(null); }
      return;
    }
    if (r.phase === "result") { if (el > (r.out && r.out.khan >= 4 ? 2400 : 1500)) nextThrow(); return; }
    if (r.phase === "end") {
      const w = g.winner; r.msg = w === 0 ? "🏆 " + (L().youWin || "") : w > 0 ? `🏆 ${names()[w]}` : "🤝";
      if (el > 2600 && !pending) { pending = true; mode = "wait"; controls();
        send("streamlit:setComponentValue", { value: { inputs: r.inputs, nonce: Date.now() + Math.random() }, dataType: "json" }); }
    }
  }

  // ---- сурет
  const i0 = (r) => 0, o2 = (r) => r.out;
  function asykPos(i, now) {   // [x,y,z, roll, pitch, scale]
    const r = run, g = r.g, o = r.out;
    if (!o || r.phase === "aim" || r.phase === "draw") return null;
    const p = o.pos[i], side = o.sides[i];
    const fly = r.phase === "fly" ? clamp01(((now - r.t0) - i * 35) / 800) : 1;
    let x = p[0], z = p[1], y = FELT + LIFT[side] * AS, roll = ROLL[side], pitch = PITCH[side];
    if (fly < 1) {
      const [sx, sz] = seatW(g, o.t, 0.9), e = ease(fly);
      x = sx + (p[0] - sx) * e; z = sz + (p[1] - sz) * e; y = 0.55 * (1 - e) + FELT + LIFT[side] * AS + Math.sin(Math.PI * e) * 0.45;
      roll = ROLL[side] + (1 - e) * 14; pitch = PITCH[side] + (1 - e) * 6;
      if (fly > 0.85) y += Math.abs(Math.sin((fly - 0.85) * 40)) * 0.03 * (1 - fly) * 6;
    }
    const a = r.ast[i];
    if (a.owner >= 0 && now > a.tOwn) {
      const k = clamp01((now - a.tOwn) / 380), [sx, sz] = seatW(g, a.owner, 1.0);
      const n = a.slot == null ? (a.slot = r.piles[a.owner]++) : a.slot;
      const tx = sx + g.seats[a.owner][1] * (0.06 * (n % 4) - 0.09), tz = sz - g.seats[a.owner][0] * (0.06 * (n % 4) - 0.09) - g.seats[a.owner][1] * 0.05 * Math.floor(n / 4);
      x = x + (tx - x) * ease(k); z = z + (tz - z) * ease(k); y = y + Math.sin(Math.PI * k) * 0.3;
    }
    return [x, y, z, roll, pitch];
  }

  function kidPose(j, now) {
    const r = run, g = r.g, el = now - r.t0, ph = now / 1000;
    let p = HB.blend(BEND, {}, 0), lunge = 0, handW = null;
    p.roll = Math.sin(ph * 1.3 + j) * 0.04; p.hp = -0.75 + Math.sin(ph * 0.9 + j * 2) * 0.05;
    const o = r.out;
    if ((r.phase === "aim" || r.phase === "fly") && g.turn() === j) {
      const k = r.phase === "fly" ? clamp01(el / 300) : 0.5 + 0.5 * Math.sin(ph * 4);
      p = HB.blend(BEND, CROUCH, r.phase === "aim" ? 0.8 : 1);
      p.hands = [[0.3, 0.45, 0.2], r.phase === "fly" ? [0.25 + 0.45 * k, 0.75 - 0.4 * k, -0.15] : [0.15, 0.75 + 0.08 * k, -0.18]];
    }
    if (r.phase === "talapai" && r.pv) {
      const mine = r.pv.order.filter((q) => q[1] === j && q[0] <= el + 250).pop();
      if (mine && el - mine[0] < 600) { lunge = 1 - Math.abs((el - mine[0]) / 600 - 0.4) * 1.2; handW = o.pos[mine[2]]; }
      p = HB.blend(p, CROUCH, 0.7);
      if (j === r.pv.fs) p.hy = Math.sin(ph * 20) * 0.05;
    }
    if (r.phase === "flick" && o && o.t === j) { p = HB.blend(BEND, KNEEL, 1); lunge = 0.9; const ri = run.flickRes.length; handW = o.pos[Math.min(10, ri * 2)]; }
    if (r.phase === "end" && g.winner === j) { p = HB.blend(WIN, {}, 0); p.hip[1] += Math.abs(Math.sin(ph * 6)) * 0.08; }
    return { p, lunge: Math.max(0, lunge), handW };
  }

  function render(now) {
    const r = run, g = r.g, nm = names(), heads = [];
    let khanP = [0, 0.02, 0];
    SPR = [];
    const list = G3.record(() => {
      const m = G3.I4();
      stage(m, now / 1000);
      for (let j = 0; j < g.n; j++) {
        const [sx, sz] = seatW(g, j), kp = kidPose(j, now), d = 0.35 * kp.lunge;
        const R = G3.mul(G3.T(sx - g.seats[j][0] * d, 0, sz - g.seats[j][1] * d), G3.RY(Math.atan2(g.seats[j][1], -g.seats[j][0])));
        let ps = kp.p;
        if (kp.handW) ps = Object.assign({}, ps, { handsW: [HB.xf(R, [0.3, 0.5, 0.2]).map((v, q) => q === 1 ? 0.5 : v), [kp.handW[0], 0.04, kp.handW[1]]] });
        if (kp.handW) { const sk0 = HB.skeleton(R, Object.assign({}, kp.p)); ps.handsW[0] = HB.xf(sk0.Mp, [0.25, -0.25, 0.2]); }
        const sk = HB.skeleton(R, ps); HB.draw(sk, KIDS[j % KIDS.length]);
        const c = HB.xf(sk.Mp, [0, 0, 0]); HB.shadow(m, c[0], c[2], 0.28);
        heads.push(HB.headPt(sk));
        if (j === 0) { const hp = heads[0]; G3.P(m, G3.CONE, [hp[0], hp[1] + 0.42 + Math.sin(now / 250) * 0.04, hp[2]], [0, 0, 3.1416], [0.08, 0.16, 0.08], [0.97, 0.78, 0.2], 0.6); }
      }
      // асықтар
      if (r.out && r.phase !== "aim") {
        for (let i = 0; i < H.N_ASYK; i++) { const a = asykPos(i, now); if (!a) continue;
          const fl = r.phase === "fly" && a[1] > FELT + 0.02, sd = fl ? Math.floor(now / 70 + i) % 4 : o2(r).sides[i];
          asykSpr(a[0], a[1], a[2], sd, i === H.KHAN ? true : r.cols[i], r.yaw[i] > 3.14, fl ? now / 90 + i : 0, 1);
          if (i === H.KHAN) khanP = [a[0], a[1], a[2]];
          if (a[1] < 0.09) G3.P(m, G3.SPH, [a[0] + 0.012, FELT + 0.0015, a[2] + 0.01], null, [0.055, 0.001, 0.04], [0.25, 0.18, 0.1], 0, 0.3); }
      } else {   // шашылып жатқан асықтар → лақтырушының уысына жиналады
        const t = g.turn(), [sx, sz] = seatW(g, t, 0.95), k = r.phase === "aim" ? ease(clamp01((now - r.t0 - i0(r)) / 700)) : 0;
        for (let i = 0; i < H.N_ASYK; i++) {
          const c = r.scatter[i], hx = sx + (i % 4) * 0.035 - 0.05, hy = 0.6 + Math.floor(i / 4) * 0.025, kk = clamp01(k * 1.25 - i * 0.025);
          const x = c.x + (hx - c.x) * kk, y = c.y + (hy - c.y) * kk + Math.sin(Math.PI * kk) * 0.12, z = c.z + (sz - c.z) * kk;
          asykSpr(x, y, z, c.side, i === H.KHAN ? true : r.cols[i], c.yaw > 3.14, kk * 2, kk > 0.9 ? 0.6 : 1);
          if (i === H.KHAN) khanP = [x, y, z];
          if (kk < 0.05) G3.P(m, G3.SPH, [x + 0.012, FELT + 0.0015, z + 0.01], null, [0.055, 0.001, 0.04], [0.25, 0.18, 0.1], 0, 0.3);
        }
      }
    });
    if (V3) {
      view3d(cs, V3.s, 600, 300, [0.7, 3.4, 2.15], [0, 0.0, -0.2], 0.72, list, 0); V3.s.sprites(sprList(false));
      const lab = V3.lab; lab.clearRect(0, 0, 600, 300); lab.textAlign = "center";
      for (let j = 0; j < g.n; j++) { const q = V3.s.project([heads[j][0], heads[j][1] + 0.32, heads[j][2]]); if (!q) continue;
        lab.font = "bold 13px system-ui"; lab.lineWidth = 4; lab.strokeStyle = "rgba(0,0,0,.6)"; lab.fillStyle = CHIP[j];
        const txt = `${nm[j].replace("🤖 ", "")} · ${g.scores[j]}`; lab.strokeText(txt, q[0], q[1]); lab.fillText(txt, q[0], q[1]);
        if (r.phase === "talapai" && (r.shoutP === j || (j === 0 && r.shout != null))) {
          lab.font = "900 16px system-ui"; lab.fillStyle = "#fff"; const w = 92;
          lab.beginPath(); lab.roundRect(q[0] - w / 2, q[1] - 40, w, 24, 10); lab.fillStyle = "#c0392b"; lab.fill();
          lab.fillStyle = "#fff"; lab.fillText("ТАЛАПАЙ!", q[0], q[1] - 22); } }
      const kq = r.out && r.phase !== "aim" ? V3.s.project(khanP) : null;
      if (kq && r.phase !== "fly") { lab.font = "bold 12px system-ui"; lab.fillStyle = "#ffd54f"; lab.strokeText("👑 " + SIDE()[r.out.khan], kq[0], kq[1] - 14); lab.fillText("👑 " + SIDE()[r.out.khan], kq[0], kq[1] - 14); }
      view3d(cf, V3.f, 360, 300, [khanP[0] + 0.06, khanP[1] + 0.62, khanP[2] + 0.2], [khanP[0], khanP[1], khanP[2] - 0.02], 0.5, list, 0); V3.f.sprites(sprList(true));
      view3d(cr, V3.r, 360, 300, [0.05, 0.5, 0.3], [0, 1.15, -1.45], 0.9, list, 0); V3.r.sprites(sprList(false));
    } else {
      [cs, cf, cr].forEach((c, k) => { const w = k ? 360 : 600; c.fillStyle = "#7cb342"; c.fillRect(0, 0, w, 300); c.save(); c.translate(w / 2, 150);
        c.fillStyle = "#efe2c4"; c.beginPath(); c.arc(0, 0, 90, 0, 7); c.fill();
        if (r.out) r.out.pos.forEach((p, i) => { c.fillStyle = i === H.KHAN ? "#c0392b" : "#fff8e1"; c.fillRect(p[0] * 120 - 4, p[1] * 120 - 3, 8, 6); });
        for (let j = 0; j < g.n; j++) { c.fillStyle = CHIP[j]; c.beginPath(); c.arc(g.seats[j][0] * 120, g.seats[j][1] * 120, 12, 0, 7); c.fill(); } c.restore(); });
    }
    $("ls").textContent = L().center || ""; $("lf").textContent = "👑 " + (L().khan || "Хан"); $("lr").textContent = L().front || "";
  }

  // ---- HUD және жолақтар
  function hud(now) {
    const r = run, g = r.g, nm = names();
    $("hud").innerHTML = `<div class="chips">${nm.map((n, j) => `<span class="chip ${g.turn() === j && !g.over ? "on" : ""}" style="border-color:${CHIP[j]}"><i style="background:${CHIP[j]}"></i>${n}<b>${g.scores[j]}</b></span>`).join("")}</div>
      <div class="goal">🎯 ${L().goal || ""}: <b>${g.target}</b> · ${L().throwN || ""} ${g.k + 1}</div>`;
    $("big").textContent = r.msg || ""; $("big").style.fontSize = (r.msg || "").length > 26 ? "19px" : "";
    const pb = $("pbar"), el = now - r.t0;
    if ((r.phase === "aim" && g.turn() === 0) || (r.phase === "flick" && r.out.t === 0 && !r.flickAnim)) {
      const aim = r.phase === "aim", v = H.tri(el, aim ? 1600 : 1200), c = aim ? 0.75 : 0.5, w = aim ? 0.2 * g.hs.h_throw * 0.5 : 0.12 * g.hs.h_aim * 0.6;
      pb.style.display = "block";
      pb.innerHTML = `<span>${aim ? (L().power || "") : (L().aim || "")}</span><i class="zone" style="left:${(c - w) * 100}%;width:${w * 200}%"></i><i class="cur" style="left:${v * 100}%"></i>`;
    } else pb.style.display = "none";
    if (mode === "run") {
      const can = { b_throw: r.phase === "aim" && g.turn() === 0, b_shout: r.phase === "talapai" || r.phase === "watch",
        b_grab: r.phase === "talapai" || r.phase === "watch", b_flick: r.phase === "flick" && r.out && r.out.t === 0 && !r.flickAnim };
      Object.entries(can).forEach(([id, ok]) => { const b = $(id); if (b) b.classList.toggle("off", !ok); });
    }
  }

  function controls() {
    const c = $("ctrl");
    if (mode === "ready") { c.innerHTML = `<button class="go" id="go">▶ ${L().start || "Start"}</button>`; $("go").onclick = start; }
    else if (mode === "run") {
      if (!$("b_throw")) {
        c.innerHTML = `<div class="hbtns"><button id="b_throw">🫳 ${L().throwBtn}</button><button id="b_shout" class="shout">📣 ${L().talapai}!</button>
          <button id="b_grab" class="grab">✋ ${L().grab}</button><button id="b_flick" class="flick">👆 ${L().flick}</button></div>`;
        const on = (id, f) => $(id).addEventListener("pointerdown", (e) => { e.preventDefault(); f(); });
        on("b_throw", mainPress); on("b_flick", mainPress); on("b_shout", shoutNow); on("b_grab", () => grab(null));
      }
    } else c.innerHTML = "";
    setH();
  }
  document.addEventListener("keydown", (e) => { if (keys[e.code]) return; keys[e.code] = true; if (mode !== "run") return;
    if (e.code === "Space") { e.preventDefault(); mainPress(); }
    if (e.code === "Enter" || e.code === "KeyT") { e.preventDefault(); shoutNow(); }
    if (e.code === "KeyG") { e.preventDefault(); grab(null); } });
  document.addEventListener("keyup", (e) => { keys[e.code] = false; });
  // асықты басу (басты көрініс)
  $("cs").parentElement.addEventListener("pointerdown", (e) => {
    if (mode !== "run" || !run || !V3) return;
    const rc = e.currentTarget.getBoundingClientRect(), x = (e.clientX - rc.left) * 600 / rc.width, y = (e.clientY - rc.top) * 300 / rc.height;
    if (run.phase === "talapai" || run.phase === "watch") {
      let b = -1, bd = 34 * 34; const now = performance.now();
      for (let i = 0; i < H.N_ASYK; i++) { if (run.ast[i].owner >= 0) continue; const a = asykPos(i, now); if (!a) continue; const q = V3.s.project([a[0], a[1], a[2]]); if (!q) continue;
        const d = (q[0] - x) ** 2 + (q[1] - y) ** 2; if (d < bd) { bd = d; b = i; } }
      if (b >= 0) grab(b); else if (run.phase === "watch") grab(null);
    } else mainPress();
  });

  function frame(now) {
    requestAnimationFrame(frame);
    if (!args) return;
    if ((mode === "run" || mode === "wait") && run) { if (mode === "run") tick(now); render(now); hud(now); return; }
    if (!run || mode === "idle" || mode === "ready") {   // күту: балалар шеңберде
      if (!run || !run.preview) { const s = args.state, me = args.me == null ? 0 : args.me;
        const g = new H.Game(s.stats[me], s.n_ai, s.level, s.target, s.seed, s.ai_stats);
        run = { g, inputs: [], phase: "idle", t0: now, out: null, taps: [], preview: true, msg: "", scatter: mkScatter(), cols: mkColors() }; newRound(run); }
      run.msg = ""; render(now); hud(now);
    }
  }

  function bar() {
    const a = args, s = a.state, rd = s.rides || [null, null];
    const res = (p) => rd[p] ? `${rd[p].win ? "🏆 " : ""}${rd[p].score} : ${rd[p].best}` : (s.turn === p && !s.over ? "🫳 …" : "—");
    $("bar").innerHTML = s.solo
      ? `<span class="pl">🟦 ${a.names[a.me == null ? 0 : a.me]}</span><span class="res">${rd.find((x) => x) ? res(rd[0] ? 0 : 1) : "—"}</span><span class="pl">${a.ai_name || ""}</span>`
      : `<span class="pl">⚪ ${a.names[0]}</span><span class="res">${res(0)}</span><span class="res">${res(1)}</span><span class="pl">${a.names[1]} ⚫</span>`;
    $("msg").textContent = a.message || "";
  }
  function decide() {
    const s = args.state;
    if (args.clickable && !s.over && !pending) { if (mode !== "run") { mode = "ready"; } }
    else if (mode !== "run" || !args.clickable) mode = "idle";
    controls();
  }
  window.addEventListener("message", (ev) => {
    const d = ev.data;
    if (!d || d.type !== "streamlit:render") return;
    const prev = args; args = d.args;
    if (!prev || prev.state.turn !== args.state.turn || (prev.state.last || {}).id !== (args.state.last || {}).id) { pending = false; if (mode === "wait") mode = "idle"; run = null; }
    bar(); decide(); setH();
  });
  window.addEventListener("resize", () => args && setH());
  requestAnimationFrame(frame);
  send("streamlit:componentReady", { apiVersion: 1 });
  // ================= HANTALAPAY UI соңы =================
