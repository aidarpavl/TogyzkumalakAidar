  // ================= KURES SIM (core/kures.py-мен бірдей) =================
  const K = (function () {
    const DT = 0.05, MAT = 4.0, GRIP_D = 1.3, WIND = 8, OPEN = 6, GOLDEN_S = 60;
    const BASIC = ["pull", "push", "rock"];
    const BEATS = { rock: "pull", pull: "push", push: "rock" };
    const COUNTER = {}; for (const k in BEATS) COUNTER[BEATS[k]] = k;
    const THROWS = {
      surin: [10, 6.0, 0.60, 0.55, 0.6, "push"], ilip: [12, 8.0, 0.52, 0.70, 0.7, "pull"],
      burap: [12, 9.0, 0.50, 0.75, 1.2, "push"], zhambas: [14, 10.0, 0.45, 0.85, 0.6, "rock"],
      koter: [18, 14.0, 0.36, 1.05, 0.9, "pull"], arqa: [20, 16.0, 0.30, 1.20, 0.8, "rock"],
    };
    const THROW_ORDER = ["arqa", "koter", "zhambas", "burap", "ilip", "surin"];
    const WEIGHTS = { 60: [0.9, 1.15], 74: [1.0, 1.0], 90: [1.08, 0.93], 100: [1.15, 0.86] };
    const LEVEL = { easy: [8, 26, 4, 3, 0.60], medium: [6, 22, 6, 2, 0.52], hard: [4, 16, 12, 1, 0.50], master: [3, 12, 15, 0, 0.45] };
    const isThrow = (a) => Object.prototype.hasOwnProperty.call(THROWS, a);
    function mult(att, dfn) {
      const winding = dfn.wind > 0;
      if (winding && dfn.act === COUNTER[att]) return -1.0;
      let m = 1.0;
      if (dfn.hold === 1) m = att === "push" ? 1.6 : 0.45;
      if (winding && isThrow(dfn.act)) m = m * 1.3;
      return m;
    }
    class Sim {
      constructor(hs, level, boutS, aiSt, weight) {
        this.level = level; const lv = LEVEL[level] || LEVEL.medium;
        [this.react, this.every, this.notice, this.late, this.patience] = lv;
        const wv = WEIGHTS[Math.trunc(weight)] || WEIGHTS[74], wp = wv[0], ws = wv[1];
        this.p = [hs, aiSt].map((st) => ({ pow: st.w_power * wp, grip: st.w_grip, smax: st.w_stamina, bmax: st.w_balance,
          tech: st.w_technique, spd: st.w_speed * ws, x: 0.0, y: 0.0, dx: 0.0, dy: 0.0, s: st.w_stamina, b: st.w_balance,
          act: "", wind: 0, k: 0, open: 0, hold: 0, cd: 0, hit: 0, adv: 0.0, warn: 0, pts: 0, q: 0.0 }));
        this.boutSteps = Math.trunc(boutS / DT); this.limit = this.boutSteps + Math.trunc(GOLDEN_S / DT);
        this.n = 0; this.grip = false; this.gwant = 0; this.golden = false; this.clean = -1; this.winner = -2;
        this.lastAct = 0; this.closeN = -1; this.hist = []; this.seen = -1; this.events = []; this.over = false;
        this.stand();
      }
      stand() {
        this.p.forEach((r, i) => { r.x = i === 0 ? -1.6 : 1.6; r.y = 0.0; r.dx = 0.0; r.dy = 0.0; r.act = ""; r.wind = 0;
          r.open = 0; r.hold = 0; r.cd = 16; r.b = Math.min(r.bmax, r.b + 30.0); });
        this.grip = false; this.gwant = 0; this.closeN = -1; this.seen = -1; this.lastAct = this.n;
      }
      start(i, act) {
        const r = this.p[i], o = this.p[1 - i];
        if (r.wind > 0 || !this.grip) return;
        if (isThrow(act)) {
          const t = THROWS[act];
          if (r.s < t[1] || o.b >= t[2] * o.bmax) return;
          r.s = r.s - t[1]; r.wind = t[0]; this.events.push([this.n, "tstart", i, act]);
        } else { if (r.s < 5.0) return; r.s = r.s - 5.0; r.wind = WIND; }
        r.act = act; r.k = 0; r.hold = 0;
        if (i === 0) { this.lastAct = this.n; this.hist.push(BASIC.includes(act) ? act : "rock"); if (this.hist.length > 5) this.hist = this.hist.slice(-5); }
      }
      quality(r) {
        const sweet = THROWS[r.act][0] - 4; let d = r.k - sweet; if (d < 0) d = -d;
        const q = 1.0 - d / (4.0 * r.tech); return q < 0.15 ? 0.15 : q;
      }
      resolveThrow(i, q) {
        const a = this.p[i], o = this.p[1 - i], t = THROWS[a.act], name = a.act;
        a.act = ""; a.wind = 0; a.open = OPEN;
        if (o.wind > 0 && o.act === t[5]) { a.b = Math.max(0.0, a.b - 12.0); a.hit = 0; o.pts = o.pts + 1; o.adv = o.adv + 12.0;
          this.events.push([this.n, "tcounter", 1 - i, name]); return; }
        const hm = o.hold === 1 ? t[4] : 1.0;
        const pw = (1.3 * t[3] * a.pow * (0.6 + 0.4 * a.grip) * q * (0.55 + 0.45 * a.s / a.smax) * (1.6 - 1.2 * o.b / o.bmax) * hm);
        const sc = pw >= 1.0 ? 4 : pw >= 0.7 ? 3 : pw >= 0.45 ? 2 : pw >= 0.25 ? 1 : 0;
        this.events.push([this.n, "throw", i, name, sc]);
        if (sc === 0) { a.b = Math.max(0.0, a.b - 10.0); a.hit = 0; return; }
        a.adv = a.adv + pw * 10.0;
        if (sc === 4) { this.clean = i; this.winner = i; return; }
        a.pts = a.pts + sc;
        if (this.golden) { this.winner = i; return; }
        this.stand();
      }
      ai() {
        const a = this.p[1], h = this.p[0], n = this.n;
        if (!this.grip) {
          const ux = h.x - a.x, uy = h.y - a.y, d = Math.sqrt(ux * ux + uy * uy);
          if (d > 1.1) { a.dx = ux / d; a.dy = uy / d; } else { a.dx = 0.0; a.dy = 0.0; }
          if (d < GRIP_D) { if (this.closeN < 0) this.closeN = n; if (n - this.closeN >= this.react) this.gwant = 1; }
          else this.closeN = -1;
          return;
        }
        a.dx = 0.0; a.dy = 0.0;
        if (a.wind > 0 && isThrow(a.act)) { if (a.k >= THROWS[a.act][0] - 4 + this.late) this.resolveThrow(1, this.quality(a)); return; }
        if (h.wind > 0) {
          if (this.seen < 0) this.seen = n;
          if (n - this.seen === this.react && a.wind === 0 && (this.seen * 7 + 3) % 20 < this.notice) {
            const c = isThrow(h.act) ? THROWS[h.act][5] : COUNTER[h.act];
            if (a.s >= 5.0) { this.start(1, c); return; } }
        } else this.seen = -1;
        if (a.wind === 0) {
          a.hold = (a.b < 0.3 * a.bmax && a.s > 12.0) ? 1 : 0;
          if (n % this.every === 0 && a.hold === 0) {
            for (const t of THROW_ORDER) if (THROWS[t][2] <= this.patience && h.b < THROWS[t][2] * h.bmax && a.s >= THROWS[t][1] + 4.0) { this.start(1, t); return; }
            if (a.s < 5.0) return;
            const cnt = { pull: 0, push: 0, rock: 0 }; for (const x of this.hist) cnt[x] = cnt[x] + 1;
            let best = "pull"; if (cnt.push > cnt[best]) best = "push"; if (cnt.rock > cnt[best]) best = "rock";
            let act = this.hist.length >= 3 ? COUNTER[best] : BASIC[Math.floor(n / this.every) % 3];
            if (h.hold === 1) act = "push";
            this.start(1, act);
          }
        }
      }
      step(inputs) {
        const n = this.n, h = this.p[0];
        for (const ev of inputs) { const k = ev[1];
          if (k === "d") { h.dx = +ev[2][0]; h.dy = +ev[2][1]; }
          else if (k === "g") { if (!this.grip) { this.gwant = 1; this.lastAct = n; } }
          else if (k === "a") this.start(0, ev[2]);
          else if (k === "h") h.hold = (ev[2] && h.wind === 0) ? 1 : 0;
          else if (k === "t") { if (h.wind > 0 && isThrow(h.act) && this.winner === -2) this.resolveThrow(0, this.quality(h)); } }
        if (this.winner === -2 && (n % 2 === 0 || this.grip)) this.ai();
        if (this.winner === -2) this.physics(n);
        if (this.winner === -2 && n - this.lastAct > 240) this.warn(n, "passive");
        this.n = n + 1;
        if (this.winner === -2 && !this.golden && this.n >= this.boutSteps) {
          const a = this.p[0].pts, b = this.p[1].pts;
          if (a !== b) this.winner = a > b ? 0 : 1; else { this.golden = true; this.events.push([n, "golden", 0]); } }
        if (this.winner === -2 && this.golden && this.n >= this.limit) {
          const d = this.p[0].adv - this.p[1].adv; this.winner = d > 1.0 ? 0 : (d < -1.0 ? 1 : -1); }
        if (this.winner !== -2) { this.over = true; this.events.push([n, "end", this.winner]); }
      }
      warn(n, why) {
        const h = this.p[0]; h.warn = h.warn + 1; this.lastAct = n; this.events.push([n, "warn", 0, why]);
        if (h.warn >= 2) { h.warn = 0; this.p[1].pts = this.p[1].pts + 1; this.events.push([n, "pen", 1]); if (this.golden) this.winner = 1; }
      }
      physics(n) {
        for (let i = 0; i < 2; i++) { const r = this.p[i];
          if (!this.grip) {
            const sp = (1.6 + 1.2 * r.spd) * DT; r.x = r.x + r.dx * sp; r.y = r.y + r.dy * sp;
            if (r.x > MAT || r.x < -MAT || r.y > MAT || r.y < -MAT) { r.x = r.x * 0.7; r.y = r.y * 0.7;
              if (i === 0) { r.dx = 0.0; r.dy = 0.0; this.warn(n, "out"); } }
            r.s = Math.min(r.smax, r.s + 8.0 * DT); r.b = Math.min(r.bmax, r.b + 6.0 * DT);
          } else {
            if (r.hold === 1) { r.s = Math.max(0.0, r.s - 6.0 * DT); if (r.s <= 0.0) r.hold = 0; }
            else if (r.wind === 0) r.s = Math.min(r.smax, r.s + 4.0 * DT);
            if (r.hit > 40) r.b = Math.min(r.bmax, r.b + 2.0 * DT);
          }
          if (r.cd > 0) r.cd = r.cd - 1; if (r.open > 0) r.open = r.open - 1; r.hit = r.hit + 1;
        }
        if (!this.grip) {
          const dx = this.p[1].x - this.p[0].x, dy = this.p[1].y - this.p[0].y;
          if (this.gwant === 1 && dx * dx + dy * dy < GRIP_D * GRIP_D && this.p[0].cd === 0 && this.p[1].cd === 0) {
            this.grip = true; this.events.push([n, "grip", 0]);
            const mx = (this.p[0].x + this.p[1].x) / 2, my = (this.p[0].y + this.p[1].y) / 2, d = Math.sqrt(dx * dx + dy * dy);
            const ux = d > 1e-9 ? dx / d : 1.0, uy = d > 1e-9 ? dy / d : 0.0;
            this.p[0].x = mx - ux * 0.45; this.p[0].y = my - uy * 0.45; this.p[1].x = mx + ux * 0.45; this.p[1].y = my + uy * 0.45;
          }
          this.gwant = 0; return;
        }
        const res = [];
        for (let i = 0; i < 2; i++) { const r = this.p[i]; if (r.wind > 0) { r.k = r.k + 1; r.wind = r.wind - 1; if (r.wind === 0) res.push(i); } }
        for (const i of res) {
          const a = this.p[i], o = this.p[1 - i];
          if (this.winner !== -2 || !this.grip || a.act === "") continue;
          if (isThrow(a.act)) { this.resolveThrow(i, 0.3); continue; }
          let m = mult(a.act, o);
          if (m < 0) { a.b = Math.max(0.0, a.b - 6.0); a.hit = 0; o.adv = o.adv + 6.0; this.events.push([n, "counter", 1 - i]); }
          else { if (o.open > 0) m = m * 1.5;
            let dmg = 5.0 * a.pow * a.grip * m * (0.5 + 0.5 * a.s / a.smax) - 1.5 * o.tech; if (dmg < 1.0) dmg = 1.0;
            o.b = Math.max(0.0, o.b - dmg); o.hit = 0; a.adv = a.adv + dmg; this.events.push([n, a.act, i]); }
          a.act = ""; a.open = OPEN;
        }
      }
    }
    return { Sim, DT, MAT, THROWS, THROW_ORDER, BASIC, COUNTER, isThrow };
  })();
  // ================= KURES SIM соңы =================
