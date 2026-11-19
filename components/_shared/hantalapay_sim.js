  // ================= HANTALAPAY SIM (core/hantalapay.py-мен бірдей) =================
  const H = (function () {
    const N_ASYK = 11, KHAN = 10, GRAB_MS = 4000, MAX_THROWS = 90, SEAT_R = 1.25, REACH = 220.0;
    const SEATS = { 2: [[0.0, 1.0], [0.0, -1.0]], 3: [[0.0, 1.0], [0.866, -0.5], [-0.866, -0.5]],
      4: [[0.0, 1.0], [1.0, 0.0], [0.0, -1.0], [-1.0, 0.0]],
      5: [[0.0, 1.0], [0.9511, 0.309], [0.5878, -0.809], [-0.5878, -0.809], [-0.9511, 0.309]],
      6: [[0.0, 1.0], [0.866, 0.5], [0.866, -0.5], [0.0, -1.0], [-0.866, -0.5], [-0.866, 0.5]],
      7: [[0.0, 1.0], [0.7818, 0.6235], [0.9749, -0.2225], [0.4339, -0.901], [-0.4339, -0.901], [-0.9749, -0.2225], [-0.7818, 0.6235]] };
    const LEVEL = { easy: [1000, 600, 0.45, 15, 0.40], medium: [780, 480, 0.60, 5, 0.60], hard: [660, 420, 0.72, 0, 0.75], master: [540, 360, 0.82, 0, 0.88] };
    class Rng {
      constructor(seed) { this.x = (seed >>> 0) || 0x9E3779B9; }
      next() { let x = this.x; x = (x ^ (x << 13)) >>> 0; x = (x ^ (x >>> 17)) >>> 0; x = (x ^ (x << 5)) >>> 0; this.x = x; return x / 4294967296.0; }
    }
    const subSeed = (seed, k, salt) => ((seed ^ (((k + 1) * 2654435761) % 4294967296) ^ ((salt * 40503) % 65536)) >>> 0);
    function tri(ms, period) { ms = Math.trunc(ms); if (ms < 0) ms = 0; const ph = (ms % period) / (period / 2); return ph <= 1.0 ? ph : 2.0 - ph; }
    class Game {
      constructor(hs, nAi, level, target, seed, aiSt) {
        this.n = Math.max(2, Math.min(7, Math.trunc(nAi) + 1));
        this.level = LEVEL[level] ? level : "medium"; this.lv = LEVEL[this.level];
        this.target = Math.trunc(target); this.seed = Math.trunc(seed) >>> 0; this.hs = hs; this.ai = aiSt;
        this.seats = SEATS[this.n]; this.scores = new Array(this.n).fill(0); this.k = 0;
        const r = new Rng(subSeed(this.seed, 999, 7)); this.first = Math.trunc(r.next() * this.n) % this.n;
        this.over = false; this.winner = -1; this.events = []; this.out = null; this.flicks = 0; this.left = [];
      }
      turn() { return (this.first + this.k) % this.n; }
      throw(ms) {
        const t = this.turn(), r = new Rng(subSeed(this.seed, this.k, 1));
        let q;
        if (t === 0) { const v = tri(ms != null ? ms : 0, 1600); let d = v - 0.75; if (d < 0) d = -d; q = 1.0 - d / (0.2 * this.hs.h_throw); if (q < 0.0) q = 0.0; }
        else { q = this.lv[4] + (r.next() - 0.5) * 0.3; q = q < 0.0 ? 0.0 : (q > 1.0 ? 1.0 : q); }
        const spread = 0.28 + 0.42 * (1.0 - q), sx = this.seats[t][0], sz = this.seats[t][1], cx = sx * 0.15, cz = sz * 0.15;
        const pos = [], sides = [];
        for (let i = 0; i < N_ASYK; i++) {
          let x, z;
          while (true) { x = (2.0 * r.next() - 1.0) * spread; z = (2.0 * r.next() - 1.0) * spread; if (x * x + z * z <= spread * spread) break; }
          pos.push([cx + x, cz + z]);
          const u = r.next(); let s;
          if (i === KHAN) { const pa = 0.24 + 0.12 * q, rest = 1.0 - pa - 0.03;
            if (u < pa) s = 0; else if (u < pa + 0.015) s = 4; else if (u < pa + 0.03) s = 5;
            else s = u < pa + 0.03 + rest * 0.3 ? 1 : (u < pa + 0.03 + rest * 0.66 ? 2 : 3); }
          else s = u < 0.17 ? 0 : u < 0.34 ? 1 : u < 0.66 ? 2 : u < 0.97 ? 3 : u < 0.985 ? 4 : 5;
          sides.push(s);
        }
        this.out = { k: this.k, t, q, pos, sides, khan: sides[KHAN] };
        this.events.push([this.k, "throw", t, sides[KHAN]]);
        return this.out;
      }
      aiTimes(j) {
        const r = new Rng(subSeed(this.seed, this.k, 10 + j)), sp = this.ai.h_reaction;
        let first = this.lv[0] * (1.0 + (r.next() - 0.5) * 0.9) / sp;
        const gap = this.lv[1] * (1.0 + (r.next() - 0.5) * 0.6) / sp;
        if (this.out.t === j) first = first - 100.0;
        return [first, gap];
      }
      humanEff(ms) { let e = (ms - 150.0 * (this.hs.h_reaction - 1.0)) / (1.0 + 0.3 * (this.hs.h_hands - 1.0)); if (this.out.t === 0) e = e - 100.0; return e; }
      aiPick(j, owner) {
        if (owner[KHAN] < 0) return KHAN;
        let idx = -1, bd = 0.0;
        for (let i = 0; i < N_ASYK; i++) if (owner[i] < 0) { const d = this.reach(j, i); if (idx < 0 || d < bd) { idx = i; bd = d; } }
        return idx;
      }
      reach(j, i) { const sx = this.seats[j][0], sz = this.seats[j][1], p = this.out.pos[i], dx = p[0] - sx * SEAT_R, dz = p[1] - sz * SEAT_R; return REACH * Math.sqrt(dx * dx + dz * dz); }
      talapai(taps, shout) {
        const owner = new Array(N_ASYK).fill(-1), clean = []; let last = -1000;
        const ts = taps.map((a) => [Math.trunc(a[0]), Math.trunc(a[1])]).sort((a, b) => a[0] - b[0]);
        for (const tp of ts) if (tp[0] >= 100 && tp[0] <= GRAB_MS && tp[1] >= 0 && tp[1] < N_ASYK && tp[0] - last >= 110) { clean.push(tp); last = tp[0]; }
        const hq = clean.map((tp) => [this.humanEff(tp[0]) + this.reach(0, tp[1]), tp[1]]);
        const nxt = new Array(this.n).fill(null), gaps = new Array(this.n).fill(0.0);
        for (let j = 1; j < this.n; j++) { const a = this.aiTimes(j); nxt[j] = a[0]; gaps[j] = a[1]; }
        let fs = [null, -1];
        if (shout != null && Math.trunc(shout) >= 100 && Math.trunc(shout) <= GRAB_MS) fs = [this.humanEff(Math.trunc(shout)), 0];
        if (hq.length && (fs[1] < 0 || hq[0][0] < fs[0])) fs = [hq[0][0], 0];
        for (let j = 1; j < this.n; j++) if (fs[1] < 0 || nxt[j] < fs[0]) fs = [nxt[j], j];
        let hi = 0; const order = [];
        while (owner.includes(-1)) {
          let bt = null, bp = -1, bi = -1;
          if (hi < hq.length) { bt = hq[hi][0]; bp = 0; bi = hq[hi][1]; }
          for (let j = 1; j < this.n; j++) {
            if (nxt[j] === null || nxt[j] > GRAB_MS) continue;
            const idx = this.aiPick(j, owner), tj = nxt[j] + this.reach(j, idx);
            if (bt === null || tj < bt) { bt = tj; bp = j; bi = idx; }
          }
          if (bp < 0) break;
          if (bp === 0) hi += 1; else nxt[bp] = nxt[bp] + gaps[bp] + this.reach(bp, bi);
          if (owner[bi] < 0) { owner[bi] = bp; order.push([bt, bp, bi]); }
        }
        for (let i = 0; i < N_ASYK; i++) if (owner[i] >= 0) this.scores[owner[i]] += i === KHAN ? 5 : 1;
        if (fs[1] >= 0) this.scores[fs[1]] += 1;
        this.events.push([this.k, "talapai", owner, fs[1]]);
        this.out.owner = owner; this.out.order = order; this.out.shout = fs[1];
        return owner;
      }
      falseStarts(human) {
        const bad = []; if (human) bad.push(0);
        const r = new Rng(subSeed(this.seed, this.k, 3));
        for (let j = 1; j < this.n; j++) if (r.next() * 100.0 < this.lv[3]) bad.push(j);
        for (const p of bad) this.scores[p] = Math.max(0, this.scores[p] - 2);
        if (bad.length) this.events.push([this.k, "false", bad]);
        this.out.false = bad; return bad;
      }
      flickStart() { this.flicks = 0; this.left = []; for (let i = 0; i < N_ASYK; i++) this.left.push(i); this.out.flicks = []; }
      flick(ms) {
        const t = this.out.t, r = new Rng(subSeed(this.seed, this.k, 20 + this.flicks));
        let q;
        if (t === 0) { if (ms == null) q = 0.0; else { const v = tri(ms, 1200); let d = v - 0.5; if (d < 0) d = -d; q = 1.0 - d / (0.12 * this.hs.h_aim); if (q < 0.0) q = 0.0; } }
        else q = this.lv[2] + (r.next() - 0.5) * 0.3;
        const thr = 0.3 + 0.5 * r.next(), hit = q >= thr && this.left.length >= 2;
        this.flicks += 1;
        if (hit) { const a = this.left[0], b = this.left[1]; this.left = this.left.slice(2);
          this.scores[t] += (a === KHAN ? 5 : 1) + (b === KHAN ? 5 : 1); this.out.flicks.push([a, b]); }
        else this.out.flicks.push(null);
        return hit && this.left.length >= 2 && this.flicks < 5;
      }
      special() { const t = this.out.t, pts = this.out.khan === 4 ? 15 : 5; this.scores[t] += pts;
        this.events.push([this.k, "special", t, this.out.khan]); this.out.special = pts; return pts; }
      endThrow() {
        this.k += 1;
        const best = Math.max(...this.scores);
        if (best >= this.target || this.k >= MAX_THROWS) {
          this.over = true; const tops = []; for (let i = 0; i < this.n; i++) if (this.scores[i] === best) tops.push(i);
          this.winner = tops.length === 1 ? tops[0] : -1; this.events.push([this.k, "end", this.winner]);
        }
      }
    }
    function run(hs, nAi, level, target, seed, inputs, aiSt) {
      const g = new Game(hs, nAi, level, target, seed, aiSt), by = {};
      for (const e of inputs) (by[e[0]] = by[e[0]] || []).push(e);
      while (!g.over) {
        const evs = by[g.k] || [], t = g.turn();
        const pe = evs.find((e) => e[1] === "p"), out = g.throw(t === 0 && pe ? pe[2] : null);
        const taps = evs.filter((e) => e[1] === "g").map((e) => e[2]), se = evs.find((e) => e[1] === "s");
        if (out.khan === 0) g.talapai(taps, se ? se[2] : null);
        else {
          g.falseStarts(taps.length > 0 || !!se);
          if (out.khan >= 4) g.special();
          if (out.khan === 1) { g.flickStart(); const fl = evs.filter((e) => e[1] === "f").map((e) => e[2]); let i = 0;
            while (true) { const ms = (t === 0 && i < fl.length) ? fl[i] : null; i++; if (!g.flick(ms)) break; } }
        }
        g.endThrow();
      }
      return g;
    }
    return { Game, run, tri, N_ASYK, KHAN, GRAB_MS, SEATS, SEAT_R, LEVEL };
  })();
  // ================= HANTALAPAY SIM соңы =================
