"""Ұлттық ойындар порталы: Тоғызқұмалақ · Асық ату · Дойбы — Streamlit."""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Ұлттық ойындар · Тоғызқұмалақ · Асық · Дойбы · Жамбы", page_icon="🟤", layout="wide",
                   initial_sidebar_state="collapsed")

import importlib  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

REQUIRED = "2.4"
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path[:1]:
    sys.path.insert(0, str(_ROOT))


def _file_version():
    try:
        txt = (_ROOT / "core" / "__init__.py").read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r'VERSION\s*=\s*"([^"]+)"', txt)
    return m.group(1) if m else None


def _purge_modules():
    """Streamlit Cloud жаңартудан кейін ескі модульдерді жадта қалдырады — тазалаймыз."""
    for name in list(sys.modules):
        if name in ("core", "ui") or name.startswith(("core.", "ui.")):
            del sys.modules[name]
    importlib.invalidate_caches()


_fv = _file_version()
if _fv == REQUIRED:
    import core  # noqa: E402

    if getattr(core, "VERSION", None) != REQUIRED or not Path(getattr(core, "__file__", "") or "").is_relative_to(_ROOT):
        _purge_modules()
        import core  # noqa: E402,F811
else:
    _files = sorted(p.name for p in (_ROOT / "core").glob("*")) if (_ROOT / "core").exists() else []
    st.error("⚠️ GitHub-тағы `core/` бумасы ескі немесе толық емес. / Папка `core/` на GitHub устарела или неполная.")
    st.markdown(
        f"- Табылған нұсқа / найдена версия: **{_fv or '—'}**, керек / нужна: **{REQUIRED}**\n"
        f"- `core/` ішінде / в `core/`: `{', '.join(_files) or 'жоқ / нет'}`\n"
        f"- Керек файлдар / нужные файлы: `__init__.py, asyk.py, db.py, draughts.py, engine.py, i18n.py, jamby.py, kokpar.py, kyzkuu.py, llm.py, tenge.py`\n"
        f"- `core/__init__.py` ішінде дәл осы жол болуы керек / в `core/__init__.py` должна быть строка: "
        f"`VERSION = \"{REQUIRED}\"`\n"
        f"- Файлдарды ауыстырғаннан кейін: **Manage app → ⋮ → Reboot app** / после замены: **Manage app → ⋮ → Reboot app**")
    st.stop()

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
    subs = ["play"] + (["puzzles"] if gk == "togyz" else []) + (["upgrade"] if gk in ("kyzkuu", "tenge", "kokpar") else []) + ["rules"]
    sub = st.radio("sub", subs, horizontal=True, key=f"sub_{gk}", label_visibility="collapsed",
                   format_func=lambda x: tr(f"nav_{x}"))
    if sub == "play":
        play_page(spec)
    elif sub == "upgrade":
        pages.upgrade_page(gk)
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

PAGES = ["home", "togyz", "asyk", "doyby", "jamby", "kyzkuu", "tenge", "kokpar", "champ", "rating", "profile", "settings"]
if is_admin():
    PAGES.append("admin")
LABELS = {"home": tr("nav_home"), "togyz": "⚫ " + tr("game_togyz"), "asyk": "🦴 " + tr("game_asyk"),
          "doyby": "♛ " + tr("game_doyby"), "jamby": "🏹 " + tr("game_jamby"), "kyzkuu": "🐎 " + tr("game_kyzkuu"), "tenge": "🪙 " + tr("game_tenge"), "kokpar": "🐐 " + tr("game_kokpar"), "champ": tr("nav_champ"), "rating": tr("nav_rating"),
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
fc1.caption("Ұлттық ойындар · Тоғызқұмалақ · Асық ату · Дойбы · Жамбы ату · Қыз қуу · Теңге алу · Көкпар · 2026")
if fc2.button(tr("logout"), use_container_width=True):
    for g in list(ss.games.values()):
        abandon(g)
    ss.user, ss.guest, ss.games, ss.rooms = None, False, {}, {}
    st.rerun()
