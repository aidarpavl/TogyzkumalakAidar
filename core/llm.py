"""Нейрожелі провайдерлері: OpenAI, Anthropic Claude, Google Gemini, кез келген OpenAI-үйлесімді API."""
from __future__ import annotations

import re

import requests

PROVIDERS = {
    "OpenAI (ChatGPT)": {"kind": "openai", "base": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "Anthropic (Claude)": {"kind": "anthropic", "base": "https://api.anthropic.com/v1", "model": "claude-sonnet-4-5"},
    "Google (Gemini)": {"kind": "gemini", "base": "https://generativelanguage.googleapis.com/v1beta",
                        "model": "gemini-2.0-flash"},
    "DeepSeek": {"kind": "openai", "base": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    "Groq": {"kind": "openai", "base": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile"},
    "OpenRouter": {"kind": "openai", "base": "https://openrouter.ai/api/v1", "model": "openai/gpt-4o-mini"},
    "Custom (OpenAI-compatible)": {"kind": "openai", "base": "", "model": ""},
}


def chat(cfg: dict, prompt: str, system: str = "", max_tokens: int = 400, timeout: int = 40) -> str:
    kind = cfg["kind"]
    key = cfg["key"].strip()
    model = cfg["model"].strip()
    base = cfg["base"].rstrip("/")
    if kind == "openai":
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        r = requests.post(f"{base}/chat/completions", timeout=timeout,
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                          json={"model": model, "messages": msgs, "max_tokens": max_tokens, "temperature": 0.3})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    if kind == "anthropic":
        body = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
        if system:
            body["system"] = system
        r = requests.post(f"{base}/messages", timeout=timeout, json=body,
                          headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                   "content-type": "application/json"})
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json()["content"])
    if kind == "gemini":
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        r = requests.post(f"{base}/models/{model}:generateContent", timeout=timeout, json=body,
                          headers={"x-goog-api-key": key, "Content-Type": "application/json"})
        r.raise_for_status()
        return "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"])
    raise ValueError("unknown provider")


def describe(state: dict, player: int) -> str:
    p = state["pits"]
    me = p[player * 9:(player + 1) * 9]
    opp = p[(1 - player) * 9:(2 - player) * 9]
    tz = state["tuzdyk"]

    def tzs(owner):
        return f"pit {tz[owner] % 9 + 1}" if tz[owner] != -1 else "none"

    return (
        f"Your pits 1..9: {me}\n"
        f"Opponent pits 1..9: {opp}\n"
        f"Your kazan: {state['kazan'][player]}, opponent kazan: {state['kazan'][1 - player]}\n"
        f"Your tuzdyk (on opponent side): {tzs(player)}; opponent tuzdyk (on your side): {tzs(1 - player)}\n"
        f"Moves so far: {' '.join(state['moves'][-20:]) or '-'}"
    )


RULES_SHORT = (
    "Togyz kumalak rules: each side has 9 pits. A move takes all stones from one own non-empty pit, puts the first "
    "back into the same pit and sows the rest one by one counter-clockwise (own pits 1→9, then opponent pits 1→9). "
    "A pit with exactly 1 stone moves it to the next pit. If the last stone lands in an opponent pit and makes an "
    "even count, you capture them. If it makes exactly 3, the pit becomes your tuzdyk (only one per game, not "
    "opponent's pit 9, not the same number as opponent's tuzdyk). Win with more than 81 stones."
)


def choose_move(cfg: dict, state: dict, legal: list[int]) -> int | None:
    player = state["turn"]
    prompt = (
        RULES_SHORT + "\n\nPosition:\n" + describe(state, player) +
        f"\nLegal moves (pit numbers): {[m + 1 for m in legal]}\n"
        "Think briefly, then answer with the line `MOVE: <number>`."
    )
    txt = chat(cfg, prompt, system="You are a strong togyz kumalak player.", max_tokens=300)
    m = re.search(r"MOVE\s*[:\-]?\s*(\d)", txt, re.I) or re.search(r"(\d)\D*$", txt)
    if m:
        n = int(m.group(1)) - 1
        if n in legal:
            return n
    return None


def coach(cfg: dict, state: dict, player: int, analysis: list[tuple[int, int]], lang: str) -> str:
    lang_name = "Kazakh" if lang == "kz" else "Russian"
    eng = ", ".join(f"pit {m + 1}: {v / 10:+.1f}" for m, v in analysis[:5])
    prompt = (
        RULES_SHORT + "\n\nPosition:\n" + describe(state, player) +
        f"\nEngine evaluation of candidate moves (higher is better for you): {eng}\n\n"
        f"As a friendly coach, explain in {lang_name} in 4-6 short sentences: the key idea of the position, "
        "the best move and why, and one danger to watch for. Use the word 'отау' for pit and 'түздық/туздык' for tuzdyk."
    )
    return chat(cfg, prompt, system="You are a togyz kumalak coach.", max_tokens=500)


# ---------------------------------------------------------------- Барлық ойындарға ортақ

RULES_BY_GAME = {
    "togyz": RULES_SHORT,
    "doyby": ("Draughts (checkers). Captures are mandatory; men move diagonally forward and capture both ways; "
              "kings move and capture any distance diagonally. Squares use a1..h8 (or a1..j10) notation; "
              "':' marks a capture path, '-' a simple move."),
    "jamby": ("Zhamby atu: horseback archery. The archer gallops past a target; the bow bobs with the horse's gait; "
              "wind drifts arrows sideways. You choose the release moment; the aim is then set automatically."),
    "asyk": ("Asyk atu (Kazakh knucklebones): asyks stand inside a ring; you shoot your heavy saqa from the "
             "bottom line; asyks knocked out of the ring are yours; if you capture any, you shoot again."),
}


def choose_option(cfg: dict, game: str, position: str, options: list[str]) -> int | None:
    lst = "\n".join(f"{i + 1}. {o}" for i, o in enumerate(options))
    prompt = (RULES_BY_GAME[game] + "\n\nPosition:\n" + position + "\n\nLegal options:\n" + lst +
              "\nThink briefly, then answer with the line `CHOICE: <number>`.")
    txt = chat(cfg, prompt, system="You are a strong player of traditional Kazakh games.", max_tokens=300)
    m = re.search(r"CHOICE\s*[:\-]?\s*(\d+)", txt, re.I) or re.search(r"(\d+)\D*$", txt)
    if m:
        k = int(m.group(1)) - 1
        if 0 <= k < len(options):
            return k
    return None


def coach_generic(cfg: dict, game: str, position: str, hints: str, lang: str) -> str:
    lang_name = "Kazakh" if lang == "kz" else "Russian"
    prompt = (RULES_BY_GAME[game] + "\n\nPosition:\n" + position + "\n\nEngine notes: " + hints +
              f"\n\nAs a friendly coach, explain in {lang_name} in 4-6 short sentences the key idea, the best move "
              "and why, and one danger to watch for.")
    return chat(cfg, prompt, system="You are a coach of traditional Kazakh games.", max_tokens=500)
