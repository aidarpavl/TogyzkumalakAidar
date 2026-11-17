"""Қазақ күресі — белбеуден ұстап, тік тұрып белдесу.

Детерминистік модель (DT = 0.05 с), тек + − × ÷ және sqrt — JS-те дәл қайталанады
(components/_shared/kures_sim.js). 0 — ойыншы, 1 — ИИ қарсылас.

Кезеңдер:
  1) жақындасу — кілем 8 × 8 м, джойстикпен қозғалу; 1.3 м-де ҰСТАУ (белбеуден ұстасу);
  2) тартыс — ТАРТУ / ИТЕРУ / ТЕРБЕТУ («тас-қайшы-қағаз»: тербету > тарту > итеру > тербету),
     ТІРЕЛУ (басып тұру) — тарту мен тербетуден қорғайды, итеруге осал;
  3) әдіс — қарсыластың тепе-теңдігі әдістің шегінен төмен түссе, әдіс ашылады. Әдіс батырмасын
     басқаннан кейін «дәлдік жолағы» жүреді, ЛАҚТЫРУ (t) — жасыл аймақта басу керек.
     Қарсылас дайындық кезінде дұрыс қарсы әрекетті бастаса — әдіс бұзылады.
Нәтиже: арқамен түсірсе — «Таза жеңіс» (бірден жеңіс), бүйірмен — 3 ұпай, иықпен — 2, тізе/қол тисе — 1.
Белдесу 2 немесе 3 мин; тең болса — «алтын сәт» 60 с (бірінші ұпай жеңеді).
Ескерту (тек ойыншыға): кілемнен шығу немесе 12 с енжарлық; 2 ескерту = қарсыласқа 1 ұпай.

Енгізу: [қадам, "d", [dx, dy]] | [қадам, "g", None] | [қадам, "a", әрекет] | [қадам, "h", 1/0] | [қадам, "t", None].
"""
from __future__ import annotations

import copy
import math

DT = 0.05
MAT = 4.0           # кілемнің жарты ені (8 × 8 м)
GRIP_D = 1.3
WIND = 8            # негізгі әрекеттің дайындығы (0.4 с)
OPEN = 6
GOLDEN_S = 60
BASIC = ("pull", "push", "rock")
BEATS = {"rock": "pull", "pull": "push", "push": "rock"}      # кілт мәнді жеңеді
COUNTER = {v: k for k, v in BEATS.items()}                   # әрекетке қарсы әрекет
# әдіс: (дайындық қадамы, шыдамдылық, ашылу шегі (қарсылас тепе-теңдігі %), күш, ТІРЕЛУ-ге коэф., қарсы әрекет)
THROWS = {
    "surin":   (10, 6.0, 0.60, 0.55, 0.6, "push"),     # Сүріндіру — подножка
    "ilip":    (12, 8.0, 0.52, 0.70, 0.7, "pull"),     # Іліп лақтыру — зацеп
    "burap":   (12, 9.0, 0.50, 0.75, 1.2, "push"),     # Бұрап түсіру — скрутка
    "zhambas": (14, 10.0, 0.45, 0.85, 0.6, "rock"),    # Жамбастан асыру — через бедро
    "koter":   (18, 14.0, 0.36, 1.05, 0.9, "pull"),    # Көтеріп ұру — подъём за пояс
    "arqa":    (20, 16.0, 0.30, 1.20, 0.8, "rock"),    # Арқадан асыру — прогиб
}
THROW_ORDER = ("arqa", "koter", "zhambas", "burap", "ilip", "surin")

BASE = {"w_power": 1.0, "w_grip": 1.0, "w_stamina": 100.0, "w_balance": 100.0, "w_technique": 1.0, "w_speed": 1.0}
STATS = ("w_power", "w_grip", "w_stamina", "w_balance", "w_technique", "w_speed")
STRENGTH_STATS = ("w_power", "w_grip", "w_stamina")
SKILL_STATS = ("w_balance", "w_technique", "w_speed")
WEIGHTS = {60: (0.9, 1.15), 74: (1.0, 1.0), 90: (1.08, 0.93), 100: (1.15, 0.86)}   # (күш, жылдамдық)
# ИИ: (реакция, шешім аралығы, байқау шегі /20, лақтыру кешігуі, әдістің ең жоғары шегі — «шыдам»)
LEVEL = {"easy": (8, 26, 4, 3, 0.60), "medium": (6, 22, 6, 2, 0.52), "hard": (4, 16, 12, 1, 0.50),
         "master": (3, 12, 15, 0, 0.45)}
TITLES = ((0, "t_jas"), (1050, "t_baluan"), (1150, "t_paluan"), (1300, "t_alyp"), (1500, "t_kazhy"))


def title_key(rating) -> str:
    out = TITLES[0][1]
    for lim, k in TITLES:
        if (rating or 0) >= lim:
            out = k
    return out


def stats_from_mult(m: dict) -> dict:
    return {k: round(BASE[k] * float(m.get(k, 1.0) or 1.0), 4) for k in STATS}


def ai_stats(level: str) -> dict:
    f = {"easy": 0.94, "medium": 1.0, "hard": 1.03, "master": 1.07}.get(level, 1.0)
    return {k: round(BASE[k] * f, 4) for k in STATS}


def _mult(att: str, dfn: dict) -> float:
    """Негізгі әрекеттің әсері. -1 — қарсы әрекет (шабуылдаушы өзі зардап шегеді)."""
    winding = dfn["wind"] > 0
    if winding and dfn["act"] == COUNTER[att]:
        return -1.0
    m = 1.0
    if dfn["hold"] == 1:
        m = 1.6 if att == "push" else 0.45
    if winding and dfn["act"] in THROWS:
        m = m * 1.3
    return m


class Sim:
    def __init__(self, hs: dict, level: str, bout_s: int = 180, ai_st: dict | None = None, weight: int = 74):
        self.level = level
        self.react, self.every, self.notice, self.late, self.patience = LEVEL.get(level, LEVEL["medium"])
        wp, ws = WEIGHTS.get(int(weight), WEIGHTS[74])
        ast = ai_st or ai_stats(level)
        self.p = []
        for st in (hs, ast):
            self.p.append({"pow": st["w_power"] * wp, "grip": st["w_grip"], "smax": st["w_stamina"],
                           "bmax": st["w_balance"], "tech": st["w_technique"], "spd": st["w_speed"] * ws,
                           "x": 0.0, "y": 0.0, "dx": 0.0, "dy": 0.0, "s": st["w_stamina"], "b": st["w_balance"],
                           "act": "", "wind": 0, "k": 0, "open": 0, "hold": 0, "cd": 0, "hit": 0, "adv": 0.0,
                           "warn": 0, "pts": 0, "q": 0.0})
        self.bout_steps = int(bout_s / DT)
        self.limit = self.bout_steps + int(GOLDEN_S / DT)
        self.n = 0
        self.grip = False
        self.gwant = 0
        self.golden = False
        self.clean = -1
        self.winner = -2
        self.last_act = 0
        self.close_n = -1
        self.hist = []
        self.seen = -1
        self.events = []
        self.over = False
        self.stand()

    def stand(self):
        for i, r in enumerate(self.p):
            r["x"] = -1.6 if i == 0 else 1.6
            r["y"] = 0.0
            r["dx"] = 0.0
            r["dy"] = 0.0
            r["act"] = ""
            r["wind"] = 0
            r["open"] = 0
            r["hold"] = 0
            r["cd"] = 16
            r["b"] = min(r["bmax"], r["b"] + 30.0)
        self.grip = False
        self.gwant = 0
        self.close_n = -1
        self.seen = -1
        self.last_act = self.n

    # ---------------------------------------------------------------- әрекеттер
    def _start(self, i, act):
        r = self.p[i]
        o = self.p[1 - i]
        if r["wind"] > 0 or not self.grip:
            return
        if act in THROWS:
            w, cost, thr = THROWS[act][0], THROWS[act][1], THROWS[act][2]
            if r["s"] < cost or o["b"] >= thr * o["bmax"]:
                return
            r["s"] = r["s"] - cost
            r["wind"] = w
            self.events.append([self.n, "tstart", i, act])
        else:
            if r["s"] < 5.0:
                return
            r["s"] = r["s"] - 5.0
            r["wind"] = WIND
        r["act"] = act
        r["k"] = 0
        r["hold"] = 0
        if i == 0:
            self.last_act = self.n
            self.hist.append(act if act in BASIC else "rock")
            if len(self.hist) > 5:
                self.hist = self.hist[-5:]

    def _quality(self, r):
        sweet = THROWS[r["act"]][0] - 4
        d = r["k"] - sweet
        if d < 0:
            d = -d
        q = 1.0 - d / (4.0 * r["tech"])
        return 0.15 if q < 0.15 else q

    def _resolve_throw(self, i, q):
        a = self.p[i]
        o = self.p[1 - i]
        t = THROWS[a["act"]]
        name = a["act"]
        a["act"] = ""
        a["wind"] = 0
        a["open"] = OPEN
        if o["wind"] > 0 and o["act"] == t[5]:          # қарсы әрекет — әдіс бұзылды
            a["b"] = max(0.0, a["b"] - 12.0)
            a["hit"] = 0
            o["pts"] = o["pts"] + 1
            o["adv"] = o["adv"] + 12.0
            self.events.append([self.n, "tcounter", 1 - i, name])
            return
        hm = t[4] if o["hold"] == 1 else 1.0
        pw = (1.3 * t[3] * a["pow"] * (0.6 + 0.4 * a["grip"]) * q * (0.55 + 0.45 * a["s"] / a["smax"])
              * (1.6 - 1.2 * o["b"] / o["bmax"]) * hm)
        if pw >= 1.0:
            sc = 4
        elif pw >= 0.7:
            sc = 3
        elif pw >= 0.45:
            sc = 2
        elif pw >= 0.25:
            sc = 1
        else:
            sc = 0
        self.events.append([self.n, "throw", i, name, sc])
        if sc == 0:
            a["b"] = max(0.0, a["b"] - 10.0)
            a["hit"] = 0
            return
        a["adv"] = a["adv"] + pw * 10.0
        if sc == 4:
            self.clean = i
            self.winner = i
            return
        a["pts"] = a["pts"] + sc
        if self.golden:
            self.winner = i
            return
        self.stand()

    # ---------------------------------------------------------------- ИИ
    def _ai(self):
        a = self.p[1]
        h = self.p[0]
        n = self.n
        if not self.grip:
            ux = h["x"] - a["x"]
            uy = h["y"] - a["y"]
            d = math.sqrt(ux * ux + uy * uy)
            if d > 1.1:
                a["dx"] = ux / d
                a["dy"] = uy / d
            else:
                a["dx"] = 0.0
                a["dy"] = 0.0
            if d < GRIP_D:
                if self.close_n < 0:
                    self.close_n = n
                if n - self.close_n >= self.react:
                    self.gwant = 1
            else:
                self.close_n = -1
            return
        a["dx"] = 0.0
        a["dy"] = 0.0
        if a["wind"] > 0 and a["act"] in THROWS:          # әдісті дәл сәтте босату
            if a["k"] >= THROWS[a["act"]][0] - 4 + self.late:
                self._resolve_throw(1, self._quality(a))
            return
        if h["wind"] > 0:
            if self.seen < 0:
                self.seen = n
            if n - self.seen == self.react and a["wind"] == 0 and (self.seen * 7 + 3) % 20 < self.notice:
                c = THROWS[h["act"]][5] if h["act"] in THROWS else COUNTER[h["act"]]
                if a["s"] >= 5.0:
                    self._start(1, c)
                    return
        else:
            self.seen = -1
        if a["wind"] == 0:
            a["hold"] = 1 if (a["b"] < 0.3 * a["bmax"] and a["s"] > 12.0) else 0
            if n % self.every == 0 and a["hold"] == 0:
                for t in THROW_ORDER:
                    if (THROWS[t][2] <= self.patience and h["b"] < THROWS[t][2] * h["bmax"]
                            and a["s"] >= THROWS[t][1] + 4.0):
                        self._start(1, t)
                        return
                if a["s"] < 5.0:
                    return
                cnt = {"pull": 0, "push": 0, "rock": 0}
                for x in self.hist:
                    cnt[x] = cnt[x] + 1
                best = "pull"
                if cnt["push"] > cnt[best]:
                    best = "push"
                if cnt["rock"] > cnt[best]:
                    best = "rock"
                act = COUNTER[best] if len(self.hist) >= 3 else BASIC[(n // self.every) % 3]
                if h["hold"] == 1:
                    act = "push"
                self._start(1, act)

    # ---------------------------------------------------------------- қадам
    def step(self, inputs: list):
        n = self.n
        h = self.p[0]
        for ev in inputs:
            k = ev[1]
            if k == "d":
                h["dx"] = float(ev[2][0])
                h["dy"] = float(ev[2][1])
            elif k == "g":
                if not self.grip:
                    self.gwant = 1
                    self.last_act = n
            elif k == "a":
                self._start(0, ev[2])
            elif k == "h":
                h["hold"] = 1 if (ev[2] and h["wind"] == 0) else 0
            elif k == "t":
                if h["wind"] > 0 and h["act"] in THROWS and self.winner == -2:
                    self._resolve_throw(0, self._quality(h))
        if self.winner == -2 and (n % 2 == 0 or self.grip):
            self._ai()
        if self.winner == -2:
            self._physics(n)
        # енжарлық (тек ойыншыға)
        if self.winner == -2 and n - self.last_act > 240:
            self._warn(n, "passive")
        # нәтиже
        self.n = n + 1
        if self.winner == -2 and not self.golden and self.n >= self.bout_steps:
            a, b = self.p[0]["pts"], self.p[1]["pts"]
            if a != b:
                self.winner = 0 if a > b else 1
            else:
                self.golden = True
                self.events.append([n, "golden", 0])
        if self.winner == -2 and self.golden and self.n >= self.limit:
            d = self.p[0]["adv"] - self.p[1]["adv"]
            self.winner = 0 if d > 1.0 else (1 if d < -1.0 else -1)
        if self.winner != -2:
            self.over = True
            self.events.append([n, "end", self.winner])

    def _warn(self, n, why):
        h = self.p[0]
        h["warn"] = h["warn"] + 1
        self.last_act = n
        self.events.append([n, "warn", 0, why])
        if h["warn"] >= 2:
            h["warn"] = 0
            self.p[1]["pts"] = self.p[1]["pts"] + 1
            self.events.append([n, "pen", 1])
            if self.golden:
                self.winner = 1

    def _physics(self, n):
        for i in range(2):
            r = self.p[i]
            if not self.grip:
                sp = (1.6 + 1.2 * r["spd"]) * DT
                r["x"] = r["x"] + r["dx"] * sp
                r["y"] = r["y"] + r["dy"] * sp
                if r["x"] > MAT or r["x"] < -MAT or r["y"] > MAT or r["y"] < -MAT:
                    r["x"] = r["x"] * 0.7
                    r["y"] = r["y"] * 0.7
                    if i == 0:
                        r["dx"] = 0.0
                        r["dy"] = 0.0
                        self._warn(n, "out")
                r["s"] = min(r["smax"], r["s"] + 8.0 * DT)
                r["b"] = min(r["bmax"], r["b"] + 6.0 * DT)
            else:
                if r["hold"] == 1:
                    r["s"] = max(0.0, r["s"] - 6.0 * DT)
                    if r["s"] <= 0.0:
                        r["hold"] = 0
                elif r["wind"] == 0:
                    r["s"] = min(r["smax"], r["s"] + 4.0 * DT)
                if r["hit"] > 40:
                    r["b"] = min(r["bmax"], r["b"] + 2.0 * DT)
            if r["cd"] > 0:
                r["cd"] = r["cd"] - 1
            if r["open"] > 0:
                r["open"] = r["open"] - 1
            r["hit"] = r["hit"] + 1
        if not self.grip:
            dx = self.p[1]["x"] - self.p[0]["x"]
            dy = self.p[1]["y"] - self.p[0]["y"]
            if (self.gwant == 1 and dx * dx + dy * dy < GRIP_D * GRIP_D
                    and self.p[0]["cd"] == 0 and self.p[1]["cd"] == 0):
                self.grip = True
                self.events.append([n, "grip", 0])
                mx = (self.p[0]["x"] + self.p[1]["x"]) / 2
                my = (self.p[0]["y"] + self.p[1]["y"]) / 2
                d = math.sqrt(dx * dx + dy * dy)
                ux, uy = (dx / d, dy / d) if d > 1e-9 else (1.0, 0.0)
                self.p[0]["x"] = mx - ux * 0.45
                self.p[0]["y"] = my - uy * 0.45
                self.p[1]["x"] = mx + ux * 0.45
                self.p[1]["y"] = my + uy * 0.45
            self.gwant = 0
            return
        res = []
        for i in range(2):
            r = self.p[i]
            if r["wind"] > 0:
                r["k"] = r["k"] + 1
                r["wind"] = r["wind"] - 1
                if r["wind"] == 0:
                    res.append(i)
        for i in res:
            a = self.p[i]
            o = self.p[1 - i]
            if self.winner != -2 or not self.grip or a["act"] == "":
                continue
            if a["act"] in THROWS:
                self._resolve_throw(i, 0.3)
                continue
            m = _mult(a["act"], o)
            if m < 0:
                a["b"] = max(0.0, a["b"] - 6.0)
                a["hit"] = 0
                o["adv"] = o["adv"] + 6.0
                self.events.append([n, "counter", 1 - i])
            else:
                if o["open"] > 0:
                    m = m * 1.5
                dmg = 5.0 * a["pow"] * a["grip"] * m * (0.5 + 0.5 * a["s"] / a["smax"]) - 1.5 * o["tech"]
                if dmg < 1.0:
                    dmg = 1.0
                o["b"] = max(0.0, o["b"] - dmg)
                o["hit"] = 0
                a["adv"] = a["adv"] + dmg
                self.events.append([n, a["act"], i])
            a["act"] = ""
            a["open"] = OPEN


def simulate(hs: dict, level: str, inputs: list, bout_s: int = 180, ai_st: dict | None = None,
             weight: int = 74) -> dict:
    sim = Sim(hs, level, bout_s, ai_st, weight)
    by = {}
    for ev in inputs:
        by.setdefault(int(ev[0]), []).append(ev)
    while not sim.over and sim.n < sim.limit + 5:
        sim.step(by.get(sim.n, []))
    w = sim.winner
    return {"win": 1 if w == 0 else (0 if w == 1 else -1), "pf": sim.p[0]["pts"], "pa": sim.p[1]["pts"],
            "clean": sim.clean, "adv": round(sim.p[0]["adv"] - sim.p[1]["adv"], 2), "steps": sim.n,
            "events": sim.events[-40:]}


def clean_inputs(inputs, max_steps: int) -> list:
    out = []
    for ev in list(inputs)[:20000]:
        try:
            n, k = int(ev[0]), str(ev[1])
        except (TypeError, ValueError, IndexError):
            continue
        if not (0 <= n <= max_steps):
            continue
        if k == "d":
            try:
                dx, dy = float(ev[2][0]), float(ev[2][1])
            except (TypeError, ValueError, IndexError):
                continue
            if not (math.isfinite(dx) and math.isfinite(dy)):
                continue
            d = math.sqrt(dx * dx + dy * dy)
            out.append([n, "d", [dx, dy] if 0.98 <= d <= 1.02 else [0.0, 0.0]])
        elif k == "a" and (ev[2] in BASIC or ev[2] in THROWS):
            out.append([n, "a", ev[2]])
        elif k == "h":
            out.append([n, "h", 1 if ev[2] else 0])
        elif k in ("g", "t"):
            out.append([n, k, None])
    out.sort(key=lambda e: e[0])
    return out


# ---------------------------------------------------------------- ойын күйі

def new_state(opts: dict | None = None) -> dict:
    opts = opts or {}
    w = int(opts.get("weight", 74))
    return {"game": "kures", "stats": opts.get("stats") or [dict(BASE), dict(BASE)],
            "level": opts.get("level", "medium"), "bout_s": int(opts.get("bout_s", 180)),
            "weight": w if w in WEIGHTS else 74, "solo": False,
            "inputs": [None, None], "rides": [None, None], "turn": 0, "over": False, "winner": None,
            "reason": None, "moves": [], "last": None}


def clone(s):
    return copy.deepcopy(s)


def legal_moves(s):
    return [] if s["over"] else ["fight"]


def _key(r):
    return (r["win"], 1 if r["clean"] == 0 else 0, r["pf"] - r["pa"], r["adv"])


def apply_move(s: dict, mv: dict) -> dict:
    if s["over"]:
        raise ValueError("game over")
    p = s["turn"]
    inp = clean_inputs(mv.get("inputs", []), int((s["bout_s"] + GOLDEN_S) / DT) + 10)
    r = simulate(s["stats"][p], s["level"], inp, s["bout_s"], s.get("ai_stats"), s.get("weight", 74))
    s["inputs"][p] = inp
    s["rides"][p] = {"win": r["win"], "pf": r["pf"], "pa": r["pa"], "clean": r["clean"], "adv": r["adv"]}
    s["moves"].append(f"{'⚪⚫'[p]} {'✔' if r['clean'] == 0 else ''}{r['pf']}:{r['pa']}")
    s["last"] = {"player": p, "id": len(s["moves"])}
    s["reason"] = "score"
    if s["solo"]:
        s["over"] = True
        s["winner"] = p if r["win"] == 1 else (1 - p if r["win"] == 0 else -1)
        return s
    if s["rides"][1 - p] is None:
        s["turn"] = 1 - p
        return s
    s["over"] = True
    ka, kb = _key(s["rides"][0]), _key(s["rides"][1])
    s["winner"] = 0 if ka > kb else 1 if kb > ka else -1
    return s


def play(s, mv):
    return apply_move(clone(s), mv)


def score(s) -> list[int]:
    if s.get("solo"):
        for p, r in enumerate(s["rides"]):
            if r:
                out = [0, 0]
                out[p] = r["pf"] + (10 if r["clean"] == 0 else 0)
                out[1 - p] = r["pa"] + (10 if r["clean"] == 1 else 0)
                return out
        return [0, 0]
    return [((r or {}).get("pf", 0) + (10 if (r or {}).get("clean") == 0 else 0)) for r in s["rides"]]


def demo_inputs(level: str, hs: dict, bout_s: int = 180, skill: str = "medium", ai_st: dict | None = None,
                offset: int = 0, weight: int = 74) -> list:
    """Сынақ «боты»: ойыншы орнына берілген деңгейдегі тактикамен ойнайды."""
    sim = Sim(hs, level, bout_s, ai_st, weight)
    react, every, notice, late, patience = LEVEL.get(skill, LEVEL["medium"])
    out, seen = [], -1
    while not sim.over and sim.n < sim.limit + 5:
        n, h, a, ev = sim.n, sim.p[0], sim.p[1], []
        if not sim.grip:
            ux, uy = a["x"] - h["x"], a["y"] - h["y"]
            d = math.sqrt(ux * ux + uy * uy)
            if n % 4 == 0:
                ev.append([n, "d", [round(ux / d, 3), round(uy / d, 3)] if d > 1.0 else [0, 0]])
            if d < GRIP_D and (n + offset) % 6 == 0:
                ev.append([n, "g", None])
        elif h["wind"] > 0 and h["act"] in THROWS:
            if h["k"] >= THROWS[h["act"]][0] - 4 + late:
                ev.append([n, "t", None])
        else:
            if a["wind"] > 0:
                if seen < 0:
                    seen = n
                if n - seen == react and h["wind"] == 0 and (seen * 11 + 5) % 20 < notice:
                    c = THROWS[a["act"]][5] if a["act"] in THROWS else COUNTER[a["act"]]
                    ev.append([n, "a", c])
            else:
                seen = -1
            want_hold = 1 if (h["b"] < 0.3 * h["bmax"] and h["s"] > 12.0 and h["wind"] == 0) else 0
            if want_hold != h["hold"]:
                ev.append([n, "h", want_hold])
            if h["wind"] == 0 and want_hold == 0 and (n + offset) % every == 0:
                act = None
                for t in THROW_ORDER:
                    if THROWS[t][2] <= patience and a["b"] < THROWS[t][2] * a["bmax"] and h["s"] >= THROWS[t][1] + 4.0:
                        act = t
                        break
                if act is None:
                    act = "push" if a["hold"] == 1 else BASIC[((n + offset) // every) % 3]
                ev.append([n, "a", act])
        out.extend(ev)
        sim.step(ev)
    return out
