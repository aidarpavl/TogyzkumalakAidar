"""Ханталапай — 11 асық (10 қарапайым + 1 «Хан»), ойыншылар киіз үстінде шеңбер құрып отырады.

Детерминистік модель: өз PRNG (xorshift32, seed-тен), тригонометриясыз — JS-те дәл қайталанады
(components/_shared/hantalapay_sim.js). 0 — ойыншы (адам), 1..N-1 — ИИ.

Бір лақтыру (k):
  1) шашу — күш жолағы (үшбұрышты толқын, 1600 мс); ойыншы басқан сәт (мс) → дәлдік q;
  2) Хан АЛШЫ түссе — «ТАЛАПАЙ!»: бәрі асықты таласып жинайды (уақыт бойынша кім бұрын);
     қарапайым асық = 1 ұпай, Хан = 5 ұпай, бірінші айқайлаған = +1 ұпай;
  3) Хан алшы ЕМЕС, бірақ біреу айқайлап/асыққа ұмтылса — «асығыс»: −2 ұпай;
  4) Хан ТӘЙКЕ түссе — лақтырушы «сырту» жасайды: дәлдік жолағы (1200 мс), тисе — 2 асық (+2, Ханмен +6),
     қатесе — кезек ауысады;
  5) Хан БҮК/ШІК түссе — кезек келесіге.
Ойын келісілген ұпайға (50/80/100) дейін немесе 90 лақтыруға дейін.

Енгізу (тек ойыншының): [k, "p", мс] | [k, "s", мс] | [k, "g", [мс, асық]] | [k, "f", мс]
"""
from __future__ import annotations

import copy
import math

M32 = 0xFFFFFFFF
N_ASYK = 11
KHAN = 10
GRAB_MS = 4000
MAX_THROWS = 90
SIDES = ("alshy", "taike", "buk", "shik", "ompy", "shonkai")   # 4, 5 — сирек тік қалыптар
SEATS = {2: [[0.0, 1.0], [0.0, -1.0]],
         3: [[0.0, 1.0], [0.866, -0.5], [-0.866, -0.5]],
         4: [[0.0, 1.0], [1.0, 0.0], [0.0, -1.0], [-1.0, 0.0]],
         5: [[0.0, 1.0], [0.9511, 0.309], [0.5878, -0.809], [-0.5878, -0.809], [-0.9511, 0.309]],
         6: [[0.0, 1.0], [0.866, 0.5], [0.866, -0.5], [0.0, -1.0], [-0.866, -0.5], [-0.866, 0.5]],
         7: [[0.0, 1.0], [0.7818, 0.6235], [0.9749, -0.2225], [0.4339, -0.901], [-0.4339, -0.901],
             [-0.9749, -0.2225], [-0.7818, 0.6235]]}
SEAT_R = 1.25

BASE = {"h_reaction": 1.0, "h_hands": 1.0, "h_aim": 1.0, "h_throw": 1.0}
STATS = ("h_reaction", "h_hands", "h_aim", "h_throw")
# ИИ: (реакция мс, асықтар арасы мс, сырту дәлдігі, асығыс %, шашу дәлдігі)
LEVEL = {"easy": (1000, 600, 0.45, 15, 0.40), "medium": (780, 480, 0.60, 5, 0.60),
         "hard": (660, 420, 0.72, 0, 0.75), "master": (540, 360, 0.82, 0, 0.88)}
REACH = 220.0     # қол созу: мс / метр (орыннан асыққа дейін)


def stats_from_mult(m: dict) -> dict:
    return {k: round(BASE[k] * float(m.get(k, 1.0) or 1.0), 4) for k in STATS}


def ai_stats(level: str) -> dict:
    f = {"easy": 0.94, "medium": 1.0, "hard": 1.03, "master": 1.07}.get(level, 1.0)
    return {k: round(BASE[k] * f, 4) for k in STATS}


class Rng:
    def __init__(self, seed: int):
        self.x = (seed & M32) or 0x9E3779B9

    def next(self) -> float:
        x = self.x
        x ^= (x << 13) & M32
        x ^= x >> 17
        x ^= (x << 5) & M32
        self.x = x & M32
        return self.x / 4294967296.0


def sub_seed(seed: int, k: int, salt: int) -> int:
    return (seed ^ (((k + 1) * 2654435761) % 4294967296) ^ ((salt * 40503) % 65536)) & M32


def tri(ms, period):
    """Үшбұрышты толқын 0..1..0 (мс бойынша)."""
    ms = int(ms)
    if ms < 0:
        ms = 0
    ph = (ms % period) / (period / 2)
    return ph if ph <= 1.0 else 2.0 - ph


class Game:
    def __init__(self, hs: dict, n_ai: int = 3, level: str = "medium", target: int = 50, seed: int = 1,
                 ai_st: dict | None = None):
        self.n = max(2, min(7, int(n_ai) + 1))
        self.level = level if level in LEVEL else "medium"
        self.lv = LEVEL[self.level]
        self.target = int(target)
        self.seed = int(seed) & M32
        self.hs = hs
        self.ai = ai_st or ai_stats(self.level)
        self.seats = SEATS[self.n]
        self.scores = [0] * self.n
        self.k = 0
        r = Rng(sub_seed(self.seed, 999, 7))
        self.first = int(r.next() * self.n) % self.n          # жеребе
        self.over = False
        self.winner = -1
        self.events = []
        self.out = None          # ағымдағы лақтыру нәтижесі
        self.flicks = 0
        self.left = []

    def turn(self) -> int:
        return (self.first + self.k) % self.n

    # ---------------------------------------------------------------- шашу
    def throw(self, ms) -> dict:
        t = self.turn()
        r = Rng(sub_seed(self.seed, self.k, 1))
        if t == 0:
            v = tri(ms if ms is not None else 0, 1600)
            d = v - 0.75
            if d < 0:
                d = -d
            q = 1.0 - d / (0.2 * self.hs["h_throw"])
            if q < 0.0:
                q = 0.0
        else:
            q = self.lv[4] + (r.next() - 0.5) * 0.3
            q = 0.0 if q < 0.0 else (1.0 if q > 1.0 else q)
        spread = 0.28 + 0.42 * (1.0 - q)
        sx, sz = self.seats[t]
        cx, cz = sx * 0.15, sz * 0.15          # лақтырушыға сәл жақын
        pos, sides = [], []
        for i in range(N_ASYK):
            while True:
                x = (2.0 * r.next() - 1.0) * spread
                z = (2.0 * r.next() - 1.0) * spread
                if x * x + z * z <= spread * spread:
                    break
            pos.append([cx + x, cz + z])
            u = r.next()
            if i == KHAN:
                pa = 0.24 + 0.12 * q
                rest = 1.0 - pa - 0.03
                if u < pa:
                    s = 0
                elif u < pa + 0.015:
                    s = 4
                elif u < pa + 0.03:
                    s = 5
                else:
                    s = 1 if u < pa + 0.03 + rest * 0.3 else (2 if u < pa + 0.03 + rest * 0.66 else 3)
            else:
                s = (0 if u < 0.17 else 1 if u < 0.34 else 2 if u < 0.66 else 3 if u < 0.97 else 4 if u < 0.985 else 5)
            sides.append(s)
        self.out = {"k": self.k, "t": t, "q": q, "pos": pos, "sides": sides, "khan": sides[KHAN]}
        self.events.append([self.k, "throw", t, sides[KHAN]])
        return self.out

    # ---------------------------------------------------------------- талапай
    def ai_times(self, j):
        """j-ші ИИ: (бірінші ұмтылу мс, аралық мс)."""
        r = Rng(sub_seed(self.seed, self.k, 10 + j))
        sp = self.ai["h_reaction"]
        first = self.lv[0] * (1.0 + (r.next() - 0.5) * 0.9) / sp
        gap = self.lv[1] * (1.0 + (r.next() - 0.5) * 0.6) / sp
        if self.out["t"] == j:
            first = first - 100.0
        return first, gap

    def human_eff(self, ms) -> float:
        e = (float(ms) - 150.0 * (self.hs["h_reaction"] - 1.0)) / (1.0 + 0.3 * (self.hs["h_hands"] - 1.0))
        if self.out["t"] == 0:
            e = e - 100.0
        return e

    def ai_pick(self, j, owner) -> int:
        if owner[KHAN] < 0:
            return KHAN
        idx, bd = -1, 0.0
        for i in range(N_ASYK):
            if owner[i] < 0:
                d = self.reach(j, i)
                if idx < 0 or d < bd:
                    idx, bd = i, d
        return idx

    def reach(self, j, i) -> float:
        sx, sz = self.seats[j]
        px, pz = self.out["pos"][i]
        dx, dz = px - sx * SEAT_R, pz - sz * SEAT_R
        return REACH * math.sqrt(dx * dx + dz * dz)

    def talapai(self, taps, shout) -> list:
        """Асықтарды бөлу. taps — [[мс, асық], ...], shout — мс немесе None. Қайтарады: owner[11]."""
        owner = [-1] * N_ASYK
        clean, last = [], -1000
        for tp in sorted([[int(a[0]), int(a[1])] for a in taps], key=lambda a: a[0]):
            if 100 <= tp[0] <= GRAB_MS and 0 <= tp[1] < N_ASYK and tp[0] - last >= 110:
                clean.append(tp)
                last = tp[0]
        hq = [[self.human_eff(tp[0]) + self.reach(0, tp[1]), tp[1]] for tp in clean]
        nxt = [None] * self.n
        gaps = [0.0] * self.n
        for j in range(1, self.n):
            nxt[j], gaps[j] = self.ai_times(j)
        first_shout = [None, -1]            # (уақыт, ойыншы)
        if shout is not None and 100 <= int(shout) <= GRAB_MS:
            first_shout = [self.human_eff(int(shout)), 0]
        if hq and (first_shout[1] < 0 or hq[0][0] < first_shout[0]):
            first_shout = [hq[0][0], 0]
        for j in range(1, self.n):
            if first_shout[1] < 0 or nxt[j] < first_shout[0]:
                first_shout = [nxt[j], j]
        hi = 0
        order = []
        while -1 in owner:
            # әр ИИ-дің келесі ұмтылысы: нысана + жету уақыты
            best_t, best_p, best_i = None, -1, -1
            if hi < len(hq):
                best_t, best_p, best_i = hq[hi][0], 0, hq[hi][1]
            for j in range(1, self.n):
                if nxt[j] is None or nxt[j] > GRAB_MS:
                    continue
                idx = self.ai_pick(j, owner)
                tj = nxt[j] + self.reach(j, idx)
                if best_t is None or tj < best_t:
                    best_t, best_p, best_i = tj, j, idx
            if best_p < 0:
                break
            if best_p == 0:
                hi += 1
            else:
                nxt[best_p] = nxt[best_p] + gaps[best_p] + self.reach(best_p, best_i)
            if owner[best_i] < 0:
                owner[best_i] = best_p
                order.append([best_t, best_p, best_i])
        for i in range(N_ASYK):
            if owner[i] >= 0:
                self.scores[owner[i]] += 5 if i == KHAN else 1
        if first_shout[1] >= 0:
            self.scores[first_shout[1]] += 1
        self.events.append([self.k, "talapai", owner, first_shout[1]])
        self.out["owner"] = owner
        self.out["order"] = order
        self.out["shout"] = first_shout[1]
        return owner

    def false_starts(self, human: bool) -> list:
        """Хан алшы емес — асыққандар −2."""
        bad = []
        if human:
            bad.append(0)
        r = Rng(sub_seed(self.seed, self.k, 3))
        for j in range(1, self.n):
            if r.next() * 100.0 < self.lv[3]:
                bad.append(j)
        for p in bad:
            self.scores[p] = max(0, self.scores[p] - 2)
        if bad:
            self.events.append([self.k, "false", bad])
        self.out["false"] = bad
        return bad

    # ---------------------------------------------------------------- сырту
    def flick_start(self):
        self.flicks = 0
        self.left = list(range(N_ASYK))
        self.out["flicks"] = []

    def flick(self, ms) -> bool:
        """Бір сырту. Тисе — True (2 асық алынады)."""
        t = self.out["t"]
        r = Rng(sub_seed(self.seed, self.k, 20 + self.flicks))
        if t == 0:
            if ms is None:
                q = 0.0
            else:
                v = tri(ms, 1200)
                d = v - 0.5
                if d < 0:
                    d = -d
                q = 1.0 - d / (0.12 * self.hs["h_aim"])
                if q < 0.0:
                    q = 0.0
        else:
            q = self.lv[2] + (r.next() - 0.5) * 0.3
        thr = 0.3 + 0.5 * r.next()
        hit = q >= thr and len(self.left) >= 2
        self.flicks += 1
        if hit:
            a, b = self.left[0], self.left[1]
            self.left = self.left[2:]
            self.scores[t] += (5 if a == KHAN else 1) + (5 if b == KHAN else 1)
            self.out["flicks"].append([a, b])
        else:
            self.out["flicks"].append(None)
        return hit and len(self.left) >= 2 and self.flicks < 5

    def special(self) -> int:
        """Хан тік тұрып қалды: ОМПЫ — шашқан барлық асықты алады (+15), ШОҢҚАЙ — Ханды алады (+5)."""
        t = self.out["t"]
        pts = 15 if self.out["khan"] == 4 else 5
        self.scores[t] += pts
        self.events.append([self.k, "special", t, self.out["khan"]])
        self.out["special"] = pts
        return pts

    # ---------------------------------------------------------------- лақтыру соңы
    def end_throw(self):
        self.k += 1
        best = max(self.scores)
        if best >= self.target or self.k >= MAX_THROWS:
            self.over = True
            tops = [i for i in range(self.n) if self.scores[i] == best]
            self.winner = tops[0] if len(tops) == 1 else -1
            self.events.append([self.k, "end", self.winner])


def run(hs, n_ai, level, target, seed, inputs, ai_st=None) -> Game:
    g = Game(hs, n_ai, level, target, seed, ai_st)
    by = {}
    for ev in inputs:
        by.setdefault(int(ev[0]), []).append(ev)
    while not g.over:
        evs = by.get(g.k, [])
        t = g.turn()
        pm = next((e[2] for e in evs if e[1] == "p"), None)
        out = g.throw(pm if t == 0 else None)
        taps = [e[2] for e in evs if e[1] == "g"]
        shout = next((e[2] for e in evs if e[1] == "s"), None)
        if out["khan"] == 0:
            g.talapai(taps, shout)
        else:
            g.false_starts(bool(taps) or shout is not None)
            if out["khan"] >= 4:
                g.special()
            if out["khan"] == 1:
                g.flick_start()
                fl = [e[2] for e in evs if e[1] == "f"]
                i = 0
                while True:
                    ms = fl[i] if (t == 0 and i < len(fl)) else None
                    i += 1
                    if not g.flick(ms):
                        break
        g.end_throw()
    return g


def clean_inputs(inputs) -> list:
    out = []
    for ev in list(inputs)[:6000]:
        try:
            k, kind = int(ev[0]), str(ev[1])
        except (TypeError, ValueError, IndexError):
            continue
        if not (0 <= k < MAX_THROWS):
            continue
        try:
            if kind in ("p", "s", "f"):
                v = int(ev[2])
                if 0 <= v <= 60000:
                    out.append([k, kind, v])
            elif kind == "g":
                ms, idx = int(ev[2][0]), int(ev[2][1])
                if 0 <= ms <= 60000 and 0 <= idx < N_ASYK:
                    out.append([k, "g", [ms, idx]])
        except (TypeError, ValueError, IndexError):
            continue
    return out


# ---------------------------------------------------------------- ойын күйі

def new_state(opts: dict | None = None) -> dict:
    opts = opts or {}
    import secrets
    tg = int(opts.get("target", 50))
    na = int(opts.get("n_ai", 3))
    return {"game": "hantalapay", "stats": opts.get("stats") or [dict(BASE), dict(BASE)],
            "level": opts.get("level", "medium"), "target": tg if tg in (50, 80, 100) else 50,
            "n_ai": max(1, min(6, na)), "seed": int(opts.get("seed", secrets.randbelow(2 ** 31) + 1)),
            "solo": False, "inputs": [None, None], "rides": [None, None], "turn": 0, "over": False,
            "winner": None, "reason": None, "moves": [], "last": None}


def clone(s):
    return copy.deepcopy(s)


def legal_moves(s):
    return [] if s["over"] else ["play"]


def _key(r):
    return (r["win"], r["score"] - r["best"], r["score"])


def apply_move(s: dict, mv: dict) -> dict:
    if s["over"]:
        raise ValueError("game over")
    p = s["turn"]
    inp = clean_inputs(mv.get("inputs", []))
    g = run(s["stats"][p], s["n_ai"], s["level"], s["target"], s["seed"], inp, s.get("ai_stats"))
    best = max(g.scores[1:])
    win = 1 if g.winner == 0 else (0 if g.winner > 0 else (1 if g.scores[0] > best else 0))
    s["inputs"][p] = inp
    s["rides"][p] = {"win": win, "score": g.scores[0], "best": best, "scores": g.scores, "throws": g.k}
    s["moves"].append(f"{'⚪⚫'[p]} {g.scores[0]}:{best}")
    s["last"] = {"player": p, "id": len(s["moves"])}
    s["reason"] = "score"
    if s["solo"]:
        s["over"] = True
        s["winner"] = p if win == 1 else 1 - p
        return s
    if s["rides"][1 - p] is None:
        s["turn"] = 1 - p
        return s
    s["over"] = True
    ka, kb = _key(s["rides"][0]), _key(s["rides"][1])
    s["winner"] = 0 if ka > kb else 1 if kb > ka else -1
    return s


def play(s, mv):
    return apply_move(clone(s), mv)


def score(s) -> list[int]:
    if s.get("solo"):
        for p, r in enumerate(s["rides"]):
            if r:
                out = [0, 0]
                out[p] = r["score"]
                out[1 - p] = r["best"]
                return out
        return [0, 0]
    return [(r or {}).get("score", 0) for r in s["rides"]]


def demo_inputs(hs, n_ai, level, target, seed, skill: str = "medium", ai_st=None) -> list:
    """Сынақ «боты»: берілген деңгейдегі адамның реакциясымен ойнайды."""
    react = {"easy": 720, "medium": 580, "hard": 470, "master": 400}[skill]
    gapms = {"easy": 470, "medium": 400, "hard": 340, "master": 290}[skill]
    pms = {"easy": 1350, "medium": 1250, "hard": 1210, "master": 1200}[skill]     # күш жолағы (v≈0.75 → 600/1000 мс)
    fms = {"easy": 640, "medium": 620, "hard": 608, "master": 600}[skill]
    g = Game(hs, n_ai, level, target, seed, ai_st)
    out = []
    while not g.over:
        k, t = g.k, g.turn()
        if t == 0:
            out.append([k, "p", pms])
        o = g.throw(pms if t == 0 else None)
        if o["khan"] == 0:
            # жақын асықтардан бастап, Ханды бірінші
            order = [KHAN] + sorted(range(10), key=lambda i: (o["pos"][i][0]) ** 2 + (o["pos"][i][1] - SEAT_R) ** 2)
            rr = Rng(sub_seed(seed, k, 77))
            r0 = int(react * (0.6 + 0.8 * rr.next()))
            taps = [[r0 + i * int(gapms * (0.7 + 0.6 * rr.next())), idx] for i, idx in enumerate(order)]
            out += [[k, "g", tp] for tp in taps]
            g.talapai(taps, None)
        else:
            g.false_starts(False)
            if o["khan"] >= 4:
                g.special()
            if o["khan"] == 1:
                g.flick_start()
                while True:
                    ms = fms if t == 0 else None
                    if t == 0:
                        out.append([k, "f", ms])
                    if not g.flick(ms):
                        break
        g.end_throw()
    return out
