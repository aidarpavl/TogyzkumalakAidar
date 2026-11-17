  // ================= KOKPAR SIM (core/kokpar.py-мен бірдей) =================
  const K = (function () {
    const DT = 0.05, FW = 200.0, FH = 100.0, KR = 3.5, TARGET = [[193.0, 50.0], [7.0, 50.0]], R = 1.2;
    const GRAB_D = 2.2, PULL_D = 2.8, DUEL = 60, GOLDEN = 1200;
    const BASE = { k_speed: 45.0, k_accel: 6.0, k_stamina: 100.0, k_power: 1.0, k_agility: 1.0 };
    const LEVEL = { easy: [12, 0.9, 4.0], medium: [7, 0.95, 5.5], hard: [5, 0.97, 6.5], master: [5, 1.0, 7.5] };
    const pyRound4 = (x) => Math.round(x * 10000) / 10000;
    function aiStats(level) { const f = { easy: 0.94, medium: 1.0, hard: 1.02, master: 1.06 }[level] || 1.0;
      const o = {}; for (const k in BASE) o[k] = pyRound4(BASE[k] * f); return o; }
    function norm(x, y) { const d = Math.sqrt(x * x + y * y); if (d < 1e-9) return [0.0, 0.0, 0.0]; return [x / d, y / d, d]; }

    class Sim {
      constructor(hs, level, periods, periodS, aiSt) {
        this.level = level; const lv = LEVEL[level] || LEVEL.medium, mlv = LEVEL.medium;
        const stAi = aiSt || aiStats(level), stMate = Object.assign({}, BASE);
        this.riders = [];
        for (let i = 0; i < 6; i++) {
          const t = i < 3 ? 0 : 1, st = i === 0 ? hs : (t === 0 ? stMate : stAi), L = t === 0 ? mlv : lv;
          this.riders.push({ t, vmax: st.k_speed / 3.6 * (i === 0 ? 1.0 : L[1]), acc: st.k_accel / 3.6, smax: st.k_stamina,
            pow: st.k_power, agi: st.k_agility, K: L[0], tap: L[2], x: 0.0, y: 0.0, hx: 1.0, hy: 0.0, v: 0.0, s: st.k_stamina,
            whip: 0, cd: 0, stop: 0, fc: 0, dx: 0.0, dy: 0.0, slow: 0, g: 0, p: 0, w: 0 });
        }
        this.score = [0, 0]; this.periodSteps = Math.trunc(periodS / DT); this.periods = periods; this.n = 0;
        this.holder = -1; this.sx = 100.0; this.sy = 50.0; this.duel = null; this.events = []; this.over = false; this.golden = false;
        this.reset();
      }
      reset() {
        this.riders.forEach((r, i) => { const k = i % 3;
          r.x = r.t === 0 ? 70.0 : 130.0; r.y = 35.0 + 15.0 * k; r.hx = r.t === 0 ? 1.0 : -1.0; r.hy = 0.0; r.v = 0.0;
          r.whip = 0; r.cd = 10; r.stop = 0; r.dx = 0.0; r.dy = 0.0; r.slow = 0; });
        this.holder = -1; this.sx = 100.0; this.sy = 50.0; this.duel = null;
      }
      dist(a, x, y) { const dx = x - a.x, dy = y - a.y; return Math.sqrt(dx * dx + dy * dy); }
      go(r, x, y) { const [ux, uy, d] = norm(x - r.x, y - r.y); r.dx = ux; r.dy = uy; return d; }
      ai(i) {
        const r = this.riders[i], t = r.t, G = TARGET[t], D = TARGET[1 - t], h = this.holder;
        r.slow = 0;
        if (h === i) { const d = this.go(r, G[0], G[1]); if (r.s > 50.0 && d < 70.0 && r.whip === 0) r.w = 1; return; }
        const mates = []; for (let j = 0; j < 6; j++) if (this.riders[j].t === t) mates.push(j);
        if (h >= 0 && this.riders[h].t === t) {
          const hr = this.riders[h], [ux, uy] = norm(G[0] - hr.x, G[1] - hr.y), side = mates.indexOf(i) % 2 === 0 ? 1.0 : -1.0;
          this.go(r, hr.x + ux * 8.0 - uy * 6.0 * side, hr.y + uy * 8.0 + ux * 6.0 * side); return;
        }
        const byDist = (x, y) => mates.slice().sort((a, b) => { const da = this.dist(this.riders[a], x, y), db = this.dist(this.riders[b], x, y);
          return da < db ? -1 : da > db ? 1 : a - b; });
        if (h >= 0) {
          const hr = this.riders[h], order = byDist(hr.x, hr.y);
          if (order.indexOf(i) < 2) {
            const d = this.go(r, hr.x + hr.hx * hr.v * 0.4, hr.y + hr.hy * hr.v * 0.4);
            if (d < PULL_D + 0.4 && r.cd === 0) r.p = 1;
            if (d > 25.0 && r.s > 40.0 && r.whip === 0) r.w = 1;
          } else { const [ux, uy] = norm(100.0 - D[0], 50.0 - D[1]); this.go(r, D[0] + ux * 12.0, D[1] + uy * 12.0); }
          return;
        }
        const order = byDist(this.sx, this.sy);
        if (i === order[0]) { const d = this.go(r, this.sx, this.sy); if (d < 10.0) r.slow = 1; if (d < GRAB_D) r.g = 1; }
        else { const side = order.indexOf(i) === 1 ? 1.0 : -1.0, [ux, uy] = norm(G[0] - this.sx, G[1] - this.sy);
          this.go(r, this.sx + ux * 10.0 - uy * 8.0 * side, this.sy + uy * 10.0 + ux * 8.0 * side); }
      }
      step(inputs) {
        const n = this.n, hr = this.riders[0];
        hr.g = 0; hr.p = 0; hr.w = 0;
        for (const ev of inputs) { const k = ev[1];
          if (k === "d") { hr.dx = +ev[2][0]; hr.dy = +ev[2][1]; } else if (k === "w") hr.w = 1; else if (k === "g") hr.g = 1; else if (k === "p") hr.p = 1; }
        for (let i = 1; i < 6; i++) { const r = this.riders[i]; r.g = 0; r.p = 0; r.w = 0;
          if (n % r.K === i % r.K) this.ai(i);
          else if (this.holder >= 0 && this.riders[this.holder].t !== r.t) {
            const d = this.dist(r, this.riders[this.holder].x, this.riders[this.holder].y);
            if (d < PULL_D && r.cd === 0) r.p = 1; } }
        for (let i = 0; i < 6; i++) {
          const r = this.riders[i];
          if (r.w === 1 && r.whip === 0 && r.s >= 8.0 && r.stop === 0) { r.s = r.s - 8.0; r.whip = 20; }
          const vmax = r.vmax; let target;
          if (r.stop > 0) { r.stop = r.stop - 1; target = 0.0; }
          else if ((r.dx === 0.0 && r.dy === 0.0) || r.slow === 1) target = 0.25 * vmax;
          else if (r.whip > 0) target = 1.15 * vmax; else target = 0.85 * vmax;
          if (r.s < 15.0 && target > 0.6 * vmax) target = 0.6 * vmax;
          if (this.holder === i) target = target * 0.92;
          if (this.duel !== null && (this.duel[0] === i || this.duel[1] === i)) target = target * 0.6;
          if (r.v < target) r.v = Math.min(target, r.v + r.acc * DT); else r.v = Math.max(target, r.v - 2.0 * r.acc * DT);
          if (!(r.dx === 0.0 && r.dy === 0.0)) {
            const hx = r.hx + (r.dx - r.hx) * 0.15, hy = r.hy + (r.dy - r.hy) * 0.15, [ux, uy, d] = norm(hx, hy);
            if (d < 1e-6) { r.hx = r.dx; r.hy = r.dy; } else { r.hx = ux; r.hy = uy; } }
          r.x = r.x + r.hx * r.v * DT; r.y = r.y + r.hy * r.v * DT;
          if (r.x < 1.0 || r.x > FW - 1.0 || r.y < 1.0 || r.y > FH - 1.0) {
            r.x = Math.min(FW - 1.0, Math.max(1.0, r.x)); r.y = Math.min(FH - 1.0, Math.max(1.0, r.y)); r.v = r.v * 0.5; }
          if (r.v > 0.7 * vmax) r.s = r.s - 1.0 * DT; else r.s = r.s + 4.0 * DT;
          r.s = Math.min(r.smax, Math.max(0.0, r.s));
          if (r.whip > 0) r.whip = r.whip - 1; if (r.cd > 0) r.cd = r.cd - 1; if (r.fc > 0) r.fc = r.fc - 1;
        }
        for (let i = 0; i < 6; i++) { const a = this.riders[i];
          for (let j = i + 1; j < 6; j++) { const b = this.riders[j];
            const dx = b.x - a.x, dy = b.y - a.y, d2 = dx * dx + dy * dy;
            if (d2 >= 4.0 * R * R || d2 === 0.0) continue;
            const d = Math.sqrt(d2), nx = dx / d, ny = dy / d, o = (2.0 * R - d) / 2.0;
            a.x = a.x - nx * o; a.y = a.y - ny * o; b.x = b.x + nx * o; b.y = b.y + ny * o;
            if (a.t !== b.t && i === 0) {
              const rvx = a.hx * a.v - b.hx * b.v, rvy = a.hy * a.v - b.hy * b.v;
              if (rvx * rvx + rvy * rvy > 324.0) { const f = a;
                if (f.fc === 0 && a.v >= b.v) { f.s = Math.max(0.0, f.s - 30.0); f.stop = 100; f.fc = 140; f.v = f.v * 0.3; this.events.push([n, "foul", 0]); } } } } }
        if (this.holder >= 0) { this.sx = this.riders[this.holder].x; this.sy = this.riders[this.holder].y; }
        else for (let i = 0; i < 6; i++) { const r = this.riders[i];
          if (r.g === 1 && r.cd === 0 && this.holder < 0 && this.dist(r, this.sx, this.sy) < GRAB_D) {
            if (r.v * 3.6 <= 20.0 * r.agi && r.s >= 10.0) { this.holder = i; this.events.push([n, "grab", i]); }
            else { r.s = Math.max(0.0, r.s - 5.0); r.cd = 20; } } }
        if (this.duel === null && this.holder >= 0) { const hrd = this.riders[this.holder];
          for (let i = 0; i < 6; i++) { const r = this.riders[i];
            if (r.p === 1 && r.cd === 0 && r.t !== hrd.t && this.dist(r, hrd.x, hrd.y) < PULL_D) {
              this.duel = [this.holder, i, n + DUEL, 0, 0, n]; this.events.push([n, "duel", i]); r.p = 0; break; } } }
        if (this.duel !== null) { const du = this.duel;
          for (const side of [0, 1]) { const idx = du[side], r = this.riders[idx];
            if (idx === 0) { if (r.p === 1) du[3 + side] = du[3 + side] + 1; }
            else { const per = Math.max(1, Math.trunc(20.0 / r.tap + 0.5)); if ((n - du[5]) % per === 0) du[3 + side] = du[3 + side] + 1; } }
          if (n >= du[2]) { const a = this.riders[du[0]], b = this.riders[du[1]];
            const sa = du[3] * a.pow * (0.5 + 0.5 * a.s / a.smax), sb = du[4] * b.pow * (0.5 + 0.5 * b.s / b.smax);
            let loser; if (sb > sa) { this.holder = du[1]; loser = a; this.events.push([n, "steal", du[1]]); } else { loser = b; this.events.push([n, "keep", du[0]]); }
            loser.s = Math.max(0.0, loser.s - 20.0); loser.cd = 30; this.duel = null; } }
        if (this.holder >= 0) { const hrd = this.riders[this.holder], G = TARGET[hrd.t];
          if (this.dist(hrd, G[0], G[1]) < KR) { this.score[hrd.t] = this.score[hrd.t] + 1; this.events.push([n, "goal", this.holder]); this.reset(); if (this.golden) this.over = true; } }
        this.n = n + 1;
        const total = this.periodSteps * this.periods;
        if (!this.golden && this.n % this.periodSteps === 0 && this.n <= total) {
          this.reset(); if (this.n === total) { if (this.score[0] === this.score[1]) this.golden = true; else this.over = true; } }
        if (this.golden && this.n >= total + GOLDEN) this.over = true;
      }
    }
    return { Sim, DT, TARGET, KR, GRAB_D, PULL_D, GOLDEN, BASE, aiStats };
  })();
  // ================= KOKPAR SIM соңы =================
