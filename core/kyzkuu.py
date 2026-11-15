"""Қыз қуу — ұлттық ат жарысы.

Ойыншы 0 — Қыз, ойыншы 1 — Жігіт.
1-кезең («бару»): қыз қашады, 15 м озғаннан кейін жігіт қуады. Қыз 200 м-ге жеткенше жігіт қуып жетсе — жігіт ұтады.
2-кезең («қайту»): рөлдер ауысады — жігіт қашады, қыз қуады. Қуып жетсе — қыз ұтады (қамшымен тартады).

Жарыс детерминистік: әр шабандоз «қамшы» басу уақыттарын (өз стартынан бастап, секундпен) жібереді,
сервер екі тізімді біріктіріп модельдейді. Формулалар JS компонентінде дәл қайталанады.
"""
from __future__ import annotations

import copy
import math

DT = 0.05
HEAD = 15.0
DIST = 200.0
MAX_STEPS = 3000          # 150 с
WHIP_COST = 4.0
WHIP_TIME = 0.6
WHIP_GAP = 0.25
REGEN = 3.0
CHASE = 1.08            # қуушы атын барынша қамшылайды — жылдамдығы 8% жоғары

BASE = {"burst": 5.0, "speed": 20.0, "stamina": 100.0, "reverse": 20.0}
STATS = ("burst", "speed", "stamina", "reverse")
ROLES = ("girl", "jigit")


def stats_from_mult(m: dict) -> dict:
    return {k: round(BASE[k] * float(m.get(k, 1.0)), 3) for k in STATS}


def ai_stats(level: str) -> dict:
    f = {"easy": 0.92, "medium": 1.0, "hard": 1.08, "master": 1.16}.get(level, 1.0)
    return {k: round(BASE[k] * f, 3) for k in STATS}


class Runner:
    def __init__(self, st: dict, stage: int, taps: list):
        kmh = st["speed"] if stage == 0 else st["reverse"]
        self.vmax = kmh / 3.6
        self.v = st["burst"] / 3.6
        self.k = 0.9 * math.sqrt(st["burst"] / 5.0)
        self.smax = st["stamina"]
        self.s = st["stamina"]
        self.taps = taps
        self.i = 0
        self.whip_until = -1.0
        self.last = -1.0

    def step(self, lt: float) -> None:
        taps = self.taps
        while self.i < len(taps) and taps[self.i] <= lt:
            tp = taps[self.i]
            if tp - self.last >= WHIP_GAP and self.s >= WHIP_COST:
                self.s = self.s - WHIP_COST
                self.whip_until = tp + WHIP_TIME
                self.last = tp
            self.i += 1
        whipping = lt < self.whip_until
        if whipping:
            target = self.vmax * 1.2
        elif self.s < 15.0:
            target = self.vmax * 0.65
        else:
            target = self.vmax * 0.8
        self.v = self.v + (target - self.v) * self.k * DT
        if not whipping:
            self.s = min(self.smax, self.s + REGEN * DT)


def simulate(stage: int, fleer_st: dict, chaser_st: dict, fleer_taps: list, chaser_taps: list,
             frames_every: int = 4) -> dict:
    F = Runner(fleer_st, stage, fleer_taps)
    C = Runner(chaser_st, stage, chaser_taps)
    C.vmax = C.vmax * CHASE
    fx = 0.0
    cx = 0.0
    started = False
    c0 = 0.0
    frames = []
    result = {"caught": False, "time": None, "fx": 0.0, "cx": 0.0}
    for n in range(MAX_STEPS):
        t = n * DT
        F.step(t)
        fx = fx + F.v * DT
        if not started and fx >= HEAD:
            started = True
            c0 = t
        if started:
            C.step(t - c0)
            cx = cx + C.v * DT
        if n % frames_every == 0:
            frames.append([round(fx, 2), round(cx, 2), round(F.v * 3.6, 1), round(C.v * 3.6, 1),
                           round(F.s, 1), round(C.s, 1)])
        if started and cx >= fx:
            result.update(caught=True, time=round(t, 2), fx=round(fx, 2), cx=round(cx, 2))
            break
        if fx >= DIST:
            result.update(caught=False, time=round(t, 2), fx=round(fx, 2), cx=round(cx, 2))
            break
    frames.append([round(fx, 2), round(cx, 2), round(F.v * 3.6, 1), round(C.v * 3.6, 1),
                   round(F.s, 1), round(C.s, 1)])
    result["frames"] = frames
    return result


# ---------------------------------------------------------------- ИИ қамшы кестесі

AI_STYLE = {"easy": (0.9, 30, 50), "medium": (0.55, 22, 55), "hard": (0.38, 18, 60), "master": (0.3, 16, 70)}


def ai_taps(st: dict, stage: int, level: str, horizon: float = 150.0) -> list:
    gap, rest_below, resume_above = AI_STYLE.get(level, AI_STYLE["medium"])
    r = Runner(st, stage, [])
    taps, nxt, resting = [], 0.4, False
    n = 0
    while n * DT < horizon:
        lt = n * DT
        if resting and r.s >= resume_above:
            resting = False
        if not resting and r.s < rest_below:
            resting = True
        if not resting and lt >= nxt and r.s >= WHIP_COST:
            taps.append(round(lt, 2))
            r.taps = taps
            nxt = lt + gap
        r.step(lt)
        n += 1
    return taps


# ---------------------------------------------------------------- Ойын күйі

def fleer(stage: int) -> int:
    """Қай ойыншы қашады: 1-кезең — қыз (0), 2-кезең — жігіт (1)."""
    return 0 if stage == 0 else 1


def new_state(opts: dict | None = None) -> dict:
    opts = opts or {}
    stats = opts.get("stats") or [dict(BASE), dict(BASE)]
    return {"game": "kyzkuu", "stats": stats, "stage": 0, "turn": 0, "inputs": [{}, {}],
            "results": [], "points": [0, 0], "over": False, "winner": None, "reason": None,
            "moves": [], "last": None, "ghost": None}


def clone(s):
    return copy.deepcopy(s)


def legal_moves(s):
    return [] if s["over"] else ["ride"]


def _clean(taps) -> list:
    out = []
    for x in list(taps)[:2000]:
        x = float(x)
        if math.isfinite(x) and 0 <= x <= 200:
            out.append(x)  # дөңгелектемейміз — JS-пен дәл сәйкес болуы үшін
    out.sort()
    return out


def apply_move(s: dict, mv: dict) -> dict:
    """mv = {"taps": [...]}: кезектегі ойыншының осы кезеңдегі қамшы уақыттары."""
    if s["over"]:
        raise ValueError("game over")
    stage, p = s["stage"], s["turn"]
    s["inputs"][stage][str(p)] = _clean(mv.get("taps", []))
    f = fleer(stage)
    if str(1 - p) not in s["inputs"][stage]:
        s["turn"] = 1 - p
        return s
    res = simulate(stage, s["stats"][f], s["stats"][1 - f], s["inputs"][stage][str(f)],
                   s["inputs"][stage][str(1 - f)])
    chaser = 1 - f
    winner = chaser if res["caught"] else f
    s["points"][winner] += 1
    res.update(stage=stage, fleer=f, winner=winner, id=stage + 1)
    s["results"].append({k: v for k, v in res.items() if k != "frames"})
    s["last"] = res
    sym = "❤" if (stage == 0 and res["caught"]) else ("〰" if res["caught"] else "🏁")
    s["moves"].append(f"{stage + 1}:{sym}{res['time']}s")
    if stage == 0:
        s["stage"] = 1
        s["turn"] = fleer(1)
    else:
        s["over"] = True
        s["reason"] = "score"
        a, b = s["points"]
        s["winner"] = 0 if a > b else 1 if b > a else -1
    return s


def play(s, mv):
    return apply_move(clone(s), mv)


def score(s):
    return s["points"]
