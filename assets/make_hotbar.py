"""Builds the toolbox as a game hotbar: one slot per tool and a selection frame that glides from slot to slot, lifting
the tool it lands on and showing its name.

Logos come from simple-icons (CC0); tools it has no logo for get a small hand-drawn glyph.
Run: python assets/make_hotbar.py  -> writes hotbar-light.svg and hotbar-dark.svg next to this file.
"""
import re
import urllib.request
from pathlib import Path

W, H = 1000, 108
SLOT, GAP, SLOT_Y = 60, 10, 42
STEP, GLIDE = 2.0, .55  # seconds on each slot, seconds to glide to the next
EASE = "cubic-bezier(.65,0,.35,1)"

SIMPLE_ICONS = "https://cdn.jsdelivr.net/npm/simple-icons@16.36.0/icons/{}.svg"
GLYPHS = {  # 24x24, for tools simple-icons has no logo for
    "sql": '<path d="M12 2C7.6 2 4 3.3 4 5s3.6 3 8 3 8-1.3 8-3-3.6-3-8-3zM4 7.5V11c0 1.7 3.6 3 8 3s8-1.3 8-3V7.5c-1.6 1.2-4.7 2-8 2s-6.4-.8-8-2zM4 13.5V19c0 1.7 3.6 3 8 3s8-1.3 8-3v-5.5c-1.6 1.2-4.7 2-8 2s-6.4-.8-8-2z"/>',
    "lightgbm": '<path d="M12 4L6 13M12 4l6 9M6 13l-3 7M6 13l3 7M18 13l-3 7M18 13l3 7" class="edge"/>'
                '<circle cx="12" cy="4" r="2.6"/><circle cx="6" cy="13" r="2.3"/><circle cx="18" cy="13" r="2.3"/>'
                '<circle cx="3" cy="20" r="1.9"/><circle cx="9" cy="20" r="1.9"/><circle cx="15" cy="20" r="1.9"/><circle cx="21" cy="20" r="1.9"/>',
}
TOOLS = [("Python", "python"), ("pandas", "pandas"), ("SQL", "sql"), ("scikit-learn", "scikitlearn"), ("LightGBM", "lightgbm"),
         ("Streamlit", "streamlit"), ("Plotly", "plotly"), ("TypeScript", "typescript"), ("Astro", "astro"),
         ("Unity · C#", "unity"), ("C · C++", "cplusplus")]

THEMES = {
    "light": dict(text="#1f2328", soft="#8c959f", muted="#d1d9e0", slot="#f6f8fa", accent="#dd6a45", lit="#fdeee8",
                  tip="#1f2328", tip_text="#ffffff"),
    "dark": dict(text="#e6edf3", soft="#6e7681", muted="#3d444d", slot="#161b22", accent="#f0805a", lit="#2b1912",
                 tip="#e6edf3", tip_text="#0d1117"),
}
MONO = "ui-monospace, 'SF Mono', 'Cascadia Code', Consolas, monospace"


def icon(slug):
    if slug in GLYPHS:
        return GLYPHS[slug]
    with urllib.request.urlopen(SIMPLE_ICONS.format(slug)) as r:
        d = re.search(r' d="([^"]+)"', r.read().decode()).group(1)
    return f'<path d="{d}"/>'


def svg(theme, glyphs):
    t = THEMES[theme]
    D = len(TOOLS) * STEP
    x0 = (W - len(TOOLS) * SLOT - (len(TOOLS) - 1) * GAP) / 2
    pct = lambda s: f"{100 * s / D:.3f}%"
    # The frame rests on each slot, then glides to the next; from the last slot it glides back to the first.
    frame = []
    for i in range(len(TOOLS)):
        x = i * (SLOT + GAP)
        frame += [f"{pct(i * STEP)} {{ transform: translateX({x}px); }}",
                  f"{pct((i + 1) * STEP - GLIDE)} {{ transform: translateX({x}px); animation-timing-function: {EASE}; }}"]
    held, off = pct(STEP - GLIDE), pct(STEP - GLIDE / 2)
    body = []
    for i, ((name, _), glyph) in enumerate(zip(TOOLS, glyphs)):
        x = x0 + i * (SLOT + GAP)
        delay = f"animation-delay:{i * STEP - D:.2f}s"
        tip_w = len(name) * 7.8 + 18
        body.append(
            f'<rect class="slot" x="{x:.1f}" y="{SLOT_Y}" width="{SLOT}" height="{SLOT}" rx="12"/>'
            f'<rect class="lit" x="{x:.1f}" y="{SLOT_Y}" width="{SLOT}" height="{SLOT}" rx="12" style="{delay}"/>'
            f'<g class="ic" style="{delay}"><g transform="translate({x + 15:.1f} {SLOT_Y + 15}) scale(1.25)">{glyph}</g></g>'
            f'<g class="tip" style="{delay}"><rect x="{x + SLOT / 2 - tip_w / 2:.1f}" y="6" width="{tip_w:.1f}" height="22" rx="6"/>'
            f'<text x="{x + SLOT / 2:.1f}" y="21">{name}</text></g>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Toolbox: {", ".join(n for n, _ in TOOLS)}">
<style>
  .slot {{ fill: {t["slot"]}; stroke: {t["muted"]}; stroke-width: 1.5; }}
  .lit {{ fill: {t["lit"]}; opacity: 0; animation: lit {D:.2f}s infinite; }}
  .ic {{ fill: {t["soft"]}; color: {t["soft"]}; transform-box: fill-box; transform-origin: center; animation: on {D:.2f}s infinite; }}
  .edge {{ fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; }}
  .tip {{ opacity: 0; animation: tip {D:.2f}s infinite; }}
  .tip rect {{ fill: {t["tip"]}; }}
  .tip text {{ font: 600 13px {MONO}; fill: {t["tip_text"]}; text-anchor: middle; }}
  .frame {{ fill: none; stroke: {t["accent"]}; stroke-width: 2.5; animation: frame {D:.2f}s linear infinite; }}
  @keyframes frame {{ {" ".join(frame)} 100% {{ transform: none; }} }}
  @keyframes on {{
    0%, {held} {{ fill: {t["accent"]}; color: {t["accent"]}; transform: translateY(-3px) scale(1.14); animation-timing-function: {EASE}; }}
    {off}, {pct(D - GLIDE / 2)} {{ fill: {t["soft"]}; color: {t["soft"]}; transform: none; animation-timing-function: {EASE}; }}
    100% {{ fill: {t["accent"]}; color: {t["accent"]}; transform: translateY(-3px) scale(1.14); }} }}
  @keyframes lit {{ 0%, {held} {{ opacity: 1; animation-timing-function: {EASE}; }} {off}, {pct(D - GLIDE / 2)} {{ opacity: 0; animation-timing-function: {EASE}; }} 100% {{ opacity: 1; }} }}
  @keyframes tip {{ 0%, {held} {{ opacity: 1; transform: none; animation-timing-function: {EASE}; }} {pct(STEP - GLIDE + .25)}, {pct(D - .3)} {{ opacity: 0; transform: translateY(4px); animation-timing-function: {EASE}; }} 100% {{ opacity: 1; transform: none; }} }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>
{"".join(body)}
<rect class="frame" x="{x0 - 4:.1f}" y="{SLOT_Y - 4}" width="{SLOT + 8}" height="{SLOT + 8}" rx="14"/>
</svg>
"""


if __name__ == "__main__":
    here = Path(__file__).parent
    glyphs = [icon(slug) for _, slug in TOOLS]
    for theme in THEMES:
        (here / f"hotbar-{theme}.svg").write_text(svg(theme, glyphs), encoding="utf-8")
