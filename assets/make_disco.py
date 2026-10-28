"""Builds the inner-monologue panel, after Disco Elysium's dialogue: someone opens the profile and Deimos's skills speak
up one by one, each in its attribute's colour, with today's numbers from GitHub in them. Then a cursor picks the first
answer and a task lands under the portrait. Plays once and stays; only the portrait keeps breathing.

Run: GH_TOKEN=<token> python assets/make_disco.py [out_dir]  -> writes disco.svg (default out_dir: next to this file).
portrait.jpg next to this file is the GitHub avatar at 360 px, embedded as the portrait and, blurred, as the backdrop.
"""
import base64
import calendar
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
    H = max(y + PAD - 4, task_y + 26 + len(task_lines) * 18 + PAD)
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
