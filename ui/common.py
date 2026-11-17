"""Ортақ көмекшілер: сессия, аударма, стиль."""
from __future__ import annotations

import streamlit as st

from core import db, llm
from core.i18n import t

ss = st.session_state


def secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:  # noqa: BLE001
        return default


def init_session():
    ss.setdefault("lang", "kz")
    ss.setdefault("user", None)
    ss.setdefault("guest", False)
    ss.setdefault("games", {})      # {game_key: ойын күйі (ИИ/жергілікті)}
    ss.setdefault("rooms", {})      # {game_key: бөлме коды}
    ss.setdefault("puzzle_i", 0)
    ss.setdefault("puzzles_solved", 0)
    ss.setdefault("board_theme", "light")
    ss.setdefault("draughts_style", "")
    ss.setdefault("show_numbers", True)
    ss.setdefault("show_stones", True)
    ss.setdefault("button_mode", False)
    ss.setdefault("llm", None)
    if ss.llm is None and secret("LLM_API_KEY"):
        prov = secret("LLM_PROVIDER", "OpenAI (ChatGPT)")
        p = llm.PROVIDERS.get(prov, llm.PROVIDERS["OpenAI (ChatGPT)"])
        ss.llm = {"provider": prov, "kind": p["kind"], "base": secret("LLM_BASE_URL", p["base"]),
                  "model": secret("LLM_MODEL", p["model"]), "key": secret("LLM_API_KEY")}


def tr(key: str, **kw) -> str:
    return t(key, ss.lang, **kw)


def is_registered() -> bool:
    return bool(ss.user) and not ss.guest


def is_admin() -> bool:
    if not is_registered():
        return False
    admins = secret("ADMIN_USERS", "aidarpavl")
    if isinstance(admins, str):
        admins = [a.strip() for a in admins.split(",")]
    return ss.user.casefold() in {a.casefold() for a in admins}


def esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def lvl_name(level: str) -> str:
    return tr(f"lv_{level}")


LEVEL_POINTS = {"easy": 1, "medium": 2, "hard": 3, "master": 4}


def tick() -> int:
    ss["_tok"] = ss.get("_tok", 0) + 1
    return ss["_tok"]


def take(val, key: str):
    """Компоненттен келген мәнді бір рет қана қабылдау (nonce бойынша)."""
    if val and val.get("nonce") != ss.get(f"_nonce_{key}"):
        ss[f"_nonce_{key}"] = val["nonce"]
        return val
    return None


def touch_presence():
    if ss.user:
        try:
            db.touch(ss.user)
        except Exception:  # noqa: BLE001
            pass


CSS = """
<style>
#MainMenu, footer, [data-testid="stToolbar"] {visibility: hidden;}
/* Streamlit-тің жоғарғы жолағы (header) мазмұнның үстін жауып тұрмасын */
header[data-testid="stHeader"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {
  display: none !important; height: 0 !important;}
.stApp > header {display: none !important;}
.block-container, [data-testid="stMainBlockContainer"], [data-testid="block-container"] {
  padding-top: max(1rem, env(safe-area-inset-top)) !important; padding-bottom: 2rem; max-width: 1200px;}
[data-testid="stAppViewContainer"] > section, [data-testid="stMain"] {padding-top: 0 !important; margin-top: 0 !important;}
.st-key-lang_toggle button {white-space: nowrap; min-height: 42px;}
.hero {background: linear-gradient(120deg, #5c3518 0%, #a5642a 55%, #e0a458 100%); color: #fff8ec;
       border-radius: 18px; padding: 12px 18px; margin-bottom: 8px; box-shadow: 0 6px 18px #0003;}
.hero h1 {margin: 0; font-size: clamp(20px, 5vw, 32px); color: #fff8ec; padding: 0;}
.hero p {margin: 2px 0 0; opacity: .92; font-size: clamp(12px, 3.2vw, 15px);}
.ornament {height: 9px; margin: 6px 0 2px; border-radius: 6px;
  background: repeating-linear-gradient(90deg, #f5b041 0 12px, transparent 12px 18px, #f5b041 18px 22px, transparent 22px 30px);
  opacity: .8;}
.card {background: var(--secondary-background-color, #f6efe6); border-radius: 14px; padding: 12px 14px; margin-bottom: 10px;
       border: 1px solid #0000000f;}
.gamecard {border-radius: 18px; padding: 16px; color: #fff8ec; min-height: 128px; box-shadow: 0 6px 16px #0003; margin-bottom: 6px;}
.gamecard h3 {color: #fff8ec; margin: 0 0 4px; padding: 0; font-size: clamp(18px, 4.6vw, 24px);}
.gamecard p {margin: 0; opacity: .92; font-size: 14px;}
.gamecard .ico {font-size: 34px; line-height: 1;}
.gc-togyz {background: linear-gradient(135deg, #7a1f1f, #b5452d 60%, #e0a458);}
.gc-asyk {background: linear-gradient(135deg, #5c3518, #a5642a 60%, #d9b98a);}
.gc-doyby {background: linear-gradient(135deg, #1f3b5c, #2d6a8f 60%, #7fb3d5);}
.gc-jamby {background: linear-gradient(135deg, #2e5a1c, #6a8f2d 60%, #d9c46a);}
.gc-kyzkuu {background: linear-gradient(135deg, #7a1f4e, #c0392b 55%, #f5b041);}
.gc-tenge {background: linear-gradient(135deg, #6b4a12, #b8860b 55%, #f5c542);}
.gc-kokpar {background: linear-gradient(135deg, #1d3d6e, #2e6b3a 50%, #a51d2a);}
.gc-kures {background: linear-gradient(135deg, #1f5fa0, #d9a520 55%, #b0202e);}
.gc-audaryspak {background: linear-gradient(135deg, #7a4419, #b8862f 50%, #1d5a8e);}
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
.champbadge {text-align: center; font-weight: 700; padding: 6px; border-radius: 10px; color: #7a4419;
             background: repeating-linear-gradient(45deg, #f5b04133 0 10px, #f5b04122 10px 20px); margin-bottom: 6px;}
.wallet {display: flex; gap: 8px; flex-wrap: wrap;}
.wallet div {flex: 1; min-width: 120px; border-radius: 14px; padding: 10px 12px; color: #fff8ec; font-weight: 700;
             background: linear-gradient(135deg, #5c3518, #a5642a);}
.wallet div span {display: block; font-size: 26px;}
div[role="radiogroup"] {flex-wrap: wrap; gap: 4px;}
div[role="radiogroup"] > label {background: #a5642a14; border-radius: 999px; padding: 4px 12px !important; margin: 0 !important;}
.st-key-movebtns [data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important; gap: 3px !important;}
.st-key-movebtns [data-testid="stColumn"], .st-key-movebtns [data-testid="column"] {
    min-width: 0 !important; width: auto !important; flex: 1 1 0 !important;}
.st-key-movebtns button {padding: 4px 0 !important; min-height: 38px;}
@media (max-width: 640px) {
  .block-container, [data-testid="stMainBlockContainer"] {padding-left: .45rem !important; padding-right: .45rem !important;
    padding-top: max(.7rem, env(safe-area-inset-top)) !important;}
  .hero {padding: 10px 12px; border-radius: 14px;}
  [data-testid="stMetricValue"] {font-size: 1.2rem;}
}
</style>
"""
