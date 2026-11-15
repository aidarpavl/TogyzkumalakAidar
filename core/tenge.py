"""Теңге алу (теңге ілу) — ат үстінде шауып келе жатып, жерде жатқан теңге түйілген қызыл орамалдарды алу.

150 м жолда 5 орамал кезектесіп сол (-1) және оң (+1) жақта жатады.
Ойыншы «Солға / Оңға» еңкею сәттерін басады. Еңкею орамалдың тұсында (терезе ішінде) болса — орамал алынады,
әйтпесе +2 с айыппұл. Әр еңкею шыдамдылықты азайтады; шыдамдылық аз болса — дәлдік екі есе төмендейді.
Жеңімпаз: көп орамал алған, тең болса — уақыты аз (айыппұлмен).

Есеп серверде (ride) жасалады, JS компоненті сол формуланы көрсету үшін қайталайды.
"""
from __future__ import annotations

import copy
import math
import random

TRACK = 150.0
N = 5
PENALTY = 2.0
COST = 15.0
REGEN = 5.0
LOW = 25.0
WINDOW = 2.5          # метр, дәлдік ×1.0 болғанда
MAX_ATTEMPTS = 25

BASE = {"t_speed": 50.0, "t_stamina": 100.0, "t_accuracy": 1.0}
STATS = ("t_speed", "t_stamina", "t_accuracy")


def stats_from_mult(m: dict) -> dict:
    return {k: round(BASE[k] * float(m.get(k, 1.0) or 1.0), 4) for k in STATS}


def ai_stats(level: str) -> dict:
    """ИИ күші — дәлдікте; жылдамдығы базалық (Жеңілде сәл баяу), сондықтан мінсіз шабыс оны жеңе алады."""
    sp = {"easy": 0.95}.get(level, 1.0)
    acc = {"easy": 0.95, "medium": 1.0, "hard": 1.05, "master": 1.1}.get(level, 1.0)
    return {"t_speed": round(BASE["t_speed"] * sp, 4), "t_stamina": BASE["t_stamina"], "t_accuracy": acc}


def make_layout(rng: random.Random) -> list:
    side = rng.choice([-1, 1])
    out = []
    for i in range(N):
        out.append([round(25 * (i + 1) + rng.uniform(-4, 4), 2), side])
        side = -side
    return out


def ride(st: dict, layout: list, attempts: list) -> dict:
    v = st["t_speed"] / 3.6
    smax = st["t_stamina"]
    win = WINDOW * st["t_accuracy"]
    T = TRACK / v
    taken = [False] * len(layout)
    s, last, pen = smax, 0.0, 0.0
    log = []
    for t, side in attempts:
        s = min(smax, s + REGEN * (t - last))
        last = t
        x = v * t
        eff = win * (0.5 if s < LOW else 1.0)
        s = max(0.0, s - COST)
        hit = -1
        for i, (p, sd) in enumerate(layout):
            if not taken[i] and sd == side and abs(x - p) <= eff:
                hit = i
                break
        if hit < 0:
            pen += PENALTY
        else:
            taken[hit] = True
        log.append([t, side, hit])
    return {"taken": sum(taken), "time": round(T + pen, 2), "pen": pen, "T": round(T, 3), "log": log,
            "got": [i for i, x in enumerate(taken) if x]}


def _clean(attempts, T) -> list:
    out = []
    for a in list(attempts)[:MAX_ATTEMPTS]:
        try:
            t, side = float(a[0]), int(a[1])
        except (TypeError, ValueError, IndexError):
            continue
        if math.isfinite(t) and 0 <= t <= T and side in (-1, 1):
            out.append([t, side])
    out.sort(key=lambda x: x[0])
    return out


def new_state(opts: dict | None = None) -> dict:
    opts = opts or {}
    return {"game": "tenge", "stats": opts.get("stats") or [dict(BASE), dict(BASE)],
            "layout": make_layout(random.Random()), "attempts": [None, None], "rides": [None, None],
            "turn": 0, "over": False, "winner": None, "reason": None, "moves": [], "last": None}


def clone(s):
    return copy.deepcopy(s)


def legal_moves(s):
    return [] if s["over"] else ["ride"]


def apply_move(s: dict, mv: dict) -> dict:
    if s["over"]:
        raise ValueError("game over")
    p = s["turn"]
    st = s["stats"][p]
    T = TRACK / (st["t_speed"] / 3.6)
    att = _clean(mv.get("attempts", []), T)
    r = ride(st, s["layout"], att)
    s["attempts"][p] = att
    s["rides"][p] = {k: r[k] for k in ("taken", "time", "pen", "T", "got")}
    s["moves"].append(f"{'⚪⚫'[p]} {r['taken']}/{N} · {r['time']}s")
    s["last"] = {"player": p, "id": len(s["moves"]), "log": r["log"], "taken": r["taken"], "time": r["time"]}
    if s["rides"][1 - p] is None:
        s["turn"] = 1 - p
    else:
        s["over"] = True
        s["reason"] = "score"
        a, b = s["rides"]
        if a["taken"] != b["taken"]:
            s["winner"] = 0 if a["taken"] > b["taken"] else 1
        elif a["time"] != b["time"]:
            s["winner"] = 0 if a["time"] < b["time"] else 1
        else:
            s["winner"] = -1
    return s


def play(s, mv):
    return apply_move(clone(s), mv)


def score(s) -> list[int]:
    return [(r or {}).get("taken", 0) for r in s["rides"]]


# ---------------------------------------------------------------- ИИ

AI_SIGMA = {"easy": (0.22, 0.12), "medium": (0.11, 0.05), "hard": (0.06, 0.02), "master": (0.035, 0.0)}


def ai_attempts(st: dict, layout: list, level: str, rng: random.Random | None = None) -> list:
    rng = rng or random.Random()
    sigma, wrong = AI_SIGMA.get(level, AI_SIGMA["medium"])
    v = st["t_speed"] / 3.6
    T = TRACK / v
    out = []
    for p, sd in layout:
        t = p / v + rng.gauss(0, sigma)
        side = -sd if rng.random() < wrong else sd
        out.append([min(T, max(0.0, t)), side])
    out.sort(key=lambda x: x[0])
    return out


def describe(s, player) -> str:
    st = s["stats"][player]
    return (f"Track 150 m, speed {st['t_speed']:.1f} km/h, window ±{WINDOW * st['t_accuracy']:.2f} m. "
            f"Kerchiefs (meters, side -1=left/+1=right): {s['layout']}.")
