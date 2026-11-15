"""Ұлттық ойындар порталы: Тоғызқұмалақ · Асық ату · Дойбы — Streamlit."""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Ұлттық ойындар · Тоғызқұмалақ · Асық · Дойбы", page_icon="🟤", layout="wide",
                   initial_sidebar_state="collapsed")

from core import db  # noqa: E402
from ui.common import CSS, init_session, is_admin, is_registered, secret, ss, touch_presence, tr  # noqa: E402

db.configure(secret("DATABASE_URL"))
db.init()
init_session()
st.markdown(CSS, unsafe_allow_html=True)

from ui import pages  # noqa: E402
from ui.play import abandon, play_page  # noqa: E402
from ui.specs import SPECS  # noqa: E402


def header():
    c1, c2 = st.columns([5, 2], vertical_alignment="center")
    with c1:
        st.markdown(f"<div class='hero'><h1>⚫⚪ {tr('portal_title')}</h1><p>{tr('portal_sub')}</p>"
                    f"<div class='ornament'></div></div>", unsafe_allow_html=True)
    with c2:
        if st.button(tr("lang_btn"), use_container_width=True, key="lang_toggle"):
            ss.lang = "ru" if ss.lang == "kz" else "kz"
            st.rerun()
        if ss.user:
            info = f"{'👤' if not ss.guest else '🎭'} **{ss.user}**"
            if is_registered():
                w = db.get_wallet(ss.user)
                info += f" · 🎟 {w['attempts']} · 🏅 {w['points']}"
            st.markdown(info)
            st.caption(f"🟢 {tr('online_now')}: {db.online_count()}")


def game_page(gk: str):
    spec = SPECS[gk]
    subs = ["play"] + (["puzzles"] if gk == "togyz" else []) + ["rules"]
    sub = st.radio("sub", subs, horizontal=True, key=f"sub_{gk}", label_visibility="collapsed",
                   format_func=lambda x: tr(f"nav_{x}"))
    if sub == "play":
        play_page(spec)
    elif sub == "puzzles":
        from ui.togyz_extra import puzzles_page  # noqa: WPS433
        puzzles_page()
    else:
        c1, c2 = st.columns([3, 2])
        c1.markdown(spec.rules(ss.lang))
        with c2:
            demo = spec.new_state({})
            spec.render(demo, 0, [tr("white"), tr("black")], False, key=f"rules_{gk}",
                        message=spec.status(demo, [tr("white"), tr("black")]))


header()

# Шақыру сілтемесі ?room=CODE
qp_room = st.query_params.get("room")

if not ss.user:
    pages.home_page(public=True)
    pages.auth_panel()
    st.stop()

touch_presence()

if qp_room:
    r = db.get_room(qp_room)
    if r:
        gk = r.get("game") or "togyz"
        if r["status"] == "waiting" and ss.user not in (r["white"], r["black"]):
            db.join_room(r["id"], ss.user, ss.guest)
        ss.rooms[gk] = r["id"]
        ss.games.pop(gk, None)
        ss["_goto"] = gk
    st.query_params.clear()

PAGES = ["home", "togyz", "asyk", "doyby", "champ", "rating", "profile", "settings"]
if is_admin():
    PAGES.append("admin")
LABELS = {"home": tr("nav_home"), "togyz": "⚫ " + tr("game_togyz"), "asyk": "🦴 " + tr("game_asyk"),
          "doyby": "♛ " + tr("game_doyby"), "champ": tr("nav_champ"), "rating": tr("nav_rating"),
          "profile": tr("nav_profile"), "settings": tr("nav_settings"), "admin": tr("nav_admin")}

goto = ss.pop("_goto", None)
if goto in PAGES:
    ss["nav"] = goto
if ss.get("nav") not in PAGES:
    ss["nav"] = "home"

page = st.radio("nav", PAGES, horizontal=True, label_visibility="collapsed", key="nav",
                format_func=lambda p: LABELS[p])

if page == "home":
    pages.home_page()
elif page in SPECS:
    game_page(page)
elif page == "champ":
    pages.champ_page()
elif page == "rating":
    pages.rating_page()
elif page == "profile":
    pages.profile_page()
elif page == "settings":
    pages.settings_page()
elif page == "admin":
    pages.admin_page()

st.divider()
fc1, fc2 = st.columns([4, 1])
fc1.caption("Ұлттық ойындар · Тоғызқұмалақ · Асық ату · Дойбы · 2026")
if fc2.button(tr("logout"), use_container_width=True):
    for g in list(ss.games.values()):
        abandon(g)
    ss.user, ss.guest, ss.games, ss.rooms = None, False, {}, {}
    st.rerun()
