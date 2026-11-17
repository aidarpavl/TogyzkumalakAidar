"""Аударыспақ — екі жігіттің ат үстінде бір-бірін аудару тартысы.

Детерминистік модель (DT = 0.05 с), тек + − × ÷ және sqrt — JS-те дәл қайталанады
(components/_shared/audaryspak_sim.js). 0 — ойыншы, 1 — ИИ қарсылас.

Кезеңдер: «жақындасу» (джойстикпен атты жақындату; 2.2 м-де — ұстасу), «тартыс» (әрекеттер).
Әрекеттер (0.4 с дайындық, содан кейін нәтиже):
  pull (ТАРТУ) > push (ИТЕРУ) > hold (ТЕПЕ-ТЕҢДІК); twist (БҰРУ) > pull; push > twist.
Қорғаныс: hold (басып тұру) — тарту мен бұрудан зиянды азайтады, бірақ итеруге осал.
Дәл сәт: қарсылас өз әрекетін аяқтағаннан кейінгі 0.3 с ішінде тисе — ×1.5.
Тепе-теңдік 0-ге түссе — «аударылды», раунд жеңілді. Раунд 60 с, 3 раундтың 2-уі.

Енгізу: [қадам, "d", [dx, dy]] | [қадам, "a", "pull"/"push"/"twist"] | [қадам, "h", 1/0] | [қадам, "x", None].
"""
from __future__ import annotations

import copy
import math

DT = 0.05
ARENA = 20.0
GRIP_D = 2.2
WIND = 10           # дайындық қадамдары (0.5 с)
OPEN = 6            # «ашық» терезе (0.3 с)
BASE = {"a_stability": 1.0, "a_agility": 1.0, "a_stamina": 100.0, "a_power": 1.0, "a_grip": 1.0, "a_balance": 100.0}
STATS = ("a_stability", "a_agility", "a_stamina", "a_power", "a_grip", "a_balance")
HORSE_STATS = ("a_stability", "a_agility", "a_stamina")
RIDER_STATS = ("a_power", "a_grip", "a_balance")
# реакция (қадам), шабуыл аралығы (қадам), байқау жиілігі (20-дан)
LEVEL = {"easy": (8, 30, 4), "medium": (5, 22, 8), "hard": (4, 18, 12), "master": (3, 14, 15)}
COUNTER = {"pull": "twist", "push": "pull", "twist": "push"}


def stats_from_mult(m: dict) -> dict:
    return {k: round(BASE[k] * float(m.get(k, 1.0) or 1.0), 4) for k in STATS}


def ai_stats(level: str) -> dict:
    f = {"easy": 0.94, "medium": 1.0, "hard": 1.03, "master": 1.07}.get(level, 1.0)
    return {k: round(BASE[k] * f, 4) for k in STATS}


def _mult(att: str, dfn: dict) -> float:
    """Шабуыл мен қорғаныстың арақатынасы. -1 — қарсы әрекет (шабуылдаушы өзі зардап шегеді)."""
    dact = dfn["act"]
    winding = dfn["wind"] > 0
    if att == "pull":
        if winding and dact == "twist":
            return -1.0
        if dfn["hold"] == 1:
            return 0.4
        return 1.0
    if att == "push":
        if winding and dact == "pull":
            return -1.0
        if dfn["hold"] == 1:
            return 1.6
        return 1.0
    if winding and dact == "push":
        return -1.0
    if winding and dact == "pull":
        return 1.5
    if dfn["hold"] == 1:
        return 0.5
    return 1.0


class Sim:
    def __init__(self, hs: dict, level: str, round_s: int = 60, ai_st: dict | None = None):
        self.level = level
        lv = LEVEL.get(level, LEVEL["medium"])
        self.react, self.every, self.notice = lv
        ast = ai_st or ai_stats(level)
        self.p = []
        for i, st in enumerate((hs, ast)):
            self.p.append({"stab": st["a_stability"], "agi": st["a_agility"], "smax": st["a_stamina"],
                           "pow": st["a_power"], "grip": st["a_grip"], "bmax": st["a_balance"],
                           "x": 0.0, "y": 0.0, "dx": 0.0, "dy": 0.0, "s": st["a_stamina"], "b": st["a_balance"],
                           "act": "", "wind": 0, "open": 0, "hold": 0, "cd": 0, "hit": 0, "adv": 0.0, "warn": 0})
        self.round_steps = int(round_s / DT)
        self.round = 1
        self.rounds = [0, 0]
        self.n = 0
        self.rn = 0          # раунд ішіндегі қадам
        self.grip = False
        self.hist = []       # ойыншының соңғы шабуылдары
        self.seen = -1       # ИИ ойыншының дайындығын көрген қадам
        self.events = []
        self.over = False
        self.reset()

    def reset(self):
        for i, r in enumerate(self.p):
            r["x"] = -8.0 if i == 0 else 8.0
            r["y"] = 0.0
            r["dx"] = 0.0
            r["dy"] = 0.0
            r["s"] = r["smax"]
            r["b"] = r["bmax"]
            r["act"] = ""
            r["wind"] = 0
            r["open"] = 0
            r["hold"] = 0
            r["cd"] = 10
            r["hit"] = 0
            r["warn"] = 0
        self.grip = False
        self.rn = 0
        self.seen = -1

    def _start(self, i, act):
        r = self.p[i]
        if r["wind"] > 0 or r["s"] < 6.0 or not self.grip:
            return
        r["s"] = r["s"] - 6.0
        r["act"] = act
        r["wind"] = WIND
        if i == 0:
            self.hist.append(act)
            if len(self.hist) > 5:
                self.hist = self.hist[-5:]

    def _disengage(self, i):
        r = self.p[i]
        o = self.p[1 - i]
        if not self.grip or r["cd"] > 0 or r["s"] < 10.0:
            return
        r["s"] = r["s"] - 10.0
        r["cd"] = 80
        if r["agi"] * r["s"] >= 0.6 * o["grip"] * o["s"]:
            self.grip = False
            r["x"] = r["x"] - 3.0 if r["x"] <= o["x"] else r["x"] + 3.0
            o["act"] = ""
            o["wind"] = 0
            self.events.append([self.n, "free", i])

    def _ai(self):
        a = self.p[1]
        h = self.p[0]
        n = self.rn
        if not self.grip:
            ux = h["x"] - a["x"]
            uy = h["y"] - a["y"]
            d = math.sqrt(ux * ux + uy * uy)
            if d > 1e-9:
                a["dx"] = ux / d
                a["dy"] = uy / d
            return
        a["dx"] = 0.0
        a["dy"] = 0.0
        # ойыншының дайындығына жауап
        if h["wind"] > 0:
            if self.seen < 0:
                self.seen = n
            if n - self.seen == self.react and a["wind"] == 0 and (self.seen * 7 + 3) % 20 < self.notice:
                c = COUNTER[h["act"]]
                if a["s"] >= 6.0:
                    self._start(1, c)
                    return
        else:
            self.seen = -1
        if a["wind"] == 0:
            a["hold"] = 1 if (a["b"] < 0.35 * a["bmax"] and a["s"] > 12.0) else 0
            if n % self.every == 0 and a["s"] >= 6.0 and a["hold"] == 0:
                cnt = {"pull": 0, "push": 0, "twist": 0}
                for x in self.hist:
                    cnt[x] = cnt[x] + 1
                best = "pull"
                if cnt["push"] > cnt[best]:
                    best = "push"
                if cnt["twist"] > cnt[best]:
                    best = "twist"
                act = COUNTER[best] if len(self.hist) >= 3 else ("pull", "push", "twist")[(n // self.every) % 3]
                if h["hold"] == 1:
                    act = "push"
                self._start(1, act)

    def step(self, inputs: list):
        n = self.n
        h = self.p[0]
        for ev in inputs:
            k = ev[1]
            if k == "d":
                h["dx"] = float(ev[2][0])
                h["dy"] = float(ev[2][1])
            elif k == "a":
                self._start(0, ev[2])
            elif k == "h":
                h["hold"] = 1 if ev[2] else 0
            elif k == "x":
                self._disengage(0)
        if n % 2 == 0 or self.grip:
            self._ai()
        # қозғалыс (жақындасу)
        for i in range(2):
            r = self.p[i]
            if not self.grip:
                sp = (5.0 + 2.0 * r["agi"]) * DT
                r["x"] = r["x"] + r["dx"] * sp
                r["y"] = r["y"] + r["dy"] * sp
                d = math.sqrt(r["x"] * r["x"] + r["y"] * r["y"])
                if d > ARENA:
                    r["x"] = r["x"] / d * (ARENA - 0.5)
                    r["y"] = r["y"] / d * (ARENA - 0.5)
                    if i == 0:
                        r["warn"] = r["warn"] + 1
                        self.events.append([n, "warn", 0])
                        r["dx"] = 0.0
                        r["dy"] = 0.0
                r["s"] = min(r["smax"], r["s"] + 10.0 * DT)
                r["b"] = min(r["bmax"], r["b"] + 4.0 * DT)
            else:
                if r["hold"] == 1:
                    r["s"] = max(0.0, r["s"] - 6.0 * DT)
                    if r["s"] <= 0.0:
                        r["hold"] = 0
                elif r["wind"] == 0:
                    r["s"] = min(r["smax"], r["s"] + 5.0 * DT)
                if r["hit"] > 40:
                    r["b"] = min(r["bmax"], r["b"] + 1.5 * DT)
            if r["cd"] > 0:
                r["cd"] = r["cd"] - 1
            if r["open"] > 0:
                r["open"] = r["open"] - 1
            r["hit"] = r["hit"] + 1
        # ұстасу
        if not self.grip:
            dx = self.p[1]["x"] - self.p[0]["x"]
            dy = self.p[1]["y"] - self.p[0]["y"]
            if dx * dx + dy * dy < GRIP_D * GRIP_D and self.p[0]["cd"] == 0 and self.p[1]["cd"] == 0:
                self.grip = True
                self.events.append([n, "grip", 0])
        # әрекеттердің нәтижесі
        if self.grip:
            res = []
            for i in range(2):
                r = self.p[i]
                if r["wind"] > 0:
                    r["wind"] = r["wind"] - 1
                    if r["wind"] == 0:
                        res.append(i)
            for i in res:
                a = self.p[i]
                o = self.p[1 - i]
                m = _mult(a["act"], o)
                if m < 0:
                    dmg = 6.0
                    a["b"] = max(0.0, a["b"] - dmg)
                    a["hit"] = 0
                    o["adv"] = o["adv"] + dmg
                    self.events.append([n, "counter", 1 - i])
                else:
                    if o["open"] > 0:
                        m = m * 1.5
                    dmg = 7.0 * a["pow"] * a["grip"] * m * (0.5 + 0.5 * a["s"] / a["smax"]) - 2.0 * o["stab"]
                    if dmg < 1.0:
                        dmg = 1.0
                    o["b"] = max(0.0, o["b"] - dmg)
                    o["hit"] = 0
                    a["adv"] = a["adv"] + dmg
                    self.events.append([n, a["act"], i])
                a["act"] = ""
                a["open"] = OPEN
        # раунд нәтижесі
        winner = -2
        for i in range(2):
            if self.p[i]["b"] <= 0.0:
                winner = 1 - i
                self.events.append([n, "fall", i])
        if winner == -2 and self.p[0]["warn"] >= 2:
            winner = 1
            self.events.append([n, "out", 0])
        self.n = n + 1
        self.rn = self.rn + 1
        if winner == -2 and self.rn >= self.round_steps:
            b0 = self.p[0]["b"] / self.p[0]["bmax"]
            b1 = self.p[1]["b"] / self.p[1]["bmax"]
            if b0 - b1 > 0.05:
                winner = 0
            elif b1 - b0 > 0.05:
                winner = 1
            else:
                winner = -1
            self.events.append([n, "time", winner])
        if winner != -2:
            if winner >= 0:
                self.rounds[winner] = self.rounds[winner] + 1
            if self.rounds[0] >= 2 or self.rounds[1] >= 2 or self.round >= 3:
                self.over = True
            else:
                self.round = self.round + 1
                self.reset()


def simulate(hs: dict, level: str, inputs: list, round_s: int = 60, ai_st: dict | None = None) -> dict:
    sim = Sim(hs, level, round_s, ai_st)
    by = {}
    for ev in inputs:
        by.setdefault(int(ev[0]), []).append(ev)
    limit = sim.round_steps * 3 + 10
    while not sim.over and sim.n < limit:
        sim.step(by.get(sim.n, []))
    return {"rw": sim.rounds[0], "rl": sim.rounds[1], "adv": round(sim.p[0]["adv"] - sim.p[1]["adv"], 2),
            "steps": sim.n, "events": sim.events[-40:]}


def clean_inputs(inputs, max_steps: int) -> list:
    out = []
    for ev in list(inputs)[:20000]:
        try:
            n, k = int(ev[0]), str(ev[1])
        except (TypeError, ValueError, IndexError):
            continue
        if not (0 <= n <= max_steps):
            continue
        if k == "d":
            try:
                dx, dy = float(ev[2][0]), float(ev[2][1])
            except (TypeError, ValueError, IndexError):
                continue
            if not (math.isfinite(dx) and math.isfinite(dy)):
                continue
            d = math.sqrt(dx * dx + dy * dy)
            out.append([n, "d", [dx, dy] if 0.98 <= d <= 1.02 else [0.0, 0.0]])
        elif k == "a" and ev[2] in ("pull", "push", "twist"):
            out.append([n, "a", ev[2]])
        elif k == "h":
            out.append([n, "h", 1 if ev[2] else 0])
        elif k == "x":
            out.append([n, "x", None])
    out.sort(key=lambda e: e[0])
    return out


# ---------------------------------------------------------------- ойын күйі

def new_state(opts: dict | None = None) -> dict:
    opts = opts or {}
    return {"game": "audaryspak", "stats": opts.get("stats") or [dict(BASE), dict(BASE)],
            "level": opts.get("level", "medium"), "round_s": int(opts.get("round_s", 60)), "solo": False,
            "inputs": [None, None], "rides": [None, None], "turn": 0, "over": False, "winner": None,
            "reason": None, "moves": [], "last": None}


def clone(s):
    return copy.deepcopy(s)


def legal_moves(s):
    return [] if s["over"] else ["fight"]


def apply_move(s: dict, mv: dict) -> dict:
    if s["over"]:
        raise ValueError("game over")
    p = s["turn"]
    inp = clean_inputs(mv.get("inputs", []), int(s["round_s"] / DT) * 3 + 10)
    r = simulate(s["stats"][p], s["level"], inp, s["round_s"], s.get("ai_stats"))
    s["inputs"][p] = inp
    s["rides"][p] = {"rw": r["rw"], "rl": r["rl"], "adv": r["adv"]}
    s["moves"].append(f"{'⚪⚫'[p]} {r['rw']}:{r['rl']}")
    s["last"] = {"player": p, "id": len(s["moves"])}
    if s["solo"]:
        s["over"] = True
        s["reason"] = "score"
        s["winner"] = p if r["rw"] > r["rl"] else (1 - p if r["rl"] > r["rw"] else -1)
        return s
    if s["rides"][1 - p] is None:
        s["turn"] = 1 - p
        return s
    s["over"] = True
    s["reason"] = "score"
    a, b = s["rides"]
    ka, kb = (a["rw"] - a["rl"], a["adv"]), (b["rw"] - b["rl"], b["adv"])
    s["winner"] = 0 if ka > kb else 1 if kb > ka else -1
    return s


def play(s, mv):
    return apply_move(clone(s), mv)


def score(s) -> list[int]:
    if s.get("solo"):
        for p, r in enumerate(s["rides"]):
            if r:
                out = [0, 0]
                out[p] = r["rw"]
                out[1 - p] = r["rl"]
                return out
        return [0, 0]
    return [(r or {}).get("rw", 0) for r in s["rides"]]


def demo_inputs(level: str, hs: dict, round_s: int = 60, skill: str = "medium", ai_st: dict | None = None,
                offset: int = 0) -> list:
    """Сынақ «боты»: ойыншы орнына берілген деңгейдегі тактикамен ойнайды."""
    sim = Sim(hs, level, round_s, ai_st)
    react, every, notice = LEVEL.get(skill, LEVEL["medium"])
    out, seen = [], -1
    limit = sim.round_steps * 3 + 10
    while not sim.over and sim.n < limit:
        n, h, a, ev = sim.n, sim.p[0], sim.p[1], []
        if not sim.grip:
            ux, uy = a["x"] - h["x"], a["y"] - h["y"]
            d = math.sqrt(ux * ux + uy * uy)
            if d > 1e-9 and n % 4 == 0:
                ev.append([n, "d", [round(ux / d, 3), round(uy / d, 3)]])
        else:
            if a["wind"] > 0:
                if seen < 0:
                    seen = sim.rn
                if sim.rn - seen == react and h["wind"] == 0 and (seen * 11 + 5) % 20 < notice:
                    ev.append([n, "a", COUNTER[a["act"]]])
            else:
                seen = -1
            want_hold = 1 if (h["b"] < 0.35 * h["bmax"] and h["s"] > 12.0 and h["wind"] == 0) else 0
            if want_hold != h["hold"]:
                ev.append([n, "h", want_hold])
            if h["wind"] == 0 and want_hold == 0 and (sim.rn + offset) % every == 0:
                act = "push" if a["hold"] == 1 else ("pull", "twist", "push")[((sim.rn + offset) // every) % 3]
                ev.append([n, "a", act])
        out.extend(ev)
        sim.step(ev)
    return out
