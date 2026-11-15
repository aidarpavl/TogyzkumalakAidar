"""Асық ату — физика (серверде), ойын логикасы және ИИ.

Алаң 600×800. Ортада сызылған шеңбер (кон) ішінде асықтар қатарға тізілген.
Ойыншы сақасын төменгі сызықтан атады. Шеңберден шығып кеткен асықтар атушыға тиеді.
Кемінде бір асық ұтса — тағы атады, әйтпесе кезек ауысады.
Барлық асық біткенде көп жинаған жеңеді.
"""
from __future__ import annotations

import copy
import math
import random

W, H = 600, 800
CX, CY, R = 300.0, 300.0, 200.0
BASE_Y = 700.0
SX_MIN, SX_MAX = 80.0, 520.0
ASYK_R, SAQA_R = 11.0, 14.0
ASYK_M, SAQA_M = 1.0, 2.2
FRICTION_SAQA, FRICTION_ASYK = 0.982, 0.92
VMIN, VMAX = 7.0, 17.0
N_ASYK = 10
MAX_SHOTS = 80
TOSS = ["алшы", "тәйке", "бүк", "шік"]


def new_state(n: int = N_ASYK) -> dict:
    gap = 26.0
    asyks = [[round(CX + (i - (n - 1) / 2) * gap, 2), CY] for i in range(n)]
    toss = random.choice(TOSS)
    return {"game": "asyk", "asyks": asyks, "captured": [0, 0], "turn": 0 if toss in ("алшы", "тәйке") else 1,
            "over": False, "winner": None, "reason": None, "moves": [], "last": None, "shots": 0,
            "toss": toss, "total": n}


def clone(s):
    return copy.deepcopy(s)


def simulate(asyks: list, sx: float, dx: float, dy: float, power: float, record_every: int = 3):
    """Атысты модельдеу. Қайтарады: (соңғы асық орындары, кадрлар)."""
    sx = min(SX_MAX, max(SX_MIN, sx))
    norm = math.sqrt(dx * dx + dy * dy) or 1.0
    dx, dy = dx / norm, dy / norm
    if dy > -0.15:  # тек жоғары қарай
        dy = -0.15
        norm = math.sqrt(dx * dx + dy * dy)
        dx, dy = dx / norm, dy / norm
    speed = VMIN + (VMAX - VMIN) * min(1.0, max(0.0, power))
    # объектілер: [x, y, vx, vy, r, m, friction]
    objs = [[sx, BASE_Y, dx * speed, dy * speed, SAQA_R, SAQA_M, FRICTION_SAQA]]
    for a in asyks:
        objs.append([float(a[0]), float(a[1]), 0.0, 0.0, ASYK_R, ASYK_M, FRICTION_ASYK])
    frames = []
    nobj = len(objs)
    for step in range(900):
        moving = False
        for o in objs:
            if o[2] or o[3]:
                o[0] += o[2]
                o[1] += o[3]
                o[2] *= o[6]
                o[3] *= o[6]
                if o[2] * o[2] + o[3] * o[3] < 0.0025:
                    o[2] = o[3] = 0.0
                else:
                    moving = True
                # қабырғалар
                if o[0] < o[4]:
                    o[0], o[2] = o[4], -o[2] * 0.4
                elif o[0] > W - o[4]:
                    o[0], o[2] = W - o[4], -o[2] * 0.4
                if o[1] < o[4]:
                    o[1], o[3] = o[4], -o[3] * 0.4
                elif o[1] > H - o[4]:
                    o[1], o[3] = H - o[4], -o[3] * 0.4
        # соқтығысулар
        for i in range(nobj):
            a = objs[i]
            for j in range(i + 1, nobj):
                b = objs[j]
                ddx = b[0] - a[0]
                ddy = b[1] - a[1]
                rr = a[4] + b[4]
                d2 = ddx * ddx + ddy * ddy
                if d2 >= rr * rr or d2 == 0.0:
                    continue
                d = math.sqrt(d2)
                nx, ny = ddx / d, ddy / d
                rel = (a[2] - b[2]) * nx + (a[3] - b[3]) * ny
                if rel > 0:
                    jimp = (1.0 + 0.82) * rel / (1.0 / a[5] + 1.0 / b[5])
                    a[2] -= jimp / a[5] * nx
                    a[3] -= jimp / a[5] * ny
                    b[2] += jimp / b[5] * nx
                    b[3] += jimp / b[5] * ny
                    moving = True
                over = (rr - d) / 2.0
                a[0] -= nx * over
                a[1] -= ny * over
                b[0] += nx * over
                b[1] += ny * over
        if step % record_every == 0:
            frames.append([[round(o[0], 1), round(o[1], 1)] for o in objs])
        if not moving:
            break
    frames.append([[round(o[0], 1), round(o[1], 1)] for o in objs])
    return [[o[0], o[1]] for o in objs[1:]], frames


def _outside(p) -> bool:
    return (p[0] - CX) ** 2 + (p[1] - CY) ** 2 > R * R


def legal_moves(s):
    return [] if s["over"] else ["shot"]


def apply_move(s: dict, shot: dict) -> dict:
    """shot = {"sx", "dx", "dy", "power"}"""
    if s["over"]:
        raise ValueError("game over")
    p = s["turn"]
    final, frames = simulate(s["asyks"], float(shot["sx"]), float(shot["dx"]), float(shot["dy"]),
                             float(shot["power"]))
    keep, got = [], 0
    for pos in final:
        if _outside(pos):
            got += 1
        else:
            keep.append([round(pos[0], 2), round(pos[1], 2)])
    s["asyks"] = keep
    s["captured"][p] += got
    s["shots"] += 1
    s["moves"].append(f"{'⚪⚫'[p]}+{got}")
    s["last"] = {"frames": frames, "shooter": p, "got": got, "id": s["shots"]}
    if got == 0:
        s["turn"] = 1 - p
    if not keep or s["shots"] >= MAX_SHOTS:
        s["over"] = True
        s["reason"] = "score"
        a, b = s["captured"]
        s["winner"] = 0 if a > b else 1 if b > a else -1
    # 2 ойыншыда да ұтыс мүмкін болмаса (көпшілігі алынған) — ерте аяқтау
    elif max(s["captured"]) > s["total"] / 2:
        s["over"] = True
        s["reason"] = "score"
        s["winner"] = 0 if s["captured"][0] > s["captured"][1] else 1
    return s


def play(s, shot):
    return apply_move(clone(s), shot)


# ---------------------------------------------------------------- ИИ

LEVELS = {"easy": (3, 0.09, 800), "medium": (10, 0.035, 1200), "hard": (24, 0.012, 1600),
          "master": (45, 0.0, 2000)}


def _candidate(s, rng):
    asyks = s["asyks"]
    # шеңбер шетіне жақын асықтар қолайлы
    weights = [1.0 + math.hypot(a[0] - CX, a[1] - CY) / R * 2 for a in asyks]
    tgt = rng.choices(asyks, weights=weights)[0]
    sx = min(SX_MAX, max(SX_MIN, tgt[0] + rng.uniform(-160, 160)))
    off = rng.uniform(-ASYK_R * 0.9, ASYK_R * 0.9)
    dx, dy = tgt[0] + off - sx, tgt[1] - BASE_Y
    return {"sx": round(sx, 1), "dx": dx, "dy": dy, "power": round(rng.uniform(0.55, 1.0), 3)}


def best_shot(s: dict, level: str = "medium", rng=None) -> dict:
    rng = rng or random.Random()
    k, noise, _ = LEVELS.get(level, LEVELS["medium"])
    best, best_score = None, -1.0
    for _ in range(k):
        c = _candidate(s, rng)
        final, _f = simulate(s["asyks"], c["sx"], c["dx"], c["dy"], c["power"], record_every=10_000)
        got = sum(1 for p in final if _outside(p))
        score = got + rng.random() * 0.1
        if score > best_score:
            best, best_score = c, score
    if noise:
        ang = math.atan2(best["dy"], best["dx"]) + rng.gauss(0, noise)
        best["dx"], best["dy"] = math.cos(ang), math.sin(ang)
        best["power"] = min(1.0, max(0.3, best["power"] + rng.gauss(0, noise * 2)))
    return best


def describe(s, player):
    lines = [f"Field 600x800, ring center (300,300) radius 140. You shoot from y=700, x in 80..520.",
             f"Your captured: {s['captured'][player]}, opponent: {s['captured'][1 - player]}.",
             "Asyks inside the ring (index: x,y):"]
    for i, a in enumerate(s["asyks"]):
        lines.append(f"{i + 1}: {a[0]:.0f},{a[1]:.0f}")
    return "\n".join(lines)
