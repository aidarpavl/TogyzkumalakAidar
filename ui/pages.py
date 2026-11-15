"""Порталдың беттері: басты бет, кіру, рейтинг, профиль, баптаулар, чемпионат, әкімші."""
from __future__ import annotations

import base64
import datetime as dt
import io
import random
import re
from pathlib import Path

import streamlit as st

from core import db, llm
from ui.common import LEVEL_POINTS, esc, is_admin, is_registered, lvl_name, ss, tr
from ui.play import abandon, start_ai
from ui.specs import SPECS

ASSETS = Path(__file__).resolve().parent.parent / "assets"
GAME_KEYS = ["togyz", "asyk", "doyby", "jamby"]
NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі0-9_]{3,20}$")
PHONE_RE = re.compile(r"^\+?[78]\d{10}$")


def goto(page: str):
    ss["_goto"] = page
    st.rerun()


# ---------------------------------------------------------------- Басты бет

def home_page(public: bool = False):
    c1, c2 = st.columns(2)
    c1.image(str(ASSETS / "togyz.png"), use_container_width=True)
    c2.image(str(ASSETS / "asyk.png"), use_container_width=True)
    st.markdown("<div class='ornament'></div>", unsafe_allow_html=True)
    cols = st.columns(4)
    icons = {"togyz": "⚫⚪", "asyk": "🦴", "doyby": "♛", "jamby": "🏹🐎"}
    for col, gk in zip(cols, GAME_KEYS):
        with col:
            st.markdown(f"<div class='gamecard gc-{gk}'><div class='ico'>{icons[gk]}</div>"
                        f"<h3>{tr('game_' + gk)}</h3><p>{tr('desc_' + gk)}</p></div>", unsafe_allow_html=True)
            if st.button(f"{tr('game_' + gk)} — {tr('open_game')}", key=f"home_{gk}", type="primary",
                         use_container_width=True, disabled=public):
                goto(gk)
    st.markdown(f"<div class='card'>{tr('home_free')}<br>{tr('home_champ')}</div>", unsafe_allow_html=True)
    if not public and is_registered():
        if st.button(tr("nav_champ"), use_container_width=True, key="home_champ"):
            goto("champ")


def auth_panel():
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
                        st.rerun()
    with col2:
        st.markdown(f"<div class='card'><b>🎭 {tr('guest')}</b><br><small>{tr('guest_note')}</small></div>",
                    unsafe_allow_html=True)
        if st.button(tr("as_guest"), use_container_width=True, key="guest_btn"):
            ss.user = f"{tr('guest')}-{random.randint(1000, 9999)}"
            ss.guest = True
            st.rerun()


# ---------------------------------------------------------------- Рейтинг

def _podium(rows, key="rating", fmt=lambda r: f"⭐ {r['rating']}"):
    top3 = rows[:3]
    if not top3:
        return
    order = [1, 0, 2] if len(top3) == 3 else list(range(len(top3)))
    medals = {0: ("p1", "🥇"), 1: ("p2", "🥈"), 2: ("p3", "🥉")}
    html = "<div class='podium'>"
    for i in order:
        r = top3[i]
        cls, md = medals[i]
        html += f"<div class='{cls}'>{md}<br>{esc(r['username'])}<div class='r'>{fmt(r)}</div></div>"
    st.markdown(html + "</div>", unsafe_allow_html=True)


def rating_page():
    st.markdown(f"### 🏆 {tr('lb_title')}")
    tabs = st.tabs([tr(f"game_{g}") for g in GAME_KEYS] + [tr("nav_champ")])
    for tab, gk in zip(tabs, GAME_KEYS):
        with tab:
            rows = db.leaderboard(gk, 100)
            if not rows:
                st.info(tr("lb_empty"))
                continue
            _podium(rows)
            table = []
            for i, r in enumerate(rows, 1):
                wr = round(100 * r["wins"] / r["games"]) if r["games"] else 0
                table.append({tr("col_place"): i, tr("col_player"): r["username"] + (" 👈" if r["username"] == ss.user else ""),
                              tr("col_rating"): r["rating"], tr("col_games"): r["games"], tr("col_wins"): r["wins"],
                              tr("col_losses"): r["losses"], tr("col_draws"): r["draws"], tr("col_winrate"): wr,
                              tr("col_peak"): r["peak"]})
            st.dataframe(table, hide_index=True, use_container_width=True,
                         column_config={tr("col_winrate"): st.column_config.ProgressColumn(
                             tr("col_winrate"), min_value=0, max_value=100, format="%d%%")})
            recent = db.recent_games(gk, 10)
            if recent:
                st.markdown(f"**{tr('recent')}**")
                st.dataframe([{tr("white"): g["white"], tr("result"): g["result"], tr("black"): g["black"],
                               tr("score"): f"{g['score_w']}:{g['score_b']}",
                               tr("date"): dt.datetime.fromtimestamp(g["created"]).strftime("%d.%m %H:%M")}
                              for g in recent], hide_index=True, use_container_width=True)
    with tabs[-1]:
        champ_leaderboard()


def champ_leaderboard():
    rows = db.champ_leaderboard(100)
    if not rows:
        st.info(tr("lb_empty"))
        return
    _podium(rows, fmt=lambda r: f"🏅 {r['earned']}")
    st.dataframe([{tr("col_place"): i, tr("col_player"): r["username"] + (" 👈" if r["username"] == ss.user else ""),
                   tr("earned"): r["earned"], tr("points"): r["points"], tr("col_wins"): r["champ_wins"],
                   tr("col_losses"): r["champ_losses"]} for i, r in enumerate(rows, 1)],
                 hide_index=True, use_container_width=True)


# ---------------------------------------------------------------- Профиль

def profile_page():
    if not is_registered():
        st.info(tr("profile_guest"))
        return
    st.markdown(f"### 👤 {esc(ss.user)}")
    cols = st.columns(4)
    for col, gk in zip(cols, GAME_KEYS):
        r = db.get_rating(ss.user, gk)
        rank = db.user_rank(ss.user, gk)
        col.metric(tr(f"game_{gk}"), r["rating"], help=f"{tr('col_games')}: {r['games']}")
        col.caption(f"{tr('place')}: {'#' + str(rank) if rank else '—'} · {r['wins']}/{r['losses']}/{r['draws']}")
    w = db.get_wallet(ss.user)
    st.markdown(f"<div class='wallet'><div>{tr('attempts')}<span>{w['attempts']}</span></div>"
                f"<div>{tr('points')}<span>{w['points']}</span></div>"
                f"<div>{tr('earned')}<span>{w['earned']}</span></div></div>", unsafe_allow_html=True)
    gk = st.radio(tr("rating_graph"), GAME_KEYS, horizontal=True, format_func=lambda g: tr(f"game_{g}"),
                  key="prof_game")
    hist = db.rating_history(ss.user, gk)
    if len(hist) > 1:
        st.line_chart([1200] + hist, height=200)
    games = db.user_games(ss.user, gk, 50)
    if games:
        rows = []
        for g in games:
            white = g["white"] == ss.user
            res = g["result"]
            outcome = "🤝" if res == "½-½" else ("✅" if (res == "1-0") == white else "❌")
            delta = g["delta_w"] if white else g["delta_b"]
            rows.append({"": outcome, tr("opponent"): g["black"] if white else g["white"],
                         tr("score"): f"{g['score_w']}:{g['score_b']}", "±": f"{delta:+d}" if delta else "",
                         tr("mode"): g["mode"],
                         tr("date"): dt.datetime.fromtimestamp(g["created"]).strftime("%d.%m.%y %H:%M")})
        st.dataframe(rows, hide_index=True, use_container_width=True)
        if gk == "togyz":
            from ui.togyz_extra import review_block  # noqa: WPS433
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


# ---------------------------------------------------------------- Баптаулар

def settings_page():
    tab_ai, tab_view = st.tabs([tr("set_ai"), tr("set_view")])
    with tab_ai:
        st.caption(tr("set_ai_desc"))
        st.caption("🎮 " + " · ".join(tr(f"game_{g}") for g in GAME_KEYS))
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
        st.markdown(f"**{tr('game_togyz')}**")
        ss.board_theme = st.radio("🎨", ["light", "dark"], horizontal=True,
                                  index=0 if ss.board_theme == "light" else 1,
                                  format_func=lambda x: tr("theme_light") if x == "light" else tr("theme_dark"))
        ss.show_numbers = st.toggle(tr("show_numbers"), value=ss.show_numbers)
        ss.show_stones = st.toggle(tr("show_stones"), value=ss.show_stones)
        ss.button_mode = st.toggle(tr("button_mode"), value=ss.button_mode)
        st.markdown(f"**{tr('game_doyby')}**")
        styles = ["", "green", "night"]
        ss.draughts_style = st.radio(tr("board_style"), styles, horizontal=True,
                                     index=styles.index(ss.draughts_style),
                                     format_func=lambda x: tr(f"style_{x}"))


# ---------------------------------------------------------------- Чемпионат

def _img_b64(upload) -> str | None:
    if upload is None:
        return None
    try:
        from PIL import Image  # noqa: WPS433

        im = Image.open(upload).convert("RGB")
        im.thumbnail((900, 900))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=72)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:  # noqa: BLE001
        return None


def _status(st_key: str) -> str:
    return tr(f"st_{st_key}")


def champ_page():
    st.markdown(f"### {tr('champ_title')}")
    price, att = db.int_setting("price"), db.int_setting("attempts_per_pay")
    share, minw = db.int_setting("fund_share"), db.int_setting("min_withdraw")
    st.markdown(tr("champ_rules", price=price, att=att, share=share, minw=minw))
    if not is_registered():
        st.warning(tr("champ_guest"))
        champ_leaderboard()
        return
    w = db.get_wallet(ss.user)
    fs = db.fund_stats()
    quote = db.withdrawal_quote(ss.user)
    st.markdown(f"<div class='wallet'><div>🎟 {tr('attempts')}<span>{w['attempts']}</span></div>"
                f"<div>🏅 {tr('points')}<span>{w['points']}</span></div>"
                f"<div>💰 {tr('fund_avail')}<span>{fs['available']:,} ₸</span></div>"
                f"<div>🤝 {tr('your_share')}<span>{quote:,} ₸</span></div></div>".replace(",", " "),
                unsafe_allow_html=True)
    st.write("")
    t_play, t_pay, t_out, t_lb = st.tabs([tr("champ_play"), tr("pay_title"), tr("withdraw_title"), tr("champ_lb")])

    with t_play:
        gk = st.radio(tr("mode"), GAME_KEYS, horizontal=True, format_func=lambda g: tr(f"game_{g}"),
                      key="champ_game")
        spec = SPECS[gk]
        opts = spec.options_ui("champ")
        level = st.radio(tr("level"), list(LEVEL_POINTS), horizontal=True, key="champ_level",
                         format_func=lambda lv: f"{lvl_name(lv)} (+{LEVEL_POINTS[lv]})")
        color = st.radio(tr("color"), ["white", "black", "random"], horizontal=True,
                         format_func=lambda c: tr(f"col_{c}"), key="champ_color")
        if w["attempts"] < 1:
            st.info(tr("champ_need"))
        if st.button(tr("champ_start"), type="primary", use_container_width=True, disabled=w["attempts"] < 1):
            old = ss.games.get(gk)
            if old:
                abandon(old)
            cid = db.start_champ(ss.user, gk, level)
            if cid:
                start_ai(spec, level, color, False, opts, champ_id=cid)
                goto(gk)
            else:
                st.error(tr("champ_need"))
        hist = db.champ_history(ss.user, 20)
        if hist:
            st.markdown(f"**{tr('champ_hist')}**")
            st.dataframe([{tr("date"): dt.datetime.fromtimestamp(h["created"]).strftime("%d.%m %H:%M"),
                           tr("mode"): tr(f"game_{h['game']}"), tr("level"): lvl_name(h["level"]),
                           tr("result"): {"win": "✅", "loss": "❌", "draw": "🤝"}.get(h["result"], "⏳"),
                           tr("points"): h["points"]} for h in hist], hide_index=True, use_container_width=True)

    with t_pay:
        c1, c2 = st.columns([1, 1.2])
        with c1:
            st.markdown(f"#### {tr('pay_amount', p=price, a=att)}")
            qr = db.get_setting("kaspi_qr")
            if qr:
                st.image(base64.b64decode(qr), use_container_width=True)
            else:
                st.warning(tr("qr_missing"))
            name, phone = db.get_setting("kaspi_name"), db.get_setting("kaspi_phone")
            if name or phone:
                st.markdown(tr("kaspi_to", name=esc(name), phone=esc(phone)))
            if phone:
                st.markdown(tr("kaspi_transfer"))
                st.code(phone, language=None)
        with c2:
            st.markdown(tr("pay_steps", p=price))
            with st.form("pay_form", clear_on_submit=True):
                receipt = st.text_input(tr("receipt"))
                up = st.file_uploader(tr("upload_check"), type=["png", "jpg", "jpeg", "webp"])
                if st.form_submit_button(tr("send_pay"), type="primary", use_container_width=True):
                    img = _img_b64(up)
                    if not receipt.strip() and not img:
                        st.error(tr("pay_need"))
                    elif receipt.strip() and db.receipt_used(receipt):
                        st.error(tr("pay_dup"))
                    else:
                        db.create_payment(ss.user, receipt, img)
                        st.success(tr("pay_sent"))
            mine = db.payments(username=ss.user, limit=20)
            if mine:
                st.markdown(f"**{tr('my_payments')}**")
                st.dataframe([{tr("date"): dt.datetime.fromtimestamp(p["created"]).strftime("%d.%m %H:%M"),
                               tr("amount"): f"{p['amount']} ₸", tr("attempts"): p["attempts"],
                               tr("status"): _status(p["status"])} for p in mine],
                             hide_index=True, use_container_width=True)

    with t_out:
        st.metric(tr("your_share"), f"{quote} ₸", help=f"{tr('points')}: {w['points']} / {fs['points_total']}")
        if w["points"] < minw:
            st.info(tr("withdraw_min", m=minw, p=w["points"]))
            st.progress(min(1.0, w["points"] / max(1, minw)))
        with st.form("wd_form"):
            phone = st.text_input(tr("withdraw_phone"), placeholder="+7 7XX XXX XX XX")
            if st.form_submit_button(tr("withdraw_btn"), type="primary", use_container_width=True,
                                     disabled=w["points"] < minw):
                ph = re.sub(r"[\s\-()]", "", phone)
                if not PHONE_RE.match(ph):
                    st.error(tr("withdraw_bad_phone"))
                else:
                    ph = "+7" + ph[-10:]
                    ok, info = db.request_withdrawal(ss.user, ph)
                    if ok:
                        st.success(tr("withdraw_ok", a=info))
                    else:
                        st.error({"min": tr("withdraw_min", m=minw, p=w["points"]),
                                  "pending": tr("withdraw_pending"), "fund": tr("withdraw_fund")}.get(info, info))
        mine = db.withdrawals(username=ss.user, limit=20)
        if mine:
            st.markdown(f"**{tr('my_withdrawals')}**")
            st.dataframe([{tr("date"): dt.datetime.fromtimestamp(x["created"]).strftime("%d.%m %H:%M"),
                           tr("points"): x["points"], tr("amount"): f"{x['amount']} ₸", "📱": x["phone"],
                           tr("status"): _status(x["status"])} for x in mine], hide_index=True,
                         use_container_width=True)

    with t_lb:
        champ_leaderboard()
    st.caption(tr("legal_note"))


# ---------------------------------------------------------------- Әкімші

def admin_page():
    if not is_admin():
        st.error("⛔")
        return
    st.markdown(f"### {tr('admin_title')}")
    fs = db.fund_stats()
    c = st.columns(5)
    c[0].metric(tr("adm_total_paid"), f"{fs['paid']} ₸")
    c[1].metric(tr("fund"), f"{fs['fund']} ₸")
    c[2].metric(tr("adm_paid_out"), f"{fs['paid_out']} ₸")
    c[3].metric(tr("adm_reserved"), f"{fs['reserved']} ₸")
    c[4].metric(tr("fund_avail"), f"{fs['available']} ₸")
    t1, t2, t3, t4 = st.tabs([tr("adm_payments"), tr("adm_withdrawals"), tr("adm_settings"), tr("adm_users")])
    with t1:
        pend = db.payments("pending", limit=50)
        if not pend:
            st.success(tr("no_pending"))
        for p in pend:
            with st.container(border=True):
                a, b = st.columns([1, 1.4])
                if p["image"]:
                    a.image(base64.b64decode(p["image"]), use_container_width=True)
                b.markdown(f"**{esc(p['username'])}** · {p['amount']} ₸ → {p['attempts']} 🎟<br>"
                           f"🧾 `{esc(p['receipt'] or '—')}`<br>"
                           f"{dt.datetime.fromtimestamp(p['created']).strftime('%d.%m.%Y %H:%M')}",
                           unsafe_allow_html=True)
                if b.button(tr("approve"), key=f"ap_{p['id']}", type="primary"):
                    db.decide_payment(p["id"], True, ss.user)
                    st.rerun()
                if b.button(tr("reject"), key=f"rj_{p['id']}"):
                    db.decide_payment(p["id"], False, ss.user)
                    st.rerun()
        done = db.payments(limit=50)
        if done:
            st.dataframe([{tr("date"): dt.datetime.fromtimestamp(p["created"]).strftime("%d.%m %H:%M"),
                           tr("user"): p["username"], tr("amount"): p["amount"], "🧾": p["receipt"],
                           tr("status"): _status(p["status"])} for p in done], hide_index=True,
                         use_container_width=True)
    with t2:
        pend = db.withdrawals("pending", limit=50)
        if not pend:
            st.success(tr("no_pending"))
        for x in pend:
            with st.container(border=True):
                st.markdown(f"**{esc(x['username'])}** · {x['points']} 🏅 → **{x['amount']} ₸** · 📱 `{esc(x['phone'])}`")
                a, b = st.columns(2)
                if a.button(tr("mark_paid"), key=f"wp_{x['id']}", type="primary"):
                    db.decide_withdrawal(x["id"], True, ss.user)
                    st.rerun()
                if b.button(tr("reject"), key=f"wr_{x['id']}"):
                    db.decide_withdrawal(x["id"], False, ss.user)
                    st.rerun()
        allw = db.withdrawals(limit=50)
        if allw:
            st.dataframe([{tr("date"): dt.datetime.fromtimestamp(x["created"]).strftime("%d.%m %H:%M"),
                           tr("user"): x["username"], tr("amount"): x["amount"], "📱": x["phone"],
                           tr("status"): _status(x["status"])} for x in allw], hide_index=True,
                         use_container_width=True)
    with t3:
        qr = db.get_setting("kaspi_qr")
        if qr:
            st.image(base64.b64decode(qr), width=220)
        with st.form("adm_settings"):
            up = st.file_uploader(tr("adm_qr"), type=["png", "jpg", "jpeg", "webp"])
            phone = st.text_input(tr("kaspi_phone"), value=db.get_setting("kaspi_phone"))
            name = st.text_input(tr("kaspi_name"), value=db.get_setting("kaspi_name"))
            c1, c2 = st.columns(2)
            price = c1.number_input(tr("price"), 50, 100000, db.int_setting("price"), step=50)
            att = c2.number_input(tr("att_per_pay"), 1, 100, db.int_setting("attempts_per_pay"))
            share = c1.number_input(tr("fund_share"), 0, 100, db.int_setting("fund_share"))
            minw = c2.number_input(tr("min_withdraw"), 1, 1_000_000, db.int_setting("min_withdraw"))
            if st.form_submit_button(tr("save"), type="primary"):
                if up is not None:
                    db.set_setting("kaspi_qr", base64.b64encode(up.getvalue()).decode())
                for k, v in (("kaspi_phone", phone), ("kaspi_name", name), ("price", price),
                             ("attempts_per_pay", att), ("fund_share", share), ("min_withdraw", minw)):
                    db.set_setting(k, v)
                st.success(tr("saved"))
                st.rerun()
    with t4:
        with st.form("give_form"):
            c1, c2 = st.columns([2, 1])
            u = c1.text_input(tr("user"))
            n = c2.number_input(tr("attempts"), 1, 1000, 3)
            if st.form_submit_button(tr("adm_give")):
                usr = db.get_user(u.strip())
                if usr:
                    db.add_attempts(usr["username"], int(n))
                    st.success(tr("saved"))
                else:
                    st.error(tr("room_not_found"))
        rows = db.execute("SELECT * FROM wallet ORDER BY paid_total DESC, earned DESC LIMIT 200", (), "all")
        if rows:
            st.dataframe(rows, hide_index=True, use_container_width=True)
