"""Тоғызқұмалақ онлайн — Streamlit қосымшасы."""
from __future__ import annotations

import datetime as dt
import json
import random
import re
import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core import db, engine, llm
from core.i18n import RULES, t

st.set_page_config(page_title="Тоғызқұмалақ онлайн", page_icon="🟤", layout="wide",
                   initial_sidebar_state="collapsed")

# ---------------------------------------------------------------- Init


def _secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:  # secrets.toml жоқ
        return default


db.configure(_secret("DATABASE_URL"))
db.init()

ss = st.session_state
ss.setdefault("lang", "kz")
ss.setdefault("user", None)          # аты
ss.setdefault("guest", False)
ss.setdefault("game", None)          # ИИ / жергілікті ойын
ss.setdefault("room", None)          # онлайн бөлме коды
ss.setdefault("puzzle_i", 0)
ss.setdefault("puzzles_solved", 0)
ss.setdefault("board_theme", "light")
ss.setdefault("show_numbers", True)
ss.setdefault("show_stones", True)
ss.setdefault("button_mode", False)
ss.setdefault("llm", None)           # {"provider","kind","base","model","key"}

if ss.llm is None and _secret("LLM_API_KEY"):
    prov = _secret("LLM_PROVIDER", "OpenAI (ChatGPT)")
    p = llm.PROVIDERS.get(prov, llm.PROVIDERS["OpenAI (ChatGPT)"])
    ss.llm = {"provider": prov, "kind": p["kind"], "base": _secret("LLM_BASE_URL", p["base"]),
              "model": _secret("LLM_MODEL", p["model"]), "key": _secret("LLM_API_KEY")}


def tr(key: str, **kw) -> str:
    return t(key, ss.lang, **kw)


_board = components.declare_component("togyz_board", path=str(Path(__file__).parent / "components" / "board"))

# ---------------------------------------------------------------- Стиль

st.markdown("""
<style>
#MainMenu, footer, [data-testid="stToolbar"] {visibility: hidden;}
.block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1200px;}
.hero {background: linear-gradient(120deg, #5c3518 0%, #a5642a 55%, #e0a458 100%); color: #fff8ec;
       border-radius: 18px; padding: 14px 20px; margin-bottom: 10px; box-shadow: 0 6px 18px #0003;}
.hero h1 {margin: 0; font-size: clamp(22px, 5vw, 34px); color: #fff8ec; padding: 0;}
.hero p {margin: 2px 0 0; opacity: .9; font-size: clamp(12px, 3.2vw, 15px);}
.ornament {height: 10px; margin: 6px 0 2px; border-radius: 6px;
  background: repeating-linear-gradient(90deg, #f5b041 0 12px, transparent 12px 18px, #f5b041 18px 22px, transparent 22px 30px);
  opacity: .8;}
.card {background: var(--secondary-background-color, #f6efe6); border-radius: 14px; padding: 12px 14px; margin-bottom: 10px;
       border: 1px solid #0000000f;}
.podium {display: flex; gap: 10px; justify-content: center; align-items: flex-end; margin: 6px 0 14px;}
.podium div {flex: 1; max-width: 200px; text-align: center; border-radius: 14px 14px 4px 4px; padding: 10px 6px; color: #fff;
             box-shadow: 0 4px 12px #0003; font-weight: 700;}
.podium .p1 {background: linear-gradient(#f7c948, #c99a06); min-height: 130px;}
.podium .p2 {background: linear-gradient(#cfd8dc, #90a4ae); min-height: 105px;}
.podium .p3 {background: linear-gradient(#e0a070, #a0522d); min-height: 90px;}
.podium .r {font-size: 13px; opacity: .95; font-weight: 600;}
.movelist {font-family: ui-monospace, monospace; font-size: 14px; line-height: 1.7; max-height: 260px; overflow-y: auto;}
.movelist b {color: #a5642a;}
.result {text-align: center; font-size: clamp(18px, 5vw, 26px); font-weight: 800; padding: 10px; border-radius: 14px;
         background: linear-gradient(90deg, #f5b04133, #2ecc7133); margin: 6px 0;}
div[role="radiogroup"] {flex-wrap: wrap; gap: 4px;}
div[role="radiogroup"] > label {background: #a5642a14; border-radius: 999px; padding: 4px 12px !important; margin: 0 !important;}
.st-key-movebtns [data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important; gap: 3px !important;}
.st-key-movebtns [data-testid="stColumn"], .st-key-movebtns [data-testid="column"] {
    min-width: 0 !important; width: auto !important; flex: 1 1 0 !important;}
.st-key-movebtns button {padding: 4px 0 !important; min-height: 38px;}
@media (max-width: 640px) {
  .block-container {padding-left: .45rem; padding-right: .45rem; padding-top: .6rem;}
  .hero {padding: 10px 12px; border-radius: 14px;}
  [data-testid="stMetricValue"] {font-size: 1.2rem;}
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- Көмекшілер

def board(state: dict, bottom: int, names: list[str], clickable: bool, key: str,
          message: str = "", clocks=None, clock_running: bool = False):
    """Тақтаны көрсетеді. Басылған жаңа жүрісті (0..8) немесе None қайтарады."""
    ss["_tok"] = ss.get("_tok", 0) + 1
    legal = engine.legal_moves(state) if clickable else []
    view = {k: state[k] for k in ("pits", "kazan", "tuzdyk", "turn", "over", "last", "moves")}
    val = _board(state=view, bottom=bottom, names=names, clickable=clickable and not ss.button_mode,
                 legal=legal, message=message, theme=ss.board_theme, show_numbers=ss.show_numbers,
                 show_stones=ss.show_stones, animate=True, clocks=clocks, clock_running=clock_running,
                 token=ss["_tok"], key=key, default=None)
    move = None
    if val and val.get("nonce") != ss.get(f"_nonce_{key}"):
        ss[f"_nonce_{key}"] = val["nonce"]
        if val.get("move") in legal:
            move = val["move"]
    if ss.button_mode and clickable and state["turn"] == bottom:
        with st.container(key="movebtns"):
            cols = st.columns(9)
            for i, c in enumerate(cols):
                if c.button(str(i + 1), key=f"{key}_b{i}", disabled=i not in legal, use_container_width=True):
                    move = i
    return move


def lvl_name(level: str) -> str:
    return tr(f"lv_{level}")


def result_text(state: dict, me: int | None, names: list[str]) -> str:
    w = state["winner"]
    reason = tr(f"reason_{state.get('reason') or 'score'}")
    if w == -1:
        head = tr("draw")
    elif me is None:
        head = tr("winner_is", name=names[w])
    else:
        head = tr("you_win") if w == me else tr("you_lose")
    return f"{head}<br><small>{state['kazan'][0]} : {state['kazan'][1]} — {reason}</small>"


def move_list_html(moves: list[str]) -> str:
    if not moves:
        return "<div class='movelist'>—</div>"
    parts = []
    for i in range(0, len(moves), 2):
        pair = moves[i:i + 2]
        parts.append(f"<b>{i // 2 + 1}.</b> {pair[0]} {pair[1] if len(pair) > 1 else ''}")
    return "<div class='movelist'>" + "<br>".join(parts) + "</div>"


def last_move_msg(state: dict, names: list[str]) -> str:
    lm = state.get("last")
    if not lm:
        return tr("click_pit")
    s = f"{tr('last_move')}: {names[lm['player']]} — {state['moves'][-1] if state['moves'] else ''}"
    if lm.get("tuz"):
        s += " · ✕ " + tr("tuzdyk_made")
    elif lm.get("cap"):
        s += " · " + tr("captured", n=lm["cap"])
    return s


def is_registered() -> bool:
    return bool(ss.user) and not ss.guest


# ---------------------------------------------------------------- Шапка

def header():
    c1, c2 = st.columns([5, 2], vertical_alignment="center")
    with c1:
        st.markdown(f"<div class='hero'><h1>⚫⚪ {tr('title')}</h1><p>{tr('subtitle')}</p>"
                    f"<div class='ornament'></div></div>", unsafe_allow_html=True)
    with c2:
        if st.button(tr("lang_btn"), use_container_width=True, key="lang_toggle"):
            ss.lang = "ru" if ss.lang == "kz" else "kz"
            st.rerun()
        if ss.user:
            badge = "👤" if not ss.guest else "🎭"
            info = f"{badge} **{ss.user}**"
            if is_registered():
                u = db.get_user(ss.user)
                if u:
                    info += f" · ⭐ {u['rating']}"
            st.markdown(info)
            st.caption(f"🟢 {tr('online_now')}: {db.online_count()}")


# ---------------------------------------------------------------- Кіру беті

NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі0-9_]{3,20}$")


def auth_page():
    st.markdown(f"#### {tr('welcome_text')}")
    demo = engine.new_state()
    board(demo, 0, [tr("white"), tr("black")], False, key="demo_board")
    col1, col2 = st.columns([3, 2])
    with col1:
        tab_login, tab_reg = st.tabs([tr("login"), tr("register")])
        with tab_login:
            with st.form("login_form"):
                u = st.text_input(tr("username"))
                p = st.text_input(tr("password"), type="password")
                if st.form_submit_button(tr("login"), type="primary", use_container_width=True):
                    user = db.check_login(u.strip(), p)
                    if user:
                        ss.user, ss.guest = user["username"], False
                        st.rerun()
                    else:
                        st.error(tr("login_bad"))
        with tab_reg:
            with st.form("reg_form"):
                u = st.text_input(tr("username"), key="r_u")
                p1 = st.text_input(tr("password"), type="password", key="r_p1")
                p2 = st.text_input(tr("password2"), type="password", key="r_p2")
                if st.form_submit_button(tr("register"), type="primary", use_container_width=True):
                    u = u.strip()
                    if not NAME_RE.match(u):
                        st.error(tr("reg_bad_name"))
                    elif len(p1) < 6:
                        st.error(tr("reg_bad_pw"))
                    elif p1 != p2:
                        st.error(tr("reg_mismatch"))
                    elif not db.create_user(u, p1):
                        st.error(tr("reg_exists"))
                    else:
                        ss.user, ss.guest = u, False
                        st.success(tr("reg_ok"))
                        st.rerun()
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"**🎭 {tr('guest')}**")
        st.caption(tr("guest_note"))
        if st.button(tr("as_guest"), use_container_width=True, key="guest_btn"):
            ss.user = f"{tr('guest')}-{random.randint(1000, 9999)}"
            ss.guest = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        top = db.leaderboard(5)
        if top:
            st.markdown(f"**🏆 {tr('lb_title')}**")
            for i, r in enumerate(top, 1):
                st.markdown(f"{i}. **{r['username']}** — {r['rating']}")


# ---------------------------------------------------------------- ИИ / жергілікті ойын

def start_ai_game(level: str, color: str, rated: bool):
    human = {"white": 0, "black": 1}.get(color, random.choice([0, 1]))
    ai_name = f"🤖 {lvl_name(level)}"
    names = [ss.user, ai_name] if human == 0 else [ai_name, ss.user]
    ss.game = {"mode": "ai", "state": engine.new_state(), "human": human, "level": level,
               "rated": rated and is_registered() and level != "llm", "names": names,
               "history": [], "recorded": False, "delta": None, "hint": None, "coach": None, "note": None}


def start_local_game(n1: str, n2: str):
    ss.game = {"mode": "local", "state": engine.new_state(), "human": None, "level": None, "rated": False,
               "names": [n1 or tr("white"), n2 or tr("black")], "history": [], "recorded": False,
               "delta": None, "hint": None, "coach": None, "note": None}


def ai_pick(g: dict) -> int:
    s = g["state"]
    if g["level"] == "llm" and ss.llm:
        try:
            m = llm.choose_move(ss.llm, s, engine.legal_moves(s))
            if m is not None:
                return m
        except Exception:  # noqa: BLE001
            pass
        g["note"] = tr("llm_fallback")
        return engine.best_move(s, "hard")
    return engine.best_move(s, g["level"] if g["level"] in engine.LEVELS else "medium")


def finish_local(g: dict):
    if g["recorded"] or not g["state"]["over"]:
        return
    g["recorded"] = True
    if g["mode"] == "ai" and is_registered():
        human = g["human"]
        ai_elo = engine.LEVELS.get(g["level"], (0, 0, 0, 1200))[3]
        w, b = g["names"]
        res = db.record_game("ai", w, b, g["state"], white_reg=human == 0, black_reg=human == 1,
                             rated=g["rated"], ai_elo=ai_elo)
        g["delta"] = res["delta_w"] if human == 0 else res["delta_b"]
    if g["mode"] == "ai" and g["state"]["winner"] == g["human"]:
        st.balloons()


def game_view():
    g = ss.game
    s = g["state"]
    local = g["mode"] == "local"
    bottom = s["turn"] if local and not s["over"] else (g["human"] if not local else 0)
    my_turn = (not s["over"]) and (local or s["turn"] == g["human"])

    left, right = st.columns([3, 1.25])
    with left:
        msg = tr("ai_thinking") if (not my_turn and not s["over"]) else last_move_msg(s, g["names"])
        mv = board(s, bottom, g["names"], my_turn, key="game_board", message=msg)
        if mv is not None and my_turn:
            g["history"].append(engine.clone(s))
            g["state"] = engine.play(s, mv)
            g["hint"] = g["coach"] = g["note"] = None
            st.rerun()
        if s["over"]:
            finish_local(g)
            me = None if local else g["human"]
            st.markdown(f"<div class='result'>{result_text(s, me, g['names'])}</div>", unsafe_allow_html=True)
            if g.get("delta"):
                st.markdown(f"<center><b>{tr('rating_change', d=g['delta'])}</b></center>", unsafe_allow_html=True)
        if g.get("note"):
            st.info(g["note"])
        if g.get("hint") is not None:
            st.success(tr("hint_text", n=g["hint"] + 1))
        if g.get("coach"):
            st.markdown(f"<div class='card'>🧠 {g['coach']}</div>", unsafe_allow_html=True)

    with right:
        st.markdown(f"**{tr('moves')}**")
        st.markdown(move_list_html(s["moves"]), unsafe_allow_html=True)
        if not s["over"]:
            b1, b2 = st.columns(2)
            if b1.button(tr("hint"), use_container_width=True, disabled=not my_turn):
                g["hint"] = engine.best_move(s, "hard")
                st.rerun()
            if b2.button(tr("undo"), use_container_width=True, disabled=not g["history"] or g["rated"]):
                g["state"] = g["history"].pop()
                g["hint"] = g["coach"] = None
                st.rerun()
            if st.button(tr("coach_btn"), use_container_width=True, disabled=not my_turn, icon="🧠"):
                if not ss.llm:
                    st.warning(tr("need_key"))
                else:
                    with st.spinner("…"):
                        try:
                            an = engine.analyse(s, 4, 2.0)
                            g["coach"] = llm.coach(ss.llm, s, s["turn"], an, ss.lang)
                        except Exception as e:  # noqa: BLE001
                            g["coach"] = tr("key_fail", e=str(e)[:200])
                    st.rerun()
            with st.popover(tr("resign"), use_container_width=True):
                st.write(tr("resign_confirm"))
                if st.button(tr("yes"), key="resign_yes", type="primary"):
                    loser = s["turn"] if local else g["human"]
                    s["over"], s["winner"], s["reason"] = True, 1 - loser, "resign"
                    st.rerun()
        else:
            if st.button(tr("rematch"), use_container_width=True, type="primary"):
                if local:
                    start_local_game(g["names"][1], g["names"][0])
                else:
                    start_ai_game(g["level"], "black" if g["human"] == 0 else "white", g["rated"])
                st.rerun()
        if st.button(tr("new_game"), use_container_width=True):
            ss.game = None
            st.rerun()

    if s["over"] and s["moves"]:
        with st.expander(tr("analysis")):
            review_block(s["moves"], "local_review")

    # ИИ жүрісі
    if not s["over"] and not local and s["turn"] != g["human"]:
        time.sleep(0.35)
        with st.spinner(tr("ai_thinking")):
            m = ai_pick(g)
        g["state"] = engine.play(g["state"], m)
        st.rerun()


# ---------------------------------------------------------------- Талдау

@st.cache_data(show_spinner=False, max_entries=64)
def _review(moves: tuple[str, ...]):
    return engine.review_game(list(moves), depth=3)


def review_block(moves: list[str], key: str):
    with st.spinner("…"):
        rv = _review(tuple(moves))
    good = sum(1 for r in rv if r["tag"] in ("best", "good"))
    acc_w = [r for r in rv if r["player"] == 0]
    acc_b = [r for r in rv if r["player"] == 1]

    def acc(lst):
        return round(100 * sum(1 for r in lst if r["tag"] in ("best", "good")) / max(1, len(lst)))

    c1, c2, c3 = st.columns(3)
    c1.metric(f"{tr('accuracy')} ⚪", f"{acc(acc_w)}%")
    c2.metric(f"{tr('accuracy')} ⚫", f"{acc(acc_b)}%")
    c3.metric(tr("moves"), len(moves))
    _ = good
    k = st.slider(tr("replay"), 0, len(moves), len(moves), key=f"{key}_slider")
    rs = engine.replay(moves, k)
    board(rs, 0, [tr("white"), tr("black")], False, key=f"{key}_board",
          message=(f"{k}. {moves[k - 1]}" if k else ""))
    rows = []
    for r in rv:
        rows.append({"#": r["n"], "": "⚪" if r["player"] == 0 else "⚫", tr("moves"): r["move"],
                     tr("result"): tr(f"tag_{r['tag']}"),
                     "Δ": r["loss"], tr("best_was", n="").strip(": "): r["best"]})
    st.dataframe(rows, hide_index=True, use_container_width=True, height=260)


# ---------------------------------------------------------------- Онлайн

TC_OPTIONS = [0, 180, 300, 600, 900]


def tc_label(sec: int) -> str:
    return tr("tc_none") if sec == 0 else tr("tc_min", m=sec // 60)


def online_lobby():
    c1, c2 = st.columns([1, 1.3])
    with c1:
        with st.form("create_room"):
            st.markdown(f"**{tr('create_room')}**")
            color = st.radio(tr("color"), ["random", "white", "black"], horizontal=True,
                             format_func=lambda c: tr(f"col_{c}"))
            tc = st.selectbox(tr("time_control"), TC_OPTIONS, index=2, format_func=tc_label)
            rated = st.toggle(tr("rated"), value=is_registered(), disabled=not is_registered())
            private = st.toggle(tr("private"), value=False)
            if st.form_submit_button(tr("create_room"), type="primary", use_container_width=True):
                ss.room = db.create_room(ss.user, ss.guest, color, engine.new_state(), rated, private, tc)
                st.rerun()
        with st.form("join_code"):
            code = st.text_input(tr("join_code"), max_chars=6, placeholder="ABC123")
            if st.form_submit_button(tr("join_by_code"), use_container_width=True):
                r = db.get_room(code.strip())
                if r and (ss.user in (r["white"], r["black"]) or r["status"] in ("active", "finished")):
                    ss.room = r["id"]
                    st.rerun()
                elif r and db.join_room(r["id"], ss.user, ss.guest):
                    ss.room = r["id"]
                    st.rerun()
                else:
                    st.error(tr("room_not_found"))
    with c2:
        lobby_lists()


@st.fragment(run_every=5)
def lobby_lists():
    mine = db.user_active_rooms(ss.user)
    if mine:
        st.markdown(f"**{tr('my_rooms')}**")
        for r in mine:
            opp = r["black"] if r["white"] == ss.user else r["white"]
            cc1, cc2 = st.columns([3, 1], vertical_alignment="center")
            cc1.write(f"`{r['id']}` · {opp or '…'} · {tc_label(r['tc'])}")
            if cc2.button(tr("continue"), key=f"cont_{r['id']}", use_container_width=True):
                ss.room = r["id"]
                st.rerun(scope="app")
    st.markdown(f"**{tr('open_rooms')}**")
    rooms = [r for r in db.open_rooms() if ss.user not in (r["white"], r["black"])]
    if not rooms:
        st.caption(tr("no_rooms"))
    for r in rooms:
        host = r["white"] or r["black"]
        host_color = "⚪" if r["white"] else "⚫"
        hu = db.get_user(host)
        rating = f" ({hu['rating']})" if hu else ""
        cc1, cc2 = st.columns([3, 1], vertical_alignment="center")
        cc1.write(f"{host_color} **{host}**{rating} · {tc_label(r['tc'])} · {'⭐' if r['rated'] else '—'}")
        if cc2.button(tr("join"), key=f"join_{r['id']}", type="primary", use_container_width=True):
            if db.join_room(r["id"], ss.user, ss.guest):
                ss.room = r["id"]
                st.rerun(scope="app")
            else:
                st.error(tr("room_not_found"))
    live = db.active_rooms()
    if live:
        st.markdown(f"**{tr('live_games')}**")
        for r in live[:10]:
            stt = json.loads(r["state"])
            cc1, cc2 = st.columns([3, 1], vertical_alignment="center")
            cc1.write(f"⚪ {r['white']} **{stt['kazan'][0]}** : **{stt['kazan'][1]}** {r['black']} ⚫")
            if cc2.button(tr("watch"), key=f"watch_{r['id']}", use_container_width=True):
                ss.room = r["id"]
                st.rerun(scope="app")


def _live_clocks(room: dict) -> list[float] | None:
    if not room["tc"]:
        return None
    clocks = [room["clock_w"], room["clock_b"]]
    s = room["state"]
    if room["status"] == "active" and not s["over"] and room["last_ts"]:
        clocks[s["turn"]] -= time.time() - room["last_ts"]
    return clocks


def _finalize_online(room: dict, state: dict):
    """Ойын аяқталғанда рейтингті жазу (тек сәтті сақтаған клиент шақырады)."""
    res = db.record_game("online", room["white"], room["black"], state,
                         white_reg=not room["white_guest"], black_reg=not room["black_guest"],
                         rated=bool(room["rated"]))
    state["deltas"] = [res["delta_w"], res["delta_b"]]
    db.execute("UPDATE rooms SET state = ? WHERE id = ?", (json.dumps(state), room["id"]))


def online_room_view():
    room = db.get_room(ss.room)
    if not room:
        ss.room = None
        st.rerun()
    top = st.columns([1, 1, 1])
    if top[0].button(tr("back"), use_container_width=True):
        ss.room = None
        st.rerun()
    st.caption(f"{tr('join_code')}: `{room['id']}` · {tc_label(room['tc'])} · {'⭐ ' + tr('rated') if room['rated'] else ''}")
    left, right = st.columns([3, 1.25])
    with left:
        room_live()
    with right:
        room_side()


@st.fragment(run_every=2)
def room_live():
    room = db.get_room(ss.room)
    if not room:
        return
    s = room["state"]
    me = 0 if room["white"] == ss.user else 1 if room["black"] == ss.user else None
    names = [room["white"] or "…", room["black"] or "…"]
    # Күй өзгерсе (басталды / аяқталды) — бүкіл бетті жаңарту
    phase = (room["status"], s["over"])
    pkey = f"_phase_{room['id']}"
    if ss.get(pkey) is not None and ss[pkey] != phase:
        ss[pkey] = phase
        st.rerun(scope="app")
    ss[pkey] = phase

    if room["status"] == "waiting":
        st.info(f"⏳ {tr('waiting_opp')}")
        st.markdown(tr("invite"))
        st.code(room["id"], language=None)
        try:
            base = st.context.url if hasattr(st.context, "url") else ""
        except Exception:  # noqa: BLE001
            base = ""
        if base:
            st.code(f"{base.split('?')[0]}?room={room['id']}", language=None)
        if me is not None and st.button(tr("cancel"), key="cancel_room"):
            db.cancel_room(room["id"])
            ss.room = None
            st.rerun(scope="app")
        board(s, me if me is not None else 0, names, False, key="room_board_wait")
        return

    clocks = _live_clocks(room)
    # Уақыт бітуі
    if clocks and room["status"] == "active" and not s["over"] and clocks[s["turn"]] <= 0:
        s["over"], s["winner"], s["reason"] = True, 1 - s["turn"], "timeout"
        cw, cb = max(0, clocks[0]), max(0, clocks[1])
        if db.save_room_state(room, s, cw, cb):
            _finalize_online(room, s)
        st.rerun(scope="fragment")

    my_turn = me is not None and not s["over"] and s["turn"] == me and room["status"] == "active"
    if s["over"]:
        msg = ""
    elif me is None:
        msg = tr("spectator") + " · " + tr("turn_of", name=names[s["turn"]])
    else:
        msg = tr("your_turn") if my_turn else tr("opp_turn")
    if s.get("last") and not s["over"]:
        msg += " · " + last_move_msg(s, names)
    mv = board(s, me if me is not None else 0, names, my_turn, key="room_board", message=msg,
               clocks=clocks, clock_running=room["status"] == "active" and not s["over"])
    if mv is not None and my_turn:
        ns = engine.play(s, mv)
        cw, cb = room["clock_w"], room["clock_b"]
        if room["tc"] and room["last_ts"]:
            spent = time.time() - room["last_ts"]
            if me == 0:
                cw -= spent
            else:
                cb -= spent
        if db.save_room_state(room, ns, cw, cb):
            if ns["over"]:
                _finalize_online(room, ns)
        st.rerun(scope="fragment")

    if s["over"]:
        st.markdown(f"<div class='result'>{result_text(s, me, names)}</div>", unsafe_allow_html=True)
        d = s.get("deltas")
        if d and me is not None and d[me]:
            st.markdown(f"<center><b>{tr('rating_change', d=d[me])}</b></center>", unsafe_allow_html=True)
        if me is not None and not ss.get(f"_ball_{room['id']}") and s["winner"] == me:
            ss[f"_ball_{room['id']}"] = True
            st.balloons()
    st.markdown(f"**{tr('moves')}**")
    st.markdown(move_list_html(s["moves"]), unsafe_allow_html=True)


def room_side():
    room = db.get_room(ss.room)
    s = room["state"]
    me = 0 if room["white"] == ss.user else 1 if room["black"] == ss.user else None
    if me is not None and room["status"] == "active" and not s["over"]:
        with st.popover(tr("resign"), use_container_width=True):
            st.write(tr("resign_confirm"))
            if st.button(tr("yes"), key="o_resign", type="primary"):
                room = db.get_room(ss.room)
                s = room["state"]
                if not s["over"]:
                    s["over"], s["winner"], s["reason"] = True, 1 - me, "resign"
                    if db.save_room_state(room, s, room["clock_w"], room["clock_b"]):
                        _finalize_online(room, s)
                st.rerun()
    if s["over"]:
        if me is not None and st.button(tr("rematch"), use_container_width=True, type="primary"):
            opp_color = "white" if me == 1 else "black"
            new_rid = db.create_room(ss.user, ss.guest, opp_color, engine.new_state(),
                                     bool(room["rated"]), False, room["tc"])
            db.add_chat(room["id"], ss.user, f"🔁 {tr('rematch')}: {new_rid}")
            ss.room = new_rid
            st.rerun()
        with st.expander(tr("analysis")):
            review_block(s["moves"], f"rv_{room['id']}")
    st.markdown(f"**{tr('chat')}**")
    chat_box(room["id"])
    if me is not None:
        with st.form("chat_form", clear_on_submit=True):
            msg = st.text_input(tr("message"), label_visibility="collapsed", placeholder=tr("message"))
            if st.form_submit_button(tr("send"), use_container_width=True) and msg.strip():
                db.add_chat(room["id"], ss.user, msg)
                st.rerun()


@st.fragment(run_every=3)
def chat_box(rid: str):
    msgs = db.get_chat(rid)
    html = "".join(
        f"<div><b>{m['author']}</b>: {st_escape(m['body'])}</div>" for m in msgs
    ) or "<div style='opacity:.6'>…</div>"
    st.markdown(f"<div class='card movelist' style='font-family:inherit'>{html}</div>", unsafe_allow_html=True)


def st_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- Ойнау беті

def play_page():
    if ss.game:
        game_view()
        return
    if ss.room:
        online_room_view()
        return
    mode = st.radio(tr("mode"), ["ai", "online", "local"], horizontal=True,
                    format_func=lambda m: tr(f"mode_{m}"), label_visibility="collapsed", key="mode_pick")
    if mode == "ai":
        c1, c2 = st.columns([1.2, 1])
        with c1:
            levels = ["easy", "medium", "hard", "master", "llm"]
            level = st.radio(tr("level"), levels, index=1, horizontal=True, format_func=lvl_name)
            if level == "llm":
                if ss.llm:
                    st.caption(tr("key_status_on", p=f"{ss.llm['provider']} · {ss.llm['model']}"))
                else:
                    st.warning(tr("need_key"))
            color = st.radio(tr("color"), ["white", "black", "random"], horizontal=True,
                             format_func=lambda c: tr(f"col_{c}"))
            rated = st.toggle(tr("rated"), value=False, disabled=not is_registered() or level == "llm",
                              help=tr("guest_note") if not is_registered() else None)
            if st.button(tr("start"), type="primary", use_container_width=True,
                         disabled=level == "llm" and not ss.llm):
                start_ai_game(level, color, rated)
                st.rerun()
        with c2:
            lv_rows = [{tr("level"): lvl_name(k), "Elo": v[3]} for k, v in engine.LEVELS.items()]
            st.dataframe(lv_rows, hide_index=True, use_container_width=True)
    elif mode == "online":
        online_lobby()
    else:
        with st.form("local_form"):
            c1, c2 = st.columns(2)
            n1 = c1.text_input(f"⚪ {tr('white')}", value=ss.user or tr("white"))
            n2 = c2.text_input(f"⚫ {tr('black')}", value=tr("black"))
            if st.form_submit_button(tr("start"), type="primary", use_container_width=True):
                start_local_game(n1, n2)
                st.rerun()


# ---------------------------------------------------------------- Есептер

@st.cache_data(show_spinner=False, max_entries=256)
def get_puzzle(seed: int):
    return engine.make_puzzle(seed)


def puzzles_page():
    day = int(dt.date.today().strftime("%Y%m%d"))
    seed = day * 100 + ss.puzzle_i
    pz = get_puzzle(seed)
    if not pz:
        ss.puzzle_i += 1
        st.rerun()
    s = pz["state"]
    side = tr("white") if s["turn"] == 0 else tr("black")
    title = tr("puzzle_title") + (f" #{ss.puzzle_i + 1}" if ss.puzzle_i else "")
    c1, c2 = st.columns([3, 1.2])
    with c1:
        st.markdown(f"### 🧩 {title}")
        st.write(tr("puzzle_task", side=side))
        key = f"pz_{seed}"
        status = ss.get(key)
        shown = engine.play(s, pz["answer"]) if status == "ok" else s
        names = [tr("white"), tr("black")]
        msg = tr("puzzle_ok", n=pz["gain"]) if status == "ok" else (tr("puzzle_bad") if status == "bad" else "")
        mv = board(shown, s["turn"], names, status != "ok", key=f"pzb_{seed}", message=msg)
        if mv is not None:
            t_after = engine.play(s, mv)
            p = s["turn"]
            gain = t_after["kazan"][p] - s["kazan"][p] + (20 if t_after["tuzdyk"][p] != s["tuzdyk"][p] else 0)
            if mv == pz["answer"] or gain >= pz["gain"]:
                ss[key] = "ok"
                ss.puzzles_solved += 1
            else:
                ss[key] = "bad"
            st.rerun()
    with c2:
        st.metric(tr("solved"), ss.puzzles_solved)
        if st.button(tr("puzzle_next"), type="primary", use_container_width=True):
            ss.puzzle_i += 1
            st.rerun()
        if st.button(tr("puzzle_show"), use_container_width=True):
            st.info(tr("puzzle_answer", n=pz["answer"] + 1))


# ---------------------------------------------------------------- Рейтинг

def rating_page():
    st.markdown(f"### 🏆 {tr('lb_title')}")
    rows = db.leaderboard(100)
    if not rows:
        st.info(tr("lb_empty"))
        return
    top3 = rows[:3]
    if top3:
        order = [1, 0, 2] if len(top3) == 3 else list(range(len(top3)))
        medals = {0: ("p1", "🥇"), 1: ("p2", "🥈"), 2: ("p3", "🥉")}
        html = "<div class='podium'>"
        for i in order:
            if i < len(top3):
                r = top3[i]
                cls, md = medals[i]
                html += f"<div class='{cls}'>{md}<br>{st_escape(r['username'])}<div class='r'>⭐ {r['rating']}</div></div>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
    table = []
    for i, r in enumerate(rows, 1):
        wr = round(100 * r["wins"] / r["games"]) if r["games"] else 0
        name = r["username"] + (" 👈" if r["username"] == ss.user else "")
        table.append({tr("col_place"): i, tr("col_player"): name, tr("col_rating"): r["rating"],
                      tr("col_games"): r["games"], tr("col_wins"): r["wins"], tr("col_losses"): r["losses"],
                      tr("col_draws"): r["draws"], tr("col_winrate"): wr, tr("col_peak"): r["peak"]})
    st.dataframe(table, hide_index=True, use_container_width=True,
                 column_config={tr("col_winrate"): st.column_config.ProgressColumn(
                     tr("col_winrate"), min_value=0, max_value=100, format="%d%%")})
    recent = db.recent_games(15)
    if recent:
        st.markdown(f"**{tr('recent')}**")
        st.dataframe([{tr("white"): g["white"], tr("result"): g["result"], tr("black"): g["black"],
                       tr("score"): f"{g['score_w']}:{g['score_b']}",
                       tr("date"): dt.datetime.fromtimestamp(g["created"]).strftime("%d.%m %H:%M")}
                      for g in recent], hide_index=True, use_container_width=True)


# ---------------------------------------------------------------- Профиль

def profile_page():
    if not is_registered():
        st.info(tr("profile_guest"))
        return
    u = db.get_user(ss.user)
    rank = db.user_rank(ss.user)
    st.markdown(f"### 👤 {u['username']}")
    c = st.columns(5)
    c[0].metric(tr("col_rating"), u["rating"])
    c[1].metric(tr("place"), f"#{rank}" if rank else "—")
    c[2].metric(tr("col_games"), u["games"])
    c[3].metric(tr("col_wins"), u["wins"])
    c[4].metric(tr("col_peak"), u["peak"])
    hist = db.rating_history(ss.user)
    if len(hist) > 1:
        st.markdown(f"**{tr('rating_graph')}**")
        st.line_chart([1200] + hist, height=200)
    games = db.user_games(ss.user, 50)
    if games:
        st.markdown(f"**{tr('recent')}**")
        rows = []
        for g in games:
            white = g["white"] == ss.user
            opp = g["black"] if white else g["white"]
            res = g["result"]
            outcome = "🤝" if res == "½-½" else ("✅" if (res == "1-0") == white else "❌")
            delta = g["delta_w"] if white else g["delta_b"]
            rows.append({"": outcome, tr("opponent"): opp, tr("score"): f"{g['score_w']}:{g['score_b']}",
                         "±": f"{delta:+d}" if delta else "", tr("date"):
                         dt.datetime.fromtimestamp(g["created"]).strftime("%d.%m.%y %H:%M")})
        st.dataframe(rows, hide_index=True, use_container_width=True)
        idx = st.selectbox(tr("analysis"), range(len(games)), index=None,
                           format_func=lambda i: f"{rows[i][tr('date')]} · {rows[i][tr('opponent')]} · {rows[i][tr('score')]}")
        if idx is not None and games[idx]["moves"]:
            review_block(games[idx]["moves"].split(), f"prof_{games[idx]['id']}")
    with st.expander(tr("change_pw")):
        with st.form("pw_form"):
            p1 = st.text_input(tr("new_pw"), type="password")
            p2 = st.text_input(tr("password2"), type="password")
            if st.form_submit_button(tr("save")):
                if len(p1) < 6:
                    st.error(tr("reg_bad_pw"))
                elif p1 != p2:
                    st.error(tr("reg_mismatch"))
                else:
                    db.change_password(ss.user, p1)
                    st.success(tr("pw_changed"))


# ---------------------------------------------------------------- Ережелер

def rules_page():
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown(RULES[ss.lang])
    with c2:
        demo = engine.new_state()
        for m in (6, 2, 0):
            demo = engine.play(demo, m)
        board(demo, 0, [tr("white"), tr("black")], False, key="rules_board",
              message=last_move_msg(demo, [tr("white"), tr("black")]))


# ---------------------------------------------------------------- Баптаулар

def settings_page():
    tab_ai, tab_view = st.tabs([tr("set_ai"), tr("set_view")])
    with tab_ai:
        st.caption(tr("set_ai_desc"))
        cur = ss.llm or {}
        names = list(llm.PROVIDERS)
        prov = st.selectbox(tr("provider"), names,
                            index=names.index(cur["provider"]) if cur.get("provider") in names else 0)
        p = llm.PROVIDERS[prov]
        same = cur.get("provider") == prov
        model = st.text_input(tr("model"), value=cur.get("model") if same else p["model"])
        base = st.text_input(tr("base_url"), value=cur.get("base") if same else p["base"],
                             disabled=p["kind"] != "openai")
        key = st.text_input(tr("api_key"), value=cur.get("key", "") if same else "", type="password",
                            placeholder="sk-…")
        cfg = {"provider": prov, "kind": p["kind"], "base": base or p["base"], "model": model, "key": key}
        b1, b2, b3 = st.columns(3)
        if b1.button(tr("save"), type="primary", use_container_width=True, disabled=not key or not model):
            ss.llm = cfg
            st.success(tr("key_saved"))
        if b2.button(tr("test_key"), use_container_width=True, disabled=not key or not model):
            with st.spinner("…"):
                try:
                    r = llm.chat(cfg, "Reply with one word: OK", max_tokens=10, timeout=20)
                    st.success(tr("key_ok", r=r.strip()[:40]))
                except Exception as e:  # noqa: BLE001
                    st.error(tr("key_fail", e=str(e)[:300]))
        if b3.button(tr("key_clear"), use_container_width=True):
            ss.llm = None
            st.rerun()
        st.info(tr("key_status_on", p=f"{ss.llm['provider']} · {ss.llm['model']}") if ss.llm
                else tr("key_status_off"))
    with tab_view:
        ss.board_theme = st.radio("🎨", ["light", "dark"], horizontal=True,
                                  index=0 if ss.board_theme == "light" else 1,
                                  format_func=lambda x: tr("theme_light") if x == "light" else tr("theme_dark"))
        ss.show_numbers = st.toggle(tr("show_numbers"), value=ss.show_numbers)
        ss.show_stones = st.toggle(tr("show_stones"), value=ss.show_stones)
        ss.button_mode = st.toggle(tr("button_mode"), value=ss.button_mode)
    board(engine.new_state(), 0, [tr("white"), tr("black")], False, key="preview_board")


# ---------------------------------------------------------------- Main

header()

# Шақыру сілтемесі: ?room=CODE
qp_room = st.query_params.get("room")

if not ss.user:
    auth_page()
    st.stop()

db.touch(ss.user)

if qp_room and not ss.room:
    r = db.get_room(qp_room)
    if r:
        if r["status"] == "waiting" and ss.user not in (r["white"], r["black"]):
            db.join_room(r["id"], ss.user, ss.guest)
        ss.room = r["id"]
        ss.game = None
    st.query_params.clear()

PAGES = ["play", "puzzles", "rating", "profile", "rules", "settings"]
page = st.radio("nav", PAGES, horizontal=True, label_visibility="collapsed", key="nav",
                format_func=lambda p: tr(f"nav_{p}"))

{"play": play_page, "puzzles": puzzles_page, "rating": rating_page, "profile": profile_page,
 "rules": rules_page, "settings": settings_page}[page]()

st.divider()
fc1, fc2 = st.columns([4, 1])
fc1.caption("Тоғызқұмалақ онлайн · Streamlit · 2026")
if fc2.button(tr("logout"), use_container_width=True):
    for k in ("user", "guest", "game", "room"):
        ss[k] = None if k != "guest" else False
    st.rerun()
