"""Көкпар — ат үстінде серке тартысу (3 × 3).

Детерминистік модель (DT = 0.05 с): тригонометрия жоқ, тек + − × ÷ және sqrt — JS-те дәл қайталанады
(components/kokpar/index.html). Ойыншы 0-нөмірлі шабандозды басқарады (А командасы), қалғаны — ИИ.
Клиент тек енгізу журналын жібереді: [қадам, түр, мән]; сервер бүкіл матчты қайта есептейді.

Енгізу түрлері: "d" — бағыт [dx, dy] (бірлік вектор, 3 таңбаға дейін) немесе [0, 0] (тежеу),
"w" — қамшы, "g" — серкені іліп алу, "p" — тарту (тартыста — әр басу бір рет саналады).
"""
from __future__ import annotations

import copy
import math

DT = 0.05
FW, FH = 200.0, 100.0
KR = 3.5                       # қазан радиусы
TARGET = [[193.0, 50.0], [7.0, 50.0]]   # команда t серкені осы қазанға салады
R = 1.2                        # шабандоз радиусы
GRAB_D, PULL_D = 2.2, 2.8
DUEL = 60                      # тартыс ұзақтығы (3 с)
GOLDEN = 1200                  # алтын гол уақыты (60 с)

BASE = {"k_speed": 45.0, "k_accel": 6.0, "k_stamina": 100.0, "k_power": 1.0, "k_agility": 1.0}
STATS = ("k_speed", "k_accel", "k_stamina", "k_power", "k_agility")
HORSE_STATS = ("k_speed", "k_accel", "k_stamina")
RIDER_STATS = ("k_power", "k_agility")

LEVEL = {  # шешім жиілігі (қадам), жылдамдық коэф., тартыс жиілігі (басу/с)
    "easy": (12, 0.9, 4.0), "medium": (7, 0.95, 5.5), "hard": (5, 0.97, 6.5), "master": (5, 1.0, 7.5)}


def stats_from_mult(m: dict) -> dict:
    return {k: round(BASE[k] * float(m.get(k, 1.0) or 1.0), 4) for k in STATS}


def ai_stats(level: str) -> dict:
    f = {"easy": 0.94, "medium": 1.0, "hard": 1.02, "master": 1.06}.get(level, 1.0)
    return {k: round(BASE[k] * f, 4) for k in STATS}


def _norm(x, y):
    d = math.sqrt(x * x + y * y)
    if d < 1e-9:
        return 0.0, 0.0, 0.0
    return x / d, y / d, d


class Sim:
    def __init__(self, human_stats: dict, level: str, periods: int = 3, period_s: int = 60, ai_st: dict | None = None):
        self.level = level
        self.mate_level = "medium"   # серіктестер — орташа деңгейде, базалық аттарда
        lv = LEVEL.get(level, LEVEL["medium"])
        mlv = LEVEL[self.mate_level]
        st_ai = ai_st or ai_stats(level)
        st_mate = dict(BASE)
        self.riders = []
        for i in range(6):
            t = 0 if i < 3 else 1
            st = human_stats if i == 0 else (st_mate if t == 0 else st_ai)
            L = mlv if t == 0 else lv
            self.riders.append({
                "t": t, "vmax": st["k_speed"] / 3.6 * (1.0 if i == 0 else L[1]), "acc": st["k_accel"] / 3.6,
                "smax": st["k_stamina"], "pow": st["k_power"], "agi": st["k_agility"],
                "K": L[0], "tap": L[2], "x": 0.0, "y": 0.0, "hx": 1.0, "hy": 0.0, "v": 0.0,
                "s": st["k_stamina"], "whip": 0, "cd": 0, "stop": 0, "fc": 0,
                "dx": 0.0, "dy": 0.0, "slow": 0, "g": 0, "p": 0, "w": 0})
        self.score = [0, 0]
        self.period_steps = int(period_s / DT)
        self.periods = periods
        self.n = 0
        self.holder = -1
        self.sx, self.sy = 100.0, 50.0
        self.duel = None   # [a, b, end, ta, tb, start]
        self.events = []   # гол, тартыс т.б. (көрсету үшін)
        self.over = False
        self.golden = False
        self.reset()

    def reset(self):
        for i, r in enumerate(self.riders):
            k = i % 3
            r["x"] = 70.0 if r["t"] == 0 else 130.0
            r["y"] = 35.0 + 15.0 * k
            r["hx"] = 1.0 if r["t"] == 0 else -1.0
            r["hy"] = 0.0
            r["v"] = 0.0
            r["whip"] = 0
            r["cd"] = 10
            r["stop"] = 0
            r["dx"] = 0.0
            r["dy"] = 0.0
            r["slow"] = 0
        self.holder = -1
        self.sx, self.sy = 100.0, 50.0
        self.duel = None

    # ---------------------------------------------------------------- ИИ
    def _dist(self, a, x, y):
        dx = x - a["x"]
        dy = y - a["y"]
        return math.sqrt(dx * dx + dy * dy)

    def _go(self, r, x, y):
        ux, uy, d = _norm(x - r["x"], y - r["y"])
        r["dx"] = ux
        r["dy"] = uy
        return d

    def ai(self, i):
        r = self.riders[i]
        t = r["t"]
        G = TARGET[t]
        D = TARGET[1 - t]
        h = self.holder
        r["slow"] = 0
        if h == i:
            d = self._go(r, G[0], G[1])
            if r["s"] > 50.0 and d < 70.0 and r["whip"] == 0:
                r["w"] = 1
            return
        mates = [j for j in range(6) if self.riders[j]["t"] == t]
        if h >= 0 and self.riders[h]["t"] == t:
            hr = self.riders[h]
            ux, uy, _ = _norm(G[0] - hr["x"], G[1] - hr["y"])
            side = 1.0 if mates.index(i) % 2 == 0 else -1.0
            self._go(r, hr["x"] + ux * 8.0 - uy * 6.0 * side, hr["y"] + uy * 8.0 + ux * 6.0 * side)
            return
        if h >= 0:
            hr = self.riders[h]
            order = sorted(mates, key=lambda j: (self._dist(self.riders[j], hr["x"], hr["y"]), j))
            if i in order[:2]:
                d = self._go(r, hr["x"] + hr["hx"] * hr["v"] * 0.4, hr["y"] + hr["hy"] * hr["v"] * 0.4)
                if d < PULL_D + 0.4 and r["cd"] == 0:
                    r["p"] = 1
                if d > 25.0 and r["s"] > 40.0 and r["whip"] == 0:
                    r["w"] = 1
            else:
                ux, uy, _ = _norm(100.0 - D[0], 50.0 - D[1])
                self._go(r, D[0] + ux * 12.0, D[1] + uy * 12.0)
            return
        order = sorted(mates, key=lambda j: (self._dist(self.riders[j], self.sx, self.sy), j))
        if i == order[0]:
            d = self._go(r, self.sx, self.sy)
            if d < 10.0:
                r["slow"] = 1
            if d < GRAB_D:
                r["g"] = 1
        else:
            side = 1.0 if order.index(i) == 1 else -1.0
            ux, uy, _ = _norm(G[0] - self.sx, G[1] - self.sy)
            self._go(r, self.sx + ux * 10.0 - uy * 8.0 * side, self.sy + uy * 10.0 + ux * 8.0 * side)

    # ---------------------------------------------------------------- бір қадам
    def step(self, inputs: list):
        n = self.n
        hr = self.riders[0]
        hr["g"] = 0
        hr["p"] = 0
        hr["w"] = 0
        for ev in inputs:
            k = ev[1]
            if k == "d":
                hr["dx"] = float(ev[2][0])
                hr["dy"] = float(ev[2][1])
            elif k == "w":
                hr["w"] = 1
            elif k == "g":
                hr["g"] = 1
            elif k == "p":
                hr["p"] = 1
        for i in range(1, 6):
            r = self.riders[i]
            r["g"] = 0
            r["p"] = 0
            r["w"] = 0
            if n % r["K"] == i % r["K"]:
                self.ai(i)
            elif self.holder >= 0 and self.riders[self.holder]["t"] != r["t"]:
                d = self._dist(r, self.riders[self.holder]["x"], self.riders[self.holder]["y"])
                if d < PULL_D and r["cd"] == 0:
                    r["p"] = 1
        # қозғалыс
        for i in range(6):
            r = self.riders[i]
            if r["w"] == 1 and r["whip"] == 0 and r["s"] >= 8.0 and r["stop"] == 0:
                r["s"] = r["s"] - 8.0
                r["whip"] = 20
            vmax = r["vmax"]
            if r["stop"] > 0:
                r["stop"] = r["stop"] - 1
                target = 0.0
            elif (r["dx"] == 0.0 and r["dy"] == 0.0) or r["slow"] == 1:
                target = 0.25 * vmax
            elif r["whip"] > 0:
                target = 1.15 * vmax
            else:
                target = 0.85 * vmax
            if r["s"] < 15.0 and target > 0.6 * vmax:
                target = 0.6 * vmax
            if self.holder == i:
                target = target * 0.92
            if self.duel is not None and (self.duel[0] == i or self.duel[1] == i):
                target = target * 0.6
            if r["v"] < target:
                r["v"] = min(target, r["v"] + r["acc"] * DT)
            else:
                r["v"] = max(target, r["v"] - 2.0 * r["acc"] * DT)
            if not (r["dx"] == 0.0 and r["dy"] == 0.0):
                hx = r["hx"] + (r["dx"] - r["hx"]) * 0.15
                hy = r["hy"] + (r["dy"] - r["hy"]) * 0.15
                ux, uy, d = _norm(hx, hy)
                if d < 1e-6:
                    r["hx"], r["hy"] = r["dx"], r["dy"]
                else:
                    r["hx"], r["hy"] = ux, uy
            r["x"] = r["x"] + r["hx"] * r["v"] * DT
            r["y"] = r["y"] + r["hy"] * r["v"] * DT
            if r["x"] < 1.0 or r["x"] > FW - 1.0 or r["y"] < 1.0 or r["y"] > FH - 1.0:
                r["x"] = min(FW - 1.0, max(1.0, r["x"]))
                r["y"] = min(FH - 1.0, max(1.0, r["y"]))
                r["v"] = r["v"] * 0.5
            if r["v"] > 0.7 * vmax:
                r["s"] = r["s"] - 1.0 * DT
            else:
                r["s"] = r["s"] + 4.0 * DT
            r["s"] = min(r["smax"], max(0.0, r["s"]))
            if r["whip"] > 0:
                r["whip"] = r["whip"] - 1
            if r["cd"] > 0:
                r["cd"] = r["cd"] - 1
            if r["fc"] > 0:
                r["fc"] = r["fc"] - 1
        # соқтығысу
        for i in range(6):
            a = self.riders[i]
            for j in range(i + 1, 6):
                b = self.riders[j]
                dx = b["x"] - a["x"]
                dy = b["y"] - a["y"]
                d2 = dx * dx + dy * dy
                if d2 >= 4.0 * R * R or d2 == 0.0:
                    continue
                d = math.sqrt(d2)
                nx = dx / d
                ny = dy / d
                o = (2.0 * R - d) / 2.0
                a["x"] = a["x"] - nx * o
                a["y"] = a["y"] - ny * o
                b["x"] = b["x"] + nx * o
                b["y"] = b["y"] + ny * o
                if a["t"] != b["t"] and i == 0:   # ИИ ережені бұзбайды; айыппұл тек ойыншыға (таран)
                    rvx = a["hx"] * a["v"] - b["hx"] * b["v"]
                    rvy = a["hy"] * a["v"] - b["hy"] * b["v"]
                    if rvx * rvx + rvy * rvy > 324.0:
                        f = a
                        if f["fc"] == 0 and a["v"] >= b["v"]:
                            f["s"] = max(0.0, f["s"] - 30.0)
                            f["stop"] = 100
                            f["fc"] = 140
                            f["v"] = f["v"] * 0.3
                            self.events.append([n, "foul", self.riders.index(f)])
        # серке
        if self.holder >= 0:
            self.sx = self.riders[self.holder]["x"]
            self.sy = self.riders[self.holder]["y"]
        else:
            for i in range(6):
                r = self.riders[i]
                if r["g"] == 1 and r["cd"] == 0 and self.holder < 0:
                    if self._dist(r, self.sx, self.sy) < GRAB_D:
                        if r["v"] * 3.6 <= 20.0 * r["agi"] and r["s"] >= 10.0:
                            self.holder = i
                            self.events.append([n, "grab", i])
                        else:
                            r["s"] = max(0.0, r["s"] - 5.0)
                            r["cd"] = 20
        # тартыс
        if self.duel is None and self.holder >= 0:
            hrd = self.riders[self.holder]
            for i in range(6):
                r = self.riders[i]
                if r["p"] == 1 and r["cd"] == 0 and r["t"] != hrd["t"]:
                    if self._dist(r, hrd["x"], hrd["y"]) < PULL_D:
                        self.duel = [self.holder, i, n + DUEL, 0, 0, n]
                        self.events.append([n, "duel", i])
                        r["p"] = 0
                        break
        if self.duel is not None:
            du = self.duel
            for side in (0, 1):
                idx = du[side]
                r = self.riders[idx]
                if idx == 0:
                    if r["p"] == 1:
                        du[3 + side] = du[3 + side] + 1
                else:
                    per = max(1, int(20.0 / r["tap"] + 0.5))
                    if (n - du[5]) % per == 0:
                        du[3 + side] = du[3 + side] + 1
            if n >= du[2]:
                a = self.riders[du[0]]
                b = self.riders[du[1]]
                sa = du[3] * a["pow"] * (0.5 + 0.5 * a["s"] / a["smax"])
                sb = du[4] * b["pow"] * (0.5 + 0.5 * b["s"] / b["smax"])
                if sb > sa:
                    self.holder = du[1]
                    loser = a
                    self.events.append([n, "steal", du[1]])
                else:
                    loser = b
                    self.events.append([n, "keep", du[0]])
                loser["s"] = max(0.0, loser["s"] - 20.0)
                loser["cd"] = 30
                self.duel = None
        # гол
        if self.holder >= 0:
            hrd = self.riders[self.holder]
            G = TARGET[hrd["t"]]
            if self._dist(hrd, G[0], G[1]) < KR:
                self.score[hrd["t"]] = self.score[hrd["t"]] + 1
                self.events.append([n, "goal", self.holder])
                self.reset()
                if self.golden:
                    self.over = True
        # уақыт
        self.n = n + 1
        total = self.period_steps * self.periods
        if not self.golden and self.n % self.period_steps == 0 and self.n <= total:
            self.reset()
            if self.n == total:
                if self.score[0] == self.score[1]:
                    self.golden = True
                else:
                    self.over = True
        if self.golden and self.n >= total + GOLDEN:
            self.over = True


def simulate(human_stats: dict, level: str, inputs: list, periods: int = 3, period_s: int = 60,
             frames_every: int = 0):
    """inputs: [[қадам, түр, мән], ...]. Қайтарады: {"gf", "ga", "events", "steps"}."""
    sim = Sim(human_stats, level, periods, period_s)
    by = {}
    for ev in inputs:
        by.setdefault(int(ev[0]), []).append(ev)
    limit = sim.period_steps * periods + GOLDEN + 5
    while not sim.over and sim.n < limit:
        sim.step(by.get(sim.n, []))
    return {"gf": sim.score[0], "ga": sim.score[1], "events": sim.events[-60:], "steps": sim.n}


def clean_inputs(inputs, max_steps: int) -> list:
    out = []
    for ev in list(inputs)[:20000]:
        try:
            n, k = int(ev[0]), str(ev[1])
        except (TypeError, ValueError, IndexError):
            continue
        if not (0 <= n <= max_steps) or k not in ("d", "w", "g", "p"):
            continue
        if k == "d":
            try:
                dx, dy = float(ev[2][0]), float(ev[2][1])
            except (TypeError, ValueError, IndexError):
                continue
            if not (math.isfinite(dx) and math.isfinite(dy)):
                continue
            d = math.sqrt(dx * dx + dy * dy)
            # клиент бірлік векторды 3 таңбаға дөңгелектеп жібереді — өзгертпейміз (JS-пен дәл сәйкестік)
            if 0.98 <= d <= 1.02:
                out.append([n, "d", [dx, dy]])
            else:
                out.append([n, "d", [0.0, 0.0]])
        else:
            out.append([n, k, None])
    out.sort(key=lambda e: e[0])
    return out


# ---------------------------------------------------------------- ойын күйі

def new_state(opts: dict | None = None) -> dict:
    opts = opts or {}
    return {"game": "kokpar", "stats": opts.get("stats") or [dict(BASE), dict(BASE)],
            "level": opts.get("level", "medium"), "period_s": int(opts.get("period_s", 60)), "periods": 3,
            "solo": False, "inputs": [None, None], "rides": [None, None], "turn": 0, "over": False,
            "winner": None, "reason": None, "moves": [], "last": None}


def clone(s):
    return copy.deepcopy(s)


def legal_moves(s):
    return [] if s["over"] else ["ride"]


def apply_move(s: dict, mv: dict) -> dict:
    if s["over"]:
        raise ValueError("game over")
    p = s["turn"]
    max_steps = int(s["period_s"] / DT) * s["periods"] + GOLDEN + 5
    inp = clean_inputs(mv.get("inputs", []), max_steps)
    r = simulate(s["stats"][p], s["level"], inp, s["periods"], s["period_s"])
    s["inputs"][p] = inp
    s["rides"][p] = {"gf": r["gf"], "ga": r["ga"]}
    s["moves"].append(f"{'⚪⚫'[p]} {r['gf']}:{r['ga']}")
    s["last"] = {"player": p, "id": len(s["moves"]), "gf": r["gf"], "ga": r["ga"]}
    if s["solo"]:
        s["over"] = True
        s["reason"] = "score"
        s["winner"] = p if r["gf"] > r["ga"] else (1 - p if r["ga"] > r["gf"] else -1)
        return s
    if s["rides"][1 - p] is None:
        s["turn"] = 1 - p
        return s
    s["over"] = True
    s["reason"] = "score"
    a, b = s["rides"]
    ka, kb = (a["gf"] - a["ga"], a["gf"]), (b["gf"] - b["ga"], b["gf"])
    s["winner"] = 0 if ka > kb else 1 if kb > ka else -1
    return s


def play(s, mv):
    return apply_move(clone(s), mv)


def score(s) -> list[int]:
    if s.get("solo"):
        for p, r in enumerate(s["rides"]):
            if r:
                out = [0, 0]
                out[p] = r["gf"]
                out[1 - p] = r["ga"]
                return out
        return [0, 0]
    return [(r or {}).get("gf", 0) for r in s["rides"]]


def demo_inputs(level: str, stats: dict, period_s: int = 60) -> list:
    """Сынақ үшін: адам орнына ИИ стратегиясымен ойнайтын «бот» енгізу журналы."""
    sim = Sim(stats, level, 3, period_s)
    out = []
    limit = sim.period_steps * 3 + GOLDEN + 5
    while not sim.over and sim.n < limit:
        n = sim.n
        ev = []
        if n % 4 == 0:
            r = sim.riders[0]
            sim.ai(0)
            slow = r["slow"]
            r["slow"] = 0
            ev.append([n, "d", [round(r["dx"], 3), round(r["dy"], 3)] if not slow else [0.0, 0.0]])
            if r["w"]:
                ev.append([n, "w", None])
            if r["g"]:
                ev.append([n, "g", None])
            if r["p"]:
                ev.append([n, "p", None])
        if sim.duel is not None and 0 in sim.duel[:2] and n % 3 == 0:
            ev.append([n, "p", None])
        out.extend(ev)
        sim.step(ev)
    return out
