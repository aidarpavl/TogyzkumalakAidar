"""Үш ойынның сипаттамасы: күй, жүріс, ИИ, тақта, кеңес."""
from __future__ import annotations

import math
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core import asyk, draughts, engine, jamby, llm
from core.i18n import RULES, RULES_ASYK, RULES_DOYBY, RULES_JAMBY
from ui.common import ss, take, tick, tr

_ROOT = Path(__file__).resolve().parent.parent / "components"
_togyz = components.declare_component("togyz_board", path=str(_ROOT / "board"))
_draughts = components.declare_component("draughts_board", path=str(_ROOT / "draughts"))
_asyk = components.declare_component("asyk_field", path=str(_ROOT / "asyk"))
_jamby = components.declare_component("jamby_field", path=str(_ROOT / "jamby"))


class Spec:
    key = ""
    icon = ""
    levels = ("easy", "medium", "hard", "master")
    has_options = False

    def title(self):
        return tr(f"game_{self.key}")

    def rules(self, lang):
        raise NotImplementedError

    def options_ui(self, prefix: str) -> dict:
        return {}

    def new_state(self, opts: dict | None = None) -> dict:
        raise NotImplementedError

    def apply(self, s: dict, mv) -> dict:
        raise NotImplementedError

    def ai(self, s: dict, level: str):
        raise NotImplementedError

    def ai_elo(self, level: str) -> int:
        return {"easy": 800, "medium": 1200, "hard": 1600, "master": 2000}.get(level, 1200)

    def llm_move(self, cfg, s):
        return None

    def render(self, s, bottom, names, clickable, key, message="", clocks=None, clock_running=False, room=""):
        raise NotImplementedError

    def score(self, s) -> list[int]:
        raise NotImplementedError

    def status(self, s, names) -> str:
        return ""

    def hint(self, s) -> str | None:
        return None

    def coach(self, cfg, s, lang) -> str:
        return ""

    def anim_delay(self, s) -> float:
        return 0.35

    def move_list(self, s) -> list[str]:
        return s.get("moves", [])


# ---------------------------------------------------------------- Тоғызқұмалақ

class Togyz(Spec):
    key = "togyz"
    icon = "⚫"

    def rules(self, lang):
        return RULES[lang]

    def new_state(self, opts=None):
        return engine.new_state()

    def apply(self, s, mv):
        mv = int(mv)
        if mv not in engine.legal_moves(s):
            raise ValueError("illegal")
        return engine.play(s, mv)

    def ai(self, s, level):
        return engine.best_move(s, level)

    def llm_move(self, cfg, s):
        return llm.choose_move(cfg, s, engine.legal_moves(s))

    def render(self, s, bottom, names, clickable, key, message="", clocks=None, clock_running=False, room=""):
        legal = engine.legal_moves(s) if clickable else []
        view = {k: s[k] for k in ("pits", "kazan", "tuzdyk", "turn", "over", "last", "moves")}
        val = _togyz(state=view, bottom=bottom, names=names, clickable=clickable and not ss.button_mode,
                     legal=legal, message=message, theme=ss.board_theme, show_numbers=ss.show_numbers,
                     show_stones=ss.show_stones, animate=True, clocks=clocks, clock_running=clock_running,
                     token=tick(), key=key, default=None)
        move = None
        v = take(val, key)
        if v and v.get("move") in legal:
            move = v["move"]
        if ss.button_mode and clickable and s["turn"] == bottom:
            with st.container(key=f"movebtns_{key}"):
                cols = st.columns(9)
                for i, c in enumerate(cols):
                    if c.button(str(i + 1), key=f"{key}_b{i}", disabled=i not in legal, use_container_width=True):
                        move = i
        return move

    def score(self, s):
        return s["kazan"]

    def status(self, s, names):
        lm = s.get("last")
        if not lm:
            return tr("click_pit")
        txt = f"{tr('last_move')}: {names[lm['player']]} — {s['moves'][-1] if s['moves'] else ''}"
        if lm.get("tuz"):
            txt += " · ✕ " + tr("tuzdyk_made")
        elif lm.get("cap"):
            txt += " · " + tr("captured", n=lm["cap"])
        return txt

    def hint(self, s):
        return tr("hint_text", n=engine.best_move(s, "hard") + 1)

    def coach(self, cfg, s, lang):
        return llm.coach(cfg, s, s["turn"], engine.analyse(s, 4, 2.0), lang)


# ---------------------------------------------------------------- Дойбы

class Doyby(Spec):
    key = "doyby"
    icon = "♛"
    has_options = True

    def rules(self, lang):
        return RULES_DOYBY[lang]

    def options_ui(self, prefix):
        v = st.radio(tr("variant"), list(draughts.VARIANTS), horizontal=True, key=f"{prefix}_variant",
                     format_func=lambda x: tr(f"var_{x}"))
        return {"variant": v}

    def new_state(self, opts=None):
        return draughts.new_state((opts or {}).get("variant", "russian"))

    def apply(self, s, mv):
        path = [int(x) for x in mv["path"]]
        return draughts.play(s, {"path": path})

    def ai(self, s, level):
        return {"path": draughts.best_move(s, level)["path"]}

    def _position(self, s):
        n = s["n"]
        rows = []
        for r in range(n):
            row = ""
            for c in range(n):
                p = s["board"][r * n + c]
                row += {0: ".", 1: "w", 2: "W", -1: "b", -2: "B"}[p]
            rows.append(f"{n - r:>2} {row}")
        side = "white (w/W)" if s["turn"] == 0 else "black (b/B)"
        return "\n".join(rows) + "\n   " + "abcdefghij"[:n] + f"\nYou play {side}."

    def llm_move(self, cfg, s):
        moves = draughts.legal_moves(s)
        k = llm.choose_option(cfg, "doyby", self._position(s), [draughts.notation(m, s["n"]) for m in moves])
        return {"path": moves[k]["path"]} if k is not None else None

    def render(self, s, bottom, names, clickable, key, message="", clocks=None, clock_running=False, room=""):
        legal = [m["path"] for m in draughts.legal_moves(s)] if clickable else []
        val = _draughts(state=s, bottom=bottom, names=names, clickable=clickable, legal=legal,
                        counts=draughts.counts(s), message=message, theme=ss.draughts_style, clocks=clocks,
                        token=tick(), key=key, default=None)
        v = take(val, key)
        if v and v.get("path") in legal:
            return {"path": v["path"]}
        return None

    def score(self, s):
        return draughts.counts(s)

    def status(self, s, names):
        if not s["moves"]:
            return ""
        p = 1 - s["turn"]
        return f"{tr('last_move')}: {names[p]} — {s['moves'][-1]}"

    def hint(self, s):
        m = draughts.best_move(s, "hard")
        return f"💡 {draughts.notation(m, s['n'])}"

    def coach(self, cfg, s, lang):
        res = draughts.analyse(s, 4, 2.0)
        hints = ", ".join(f"{draughts.notation(m, s['n'])}: {v / 100:+.1f}" for m, v in res[:4])
        return llm.coach_generic(cfg, "doyby", self._position(s), hints, lang)


# ---------------------------------------------------------------- Асық ату

class Asyk(Spec):
    key = "asyk"
    icon = "🦴"

    def rules(self, lang):
        return RULES_ASYK[lang]

    def new_state(self, opts=None):
        return asyk.new_state()

    def apply(self, s, mv):
        shot = {"sx": float(mv["sx"]), "dx": float(mv["dx"]), "dy": float(mv["dy"]),
                "power": max(0.0, min(1.0, float(mv["power"])))}
        if not all(math.isfinite(v) for v in shot.values()):
            raise ValueError("bad shot")
        return asyk.play(s, shot)

    def ai(self, s, level):
        return asyk.best_shot(s, level)

    def llm_move(self, cfg, s):
        opts = [f"asyk at ({a[0]:.0f},{a[1]:.0f})" for a in s["asyks"]]
        k = llm.choose_option(cfg, "asyk", asyk.describe(s, s["turn"]), opts)
        if k is None:
            return None
        tx, ty = s["asyks"][k]
        sx = max(asyk.SX_MIN, min(asyk.SX_MAX, tx))
        return {"sx": sx, "dx": tx - sx, "dy": ty - asyk.BASE_Y, "power": 0.85}

    def render(self, s, bottom, names, clickable, key, message="", clocks=None, clock_running=False, room=""):
        val = _asyk(state=s, bottom=bottom, names=names, clickable=clickable, message=message,
                    hint=tr("asyk_canvas_hint"), clocks=clocks, room=room, token=tick(), key=key, default=None)
        v = take(val, key)
        if v and clickable:
            return {k: v[k] for k in ("sx", "dx", "dy", "power")}
        return None

    def score(self, s):
        return s["captured"]

    def status(self, s, names):
        lm = s.get("last")
        left = tr("asyk_left", n=len(s["asyks"]))
        if not lm:
            return tr("asyk_toss", t=s["toss"], name=names[s["turn"]]) + " · " + left
        nm = names[lm["shooter"]]
        msg = tr("asyk_got", name=nm, n=lm["got"]) if lm["got"] else tr("asyk_miss", name=nm)
        return msg + " · " + left

    def anim_delay(self, s):
        lm = s.get("last")
        return (len(lm["frames"]) / 60 + 0.6) if lm else 0.6

    def move_list(self, s):
        return s.get("moves", [])


# ---------------------------------------------------------------- Жамбы ату

class Jamby(Spec):
    key = "jamby"
    icon = "🏹"

    def rules(self, lang):
        return RULES_JAMBY[lang]

    def new_state(self, opts=None):
        return jamby.new_state()

    def apply(self, s, mv):
        shot = {"ax": float(mv["ax"]), "ay": float(mv["ay"]), "t": float(mv["t"])}
        if not all(math.isfinite(v) for v in shot.values()):
            raise ValueError("bad shot")
        return jamby.play(s, shot)

    def ai(self, s, level):
        return jamby.best_shot(s, level)

    def llm_move(self, cfg, s):
        cur = s["cur"]
        cands = [cur["T"] * i / 8 for i in range(1, 8)]
        opts = []
        for t in cands:
            bx, by = jamby.bob(cur, t)
            opts.append(f"release at t={t:.2f}s: bow sway {math.hypot(bx, by):.2f}, target x {jamby.target_x(cur, t):+.2f}")
        k = llm.choose_option(cfg, "jamby", jamby.describe(s, s["turn"]), opts)
        if k is None:
            return None
        shot = jamby.best_shot(s, "hard")
        t = cands[k]
        bx, by = jamby.bob(cur, t)
        kk = cur["dist"] / 30
        return {"ax": jamby.target_x(cur, t) - bx - cur["wind"] * kk, "ay": -by - 0.02 * kk, "t": t} if shot else None

    def render(self, s, bottom, names, clickable, key, message="", clocks=None, clock_running=False, room=""):
        val = _jamby(state=s, bottom=bottom, names=names, clickable=clickable, message=message,
                     hint=tr("jamby_hint"), labels={"end": tr("jamby_end"), "wind": tr("jamby_wind"),
                                                    "miss": tr("jamby_miss")},
                     clocks=clocks, room=room, token=tick(), key=key, default=None)
        v = take(val, key)
        if v and clickable:
            return {k: v[k] for k in ("ax", "ay", "t")}
        return None

    def score(self, s):
        return jamby.totals(s)

    def status(self, s, names):
        parts = []
        lm = s.get("last")
        if lm:
            pts = "X" if lm["x"] else (str(lm["pts"]) if lm["pts"] else tr("jamby_miss"))
            parts.append(tr("jamby_last", name=names[lm["shooter"]], pts=pts))
        if s.get("cur"):
            parts.append(tr("jamby_status", d=s["cur"]["dist"], w=f"{s['cur']['wind']:+.2f}"))
        return " · ".join(parts) or tr("jamby_ride")

    def hint(self, s):
        cur = s["cur"]
        a = cur["wind"] * cur["dist"] / 30
        return tr("jamby_tip", w=cur["wind"], side=tr("left_side") if a > 0 else tr("right_side"), a=abs(a))

    def coach(self, cfg, s, lang):
        return llm.coach_generic(cfg, "jamby", jamby.describe(s, s["turn"]), self.hint(s), lang)

    def anim_delay(self, s):
        return 1.9


SPECS = {"togyz": Togyz(), "asyk": Asyk(), "doyby": Doyby(), "jamby": Jamby()}
