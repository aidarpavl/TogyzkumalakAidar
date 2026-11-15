"""Үш ойынның сипаттамасы: күй, жүріс, ИИ, тақта, кеңес."""
from __future__ import annotations

import math
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core import asyk, db, draughts, engine, jamby, kyzkuu, llm
from core.i18n import RULES, RULES_ASYK, RULES_DOYBY, RULES_JAMBY, RULES_KYZKUU
from ui.common import ss, take, tick, tr

_ROOT = Path(__file__).resolve().parent.parent / "components"
_togyz = components.declare_component("togyz_board", path=str(_ROOT / "board"))
_draughts = components.declare_component("draughts_board", path=str(_ROOT / "draughts"))
_asyk = components.declare_component("asyk_field", path=str(_ROOT / "asyk"))
_jamby = components.declare_component("jamby_field", path=str(_ROOT / "jamby"))
_kyzkuu = components.declare_component("kyzkuu_field", path=str(_ROOT / "kyzkuu"))


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

    def color_label(self, c: str) -> str:
        return tr(f"col_{c}")

    # Қосымша ілмектер (Қыз қуу үшін)
    def after_start(self, g: dict) -> None:
        pass

    def on_active(self, room: dict):
        return None

    def rewards(self, s: dict, players: list, level: str | None, champ: bool, mode: str) -> list[str]:
        return []


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


# ---------------------------------------------------------------- Қыз қуу

def _horse_stats(name: str | None, registered: bool) -> dict:
    if name and registered:
        try:
            return kyzkuu.stats_from_mult(db.get_horse(name))
        except Exception:  # noqa: BLE001
            pass
    return dict(kyzkuu.BASE)


class Kyzkuu(Spec):
    key = "kyzkuu"
    icon = "🐎"

    def rules(self, lang):
        return RULES_KYZKUU[lang]

    def color_label(self, c):
        return {"white": tr("role_girl"), "black": tr("role_jigit")}.get(c, tr("col_random"))

    def new_state(self, opts=None):
        return kyzkuu.new_state(opts)

    def after_start(self, g):
        s = g["state"]
        if g["mode"] == "ai":
            h, a = g["human"], 1 - g["human"]
            s["stats"][h] = _horse_stats(g["names"][h], not ss.guest)
            s["stats"][a] = kyzkuu.ai_stats(g["level"] if g["level"] in kyzkuu.AI_STYLE else "hard")
            lvl = g["level"] if g["level"] in kyzkuu.AI_STYLE else "medium"
            s["ai_plan"] = {str(st): kyzkuu.ai_taps(s["stats"][a], st, lvl) for st in (0, 1)}
        else:
            for p in (0, 1):
                s["stats"][p] = _horse_stats(g["names"][p], g["names"][p] == ss.user and not ss.guest)
        s["ready"] = True

    def on_active(self, room):
        s = room["state"]
        if s.get("ready") or room["status"] != "active":
            return None
        s["stats"] = [_horse_stats(room["white"], not room["white_guest"]),
                      _horse_stats(room["black"], not room["black_guest"])]
        s["ready"] = True
        return s

    def apply(self, s, mv):
        return kyzkuu.play(s, {"taps": list(mv.get("taps", []))})

    def ai(self, s, level):
        plan = s.get("ai_plan") or {}
        taps = plan.get(str(s["stage"]))
        if taps is None:
            taps = kyzkuu.ai_taps(s["stats"][s["turn"]], s["stage"], level if level in kyzkuu.AI_STYLE else "medium")
        return {"taps": taps}

    def _ghost(self, s, me):
        stage, opp = s["stage"], 1 - me
        got = s["inputs"][stage].get(str(opp))
        if got is not None:
            return got
        plan = s.get("ai_plan")
        if plan:
            return plan.get(str(stage), [])
        return kyzkuu.ai_taps(s["stats"][opp], stage, "medium")

    def llm_move(self, cfg, s):
        styles = list(kyzkuu.AI_STYLE)
        opts = [f"whip every {kyzkuu.AI_STYLE[k][0]} s, rest below {kyzkuu.AI_STYLE[k][1]} stamina until "
                f"{kyzkuu.AI_STYLE[k][2]}" for k in styles]
        role = "fleeing" if kyzkuu.fleer(s["stage"]) == s["turn"] else "chasing"
        pos = f"Stage {s['stage'] + 1}, you are {role}. Your horse: {s['stats'][s['turn']]}. Opponent: {s['stats'][1 - s['turn']]}."
        k = llm.choose_option(cfg, "kyzkuu", pos, opts)
        if k is None:
            return None
        return {"taps": kyzkuu.ai_taps(s["stats"][s["turn"]], s["stage"], styles[k])}

    def render(self, s, bottom, names, clickable, key, message="", clocks=None, clock_running=False, room=""):
        me = bottom
        view = {k: v for k, v in s.items() if k != "ai_plan"}
        val = _kyzkuu(state=view, me=me, names=names, clickable=clickable, message=message,
                      ghost=self._ghost(s, me) if clickable else [],
                      labels={"side": tr("kk_side"), "front": tr("kk_front"), "rear": tr("kk_rear"),
                              "speed": tr("kk_speed"), "stamina": tr("kk_stamina"), "gap": tr("kk_gap"),
                              "left": tr("kk_left"), "start": tr("kk_start"), "whip": tr("kk_whip"),
                              "wait": tr("kk_wait"), "kiss": tr("kk_kiss"), "whipHit": tr("kk_whiphit"),
                              "escaped": tr("kk_escaped"), "kmh": tr("kmh")},
                      room=room, token=tick(), key=key, default=None)
        v = take(val, key)
        if v and clickable:
            return {"taps": v.get("taps", [])}
        return None

    def score(self, s):
        return s["points"]

    def status(self, s, names):
        if s["over"]:
            return ""
        f = kyzkuu.fleer(s["stage"])
        who = names[f]
        txt = tr("kk_stage", n=s["stage"] + 1, who=who)
        if s.get("last"):
            lm = s["last"]
            txt = (tr("kk_kiss") if lm["stage"] == 0 else tr("kk_whiphit")) if lm["caught"] else tr("kk_escaped")
            txt += " · " + tr("kk_stage", n=s["stage"] + 1, who=who)
        return txt

    def hint(self, s):
        return tr("kk_hint")

    def coach(self, cfg, s, lang):
        role = "fleeing" if kyzkuu.fleer(s["stage"]) == s["turn"] else "chasing"
        pos = f"Stage {s['stage'] + 1}, player is {role}. Horses: {s['stats']}. Points: {s['points']}."
        return llm.coach_generic(cfg, "kyzkuu", pos, tr("kk_hint"), lang)

    def rewards(self, s, players, level, champ, mode):
        """players: [(name, registered), (name, registered)]. Жеңімпазға ат бонусы."""
        w = s.get("winner")
        if w not in (0, 1):
            return []
        name, reg = players[w]
        if not reg:
            return []
        if mode == "ai" and not champ and level not in ("hard", "master"):
            return []
        pct = 10 if w == 0 else 5
        db.add_horse_bonus(name, pct)
        return [tr("kk_bonus", p=pct)]

    def anim_delay(self, s):
        return 0.3


SPECS = {"togyz": Togyz(), "asyk": Asyk(), "doyby": Doyby(), "jamby": Jamby(), "kyzkuu": Kyzkuu()}
