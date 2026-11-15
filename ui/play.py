"""Ойын беттері: ИИ-мен, бір құрылғыда, онлайн — үш ойынға ортақ."""
from __future__ import annotations

import random
import time

import streamlit as st

from core import db
from ui.common import LEVEL_POINTS, esc, is_registered, lvl_name, ss, tr
from ui.specs import SPECS, Spec

TC_OPTIONS = [0, 180, 300, 600, 900]


def tc_label(sec: int) -> str:
    return tr("tc_none") if sec == 0 else tr("tc_min", m=sec // 60)


def move_list_html(moves: list[str]) -> str:
    if not moves:
        return "<div class='movelist'>—</div>"
    parts = []
    for i in range(0, len(moves), 2):
        pair = moves[i:i + 2]
        parts.append(f"<b>{i // 2 + 1}.</b> {esc(pair[0])} {esc(pair[1]) if len(pair) > 1 else ''}")
    return "<div class='movelist'>" + "<br>".join(parts) + "</div>"


def result_text(spec: Spec, s: dict, me, names) -> str:
    w = s["winner"]
    reason = tr(f"reason_{s.get('reason') or 'score'}")
    if w == -1:
        head = tr("draw")
    elif me is None:
        head = tr("winner_is", name=esc(names[w]))
    else:
        head = tr("you_win") if w == me else tr("you_lose")
    sc = spec.score(s)
    return f"{head}<br><small>{sc[0]} : {sc[1]} — {reason}</small>"


# ---------------------------------------------------------------- ИИ / жергілікті

def start_ai(spec: Spec, level: str, color: str, rated: bool, opts: dict, champ_id: str | None = None):
    human = {"white": 0, "black": 1}.get(color, random.choice([0, 1]))
    ai_name = f"🤖 {lvl_name(level)}"
    names = [ss.user, ai_name] if human == 0 else [ai_name, ss.user]
    ss.games[spec.key] = {
        "mode": "ai", "state": spec.new_state(opts), "human": human, "level": level, "opts": opts,
        "rated": bool(rated and is_registered() and level != "llm" and not champ_id), "names": names,
        "history": [], "recorded": False, "delta": None, "hint": None, "coach": None, "note": None,
        "champ": champ_id, "champ_msg": None, "gid": random.randint(1, 10**9)}


def start_local(spec: Spec, n1: str, n2: str, opts: dict):
    ss.games[spec.key] = {
        "mode": "local", "state": spec.new_state(opts), "human": None, "level": None, "opts": opts,
        "rated": False, "names": [n1 or tr("white"), n2 or tr("black")], "history": [], "recorded": False,
        "delta": None, "hint": None, "coach": None, "note": None, "champ": None, "champ_msg": None,
        "gid": random.randint(1, 10**9)}


def abandon(g: dict):
    """Чемпионат ойынын тастап кету — жеңіліс."""
    if g and g.get("champ") and not g.get("recorded"):
        db.finish_champ(g["champ"], "loss", 0)
        g["recorded"] = True


def ai_pick(spec: Spec, g: dict):
    s = g["state"]
    if g["level"] == "llm":
        if ss.llm:
            try:
                m = spec.llm_move(ss.llm, s)
                if m is not None:
                    return m
            except Exception:  # noqa: BLE001
                pass
        g["note"] = tr("llm_fallback")
        return spec.ai(s, "hard")
    return spec.ai(s, g["level"])


def finish(spec: Spec, g: dict):
    s = g["state"]
    if g["recorded"] or not s["over"]:
        return
    g["recorded"] = True
    if g["mode"] != "ai":
        return
    human = g["human"]
    if is_registered():
        w, b = g["names"]
        res = db.record_game(spec.key, "champ" if g.get("champ") else "ai", w, b, s, spec.score(s),
                             white_reg=human == 0, black_reg=human == 1, rated=g["rated"],
                             ai_elo=spec.ai_elo(g["level"]))
        g["delta"] = res["delta_w"] if human == 0 else res["delta_b"]
    if g.get("champ"):
        if s["winner"] == human:
            pts = LEVEL_POINTS.get(g["level"], 1)
            db.finish_champ(g["champ"], "win", pts)
            g["champ_msg"] = tr("champ_win", p=pts)
        elif s["winner"] == -1:
            db.finish_champ(g["champ"], "draw", 0)
            g["champ_msg"] = tr("champ_draw")
        else:
            db.finish_champ(g["champ"], "loss", 0)
            g["champ_msg"] = tr("champ_loss")
    if s["winner"] == human:
        st.balloons()


def game_view(spec: Spec):
    g = ss.games[spec.key]
    s = g["state"]
    local = g["mode"] == "local"
    champ = bool(g.get("champ"))
    bottom = (s["turn"] if not s["over"] else 0) if local else g["human"]
    if spec.key == "asyk" and local:
        bottom = 0
    my_turn = (not s["over"]) and (local or s["turn"] == g["human"])

    if champ:
        st.markdown(f"<div class='champbadge'>{tr('champ_badge')} · {lvl_name(g['level'])}</div>",
                    unsafe_allow_html=True)
    left, right = st.columns([3, 1.25])
    with left:
        msg = tr("ai_thinking") if (not my_turn and not s["over"]) else spec.status(s, g["names"])
        mv = spec.render(s, bottom, g["names"], my_turn, key=f"{spec.key}_game", message=msg,
                         room=f"g{g['gid']}")
        if mv is not None and my_turn:
            try:
                new = spec.apply(s, mv)
            except (ValueError, KeyError, TypeError):
                st.toast("⚠️")
            else:
                g["history"].append(s)
                g["state"] = new
                g["hint"] = g["coach"] = g["note"] = None
                st.rerun()
        if s["over"]:
            finish(spec, g)
            me = None if local else g["human"]
            st.markdown(f"<div class='result'>{result_text(spec, s, me, g['names'])}</div>", unsafe_allow_html=True)
            if g.get("delta"):
                st.markdown(f"<center><b>{tr('rating_change', d=g['delta'])}</b></center>", unsafe_allow_html=True)
            if g.get("champ_msg"):
                st.markdown(f"<div class='champbadge'>{g['champ_msg']}</div>", unsafe_allow_html=True)
        if g.get("note"):
            st.info(g["note"])
        if g.get("hint"):
            st.success(g["hint"])
        if g.get("coach"):
            st.markdown(f"<div class='card'>🧠 {g['coach']}</div>", unsafe_allow_html=True)

    with right:
        st.markdown(f"**{tr('moves')}**")
        st.markdown(move_list_html(spec.move_list(s)), unsafe_allow_html=True)
        if not s["over"]:
            if not champ:
                b1, b2 = st.columns(2)
                if spec.key != "asyk" and b1.button(tr("hint"), use_container_width=True, disabled=not my_turn,
                                                    key=f"{spec.key}_hint"):
                    with st.spinner("…"):
                        g["hint"] = spec.hint(s)
                    st.rerun()
                if b2.button(tr("undo"), use_container_width=True, disabled=not g["history"] or g["rated"],
                             key=f"{spec.key}_undo"):
                    g["state"] = g["history"].pop()
                    g["hint"] = g["coach"] = None
                    st.rerun()
                if spec.key != "asyk" and st.button(tr("coach_btn"), use_container_width=True, disabled=not my_turn,
                                                    icon="🧠", key=f"{spec.key}_coach"):
                    if not ss.llm:
                        st.warning(tr("need_key"))
                    else:
                        with st.spinner("…"):
                            try:
                                g["coach"] = spec.coach(ss.llm, s, ss.lang)
                            except Exception as e:  # noqa: BLE001
                                g["coach"] = tr("key_fail", e=str(e)[:200])
                        st.rerun()
            with st.popover(tr("resign"), use_container_width=True):
                st.write(tr("resign_confirm"))
                if st.button(tr("yes"), key=f"{spec.key}_resign_yes", type="primary"):
                    loser = s["turn"] if local else g["human"]
                    s["over"], s["winner"], s["reason"] = True, 1 - loser, "resign"
                    st.rerun()
        elif not champ:
            if st.button(tr("rematch"), use_container_width=True, type="primary", key=f"{spec.key}_rematch"):
                if local:
                    start_local(spec, g["names"][1], g["names"][0], g.get("opts") or {})
                else:
                    start_ai(spec, g["level"], "black" if g["human"] == 0 else "white", g["rated"], g.get("opts") or {})
                st.rerun()
        if st.button(tr("new_game"), use_container_width=True, key=f"{spec.key}_new"):
            abandon(g)
            ss.games.pop(spec.key, None)
            if champ:
                ss["_goto"] = "champ"
            st.rerun()

    if s["over"] and spec.key == "togyz" and s["moves"]:
        from ui.togyz_extra import review_block  # noqa: WPS433
        with st.expander(tr("analysis")):
            review_block(s["moves"], f"review_{g['gid']}")

    # ИИ жүрісі
    if not s["over"] and not local and s["turn"] != g["human"]:
        time.sleep(spec.anim_delay(s))
        with st.spinner(tr("ai_thinking")):
            m = ai_pick(spec, g)
        g["state"] = spec.apply(g["state"], m)
        st.rerun()


# ---------------------------------------------------------------- Онлайн

def online_lobby(spec: Spec):
    c1, c2 = st.columns([1, 1.3])
    with c1:
        with st.form(f"create_room_{spec.key}"):
            st.markdown(f"**{tr('create_room')}**")
            opts = spec.options_ui(f"room_{spec.key}")
            color = st.radio(tr("color"), ["random", "white", "black"], horizontal=True,
                             format_func=lambda c: tr(f"col_{c}"), key=f"room_color_{spec.key}")
            tc = st.selectbox(tr("time_control"), TC_OPTIONS, index=2, format_func=tc_label, key=f"tc_{spec.key}")
            rated = st.toggle(tr("rated"), value=is_registered(), disabled=not is_registered(), key=f"rt_{spec.key}")
            private = st.toggle(tr("private"), value=False, key=f"pv_{spec.key}")
            if st.form_submit_button(tr("create_room"), type="primary", use_container_width=True):
                ss.rooms[spec.key] = db.create_room(spec.key, ss.user, ss.guest, color, spec.new_state(opts),
                                                    rated, private, tc)
                st.rerun()
        with st.form(f"join_code_{spec.key}"):
            code = st.text_input(tr("join_code"), max_chars=6, placeholder="ABC123", key=f"code_{spec.key}")
            if st.form_submit_button(tr("join_by_code"), use_container_width=True):
                r = db.get_room(code.strip()) if code.strip() else None
                if r and r.get("game", "togyz") != spec.key:
                    r = None
                if r and (ss.user in (r["white"], r["black"]) or r["status"] in ("active", "finished")):
                    ss.rooms[spec.key] = r["id"]
                    st.rerun()
                elif r and db.join_room(r["id"], ss.user, ss.guest):
                    ss.rooms[spec.key] = r["id"]
                    st.rerun()
                else:
                    st.error(tr("room_not_found"))
    with c2:
        lobby_lists(spec.key)


@st.fragment(run_every=5)
def lobby_lists(gkey: str):
    import json  # noqa: WPS433

    spec = SPECS[gkey]
    mine = db.user_active_rooms(ss.user, gkey)
    if mine:
        st.markdown(f"**{tr('my_rooms')}**")
        for r in mine:
            opp = r["black"] if r["white"] == ss.user else r["white"]
            cc1, cc2 = st.columns([3, 1], vertical_alignment="center")
            cc1.write(f"`{r['id']}` · {opp or '…'} · {tc_label(r['tc'])}")
            if cc2.button(tr("continue"), key=f"cont_{r['id']}", use_container_width=True):
                ss.rooms[gkey] = r["id"]
                st.rerun(scope="app")
    st.markdown(f"**{tr('open_rooms')}**")
    rooms = [r for r in db.open_rooms(gkey) if ss.user not in (r["white"], r["black"])]
    if not rooms:
        st.caption(tr("no_rooms"))
    for r in rooms:
        host = r["white"] or r["black"]
        rating = db.get_rating(host, gkey)["rating"] if db.get_user(host) else None
        extra = ""
        if gkey == "doyby":
            extra = " · " + tr(f"var_{json.loads(r['state']).get('variant', 'russian')}")
        cc1, cc2 = st.columns([3, 1], vertical_alignment="center")
        cc1.write(f"{'⚪' if r['white'] else '⚫'} **{esc(host)}**{f' ({rating})' if rating else ''} · "
                  f"{tc_label(r['tc'])}{extra} · {'⭐' if r['rated'] else '—'}")
        if cc2.button(tr("join"), key=f"join_{r['id']}", type="primary", use_container_width=True):
            if db.join_room(r["id"], ss.user, ss.guest):
                ss.rooms[gkey] = r["id"]
                st.rerun(scope="app")
            else:
                st.error(tr("room_not_found"))
    live = db.active_rooms(gkey)
    if live:
        st.markdown(f"**{tr('live_games')}**")
        for r in live[:10]:
            sc = spec.score(json.loads(r["state"]))
            cc1, cc2 = st.columns([3, 1], vertical_alignment="center")
            cc1.write(f"⚪ {esc(r['white'])} **{sc[0]}** : **{sc[1]}** {esc(r['black'])} ⚫")
            if cc2.button(tr("watch"), key=f"watch_{r['id']}", use_container_width=True):
                ss.rooms[gkey] = r["id"]
                st.rerun(scope="app")


def _live_clocks(room: dict):
    if not room["tc"]:
        return None
    clocks = [room["clock_w"], room["clock_b"]]
    s = room["state"]
    if room["status"] == "active" and not s["over"] and room["last_ts"]:
        clocks[s["turn"]] -= time.time() - room["last_ts"]
    return clocks


def _finalize_online(spec: Spec, room: dict, state: dict):
    res = db.record_game(spec.key, "online", room["white"], room["black"], state, spec.score(state),
                         white_reg=not room["white_guest"], black_reg=not room["black_guest"],
                         rated=bool(room["rated"]))
    state["deltas"] = [res["delta_w"], res["delta_b"]]
    db.patch_room_state(room["id"], state)


def room_view(spec: Spec):
    room = db.get_room(ss.rooms[spec.key])
    if not room or room.get("game", "togyz") != spec.key:
        ss.rooms.pop(spec.key, None)
        st.rerun()
    if st.button(tr("back"), key=f"room_back_{spec.key}"):
        ss.rooms.pop(spec.key, None)
        st.rerun()
    st.caption(f"{tr('join_code')}: `{room['id']}` · {tc_label(room['tc'])}"
               f"{' · ⭐ ' + tr('rated') if room['rated'] else ''}")
    left, right = st.columns([3, 1.25])
    with left:
        room_live(spec.key)
    with right:
        room_side(spec)


@st.fragment(run_every=2)
def room_live(gkey: str):
    spec = SPECS[gkey]
    rid = ss.rooms.get(gkey)
    room = db.get_room(rid) if rid else None
    if not room:
        return
    s = room["state"]
    me = 0 if room["white"] == ss.user else 1 if room["black"] == ss.user else None
    names = [room["white"] or "…", room["black"] or "…"]
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
        if me is not None and st.button(tr("cancel"), key=f"cancel_{room['id']}"):
            db.cancel_room(room["id"])
            ss.rooms.pop(gkey, None)
            st.rerun(scope="app")
        spec.render(s, me if me is not None else 0, names, False, key=f"{gkey}_room_wait", room=room["id"])
        return

    clocks = _live_clocks(room)
    if clocks and room["status"] == "active" and not s["over"] and clocks[s["turn"]] <= 0:
        s["over"], s["winner"], s["reason"] = True, 1 - s["turn"], "timeout"
        if db.save_room_state(room, s, max(0, clocks[0]), max(0, clocks[1])):
            _finalize_online(spec, room, s)
        st.rerun(scope="fragment")

    my_turn = me is not None and not s["over"] and s["turn"] == me and room["status"] == "active"
    if s["over"]:
        msg = ""
    elif me is None:
        msg = tr("spectator") + " · " + tr("turn_of", name=names[s["turn"]])
    else:
        msg = tr("your_turn") if my_turn else tr("opp_turn")
    st_msg = spec.status(s, names)
    if st_msg and not s["over"]:
        msg += " · " + st_msg
    mv = spec.render(s, me if me is not None else 0, names, my_turn, key=f"{gkey}_room", message=msg,
                     clocks=clocks, clock_running=room["status"] == "active" and not s["over"], room=room["id"])
    if mv is not None and my_turn:
        try:
            ns = spec.apply(s, mv)
        except (ValueError, KeyError, TypeError):
            ns = None
        if ns is not None:
            cw, cb = room["clock_w"], room["clock_b"]
            if room["tc"] and room["last_ts"]:
                spent = time.time() - room["last_ts"]
                if me == 0:
                    cw -= spent
                else:
                    cb -= spent
            if db.save_room_state(room, ns, cw, cb) and ns["over"]:
                _finalize_online(spec, room, ns)
        st.rerun(scope="fragment")

    if s["over"]:
        st.markdown(f"<div class='result'>{result_text(spec, s, me, names)}</div>", unsafe_allow_html=True)
        d = s.get("deltas")
        if d and me is not None and d[me]:
            st.markdown(f"<center><b>{tr('rating_change', d=d[me])}</b></center>", unsafe_allow_html=True)
        if me is not None and not ss.get(f"_ball_{room['id']}") and s["winner"] == me:
            ss[f"_ball_{room['id']}"] = True
            st.balloons()
    st.markdown(f"**{tr('moves')}**")
    st.markdown(move_list_html(spec.move_list(s)), unsafe_allow_html=True)


def room_side(spec: Spec):
    room = db.get_room(ss.rooms[spec.key])
    s = room["state"]
    me = 0 if room["white"] == ss.user else 1 if room["black"] == ss.user else None
    if me is not None and room["status"] == "active" and not s["over"]:
        with st.popover(tr("resign"), use_container_width=True):
            st.write(tr("resign_confirm"))
            if st.button(tr("yes"), key=f"o_resign_{room['id']}", type="primary"):
                room = db.get_room(room["id"])
                s = room["state"]
                if not s["over"]:
                    s["over"], s["winner"], s["reason"] = True, 1 - me, "resign"
                    if db.save_room_state(room, s, room["clock_w"], room["clock_b"]):
                        _finalize_online(spec, room, s)
                st.rerun()
    if s["over"]:
        if me is not None and st.button(tr("rematch"), use_container_width=True, type="primary",
                                        key=f"o_rematch_{room['id']}"):
            opts = {"variant": s.get("variant", "russian")}
            new_rid = db.create_room(spec.key, ss.user, ss.guest, "white" if me == 1 else "black",
                                     spec.new_state(opts), bool(room["rated"]), False, room["tc"])
            db.add_chat(room["id"], ss.user, f"🔁 {tr('rematch')}: {new_rid}")
            ss.rooms[spec.key] = new_rid
            st.rerun()
        if spec.key == "togyz" and s["moves"]:
            from ui.togyz_extra import review_block  # noqa: WPS433
            with st.expander(tr("analysis")):
                review_block(s["moves"], f"rv_{room['id']}")
    st.markdown(f"**{tr('chat')}**")
    chat_box(room["id"])
    if me is not None:
        with st.form(f"chat_form_{room['id']}", clear_on_submit=True):
            msg = st.text_input(tr("message"), label_visibility="collapsed", placeholder=tr("message"))
            if st.form_submit_button(tr("send"), use_container_width=True) and msg.strip():
                db.add_chat(room["id"], ss.user, msg)
                st.rerun()


@st.fragment(run_every=3)
def chat_box(rid: str):
    msgs = db.get_chat(rid)
    html = "".join(f"<div><b>{esc(m['author'])}</b>: {esc(m['body'])}</div>" for m in msgs) \
        or "<div style='opacity:.6'>…</div>"
    st.markdown(f"<div class='card movelist' style='font-family:inherit'>{html}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- Ойын беті

def play_page(spec: Spec):
    if ss.rooms.get(spec.key):
        room_view(spec)
        return
    if ss.games.get(spec.key):
        game_view(spec)
        return
    mode = st.radio(tr("mode"), ["ai", "online", "local"], horizontal=True, key=f"mode_{spec.key}",
                    format_func=lambda m: tr(f"mode_{m}"), label_visibility="collapsed")
    if mode == "ai":
        c1, c2 = st.columns([1.2, 1])
        with c1:
            opts = spec.options_ui(f"ai_{spec.key}")
            levels = list(spec.levels) + ["llm"]
            level = st.radio(tr("level"), levels, index=1, horizontal=True, format_func=lvl_name,
                             key=f"lvl_{spec.key}")
            if level == "llm":
                if ss.llm:
                    st.caption(tr("key_status_on", p=f"{ss.llm['provider']} · {ss.llm['model']}"))
                else:
                    st.warning(tr("need_key"))
            color = st.radio(tr("color"), ["white", "black", "random"], horizontal=True,
                             format_func=lambda c: tr(f"col_{c}"), key=f"col_{spec.key}")
            rated = st.toggle(tr("rated"), value=False, disabled=not is_registered() or level == "llm",
                              key=f"rated_{spec.key}", help=tr("guest_note") if not is_registered() else None)
            st.caption(tr("home_free"))
            if st.button(tr("start"), type="primary", use_container_width=True, key=f"start_{spec.key}",
                         disabled=level == "llm" and not ss.llm):
                start_ai(spec, level, color, rated, opts)
                st.rerun()
        with c2:
            st.dataframe([{tr("level"): lvl_name(k), "Elo": spec.ai_elo(k)} for k in spec.levels],
                         hide_index=True, use_container_width=True)
    elif mode == "online":
        online_lobby(spec)
    else:
        with st.form(f"local_form_{spec.key}"):
            opts = spec.options_ui(f"loc_{spec.key}")
            c1, c2 = st.columns(2)
            n1 = c1.text_input(f"⚪ {tr('white')}", value=ss.user or tr("white"))
            n2 = c2.text_input(f"⚫ {tr('black')}", value=tr("black"))
            if st.form_submit_button(tr("start"), type="primary", use_container_width=True):
                start_local(spec, n1, n2, opts)
                st.rerun()
