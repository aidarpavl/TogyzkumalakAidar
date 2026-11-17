"""Деректер қоймасы: SQLite (әдепкі) немесе PostgreSQL / Supabase (DATABASE_URL берілсе).

Кестелер: users, ratings (әр ойынға жеке Elo), games, rooms, chat, presence,
wallet (әрекет / ұпай), payments (Kaspi төлемдері), withdrawals (шығару өтінімдері),
champ_games (чемпионат ойындары), settings.
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

GAMES = ("togyz", "asyk", "doyby", "jamby", "kyzkuu", "tenge", "kokpar", "audaryspak", "kures")

# Чемпионат параметрлері (settings кестесі арқылы өзгертуге болады)
DEFAULTS = {
    "price": "500",           # бір төлем, ₸
    "attempts_per_pay": "3",  # бір төлемге әрекет саны
    "fund_share": "30",       # жүлде қорына, %
    "min_withdraw": "1000",   # шығаруға қажетті ең аз ұпай
    "kaspi_phone": "",
    "kaspi_name": "",
    "kaspi_qr": "",           # base64 PNG/JPEG
    "upgrade_price": "100",   # Қыз қуу: атты бір рет жетілдіру, ₸
    "upgrade_qr": "",         # жетілдіруге бөлек QR (бос болса — kaspi_qr)
}

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
    """CREATE TABLE IF NOT EXISTS ratings (
        username TEXT NOT NULL,
        game TEXT NOT NULL,
        rating INTEGER NOT NULL DEFAULT 1200,
        peak INTEGER NOT NULL DEFAULT 1200,
        games INTEGER NOT NULL DEFAULT 0,
        wins INTEGER NOT NULL DEFAULT 0,
        losses INTEGER NOT NULL DEFAULT 0,
        draws INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (username, game)
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
    """CREATE TABLE IF NOT EXISTS wallet (
        username TEXT PRIMARY KEY,
        attempts INTEGER NOT NULL DEFAULT 0,
        points INTEGER NOT NULL DEFAULT 0,
        earned INTEGER NOT NULL DEFAULT 0,
        paid_total INTEGER NOT NULL DEFAULT 0,
        champ_wins INTEGER NOT NULL DEFAULT 0,
        champ_losses INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS payments (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        amount INTEGER NOT NULL,
        attempts INTEGER NOT NULL,
        receipt TEXT,
        image TEXT,
        status TEXT NOT NULL,
        admin TEXT,
        note TEXT,
        created DOUBLE PRECISION NOT NULL,
        decided DOUBLE PRECISION
    )""",
    """CREATE TABLE IF NOT EXISTS withdrawals (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        points INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        phone TEXT NOT NULL,
        status TEXT NOT NULL,
        admin TEXT,
        created DOUBLE PRECISION NOT NULL,
        decided DOUBLE PRECISION
    )""",
    """CREATE TABLE IF NOT EXISTS champ_games (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        game TEXT NOT NULL,
        level TEXT NOT NULL,
        status TEXT NOT NULL,
        result TEXT,
        points INTEGER NOT NULL DEFAULT 0,
        created DOUBLE PRECISION NOT NULL,
        finished DOUBLE PRECISION
    )""",
    """CREATE TABLE IF NOT EXISTS horses (
        username TEXT PRIMARY KEY,
        burst DOUBLE PRECISION NOT NULL DEFAULT 1,
        speed DOUBLE PRECISION NOT NULL DEFAULT 1,
        stamina DOUBLE PRECISION NOT NULL DEFAULT 1,
        reverse DOUBLE PRECISION NOT NULL DEFAULT 1,
        bonus INTEGER NOT NULL DEFAULT 0,
        upgrades INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_games_white ON games(white)",
    "CREATE INDEX IF NOT EXISTS idx_games_black ON games(black)",
    "CREATE INDEX IF NOT EXISTS idx_chat_room ON chat(room)",
    "CREATE INDEX IF NOT EXISTS idx_rooms_status ON rooms(status)",
    "CREATE INDEX IF NOT EXISTS idx_ratings_game ON ratings(game, rating)",
    "CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)",
    "CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status)",
]

# Бұрынғы базаға қосылатын бағандар
MIGRATIONS = [
    ("games", "game", "TEXT NOT NULL DEFAULT 'togyz'"),
    ("rooms", "game", "TEXT NOT NULL DEFAULT 'togyz'"),
    ("payments", "kind", "TEXT NOT NULL DEFAULT 'attempts'"),
    ("payments", "qty", "INTEGER NOT NULL DEFAULT 1"),
    ("horses", "t_speed", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "t_stamina", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "t_accuracy", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "t_bonus", "INTEGER NOT NULL DEFAULT 0"),
    ("horses", "k_speed", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "k_accel", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "k_stamina", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "k_power", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "k_agility", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "k_bonus", "INTEGER NOT NULL DEFAULT 0"),
    ("horses", "a_stability", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "a_agility", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "a_stamina", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "a_power", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "a_grip", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "a_balance", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "a_bonus", "INTEGER NOT NULL DEFAULT 0"),
    ("horses", "w_power", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "w_grip", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "w_stamina", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "w_balance", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "w_technique", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "w_speed", "DOUBLE PRECISION NOT NULL DEFAULT 1"),
    ("horses", "w_bonus", "INTEGER NOT NULL DEFAULT 0"),
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
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()


def init() -> None:
    global _INIT
    if _INIT:
        return
    for q in SCHEMA:
        execute(q if _PG else q.replace("DOUBLE PRECISION", "REAL"))
    for table, col, decl in MIGRATIONS:
        try:
            if _PG:
                execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {decl}")
            else:
                cols = [r["name"] for r in execute(f"PRAGMA table_info({table})", fetch="all")]
                if col not in cols:
                    execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        except Exception:  # noqa: BLE001
            pass
    _INIT = True


def new_id(n: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


# ---------------------------------------------------------------- Settings

def get_setting(key: str) -> str:
    r = execute("SELECT value FROM settings WHERE key = ?", (key,), "one")
    return r["value"] if r else DEFAULTS.get(key, "")


def set_setting(key: str, value: str) -> None:
    execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (key, str(value)))


def int_setting(key: str) -> int:
    try:
        return int(get_setting(key))
    except ValueError:
        return int(DEFAULTS[key])


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


# ---------------------------------------------------------------- Ratings

def get_rating(username: str, game: str) -> dict:
    r = execute("SELECT * FROM ratings WHERE username = ? AND game = ?", (username, game), "one")
    return r or {"username": username, "game": game, "rating": 1200, "peak": 1200, "games": 0,
                 "wins": 0, "losses": 0, "draws": 0}


def leaderboard(game: str, limit: int = 100) -> list[dict]:
    return execute(
        "SELECT username, rating, peak, games, wins, losses, draws FROM ratings "
        "WHERE game = ? AND games > 0 ORDER BY rating DESC, wins DESC LIMIT ?",
        (game, limit), "all")


def user_rank(username: str, game: str) -> int | None:
    r = get_rating(username, game)
    if not r["games"]:
        return None
    c = execute("SELECT COUNT(*) AS c FROM ratings WHERE game = ? AND games > 0 AND rating > ?",
                (game, r["rating"]), "one")
    return c["c"] + 1


def _apply_result(username: str, game: str, delta: int, result: str) -> None:
    col = {"win": "wins", "loss": "losses", "draw": "draws"}[result]
    execute("INSERT INTO ratings (username, game) VALUES (?, ?) ON CONFLICT (username, game) DO NOTHING",
            (username, game))
    execute(
        f"UPDATE ratings SET rating = rating + ?, games = games + 1, {col} = {col} + 1, "
        f"peak = CASE WHEN rating + ? > peak THEN rating + ? ELSE peak END WHERE username = ? AND game = ?",
        (delta, delta, delta, username, game))


def elo(ra: int, rb: int, score_a: float, k: int = 32) -> tuple[int, int]:
    ea = 1 / (1 + 10 ** ((rb - ra) / 400))
    da = round(k * (score_a - ea))
    return da, -da


def record_game(game: str, mode: str, white: str, black: str, state: dict, score: list[int],
                white_reg: bool, black_reg: bool, rated: bool, ai_elo: int | None = None) -> dict:
    w = state["winner"]
    result = "1-0" if w == 0 else "0-1" if w == 1 else "½-½"
    sw = 1.0 if w == 0 else 0.0 if w == 1 else 0.5
    rw = rb = None
    dw = db_ = 0
    uw = get_user(white) if white_reg else None
    ub = get_user(black) if black_reg else None
    if rated:
        rw = get_rating(uw["username"], game)["rating"] if uw else (ai_elo or 1200)
        rb = get_rating(ub["username"], game)["rating"] if ub else (ai_elo or 1200)
        k = 32 if (uw and ub) else 20
        dw, db_ = elo(rw, rb, sw, k)
        res_w = "win" if sw == 1 else "loss" if sw == 0 else "draw"
        res_b = "win" if sw == 0 else "loss" if sw == 1 else "draw"
        if uw:
            _apply_result(uw["username"], game, dw, res_w)
        if ub:
            _apply_result(ub["username"], game, db_, res_b)
    execute(
        "INSERT INTO games (id, game, mode, white, black, result, reason, score_w, score_b, moves, "
        "rating_w, rating_b, delta_w, delta_b, created) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (new_id(10), game, mode, white, black, result, state.get("reason"), int(score[0]), int(score[1]),
         " ".join(state.get("moves", [])), rw, rb, dw if (uw and rated) else None, db_ if (ub and rated) else None,
         time.time()))
    return {"delta_w": dw, "delta_b": db_}


def user_games(username: str, game: str | None = None, limit: int = 50) -> list[dict]:
    if game:
        return execute("SELECT * FROM games WHERE game = ? AND (white = ? OR black = ?) "
                       "ORDER BY created DESC LIMIT ?", (game, username, username, limit), "all")
    return execute("SELECT * FROM games WHERE white = ? OR black = ? ORDER BY created DESC LIMIT ?",
                   (username, username, limit), "all")


def recent_games(game: str, limit: int = 20) -> list[dict]:
    return execute("SELECT * FROM games WHERE game = ? AND mode = 'online' ORDER BY created DESC LIMIT ?",
                   (game, limit), "all")


def rating_history(username: str, game: str, limit: int = 200) -> list[int]:
    rows = execute(
        "SELECT white, black, rating_w, rating_b, delta_w, delta_b FROM games WHERE game = ? AND "
        "((white = ? AND delta_w IS NOT NULL AND rating_w IS NOT NULL) OR "
        "(black = ? AND delta_b IS NOT NULL AND rating_b IS NOT NULL)) "
        "ORDER BY created ASC LIMIT ?", (game, username, username, limit), "all")
    return [(r["rating_w"] + r["delta_w"]) if r["white"] == username else (r["rating_b"] + r["delta_b"])
            for r in rows]


# ---------------------------------------------------------------- Presence

def touch(name: str) -> None:
    execute("INSERT INTO presence (name, ts) VALUES (?, ?) ON CONFLICT (name) DO UPDATE SET ts = excluded.ts",
            (name, time.time()))


def online_count(window: int = 300) -> int:
    r = execute("SELECT COUNT(*) AS c FROM presence WHERE ts > ?", (time.time() - window,), "one")
    return r["c"] if r else 0


# ---------------------------------------------------------------- Rooms

def create_room(game: str, host: str, host_guest: bool, color: str, state: dict, rated: bool,
                private: bool, tc: int) -> str:
    rid = new_id()
    now = time.time()
    if color == "random":
        color = secrets.choice(["white", "black"])
    white, black = (host, None) if color == "white" else (None, host)
    execute(
        "INSERT INTO rooms (id, game, white, black, white_guest, black_guest, state, status, rated, private, tc, "
        "clock_w, clock_b, last_ts, created, updated) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (rid, game, white, black, int(host_guest and color == "white"), int(host_guest and color == "black"),
         json.dumps(state), "waiting", int(rated and not host_guest), int(private), tc, tc, tc, 0, now, now))
    return rid


def get_room(rid: str) -> dict | None:
    r = execute("SELECT * FROM rooms WHERE id = ?", (rid.upper(),), "one")
    if r:
        r["state"] = json.loads(r["state"])
    return r


def open_rooms(game: str) -> list[dict]:
    return execute(
        "SELECT * FROM rooms WHERE game = ? AND status = 'waiting' AND private = 0 AND updated > ? "
        "ORDER BY created DESC", (game, time.time() - 1800), "all")


def active_rooms(game: str) -> list[dict]:
    return execute(
        "SELECT * FROM rooms WHERE game = ? AND status = 'active' AND updated > ? ORDER BY updated DESC LIMIT 30",
        (game, time.time() - 1800), "all")


def join_room(rid: str, name: str, guest: bool) -> bool:
    r = get_room(rid)
    if not r or r["status"] != "waiting" or name in (r["white"], r["black"]):
        return False
    now = time.time()
    side = "white" if r["white"] is None else "black"
    n = execute(f"UPDATE rooms SET {side} = ?, {side}_guest = ?, status = 'active', last_ts = ?, updated = ?, "
                f"rated = rated * ? WHERE id = ? AND status = 'waiting'",
                (name, int(guest), now, now, int(not guest), r["id"]))
    return bool(n)


def save_room_state(room: dict, state: dict, clock_w: float, clock_b: float) -> bool:
    now = time.time()
    status = "finished" if state["over"] else room["status"]
    n = execute(
        "UPDATE rooms SET state = ?, status = ?, clock_w = ?, clock_b = ?, last_ts = ?, updated = ?, "
        "version = version + 1 WHERE id = ? AND version = ?",
        (json.dumps(state), status, clock_w, clock_b, now, now, room["id"], room["version"]))
    return bool(n)


def patch_room_state(rid: str, state: dict) -> None:
    execute("UPDATE rooms SET state = ? WHERE id = ?", (json.dumps(state), rid))


def cancel_room(rid: str) -> None:
    execute("UPDATE rooms SET status = 'cancelled', updated = ? WHERE id = ? AND status = 'waiting'",
            (time.time(), rid))


def user_active_rooms(name: str, game: str) -> list[dict]:
    return execute(
        "SELECT * FROM rooms WHERE game = ? AND (white = ? OR black = ?) AND status IN ('waiting', 'active') "
        "ORDER BY updated DESC", (game, name, name), "all")


# ---------------------------------------------------------------- Chat

def add_chat(room: str, author: str, body: str) -> None:
    body = body.strip()[:300]
    if body:
        execute("INSERT INTO chat (id, room, author, body, ts) VALUES (?,?,?,?,?)",
                (new_id(12), room, author, body, time.time()))


def get_chat(room: str, limit: int = 40) -> list[dict]:
    rows = execute("SELECT * FROM chat WHERE room = ? ORDER BY ts DESC LIMIT ?", (room, limit), "all")
    return list(reversed(rows))


# ---------------------------------------------------------------- Wallet / чемпионат

def _ensure_wallet(username: str) -> None:
    execute("INSERT INTO wallet (username) VALUES (?) ON CONFLICT (username) DO NOTHING", (username,))


def get_wallet(username: str) -> dict:
    _ensure_wallet(username)
    return execute("SELECT * FROM wallet WHERE username = ?", (username,), "one")


def add_attempts(username: str, n: int) -> None:
    _ensure_wallet(username)
    execute("UPDATE wallet SET attempts = attempts + ? WHERE username = ?", (n, username))


def start_champ(username: str, game: str, level: str) -> str | None:
    """Әрекетті «кепілге» алады. Жеңсе немесе тең түссе — қайтарылады, жеңілсе немесе тастап кетсе — жанады."""
    _ensure_wallet(username)
    # Аяқталмаған ойындар — жеңіліс
    for g in execute("SELECT id FROM champ_games WHERE username = ? AND status = 'active'", (username,), "all"):
        finish_champ(g["id"], "loss", 0)
    n = execute("UPDATE wallet SET attempts = attempts - 1 WHERE username = ? AND attempts >= 1", (username,))
    if not n:
        return None
    cid = new_id(10)
    execute("INSERT INTO champ_games (id, username, game, level, status, created) VALUES (?,?,?,?,?,?)",
            (cid, username, game, level, "active", time.time()))
    return cid


def finish_champ(cid: str, result: str, points: int) -> bool:
    row = execute("SELECT * FROM champ_games WHERE id = ?", (cid,), "one")
    if not row:
        return False
    n = execute("UPDATE champ_games SET status = 'done', result = ?, points = ?, finished = ? "
                "WHERE id = ? AND status = 'active'", (result, points if result == "win" else 0, time.time(), cid))
    if not n:
        return False
    u = row["username"]
    if result == "win":
        execute("UPDATE wallet SET attempts = attempts + 1, points = points + ?, earned = earned + ?, "
                "champ_wins = champ_wins + 1 WHERE username = ?", (points, points, u))
    elif result == "draw":
        execute("UPDATE wallet SET attempts = attempts + 1 WHERE username = ?", (u,))
    else:
        execute("UPDATE wallet SET champ_losses = champ_losses + 1 WHERE username = ?", (u,))
    return True


def champ_leaderboard(limit: int = 100) -> list[dict]:
    return execute("SELECT * FROM wallet WHERE earned > 0 OR champ_losses > 0 "
                   "ORDER BY earned DESC, champ_wins DESC LIMIT ?", (limit,), "all")


def champ_history(username: str, limit: int = 30) -> list[dict]:
    return execute("SELECT * FROM champ_games WHERE username = ? ORDER BY created DESC LIMIT ?",
                   (username, limit), "all")


# ---------------------------------------------------------------- Payments

def create_payment(username: str, receipt: str, image_b64: str | None, kind: str = "attempts",
                   qty: int = 1, code: str = "") -> str:
    """kind: 'attempts' — чемпионат әрекеттері (әкімші растайды);
    'upg_<stat>' — атты жетілдіру: бірден қолданылады (әкімші кейін болдырмауы мүмкін)."""
    pid = new_id(10)
    qty = max(1, min(50, int(qty)))
    now = time.time()
    if kind == "attempts":
        # Kaspi түсініктемесіндегі «1» коды — әрекеттер бірден беріледі (әкімші кейін болдырмауы мүмкін)
        auto = str(code).strip() == "1"
        amount, att, status = int_setting("price"), int_setting("attempts_per_pay"), "approved" if auto else "pending"
        qty = 1
    else:
        amount, att, status = int_setting("upgrade_price") * qty, 0, "approved"
    execute("INSERT INTO payments (id, username, amount, attempts, receipt, image, status, created, kind, qty, admin, decided) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (pid, username, amount, att, receipt.strip()[:100], image_b64, status, now, kind, qty,
             "auto" if status == "approved" else None, now if status == "approved" else None))
    if status == "approved":
        _ensure_wallet(username)
        if kind == "attempts":
            execute("UPDATE wallet SET attempts = attempts + ?, paid_total = paid_total + ? WHERE username = ?",
                    (att, amount, username))
        else:
            upgrade_horse(username, kind[4:], qty)
            execute("UPDATE wallet SET paid_total = paid_total + ? WHERE username = ?", (amount, username))
    return pid


def revoke_payment(pid: str, admin: str) -> bool:
    """Автоматты жетілдіруді болдырмау: төлем келмесе, ат көрсеткіші қайта азаяды."""
    row = execute("SELECT * FROM payments WHERE id = ?", (pid,), "one")
    if not row:
        return False
    n = execute("UPDATE payments SET status = 'revoked', admin = ?, decided = ? WHERE id = ? AND status = 'approved'",
                (admin, time.time(), pid))
    if n and (row.get("kind") or "attempts") == "attempts":
        execute("UPDATE wallet SET attempts = CASE WHEN attempts > ? THEN attempts - ? ELSE 0 END, "
                "paid_total = paid_total - ? WHERE username = ?",
                (row["attempts"], row["attempts"], row["amount"], row["username"]))
        return True
    if n:
        stat = row["kind"][4:]
        if stat in HORSE_STATS:
            f = 1.05 ** int(row.get("qty") or 1)
            execute(f"UPDATE horses SET {stat} = {stat} / ?, upgrades = upgrades - ? WHERE username = ?",
                    (f, int(row.get("qty") or 1), row["username"]))
        execute("UPDATE wallet SET paid_total = paid_total - ? WHERE username = ?", (row["amount"], row["username"]))
    return bool(n)


def payments(status: str | None = None, username: str | None = None, limit: int = 100) -> list[dict]:
    q = "SELECT * FROM payments WHERE 1=1"
    p: list = []
    if status:
        q += " AND status = ?"
        p.append(status)
    if username:
        q += " AND username = ?"
        p.append(username)
    q += " ORDER BY created DESC LIMIT ?"
    p.append(limit)
    return execute(q, tuple(p), "all")


def receipt_used(receipt: str) -> bool:
    r = execute("SELECT COUNT(*) AS c FROM payments WHERE receipt = ? AND status <> 'rejected'",
                (receipt.strip(),), "one")
    return bool(r and r["c"])


def decide_payment(pid: str, approve: bool, admin: str, note: str = "") -> bool:
    row = execute("SELECT * FROM payments WHERE id = ?", (pid,), "one")
    if not row:
        return False
    n = execute("UPDATE payments SET status = ?, admin = ?, note = ?, decided = ? WHERE id = ? AND status = 'pending'",
                ("approved" if approve else "rejected", admin, note, time.time(), pid))
    if n and approve:
        _ensure_wallet(row["username"])
        kind = row.get("kind") or "attempts"
        if kind.startswith("upg_"):
            upgrade_horse(row["username"], kind[4:], int(row.get("qty") or 1))
            execute("UPDATE wallet SET paid_total = paid_total + ? WHERE username = ?",
                    (row["amount"], row["username"]))
        else:
            execute("UPDATE wallet SET attempts = attempts + ?, paid_total = paid_total + ? WHERE username = ?",
                    (row["attempts"], row["amount"], row["username"]))
    return bool(n)


# ---------------------------------------------------------------- Қыз қуу: ат

HORSE_STATS = ("burst", "speed", "stamina", "reverse", "t_speed", "t_stamina", "t_accuracy",
               "k_speed", "k_accel", "k_stamina", "k_power", "k_agility",
               "a_stability", "a_agility", "a_stamina", "a_power", "a_grip", "a_balance",
               "w_power", "w_grip", "w_stamina", "w_balance", "w_technique", "w_speed")
BONUS_COLS = ("bonus", "t_bonus", "k_bonus", "a_bonus", "w_bonus")


def get_horse(username: str) -> dict:
    execute("INSERT INTO horses (username) VALUES (?) ON CONFLICT (username) DO NOTHING", (username,))
    return execute("SELECT * FROM horses WHERE username = ?", (username,), "one")


def upgrade_horse(username: str, stat: str, times: int = 1, pct: float = 5.0) -> None:
    if stat not in HORSE_STATS:
        return
    get_horse(username)
    f = (1 + pct / 100.0) ** max(1, int(times))
    execute(f"UPDATE horses SET {stat} = {stat} * ?, upgrades = upgrades + ? WHERE username = ?",
            (f, int(times), username))


def boost_horse(username: str, stats: tuple, pct: float) -> None:
    """Жеңіс бонусы — таңдаусыз, барлық көрсеткішке бірден +pct%."""
    get_horse(username)
    f = 1 + pct / 100.0
    sets = ", ".join(f"{k} = {k} * ?" for k in stats if k in HORSE_STATS)
    if sets:
        execute(f"UPDATE horses SET {sets} WHERE username = ?", tuple([f] * len(stats)) + (username,))


def add_horse_bonus(username: str, pct: int, col: str = "bonus") -> None:
    if col not in BONUS_COLS:
        return
    get_horse(username)
    execute(f"UPDATE horses SET {col} = {col} + ? WHERE username = ?", (int(pct), username))


def apply_horse_bonus(username: str, stat: str, col: str = "bonus") -> int:
    """Жиналған бонус %-ын таңдалған көрсеткішке қосу."""
    h = get_horse(username)
    if stat not in HORSE_STATS or col not in BONUS_COLS or (h.get(col) or 0) <= 0:
        return 0
    b = h[col]
    n = execute(f"UPDATE horses SET {stat} = {stat} * ?, {col} = 0 WHERE username = ? AND {col} = ?",
                (1 + b / 100.0, username, b))
    return b if n else 0


# ---------------------------------------------------------------- Fund / withdrawals

def fund_stats() -> dict:
    paid = execute("SELECT COALESCE(SUM(amount), 0) AS s FROM payments WHERE status = 'approved'", (), "one")["s"]
    out = execute("SELECT COALESCE(SUM(amount), 0) AS s FROM withdrawals WHERE status = 'paid'", (), "one")["s"]
    reserved = execute("SELECT COALESCE(SUM(amount), 0) AS s FROM withdrawals WHERE status = 'pending'",
                       (), "one")["s"]
    pts = execute("SELECT COALESCE(SUM(points), 0) AS s FROM wallet", (), "one")["s"]
    fund = int(paid) * int_setting("fund_share") // 100
    return {"paid": int(paid), "fund": fund, "paid_out": int(out), "reserved": int(reserved),
            "available": max(0, fund - int(out) - int(reserved)), "points_total": int(pts)}


def withdrawal_quote(username: str) -> int:
    """Ойыншының ұпай үлесіне сәйкес жүлде қорынан сома (₸)."""
    w = get_wallet(username)
    st = fund_stats()
    if w["points"] <= 0 or st["points_total"] <= 0:
        return 0
    return st["available"] * w["points"] // st["points_total"]


def request_withdrawal(username: str, phone: str) -> tuple[bool, str]:
    w = get_wallet(username)
    if w["points"] < int_setting("min_withdraw"):
        return False, "min"
    if execute("SELECT id FROM withdrawals WHERE username = ? AND status = 'pending'", (username,), "one"):
        return False, "pending"
    amount = withdrawal_quote(username)
    if amount < 1:
        return False, "fund"
    pts = w["points"]
    n = execute("UPDATE wallet SET points = points - ? WHERE username = ? AND points = ?", (pts, username, pts))
    if not n:
        return False, "retry"
    execute("INSERT INTO withdrawals (id, username, points, amount, phone, status, created) VALUES (?,?,?,?,?,?,?)",
            (new_id(10), username, pts, amount, phone, "pending", time.time()))
    return True, str(amount)


def payment_summary(username: str) -> dict:
    """Шығаруды тексеру үшін: ойыншының төлем тарихы."""
    rows = execute("SELECT status, admin, amount FROM payments WHERE username = ?", (username,), "all")
    return {"approved": sum(r["amount"] for r in rows if r["status"] == "approved"),
            "auto": sum(1 for r in rows if r["status"] == "approved" and r["admin"] == "auto"),
            "manual": sum(1 for r in rows if r["status"] == "approved" and r["admin"] not in (None, "auto")),
            "revoked": sum(1 for r in rows if r["status"] == "revoked"),
            "pending": sum(1 for r in rows if r["status"] == "pending")}


def withdrawals(status: str | None = None, username: str | None = None, limit: int = 100) -> list[dict]:
    q = "SELECT * FROM withdrawals WHERE 1=1"
    p: list = []
    if status:
        q += " AND status = ?"
        p.append(status)
    if username:
        q += " AND username = ?"
        p.append(username)
    q += " ORDER BY created DESC LIMIT ?"
    p.append(limit)
    return execute(q, tuple(p), "all")


def decide_withdrawal(wid: str, paid: bool, admin: str) -> bool:
    row = execute("SELECT * FROM withdrawals WHERE id = ?", (wid,), "one")
    if not row:
        return False
    n = execute("UPDATE withdrawals SET status = ?, admin = ?, decided = ? WHERE id = ? AND status = 'pending'",
                ("paid" if paid else "rejected", admin, time.time(), wid))
    if n and not paid:
        execute("UPDATE wallet SET points = points + ? WHERE username = ?", (row["points"], row["username"]))
    return bool(n)
