"""Builds the inner-monologue panel, after Disco Elysium's dialogue: someone opens the profile and Deimos's skills speak
up one by one, each in its attribute's colour, with today's numbers from GitHub in them. Then a cursor picks the first
answer and a task lands under the portrait. Plays once and stays; only the portrait keeps breathing.

Run: GH_TOKEN=<token> python assets/make_disco.py [out_dir]  -> writes disco.svg (default out_dir: next to this file).
portrait.jpg next to this file is the GitHub avatar at 360 px, embedded as the portrait and, blurred, as the backdrop.
"""
import base64
import calendar
import math
import sys
import textwrap
from collections import Counter
from pathlib import Path

from contrib import fetch, streaks

W = 1000
PAD, PORTRAIT = 24, 220
TEXT_X, TEXT_W = 280, 690
LINE, GAP, CHARS = 22, 12, 92  # line height, space between entries, characters per line
SERIF = "Georgia, 'Times New Roman', serif"
COLORS = dict(intellect="#5cc8e2", psyche="#9a7cf0", physique="#e0525f", motorics="#e6b93d")

# (skill, attribute, check or "", line). An empty skill is the narrator.
SCRIPT = [
    ("", "", "", "Someone is reading your profile."),
    ("PERCEPTION", "motorics", "Easy: Success", "A visitor. Eyes on the commit graph. Act natural."),
    ("ENCYCLOPEDIA", "intellect", "", "Deimos: the smaller of Mars' two moons, a dozen kilometres of rock named for dread. "
                                       "Also you: a data science student at Sakarya University."),
    ("LOGIC", "intellect", "Medium: Success", "{total} contributions in the last year, {active} active days. Not a drip, a flood: "
                                               "{month} alone took {month_n}."),
    ("INLAND EMPIRE", "psyche", "", "The games are listening to the data. Or the data is learning to play. "
                                    "Hard to say who started it."),
    ("ELECTROCHEMISTRY", "physique", "", "One more commit, then sleep. It will not be one."),
    ("VOLITION", "psyche", "", "{streak} Get up. Push something."),
]
OPTIONS = ["Show them the repositories.", "[Return to the data.]"]
TASK = "Look through the pinned repositories."


def facts(weeks):
    days = [d for w in weeks for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    cur, best = streaks(counts)
    by_month = Counter()
    for d in days:
        by_month[d["date"][:7]] += d["contributionCount"]
    month, month_n = by_month.most_common(1)[0]
    streak = (f"Streak: {cur} day{'s' if cur != 1 else ''}, best {best}." if cur else f"The streak is broken. Best was {best}.")
    return dict(total=sum(counts), active=sum(1 for n in counts if n), month=calendar.month_name[int(month[5:])], month_n=month_n,
                streak=streak)


SW, SH = 300, 164  # the swing scene in the bottom-right corner


def swings():
    """A snowy slope with a rusty swing set, after the game's swing scene: two friends side by side on low swings. The
    one in the green jacket swings gently, pumping his legs; the one in the orange bomber barely moves, holding the
    chains, and watches him. Snow falls and the edges melt into the panel."""
    def frame(apex, feet, width, color):
        legs = "".join(f'<line x1="{apex[0]}" y1="{apex[1]}" x2="{x}" y2="{y}"/>' for x, y in feet)
        return f'<g stroke="{color}" stroke-width="{width}" stroke-linecap="round">{legs}</g>'

    left, right, ground = (86, 30), (234, 27), 150  # apexes of the two A-frames and where the swings stand

    def on_bar(x):
        return x, left[1] + (x - left[0]) * (right[1] - left[1]) / (right[0] - left[0])

    seat = ('<path d="M-10 -1.2Q0 2.4 10 -1.2L10 1.4Q0 5 -10 1.4Z" fill="#3b2a22"/>'
            '<path d="M-10 -1.2Q0 2.4 10 -1.2" stroke="#6a5142" stroke-width=".8" fill="none"/>')
    # Figures are drawn on the seat, facing right; each holds the near chain, which runs up through x = 0.
    harry_legs = ('<line x1="-3" y1="-2.5" x2="9" y2="-3.4" stroke="#3a3f31" stroke-width="5.4" stroke-linecap="round"/>'
                  '<g transform="translate(9 -3.4)"><g class="pump">'
                  '<path d="M0 0L.6 11.5" stroke="#3a3f31" stroke-width="4.6" stroke-linecap="round"/>'
                  '<path d="M-1.8 10.2h6.4q2.6 0 2.6 2.4v1.4h-9z" fill="#d1a537"/><path d="M-1.8 13.4h9" stroke="#8f6e1f" stroke-width=".9"/></g></g>')
    harry_body = ('<g class="lean">'
                  '<path d="M-6.4 -2L5.4 -2L3.6 -20.6Q-1 -23.6 -6.6 -20.4Z" fill="#5f6b33"/>'
                  '<path d="M-6.4 -2L-3.2 -2L-3.6 -20.6L-6.6 -20.4Z" fill="#454e22"/>'
                  '<path d="M1.4 -20.8L3.2 -14.4L-.2 -18Z" fill="#e8e1d2"/><path d="M1.6 -17.6L1.2 -10" stroke="#b7462c" stroke-width="1.6" stroke-linecap="round"/>'
                  '<circle cx="-1.2" cy="-26.6" r="4.6" fill="#d8a688"/>'
                  '<path d="M-6.4 -25.4C-7.8 -28.4 -6.6 -32.2 -3.8 -32.4C-2.8 -34.2 .6 -34 1.8 -32.4C3.8 -32.6 4.8 -30.6 3.6 -29.2'
                  'C2.6 -30 1.2 -29.8 .4 -30.3C-.6 -28.8 -2.4 -29 -3 -28C-3.8 -26.8 -4.6 -25.4 -6.4 -25.4Z" fill="#4b2e1e"/>'
                  '<path d="M-4.8 -27.2L-4.6 -23.4" stroke="#4b2e1e" stroke-width="1.6" stroke-linecap="round"/>'
                  '<path d="M.6 -24.8q1.7 1 3.3 0" stroke="#3a2416" stroke-width="1.2" fill="none" stroke-linecap="round"/>'
                  '<circle cx="1.9" cy="-27.6" r=".55" fill="#2a1a10"/>'
                  '<path d="M-2.6 -17.4Q-.4 -19.4 .2 -22.6" stroke="#566031" stroke-width="3.4" fill="none" stroke-linecap="round"/>'
                  '<circle cx=".2" cy="-23" r="1.5" fill="#d8a688"/></g>')
    kim_legs = ('<line x1="-3" y1="-2.5" x2="8.6" y2="-3" stroke="#2c2d31" stroke-width="5.4" stroke-linecap="round"/>'
                '<line x1="8.6" y1="-3" x2="9.6" y2="9.4" stroke="#2c2d31" stroke-width="4.6" stroke-linecap="round"/>'
                '<path d="M7.6 8.6h5.2q2.4 0 2.4 2.2v1.2h-7.6z" fill="#1b1a1a"/>')
    kim_body = ('<path d="M-6.4 -2L5.2 -2L4.4 -19.6Q-1 -22.8 -6.4 -19.6Z" fill="#c8622d"/>'
                '<path d="M-6.6 -5L5.4 -5L5.2 -2L-6.4 -2Z" fill="#8e3f1c"/><path d="M-5.6 -20.4Q-1 -23 3.8 -20.4L3.2 -18.8Q-1 -21 -5 -18.8Z" fill="#8e3f1c"/>'
                '<path d="M-6.4 -2L-3.6 -2L-4 -19.6L-6.4 -19.6Z" fill="#a54d22"/>'
                '<g class="look"><circle cx="-.6" cy="-26" r="4.4" fill="#c99a7e"/>'
                '<path d="M-5 -26.4C-5 -31.6 3.8 -32 4.2 -27.6C2.2 -29 -2 -29.2 -5 -26.4Z" fill="#161314"/>'
                '<path d="M-5 -26.4L-4.8 -24" stroke="#161314" stroke-width="1.4" stroke-linecap="round"/>'
                '<circle cx="2.5" cy="-26.1" r="1.1" fill="#e8dfd0" fill-opacity=".3" stroke="#2a2522" stroke-width=".5"/>'
                '<path d="M1.4 -26.3L-1 -26.7" stroke="#2a2522" stroke-width=".5"/></g>'
                '<path d="M-2.4 -16.8Q-.2 -18.6 .2 -21.4" stroke="#b5561f" stroke-width="3.4" fill="none" stroke-linecap="round"/>'
                '<circle cx=".2" cy="-21.8" r="1.5" fill="#c99a7e"/>')

    def swing(x, length, legs, body, scale, cls):
        px, py = on_bar(x)
        far_chain = f'<line x1="1.4" y1="0" x2="1.4" y2="{length}" class="chain far-chain"/>'
        near_chain = (f'<line x1="-.6" y1="0" x2="-.6" y2="{length}" class="chain"/>'
                      f'<line x1="-.9" y1="0" x2="-.9" y2="{length}" class="glint"/>')
        return (f'<g transform="translate({px} {py:.1f})"><g class="{cls}"><circle r="1.8" class="ring"/>{far_chain}'
                f'<g transform="translate(0 {length}) scale({scale})">{legs}{seat}{body}</g>{near_chain}</g></g>')

    # The scene's outline: a wobbly oval kept well inside its box, then feathered, so it melts away before any edge.
    pts = []
    for i in range(64):
        a = 2 * math.pi * i / 64
        k = 1 + .05 * math.sin(3 * a + 1) + .035 * math.sin(5 * a + 2)
        pts.append(f"{SW / 2 + (SW / 2 - 24) * k * math.cos(a):.1f},{SH / 2 + 4 + (SH / 2 - 22) * k * math.sin(a):.1f}")
    blob = "M" + "L".join(pts) + "Z"
    rng = __import__("random").Random(5)
    flakes = "".join(f'<circle class="flake" cx="{rng.uniform(0, SW):.0f}" cy="0" r="{rng.uniform(.6, 1.5):.1f}" '
                     f'opacity="{rng.uniform(.45, .9):.2f}" style="animation-duration:{rng.uniform(7, 12):.1f}s;'
                     f'animation-delay:-{rng.uniform(0, 12):.1f}s"/>' for _ in range(30))
    tufts = "".join(f'<g transform="translate({x} {y})"><g class="tuft" style="animation-delay:-{d}s">'
                    '<path d="M0 0l-3 -10M0 0l1 -13M0 0l4 -9M1 0l6 -7M-1 0l-6 -6"/></g></g>'
                    for x, y, d in [(52, 136, 0), (64, 140, .8), (236, 118, 1.6), (250, 124, .4), (206, 148, 1.1)])
    steps = "".join(f'<ellipse cx="{x}" cy="{y}" rx="2.6" ry="1.2"/>' for x, y in
                    [(222, 158), (214, 153), (206, 149), (197, 145), (189, 142), (180, 139)])
    scene = f"""<defs>
  <linearGradient id="snow" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#d2bdc7"/><stop offset="100%" stop-color="#ab95a6"/></linearGradient>
  <filter id="feather" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="11"/></filter>
  <mask id="melt" maskUnits="userSpaceOnUse" x="0" y="0" width="{SW}" height="{SH}"><path d="{blob}" fill="#fff" filter="url(#feather)"/></mask>
  <filter id="brush" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency=".09" numOctaves="2" seed="2"/>
    <feDisplacementMap in="SourceGraphic" scale="2.4"/></filter>
  <filter id="haze" filterUnits="userSpaceOnUse" x="0" y="0" width="{SW}" height="{SH}">
    <feColorMatrix type="saturate" values=".82"/><feGaussianBlur stdDeviation=".2"/></filter>
  <filter id="strokes" filterUnits="userSpaceOnUse" x="0" y="0" width="{SW}" height="{SH}">
    <feTurbulence type="fractalNoise" baseFrequency=".012 .16" numOctaves="3" seed="8"/>
    <feColorMatrix values="0 0 0 0 .93  0 0 0 0 .89  0 0 0 0 .92  0 0 0 .38 -.14"/></filter>
  <filter id="soft" x="-50%" y="-200%" width="200%" height="500%"><feGaussianBlur stdDeviation="6"/></filter>
  <linearGradient id="fog" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#eee6eb" stop-opacity=".3"/>
    <stop offset="45%" stop-color="#eee6eb" stop-opacity=".05"/><stop offset="100%" stop-color="#eee6eb" stop-opacity=".08"/></linearGradient>
  <radialGradient id="sun" cx="22%" cy="18%" r="60%"><stop offset="0%" stop-color="#fff0dc" stop-opacity=".25"/><stop offset="100%" stop-color="#fff0dc" stop-opacity="0"/></radialGradient>
</defs>
<g mask="url(#melt)">
 <g filter="url(#haze)">
  <g filter="url(#brush)">
    <rect width="{SW}" height="{SH}" fill="url(#snow)"/>
    <path d="M40 42C110 34 200 28 {SW} 22L{SW} 66C244 70 192 62 142 58C100 55 66 52 40 50Z" fill="#56757c"/>
    <path d="M70 44C130 38 210 33 {SW} 30M110 50C170 46 240 44 {SW} 42" stroke="#7c9aa0" stroke-width="1.2" fill="none" opacity=".7"/>
    <path d="M40 50C66 52 100 55 142 58C192 62 244 70 {SW} 66" stroke="#ece3e7" stroke-width="2.4" fill="none" opacity=".75"/>
    <path d="M0 84C40 76 80 92 120 86C160 80 220 94 {SW} 88" stroke="#e9dbe1" stroke-width="10" fill="none" opacity=".4"/>
    <path d="M0 124C60 116 110 132 160 {SH}L0 {SH}Z" fill="#9c8797" opacity=".5"/>
    <ellipse cx="72" cy="146" rx="17" ry="6.5" fill="#5d5150"/><ellipse cx="69" cy="143.5" rx="11" ry="3" fill="#8b7d7a"/>
    <g fill="#a48fa2" opacity=".7">{steps}</g>
  </g>
  {frame(left, [(left[0] - 15, ground), (left[0] + 15, ground)], 3.4, "#3f7f7a")}
  {frame(right, [(right[0] - 15, ground - 2), (right[0] + 15, ground - 2)], 3.4, "#3f7f7a")}
  <line x1="{left[0] - 5}" y1="{left[1]}" x2="{right[0] + 5}" y2="{right[1]}" stroke="#3f7f7a" stroke-width="3.4" stroke-linecap="round"/>
  <line x1="{left[0] - 5}" y1="{left[1] - 1.3}" x2="{right[0] + 5}" y2="{right[1] - 1.3}" stroke="#7fb3ad" stroke-width=".8" opacity=".7"/>
  <ellipse cx="132" cy="{ground}" rx="15" ry="3.2" fill="#7e6b80" opacity=".55"/>
  <ellipse class="shade" cx="182" cy="{ground}" rx="15" ry="3.2" fill="#7e6b80" opacity=".55"/>
  {swing(130, 88, kim_legs, kim_body, 1.4, "kim")}
  {swing(180, 88, harry_legs, harry_body, 1.4, "swing")}
  <g fill="#b5652e"><circle cx="{left[0] - 9}" cy="104" r="1.5"/><circle cx="{left[0] + 6}" cy="66" r="1.1"/><circle cx="{right[0] + 9}" cy="112" r="1.4"/><circle cx="160" cy="28" r="1.2"/></g>
  <g stroke="#b59a5a" stroke-width="1.1" stroke-linecap="round" fill="none">{tufts}</g>
 </g>
  <rect width="{SW}" height="{SH}" fill="url(#fog)"/>
  <rect width="{SW}" height="{SH}" fill="url(#sun)"/>
  <ellipse class="mist" cx="150" cy="140" rx="120" ry="9" fill="#f3ecf0" opacity=".22" filter="url(#soft)"/>
  <ellipse class="mist" cx="110" cy="74" rx="90" ry="6" fill="#f3ecf0" opacity=".18" filter="url(#soft)" style="animation-duration:26s;animation-delay:-9s"/>
  <rect width="{SW}" height="{SH}" filter="url(#strokes)"/>
  {flakes}
</g>"""
    css = f"""  .chain {{ stroke: #5c6567; stroke-width: 1.4; stroke-dasharray: 1.8 .9; }}
  .far-chain {{ stroke: #7b8486; }}
  .glint {{ stroke: #c3cacc; stroke-width: .45; stroke-dasharray: 1.8 .9; opacity: .8; }}
  .ring {{ fill: none; stroke: #5c6567; stroke-width: 1; }}
  .swing {{ animation: swing 3.6s ease-in-out infinite alternate; }}
  .pump {{ animation: pump 3.6s ease-in-out infinite alternate; }}
  .lean {{ transform-origin: 0px -2px; animation: lean 3.6s ease-in-out infinite alternate; }}
  .shade {{ transform-box: fill-box; transform-origin: center; animation: shade 3.6s ease-in-out infinite alternate; }}
  .kim {{ animation: sway 4.4s ease-in-out infinite alternate; }}
  .look {{ transform-origin: -.6px -22px; animation: look 3.6s ease-in-out -.5s infinite alternate; }}
  .tuft {{ animation: tuft 3s ease-in-out infinite alternate; }}
  .flake {{ fill: #f4ecef; animation: fall 9s linear infinite; }}
  .mist {{ animation: mist 20s ease-in-out infinite alternate; }}
  @keyframes swing {{ from {{ transform: rotate(11deg); }} to {{ transform: rotate(-11deg); }} }}
  @keyframes pump {{ from {{ transform: rotate(22deg); }} to {{ transform: rotate(-40deg); }} }}
  @keyframes lean {{ from {{ transform: rotate(3deg); }} to {{ transform: rotate(-7deg); }} }}
  @keyframes shade {{ from {{ transform: translateX(-16px) scaleX(1.1); }} to {{ transform: translateX(16px) scaleX(1.1); }} }}
  @keyframes sway {{ from {{ transform: rotate(1.5deg); }} to {{ transform: rotate(-1.5deg); }} }}
  @keyframes look {{ from {{ transform: rotate(4deg); }} to {{ transform: rotate(-4deg); }} }}
  @keyframes tuft {{ from {{ transform: rotate(-4deg); }} to {{ transform: rotate(4deg); }} }}
  @keyframes mist {{ from {{ transform: translateX(-18px); }} to {{ transform: translateX(18px); }} }}
  @keyframes fall {{ from {{ transform: translate(0px,-8px); }} 50% {{ transform: translate(6px,{SH / 2:.0f}px); }} to {{ transform: translate(0px,{SH + 8}px); }} }}"""
    return scene, css


def svg(f):
    entries, css, timeline, y, t = [], [], [], PAD + 26, .8
    for i, (skill, attr, check, line) in enumerate(SCRIPT):
        text = line.format(**f)
        indent = round(len(skill) * 1.35 + len(check) + (7 if check else 3)) if skill else 0  # bold caps run wider
        wrapped = textwrap.wrap(" " * indent + text, CHARS)
        first = wrapped[0].strip()
        rows = [f'<text x="{TEXT_X}" y="{y}">'
                + (f'<tspan class="sk {attr}">{skill}</tspan>' if skill else "")
                + (f'<tspan class="ck"> [{check}]</tspan>' if check else "")
                + (f'<tspan class="tx"> — {first}</tspan>' if skill else f'<tspan class="tx nar">{first}</tspan>') + "</text>"]
        rows += [f'<text x="{TEXT_X}" y="{y + k * LINE}" class="tx{" nar" if not skill else ""}">{w}</text>'
                 for k, w in enumerate(wrapped[1:], 1)]
        entries.append(f'<g class="e" style="animation-name:e{i}">{"".join(rows)}</g>')
        timeline.append(t)
        y += len(wrapped) * LINE + GAP
        t += 1 + .026 * len(text)  # time to read it before the next voice

    # The options, then someone picks the first one and a task lands under the portrait.
    t_opt, opt_y = t, y
    t_hover, t_click = t_opt + 1.6, t_opt + 2.3
    t_task, end = t_click + .5, t_click + 2
    timeline.append(t_opt)
    options = "".join(f'<text x="{TEXT_X}" y="{opt_y + k * (LINE + 4)}" class="opt" style="animation-name:o{k}">{k + 1}. {o}</text>'
                      for k, o in enumerate(OPTIONS))
    entries.append(f'<g class="e" style="animation-name:e{len(SCRIPT)}">{options}</g>')
    y += len(OPTIONS) * (LINE + 4)

    def kf(name, stops):
        css.append(f"@keyframes {name} {{ " + " ".join(f"{100 * s / end:.2f}% {{ {v} }}" for s, v in stops) + " }")

    shown, hidden = "opacity:1;transform:translateY(0px)", "opacity:0;transform:translateY(8px)"
    for k, start in enumerate(timeline):
        stops = [(0, hidden), (start, hidden), (start + .7, shown)]
        if k + 1 < len(timeline):  # older voices fade back as new ones speak
            nxt = timeline[k + 1]
            stops += [(nxt, shown), (nxt + .7, "opacity:.6;transform:translateY(0px)")]
        kf(f"e{k}", stops + [(end, stops[-1][1])])
    kf("o0", [(t_hover, "fill:#e36b33"), (t_hover + .25, "fill:#f3e9dc"), (end, "fill:#f3e9dc")])
    kf("o1", [(t_click, "opacity:1"), (t_click + .4, "opacity:.35"), (end, "opacity:.35")])
    ax, ay, sx, sy = TEXT_X + 150, opt_y - 6, 905, y + 10
    kf("cursor", [(t_opt + .6, f"opacity:0;transform:translate({sx}px,{sy}px) scale(1)"),
                  (t_opt + .8, f"opacity:1;transform:translate({sx}px,{sy}px) scale(1);animation-timing-function:cubic-bezier(.45,0,.2,1)"),
                  (t_hover, f"opacity:1;transform:translate({ax}px,{ay}px) scale(1)"),
                  (t_click, f"opacity:1;transform:translate({ax}px,{ay}px) scale(1)"),
                  (t_click + .08, f"opacity:1;transform:translate({ax}px,{ay}px) scale(.8)"),
                  (t_click + .2, f"opacity:1;transform:translate({ax}px,{ay}px) scale(1)"),
                  (t_click + 1.1, f"opacity:0;transform:translate({ax + 6}px,{ay + 10}px) scale(1)")])
    kf("task", [(0, "opacity:0;transform:translateX(-12px)"), (t_task, "opacity:0;transform:translateX(-12px)"), (t_task + .6, "opacity:1;transform:translateX(0px)")])
    kf("glow", [(0, "opacity:0"), (t_task, "opacity:0"), (t_task + .3, "opacity:1"), (t_task + 1.4, "opacity:.35"), (end, "opacity:.35")])

    task_y = PAD + PORTRAIT + 82
    task_lines = textwrap.wrap(TASK, 28)
    vx, vy = W - SW - 16, opt_y - 50  # the swing scene sits beside the options
    H = max(y + PAD - 4, task_y + 26 + len(task_lines) * 18 + PAD, vy + SH + 10)
    scene, scene_css = swings()
    photo = base64.b64encode((Path(__file__).parent / "portrait.jpg").read_bytes()).decode()
    alt = " ".join((f"{s}: " if s else "") + l.format(**f) for s, _, _, l in SCRIPT)
    task_text = "".join(f'<text x="{PAD}" y="{task_y + 22 + k * 18}" class="tb">{w}</text>' for k, w in enumerate(task_lines))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{alt}">
<defs>
  <image id="pic" width="{PORTRAIT}" height="{PORTRAIT}" href="data:image/jpeg;base64,{photo}"/>
  <filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" seed="4"/>
    <feColorMatrix values="0 0 0 0 .9  0 0 0 0 .85  0 0 0 0 .75  0 0 0 .09 0"/></filter>
  <filter id="smear" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="16"/></filter>
  <linearGradient id="dusk" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#0f0c0a" stop-opacity=".25"/>
    <stop offset="30%" stop-color="#0f0c0a" stop-opacity=".72"/><stop offset="55%" stop-color="#0f0c0a" stop-opacity=".93"/>
    <stop offset="100%" stop-color="#0d0b0a" stop-opacity=".97"/></linearGradient>
  <radialGradient id="vignette" cx="50%" cy="42%" r="72%"><stop offset="62%" stop-color="#0d0b0a" stop-opacity="0"/><stop offset="100%" stop-color="#0d0b0a" stop-opacity=".7"/></radialGradient>
  <clipPath id="panel"><rect width="{W}" height="{H}" rx="14"/></clipPath>
  <clipPath id="frame"><rect x="{PAD}" y="{PAD}" width="{PORTRAIT}" height="{PORTRAIT}" rx="4"/></clipPath>
</defs>
<style>
  text {{ font: 15px {SERIF}; }}
  .tx {{ fill: #d8cfc2; }} .nar {{ fill: #a59c90; font-style: italic; }}
  .sk {{ font-weight: 700; letter-spacing: .6px; }}
  .intellect {{ fill: {COLORS["intellect"]}; }} .psyche {{ fill: {COLORS["psyche"]}; }}
  .physique {{ fill: {COLORS["physique"]}; }} .motorics {{ fill: {COLORS["motorics"]}; }}
  .ck {{ fill: #8a8178; }}
  .opt {{ fill: #e36b33; animation: {end:.2f}s ease-out 1 both; }}
  .name {{ font: 700 17px {SERIF}; fill: #e9e0d2; letter-spacing: 3px; }}
  .role {{ font: italic 13px {SERIF}; fill: #8a8178; }}
  .e, .task, .glow {{ animation: {end:.2f}s ease-out 1 both; }}
  .task {{ animation-name: task; }} .glow {{ animation-name: glow; }}
  .tk {{ font: 700 11px {SERIF}; fill: #e36b33; letter-spacing: 2.5px; }} .tb {{ font: italic 14px {SERIF}; fill: #e9e0d2; }}
  .box {{ fill: none; stroke: #e36b33; stroke-width: 1.5; }}
  .cursor {{ opacity: 0; animation: cursor {end:.2f}s linear 1 both; }}
  .kb {{ transform-box: fill-box; transform-origin: 50% 40%; animation: kb 18s ease-in-out infinite alternate; }}
  @keyframes kb {{ from {{ transform: scale(1); }} to {{ transform: scale(1.06); }} }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} .cursor {{ display: none; }} }}
  {chr(10).join(css)}
{scene_css}
</style>
<g clip-path="url(#panel)">
  <rect width="{W}" height="{H}" fill="#120e0c"/>
  <use href="#pic" transform="translate(-150 -230) scale(2.6)" filter="url(#smear)" opacity=".85"/>
  <rect width="{W}" height="{H}" fill="url(#dusk)"/>
</g>
<g clip-path="url(#frame)"><g class="kb"><use href="#pic" x="{PAD}" y="{PAD}"/></g>
  <rect x="{PAD}" y="{PAD}" width="{PORTRAIT}" height="{PORTRAIT}" fill="url(#vignette)"/></g>
<rect x="{PAD}" y="{PAD}" width="{PORTRAIT}" height="{PORTRAIT}" rx="4" fill="none" stroke="#3a2f27" stroke-width="2"/>
<text x="{PAD}" y="{PAD + PORTRAIT + 30}" class="name">DEIMOS</text>
<text x="{PAD}" y="{PAD + PORTRAIT + 50}" class="role">data science, Sakarya University</text>
<g class="task"><line class="glow" x1="{PAD}" y1="{task_y - 16}" x2="{PAD + PORTRAIT}" y2="{task_y - 16}" stroke="#e36b33" stroke-width="1.5"/>
  <rect class="box" x="{PAD}" y="{task_y - 9}" width="10" height="10" rx="1.5"/><text x="{PAD + 18}" y="{task_y}" class="tk">TASK GAINED</text>
  {task_text}</g>
<line x1="{TEXT_X - 22}" y1="{PAD}" x2="{TEXT_X - 22}" y2="{H - PAD}" stroke="#3a2f27" stroke-width="1.5" opacity=".7"/>
<g transform="translate({vx} {vy})">{scene}</g>
{chr(10).join(entries)}
<g class="cursor"><path d="M0 0L0 16L4.5 12L7.5 19L10 18L7 11L12.5 11Z" fill="#f3e9dc" stroke="#0d0b0a" stroke-width="1.2" stroke-linejoin="round"/></g>
<g clip-path="url(#panel)"><rect width="{W}" height="{H}" filter="url(#grain)"/></g>
</svg>
"""

if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    out.mkdir(parents=True, exist_ok=True)
    weeks, _ = fetch()
    (out / "disco.svg").write_text(svg(facts(weeks)), encoding="utf-8")
