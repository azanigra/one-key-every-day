# Renders a 15 s, 1080x1920 vertical clip as SVG frames, then PNG via rsvg-convert.
#
#   python3 make.py EPISODE FRAMES_DIR            all 450 frames
#   python3 make.py EPISODE --cover COVER.png     one still for the thumbnail
#
# Each episode is an entry in EPISODES: the question, the two keys, the scene
# that plays when the keys land, the caption and the teaser for tomorrow.
import math, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

W, H, FPS, DUR = 1080, 1920, 30, 15.0
BG, BG2, SURF, EDGE = "#1a1b26", "#13141c", "#24283b", "#414868"
TEXT, TEXT2, MUTED, BRAND, CYAN = "#c0caf5", "#a9b1d6", "#8b93b8", "#9ece6a", "#7dcfff"
FONT = "JetBrainsMono Nerd Font"
COVER_T = 10.0   # moment used for the cover still: scene and caption both visible

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, b): return clamp((t - a) / (b - a))
def ease(x): return 1 - (1 - x) ** 3
def ease_io(x): return 4 * x**3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def back(x, s=1.8): x -= 1; return 1 + (s + 1) * x**3 + s * x**2
def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def text(x, y, s, size, fill, weight=500, anchor="middle", opacity=1, spacing=0):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" opacity="{opacity:.3f}" letter-spacing="{spacing}">{esc(s)}</text>')

def keycap(cx, cy, label, size, press, appear):
    """A keycap whose top sinks into its edge when pressed (press 0..1)."""
    if appear <= 0: return ""
    sc = back(appear)
    w = max(size * 2.0, len(label) * size * .62 + size * 1.3); h = size * 2.1; edge = size * .32
    sink = edge * .75 * press
    lit = press
    top = mix(SURF, "#2f3b2a", lit); ink = mix(TEXT, BRAND, lit); rim = mix(EDGE, BRAND, lit)
    g = [f'<g transform="translate({cx:.1f} {cy:.1f}) scale({sc:.3f})" opacity="{clamp(appear*2):.3f}">']
    if lit > 0:
        r = 14 + 40 * lit
        g.append(f'<rect x="{-w/2-r/2:.1f}" y="{-h/2-r/2+sink:.1f}" width="{w+r:.1f}" height="{h+edge+r:.1f}" rx="{14+r/2:.1f}" fill="{BRAND}" opacity="{.10*lit:.3f}"/>')
    g.append(f'<rect x="{-w/2:.1f}" y="{-h/2:.1f}" width="{w:.1f}" height="{h+edge:.1f}" rx="14" fill="{rim}"/>')
    g.append(f'<rect x="{-w/2+3:.1f}" y="{-h/2+3+sink:.1f}" width="{w-6:.1f}" height="{h-6:.1f}" rx="11" fill="{top}"/>')
    g.append(text(0, size * .36 + sink, label, size, ink, 600))
    g.append("</g>")
    return "".join(g), w

def mix(a, b, t):
    a = [int(a[i:i+2], 16) for i in (1, 3, 5)]; b = [int(b[i:i+2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))

def press_curve(t, down, up):
    return ease(prog(t, down, down + .12)) * (1 - ease(prog(t, up, up + .15)))

# ---------------------------------------------------------------------------
# Scenes: what appears on screen once the keys land (from 3.7 s to 12.2 s).
# Each one draws into s and gets ta, the window's fade/rise amount 0..1.

def window(s, ta, title, th, top=900):
    """Common frame for a window or panel that rises in; returns its top-left corner."""
    tw = 860; tx = (W - tw)/2; ty = top + 80*(1-ta)
    sc = .92 + .08*ta
    s.append(f'<g opacity="{ta:.3f}" transform="translate({W/2} {ty+th/2}) scale({sc:.3f}) translate({-W/2} {-(ty+th/2)})">')
    s.append(f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="18" fill="{BG2}" stroke="{BRAND}" stroke-width="3"/>')
    s.append(f'<rect x="{tx}" y="{ty}" width="{tw}" height="70" rx="18" fill="{SURF}"/><rect x="{tx}" y="{ty+52}" width="{tw}" height="18" fill="{SURF}"/>')
    s.append(text(tx+tw/2, ty+46, title, 28, MUTED, 500))
    return tx, ty, tw

def scene_terminal(s, t, ta):
    tx, ty, tw = window(s, ta, "terminal", 620)
    lines = []
    cmd = "echo Hello, class!"
    typed = int(len(cmd) * prog(t, 5.2, 7.0))
    lines.append([("~ ", CYAN), ("❯ ", BRAND), (cmd[:typed], TEXT)])
    if t > 7.4: lines.append([("Hello, class!", TEXT2)])
    if t > 7.8: lines.append([("~ ", CYAN), ("❯ ", BRAND)])
    y = ty + 150
    for li, parts in enumerate(lines):
        x = tx + 50
        for chunk, col in parts:
            s.append(text(x, y, chunk, 40, col, 500, anchor="start"))
            x += len(chunk) * 40 * .6
        last = li == len(lines) - 1
        if last and (int(t * 2.2) % 2 == 0 or (5.2 < t < 7.0)):
            s.append(f'<rect x="{x+4:.1f}" y="{y-34}" width="22" height="44" fill="{TEXT}" opacity=".85"/>')
        y += 64
    s.append("</g>")

# The root of the Omarchy menu (Omarchy 4.5, default/omarchy/omarchy-menu.jsonc).
MENU_ROOT = [("\U000f003b", "Apps"), ("\U000f09d1", "Learn"), ("\U000f03d8", "Appearance"),
             ("\U000f14de", "Trigger"), ("\ue615", "Setup"), ("\U000f0249", "Install"),
             ("\U000f0b4c", "Remove"), ("\uf021", "Update"), ("\uea74", "About"), ("\uf011", "System")]

def scene_menu(s, t, ta):
    row = 56
    tx, ty, tw = window(s, ta, "Go", 70 + 30 + row * len(MENU_ROOT) + 20, top=800)
    # The highlight starts on the first row, then walks down a few, as with the arrow keys.
    pos = 0.0
    for k, at in enumerate((5.4, 6.3, 7.2, 8.1)):
        pos += ease_io(prog(t, at, at + .35))
    y0 = ty + 100
    s.append(f'<rect x="{tx+24}" y="{y0 + pos*row:.1f}" width="{tw-48}" height="{row-8}" rx="10" fill="{SURF}" stroke="{BRAND}" stroke-width="2"/>')
    for i, (icon, label) in enumerate(MENU_ROOT):
        y = y0 + i * row + row * .62
        # Rows drop in one after another just after the panel appears.
        ra = ease(prog(t, 4.0 + i * .07, 4.4 + i * .07))
        on = clamp(1 - abs(pos - i))
        s.append(text(tx + 64, y, icon, 34, mix(MUTED, BRAND, on), 500, anchor="start", opacity=ra))
        s.append(text(tx + 130, y, label, 36, mix(TEXT2, TEXT, on), 500 + 100 * round(on), anchor="start", opacity=ra))
    s.append("</g>")

EPISODES = {
    1: dict(slug="super-enter", question="How do I open a terminal?", keys=("Super", "Enter"),
            scene=scene_terminal, caption="Opens a terminal", note="Super is the Windows key",
            tomorrow="Super + Space"),
    2: dict(slug="super-space", question="Where are the settings?", keys=("Super", "Space"),
            scene=scene_menu, caption="Opens the Omarchy menu", note="Themes, setup, updates, power",
            tomorrow="Super + W"),
}

# ---------------------------------------------------------------------------

def svg_frame(ep, num, t):
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<defs><radialGradient id="glow" cx="50%" cy="38%" r="60%"><stop offset="0" stop-color="#24283b"/><stop offset="1" stop-color="{BG2}"/></radialGradient>'
         f'<pattern id="dots" width="36" height="36" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.6" fill="{EDGE}" opacity=".35"/></pattern></defs>',
         f'<rect width="{W}" height="{H}" fill="url(#glow)"/><rect width="{W}" height="{H}" fill="url(#dots)"/>']

    # Header: series label and question.
    a = ease(prog(t, .2, 1.0))
    s.append(text(W/2, 250 - 20*(1-a), f"ONE KEY EVERY DAY · #{num}", 34, BRAND, 600, opacity=a, spacing=6))
    q = ep["question"]
    n = int(len(q) * prog(t, .6, 1.8))
    s.append(text(W/2, 360, q[:n], 58, TEXT, 600))

    # Keys: appear, then press the first, then the second, release together.
    lift = ease_io(prog(t, 11.6, 12.4))          # keys move up for the end card
    ky = 640 - 140 * lift
    ksize = 60 - 12 * lift
    pa = press_curve(t, 3.0, 4.9); pb = press_curve(t, 3.45, 4.9)
    k1, w1 = keycap(0, 0, ep["keys"][0], ksize, pa, prog(t, 1.6, 2.2)) or ("", 0)
    k2, w2 = keycap(0, 0, ep["keys"][1], ksize, pb, prog(t, 2.0, 2.6)) or ("", 0)
    gap = ksize * 1.6; total = w1 + gap + w2
    x1 = W/2 - total/2 + w1/2; x2 = W/2 + total/2 - w2/2
    s.append(f'<g transform="translate({x1:.1f} {ky:.1f})">{k1}</g>')
    pl = clamp(prog(t, 1.9, 2.3) * 2)
    s.append(text(W/2, ky + ksize*.4, "+", ksize, MUTED, 400, opacity=pl))
    s.append(f'<g transform="translate({x2:.1f} {ky:.1f})">{k2}</g>')

    # The scene rises when the second key lands.
    ta = ease(prog(t, 3.7, 4.5)) * (1 - ease(prog(t, 11.6, 12.2)))
    if ta > 0:
        ep["scene"](s, t, ta)

    # Caption.
    ca = ease(prog(t, 8.4, 9.2)) * (1 - ease(prog(t, 11.4, 11.9)))
    if ca > 0:
        s.append(text(W/2, 1680 - 20*(1-ca), ep["caption"], 64, TEXT, 600, opacity=ca))
        s.append(text(W/2, 1760 - 20*(1-ca), ep["note"], 34, MUTED, 500, opacity=ca))

    # End card.
    ea = ease(prog(t, 12.2, 12.9))
    if ea > 0:
        s.append(text(W/2, 900 + 30*(1-ea), ep["caption"], 72, TEXT, 600, opacity=ea))
        s.append(f'<rect x="{W/2-60}" y="{980}" width="{120*ea:.1f}" height="5" rx="2" fill="{BRAND}"/>')
        s.append(text(W/2, 1120 + 30*(1-ea), "Tomorrow:", 36, MUTED, 500, opacity=ea))
        s.append(text(W/2, 1190 + 30*(1-ea), ep["tomorrow"], 52, BRAND, 600, opacity=ea))
        s.append(text(W/2, 1560, "Save this to practice", 34, TEXT2, 500, opacity=ease(prog(t, 13.0, 13.6))))

    # Credit on every frame, so it travels with any repost or clip.
    s.append(text(W/2, 1868, "by Pablo Barrera  ·  CC BY 4.0", 28, MUTED, 500, opacity=.8*ease(prog(t, .2, 1.0))))
    fade = prog(t, DUR - .5, DUR)
    if fade > 0: s.append(f'<rect width="{W}" height="{H}" fill="{BG2}" opacity="{fade:.3f}"/>')
    s.append("</svg>")
    return "".join(s)

def render(svg, png):
    tmp = png[:-4] + ".svg"
    open(tmp, "w").write(svg)
    subprocess.run(["rsvg-convert", tmp, "-o", png], check=True)
    os.remove(tmp)

def main():
    args = sys.argv[1:]
    if len(args) not in (2, 3) or not args[0].isdigit() or int(args[0]) not in EPISODES \
            or (len(args) == 3 and args[1] != "--cover"):
        sys.exit("usage: python3 make.py EPISODE FRAMES_DIR\n"
                 "       python3 make.py EPISODE --cover COVER.png\n"
                 f"episodes: {', '.join(map(str, EPISODES))}")
    num = int(args[0]); ep = EPISODES[num]
    if len(args) == 3:
        render(svg_frame(ep, num, COVER_T), args[2])
        return
    out = args[1]
    os.makedirs(out, exist_ok=True)
    def frame(i): render(svg_frame(ep, num, i / FPS), os.path.join(out, f"{i:04d}.png"))
    with ThreadPoolExecutor(os.cpu_count()) as pool:
        list(pool.map(frame, range(int(DUR * FPS))))

if __name__ == "__main__":
    main()
