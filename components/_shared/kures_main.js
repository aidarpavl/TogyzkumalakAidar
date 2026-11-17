  // ================= KURES UI =================
  const send = (type, data) => window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type }, data), "*");
  const $ = (id) => document.getElementById(id);
  const cs = $("cs").getContext("2d"), cf = $("cf").getContext("2d"), cr = $("cr").getContext("2d");
  const L = () => (args && args.labels) || {};
  const setH = () => send("streamlit:setFrameHeight", { height: Math.ceil($("wrap").getBoundingClientRect().height + 8) });
  let args = null, mode = "idle", run = null, pending = false, joy = { x: 0, y: 0, on: false }, keys = {};

  const STYLE = [
    { jacket: "#1f5fa0", jacket2: "#174a7e", trim: "#f4f1ea", belt: "#d9a520", pants: "#f2efe8", boot: "#5a3a22",
      skin: "#c99066", skin2: "#b27a52", hair: "#15100c", lip: "#985846" },
    { jacket: "#b0202e", jacket2: "#861722", trim: "#f4f1ea", belt: "#f1ede4", pants: "#f2efe8", boot: "#45291a",
      skin: "#d6a37c", skin2: "#be8a64", hair: "#1b1410", lip: "#a26050", mustache: true },
  ];
  const JUDGE = { jacket: "#f3f0e8", jacket2: "#dcd8cf", trim: "#2b2b2b", belt: "#2b2b2b", pants: "#2a2a2e", boot: "#1d1410",
    skin: "#c8946c", skin2: "#ae7c56", hair: "#d9d6d0", lip: "#91574a", beard: true, cap: "#1b1b1b" };

  __GL3D__

  const V3 = setup3d();
  const clamp01 = (x) => Math.max(0, Math.min(1, x)), ease = (x) => x * x * (3 - 2 * x);
  const B0 = HB.BASEPOSE;
  const GRIP = { hip: [-0.1, 0.82, 0], pel: 0.28, pitch: 0.55, roll: 0, yaw: 0, hp: -0.5, hy: 0.5, hr: 0,
    feet: [[-0.3, 0.08, 0.26], [0.04, 0.08, -0.25]], hands: B0.hands, toe: [0, 0] };
  const LYING = { hip: [0, 0.9, 0], pel: 0, pitch: 0, roll: 0, yaw: 0, hp: 0.15, hy: 0.3, hr: 0,
    feet: [[0.06, 0.08, 0.24], [0.02, 0.08, -0.26]], hands: [[0.05, 1.3, 0.62], [0.1, 1.15, -0.62]], toe: [0, 0] };
  const FLY = { hip: [0, 0.9, 0], pel: 0, pitch: 0.2, roll: 0, yaw: 0, hp: -0.4, hy: 0, hr: 0,
    feet: [[0.25, 0.25, 0.3], [-0.1, 0.15, -0.3]], hands: [[0.15, 1.55, 0.55], [0.1, 1.45, -0.6]], toe: [0, 0] };
  const KNEEL = { hip: [-0.05, 0.55, 0], pel: 0.3, pitch: 0.5, roll: 0.1, yaw: 0, hp: -0.3, hy: 0, hr: 0,
    feet: [[0.25, 0.08, 0.22], [-0.4, 0.06, -0.2]], hands: [[0.45, 0.4, 0.3], [0.3, 0.7, -0.3]], toe: [0, 0] };
  const WIN = { hip: [0, 0.9, 0], pel: 0, pitch: -0.05, roll: 0, yaw: 0, hp: -0.35, hy: 0, hr: 0,
    feet: [[0, 0.08, 0.2], [0.05, 0.08, -0.2]], hands: [[0.05, 2.0, 0.35], [0.05, 2.0, -0.35]], toe: [0, 0] };
  const C_PEL = 0.98 * HB.S;   // айналу орталығы (жамбас биіктігі)

  // ---- ойын алаңы (сырмақ, киіз үйлер, көрермендер, төреші)
  const CROWD = [];
  for (let k = 0; k < 34; k++) { const a = k / 34 * 6.2832 + 0.09, r = 6.6 + (k % 3) * 0.7;
    CROWD.push({ x: Math.cos(a) * r, z: Math.sin(a) * r, c: [[0.55, 0.12, 0.15], [0.12, 0.3, 0.5], [0.25, 0.45, 0.25], [0.5, 0.35, 0.15], [0.35, 0.2, 0.4]][k % 5],
      h: (k % 4) ? [0.1, 0.08, 0.07] : [0.85, 0.82, 0.78], ph: k * 1.7 }); }
  function stage(m, t, cheer) {
    const { P, BOX, CYL, CONE, SPH } = G3;
    P(m, BOX, [0, -0.05, 0], null, [300, 0.1, 300], [0.6, 0.64, 0.33]);
    P(m, BOX, [0, 0.02, 0], null, [9.6, 0.05, 9.6], [0.6, 0.15, 0.15], 0.02);          // шекара
    P(m, BOX, [0, 0.03, 0], null, [8.0, 0.05, 8.0], [0.9, 0.84, 0.7], 0.02);           // кілем
    P(m, CYL, [0, 0.056, 0], null, [1.3, 0.004, 1.3], [0.2, 0.4, 0.62], 0.05);
    P(m, CYL, [0, 0.058, 0], null, [1.1, 0.004, 1.1], [0.9, 0.84, 0.7], 0.02);
    for (let k = 0; k < 32; k++) { const s = (k % 8) / 8 * 8 - 3.5, side = Math.floor(k / 8), x = side < 2 ? s : (side === 2 ? 4.4 : -4.4), z = side < 2 ? (side ? 4.4 : -4.4) : s;
      P(m, BOX, [x, 0.06, z], [0, 0.785, 0], [0.32, 0.02, 0.32], [0.95, 0.8, 0.3], 0.1); }
    for (let k = 0; k < 7; k++) { const a = k / 7 * 6.2832 + 0.5, x = Math.cos(a) * 17, z = Math.sin(a) * 17;
      P(m, CYL, [x, 1.1, z], null, [3.4, 2.2, 3.4], [0.95, 0.93, 0.88], 0.02);
      P(m, CONE, [x, 3.0, z], null, [3.6, 1.7, 3.6], [0.92, 0.9, 0.84], 0.02);
      P(m, BOX, [x - Math.cos(a) * 3.3, 0.9, z - Math.sin(a) * 3.3], [0, -a, 0], [0.08, 1.6, 1.0], [0.6, 0.18, 0.15], 0.1); }
    CROWD.forEach((c) => {   // отырған көрермендер (бетін кілемге қаратып)
      const j = cheer ? Math.max(0, Math.sin(t * 9 + c.ph)) * 0.12 : Math.sin(t * 1.3 + c.ph) * 0.015;
      const ux = -c.x / Math.hypot(c.x, c.z), uz = -c.z / Math.hypot(c.x, c.z), M = root(c.x, c.z, ux, uz), { seg } = G3;
      P(M, BOX, [-0.1, 0.22, 0], null, [0.5, 0.44, 0.6], [0.45, 0.3, 0.18]);                      // орындық
      [1, -1].forEach((sd) => { seg(M, [-0.05, 0.5, sd * 0.11], [0.3, 0.5, sd * 0.12], 0.075, [0.2, 0.18, 0.2]);
        seg(M, [0.3, 0.5, sd * 0.12], [0.32, 0.06, sd * 0.13], 0.06, [0.2, 0.18, 0.2]); });
      P(M, SPH, [-0.06, 0.82 + j, 0], null, [0.15, 0.3, 0.21], c.c, 0.05);                        // шапан
      [1, -1].forEach((sd) => { P(M, SPH, [-0.05, 1.05 + j, sd * 0.19], null, [0.08, 0.07, 0.08], c.c);
        if (cheer) seg(M, [-0.05, 1.05 + j, sd * 0.2], [0.05, 1.5 + j * 2, sd * 0.3], 0.05, c.c);
        else seg(M, [-0.05, 1.05, sd * 0.2], [0.2, 0.62, sd * 0.15], 0.05, c.c); });
      P(M, CYL, [-0.04, 1.14 + j, 0], null, [0.05, 0.06, 0.05], [0.78, 0.55, 0.4]);
      P(M, SPH, [-0.03, 1.28 + j, 0], null, [0.1, 0.12, 0.09], [0.8, 0.57, 0.42], 0.1);
      P(M, SPH, [0.06, 1.27 + j, 0], null, [0.02, 0.03, 0.02], [0.75, 0.52, 0.38]);
      if (c.h[0] > 0.5) P(M, SPH, [-0.05, 1.31 + j, 0], null, [0.115, 0.13, 0.105], c.h, 0.05);   // кимешек
      else { P(M, CYL, [-0.04, 1.37 + j, 0], null, [0.11, 0.05, 0.11], c.h, 0.1); P(M, SPH, [-0.04, 1.4 + j, 0], null, [0.11, 0.04, 0.11], c.h, 0.1); }
    });
  }

  // ---- поза есептеу
  const root = (x, z, hx, hz) => G3.mul(G3.T(x, 0, z), G3.RY(Math.atan2(-hz, hx)));
  function livePose(r, grip, t, i, walk) {
    let p;
    if (!grip) {
      p = HB.blend(B0, {}, 0);
      const g = walk || 0, ph = t * 7 + i;
      if (g > 0.01) { p.feet = [[-0.04 + Math.sin(ph) * 0.17 * g, 0.08 + Math.max(0, Math.sin(ph)) * 0.08 * g, 0.2], [0.1 - Math.sin(ph) * 0.17 * g, 0.08 + Math.max(0, -Math.sin(ph)) * 0.08 * g, -0.2]];
        p.hip = [0, 0.88 + Math.abs(Math.sin(ph)) * 0.02, 0]; }
      p.roll = Math.sin(t * 1.6 + i) * 0.04; p.hip[2] = Math.sin(t * 1.6 + i) * 0.03;
      return p;
    }
    p = HB.blend(GRIP, {}, 0);
    const w = r.wind > 0 ? clamp01(r.k / Math.max(1, r.k + r.wind)) : 0;
    if (r.hold === 1) { p.hip = [-0.16, 0.7, 0]; p.pitch = 0.65; p.feet = [[-0.42, 0.08, 0.3], [0.02, 0.08, -0.3]]; }
    if (r.wind > 0) {
      const a = r.act;
      if (a === "pull") { p.hip[0] -= 0.14 * w; p.pitch -= 0.3 * w; }
      else if (a === "push") { p.hip[0] += 0.12 * w; p.pitch += 0.15 * w; p.feet[0] = [-0.45 * w - 0.3, 0.08, 0.26]; }
      else if (a === "rock") { const sw = Math.sin(w * 6.28); p.roll = 0.3 * sw; p.hip[2] = 0.1 * sw; }
      else if (a === "surin" || a === "ilip") { p.feet[1] = [0.1 + 0.55 * w, 0.08 + 0.12 * w, a === "ilip" ? -0.05 : -0.3]; p.pitch += 0.1 * w; }
      else if (a === "burap") { p.yaw = 0.6 * w; p.roll = -0.2 * w; }
      else if (a === "zhambas") { p.yaw = 1.0 * w; p.hip = [0.15 * w - 0.1, 0.82 - 0.14 * w, 0]; }
      else if (a === "koter") { p.hip = [0.05 * w - 0.1, 0.82 - 0.22 * w, 0]; p.pitch = 0.55 - 0.2 * w; }
      else if (a === "arqa") { p.hip = [0.18 * w - 0.1, 0.82 - 0.2 * w, 0]; p.pitch = 0.55 - 0.45 * w; }
    }
    const wob = (1 - r.b / r.bmax); p.roll += Math.sin(t * 6 + i * 2) * wob * 0.18; p.pitch += wob * 0.15;
    if (r.jolt) { p.hip[0] += r.jolt[0]; p.pitch += r.jolt[1]; }
    return p;
  }

  // әдіс анимациясы: шабуылдаушы кадрында қорғаушының түбір матрицасы мен позасы
  const THA = {
    surin: { end: [0.75, 0.25], arc: 0.25, rz: 1.57, rx: 0.3, yaw: 0.3 },
    ilip: { end: [0.85, -0.15], arc: 0.3, rz: 1.57, rx: -0.2, yaw: -0.2 },
    burap: { end: [0.35, 0.75], arc: 0.35, rz: 1.25, rx: 0.9, yaw: 1.6 },
    zhambas: { end: [-1.55, 0.2], arc: 1.15, rz: -4.71, rx: 0.15, yaw: 0, flip: true, ayaw: 3.14 },
    koter: { end: [-0.65, 1.0], arc: 1.1, rz: 1.57, rx: 0.6, yaw: 0.9, lift: true },
    arqa: { end: [-2.0, 0.0], arc: 1.7, rz: -4.71, rx: 0, yaw: 0, flip: true, bridge: true },
  };
  function throwFrame(an, u) {
    const d = THA[an.name], dd = an.dd, sc = an.sc;
    const { mul, T, RY, RZ, RX } = G3;
    let ex = d.end[0] + dd, ez = d.end[1], rz = d.rz, rx = d.rx, yaw = d.yaw, fly = 1, yEnd = -C_PEL + 0.22 * HB.S;
    if (sc === 3) { rz = d.flip ? rz + 0.5 : rz - 0.45; rx = rx + 1.05; }
    if (sc === 2) { rz = d.flip ? -6.28 + 1.0 : rz * 0.6; rx = rx * 0.5; ex = dd + (ex - dd) * 0.6; yEnd = -C_PEL + 0.5 * HB.S; }
    if (sc <= 1) fly = 0;
    const k = ease(clamp01(u / 0.72));
    let D;
    if (fly) {
      const x = dd + (ex - dd) * k, z = ez * k, y = yEnd * k + d.arc * Math.sin(Math.PI * k);
      D = mul(mul(mul(mul(mul(T(x, y, z), RY(3.1416 + yaw * k)), T(0, C_PEL, 0)), RZ(rz * k)), RX(rx * k)), T(0, -C_PEL, 0));
    } else {
      const s = sc === 1 ? 0.25 * Math.sin(Math.PI * clamp01(u / 0.5)) : 0;
      D = mul(T(dd + s, 0, 0), RY(3.1416));
    }
    const dp = fly ? (k < 0.85 ? HB.blend(GRIP, FLY, clamp01(k * 2.5)) : HB.blend(FLY, LYING, clamp01((k - 0.85) / 0.15)))
      : (sc === 1 ? HB.blend(GRIP, KNEEL, Math.sin(Math.PI * clamp01(u / 0.8))) : GRIP);
    // шабуылдаушы
    let ap = HB.blend(GRIP, {}, 0), ayaw = 0;
    const a = clamp01(u / 0.5);
    if (an.name === "surin" || an.name === "ilip") { ap.feet[1] = [0.1 + 0.6 * Math.sin(Math.PI * a), 0.1 + 0.25 * Math.sin(Math.PI * a), -0.1]; ap.pitch = 0.6 + 0.2 * a; }
    if (an.name === "burap") { ap.yaw = 0.6 + 0.6 * a; ap.roll = -0.3 * a; }
    if (d.ayaw) { ayaw = d.ayaw * ease(clamp01(u / 0.35)); ap.hip = [0.05, 0.72, 0]; ap.pitch = 0.4 + 0.6 * clamp01((u - 0.3) / 0.3); }
    if (d.lift) { ap.hip = [0, 0.72 + 0.25 * a, 0]; ap.pitch = 0.5 - 0.4 * a; ayaw = 0.6 * clamp01((u - 0.4) / 0.3); }
    if (d.bridge) { const b = ease(clamp01(u / 0.5)); ap.hip = [0.2 * b, 0.82 - 0.25 * b, 0]; ap.pitch = 0.4 - 1.5 * b; ap.hp = 0.6 * b;
      ap.feet = [[-0.05, 0.08, 0.25], [0.05, 0.08, -0.25]]; }
    if (sc === 0) { ap = HB.blend(GRIP, KNEEL, Math.sin(Math.PI * clamp01(u / 0.9)) * 0.7); }
    if (u > 0.85 && sc >= 1) ap = HB.blend(ap, B0, clamp01((u - 0.85) / 0.15));
    return { D, dp, ap, ayaw, hold: u < 0.6 && fly };
  }

  // ---- барлық сахна
  function scene(snap, t, anim, end) {
    const out = {};
    const list = G3.record(() => {
      const m = G3.I4(), cheer = !!(anim && anim.u > 0.6 && anim.sc >= 2) || !!end;
      stage(m, t, cheer);
      const p = snap.p, a = p[0], b = p[1];
      let dx = b.x - a.x, dz = b.y - a.y; const dl = Math.hypot(dx, dz) || 1; dx /= dl; dz /= dl;
      let R = [root(a.x, a.y, dx, dz), root(b.x, b.y, -dx, -dz)], PS = [null, null], hands = [null, null];
      if (anim && (anim.kind === "throw" || anim.kind === "counter")) {
        const i = anim.att, j = 1 - i, f = throwFrame(anim, anim.u), Ra = R[i];
        R[i] = G3.mul(Ra, G3.RY(f.ayaw)); R[j] = G3.mul(Ra, f.D); PS[i] = f.ap; PS[j] = f.dp;
        if (f.hold) hands[i] = true;
      } else if (end) {
        PS[end.w] = WIN; PS[1 - end.w] = end.clean ? LYING : HB.blend(B0, { pitch: 0.5, hp: 0.3, hands: [[0.3, 0.9, 0.2], [0.3, 0.9, -0.2]] }, 1);
        if (end.clean) R[1 - end.w] = end.lieM;
      }
      for (let i = 0; i < 2; i++) if (!PS[i]) PS[i] = livePose(p[i], snap.grip, t, i, snap.walk ? snap.walk[i] : 0);
      const SK = [HB.skeleton(R[0], PS[0]), HB.skeleton(R[1], PS[1])];
      // белбеуден ұстау
      for (let i = 0; i < 2; i++) {
        const holding = (snap.grip && !anim && !end) || hands[i];
        if (holding) { PS[i] = Object.assign({}, PS[i], { handsW: [HB.beltBack(SK[1 - i], -1), HB.beltBack(SK[1 - i], 1)] }); SK[i] = HB.skeleton(R[i], PS[i]); }
      }
      for (let i = 0; i < 2; i++) {
        HB.draw(SK[i], STYLE[i]);
        const c = HB.xf(SK[i].Mp, [0, 0, 0]); HB.shadow(m, c[0], c[2], 0.3);
      }
      // ойыншы белгісі
      const hp = HB.headPt(SK[0]); G3.P(m, G3.CONE, [hp[0], hp[1] + 0.55 + Math.sin(t * 4) * 0.05, hp[2]], [0, 0, 3.1416], [0.1, 0.2, 0.1], [0.97, 0.78, 0.2], 0.6);
      // төреші
      const up = (anim && anim.u > 0.55 && anim.sc >= 1) || end;
      const jp = HB.blend(B0, { hip: [0, 0.92, 0], pel: 0, pitch: 0.05, hp: -0.1, feet: [[0, 0.08, 0.16], [0.02, 0.08, -0.16]],
        hands: up ? [[0.1, 2.05, 0.4], [0.05, 1.0, -0.3]] : [[0.05, 1.0, 0.3], [0.05, 1.0, -0.3]] }, 1);
      HB.draw(HB.skeleton(root(-4.9, -4.9, 1, 1), jp), JUDGE);
      out.sk = SK;
    });
    return { list, sk: out.sk };
  }

  function render(snap, t, anim, end) {
    const { list, sk } = scene(snap, t, anim, end);
    const hm = HB.headPt(sk[0]), ho = HB.headPt(sk[1]), cm = HB.xf(sk[0].Mp, [0, 0, 0]), co = HB.xf(sk[1].Mp, [0, 0, 0]);
    const mx = (cm[0] + co[0]) / 2, mz = (cm[2] + co[2]) / 2;
    let ax = co[0] - cm[0], az = co[2] - cm[2]; const al = Math.hypot(ax, az) || 1; ax /= al; az /= al;
    if (V3) {
      const nx = -az, nz = ax, sd = Math.max(3.7, al * 0.9 + 2.9);
      view3d(cs, V3.s, 600, 300, [mx + nx * sd, 1.55, mz + nz * sd], [mx, 1.0, mz], 0.72, list, mx * 4);
      V3.lab.clearRect(0, 0, 600, 300);
      // алдынан: қарсыластың иығының үстінен ойыншының бетіне
      view3d(cf, V3.f, 360, 300, [co[0] + ax * 0.7 - nx * 1.5, 2.0, co[2] + az * 0.7 - nz * 1.5], [hm[0], hm[1] - 0.2, hm[2]], 0.8, list, 0);
      // артынан: ойыншының иығының үстінен қарсыласқа
      view3d(cr, V3.r, 360, 300, [cm[0] - ax * 1.3 + nx * 1.1, 2.1, cm[2] - az * 1.3 + nz * 1.1], [ho[0], ho[1] - 0.35, ho[2]], 0.8, list, 0);
    } else {
      [cs, cf, cr].forEach((c, k) => { const w = k ? 360 : 600; c.fillStyle = "#e8d9b5"; c.fillRect(0, 0, w, 300);
        const sc = 300 / 10; c.save(); c.translate(w / 2, 150); c.strokeStyle = "#9c2a2a"; c.strokeRect(-4 * sc, -4 * sc, 8 * sc, 8 * sc);
        snap.p.forEach((r, i) => { c.fillStyle = i ? "#c0392b" : "#2e86de"; c.beginPath(); c.arc(r.x * sc, r.y * sc, 10, 0, 7); c.fill(); }); c.restore(); });
    }
    $("ls").textContent = L().side || ""; $("lf").textContent = L().front || ""; $("lr").textContent = L().rear || "";
  }

  // ---- HUD
  const TNAME = (n) => L()["thr_" + n] || n;
  function hud(sim) {
    const me = sim.p[0], op = sim.p[1], left = sim.golden ? Math.max(0, (sim.limit - sim.n) * K.DT) : Math.max(0, (sim.boutSteps - sim.n) * K.DT);
    const mm = Math.floor(left / 60), ss = String(Math.floor(left % 60)).padStart(2, "0");
    const bar = (v, mx, c) => `<div class="meter"><i style="width:${Math.max(0, Math.min(100, v / mx * 100))}%;background:${c}"></i></div>`;
    let st = sim.grip ? (L().gripOn || "") : (L().approach || "");
    if (op.wind > 0 && K.isThrow(op.act)) st = `⚠ ${TNAME(op.act)}! → ${L()["a_" + K.THROWS[op.act][5]] || ""}`;
    else if (op.wind > 0) st = `⚠ ${L()["a_" + op.act] || ""} → ${L()["a_" + K.COUNTER[op.act]] || ""}`;
    $("hud").innerHTML = `<div>${L().score || ""}<b>${me.pts} : ${op.pts}</b><small>${sim.golden ? "⭐ " + (L().golden || "") : ""} ${mm}:${ss}</small></div>
      <div>${L().myBal || ""}<b>${Math.round(me.b)}</b>${bar(me.b, me.bmax, "#2e86de")}</div>
      <div>${L().opBal || ""}<b>${Math.round(op.b)}</b>${bar(op.b, op.bmax, "#c0392b")}</div>
      <div>${L().stamina || ""}<b>${Math.round(me.s)}</b>${bar(me.s, me.smax, "linear-gradient(90deg,#e74c3c,#f1c40f,#2ecc71)")}</div>
      <div class="${op.wind > 0 ? "alert" : ""}">${L().state || ""} ${me.warn ? "🟨".repeat(me.warn) : ""}<b class="small">${st}</b></div>`;
    // дәлдік жолағы
    const tb = $("tbar");
    if (me.wind > 0 && K.isThrow(me.act)) {
      const W = K.THROWS[me.act][0], sweet = W - 4, z0 = Math.max(0, sweet - me.tech), z1 = Math.min(W, sweet + me.tech);
      tb.style.display = "block";
      tb.innerHTML = `<span>${TNAME(me.act)}</span><i class="zone" style="left:${z0 / W * 100}%;width:${(z1 - z0) / W * 100}%"></i><i class="cur" style="left:${me.k / W * 100}%"></i>`;
    } else tb.style.display = "none";
    // әдіс батырмаларын жаңарту
    if (mode === "run") {
      const busy = me.wind > 0 && K.isThrow(me.act);
      $("tr").style.display = busy ? "none" : ""; $("rel").style.display = busy ? "" : "none";
      K.THROW_ORDER.forEach((n) => { const b = $("t_" + n); if (!b) return;
        const ok = sim.grip && me.wind === 0 && op.b < K.THROWS[n][2] * op.bmax && me.s >= K.THROWS[n][1];
        b.classList.toggle("off", !ok); });
      $("b_g").classList.toggle("off", sim.grip);
    }
  }

  // ---- басқару
  const TKEYS = ["surin", "ilip", "burap", "zhambas", "koter", "arqa"];
  function controls() {
    const c = $("ctrl");
    if (mode === "ready") { c.innerHTML = `<button class="go" id="go">▶ ${L().start || "Start"}</button>`; $("go").onclick = start; }
    else if (mode === "run") {
      c.innerHTML = `<div id="joy"><div id="knob"></div></div><div class="pad"><div class="btns">
        <button id="b_g" class="grip">🤝 ${L().grip}</button><button id="b_pull">⬅ ${L().a_pull}</button>
        <button id="b_push">${L().a_push} ➡</button><button id="b_rock">↔ ${L().a_rock}</button>
        <button id="b_h" class="hold">🛡 ${L().hold}</button></div>
        <div class="thr" id="tr">${TKEYS.map((n, i) => `<button id="t_${n}" class="off"><small>${i + 1}</small> ${TNAME(n)}</button>`).join("")}</div>
        <button id="rel" class="rel" style="display:none">💥 ${L().release}</button></div>`;
      const pad = $("joy"), knob = $("knob");
      const upd = (ev) => { const r = pad.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
        let dx = (ev.clientX - cx) / (r.width / 2), dy = (ev.clientY - cy) / (r.height / 2); const l = Math.hypot(dx, dy);
        if (l > 1) { dx /= l; dy /= l; } joy = { x: dx, y: dy, on: l > 0.25 }; knob.style.transform = `translate(${dx * 34}px, ${dy * 34}px)`; };
      pad.addEventListener("pointerdown", (e) => { pad.setPointerCapture(e.pointerId); upd(e); });
      pad.addEventListener("pointermove", (e) => { if (e.buttons || e.pointerType === "touch") upd(e); });
      const end = () => { joy = { x: 0, y: 0, on: false }; knob.style.transform = ""; };
      pad.addEventListener("pointerup", end); pad.addEventListener("pointercancel", end);
      const on = (id, a) => $(id).addEventListener("pointerdown", (e) => { e.preventDefault(); act(a); });
      on("b_g", ["g", null]); on("b_pull", ["a", "pull"]); on("b_push", ["a", "push"]); on("b_rock", ["a", "rock"]); on("rel", ["t", null]);
      TKEYS.forEach((n) => on("t_" + n, ["a", n]));
      const hb = $("b_h");
      hb.addEventListener("pointerdown", (e) => { e.preventDefault(); hb.setPointerCapture(e.pointerId); act(["h", 1]); });
      ["pointerup", "pointercancel"].forEach((t) => hb.addEventListener(t, () => act(["h", 0])));
    } else c.innerHTML = "";
    setH();
  }
  document.addEventListener("keydown", (e) => { if (keys[e.code]) return; keys[e.code] = true; if (mode !== "run") return;
    const map = { KeyF: ["g", null], KeyJ: ["a", "pull"], KeyK: ["a", "push"], KeyL: ["a", "rock"], Enter: ["t", null], KeyT: ["t", null] };
    TKEYS.forEach((n, i) => { map["Digit" + (i + 1)] = ["a", n]; });
    if (map[e.code]) { e.preventDefault(); let a = map[e.code];
      if (a[0] === "a" && run && run.sim.p[0].wind > 0 && run.sim.p[0].act === a[1]) a = ["t", null];   // сол әдісті қайта басу — лақтыру
      act(a); }
    if (e.code === "Space") { e.preventDefault(); act(["h", 1]); } });
  document.addEventListener("keyup", (e) => { keys[e.code] = false; if (mode === "run" && e.code === "Space") act(["h", 0]); });

  function act(a) { if (run && !run.done) run.queue.push(a); }
  function keyDir() { let x = 0, y = 0;
    if (keys.KeyA || keys.ArrowLeft) x -= 1; if (keys.KeyD || keys.ArrowRight) x += 1;
    if (keys.KeyW || keys.ArrowUp) y -= 1; if (keys.KeyS || keys.ArrowDown) y += 1; return [x, y]; }

  function start() {
    const s = args.state, me = args.me;
    const sim = new K.Sim(s.stats[me], s.level, s.bout_s, s.ai_stats, s.weight);
    run = { sim, inputs: [], queue: [], lastDir: [0, 0], t0: performance.now() + 3000, done: false, ev0: 0, flash: "", flashT: 0,
      anim: null, snap: null, pause: 0, walk: [0, 0], end: null };
    window.__kRun = run; mode = "run"; controls();
  }
  const snapOf = (p, grip, walk) => ({ p: JSON.parse(JSON.stringify(p)), grip, walk: walk ? walk.slice() : [0, 0] });

  function stepRun(now) {
    const r = run, sim = r.sim, t = (now - r.t0) / 1000, tw = now / 1000;
    if (t < 0) { $("big").textContent = Math.ceil(-t); render(snapOf(sim.p, sim.grip), tw, null, null); hud(sim); return; }
    if (r.pause && now < r.pause) {
      if (r.anim) r.anim.u = (now - r.animT) / 1000 / r.anim.dur;
      render(r.snap, tw, r.anim, r.end); hud(sim); $("big").textContent = r.flash; return; }
    if (r.pause) { r.t0 += now - r.pauseFrom; r.pause = 0; r.anim = null; r.snap = null; }
    if (r.done) {
      if (!pending) { pending = true; mode = "wait"; controls();
        send("streamlit:setComponentValue", { value: { inputs: r.inputs, nonce: Date.now() + Math.random() }, dataType: "json" }); }
      render(r.snap || snapOf(sim.p, sim.grip), tw, null, r.end); hud(sim); return;
    }
    const target = Math.floor(((now - r.t0) / 1000) / K.DT);
    let guard = 0;
    while (!r.done && sim.n < target && guard < 12) {
      const n = sim.n, ev = [];
      let [dx, dy] = keyDir(); if (joy.on) { dx = joy.x; dy = joy.y; }
      let d = [0, 0]; const l = Math.hypot(dx, dy);
      if (l > 0.2) d = [Math.round(dx / l * 1000) / 1000, Math.round(dy / l * 1000) / 1000];
      if (Math.abs(d[0] - r.lastDir[0]) + Math.abs(d[1] - r.lastDir[1]) > 0.05) { ev.push([n, "d", d]); r.lastDir = d; }
      while (r.queue.length) { const q = r.queue.shift(); ev.push([n, q[0], q[1]]); }
      ev.forEach((e) => r.inputs.push(e));
      const before = snapOf(sim.p, sim.grip, r.walk), e0 = sim.events.length;
      sim.step(ev); guard++;
      sim.p.forEach((pp, i) => { const mv = Math.hypot(pp.x - before.p[i].x, pp.y - before.p[i].y) > 0.01 && !sim.grip; r.walk[i] += ((mv ? 1 : 0) - r.walk[i]) * 0.25; });
      // оқиғалар
      let stop = false;
      for (let j = e0; j < sim.events.length; j++) {
        const e = sim.events[j], kind = e[1];
        if (kind === "throw") {
          const sc = e[4], i = e[2], dd = Math.hypot(before.p[1].x - before.p[0].x, before.p[1].y - before.p[0].y) || 0.9;
          r.anim = { kind: "throw", name: e[3], sc, att: i, dd, u: 0, dur: sc >= 2 ? 1.7 : 1.1 }; r.snap = before; stop = true;
          r.flash = sc === 4 ? "🏆 " + (L().clean || "") : sc ? `${i === 0 ? "✅" : "😣"} ${TNAME(e[3])}: +${sc}` : `✖ ${TNAME(e[3])} — ${L().failed || ""}`;
        } else if (kind === "tcounter") {
          const i = e[2], dd = Math.hypot(before.p[1].x - before.p[0].x, before.p[1].y - before.p[0].y) || 0.9;
          r.anim = { kind: "counter", name: e[3], sc: 0, att: 1 - i, dd, u: 0, dur: 1.0 }; r.snap = before; stop = true;
          r.flash = `🔁 ${L().tcounter || ""} +1`;
        } else if (kind === "grip") { r.flash = "🤝 " + (L().gripOn || ""); }
        else if (kind === "warn") { r.flash = "🟨 " + (e[3] === "out" ? L().warnOut : L().warnPassive); }
        else if (kind === "pen") { r.flash = "🟨🟨 " + (L().penalty || ""); }
        else if (kind === "golden") { r.flash = "⭐ " + (L().golden || ""); }
        else if (kind === "counter") { if (e[2] === 0) r.flash = "🔁 " + (L().counter || ""); sim.p[1 - e[2]].jolt = [-0.08, 0.15]; }
        else if (BASICS.includes(kind)) { const o = sim.p[1 - e[2]]; o.jolt = kind === "pull" ? [0.12, 0.2] : kind === "push" ? [-0.15, -0.15] : [0, 0.1]; o.joltT = now; }
        if (kind === "end") {
          const w = e[2]; r.done = true;
          r.end = w >= 0 ? { w, clean: sim.clean >= 0 } : null;
          if (r.end && r.end.clean && r.anim) { const f = throwFrame(r.anim, 1), dx = before.p[1].x - before.p[0].x, dz = before.p[1].y - before.p[0].y, dl = Math.hypot(dx, dz) || 1;
            r.end.lieM = G3.mul(root(before.p[r.anim.att].x, before.p[r.anim.att].y, (r.anim.att ? -dx : dx) / dl, (r.anim.att ? -dz : dz) / dl), f.D); }
          r.endFlash = w === 0 ? "🏆 " + (L().youWin || "") : w === 1 ? "😣 " + (L().youLose || "") : "🤝 " + (L().draw || "");
        }
      }
      r.flashT = now;
      if (stop) { r.animT = now; r.pauseFrom = now; r.pause = now + r.anim.dur * 1000 + 400; break; }
      if (r.done) break;
    }
    sim.p.forEach((pp) => { if (pp.jolt && now - (pp.joltT || 0) > 300) pp.jolt = null; });
    if (r.done && !r.pause) { r.snap = snapOf(sim.p, sim.grip); r.pause = now + 2200; r.pauseFrom = now; r.flash = r.endFlash; }
    $("big").textContent = r.pause ? r.flash : (now - r.flashT < 1300 ? r.flash : "");
    render(r.anim ? r.snap : snapOf(sim.p, sim.grip, r.walk), tw, r.anim, r.anim ? null : r.end); hud(sim);
  }
  const BASICS = ["pull", "push", "rock"];

  let idle = null;
  function frame(now) {
    requestAnimationFrame(frame);
    if (!args) return;
    if (mode === "run" && run) {
      if (run.done && run.pause && now >= run.pause && run.anim) {   // лақтыру аяқталды → жеңімпаз
        run.anim = null; run.snap = snapOf(run.sim.p, run.sim.grip); run.pause = now + 2200; run.flash = run.endFlash; }
      stepRun(now); return; }
    if (!idle) { const s = args.state, me = args.me == null ? 0 : args.me; idle = new K.Sim(s.stats[me], s.level, s.bout_s, s.ai_stats, s.weight); }
    const t = now / 1000;
    if (window.__kDemo) { const d = window.__kDemo; const q = snapOf(idle.p, d.grip); if (d.gap) { q.p[0].x = -d.gap / 2; q.p[1].x = d.gap / 2; }
      if (d.end && d.end.lie) { const f = throwFrame(d.anim0, 1); d.end.lieM = G3.mul(root(q.p[d.anim0.att].x, 0, d.anim0.att ? -1 : 1, 0), f.D); }
      render(q, d.t, d.anim || null, d.end || null); hud(idle); return; }   // сынақ үшін
    render(snapOf(idle.p, false), t, null, null); hud(idle);
  }

  function bar() {
    const a = args, s = a.state, rd = s.rides || [null, null];
    const res = (p) => rd[p] ? `${rd[p].clean === 0 ? "🏆 " : ""}${rd[p].pf} : ${rd[p].pa}` : (s.turn === p && !s.over ? "🤼 …" : "—");
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
    if (!prev || prev.state.turn !== args.state.turn || (prev.state.last || {}).id !== (args.state.last || {}).id) { pending = false; if (mode === "wait") mode = "idle"; idle = null; }
    bar(); decide(); setH();
  });
  window.addEventListener("resize", () => args && setH());
  requestAnimationFrame(frame);
  send("streamlit:componentReady", { apiVersion: 1 });
  // ================= KURES UI соңы =================
