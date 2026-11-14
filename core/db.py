"""Деректер қоймасы: SQLite (әдепкі) немесе PostgreSQL (DATABASE_URL берілсе).

Streamlit Community Cloud-та файлдық жүйе қайта іске қосқанда тазаланады,
сондықтан тұрақты рейтинг үшін Supabase/Neon сияқты тегін PostgreSQL ұсынылады.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import string
import threading
import time

_lock = threading.Lock()
_URL = None
_PG = False
_INIT = False

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        lname TEXT UNIQUE NOT NULL,
        pw_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        rating INTEGER NOT NULL DEFAULT 1200,
        peak INTEGER NOT NULL DEFAULT 1200,
        games INTEGER NOT NULL DEFAULT 0,
        wins INTEGER NOT NULL DEFAULT 0,
        losses INTEGER NOT NULL DEFAULT 0,
        draws INTEGER NOT NULL DEFAULT 0,
        created DOUBLE PRECISION NOT NULL,
        last_seen DOUBLE PRECISION NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS rooms (
        id TEXT PRIMARY KEY,
        white TEXT,
        black TEXT,
        white_guest INTEGER NOT NULL DEFAULT 0,
        black_guest INTEGER NOT NULL DEFAULT 0,
        state TEXT NOT NULL,
        status TEXT NOT NULL,
        rated INTEGER NOT NULL DEFAULT 1,
        private INTEGER NOT NULL DEFAULT 0,
        tc INTEGER NOT NULL DEFAULT 0,
        clock_w DOUBLE PRECISION NOT NULL DEFAULT 0,
        clock_b DOUBLE PRECISION NOT NULL DEFAULT 0,
        last_ts DOUBLE PRECISION NOT NULL DEFAULT 0,
        version INTEGER NOT NULL DEFAULT 0,
        created DOUBLE PRECISION NOT NULL,
        updated DOUBLE PRECISION NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS games (
        id TEXT PRIMARY KEY,
        mode TEXT NOT NULL,
        white TEXT NOT NULL,
        black TEXT NOT NULL,
        result TEXT NOT NULL,
        reason TEXT,
        score_w INTEGER NOT NULL,
        score_b INTEGER NOT NULL,
        moves TEXT NOT NULL,
        rating_w INTEGER,
        rating_b INTEGER,
        delta_w INTEGER,
        delta_b INTEGER,
        created DOUBLE PRECISION NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS chat (
        id TEXT PRIMARY KEY,
        room TEXT NOT NULL,
        author TEXT NOT NULL,
        body TEXT NOT NULL,
        ts DOUBLE PRECISION NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS presence (
        name TEXT PRIMARY KEY,
        ts DOUBLE PRECISION NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_games_white ON games(white)",
    "CREATE INDEX IF NOT EXISTS idx_games_black ON games(black)",
    "CREATE INDEX IF NOT EXISTS idx_chat_room ON chat(room)",
    "CREATE INDEX IF NOT EXISTS idx_rooms_status ON rooms(status)",
]


def configure(url: str | None) -> None:
    global _URL, _PG
    _URL = url or os.environ.get("DATABASE_URL") or "sqlite:///togyz.db"
    _PG = _URL.startswith("postgres")


def _connect():
    if _URL is None:
        configure(None)
    if _PG:
        import psycopg2  # noqa: WPS433

        return psycopg2.connect(_URL)
    path = _URL.replace("sqlite:///", "", 1)
    con = sqlite3.connect(path, timeout=15, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    return con


def _sql(q: str) -> str:
    return q.replace("?", "%s") if _PG else q


def execute(q: str, params: tuple = (), fetch: str | None = None):
    with _lock:
        con = _connect()
        try:
            cur = con.cursor()
            cur.execute(_sql(q), params)
            res = None
            if fetch == "one":
                row = cur.fetchone()
                if row is not None:
                    cols = [d[0] for d in cur.description]
                    res = dict(zip(cols, row))
            elif fetch == "all":
                cols = [d[0] for d in cur.description]
                res = [dict(zip(cols, r)) for r in cur.fetchall()]
            else:
                res = cur.rowcount
            con.commit()
            return res
        finally:
            con.close()


def init() -> None:
    global _INIT
    if _INIT:
        return
    for q in SCHEMA:
        execute(q if _PG else q.replace("DOUBLE PRECISION", "REAL"))
    _INIT = True


def new_id(n: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


# ---------------------------------------------------------------- Users

def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()


def create_user(username: str, password: str) -> bool:
    if get_user(username):
        return False
    salt = secrets.token_hex(16)
    now = time.time()
    execute(
        "INSERT INTO users (username, lname, pw_hash, salt, created, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
        (username, username.casefold(), _hash(password, salt), salt, now, now),
    )
    return True


def get_user(username: str) -> dict | None:
    return execute("SELECT * FROM users WHERE lname = ?", (username.casefold(),), "one")


def check_login(username: str, password: str) -> dict | None:
    u = get_user(username)
    if u and hmac.compare_digest(u["pw_hash"], _hash(password, u["salt"])):
        execute("UPDATE users SET last_seen = ? WHERE username = ?", (time.time(), u["username"]))
        return u
    return None


def change_password(username: str, new_password: str) -> None:
    salt = secrets.token_hex(16)
    execute("UPDATE users SET pw_hash = ?, salt = ? WHERE username = ?",
            (_hash(new_password, salt), salt, username))


def leaderboard(limit: int = 100) -> list[dict]:
    return execute(
        "SELECT username, rating, peak, games, wins, losses, draws FROM users "
        "WHERE games > 0 ORDER BY rating DESC, wins DESC LIMIT ?",
        (limit,), "all")


def user_rank(username: str) -> int | None:
    u = get_user(username)
    if not u or not u["games"]:
        return None
    r = execute("SELECT COUNT(*) AS c FROM users WHERE games > 0 AND rating > ?", (u["rating"],), "one")
    return r["c"] + 1


# ---------------------------------------------------------------- Presence

def touch(name: str) -> None:
    execute("INSERT INTO presence (name, ts) VALUES (?, ?) ON CONFLICT (name) DO UPDATE SET ts = excluded.ts",
            (name, time.time()))


def online_count(window: int = 300) -> int:
    r = execute("SELECT COUNT(*) AS c FROM presence WHERE ts > ?", (time.time() - window,), "one")
    return r["c"] if r else 0


# ---------------------------------------------------------------- Elo

def elo(ra: int, rb: int, score_a: float, k: int = 32) -> tuple[int, int]:
    ea = 1 / (1 + 10 ** ((rb - ra) / 400))
    da = round(k * (score_a - ea))
    return da, -da


def _apply_result(username: str, delta: int, result: str) -> None:
    col = {"win": "wins", "loss": "losses", "draw": "draws"}[result]
    execute(
        f"UPDATE users SET rating = rating + ?, games = games + 1, {col} = {col} + 1, "
        f"peak = CASE WHEN rating + ? > peak THEN rating + ? ELSE peak END WHERE username = ?",
        (delta, delta, delta, username))


def record_game(mode: str, white: str, black: str, state: dict,
                white_reg: bool, black_reg: bool, rated: bool,
                ai_elo: int | None = None) -> dict:
    """Ойынды сақтап, рейтингті жаңарту. Қайтарады: {'delta_w', 'delta_b'}."""
    w = state["winner"]
    result = "1-0" if w == 0 else "0-1" if w == 1 else "½-½"
    sw = 1.0 if w == 0 else 0.0 if w == 1 else 0.5
    rw = rb = None
    dw = db = 0
    uw = get_user(white) if white_reg else None
    ub = get_user(black) if black_reg else None
    if rated:
        rw = uw["rating"] if uw else (ai_elo or 1200)
        rb = ub["rating"] if ub else (ai_elo or 1200)
        k = 32 if (uw and ub) else 20
        dw, db = elo(rw, rb, sw, k)
        res_w = "win" if sw == 1 else "loss" if sw == 0 else "draw"
        res_b = "win" if sw == 0 else "loss" if sw == 1 else "draw"
        if uw:
            _apply_result(uw["username"], dw, res_w)
        if ub:
            _apply_result(ub["username"], db, res_b)
    execute(
        "INSERT INTO games (id, mode, white, black, result, reason, score_w, score_b, moves, "
        "rating_w, rating_b, delta_w, delta_b, created) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (new_id(10), mode, white, black, result, state.get("reason"), state["kazan"][0], state["kazan"][1],
         " ".join(state["moves"]), rw, rb, dw if uw else None, db if ub else None, time.time()))
    return {"delta_w": dw, "delta_b": db}


def user_games(username: str, limit: int = 50) -> list[dict]:
    return execute(
        "SELECT * FROM games WHERE white = ? OR black = ? ORDER BY created DESC LIMIT ?",
        (username, username, limit), "all")


def recent_games(limit: int = 20) -> list[dict]:
    return execute("SELECT * FROM games WHERE mode = 'online' ORDER BY created DESC LIMIT ?", (limit,), "all")


def rating_history(username: str, limit: int = 200) -> list[int]:
    rows = execute(
        "SELECT white, black, rating_w, rating_b, delta_w, delta_b FROM games "
        "WHERE (white = ? AND delta_w IS NOT NULL) OR (black = ? AND delta_b IS NOT NULL) "
        "ORDER BY created ASC LIMIT ?", (username, username, limit), "all")
    out = []
    for r in rows:
        if r["white"] == username:
            out.append(r["rating_w"] + r["delta_w"])
        else:
            out.append(r["rating_b"] + r["delta_b"])
    return out


# ---------------------------------------------------------------- Rooms (онлайн)

def create_room(host: str, host_guest: bool, color: str, state: dict, rated: bool,
                private: bool, tc: int) -> str:
    rid = new_id()
    now = time.time()
    if color == "random":
        color = secrets.choice(["white", "black"])
    white, black = (host, None) if color == "white" else (None, host)
    execute(
        "INSERT INTO rooms (id, white, black, white_guest, black_guest, state, status, rated, private, tc, "
        "clock_w, clock_b, last_ts, created, updated) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (rid, white, black, int(host_guest and color == "white"), int(host_guest and color == "black"),
         json.dumps(state), "waiting", int(rated and not host_guest), int(private), tc, tc, tc, 0, now, now))
    return rid


def get_room(rid: str) -> dict | None:
    r = execute("SELECT * FROM rooms WHERE id = ?", (rid.upper(),), "one")
    if r:
        r["state"] = json.loads(r["state"])
    return r


def open_rooms() -> list[dict]:
    rows = execute(
        "SELECT * FROM rooms WHERE status = 'waiting' AND private = 0 AND updated > ? ORDER BY created DESC",
        (time.time() - 1800,), "all")
    return rows


def active_rooms() -> list[dict]:
    return execute(
        "SELECT * FROM rooms WHERE status = 'active' AND updated > ? ORDER BY updated DESC LIMIT 30",
        (time.time() - 1800,), "all")


def join_room(rid: str, name: str, guest: bool) -> bool:
    r = get_room(rid)
    if not r or r["status"] != "waiting":
        return False
    if name in (r["white"], r["black"]):
        return False
    now = time.time()
    if r["white"] is None:
        n = execute("UPDATE rooms SET white = ?, white_guest = ?, status = 'active', last_ts = ?, updated = ?, "
                    "rated = rated * ? WHERE id = ? AND status = 'waiting'",
                    (name, int(guest), now, now, int(not guest), r["id"]))
    else:
        n = execute("UPDATE rooms SET black = ?, black_guest = ?, status = 'active', last_ts = ?, updated = ?, "
                    "rated = rated * ? WHERE id = ? AND status = 'waiting'",
                    (name, int(guest), now, now, int(not guest), r["id"]))
    return bool(n)


def save_room_state(room: dict, state: dict, clock_w: float, clock_b: float) -> bool:
    """Оптимистік құлыптау: version сәйкес келсе ғана сақтайды."""
    now = time.time()
    status = "finished" if state["over"] else room["status"]
    n = execute(
        "UPDATE rooms SET state = ?, status = ?, clock_w = ?, clock_b = ?, last_ts = ?, updated = ?, "
        "version = version + 1 WHERE id = ? AND version = ?",
        (json.dumps(state), status, clock_w, clock_b, now, now, room["id"], room["version"]))
    return bool(n)


def cancel_room(rid: str) -> None:
    execute("UPDATE rooms SET status = 'cancelled', updated = ? WHERE id = ? AND status = 'waiting'",
            (time.time(), rid))


def user_active_rooms(name: str) -> list[dict]:
    return execute(
        "SELECT * FROM rooms WHERE (white = ? OR black = ?) AND status IN ('waiting', 'active') "
        "ORDER BY updated DESC", (name, name), "all")


# ---------------------------------------------------------------- Chat

def add_chat(room: str, author: str, body: str) -> None:
    body = body.strip()[:300]
    if body:
        execute("INSERT INTO chat (id, room, author, body, ts) VALUES (?,?,?,?,?)",
                (new_id(12), room, author, body, time.time()))


def get_chat(room: str, limit: int = 40) -> list[dict]:
    rows = execute("SELECT * FROM chat WHERE room = ? ORDER BY ts DESC LIMIT ?", (room, limit), "all")
    return list(reversed(rows))
