"""Builds the fight panel: the last 12 months of contributions as a fighting-game stage. A stick figure with a
Mars-orange headband fights through the year: every week with contributions is one hit, and the bigger the week the
bigger the move (jab, kick, flying kick, rising uppercut). Back-to-back active weeks make a combo, blocks fly, THE YEAR's
health bar drains and the last hit is a K.O. Then the stage resets and the round starts again.

Run: GH_TOKEN=<token> python assets/make_fight.py [out_dir]  -> writes fight-light.svg and fight-dark.svg
(default out_dir: next to this file).
"""
import math
import random
import sys
from pathlib import Path

from make_arcade import CELL, GY, MONO, MONTHS, PITCH, QUARTILES, W, fetch, level, streaks

H = 262
FLOOR = GY + 7 * PITCH  # where the fighter's feet are
THIGH, SHIN, UPPER, FORE, TORSO, SHOULDER, NECK = 10.5, 10.5, 9, 9, 15, 13.5, 21.5
HIP = THIGH + SHIN  # hip height when standing straight
RUN, DASH, DASH_FROM = 170, 320, 70  # px/s; runs longer than DASH_FROM px become dashes
QUICK = .85  # time scale for every move
INTRO, KO, RESET = 1.6, 3.0, 1.4
SLOWMO = 2.2  # the finisher plays this many times slower
SNAP, SOFT, FALL = "cubic-bezier(.2,.9,.3,1)", "ease-in-out", "cubic-bezier(.5,0,.9,.6)"

THEMES = {
    "light": dict(text="#1f2328", soft="#59636e", muted="#d1d9e0", dust="#d0d7de", mars="#dd6a45", gold="#c27c0e",
                  ghost="#f6dfae", star=["#f3d58f", "#e8b345", "#d4920f", "#a96b00"]),
    "dark": dict(text="#e6edf3", soft="#9198a1", muted="#3d444d", dust="#30363d", mars="#f0805a", gold="#fbbf24",
                 ghost="#6b5520", star=["#5a4719", "#9c7419", "#dba51e", "#fcd34d"]),
}

# Poses in degrees. Limbs: 0 hangs straight down, positive swings forward (the fighter faces right); forearms and shins
# are relative to the bone above them. Torso: positive leans forward. dy: hip offset, negative is up. F/B: front/back.
GUARD = dict(torso=6, uaF=35, faF=110, uaB=12, faB=128, thF=24, shF=-20, thB=-20, shB=-10, dy=2)


def P(**kw):
    return {**GUARD, **kw}


LOW = P(dy=4, thF=28, shF=-28, thB=-24, shB=-18)
RUNS = [dict(torso=16, uaF=-40, faF=80, uaB=48, faB=85, thF=50, shF=-28, thB=-40, shB=-60, dy=0),
        dict(torso=16, uaF=4, faF=85, uaB=4, faB=85, thF=-4, shF=-18, thB=24, shB=-118, dy=-3),
        dict(torso=16, uaF=48, faF=85, uaB=-40, faB=80, thF=-40, shF=-60, thB=50, shB=-28, dy=0),
        dict(torso=16, uaF=4, faF=85, uaB=4, faB=85, thF=24, shF=-118, thB=-4, shB=-18, dy=-3)]
VICTORY = dict(torso=-2, uaF=170, faF=4, uaB=-30, faB=40, thF=10, shF=-2, thB=-10, shB=-2, dy=0)

_jab = P(torso=20, uaF=88, faF=4, uaB=22, faB=120, thF=30, shF=-14)
_kick = P(torso=-18, thF=95, shF=-3, thB=-8, shB=-2, uaF=15, faF=100, uaB=-35, faB=70, dy=-1)
_chamber = P(torso=-4, thF=100, shF=-115, thB=-6, shB=-4, dy=-1)
_fly = dict(torso=-24, uaF=-45, faF=40, uaB=60, faB=60, thF=100, shF=-2, thB=-45, shB=-100, dy=-26)
_rise = dict(torso=6, uaF=168, faF=6, uaB=30, faB=95, thF=75, shF=-115, thB=-8, shB=-38, dy=-40)
# Moves: (effector, index of the hitting frame, frames). Frame: (seconds, pose, hip shift in px, easing to the next frame).
MOVES = {
    "jab": ("hand", 2, [(0, GUARD, 0, SOFT), (.07, P(torso=0, uaF=20, faF=130), -1, SNAP), (.12, _jab, 5, "linear"),
                        (.18, _jab, 5, SOFT), (.30, GUARD, 3, SOFT)]),
    "kick": ("foot", 2, [(0, GUARD, 0, SOFT), (.09, _chamber, 2, SNAP), (.15, _kick, 4, "linear"), (.22, _kick, 4, SOFT),
                         (.30, _chamber, 4, SOFT), (.38, GUARD, 5, SOFT)]),
    "fly": ("foot", 3, [(0, GUARD, 0, SOFT),
                        (.09, P(dy=6, torso=16, thF=40, shF=-70, thB=-32, shB=-62, uaF=-20, faF=60, uaB=-30, faB=60), 0, SNAP),
                        (.22, dict(torso=-8, uaF=-35, faF=50, uaB=55, faB=70, thF=85, shF=-105, thB=-25, shB=-115, dy=-30), 12, "linear"),
                        (.30, _fly, 22, "linear"), (.36, _fly, 23, SOFT),
                        (.48, P(dy=6, thF=38, shF=-60, thB=-30, shB=-55), 28, SOFT), (.58, GUARD, 28, SOFT)]),
    "uppercut": ("hand", 2, [(0, GUARD, 0, SOFT),
                             (.10, P(dy=8, torso=22, uaF=15, faF=145, thF=45, shF=-80, thB=-32, shB=-66), 0, SNAP),
                             (.22, _rise, 8, "linear"), (.32, {**_rise, "dy": -48}, 10, FALL),
                             (.50, P(dy=-10, thF=40, shF=-75, thB=-22, shB=-80, uaF=60, faF=90), 12, SOFT),
                             (.58, P(dy=7, thF=40, shF=-70, thB=-30, shB=-60), 12, SOFT), (.70, GUARD, 12, SOFT)]),
}
JOINTS = ["torso", "uaF", "faF", "uaB", "faB", "thF", "shF", "thB", "shB"]


def bone(angle, length):
    """End of a bone of `length` hanging from 0,0 after an SVG rotate(angle)."""
    a = math.radians(angle)
    return -length * math.sin(a), length * math.cos(a)


def effector(kind, p):
    """Front hand or foot of pose p, relative to the hip."""
    if kind == "hand":
        t = p["torso"]
        sx, sy = -bone(t, SHOULDER)[0], -bone(t, SHOULDER)[1]
        ex, ey = bone(t - p["uaF"], UPPER)
        hx, hy = bone(t - p["uaF"] - p["faF"], FORE)
        return sx + ex + hx, sy + ey + hy
    kx, ky = bone(-p["thF"], THIGH)
    fx, fy = bone(-p["thF"] - p["shF"], SHIN)
    return kx + fx, ky + fy


def move_for(week, biggest):
    if week >= 40 or week == biggest:
        return "uppercut"
    return "fly" if week >= 15 else "kick" if week >= 5 else "jab"


def build(weeks, xp_now):
    days = [d for w in weeks for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    total, active = sum(counts), sum(1 for n in counts if n)
    cur_streak, best_streak = streaks(counts)
    grid_w = len(weeks) * PITCH - (PITCH - CELL)
    gx = (W - grid_w) / 2
    x0 = gx - 14

    blocks, dust, months = [], [], []
    for col, week in enumerate(weeks):
        for d in week["contributionDays"]:
            x, y = gx + col * PITCH, GY + d["weekday"] * PITCH
            if d["contributionCount"]:
                blocks.append(dict(x=x, y=y, col=col, row=d["weekday"], q=QUARTILES.index(d["contributionLevel"])))
            else:
                dust.append(f'<circle cx="{x + CELL / 2:.1f}" cy="{y + CELL / 2:.1f}" r="1.6"/>')
        first = week["contributionDays"][0]["date"]
        if first[8:10] <= "07" and (not months or col - months[-1][0] > 2):
            months.append((col, MONTHS[int(first[5:7]) - 1]))
    sums = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]
    fights = [c for c, s in enumerate(sums) if s]

    frames = []  # (seconds, hip x, pose, easing to the next frame)

    def at(t, x, p, ease="linear"):
        if frames and t - frames[-1][0] < 1e-3:
            frames.pop()
        frames.append((t, x, p, ease))

    for k in range(int(INTRO / .4) + 1):  # bounce on the spot during ROUND 1 / FIGHT!
        at(k * .4, x0, GUARD if k % 2 == 0 else LOW, SOFT)
    t, x = INTRO, x0

    def run_to(target, end_pose=GUARD):
        nonlocal t, x
        dist = target - x
        if dist <= 2:
            return
        step = .06 if dist > DASH_FROM else .08
        if dist > DASH_FROM:
            dashes.append((t, t + dist / DASH))
        dur = dist / (DASH if dist > DASH_FROM else RUN)
        n = max(2, round(dur / step))
        for k in range(1, n):
            at(t + dur * k / n, x + dist * k / n, RUNS[k % 4])
        t, x = t + dur, target
        at(t, x, end_pose, SOFT)

    hits, dashes, biggest = [], [], max(sums) if fights else 0
    for i, col in enumerate(fights):
        last = i == len(fights) - 1
        kind = "uppercut" if last else move_for(sums[col], biggest)  # the last hit is the finisher, in slow motion
        pace = QUICK * (SLOWMO if last else 1)
        reach, imp, seq = MOVES[kind]
        fx, fy = effector(reach, seq[imp][1])
        col_x = gx + col * PITCH + CELL / 2
        run_to(col_x - fx - seq[imp][2])
        base = x
        for dt, p, dx, ease in seq:
            at(t + dt * pace, base + dx, p, ease)
        p = seq[imp][1]
        hits.append(dict(t=t + seq[imp][0] * pace, col=col, kind=kind, dmg=sums[col], slow=pace / QUICK,
                         at=(base + seq[imp][2] + fx, FLOOR - HIP + p["dy"] + fy)))
        t, x = t + seq[-1][0] * pace, base + seq[-1][2]
    t_ko = hits[-1]["t"] if hits else t
    at(t + .2, x, VICTORY, "cubic-bezier(.2,.8,.4,1)")  # arm up, then a little victory hop
    at(t + .45, x, {**VICTORY, "dy": -12}, FALL)
    at(t + .7, x, VICTORY, SOFT)
    t_reset = t_ko + KO
    at(t_reset, x, VICTORY, SOFT)
    # Off the right edge, back in from the left while the blocks come back.
    at(t_reset + .45, W + 40, RUNS[0])
    at(t_reset + .46, -40, RUNS[1])
    D = t_reset + RESET
    for k in range(1, 9):
        at(t_reset + .46 + (D - t_reset - .46) * k / 9, -40 + (x0 + 40) * k / 9, RUNS[k % 4])
    at(D, x0, GUARD)

    def kf(name, stops):
        return f"@keyframes {name} {{ " + " ".join(f"{100 * s / D:.2f}% {{ {css} }}" for s, css in stops) + " }"

    def ease(e):
        return "" if e == "linear" else f";animation-timing-function:{e}"

    def track(name, value):
        """Keyframes for one joint over all frames, leaving out frames where it holds still."""
        vals = [(s, value(hx, p), e) for s, hx, p, e in frames]
        keep = [v for i, v in enumerate(vals) if i in (0, len(vals) - 1) or not vals[i - 1][1] == v[1] == vals[i + 1][1]]
        return kf(name, [(s, f"transform:{v}{ease(e)}") for s, v, e in keep])

    css = [track("root", lambda hx, p: f"translate({hx:.1f}px,{FLOOR - HIP + p['dy']:.1f}px)"),
           track("shadow", lambda hx, p: f"translate({hx:.1f}px,{FLOOR + 1}px) scale({max(.35, 1 + min(0, p['dy']) / 60):.2f})")]
    dash = [(0, "opacity:0")]
    for a, b in dashes:
        dash += [(a, "opacity:0"), (a + .08, "opacity:.7"), (b - .05, "opacity:.7"), (b, "opacity:0")]
    css.append(kf("dash", dash + [(D, "opacity:0")]))
    if hits:
        css.append(kf("flash", [(t_ko - .01, "opacity:0"), (t_ko, "opacity:.3"), (t_ko + .35, "opacity:0")]))
    for j in JOINTS:
        css.append(track(j, lambda hx, p, j=j: f"rotate({(1 if j == 'torso' else -1) * p[j]:.0f}deg)"))

    # Blocks fly off when their week is hit, nearest to the impact first; they pop back during the reset.
    rng = random.Random(3)
    by_col = {h["col"]: h for h in hits}
    block_svg = []
    for i, b in enumerate(blocks):
        h = by_col[b["col"]]
        start = h["t"] + .018 * abs(b["y"] + CELL / 2 - h["at"][1]) / PITCH
        up = h["kind"] == "uppercut"
        vx, vy = (rng.uniform(-30, 60), rng.uniform(200, 280)) if up else (rng.uniform(40, 120), rng.uniform(110, 200))
        spin = rng.uniform(-540, 540)
        path = [(start + k * .1 * h["slow"], vx * k * .1, -vy * k * .1 + 260 * (k * .1) ** 2, spin * k / 7, 1 if k < 4 else 1 - (k - 3) / 4)
                for k in range(8)]
        back = t_reset + .3 + .6 * (b["x"] - gx) / grid_w
        stops = [(0, "transform:translate(0px,0px) rotate(0deg) scale(1);opacity:1")]
        stops += [(s, f"transform:translate({dx:.1f}px,{dy:.1f}px) rotate({r:.0f}deg) scale(1);opacity:{o:.2f}") for s, dx, dy, r, o in path]
        stops += [(back, f"transform:translate(0px,0px) rotate(0deg) scale(0);opacity:0;animation-timing-function:cubic-bezier(.34,1.56,.64,1)"),
                  (back + .4, "transform:translate(0px,0px) rotate(0deg) scale(1);opacity:1")]
        css.append(kf(f"b{i}", stops))
        block_svg.append(f'<rect class="bl q{b["q"]}" x="{b["x"]:.1f}" y="{b["y"]}" width="{CELL}" height="{CELL}" rx="3" style="animation-name:b{i}"/>')

    # Sparks, combo counter, health bars and the stage shake on uppercuts.
    sparks, combos, hp, ghost, shake = [], [], [(0, 1)], [(0, 1)], [(0, "transform:translate(0px,0px)")]
    left, combo = total, 0
    for i, h in enumerate(hits):
        combo = combo + 1 if i and h["col"] - hits[i - 1]["col"] == 1 else 1  # a combo is a run of back-to-back active weeks
        before, left = left, left - h["dmg"]
        hp += [(h["t"], before / total), (h["t"] + .12, left / total)]
        if i == 0:
            ghost.append((h["t"], 1))
        ghost.append((h["t"] + .5, left / total))
        big = h["kind"] == "uppercut"
        css.append(kf(f"k{i}", [(h["t"] - .01, "transform:scale(.2);opacity:0"), (h["t"], "transform:scale(.2);opacity:1"), (h["t"] + .1, f"transform:scale({1.5 if big else 1});opacity:1"),
                                (h["t"] + .22, f"transform:scale({1.8 if big else 1.25});opacity:0")]))
        sparks.append(f'<g transform="translate({h["at"][0]:.1f} {h["at"][1]:.1f})"><g class="spark" style="animation-name:k{i}">'
                      + "".join(f'<line x1="{3 * math.cos(a):.1f}" y1="{3 * math.sin(a):.1f}" x2="{9 * math.cos(a):.1f}" y2="{9 * math.sin(a):.1f}"/>'
                                for a in (k * math.pi / 4 + .3 for k in range(8))) + "</g></g>")
        if combo >= 2:
            end = hits[i + 1]["t"] if i + 1 < len(hits) and hits[i + 1]["col"] - h["col"] == 1 else h["t"] + .9
            css.append(kf(f"c{i}", [(h["t"] - .01, "opacity:0;transform:scale(1.35)"), (h["t"], f"opacity:1;transform:scale(1.35){ease(SNAP)}"),
                                    (h["t"] + .12, "opacity:1;transform:scale(1)"), (max(end - .01, h["t"] + .13), "opacity:1;transform:scale(1)"),
                                    (max(end, h["t"] + .14), "opacity:0;transform:scale(1)")]))
            combos.append(f'<text class="combo" x="{gx:.1f}" y="77" style="animation-name:c{i}">{combo} HITS</text>')
        if big and shake[-1][0] < h["t"]:
            shake += [(h["t"] + d, f"transform:translate({sx}px,{sy}px)") for d, sx, sy in
                      [(0, 0, 0), (.03, 4, -3), (.06, -4, 2), (.09, 3, 2), (.12, -2, -1), (.16, 0, 0)]]
    hp += [(t_reset + .3, 0), (t_reset + 1.1, 1), (D, 1)]
    ghost += [(t_reset + .3, 0), (t_reset + 1.1, 1), (D, 1)]
    css.append(kf("hp", [(s, f"transform:scaleX({v:.3f}){ease('ease-out')}") for s, v in hp]))
    css.append(kf("ghost", [(s, f"transform:scaleX({v:.3f})") for s, v in ghost]))
    css.append(kf("shake", shake + [(D, "transform:translate(0px,0px)")]))
    css.append(kf("round", [(.15, f"opacity:0;transform:scale(.7){ease(SNAP)}"), (.35, "opacity:1;transform:scale(1)"),
                            (.85, "opacity:1;transform:scale(1)"), (.95, "opacity:0;transform:scale(1.1)")]))
    css.append(kf("go", [(.9, f"opacity:0;transform:scale(1.8){ease(SNAP)}"), (1.05, "opacity:1;transform:scale(1)"),
                         (1.45, "opacity:1;transform:scale(1)"), (1.65, "opacity:0;transform:scale(1.2)")]))
    css.append(kf("ko", [(t_ko + .1, f"opacity:0;transform:scale(2.2){ease(SNAP)}"), (t_ko + .3, "opacity:1;transform:scale(1)"),
                         (t_reset, "opacity:1;transform:scale(1)"), (t_reset + .3, "opacity:0;transform:scale(1)")]))
    return dict(gx=gx, grid_w=grid_w, D=D, x0=x0, css="\n  ".join(css), dust="".join(dust), blocks="\n".join(block_svg),
                sparks="".join(sparks), combos="".join(combos), months=months, total=total, active=active,
                cur=cur_streak, best=best_streak, lv=level(xp_now))


def rig():
    """The fighter, hip at 0,0: every joint is a group rotated by its own animation."""
    def limb(bones):
        (a, la), (b, lb) = bones
        return (f'<g class="j" style="animation-name:{a};transform:rotate({-GUARD[a]}deg)"><line y2="{la}"/>'
                f'<g transform="translate(0 {la})"><g class="j" style="animation-name:{b};transform:rotate({-GUARD[b]}deg)">'
                f'<line y2="{lb}"/></g></g></g>')
    arm = lambda s: f'<g transform="translate(0 {-SHOULDER})">{limb([(f"ua{s}", UPPER), (f"fa{s}", FORE)])}</g>'
    leg = lambda s: limb([(f"th{s}", THIGH), (f"sh{s}", SHIN)])
    band = ('<path class="band" d="M-5 -1.2L5 -2.6"/>'
            '<g class="tails" transform="translate(-4.6 -1.4)"><path class="band" d="M0 0q-5 -1 -10 1.5"/>'
            '<path class="band" d="M0 .6q-4 2 -8 5"/></g>')
    return (f'<g class="back">{leg("B")}</g>'
            f'<g class="j" style="animation-name:torso;transform:rotate({GUARD["torso"]}deg)">'
            f'<g class="back">{arm("B")}</g><line y2="{-TORSO}"/>'
            f'<g transform="translate(0 {-NECK})"><circle class="head" r="5.2"/>{band}</g>{arm("F")}</g>{leg("F")}')


def svg(theme, a):
    t = THEMES[theme]
    gx, right, D = a["gx"], a["gx"] + a["grid_w"], f'{a["D"]:.2f}s'
    bar_w = 380
    months = "".join(f'<text x="{gx + col * PITCH:.1f}" y="{FLOOR + 15}" class="mon">{m}</text>' for col, m in a["months"])
    cx, cy = W / 2, GY + 3 * PITCH + 8
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Contribution fight: {a["total"]} contributions in the last 12 months, one hit per active week">
<style>
  .lab {{ font: 700 12px {MONO}; fill: {t["text"]}; letter-spacing: 2px; }}
  .note {{ font: 400 10px {MONO}; fill: {t["soft"]}; letter-spacing: 1px; }}
  .vs {{ font: 800 13px {MONO}; fill: {t["soft"]}; text-anchor: middle; letter-spacing: 2px; }}
  .mon {{ font: 400 10px {MONO}; fill: {t["soft"]}; }}
  .cap {{ font: 400 11px {MONO}; fill: {t["soft"]}; letter-spacing: .5px; }}
  .frame {{ fill: none; stroke: {t["muted"]}; stroke-width: 1.5; }}
  .track {{ fill: {t["muted"]}; }}
  .p1 {{ fill: {t["mars"]}; }}
  .p2, .gh {{ transform-box: fill-box; transform-origin: 100% 50%; animation: {D} linear infinite; }}
  .p2 {{ fill: {t["gold"]}; animation-name: hp; }} .gh {{ fill: {t["ghost"]}; animation-name: ghost; }}
  .dust {{ fill: {t["dust"]}; }}
  .bl {{ transform-box: fill-box; transform-origin: center; animation: {D} linear infinite; }}
  .q0 {{ fill: {t["star"][0]}; }} .q1 {{ fill: {t["star"][1]}; }} .q2 {{ fill: {t["star"][2]}; }} .q3 {{ fill: {t["star"][3]}; }}
  .stage {{ animation: {D} linear infinite shake; }}
  .fighter {{ animation: {D} linear infinite root; }}
  .shadow {{ fill: {t["text"]}; opacity: .18; animation: {D} linear infinite shadow; }}
  .speed {{ opacity: 0; animation: {D} linear infinite dash; }}
  .speed line {{ stroke: {t["soft"]}; stroke-width: 1.6; stroke-linecap: round; }}
  .flash {{ fill: {t["gold"]}; opacity: 0; animation: {D} linear infinite flash; }}
  .fighter line {{ stroke: {t["text"]}; stroke-width: 3.2; stroke-linecap: round; }}
  .head {{ fill: {t["text"]}; }}
  .back {{ opacity: .55; }}
  .j {{ animation: {D} linear infinite; }}
  .band {{ fill: none; stroke: {t["mars"]}; stroke-width: 2.2; stroke-linecap: round; }}
  .tails {{ animation: flutter .22s ease-in-out infinite alternate; }}
  .spark {{ opacity: 0; animation: {D} ease-out infinite; }}
  .spark line {{ stroke: {t["gold"]}; stroke-width: 2; stroke-linecap: round; }}
  .combo {{ font: italic 800 15px {MONO}; fill: {t["mars"]}; letter-spacing: 1px; opacity: 0; transform-box: fill-box; transform-origin: 0 50%; animation: {D} linear infinite; }}
  .ban {{ opacity: 0; transform-box: fill-box; transform-origin: center; animation: {D} linear infinite; }}
  .big {{ font: italic 800 34px {MONO}; text-anchor: middle; letter-spacing: 4px; }}
  .r1 {{ fill: {t["text"]}; }} .go {{ fill: {t["mars"]}; }} .ko {{ fill: {t["gold"]}; }}
  .sub {{ font: 400 13px {MONO}; fill: {t["soft"]}; text-anchor: middle; }}
  @keyframes flutter {{ from {{ transform: rotate(-10deg); }} to {{ transform: rotate(14deg); }} }}
  {a["css"]}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>
<rect class="flash" x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14"/>
<rect class="frame" x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14"/>
<text x="{gx:.1f}" y="26" class="lab">DEIMOS</text>
<rect class="track" x="{gx:.1f}" y="34" width="{bar_w}" height="10" rx="3"/>
<rect class="p1" x="{gx:.1f}" y="34" width="{bar_w}" height="10" rx="3"/>
<text x="{gx:.1f}" y="58" class="note">LV {a["lv"]} · STREAK {a["cur"]} · BEST {a["best"]}</text>
<text x="{W / 2}" y="44" class="vs">VS</text>
<text x="{right:.1f}" y="26" class="lab" text-anchor="end">THE YEAR</text>
<rect class="track" x="{right - bar_w:.1f}" y="34" width="{bar_w}" height="10" rx="3"/>
<rect class="gh" x="{right - bar_w:.1f}" y="34" width="{bar_w}" height="10" rx="3"/>
<rect class="p2" x="{right - bar_w:.1f}" y="34" width="{bar_w}" height="10" rx="3"/>
<text x="{right:.1f}" y="58" class="note" text-anchor="end">{a["total"]} HP · {a["active"]} ACTIVE DAYS</text>
{a["combos"]}
<g class="stage">
<g class="dust">{a["dust"]}</g>
{a["blocks"]}
{months}
<g class="shadow" style="transform:translate({a["x0"]:.1f}px,{FLOOR + 1}px)"><ellipse rx="10" ry="2.2"/></g>
<g class="fighter" style="transform:translate({a["x0"]:.1f}px,{FLOOR - HIP + GUARD["dy"]:.1f}px)">
<g class="speed"><line x1="-12" y1="-30" x2="-34" y2="-30"/><line x1="-16" y1="-17" x2="-44" y2="-17"/><line x1="-10" y1="-4" x2="-28" y2="-4"/></g>
{rig()}</g>
{a["sparks"]}
</g>
<text x="{gx:.1f}" y="{H - 14}" class="cap">every block is a day I showed up</text>
<text x="{right:.1f}" y="{H - 14}" class="cap" text-anchor="end">refreshed daily</text>
<g class="ban" style="animation-name:round"><text x="{cx}" y="{cy}" class="big r1">ROUND 1</text></g>
<g class="ban" style="animation-name:go"><text x="{cx}" y="{cy}" class="big go">FIGHT!</text></g>
<g class="ban" style="animation-name:ko"><text x="{cx}" y="{cy}" class="big ko">K.O.</text>
<text x="{cx}" y="{cy + 26}" class="sub">{a["total"]} contributions · {a["active"]} active days · best streak {a["best"]}</text></g>
</svg>
"""


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    out.mkdir(parents=True, exist_ok=True)
    fight = build(*fetch())
    for theme in THEMES:
        (out / f"fight-{theme}.svg").write_text(svg(theme, fight), encoding="utf-8")
