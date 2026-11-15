"""Жамбы ату — шауып бара жатқан аттың үстінен садақпен нысанаға ату.

Координаттар нысана жазықтығында: нысана радиусы = 1 (10 сақина).
Әр атыс — бір «шабыс»: T секунд ішінде нысана оңнан солға жылжиды, ал садақшы
аттың шоқырағанынан (амортизация) тербеледі. Ойыншы көздеуішті ұстап, жіберу сәтін таңдайды.

Тербеліс пен нысана қозғалысының формулалары JS компонентінде дәл қайталанады,
нәтижені (тиген нүкте мен ұпай) сервер есептейді.
"""
from __future__ import annotations

import copy
import math
import random

ENDS = 3              # сериялар
ARROWS_PER_END = 3    # әр ойыншыға бір серияда
DISTANCES = [30, 50, 70]
TOTAL_ARROWS = ENDS * ARROWS_PER_END * 2


def view_half(dist: int) -> float:
    """Экранның жарты ені (нысана радиусымен)."""
    return 2.6 * dist / 30


def bob(cur: dict, t: float) -> tuple[float, float]:
    """Аттың шоқырағанынан садақтың тербелуі (галоп: 3 соққылы ырғақ)."""
    ph = 2 * math.pi * cur["freq"] * t + cur["ph"]
    by = cur["ampy"] * (0.62 * math.sin(ph) + 0.38 * math.sin(2 * ph + 0.8))
    bx = cur["ampx"] * math.sin(ph / 2 + 0.3)
    return bx, by


def target_x(cur: dict, t: float) -> float:
    return cur["v"] * (cur["T"] / 2 - t)


def _new_arrow(s: dict, rng: random.Random) -> dict:
    n = s["shots"]
    end = min(ENDS - 1, n // (ARROWS_PER_END * 2))
    dist = DISTANCES[end]
    k = dist / 30
    return {
        "dist": dist, "end": end,
        "wind": round(rng.uniform(-1, 1) * 0.35 * (0.6 + 0.4 * end), 3),
        "T": round(7.5 - end * 0.8, 2),
        "v": round(rng.uniform(0.55, 0.85) * k, 3),
        "freq": round(rng.uniform(1.4, 1.9), 3),
        "ph": round(rng.uniform(0, 2 * math.pi), 3),
        "ampy": round((0.55 + 0.25 * end) * k * rng.uniform(0.85, 1.15), 3),
        "ampx": round((0.25 + 0.1 * end) * k * rng.uniform(0.85, 1.15), 3),
        "id": n + 1,
    }


def new_state(opts: dict | None = None) -> dict:
    s = {"game": "jamby", "scores": [[], []], "turn": 0, "shots": 0, "over": False, "winner": None,
         "reason": None, "moves": [], "last": None, "hits": [[], []]}
    s["cur"] = _new_arrow(s, random.Random())
    return s


def clone(s):
    return copy.deepcopy(s)


def score_of(r: float) -> int:
    if r >= 1:
        return 0
    return max(1, 10 - int(r * 10))


def legal_moves(s):
    return [] if s["over"] else ["shot"]


def apply_move(s: dict, shot: dict, rng: random.Random | None = None) -> dict:
    """shot = {"ax", "ay", "t"} — көздеуіштің қолдағы орны (тербеліссіз) және жіберу уақыты."""
    if s["over"]:
        raise ValueError("game over")
    rng = rng or random.Random()
    cur = s["cur"]
    p = s["turn"]
    t = float(shot.get("t", 0))
    k = cur["dist"] / 30
    timeout = not (0 <= t <= cur["T"] + 0.05)
    if timeout:
        t = cur["T"]
    bx, by = bob(cur, t)
    half = view_half(cur["dist"])
    ax = max(-half, min(half, float(shot.get("ax", 0))))
    ay = max(-half * 1.2, min(half * 1.2, float(shot.get("ay", 0))))
    # қолдың дірілі — сервер қосады
    tremor = 0.035 * k
    ix = ax + bx + cur["wind"] * k + rng.gauss(0, tremor)
    iy = ay + by + rng.gauss(0, tremor) + 0.02 * k  # аздаған түсу
    tx = target_x(cur, t)
    rx, ry = ix - tx, iy
    r = math.hypot(rx, ry)
    pts = 0 if timeout else score_of(r)
    s["scores"][p].append(pts)
    s["hits"][p].append([round(rx, 3), round(ry, 3), pts])
    s["shots"] += 1
    mark = "X" if (pts == 10 and r < 0.05) else str(pts) if pts else "M"
    s["moves"].append(f"{'⚪⚫'[p]}{mark}")
    s["last"] = {"id": s["shots"], "shooter": p, "ix": round(ix, 3), "iy": round(iy, 3), "rx": round(rx, 3),
                 "ry": round(ry, 3), "pts": pts, "x": pts == 10 and r < 0.05, "t": round(t, 3),
                 "timeout": timeout, "tx": round(tx, 3), "dist": cur["dist"]}
    s["turn"] = 1 - p
    if s["shots"] >= TOTAL_ARROWS:
        s["over"] = True
        s["reason"] = "score"
        a, b = sum(s["scores"][0]), sum(s["scores"][1])
        s["winner"] = 0 if a > b else 1 if b > a else -1
        s["cur"] = None
    else:
        s["cur"] = _new_arrow(s, rng)
    return s


def play(s, shot, rng=None):
    return apply_move(clone(s), shot, rng)


def totals(s) -> list[int]:
    return [sum(s["scores"][0]), sum(s["scores"][1])]


# ---------------------------------------------------------------- ИИ

LEVELS = {"easy": 0.42, "medium": 0.24, "hard": 0.12, "master": 0.06}


def best_shot(s: dict, level: str = "medium", rng: random.Random | None = None) -> dict:
    rng = rng or random.Random()
    cur = s["cur"]
    err = LEVELS.get(level, 0.24) * cur["dist"] / 30
    # тербеліс ең аз болатын сәтті іздеу
    best_t, best_b = cur["T"] / 2, 9e9
    for i in range(1, 60):
        t = cur["T"] * i / 60
        bx, by = bob(cur, t)
        m = math.hypot(bx, by) + abs(target_x(cur, t)) * 0.05
        if m < best_b:
            best_t, best_b = t, m
    t = best_t + rng.gauss(0, 0.05 + err * 0.2)
    t = min(cur["T"], max(0.0, t))
    bx, by = bob(cur, t)
    k = cur["dist"] / 30
    ax = target_x(cur, t) - bx - cur["wind"] * k * (1 + rng.gauss(0, err)) + rng.gauss(0, err)
    ay = -by - 0.02 * k + rng.gauss(0, err)
    return {"ax": ax, "ay": ay, "t": t}


def describe(s, player):
    cur = s["cur"]
    return (f"Distance {cur['dist']} m, wind {cur['wind']:+.2f} (target radii, + = right), "
            f"target sweeps from x={target_x(cur, 0):+.2f} to x={target_x(cur, cur['T']):+.2f} over {cur['T']} s. "
            f"Scores: you {totals(s)[player]}, opponent {totals(s)[1 - player]}.")
