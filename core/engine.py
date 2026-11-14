"""Тоғызқұмалақ — ойын логикасы және ИИ (minimax + alpha-beta).

Тақта: pits[0..17]. 0..8 — Ақ (player 0) отаулары, 9..17 — Қара (player 1) отаулары.
Құмалақтар индекс өсу бағытымен (сағат тіліне қарсы) таратылады.
tuzdyk[p] — p ойыншысына тиесілі түздықтың индексі (қарсыластың жағында) немесе -1.
"""
from __future__ import annotations

import copy
import random
import time

N = 9
TOTAL = 162
WIN = 81


def new_state() -> dict:
    return {
        "pits": [9] * 18,
        "kazan": [0, 0],
        "tuzdyk": [-1, -1],
        "turn": 0,
        "over": False,
        "winner": None,  # 0 / 1 / -1 (тең) / None
        "reason": None,  # score / nomoves / resign / timeout
        "moves": [],     # нотация: "76", "34x", "52X"
        "last": None,    # {"from": idx, "to": idx, "player": p, "cap": n, "tuz": bool}
    }


def clone(s: dict) -> dict:
    return copy.deepcopy(s)


def legal_moves(s: dict) -> list[int]:
    if s["over"]:
        return []
    p = s["turn"]
    base = p * N
    return [i for i in range(N) if s["pits"][base + i] > 0]


def _finish_if_needed(s: dict) -> None:
    k = s["kazan"]
    if k[0] > WIN or k[1] > WIN:
        s["over"] = True
        s["winner"] = 0 if k[0] > k[1] else 1
        s["reason"] = "score"
        return
    if k[0] == WIN and k[1] == WIN:
        s["over"] = True
        s["winner"] = -1
        s["reason"] = "score"
        return
    # Жүретін ойыншыда құмалақ жоқ — қалғаны қарсыластың қазанына түседі
    p = s["turn"]
    if not any(s["pits"][p * N + i] for i in range(N)):
        o = 1 - p
        rest = sum(s["pits"][o * N + i] for i in range(N))
        for i in range(N):
            s["pits"][o * N + i] = 0
        s["kazan"][o] += rest
        s["over"] = True
        s["reason"] = "nomoves"
        if s["kazan"][0] == s["kazan"][1]:
            s["winner"] = -1
        else:
            s["winner"] = 0 if s["kazan"][0] > s["kazan"][1] else 1


def apply_move(s: dict, move: int, notation: bool = True) -> dict:
    """move — 0..8 (ойыншының өз отауының нөмірі). Жаңа күй қайтарады."""
    if s["over"]:
        raise ValueError("game over")
    p = s["turn"]
    idx = p * N + move
    pits = s["pits"]
    n = pits[idx]
    if n == 0:
        raise ValueError("empty pit")
    tz = s["tuzdyk"]
    pits[idx] = 0

    def drop(pos: int) -> None:
        if pos == tz[0]:
            s["kazan"][0] += 1
        elif pos == tz[1]:
            s["kazan"][1] += 1
        else:
            pits[pos] += 1

    if n == 1:
        pos = (idx + 1) % 18
        drop(pos)
    else:
        pos = idx
        drop(pos)
        for _ in range(n - 1):
            pos = (pos + 1) % 18
            drop(pos)

    cap = 0
    made_tuz = False
    if pos // N != p and pos not in tz:
        c = pits[pos]
        if c % 2 == 0:
            cap = c
            s["kazan"][p] += c
            pits[pos] = 0
        elif (
            c == 3
            and tz[p] == -1
            and pos % N != N - 1
            and (tz[1 - p] == -1 or tz[1 - p] % N != pos % N)
        ):
            tz[p] = pos
            cap = 3
            made_tuz = True
            s["kazan"][p] += 3
            pits[pos] = 0

    s["last"] = {"from": idx, "to": pos, "player": p, "cap": cap, "tuz": made_tuz}
    if notation:
        mark = "X" if made_tuz else ("x" if cap else "")
        s["moves"].append(f"{move + 1}{pos % N + 1}{mark}")
    s["turn"] = 1 - p
    _finish_if_needed(s)
    return s


def play(s: dict, move: int) -> dict:
    return apply_move(clone(s), move)


# ---------------------------------------------------------------- ИИ

def _fast_apply(pits, kazan, tz, p, move):
    """Жылдам нұсқа (іздеу үшін). Тізімдерді орнында өзгертеді."""
    idx = p * N + move
    n = pits[idx]
    pits[idx] = 0
    t0, t1 = tz
    if n == 1:
        pos = idx + 1
        if pos == 18:
            pos = 0
        if pos == t0:
            kazan[0] += 1
        elif pos == t1:
            kazan[1] += 1
        else:
            pits[pos] += 1
    else:
        pos = idx
        for _ in range(n):
            if pos == t0:
                kazan[0] += 1
            elif pos == t1:
                kazan[1] += 1
            else:
                pits[pos] += 1
            pos += 1
            if pos == 18:
                pos = 0
        pos = pos - 1 if pos else 17
    if pos // N != p and pos != t0 and pos != t1:
        c = pits[pos]
        if c % 2 == 0:
            kazan[p] += c
            pits[pos] = 0
        elif c == 3 and tz[p] == -1 and pos % N != 8 and (tz[1 - p] == -1 or tz[1 - p] % N != pos % N):
            tz[p] = pos
            kazan[p] += 3
            pits[pos] = 0


def _evaluate(pits, kazan, tz, p):
    o = 1 - p
    score = (kazan[p] - kazan[o]) * 10
    # Түздық құндылығы
    if tz[p] != -1:
        score += 25
    if tz[o] != -1:
        score -= 25
    # Өз жағындағы құмалақтар — болашақ ресурс
    mine = sum(pits[p * N:(p + 1) * N])
    theirs = sum(pits[o * N:(o + 1) * N])
    score += (mine - theirs) // 3
    return score


def _terminal_score(pits, kazan, p):
    if kazan[p] > WIN:
        return 100000 + kazan[p]
    if kazan[1 - p] > WIN:
        return -100000 - kazan[1 - p]
    return None


class _Timeout(Exception):
    pass


def _negamax(pits, kazan, tz, p, depth, alpha, beta, deadline, counter):
    counter[0] += 1
    if counter[0] & 1023 == 0 and time.time() > deadline:
        raise _Timeout
    t = _terminal_score(pits, kazan, p)
    if t is not None:
        return t
    base = p * N
    moves = [i for i in range(N) if pits[base + i]]
    if not moves:
        o = 1 - p
        rest = sum(pits[o * N:(o + 1) * N])
        k = kazan[:]
        k[o] += rest
        diff = k[p] - k[o]
        return 100000 * (1 if diff > 0 else -1 if diff < 0 else 0) + diff
    if depth == 0:
        return _evaluate(pits, kazan, tz, p)
    # Тәртіп: көп ұтатын жүрістерді алдымен
    scored = []
    for m in moves:
        np_, nk, nt = pits[:], kazan[:], tz[:]
        _fast_apply(np_, nk, nt, p, m)
        scored.append((nk[p] - kazan[p], m, np_, nk, nt))
    scored.sort(key=lambda x: -x[0])
    best = -10**9
    for _, m, np_, nk, nt in scored:
        v = -_negamax(np_, nk, nt, 1 - p, depth - 1, -beta, -alpha, deadline, counter)
        if v > best:
            best = v
        if v > alpha:
            alpha = v
        if alpha >= beta:
            break
    return best


def analyse(s: dict, depth: int = 4, time_limit: float = 3.0) -> list[tuple[int, int]]:
    """Әр заңды жүріс үшін (жүріс, баға) — ең жақсысы бірінші."""
    moves = legal_moves(s)
    if not moves:
        return []
    p = s["turn"]
    deadline = time.time() + time_limit
    results = {m: 0 for m in moves}
    # Iterative deepening
    for d in range(1, depth + 1):
        cur = {}
        try:
            for m in moves:
                pits, kazan, tz = s["pits"][:], s["kazan"][:], s["tuzdyk"][:]
                _fast_apply(pits, kazan, tz, p, m)
                cur[m] = -_negamax(pits, kazan, tz, 1 - p, d - 1, -10**9, 10**9, deadline, [0])
        except _Timeout:
            break
        results = cur
        moves.sort(key=lambda m: -results[m])
    return sorted(results.items(), key=lambda x: -x[1])


LEVELS = {
    # name: (depth, time_limit, randomness, elo)
    "easy": (1, 0.5, 0.45, 800),
    "medium": (3, 1.5, 0.15, 1200),
    "hard": (6, 3.0, 0.0, 1600),
    "master": (8, 6.0, 0.0, 2000),
}


def best_move(s: dict, level: str = "medium") -> int:
    depth, tl, rnd, _ = LEVELS.get(level, LEVELS["medium"])
    moves = legal_moves(s)
    if not moves:
        raise ValueError("no moves")
    if rnd and random.random() < rnd:
        return random.choice(moves)
    res = analyse(s, depth, tl)
    top = res[0][1]
    best = [m for m, v in res if v == top]
    return random.choice(best)


def review_game(moves: list[str], depth: int = 3) -> list[dict]:
    """Ойынды талдау: әр жүрісті ең жақсы жүріспен салыстыру."""
    s = new_state()
    out = []
    for i, mv in enumerate(moves):
        m = int(mv[0]) - 1
        if s["over"]:
            break
        res = dict(analyse(s, depth, 1.0))
        best_m = max(res, key=res.get)
        loss = (res[best_m] - res.get(m, res[best_m])) / 10
        if loss >= 6:
            tag = "blunder"
        elif loss >= 3:
            tag = "mistake"
        elif loss >= 1.5:
            tag = "inaccuracy"
        else:
            tag = "good" if m != best_m else "best"
        out.append({"n": i + 1, "player": s["turn"], "move": mv, "best": best_m + 1,
                    "loss": round(loss, 1), "tag": tag})
        s = play(s, m)
    return out


def replay(moves: list[str], upto: int | None = None) -> dict:
    s = new_state()
    for mv in moves[: upto if upto is not None else len(moves)]:
        s = play(s, int(mv[0]) - 1)
    return s


# ---------------------------------------------------------------- Есептер (puzzles)

def make_puzzle(seed: int) -> dict | None:
    """Кездейсоқ ойыннан «бір жүрісте ең көп ұту» есебін жасау."""
    rng = random.Random(seed)
    for _attempt in range(60):
        s = new_state()
        plies = rng.randint(14, 40)
        for _ in range(plies):
            mv = legal_moves(s)
            if not mv:
                break
            s = play(s, rng.choice(mv))
        if s["over"]:
            continue
        p = s["turn"]
        gains = []
        for m in legal_moves(s):
            t = play(s, m)
            gains.append((t["kazan"][p] - s["kazan"][p] + (20 if t["tuzdyk"][p] != s["tuzdyk"][p] else 0), m))
        gains.sort(reverse=True)
        if len(gains) >= 3 and gains[0][0] >= 10 and gains[0][0] - gains[1][0] >= 6:
            s["moves"] = []
            s["last"] = None
            return {"state": s, "answer": gains[0][1], "gain": gains[0][0]}
    return None
