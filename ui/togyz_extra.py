"""Тоғызқұмалаққа арналған қосымшалар: ойын талдауы және есептер."""
from __future__ import annotations

import datetime as dt

import streamlit as st

from core import engine
from ui.common import ss, tr
from ui.specs import SPECS


@st.cache_data(show_spinner=False, max_entries=64)
def _review(moves: tuple[str, ...]):
    return engine.review_game(list(moves), depth=3)


def review_block(moves: list[str], key: str):
    with st.spinner("…"):
        rv = _review(tuple(moves))

    def acc(lst):
        return round(100 * sum(1 for r in lst if r["tag"] in ("best", "good")) / max(1, len(lst)))

    c1, c2, c3 = st.columns(3)
    c1.metric(f"{tr('accuracy')} ⚪", f"{acc([r for r in rv if r['player'] == 0])}%")
    c2.metric(f"{tr('accuracy')} ⚫", f"{acc([r for r in rv if r['player'] == 1])}%")
    c3.metric(tr("moves"), len(moves))
    k = st.slider(tr("replay"), 0, len(moves), len(moves), key=f"{key}_slider")
    rs = engine.replay(moves, k)
    SPECS["togyz"].render(rs, 0, [tr("white"), tr("black")], False, key=f"{key}_board",
                          message=(f"{k}. {moves[k - 1]}" if k else ""))
    rows = [{"#": r["n"], "": "⚪" if r["player"] == 0 else "⚫", tr("moves"): r["move"],
             tr("result"): tr(f"tag_{r['tag']}"), "Δ": r["loss"], tr("best_was", n="").strip(": "): r["best"]}
            for r in rv]
    st.dataframe(rows, hide_index=True, use_container_width=True, height=260)


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
        msg = tr("puzzle_ok", n=pz["gain"]) if status == "ok" else (tr("puzzle_bad") if status == "bad" else "")
        mv = SPECS["togyz"].render(shown, s["turn"], [tr("white"), tr("black")], status != "ok",
                                   key=f"pzb_{seed}", message=msg)
        if mv is not None:
            after = engine.play(s, mv)
            p = s["turn"]
            gain = after["kazan"][p] - s["kazan"][p] + (20 if after["tuzdyk"][p] != s["tuzdyk"][p] else 0)
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
