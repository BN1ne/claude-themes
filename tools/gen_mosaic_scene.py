"""Generates an animated SVG scene: ASCII-mosaic sharks on light grid paper.

Technique (cell-rasterised silhouettes, ":;t%SX8#@" skin ramp, dash schools)
adapted from stackedlol/ascii-sharks (MIT).

Fluid motion, without script or shader:
- each shark is rasterised once, straight, nose toward +x;
- it is cut into one slice per cell column, and every slice sways up and down
  with a delay that grows toward the tail, so a wave runs along the body;
- the whole shark follows a smooth closed curve (SMIL animateMotion,
  rotate="auto"), so it turns where the curve turns.

    python tools/gen_mosaic_scene.py hooks/mosaic-scene [--svg]
"""
import json, math, random, sys

random.seed(11)
W, H = 1680, 1050
CW, CH = 12, 14          # cell size
COLS, ROWS = W // CW, H // CH
RAMP = ":;t%SX8#@"
EDGE_HEAVY, EDGE_LIGHT = ":;", ".',`"
ACCENTS = ["#7f9c7b", "#b98c91", "#8e86b3", "#a38b67", "#7b93ad"]


def smooth(a, b, x):
    t = max(0, min(1, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def half_width(s):
    if s < 0.13: return 0.09 * math.sin((s / 0.13) * math.pi / 2) ** 0.95
    if s < 0.3: return 0.09 + 0.016 * smooth(0.13, 0.3, s)
    if s < 0.84: return 0.019 + 0.087 * (1 - (s - 0.3) / 0.54) ** 1.25
    k = (s - 0.84) / 0.16
    return 0.019 * (1 - k) + 0.012 * math.sin(k * math.pi)


def tri(p, a, b, c):
    def sg(p1, p2, p3): return (p1[0]-p3[0])*(p2[1]-p3[1])-(p2[0]-p3[0])*(p1[1]-p3[1])
    d1, d2, d3 = sg(p, a, b), sg(p, b, c), sg(p, c, a)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def sample(s, v, L, hammer):
    """s along the body 0..1 (nose->tail), v lateral px. Returns (darkness, kind) or None."""
    if s < -0.03 or s > 1.12: return None
    sv = abs(v) / L / THICK
    if hammer and -0.02 <= s <= 0.07:
        # the hammer: a wide flat bar across the head, eyes at its tips
        reach = 0.16 * (1 - 0.35 * smooth(0.0, 0.07, s))
        if sv <= reach and s <= 0.035 + 0.035 * (1 - sv / reach):
            if sv > reach - 0.022: return (1.0, "eye")
            return (0.55 + 0.3 * (1 - sv / reach), "skin")
    if 0 <= s <= 1:
        w = half_width(s)
        if sv <= w:
            d = sv / max(w, 1e-6)
            dark = (1 - d) ** 0.8 * (0.35 + 0.65 * smooth(0.0, 0.25, s)) * (1 - 0.5 * smooth(0.7, 1.0, s))
            if not hammer and 0.08 < s < 0.13 and 0.45 < d < 0.8: return (1.0, "eye")
            if d < 0.18 and 0.12 < s < 0.75: return (min(1, dark + 0.15), "ridge")
            return (dark, "skin")
    w = half_width(min(max(s, 0), 1))
    q = (s, sv - w)
    if sv > w and tri(q, (0.24, 0), (0.45, 0.17), (0.35, 0)):
        return (0.3 + 0.35 * (1 - (sv - w) / 0.17), "fin")
    if sv > w and tri(q, (0.60, 0), (0.70, 0.05), (0.66, 0)):
        return (0.3, "fin")
    if 0.86 <= s <= 1.1:   # caudal fork
        k = (s - 0.86) / 0.24
        spread = 0.11 * math.sin(k * math.pi * 0.9) ** 0.8
        lobe = abs(sv - spread * 0.75)
        if lobe < 0.025 * (1 - k * 0.6) or sv < 0.012 * (1 - k):
            return (0.4, "fin")
    return None


SUBS = [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)]


def rasterise(L, hammer):
    """Cells of a straight shark, nose at (0,0), body toward -x. Cell coords (c, r)."""
    def to_shark(px, py):
        return -px / L, py
    cmin, cmax = -int(L * 1.13 / CW) - 2, int(L * 0.04 / CW) + 2
    rr = int(L * 0.2 / CH) + 2
    cells = []
    for r in range(-rr, rr + 1):
        for c in range(cmin, cmax + 1):
            center = sample(*to_shark(c * CW + CW / 2, r * CH + CH / 2), L, hammer)
            hits = (1 if center else 0) + sum(
                1 for ox, oy in SUBS if sample(*to_shark(c * CW + ox * CW, r * CH + oy * CH), L, hammer))
            if hits == 0: continue
            key = random.random()
            if center and hits / 5 >= 0.6:
                dark, kind = center
                cells.append((c, r, kind, dark, key))
            else:
                cells.append((c, r, "edge", hits / 5, key))
    return cells


def tinted(level, tint):
    r, g, b = (min(255, max(0, round(level * t))) for t in tint)
    return f"#{r:02x}{g:02x}{b:02x}"


def cells_svg(cells, tint):
    """Block paths grouped by fill colour, glyph runs grouped by colour."""
    blocks, glyphs = {}, {}
    for c, r, kind, val, key in cells:
        x, y = c * CW, r * CH
        if kind == "edge":
            g = EDGE_HEAVY if val >= 0.5 else EDGE_LIGHT
            col = "#a7a9b0" if key > 0.07 else ACCENTS[int(key * 1000) % len(ACCENTS)]
            glyphs.setdefault(col, []).append((x, y, g[int(key * 97) % len(g)]))
            continue
        if kind == "eye":
            level, ch, gc = 40, "o", "#c9ccd3"
        elif kind == "ridge":
            level, ch, gc = 70 - val * 30, "@8%"[int(key * 31) % 3], "#e6e8ec"
        elif kind == "fin":
            level, ch, gc = 215 - val * 90, "%;tS:"[int(key * 53) % 5], "#2a2c33"
        else:
            level = 228 - val * 175
            ch = RAMP[max(0, min(8, int(val * 8.99) + int(key * 3) - 1))]
            gc = "#1d1f25" if level > 120 else "#eceef2"
        level = round(level / 12) * 12
        if key < 0.07:
            gc = ACCENTS[int(key * 1000) % len(ACCENTS)]
        blocks.setdefault(tinted(level, tint), []).append((x, y))
        glyphs.setdefault(gc, []).append((x, y, ch))
    out = []
    for fill, pts in blocks.items():
        d = "".join(f"M{x+1} {y+1}h{CW-1}v{CH-1}h-{CW-1}z" for x, y in pts)
        out.append(f'<path fill="{fill}" d="{d}"/>')
    for col, pts in glyphs.items():
        xs = " ".join(str(x + CW // 2) for x, _, _ in pts)
        ys = " ".join(str(y + CH - 4) for _, y, _ in pts)
        txt = "".join(g for _, _, g in pts).replace("&", "&amp;").replace("<", "&lt;").replace("'", "&#39;")
        out.append(f'<text fill="{col}" x="{xs}" y="{ys}">{txt}</text>')
    return "".join(out)


# ── routes: closed Lissajous-like loops reaching past the window's edges ──
def route(fx, fy, px, py, hx, hy):
    def at(t):
        x = W / 2 + (W / 2 + 20) * (0.82 * math.sin(fx * t + px) + 0.18 * math.sin(hx * t + px * 1.7))
        y = H / 2 + (H / 2 + 10) * (0.82 * math.sin(fy * t + py) + 0.18 * math.cos(hy * t + py * 0.6))
        return x, y
    return at


def path_d(at, n=72):
    """Smooth closed path: Catmull-Rom through n samples, as cubic Béziers."""
    pts = [at(2 * math.pi * i / n) for i in range(n)]
    d = [f"M{pts[0][0]:.0f} {pts[0][1]:.0f}"]
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.0f} {c1[1]:.0f} {c2[0]:.0f} {c2[1]:.0f} {p2[0]:.0f} {p2[1]:.0f}")
    length = sum(math.dist(at(2 * math.pi * i / 2000), at(2 * math.pi * (i + 1) / 2000)) for i in range(2000))
    return "".join(d), length


# L px, tint, hammer, route (fx, fy, phase x, phase y, harmonic x, harmonic y), speed px/s, sway period s
SHARKS = [
    (430, (0.93, 0.97, 1.06), False, (1, 2, 0.3, 1.1, 3, 3), 80, 2.3),
    (360, (0.95, 0.97, 1.03), True,  (2, 1, 2.0, 0.2, 3, 4), 90, 2.0),
    (400, (1.06, 0.97, 0.84), False, (2, 3, 4.1, 2.6, 1, 1), 72, 2.5),
    (300, (0.93, 0.97, 1.06), False, (3, 2, 1.2, 4.0, 1, 4), 95, 1.8),
    (340, (1.04, 0.98, 0.88), True,  (1, 3, 5.0, 3.3, 2, 2), 84, 2.1),
]
THICK = 1.25    # body width multiplier
WAVE = 5.2      # radians of wave along the body

css = [
    "text{font:600 10px ui-monospace,Menlo,Consolas,monospace;text-anchor:middle}",
    ".k{animation-timing-function:ease-in-out;animation-iteration-count:infinite;"
    "animation-direction:alternate;will-change:transform}",
]
amps = set()
live, still = [], []
for i, (L, tint, hammer, rt, speed, period) in enumerate(SHARKS):
    cells = rasterise(L, hammer)
    by_col = {}
    for cell in cells:
        by_col.setdefault(cell[0], []).append(cell)
    slices_live, slices_still = [], []
    t_still = random.uniform(0, 2 * math.pi)
    for c in sorted(by_col):
        s = max(0.0, -(c * CW + CW / 2) / L)
        amp = round(L * 0.05 * (0.12 + 0.88 * min(s, 1.1) ** 1.8))
        body = cells_svg(by_col[c], tint)
        # half a period per direction (alternate); the wave travels nose -> tail
        delay = -(s * WAVE / (2 * math.pi)) * period
        if amp == 0:
            slices_live.append(f"<g>{body}</g>")
        else:
            amps.add(amp)
            slices_live.append(
                f'<g class="k" style="animation-name:s{amp};animation-duration:{period/2:.2f}s;'
                f'animation-delay:{delay:.2f}s">{body}</g>')
        off = amp * math.sin(t_still * 7 - s * WAVE)
        slices_still.append(f'<g transform="translate(0 {off:.1f})">{body}</g>' if abs(off) >= 0.5 else body)
    at = route(*rt)
    d, length = path_d(at)
    dur = length / speed
    begin = -random.uniform(0, dur)
    live.append(
        f'<g><animateMotion dur="{dur:.1f}s" begin="{begin:.1f}s" repeatCount="indefinite" rotate="auto" '
        f'path="{d}"/>{"".join(slices_live)}</g>')
    # still: the shark at one point of its route, facing along it
    (x0, y0), (x1, y1) = at(t_still), at(t_still + 0.002)
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    still.append(f'<g transform="translate({x0:.0f} {y0:.0f}) rotate({ang:.1f})">{"".join(slices_still)}</g>')

for a in sorted(amps):
    css.append(f"@keyframes s{a}{{from{{transform:translateY({-a}px)}}to{{transform:translateY({a}px)}}}}")

# ── small fish: schools of dashes gliding across, gently bobbing ──
schools_live, schools_still = [], []
for j in range(4):
    n = random.randint(12, 20)
    y0 = random.uniform(0.15, 0.85) * H
    left = j % 2 == 0
    xs = [round(random.gauss(0, 3.2) * CW) for _ in range(n)]
    ys = [round(random.gauss(0, 2.2) * CH) for _ in range(n)]
    dur = random.uniform(45, 70)
    a, b = (-200, W + 200) if left else (W + 200, -200)
    css.append(f"@keyframes f{j}{{from{{transform:translate({a}px,{y0:.0f}px)}}to{{transform:translate({b}px,{y0:.0f}px)}}}}")
    css.append(f"@keyframes w{j}{{from{{transform:translateY(-{CH}px)}}to{{transform:translateY({CH}px)}}}}")
    txt = f'<text fill="#6f737c" x="{" ".join(map(str, xs))}" y="{" ".join(map(str, ys))}">{"-" * n}</text>'
    schools_live.append(
        f'<g style="animation:f{j} {dur:.0f}s linear {-random.uniform(0, dur):.1f}s infinite">'
        f'<g style="animation:w{j} {random.uniform(3, 5):.1f}s ease-in-out infinite alternate">{txt}</g></g>')
    schools_still.append(f'<g transform="translate({random.uniform(0.1, 0.9) * W:.0f} {y0:.0f})">{txt}</g>')

# ── scattered faint dashes, slowly breathing ──
dashes_live, dashes_still = [], []
for k in range(3):
    xs = [random.randrange(COLS) * CW + CW // 2 for _ in range(40)]
    ys = [random.randrange(ROWS) * CH + CH - 4 for _ in range(40)]
    attrs = f'fill="#9a9da4" x="{" ".join(map(str, xs))}" y="{" ".join(map(str, ys))}">{"-" * 40}</text>'
    dashes_live.append(
        f'<text style="animation:tw {random.uniform(5, 8):.1f}s ease-in-out {-k * 2.2:.1f}s infinite alternate" {attrs}')
    dashes_still.append(f'<text opacity=".45" {attrs}')
css.append("@keyframes tw{from{opacity:.15}to{opacity:.7}}")
css.append("@media (prefers-reduced-motion:reduce){*{animation-play-state:paused!important}}")

grid = (f'<pattern id="g" width="{CW}" height="{CH}" patternUnits="userSpaceOnUse">'
        f'<path d="M{CW} 0V{CH}H0" fill="none" stroke="#1d2027" stroke-opacity=".055" stroke-width="1"/></pattern>')
glow = ('<radialGradient id="r" cx="50%" cy="48%" r="38%">'
        '<stop offset="0" stop-color="#fbfbfa" stop-opacity=".9"/>'
        '<stop offset=".55" stop-color="#fbfbfa" stop-opacity=".65"/>'
        '<stop offset="1" stop-color="#fbfbfa" stop-opacity="0"/></radialGradient>')


def scene(style, dashes, schools, sharks):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice">'
            f'<defs>{grid}{glow}</defs><style>{style}</style>'
            f'<rect width="{W}" height="{H}" fill="#f5f5f3"/><rect width="{W}" height="{H}" fill="url(#g)"/>'
            f'{"".join(dashes)}{"".join(schools)}{"".join(sharks)}'
            f'<rect width="{W}" height="{H}" fill="url(#r)"/></svg>')


svg = scene("".join(css), dashes_live, schools_live, live)
svg_still = scene(css[0], dashes_still, schools_still, still)

out = sys.argv[1]
if "--svg" in sys.argv:
    open(out + ".svg", "w", encoding="utf8").write(svg)
    open(out + "-still.svg", "w", encoding="utf8").write(svg_still)
open(out + ".ts", "w", encoding="utf8", newline="\n").write(
    "// Generated by tools/gen_mosaic_scene.py: ASCII-mosaic sharks on grid paper (light).\n"
    "// Cell-rasterised silhouettes adapted from stackedlol/ascii-sharks (MIT).\n"
    "export const SCENE = " + json.dumps(svg) + "\n"
    "export const SCENE_STILL = " + json.dumps(svg_still) + "\n")
print(len(svg), len(svg_still), "chars (limit 131072)")
