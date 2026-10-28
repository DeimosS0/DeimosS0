"""Builds the arcade panel: the last 12 months of contributions as a field of stars. Deimos glides across the year,
drifting toward where the stars are, and pulls in every star it passes while score, level and XP roll up. After the
last star it shows YEAR CLEAR, the sky refills and the loop starts over. All motion is eased; nothing steps.

XP is the all-time contribution count; level n starts at 5·(n-1)² XP. The replay starts from the XP held a year ago.

Run: GH_TOKEN=<token> python assets/make_arcade.py [out_dir]  -> writes arcade-light.svg and arcade-dark.svg
(default out_dir: next to this file). The daily workflow runs it and pushes the result to the `output` branch.
"""
import json
import math
import os
import sys
import urllib.request
from pathlib import Path

import moon

USER = "DeimosS0"
W, H = 1000, 258
CELL, PITCH, GY = 13, 17, 84  # calendar cell size, cell pitch, grid top
FLY, RAMP = 10.0, 1.2  # seconds to cross the year, seconds to get up to speed
LEAD, PULL = 34, .42  # a star lets go when the moon is LEAD px before its column and takes PULL s (+ distance) to arrive
CLEAR, RESET = 2.6, 1.4  # seconds of the YEAR CLEAR banner, seconds to refill the sky
LH, CW = 26, 13  # odometer line height and digit width
SUCK = "cubic-bezier(.55,0,.9,.45)"  # stars speed up as they fall into the moon
SETTLE = "cubic-bezier(.2,.8,.2,1)"  # rolls, fills and the moon flying back in
POP = "cubic-bezier(.34,1.56,.64,1)"  # stars coming back, with a little overshoot

THEMES = {
    "light": dict(text="#1f2328", soft="#59636e", muted="#d1d9e0", dust="#d0d7de", violet="#6e56cf", gold="#c27c0e",
                  star=["#f3d58f", "#e8b345", "#d4920f", "#a96b00"]),
    "dark": dict(text="#e6edf3", soft="#9198a1", muted="#3d444d", dust="#30363d", violet="#a78bfa", gold="#fbbf24",
                 star=["#5a4719", "#9c7419", "#dba51e", "#fcd34d"]),
}

MONO = "ui-monospace, 'SF Mono', 'Cascadia Code', Consolas, monospace"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
QUARTILES = ["FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]

CALENDAR = """{user(login:"%s"){contributionsCollection{contributionYears
  contributionCalendar{weeks{contributionDays{date weekday contributionCount contributionLevel}}}}}}"""
YEAR = """y%d:contributionsCollection(from:"%d-01-01T00:00:00Z",to:"%d-12-31T23:59:59Z"){
  contributionCalendar{totalContributions}}"""


def gql(query):
    token = os.environ.get("GH_TOKEN") or os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request("https://api.github.com/graphql", json.dumps({"query": query}).encode(),
                                 {"Authorization": f"bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)["data"]["user"]


def fetch():
    """Calendar weeks of the last 12 months and the all-time contribution count."""
    cc = gql(CALENDAR % USER)["contributionsCollection"]
    years = gql('{user(login:"%s"){%s}}' % (USER, " ".join(YEAR % (y, y, y) for y in cc["contributionYears"])))
    return cc["contributionCalendar"]["weeks"], sum(v["contributionCalendar"]["totalContributions"] for v in years.values())


def level(xp):
    return math.isqrt(xp // 5) + 1


def progress(xp):
    lv = level(xp)
    return (xp - 5 * (lv - 1) ** 2) / (5 * lv ** 2 - 5 * (lv - 1) ** 2)


def streaks(counts):
    best = run = 0
    for n in counts:
        run = run + 1 if n else 0
        best = max(best, run)
    i, cur = len(counts) - 1, 0
    if counts and not counts[i]:  # today may still be empty
        i -= 1
    while i >= 0 and counts[i]:
        cur, i = cur + 1, i - 1
    return cur, best


def glide(stars, cols, mid):
    """Height of the moon over each week: it leans toward where that part of the year has stars, smoothed hard."""
    want = []
    for col in range(cols):
        ys = [s["c"][1] for s in stars if s["col"] == col]
        want.append(sum(ys) / len(ys) if ys else mid)
    out = []
    for c in range(cols):
        w = [math.exp(-((k - c) / 3) ** 2 / 2) for k in range(cols)]
        out.append(mid + .75 * (sum(a * y for a, y in zip(w, want)) / sum(w) - mid))
    return out


def build(weeks, xp_now):
    days = [d for w in weeks for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    total, active = sum(counts), sum(1 for n in counts if n)
    cur_streak, best_streak = streaks(counts)

    grid_w = len(weeks) * PITCH - (PITCH - CELL)
    gx = (W - grid_w) / 2
    mid = GY + 3 * PITCH + CELL / 2
    rest, entry, exit_ = (gx - 24, mid), (-30, mid), (W + 30, mid)

    dust, stars, months = [], [], []
    for col, week in enumerate(weeks):
        for d in week["contributionDays"]:
            x, y = gx + col * PITCH, GY + d["weekday"] * PITCH
            if d["contributionCount"]:
                stars.append(dict(x=x, y=y, col=col, c=(x + CELL / 2, y + CELL / 2), n=d["contributionCount"],
                                  q=QUARTILES.index(d["contributionLevel"])))
            else:
                dust.append(f'<circle cx="{x + CELL / 2:.1f}" cy="{y + CELL / 2:.1f}" r="1.6"/>')
        first = week["contributionDays"][0]["date"]
        if first[8:10] <= "07" and (not months or col - months[-1][0] > 2):
            months.append((col, MONTHS[int(first[5:7]) - 1]))

    # The moon's flight: speeds up over RAMP seconds, then crosses at a constant pace; height follows glide().
    heights = glide(stars, len(weeks), mid)
    speed = (exit_[0] - rest[0]) / (FLY - RAMP / 2)

    def x_at(t):
        return rest[0] + speed * (t * t / (2 * RAMP) if t < RAMP else t - RAMP / 2)

    def t_at(x):
        d = max(0.0, x - rest[0])
        return math.sqrt(2 * RAMP * d / speed) if d < speed * RAMP / 2 else d / speed + RAMP / 2

    first_c, last_c = gx + CELL / 2, gx + grid_w - CELL / 2

    def y_at(x):
        k = (x - first_c) / PITCH  # week under the moon
        if 0 <= k <= len(weeks) - 1:
            i = min(int(k), len(weeks) - 2)
            return heights[i] + (heights[i + 1] - heights[i]) * (k - i)
        # off either end of the grid, ease back to the middle
        edge, f = (heights[0], (x - rest[0]) / (first_c - rest[0])) if k < 0 else \
                  (heights[-1], 1 - (x - last_c) / (exit_[0] - last_c))
        f = max(0.0, min(1.0, f))
        return mid + (edge - mid) * f * f * (3 - 2 * f)

    t_reset = FLY + CLEAR
    D = t_reset + RESET
    fly = [(i / 10, x_at(i / 10), y_at(x_at(i / 10))) for i in range(int(FLY * 10) + 1)]
    fly += [(t_reset, *exit_), (t_reset + .01, *entry), (D, *rest)]

    def kf(name, stops):
        return f"@keyframes {name} {{ " + " ".join(f"{100 * t / D:.3f}% {{ {css} }}" for t, css in stops) + " }"

    css = [kf("fly", [(t, f"transform:translate({x:.1f}px,{y:.1f}px)" + (f";animation-timing-function:{SETTLE}" if t == t_reset + .01 else ""))
                      for t, x, y in fly])]

    # Each star lets go as the moon comes near and falls into where the moon will be when it arrives.
    events, pops, star_svg = [], [], []
    for i, s in enumerate(stars):
        sx, sy = s["c"]
        t0 = max(.05, t_at(sx - LEAD))
        ta = min(FLY, t0 + PULL + .003 * abs(sy - y_at(x_at(t0 + PULL))))
        mx, my = x_at(ta), y_at(x_at(ta))
        back = t_reset + .55 * (sx - gx) / grid_w
        home = "transform:translate(0px,0px) scale(1);opacity:1"
        css.append(kf(f"e{i}", [(0, home), (t0, f"{home};animation-timing-function:{SUCK}"),
                                (ta, f"transform:translate({mx - sx:.1f}px,{my - sy:.1f}px) scale(.3);opacity:.5"),
                                (ta + .05, f"transform:translate({mx - sx:.1f}px,{my - sy:.1f}px) scale(0);opacity:0"),
                                (back, f"transform:translate(0px,0px) scale(0);opacity:0;animation-timing-function:{POP}"),
                                (back + .45, home)]))
        star_svg.append(f'<rect class="st q{s["q"]}" x="{s["x"]:.1f}" y="{s["y"]}" width="{CELL}" height="{CELL}" rx="3" '
                        f'style="animation-name:e{i}"/>')
        if s["q"] >= 2:  # bright days get a floating +N over the moon
            css.append(kf(f"p{i}", [(ta, f"opacity:0;transform:translateY(0px);animation-timing-function:{SETTLE}"),
                                    (ta + .05, "opacity:1"), (ta + .9, "opacity:0;transform:translateY(-16px)")]))
            pops.append(f'<text class="pop" x="{mx:.1f}" y="{my - 18:.1f}" style="animation-name:p{i}">+{s["n"]}</text>')
        events.append((ta, s["n"]))

    # Score, level and XP change when stars land; landings closer than 30 ms count as one.
    merged = []
    for t, n in sorted(events):
        if merged and t - merged[-1][0] < .03:
            merged[-1][1] += n
        else:
            merged.append([t, n])
    xp0 = xp = max(0, xp_now - total)  # year totals are UTC, the calendar is local time
    score, lv_line, score_line, ups = 0, [(0, level(xp))], [(0, 0)], []
    bar = [(0, f"transform:scaleX({progress(xp):.3f})")]
    for i, (t, n) in enumerate(merged):
        gap = (merged[i + 1][0] if i + 1 < len(merged) else t_reset) - t
        fill = min(.35, gap * .85)
        before, xp, score = xp, xp + n, score + n
        score_line.append((t, score))
        if level(xp) > level(before):
            lv_line.append((t, level(xp)))
            ups.append(t)
            bar += [(t, f"transform:scaleX({progress(before):.3f});animation-timing-function:{SETTLE}"),
                    (t + fill / 2, "transform:scaleX(1)"), (t + fill / 2 + .005, "transform:scaleX(0)"),
                    (t + fill, f"transform:scaleX({progress(xp):.3f})")]
        else:
            bar += [(t, f"transform:scaleX({progress(before):.3f});animation-timing-function:{SETTLE}"),
                    (t + fill, f"transform:scaleX({progress(xp):.3f})")]
    bar += [(t_reset + .1, f"transform:scaleX({progress(xp):.3f});animation-timing-function:{SETTLE}"),
            (t_reset + .8, f"transform:scaleX({progress(xp0):.3f})"), (D, f"transform:scaleX({progress(xp0):.3f})")]
    css.append(kf("xp", bar))
    lv_line.append((t_reset + .2, level(xp0)))
    score_line.append((t_reset + .2, 0))
    for i, u in enumerate(ups):
        css.append(kf(f"u{i}", [(u, f"opacity:0;transform:translateY(4px);animation-timing-function:{SETTLE}"),
                                (u + .15, "opacity:1;transform:translateY(0px)"), (u + .8, "opacity:1;transform:translateY(-4px)"),
                                (u + 1.2, "opacity:0;transform:translateY(-8px)")]))
    css.append(kf("ban", [(0, "opacity:0;transform:scale(.85)"),
                          (FLY - .3, f"opacity:0;transform:scale(.85);animation-timing-function:{SETTLE}"),
                          (FLY + .5, "opacity:1;transform:scale(1)"), (t_reset - .3, "opacity:1;transform:scale(1)"),
                          (t_reset + .1, "opacity:0;transform:scale(1.04)")]))

    def counter(key, x, y, width, line, final):
        """Odometer: a clipped 0-9,0-9 strip per digit place that rolls forward to each new digit and settles."""
        out = []
        for p in range(width):
            digit = lambda v: v // 10 ** (width - 1 - p) % 10
            changes = [(t, digit(v)) for k, (t, v) in enumerate(line) if k == 0 or digit(v) != digit(line[k - 1][1])]
            stops = [(0, f"transform:translateY({-changes[0][1] * LH}px)")]
            for k, (t, d) in enumerate(changes[1:], 1):
                old = changes[k - 1][1]
                nxt = changes[k + 1][0] if k + 1 < len(changes) else D
                roll = min(.3, (nxt - t) * .8)
                stops += [(t, f"transform:translateY({-old * LH}px);animation-timing-function:{SETTLE}"),
                          (t + roll, f"transform:translateY({-(d if d > old else d + 10) * LH}px)")]
                if d < old:  # rolled onto the second 0-9 copy; jump back to the first, which looks the same
                    stops.append((t + roll + .005, f"transform:translateY({-d * LH}px)"))
            stops.append((D, f"transform:translateY({-changes[-1][1] * LH}px)"))
            css.append(kf(f"{key}{p}", stops))
            strip = "".join(f'<text x="{CW / 2}" y="{(i + 1) * LH - 6}">{i % 10}</text>' for i in range(20))
            out.append(f'<svg x="{x + p * CW:.1f}" y="{y}" width="{CW}" height="{LH}"><g class="odo" '
                       f'style="animation-name:{key}{p};transform:translateY({-digit(final) * LH}px)">{strip}</g></svg>')
        return "".join(out)

    level_digits = counter("l", gx, 34, 2, lv_line, level(xp))
    score_digits = counter("s", gx + 400, 34, 5, score_line, score)
    return dict(gx=gx, grid_w=grid_w, D=D, rest=rest, css="\n  ".join(css), dust="".join(dust), stars="\n".join(star_svg),
                pops="".join(pops), ups=len(ups), months=months, total=total, active=active, cur=cur_streak,
                best=best_streak, lv=level(xp), xp=progress(xp), level_digits=level_digits, score_digits=score_digits)


def svg(theme, a):
    t = THEMES[theme]
    gx, bar_x, bar_w = a["gx"], a["gx"] + 64, 260
    right = gx + a["grid_w"]
    months = "".join(f'<text x="{gx + col * PITCH:.1f}" y="{GY + 7 * PITCH + 12}" class="mon">{m}</text>' for col, m in a["months"])
    ups = "".join(f'<text x="{bar_x + bar_w}" y="28" class="up" style="animation-name:u{i}">LEVEL UP!</text>' for i in range(a["ups"]))
    trail = "".join(f'<circle class="fly trail" r="{r}" opacity="{o}" style="animation-delay:{d}s;transform:translate({a["rest"][0]:.1f}px,{a["rest"][1]:.1f}px)"/>'
                    for r, o, d in [(6, .3, .09), (4.5, .2, .18), (3, .12, .27)])
    cx, cy = W / 2, GY + 3 * PITCH + 4
    D = f'{a["D"]:.2f}s'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Contribution arcade: level {a["lv"]}, {a["total"]} contributions in the last 12 months">
<defs>{moon.defs(theme)}</defs>
<style>
  .lab {{ font: 600 10px {MONO}; fill: {t["soft"]}; letter-spacing: 2px; }}
  .val {{ font: 700 20px {MONO}; fill: {t["text"]}; }}
  .dim {{ font-weight: 400; fill: {t["soft"]}; font-size: 13px; }}
  .odo {{ font: 700 20px {MONO}; fill: {t["text"]}; text-anchor: middle; animation: {D} linear infinite; }}
  .lvl .odo {{ fill: {t["violet"]}; }}
  .mon {{ font: 400 10px {MONO}; fill: {t["soft"]}; }}
  .cap {{ font: 400 11px {MONO}; fill: {t["soft"]}; letter-spacing: .5px; }}
  .frame {{ fill: none; stroke: {t["muted"]}; stroke-width: 1.5; }}
  .track {{ fill: {t["muted"]}; }}
  .bar {{ fill: {t["violet"]}; transform-box: fill-box; transform-origin: 0 50%; animation: {D} linear infinite xp; }}
  .dust {{ fill: {t["dust"]}; }}
  .st {{ transform-box: fill-box; transform-origin: center; animation: {D} linear infinite; }}
  .q0 {{ fill: {t["star"][0]}; }} .q1 {{ fill: {t["star"][1]}; }} .q2 {{ fill: {t["star"][2]}; }} .q3 {{ fill: {t["star"][3]}; }}
  .pop {{ font: 700 11px {MONO}; fill: {t["gold"]}; text-anchor: middle; opacity: 0; animation: {D} linear infinite; }}
  .up {{ font: 700 11px {MONO}; fill: {t["violet"]}; text-anchor: end; letter-spacing: 1px; opacity: 0; animation: {D} linear infinite; }}
  .ban {{ opacity: 0; transform-box: fill-box; transform-origin: center; animation: {D} linear infinite ban; }}
  .big {{ font: 800 30px {MONO}; fill: {t["gold"]}; text-anchor: middle; letter-spacing: 4px; }}
  .sub {{ font: 400 13px {MONO}; fill: {t["soft"]}; text-anchor: middle; }}
  .fly {{ animation: {D} linear infinite fly; }}
  .trail {{ fill: {t["violet"]}; }}
  .bob {{ animation: bob 1.6s ease-in-out infinite alternate; }}
  @keyframes bob {{ from {{ transform: translateY(-1.5px) rotate(-6deg); }} to {{ transform: translateY(1.5px) rotate(6deg); }} }}
{moon.css(theme)}
  {a["css"]}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} .trail {{ display: none; }} }}
</style>
<rect class="frame" x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14"/>
<text x="{gx:.1f}" y="28" class="lab">LEVEL</text>
<g class="lvl">{a["level_digits"]}</g>
<text x="{bar_x:.1f}" y="28" class="lab">XP</text>
<rect class="track" x="{bar_x:.1f}" y="42" width="{bar_w}" height="10" rx="5"/>
<rect class="bar" x="{bar_x:.1f}" y="42" width="{bar_w}" height="10" rx="5" style="transform:scaleX({a["xp"]:.3f})"/>
{ups}
<text x="{gx + 400:.1f}" y="28" class="lab">SCORE</text>
{a["score_digits"]}
<text x="{gx + 560:.1f}" y="28" class="lab">STREAK</text>
<text x="{gx + 560:.1f}" y="54" class="val">{a["cur"]} <tspan class="dim">best {a["best"]}</tspan></text>
<text x="{right:.1f}" y="28" class="lab" text-anchor="end">ACTIVE DAYS</text>
<text x="{right:.1f}" y="54" class="val" text-anchor="end">{a["active"]}</text>
<g class="dust">{a["dust"]}</g>
{a["stars"]}
{months}
<text x="{gx:.1f}" y="{H - 16}" class="cap">every star is a day I showed up</text>
<text x="{right:.1f}" y="{H - 16}" class="cap" text-anchor="end">refreshed daily</text>
<g class="ban"><text x="{cx}" y="{cy}" class="big">YEAR CLEAR!</text>
<text x="{cx}" y="{cy + 26}" class="sub">{a["total"]} contributions · {a["active"]} active days · best streak {a["best"]}</text></g>
{trail}
<g class="fly" style="transform:translate({a["rest"][0]:.1f}px,{a["rest"][1]:.1f}px)"><g class="bob">{moon.body(1.0, "chomp")}</g></g>
{a["pops"]}
</svg>
"""


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    out.mkdir(parents=True, exist_ok=True)
    arcade = build(*fetch())
    for theme in THEMES:
        (out / f"arcade-{theme}.svg").write_text(svg(theme, arcade), encoding="utf-8")
