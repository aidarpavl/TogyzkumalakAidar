  // ================= AUDARYSPAK SIM (core/audaryspak.py-мен бірдей) =================
  const A = (function () {
    const DT = 0.05, ARENA = 20.0, GRIP_D = 2.2, WIND = 10, OPEN = 6;
    const BASE = { a_stability: 1.0, a_agility: 1.0, a_stamina: 100.0, a_power: 1.0, a_grip: 1.0, a_balance: 100.0 };
    const LEVEL = { easy: [8, 30, 4], medium: [5, 22, 8], hard: [4, 18, 12], master: [3, 14, 15] };
    const COUNTER = { pull: "twist", push: "pull", twist: "push" };
    function mult(att, dfn) {
      const dact = dfn.act, winding = dfn.wind > 0;
      if (att === "pull") { if (winding && dact === "twist") return -1.0; if (dfn.hold === 1) return 0.4; return 1.0; }
      if (att === "push") { if (winding && dact === "pull") return -1.0; if (dfn.hold === 1) return 1.6; return 1.0; }
      if (winding && dact === "push") return -1.0;
      if (winding && dact === "pull") return 1.5;
      if (dfn.hold === 1) return 0.5;
      return 1.0;
    }
    class Sim {
      constructor(hs, level, roundS, aiSt) {
        this.level = level; const lv = LEVEL[level] || LEVEL.medium;
        this.react = lv[0]; this.every = lv[1]; this.notice = lv[2];
        this.p = [hs, aiSt].map((st) => ({ stab: st.a_stability, agi: st.a_agility, smax: st.a_stamina, pow: st.a_power, grip: st.a_grip,
          bmax: st.a_balance, x: 0.0, y: 0.0, dx: 0.0, dy: 0.0, s: st.a_stamina, b: st.a_balance, act: "", wind: 0, open: 0, hold: 0,
          cd: 0, hit: 0, adv: 0.0, warn: 0 }));
        this.roundSteps = Math.trunc(roundS / DT); this.round = 1; this.rounds = [0, 0]; this.n = 0; this.rn = 0;
        this.grip = false; this.hist = []; this.seen = -1; this.events = []; this.over = false; this.reset();
      }
      reset() {
        this.p.forEach((r, i) => { r.x = i === 0 ? -8.0 : 8.0; r.y = 0.0; r.dx = 0.0; r.dy = 0.0; r.s = r.smax; r.b = r.bmax;
          r.act = ""; r.wind = 0; r.open = 0; r.hold = 0; r.cd = 10; r.hit = 0; r.warn = 0; });
        this.grip = false; this.rn = 0; this.seen = -1;
      }
      start(i, act) {
        const r = this.p[i];
        if (r.wind > 0 || r.s < 6.0 || !this.grip) return;
        r.s = r.s - 6.0; r.act = act; r.wind = WIND;
        if (i === 0) { this.hist.push(act); if (this.hist.length > 5) this.hist = this.hist.slice(-5); }
      }
      disengage(i) {
        const r = this.p[i], o = this.p[1 - i];
        if (!this.grip || r.cd > 0 || r.s < 10.0) return;
        r.s = r.s - 10.0; r.cd = 80;
        if (r.agi * r.s >= 0.6 * o.grip * o.s) { this.grip = false; r.x = r.x <= o.x ? r.x - 3.0 : r.x + 3.0; o.act = ""; o.wind = 0; this.events.push([this.n, "free", i]); }
      }
      ai() {
        const a = this.p[1], h = this.p[0], n = this.rn;
        if (!this.grip) { const ux = h.x - a.x, uy = h.y - a.y, d = Math.sqrt(ux * ux + uy * uy); if (d > 1e-9) { a.dx = ux / d; a.dy = uy / d; } return; }
        a.dx = 0.0; a.dy = 0.0;
        if (h.wind > 0) {
          if (this.seen < 0) this.seen = n;
          if (n - this.seen === this.react && a.wind === 0 && (this.seen * 7 + 3) % 20 < this.notice) {
            const c = COUNTER[h.act]; if (a.s >= 6.0) { this.start(1, c); return; } }
        } else this.seen = -1;
        if (a.wind === 0) {
          a.hold = (a.b < 0.35 * a.bmax && a.s > 12.0) ? 1 : 0;
          if (n % this.every === 0 && a.s >= 6.0 && a.hold === 0) {
            const cnt = { pull: 0, push: 0, twist: 0 }; for (const x of this.hist) cnt[x] = cnt[x] + 1;
            let best = "pull"; if (cnt.push > cnt[best]) best = "push"; if (cnt.twist > cnt[best]) best = "twist";
            let act = this.hist.length >= 3 ? COUNTER[best] : ["pull", "push", "twist"][Math.floor(n / this.every) % 3];
            if (h.hold === 1) act = "push";
            this.start(1, act);
          }
        }
      }
      step(inputs) {
        const n = this.n, h = this.p[0];
        for (const ev of inputs) { const k = ev[1];
          if (k === "d") { h.dx = +ev[2][0]; h.dy = +ev[2][1]; } else if (k === "a") this.start(0, ev[2]);
          else if (k === "h") h.hold = ev[2] ? 1 : 0; else if (k === "x") this.disengage(0); }
        if (n % 2 === 0 || this.grip) this.ai();
        for (let i = 0; i < 2; i++) { const r = this.p[i];
          if (!this.grip) {
            const sp = (5.0 + 2.0 * r.agi) * DT; r.x = r.x + r.dx * sp; r.y = r.y + r.dy * sp;
            const d = Math.sqrt(r.x * r.x + r.y * r.y);
            if (d > ARENA) { r.x = r.x / d * (ARENA - 0.5); r.y = r.y / d * (ARENA - 0.5);
              if (i === 0) { r.warn = r.warn + 1; this.events.push([n, "warn", 0]); r.dx = 0.0; r.dy = 0.0; } }
            r.s = Math.min(r.smax, r.s + 10.0 * DT); r.b = Math.min(r.bmax, r.b + 4.0 * DT);
          } else {
            if (r.hold === 1) { r.s = Math.max(0.0, r.s - 6.0 * DT); if (r.s <= 0.0) r.hold = 0; }
            else if (r.wind === 0) r.s = Math.min(r.smax, r.s + 5.0 * DT);
            if (r.hit > 40) r.b = Math.min(r.bmax, r.b + 1.5 * DT);
          }
          if (r.cd > 0) r.cd = r.cd - 1; if (r.open > 0) r.open = r.open - 1; r.hit = r.hit + 1;
        }
        if (!this.grip) { const dx = this.p[1].x - this.p[0].x, dy = this.p[1].y - this.p[0].y;
          if (dx * dx + dy * dy < GRIP_D * GRIP_D && this.p[0].cd === 0 && this.p[1].cd === 0) { this.grip = true; this.events.push([n, "grip", 0]); } }
        if (this.grip) {
          const res = [];
          for (let i = 0; i < 2; i++) { const r = this.p[i]; if (r.wind > 0) { r.wind = r.wind - 1; if (r.wind === 0) res.push(i); } }
          for (const i of res) { const a = this.p[i], o = this.p[1 - i]; let m = mult(a.act, o);
            if (m < 0) { const dmg = 6.0; a.b = Math.max(0.0, a.b - dmg); a.hit = 0; o.adv = o.adv + dmg; this.events.push([n, "counter", 1 - i]); }
            else { if (o.open > 0) m = m * 1.5;
              let dmg = 7.0 * a.pow * a.grip * m * (0.5 + 0.5 * a.s / a.smax) - 2.0 * o.stab; if (dmg < 1.0) dmg = 1.0;
              o.b = Math.max(0.0, o.b - dmg); o.hit = 0; a.adv = a.adv + dmg; this.events.push([n, a.act, i]); }
            a.act = ""; a.open = OPEN; }
        }
        let winner = -2;
        for (let i = 0; i < 2; i++) if (this.p[i].b <= 0.0) { winner = 1 - i; this.events.push([n, "fall", i]); }
        if (winner === -2 && this.p[0].warn >= 2) { winner = 1; this.events.push([n, "out", 0]); }
        this.n = n + 1; this.rn = this.rn + 1;
        if (winner === -2 && this.rn >= this.roundSteps) {
          const b0 = this.p[0].b / this.p[0].bmax, b1 = this.p[1].b / this.p[1].bmax;
          winner = b0 - b1 > 0.05 ? 0 : (b1 - b0 > 0.05 ? 1 : -1); this.events.push([n, "time", winner]); }
        if (winner !== -2) {
          if (winner >= 0) this.rounds[winner] = this.rounds[winner] + 1;
          if (this.rounds[0] >= 2 || this.rounds[1] >= 2 || this.round >= 3) this.over = true;
          else { this.round = this.round + 1; this.reset(); }
          this.lastRound = { winner, n };
        }
      }
    }
    return { Sim, DT, ARENA, WIND, BASE };
  })();
  // ================= AUDARYSPAK SIM соңы =================
