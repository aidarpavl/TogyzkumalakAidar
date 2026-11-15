"""Дойбы (шашки): орыс 8×8 және халықаралық 10×10 ережелері + ИИ.

Тақта: board[r*n + c]. r=0 — жоғары (қаралар жағы), r=n-1 — төмен (ақтар жағы).
Мәндер: 0 бос, 1 ақ дала, 2 ақ дамка, -1 қара дала, -2 қара дамка.
turn: 0 — ақ, 1 — қара. Ақ бірінші жүреді.
Жүріс: {"path": [idx, ...], "cap": [idx, ...]}.
"""
from __future__ import annotations

import copy
import random
import time

VARIANTS = {
    "russian": {"n": 8, "rows": 3, "max_capture": False, "promote_mid": True},
    "international": {"n": 10, "rows": 4, "max_capture": True, "promote_mid": False},
}
DIRS = ((-1, -1), (-1, 1), (1, -1), (1, 1))


def new_state(variant: str = "russian") -> dict:
    v = VARIANTS[variant]
    n = v["n"]
    b = [0] * (n * n)
    for r in range(n):
        for c in range(n):
            if (r + c) % 2 == 1:
                if r < v["rows"]:
                    b[r * n + c] = -1
                elif r >= n - v["rows"]:
                    b[r * n + c] = 1
    return {"game": "doyby", "variant": variant, "n": n, "board": b, "turn": 0, "over": False, "winner": None,
            "reason": None, "moves": [], "last": None, "quiet": 0, "ply": 0}


def clone(s: dict) -> dict:
    return copy.deepcopy(s)


def sq_name(idx: int, n: int) -> str:
    r, c = divmod(idx, n)
    return f"{'abcdefghij'[c]}{n - r}"


def _sign(p: int) -> int:
    return 0 if p == 0 else (1 if p > 0 else -1)


def _captures_from(b, n, start, piece, promote_mid):
    """Барлық соғу тізбектері: [(path, caps)]."""
    me = _sign(piece)
    results = []

    def dfs(pos, king, path, caps):
        r, c = divmod(pos, n)
        found = False
        for dr, dc in DIRS:
            if king:
                rr, cc = r + dr, c + dc
                while 0 <= rr < n and 0 <= cc < n and b[rr * n + cc] == 0:
                    rr += dr
                    cc += dc
                if not (0 <= rr < n and 0 <= cc < n):
                    continue
                mid = rr * n + cc
                if _sign(b[mid]) != -me or mid in caps:
                    continue
                lands = []
                rr += dr
                cc += dc
                while 0 <= rr < n and 0 <= cc < n and b[rr * n + cc] == 0:
                    lands.append(rr * n + cc)
                    rr += dr
                    cc += dc
                if not lands:
                    continue
                # Жалғасы бар қондыру нүктелері басым
                cont = [l for l in lands if _can_continue(b, n, l, True, caps + [mid], me)]
                for land in (cont or lands):
                    found = True
                    dfs(land, True, path + [land], caps + [mid])
            else:
                mr, mc = r + dr, c + dc
                lr, lc = r + 2 * dr, c + 2 * dc
                if not (0 <= lr < n and 0 <= lc < n):
                    continue
                mid, land = mr * n + mc, lr * n + lc
                if _sign(b[mid]) == -me and mid not in caps and b[land] == 0:
                    found = True
                    last_row = 0 if me > 0 else n - 1
                    nk = promote_mid and lr == last_row
                    dfs(land, nk, path + [land], caps + [mid])
        if not found and caps:
            results.append((path, caps))

    b[start] = 0
    try:
        dfs(start, abs(piece) == 2, [start], [])
    finally:
        b[start] = piece
    return results


def _can_continue(b, n, pos, king, caps, me):
    r, c = divmod(pos, n)
    for dr, dc in DIRS:
        rr, cc = r + dr, c + dc
        if king:
            while 0 <= rr < n and 0 <= cc < n and b[rr * n + cc] == 0:
                rr += dr
                cc += dc
        if not (0 <= rr < n and 0 <= cc < n):
            continue
        mid = rr * n + cc
        if _sign(b[mid]) != -me or mid in caps:
            continue
        lr, lc = rr + dr, cc + dc
        if 0 <= lr < n and 0 <= lc < n and b[lr * n + lc] == 0:
            return True
    return False


def _gen(b, n, turn, variant):
    v = VARIANTS[variant]
    me = 1 if turn == 0 else -1
    caps = []
    for i, p in enumerate(b):
        if _sign(p) == me:
            caps.extend(_captures_from(b, n, i, p, v["promote_mid"]))
    if caps:
        if v["max_capture"]:
            m = max(len(cp) for _, cp in caps)
            caps = [x for x in caps if len(x[1]) == m]
        # Бірдей жолдарды жою
        seen, out = set(), []
        for path, cp in caps:
            k = (tuple(path), tuple(sorted(cp)))
            if k not in seen:
                seen.add(k)
                out.append({"path": path, "cap": cp})
        return out
    moves = []
    fwd = -1 if me > 0 else 1
    for i, p in enumerate(b):
        if _sign(p) != me:
            continue
        r, c = divmod(i, n)
        if abs(p) == 2:
            for dr, dc in DIRS:
                rr, cc = r + dr, c + dc
                while 0 <= rr < n and 0 <= cc < n and b[rr * n + cc] == 0:
                    moves.append({"path": [i, rr * n + cc], "cap": []})
                    rr += dr
                    cc += dc
        else:
            for dc in (-1, 1):
                rr, cc = r + fwd, c + dc
                if 0 <= rr < n and 0 <= cc < n and b[rr * n + cc] == 0:
                    moves.append({"path": [i, rr * n + cc], "cap": []})
    return moves


def legal_moves(s: dict) -> list[dict]:
    if s["over"]:
        return []
    return _gen(s["board"], s["n"], s["turn"], s["variant"])


def _do(b, n, mv, variant):
    v = VARIANTS[variant]
    path, caps = mv["path"], mv["cap"]
    piece = b[path[0]]
    b[path[0]] = 0
    me = _sign(piece)
    last_row = 0 if me > 0 else n - 1
    king = abs(piece) == 2
    if v["promote_mid"] and not king:
        for sq in path[1:]:
            if sq // n == last_row:
                king = True
                break
    elif not king and path[-1] // n == last_row:
        king = True
    for cpos in caps:
        b[cpos] = 0
    b[path[-1]] = me * (2 if king else 1)
    return abs(piece) == 2


def notation(mv: dict, n: int) -> str:
    sep = ":" if mv["cap"] else "-"
    return sep.join(sq_name(i, n) for i in mv["path"])


def apply_move(s: dict, mv: dict) -> dict:
    legal = legal_moves(s)
    match = None
    for m in legal:
        if m["path"] == list(mv["path"]) and (not mv.get("cap") or sorted(m["cap"]) == sorted(mv["cap"])):
            match = m
            break
    if match is None:
        raise ValueError("illegal move")
    n = s["n"]
    was_king = _do(s["board"], n, match, s["variant"])
    s["moves"].append(notation(match, n))
    s["last"] = {"path": match["path"], "cap": match["cap"]}
    s["quiet"] = s["quiet"] + 1 if (was_king and not match["cap"]) else 0
    s["ply"] += 1
    s["turn"] = 1 - s["turn"]
    _check_end(s)
    return s


def play(s: dict, mv: dict) -> dict:
    return apply_move(clone(s), mv)


def _check_end(s):
    if not legal_moves(s):
        s["over"] = True
        s["winner"] = 1 - s["turn"]
        s["reason"] = "nomoves"
    elif s["quiet"] >= 30 or s["ply"] >= 400:
        s["over"] = True
        s["winner"] = -1
        s["reason"] = "draw_rule"


def counts(s):
    b = s["board"]
    return [sum(1 for p in b if p > 0), sum(1 for p in b if p < 0)]


# ---------------------------------------------------------------- ИИ

def _eval(b, n, me):
    score = 0
    for i, p in enumerate(b):
        if p == 0:
            continue
        r, c = divmod(i, n)
        val = 100 if abs(p) == 1 else 320
        if abs(p) == 1:
            adv = (n - 1 - r) if p > 0 else r
            val += adv * 4
            if 2 <= c <= n - 3:
                val += 4
            if (p > 0 and r == n - 1) or (p < 0 and r == 0):
                val += 6  # артқы қатар қорғанысы
        score += val if _sign(p) == me else -val
    return score


class _TO(Exception):
    pass


def _search(b, n, turn, variant, depth, alpha, beta, deadline, cnt):
    cnt[0] += 1
    if cnt[0] & 511 == 0 and time.time() > deadline:
        raise _TO
    me = 1 if turn == 0 else -1
    moves = _gen(b, n, turn, variant)
    if not moves:
        return -100000 - depth
    if depth <= 0 and not moves[0]["cap"]:
        return _eval(b, n, me)
    if depth <= -6:
        return _eval(b, n, me)
    moves.sort(key=lambda m: -len(m["cap"]))
    best = -10**9
    for m in moves:
        nb = b[:]
        _do(nb, n, m, variant)
        v = -_search(nb, n, 1 - turn, variant, depth - 1, -beta, -alpha, deadline, cnt)
        if v > best:
            best = v
        if v > alpha:
            alpha = v
        if alpha >= beta:
            break
    return best


def analyse(s, depth=4, time_limit=2.0):
    moves = legal_moves(s)
    if not moves:
        return []
    if len(moves) == 1:
        return [(moves[0], 0)]
    deadline = time.time() + time_limit
    res = [(m, 0) for m in moves]
    for d in range(1, depth + 1):
        cur = []
        try:
            for m, _ in res:
                nb = s["board"][:]
                _do(nb, s["n"], m, s["variant"])
                v = -_search(nb, s["n"], 1 - s["turn"], s["variant"], d - 1, -10**9, 10**9, deadline, [0])
                cur.append((m, v))
        except _TO:
            break
        cur.sort(key=lambda x: -x[1])
        res = cur
    return res


LEVELS = {"easy": (1, 0.3, 0.4, 800), "medium": (3, 1.0, 0.1, 1200), "hard": (5, 2.5, 0.0, 1600),
          "master": (8, 5.0, 0.0, 2000)}


def best_move(s, level="medium"):
    depth, tl, rnd, _ = LEVELS.get(level, LEVELS["medium"])
    moves = legal_moves(s)
    if rnd and random.random() < rnd:
        return random.choice(moves)
    res = analyse(s, depth, tl)
    top = res[0][1]
    return random.choice([m for m, v in res if v == top])
