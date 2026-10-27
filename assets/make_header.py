"""Builds the animated profile header: DEİMOS (the İ's dot drops in last) and scattered points settling into three clusters.

Run: python assets/make_header.py  -> writes header-light.svg and header-dark.svg next to this file.
"""
import math
import random
from pathlib import Path

W, H = 1000, 260
SUBTITLE = "Data Science &amp; Analytics · Sakarya University"
TAGLINE = "chaos in, structure out"

# Title is set letter by letter so the İ's dot can be its own animated circle.
# Widths are rough bold-sans advances in em; each letter is centred in its slot.
TITLE = [("D", .72), ("E", .60), ("I", .29), ("M", .86), ("O", .78), ("S", .62)]
TITLE_SIZE, TITLE_TRACK, TITLE_X, TITLE_Y = 70, .30, 40, 124

# Cluster centres on the right half; labels sit under each centroid.
CLUSTERS = [("data", 640, 92), ("ai", 790, 178), ("play", 905, 84)]
POINTS_PER_CLUSTER = 22
SPREAD = 24
FIELD = (560, 24, 975, 236)  # where the chaotic start positions are drawn from

THEMES = {
    "light": dict(text="#1f2328", soft="#59636e", muted="#d1d9e0", c=["#0f8f7e", "#d4860b", "#6e56cf"]),
    "dark": dict(text="#e6edf3", soft="#9198a1", muted="#3d444d", c=["#2dd4bf", "#fbbf24", "#a78bfa"]),
}

SANS = "'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif"
MONO = "ui-monospace, 'SF Mono', 'Cascadia Code', Consolas, monospace"


def points():
    rng = random.Random(7)
    out = []
    for k, (_, cx, cy) in enumerate(CLUSTERS):
        for _ in range(POINTS_PER_CLUSTER):
            a, r = rng.uniform(0, 2 * math.pi), abs(rng.gauss(0, SPREAD))
            x, y = cx + r * math.cos(a), cy + r * math.sin(a) * 0.8
            sx, sy = rng.uniform(FIELD[0], FIELD[2]), rng.uniform(FIELD[1], FIELD[3])
            out.append(dict(k=k, x=x, y=y, dx=sx - x, dy=sy - y, r=rng.uniform(3.2, 6), d=rng.uniform(0.1, 0.9)))
    return out


def title():
    """Letter <text>s plus the İ dot position."""
    parts, x, dot = [], TITLE_X, None
    for i, (ch, w) in enumerate(TITLE):
        cx = x + w * TITLE_SIZE / 2
        parts.append(f'  <text x="{cx:.1f}" y="{TITLE_Y}" class="t in" style="animation-delay:{i * .07:.2f}s">{ch}</text>')
        if ch == "I":
            dot = (cx, TITLE_Y - .86 * TITLE_SIZE)
        x += (w + TITLE_TRACK) * TITLE_SIZE
    return "\n".join(parts), dot


def svg(theme):
    t = THEMES[theme]
    letters, (dot_x, dot_y) = title()
    dots = "\n".join(
        f'  <circle class="p k{p["k"]}" cx="{p["x"]:.1f}" cy="{p["y"]:.1f}" r="{p["r"]:.1f}" '
        f'style="--dx:{p["dx"]:.0f}px;--dy:{p["dy"]:.0f}px;animation-delay:{p["d"]:.2f}s"/>'
        for p in points()
    )
    marks = "\n".join(
        f'  <g class="mark" style="animation-delay:{2.7 + i * 0.15:.2f}s">'
        f'<circle cx="{cx}" cy="{cy}" r="34" class="ring k{i}"/>'
        f'<text x="{cx}" y="{cy + 54}" class="lbl k{i}">{label}</text></g>'
        for i, (label, cx, cy) in enumerate(CLUSTERS)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="DEİMOS">
<style>
  .k0 {{ --c: {t["c"][0]}; }} .k1 {{ --c: {t["c"][1]}; }} .k2 {{ --c: {t["c"][2]}; }}
  .t {{ font: 800 {TITLE_SIZE}px {SANS}; fill: {t["text"]}; text-anchor: middle; }}
  .moon {{ fill: {t["c"][2]}; animation: drop .9s cubic-bezier(.34,1.7,.5,1) 1.1s both; }}
  .sub {{ font: 400 19px {SANS}; fill: {t["soft"]}; }}
  .tag {{ font: 400 14px {MONO}; fill: {t["soft"]}; letter-spacing: 1.5px; }}
  .lbl {{ font: 500 13px {MONO}; fill: var(--c); text-anchor: middle; letter-spacing: 1px; }}
  .p {{ fill: var(--c); animation: settle 2.2s cubic-bezier(.22,.9,.24,1) both; }}
  .ring {{ fill: none; stroke: var(--c); stroke-width: 1.5; stroke-dasharray: 3 5; opacity: .75; }}
  .mark {{ animation: pop .5s ease-out both; transform-box: fill-box; transform-origin: center; }}
  .in {{ animation: rise .9s cubic-bezier(.2,.8,.2,1) both; }}
  @keyframes settle {{
    0% {{ transform: translate(var(--dx), var(--dy)); fill: {t["muted"]}; opacity: 0; }}
    15% {{ opacity: 1; }}
    55% {{ fill: {t["muted"]}; }}
    100% {{ transform: translate(0, 0); }}
  }}
  @keyframes drop {{ from {{ opacity: 0; transform: translateY(-70px); }} 30% {{ opacity: 1; }} to {{ transform: none; }} }}
  @keyframes pop {{ from {{ opacity: 0; transform: scale(.6); }} to {{ opacity: 1; transform: scale(1); }} }}
  @keyframes rise {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: none; }} }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>
{letters}
  <circle class="moon" cx="{dot_x:.1f}" cy="{dot_y:.1f}" r="{.075 * TITLE_SIZE:.1f}"/>
  <text x="42" y="170" class="sub in" style="animation-delay:.45s">{SUBTITLE}</text>
  <text x="42" y="204" class="tag in" style="animation-delay:.6s">{TAGLINE}</text>
{dots}
{marks}
</svg>
"""


if __name__ == "__main__":
    here = Path(__file__).parent
    for theme in THEMES:
        (here / f"header-{theme}.svg").write_text(svg(theme), encoding="utf-8")
