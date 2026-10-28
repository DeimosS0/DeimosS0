"""Builds the animated profile header: DEİMOS, whose İ dot is a tiny Deimos that lands on the stem like the Pixar lamp
and every few seconds hops and twirls, and on the right Deimos again, orbiting a slowly turning Mars and passing
behind it on the far side.

Run: python assets/make_header.py  -> writes header-light.svg and header-dark.svg next to this file.
"""
import math
import random
from pathlib import Path

import moon

W, H = 1000, 260
SUBTITLE = "Data Science &amp; Analytics · Sakarya University"
TAGLINE = "chaos in, structure out"

# Title is set letter by letter so the İ's dot can be its own animated circle.
# Widths are rough bold-sans advances in em; each letter is centred in its slot.
TITLE = [("D", .72), ("E", .60), ("I", .29), ("M", .86), ("O", .78), ("S", .62)]
TITLE_SIZE, TITLE_TRACK, TITLE_X, TITLE_Y = 70, .30, 40, 124
CAP, DOT_R = .70, 8  # cap height in em; radius of the İ moon, whose bottom is the pivot for squash and stretch
FALL, SPRING = "cubic-bezier(.55,0,1,.55)", "cubic-bezier(0,.55,.45,1)"  # gravity; springing out of a squash

MX, MY, MR = 800, 130, 56  # Mars centre and radius
RX, RY, TILT, LAP = 158, 44, -12, 12  # orbit radii, tilt in degrees, seconds per lap
ORBIT_STEPS = 72
SPIN = 40  # seconds for the surface to drift once across

THEMES = {
    "light": dict(text="#1f2328", soft="#59636e", muted="#d1d9e0", dot="#8c959f", spark="#d4920f",
                  mars=["#f9b08f", "#dd6a45", "#a3402a"], spot="#8f3620", cap="#fff7f2", glow="#f08a64", shade="#5a1d0e"),
    "dark": dict(text="#e6edf3", soft="#9198a1", muted="#3d444d", dot="#6e7681", spark="#fbbf24",
                 mars=["#ffb592", "#e86c44", "#922f1a"], spot="#7d2814", cap="#ffeee6", glow="#ff7a50", shade="#000000"),
}

SANS = "'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif"
MONO = "ui-monospace, 'SF Mono', 'Cascadia Code', Consolas, monospace"


def title():
    """Letter <text>s plus the İ dot position."""
    parts, x, dot = [], TITLE_X, None
    for i, (ch, w) in enumerate(TITLE):
        cx = x + w * TITLE_SIZE / 2
        text = f'<text x="{cx:.1f}" y="{TITLE_Y}" class="t in" style="animation-delay:{i * .07:.2f}s">{ch}</text>'
        if ch == "I":  # the stem gives under the landing moon
            text = f'<g class="stem" style="transform-origin:{cx:.1f}px {TITLE_Y}px">{text}</g>'
        parts.append("  " + text)
        if ch == "I":
            dot = (cx, TITLE_Y - .91 * TITLE_SIZE)
        x += (w + TITLE_TRACK) * TITLE_SIZE
    return "\n".join(parts), dot


def keyframes(name, length, stops):
    """stops: (seconds, transform, easing towards the next stop)."""
    return f"@keyframes {name} {{ " + " ".join(f"{100 * t / length:.1f}% {{ transform: {tr}; animation-timing-function: {ease}; }}"
                                              for t, tr, ease in stops) + " }"


def landing(dot_y):
    """Squash-and-stretch landing on the İ: falls stretched, squashes on the stem and presses it down, bounces once,
    then settles into place as the dot. Returns the moon's and the stem's keyframes."""
    gap = TITLE_Y - CAP * TITLE_SIZE - dot_y - DOT_R  # air between the resting moon and the top of the stem
    press = .14 * CAP * TITLE_SIZE  # how far the stem gives on the first landing
    m = lambda dy, sx, sy: f"translateY({dy:.1f}px) scale({sx},{sy})"
    st = lambda sx, sy: f"scale({sx},{sy})"
    drop = [(0, m(-100, .8, 1.25), FALL), (.40, m(gap, .86, 1.18), SPRING), (.50, m(gap + press, 1.42, .58), SPRING),
            (.62, m(-6, .88, 1.14), SPRING), (.80, m(-26, 1, 1), FALL), (1.00, m(gap, .94, 1.06), SPRING),
            (1.07, m(gap + press * .35, 1.18, .82), SPRING), (1.18, m(-2, .97, 1.04), SPRING),
            (1.30, m(-6, 1, 1), "ease-in-out"), (1.46, m(1, 1.04, .96), "ease-out"), (1.62, m(0, 1, 1), "linear")]
    stem = [(0, st(1, 1), "linear"), (.40, st(1, 1), SPRING), (.50, st(1.05, .86), "ease-in-out"),
            (.62, st(.98, 1.05), "ease-in-out"), (.74, st(1.01, .98), "ease-in-out"), (.86, st(1, 1), "linear"),
            (1.00, st(1, 1), SPRING), (1.07, st(1.02, .95), "ease-in-out"), (1.18, st(1, 1.01), "ease-in-out"),
            (1.30, st(1, 1), "linear"), (1.62, st(1, 1), "linear")]
    return keyframes("land", 1.62, drop), keyframes("give", 1.62, stem)


def on_orbit(phi):
    """Point on the tilted orbit; phi in (0, pi) is the near side, below the planet's centre line."""
    x, y, a = RX * math.cos(phi), RY * math.sin(phi), math.radians(TILT)
    return MX + x * math.cos(a) - y * math.sin(a), MY + x * math.sin(a) + y * math.cos(a)


def arc(start, end):
    (x0, y0), (x1, y1) = on_orbit(start), on_orbit(end)
    return f"M{x0:.1f} {y0:.1f}A{RX} {RY} {TILT} 0 1 {x1:.1f} {y1:.1f}"


def ring():
    """The whole orbit, starting at the right end and running through the near side first."""
    x0, y0 = on_orbit(0)
    return f"{arc(0, math.pi)}A{RX} {RY} {TILT} 0 1 {x0:.1f} {y0:.1f}"


def surface():
    """Dark patches drawn twice side by side so they can drift across the disc and wrap without a seam."""
    rng, spots = random.Random(4), []
    for _ in range(7):
        x, y = rng.uniform(-MR, MR), rng.uniform(-MR * .7, MR * .8)
        spots.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rng.uniform(7, 17):.1f}" ry="{rng.uniform(4, 8):.1f}" '
                     f'transform="rotate({rng.uniform(-25, 25):.0f} {x:.1f} {y:.1f})"/>')
    one = "".join(spots)
    return f'<g class="spots"><g>{one}</g><g transform="translate({-2 * MR} 0)">{one}</g></g>'


def svg(theme):
    t = THEMES[theme]
    letters, (dot_x, dot_y) = title()
    land, give = landing(dot_y)
    rng = random.Random(11)
    dust = "".join(f'<circle cx="{rng.uniform(560, 990):.0f}" cy="{rng.uniform(14, 246):.0f}" r="{rng.uniform(.6, 1.3):.1f}" '
                   f'opacity="{rng.uniform(.3, .75):.2f}"/>' for _ in range(22))
    sparks = "".join(f'<g transform="translate({x} {y})"><path class="spark" d="M0-6L1.4-1.4L6 0L1.4 1.4L0 6L-1.4 1.4L-6 0L-1.4-1.4Z" '
                     f'style="animation-delay:{d}s"/></g>'
                     for x, y, d in [(612, 64, 0), (958, 58, 1.1), (668, 214, 2.3), (944, 206, .6), (720, 34, 1.8)])
    # Even steps in orbit angle, not in path length, so the moon eases through the far ends like a real orbit seen at a slant.
    phis = [2 * math.pi * i / ORBIT_STEPS for i in range(ORBIT_STEPS + 1)]
    seg = [math.hypot(RX * math.sin(a), RY * math.cos(a)) for a in phis]
    length = [0.0]
    for a, b in zip(seg, seg[1:]):
        length.append(length[-1] + (a + b) / 2)
    times = ";".join(f"{i / ORBIT_STEPS:.4f}" for i in range(ORBIT_STEPS + 1))
    motion = (f'<animateMotion dur="{LAP}s" repeatCount="indefinite" calcMode="linear" path="{ring()}" keyTimes="{times}" '
              f'keyPoints="{";".join(f"{v / length[-1]:.4f}" for v in length)}"/>')
    depth = (f'<animateTransform attributeName="transform" type="scale" dur="{LAP}s" repeatCount="indefinite" calcMode="linear" '
             f'keyTimes="{times}" values="{";".join(f"{1 + .14 * math.sin(a):.3f}" for a in phis)}"/>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="DEİMOS">
<defs>
  <radialGradient id="mars" cx="36%" cy="30%" r="78%"><stop offset="0%" stop-color="{t["mars"][0]}"/><stop offset="55%" stop-color="{t["mars"][1]}"/><stop offset="100%" stop-color="{t["mars"][2]}"/></radialGradient>
  <radialGradient id="glow"><stop offset="62%" stop-color="{t["glow"]}" stop-opacity=".3"/><stop offset="100%" stop-color="{t["glow"]}" stop-opacity="0"/></radialGradient>
  <linearGradient id="shade" x1="20%" y1="10%" x2="90%" y2="95%"><stop offset="45%" stop-color="{t["shade"]}" stop-opacity="0"/><stop offset="100%" stop-color="{t["shade"]}" stop-opacity=".45"/></linearGradient>
  <clipPath id="disc"><circle r="{MR}"/></clipPath>
  {moon.defs(theme)}
</defs>
<style>
  .t {{ font: 800 {TITLE_SIZE}px {SANS}; fill: {t["text"]}; text-anchor: middle; }}
  .idot {{ transform-origin: 0px {DOT_R}px; animation: land 1.62s 1s both; }}
  .stem {{ animation: give 1.62s 1s both; }}
  .hop {{ transform-origin: 0px {DOT_R}px; animation: hop 7s 3.4s infinite; }}
  .twirl {{ animation: twirl 7s 3.4s infinite; }}
  .sub {{ font: 400 19px {SANS}; fill: {t["soft"]}; }}
  .tag {{ font: 400 14px {MONO}; fill: {t["soft"]}; letter-spacing: 1.5px; }}
  .in {{ animation: rise .9s cubic-bezier(.2,.8,.2,1) both; }}
  .scene {{ transform-box: fill-box; transform-origin: center; animation: appear 1.4s cubic-bezier(.2,.8,.2,1) .3s both; }}
  .dust {{ fill: {t["dot"]}; }}
  .orbit {{ fill: none; stroke: {t["soft"]}; stroke-width: 1.2; stroke-dasharray: 2 6; stroke-linecap: round; animation: march 4s linear infinite; }}
  .far {{ opacity: .35; }} .near {{ opacity: .6; }}
  .spots {{ fill: {t["spot"]}; opacity: .32; animation: spin {SPIN}s linear infinite; }}
  .cap {{ fill: {t["cap"]}; opacity: .9; }}
  .spark {{ fill: {t["spark"]}; transform-box: fill-box; transform-origin: center; animation: twinkle 2.8s ease-in-out infinite alternate both; }}
{moon.css(theme)}
  {land}
  {give}
  @keyframes hop {{ 0%, 76% {{ transform: none; animation-timing-function: ease-out; }}
    79% {{ transform: translateY(0) scale(1.16,.82); animation-timing-function: {SPRING}; }}
    83% {{ transform: translateY(-5px) scale(.9,1.12); animation-timing-function: ease-out; }}
    89% {{ transform: translateY(-16px) scale(1,1); animation-timing-function: {FALL}; }}
    94% {{ transform: translateY(0) scale(.95,1.05); animation-timing-function: ease-out; }}
    96.5% {{ transform: translateY(0) scale(1.1,.9); animation-timing-function: ease-in-out; }} 100% {{ transform: none; }} }}
  @keyframes twirl {{ 0%, 82% {{ transform: rotate(0deg); animation-timing-function: cubic-bezier(.45,0,.55,1); }} 93%, 100% {{ transform: rotate(360deg); }} }}
  @keyframes rise {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes appear {{ from {{ opacity: 0; transform: scale(.92); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes march {{ to {{ stroke-dashoffset: -32; }} }}
  @keyframes spin {{ to {{ transform: translateX({2 * MR}px); }} }}
  @keyframes twinkle {{ from {{ opacity: .15; transform: scale(.35); }} to {{ opacity: .9; transform: scale(1); }} }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>
{letters}
  <g transform="translate({dot_x:.1f} {dot_y:.1f})"><g class="idot"><g class="hop"><g class="twirl">{moon.body(.62, "smile")}</g></g></g></g>
  <text x="42" y="170" class="sub in" style="animation-delay:.45s">{SUBTITLE}</text>
  <text x="42" y="204" class="tag in" style="animation-delay:.6s">{TAGLINE}</text>
<g class="scene">
  <g class="dust">{dust}</g>
  {sparks}
  <circle cx="{MX}" cy="{MY}" r="{MR * 1.5:.0f}" fill="url(#glow)"/>
  <path class="orbit far" d="{arc(math.pi, 2 * math.pi)}"/>
  <g>{motion}<g>{depth}{moon.body(1.05, "smile", halo=False)}</g></g>
  <circle cx="{MX}" cy="{MY}" r="{MR}" fill="url(#mars)"/>
  <g clip-path="url(#disc)" transform="translate({MX} {MY})">{surface()}
    <ellipse class="cap" cx="-6" cy="{-MR + 5}" rx="17" ry="7"/><circle r="{MR}" fill="url(#shade)"/></g>
  <path class="orbit near" d="{arc(0, math.pi)}"/>
  <g>{motion}<animate attributeName="opacity" dur="{LAP}s" repeatCount="indefinite" values="1;0" keyTimes="0;.5" calcMode="discrete"/>
    <g>{depth}{moon.body(1.05, "smile", halo=False)}</g></g>
</g>
</svg>
"""


if __name__ == "__main__":
    here = Path(__file__).parent
    for theme in THEMES:
        (here / f"header-{theme}.svg").write_text(svg(theme), encoding="utf-8")
