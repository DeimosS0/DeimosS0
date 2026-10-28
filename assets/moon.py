"""The Deimos character shared by the header and the arcade: a lumpy violet moon with a face. Deimos is a potato, not a ball."""
import math

COLORS = {
    "light": dict(moon="#8b74e6", crater="#7259d8", face="#1f2328", blush="#f4a6c4"),
    "dark": dict(moon="#a78bfa", crater="#8c6ef0", face="#0d1117", blush="#f48fb1"),
}


def css(theme):
    c = COLORS[theme]
    return f"""  .m-body {{ fill: {c["moon"]}; }} .m-crater {{ fill: {c["crater"]}; }} .m-blush {{ fill: {c["blush"]}; opacity: .85; }}
  .m-halo {{ fill: url(#m-halo); }}
  .m-eye {{ fill: {c["face"]}; transform-box: fill-box; transform-origin: center; animation: m-blink 3.8s infinite; }}
  .m-glint {{ fill: #fff; }}
  .m-chomp {{ fill: {c["face"]}; transform-box: fill-box; transform-origin: center; animation: m-chomp .3s ease-in-out infinite alternate; }}
  .m-smile {{ fill: none; stroke: {c["face"]}; stroke-width: 1.5; stroke-linecap: round; }}
  @keyframes m-blink {{ 0%, 93%, 100% {{ transform: scaleY(1); }} 96% {{ transform: scaleY(.1); }} }}
  @keyframes m-chomp {{ from {{ transform: scaleY(.3); }} to {{ transform: scaleY(1); }} }}"""


def defs(theme):
    return (f'<radialGradient id="m-halo"><stop offset="40%" stop-color="{COLORS[theme]["moon"]}" stop-opacity=".45"/>'
            f'<stop offset="100%" stop-color="{COLORS[theme]["moon"]}" stop-opacity="0"/></radialGradient>')


def outline(r):
    pts = []
    for i in range(48):
        a = 2 * math.pi * i / 48
        k = 1 + .07 * math.sin(2 * a + .6) + .05 * math.sin(3 * a + 2.1)
        pts.append(f"{r * k * math.cos(a):.1f},{r * k * math.sin(a):.1f}")
    return "M" + "L".join(pts) + "Z"


def body(scale=1.0, mouth="chomp", halo=True):
    """The moon centred on 0,0 at radius 13 times `scale`, optionally with a soft halo behind it."""
    lips = ('<ellipse class="m-chomp" cx="0" cy="4.6" rx="1.9" ry="1.7"/>' if mouth == "chomp"
            else '<path class="m-smile" d="M-2.6 4.2Q0 6.8 2.6 4.2"/>')
    glow = '<circle class="m-halo" r="24"/>' if halo else ""
    return (f'<g transform="scale({scale})">{glow}<path class="m-body" d="{outline(13)}"/>'
            '<circle class="m-crater" cx="5.5" cy="-7.5" r="2.2"/><circle class="m-crater" cx="-7.5" cy="6.5" r="1.5"/>'
            '<circle class="m-crater" cx="-2" cy="-10" r="1.1"/>'
            '<ellipse class="m-eye" cx="-4.6" cy="-1.2" rx="2.1" ry="2.7"/><ellipse class="m-eye" cx="4.6" cy="-1.2" rx="2.1" ry="2.7"/>'
            '<circle class="m-glint" cx="-3.9" cy="-2.3" r=".85"/><circle class="m-glint" cx="5.3" cy="-2.3" r=".85"/>'
            '<ellipse class="m-blush" cx="-8" cy="3" rx="2.3" ry="1.4"/><ellipse class="m-blush" cx="8" cy="3" rx="2.3" ry="1.4"/>'
            f'{lips}</g>')
