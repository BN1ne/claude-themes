"""Generates an animated SVG scene: ASCII-mosaic sharks on light grid paper.

Technique (cell-rasterised silhouettes, ":;t%SX8#@" skin ramp, dash schools)
adapted from stackedlol/ascii-sharks (MIT). Pre-rasterised here; CSS animates.
"""
import math, random, sys

random.seed(7)
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

def sample(s, v, L, phase):
    """Shark frame: s along body 0..1 (nose->tail), v lateral (px), spine straight
    after the wave offset is removed by caller. Returns (hit, darkness, kind)."""
    if s < -0.01 or s > 1.12: return None
    sv = abs(v) / L
    if 0 <= s <= 1:
        w = half_width(s)
        if sv <= w:
            d = sv / max(w, 1e-6)
            dark = (1 - d) ** 0.8 * (0.35 + 0.65 * smooth(0.0, 0.25, s)) * (1 - 0.5 * smooth(0.7, 1.0, s))
            if 0.08 < s < 0.13 and 0.45 < d < 0.8: return (True, 1.0, "eye")
            if d < 0.18 and 0.12 < s < 0.75: return (True, min(1, dark + 0.15), "ridge")
            return (True, dark, "skin")
    w = half_width(min(max(s, 0), 1))
    def tri(p, a, b, c):
        def sg(p1, p2, p3): return (p1[0]-p3[0])*(p2[1]-p3[1])-(p2[0]-p3[0])*(p1[1]-p3[1])
        d1, d2, d3 = sg(p, a, b), sg(p, b, c), sg(p, c, a)
        return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))
    q = (s, sv - w)
    if sv > w and tri(q, (0.24, 0), (0.45, 0.17), (0.35, 0)):
        return (True, 0.3 + 0.35 * (1 - (sv - w) / 0.17), "fin")
    if sv > w and tri(q, (0.60, 0), (0.70, 0.05), (0.66, 0)):
        return (True, 0.3, "fin")
    # caudal fork
    if 0.86 <= s <= 1.1:
        k = (s - 0.86) / 0.24
        spread = 0.11 * math.sin(k * math.pi * 0.9) ** 0.8
        lobe = abs(sv - spread * 0.75)
        if lobe < 0.025 * (1 - k * 0.6) or sv < 0.012 * (1 - k):
            return (True, 0.4, "fin")
    return None

SUBS = [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)]

def rasterise(L, heading, phase, tint):
    """Cells of one shark frame, around origin (shark nose at 0,0), in cell units."""
    hx, hy = math.cos(heading), math.sin(heading)  # nose direction
    # body runs from nose (0) back along -heading
    def to_shark(px, py):
        # s along body from nose, lateral v
        along = -(px * hx + py * hy)
        lat = -px * hy + py * hx
        s = along / L
        off = L * 0.05 * (0.1 + 0.9 * max(0, s) ** 1.8) * math.sin(phase - s * 5.2)
        return s, lat - off
    reach = int(L * 1.15 / min(CW, CH)) + 3
    cells = []
    for r in range(-reach, reach + 1):
        for c in range(-reach, reach + 1):
            cx, cy = c * CW + CW / 2, r * CH + CH / 2
            s, v = to_shark(cx, cy)
            center = sample(s, v, L, phase)
            hits = 1 if center else 0
            for ox, oy in SUBS:
                ss, vv = to_shark(c * CW + ox * CW, r * CH + oy * CH)
                if sample(ss, vv, L, phase): hits += 1
            if hits == 0: continue
            cov = hits / 5
            key = random.random()
            if center and cov >= 0.6:
                _, dark, kind = center
                cells.append((c, r, kind, dark, key))
            else:
                cells.append((c, r, "edge", cov, key))
    return cells

def tinted(level, tint):
    r, g, b = (min(255, max(0, round(level * t))) for t in tint)
    return f"#{r:02x}{g:02x}{b:02x}"

def frame_svg(cells, tint):
    """Group cells into: block paths by fill colour, text runs by colour."""
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
            level = 70 - val * 30
            ch = "@8%"[int(key * 31) % 3]
            gc = "#e6e8ec"
        elif kind == "fin":
            level = 215 - val * 90
            ch = "%;tS:"[int(key * 53) % 5]
            gc = "#2a2c33"
        else:
            level = 228 - val * 175
            jit = int(key * 3) - 1
            ch = RAMP[max(0, min(8, int(val * 8.99) + jit))]
            gc = "#1d1f25" if level > 120 else "#eceef2"
        level = round(level / 12) * 12  # bucket for fewer paths
        fill = tinted(level, tint)
        if key < 0.07:
            gc = ACCENTS[int(key * 1000) % len(ACCENTS)]
        blocks.setdefault(fill, []).append((x, y))
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

# ── sharks: length px, heading, route (start cell, step vector in cells), period
SHARKS = [
    # L, tint, start (col,row), step (dc,dr), steps, duration s
    (470, (0.93, 0.97, 1.06), (44, 100), (1, -2), 80, 70),     # rises from bottom centre, up-right
    (360, (0.95, 0.97, 1.02), (-6, 46), (2, -1), 95, 84),    # left edge, drifting up-right
    (400, (1.03, 0.96, 0.86), (-4, 96), (2, -1), 105, 96),   # bottom-left, brown tint
    (330, (0.92, 0.96, 1.08), (150, -4), (-1, 2), 70, 76),   # top-right, diving down-left
]
FRAMES = 3
parts, css = [], []
css.append("text{font:600 10px ui-monospace,Menlo,Consolas,monospace;text-anchor:middle}")
css.append(f"@keyframes fr{{0%,33.33%{{opacity:1}}33.34%,100%{{opacity:0}}}}")
WIG = 1.2
for i, (L, tint, (sc, sr), (dc, dr), steps, dur) in enumerate(SHARKS):
    heading = math.atan2(dr * CH, dc * CW)
    frames = []
    for f in range(FRAMES):
        cells = rasterise(L, heading, f * 2 * math.pi / FRAMES, tint)
        delay = -f * WIG / FRAMES
        frames.append(f'<g style="animation:fr {WIG}s step-end {delay:.2f}s infinite">{frame_svg(cells, tint)}</g>')
    dx, dy = dc * steps * CW, dr * steps * CH
    css.append(f"@keyframes m{i}{{from{{transform:translate({sc*CW}px,{sr*CH}px)}}to{{transform:translate({sc*CW+dx}px,{sr*CH+dy}px)}}}}")
    delay = -random.uniform(0.15, 0.6) * dur
    parts.append(f'<g style="animation:m{i} {dur}s steps({steps}) {delay:.1f}s infinite">{"".join(frames)}</g>')

# ── small fish: schools of dashes
for j in range(4):
    n = random.randint(12, 20)
    sc, sr = random.choice([(-10, 20), (-10, 60), (150, 30), (150, 70)])
    dc = 1 if sc < 0 else -1
    dr = random.choice([0, 0, -1, 1]) * 0
    steps = 175
    dur = random.uniform(55, 85)
    xs, ys = [], []
    for _ in range(n):
        xs.append(round(random.gauss(0, 3.2)) * CW + CW // 2)
        ys.append(round(random.gauss(0, 2.2)) * CH + CH - 4)
    css.append(f"@keyframes f{j}{{from{{transform:translate({sc*CW}px,{sr*CH}px)}}to{{transform:translate({(sc+dc*steps)*CW}px,{sr*CH}px)}}}}")
    css.append(f"@keyframes w{j}{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY({CH}px)}}}}")
    delay = -random.uniform(0, dur)
    parts.append(
        f'<g style="animation:f{j} {dur:.0f}s steps({steps}) {delay:.1f}s infinite">'
        f'<g style="animation:w{j} {random.uniform(6,10):.1f}s steps(2) infinite">'
        f'<text fill="#6f737c" x="{" ".join(map(str,xs))}" y="{" ".join(map(str,ys))}">{"-"*n}</text></g></g>')

# ── scattered faint dashes (still water marks), twinkling
dash_groups = []
for k in range(3):
    xs, ys = [], []
    for _ in range(40):
        xs.append(random.randrange(COLS) * CW + CW // 2)
        ys.append(random.randrange(ROWS) * CH + CH - 4)
    dash_groups.append(
        f'<text fill="#9a9da4" style="animation:tw {random.uniform(6,10):.1f}s step-end {-k*2.5:.1f}s infinite" '
        f'x="{" ".join(map(str,xs))}" y="{" ".join(map(str,ys))}">{"-"*40}</text>')
css.append("@keyframes tw{0%{opacity:.2}33%{opacity:.45}66%{opacity:.7}}")
css.append("@media (prefers-reduced-motion:reduce){*{animation-play-state:paused!important}}")

grid = (f'<pattern id="g" width="{CW}" height="{CH}" patternUnits="userSpaceOnUse">'
        f'<path d="M{CW} 0V{CH}H0" fill="none" stroke="#1d2027" stroke-opacity=".055" stroke-width="1"/></pattern>')
glow = ('<radialGradient id="r" cx="50%" cy="48%" r="38%">'
        '<stop offset="0" stop-color="#fbfbfa" stop-opacity=".93"/>'
        '<stop offset=".55" stop-color="#fbfbfa" stop-opacity=".72"/>'
        '<stop offset="1" stop-color="#fbfbfa" stop-opacity="0"/></radialGradient>')

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice">'
       f'<defs>{grid}{glow}</defs><style>{"".join(css)}</style>'
       f'<rect width="{W}" height="{H}" fill="#f5f5f3"/><rect width="{W}" height="{H}" fill="url(#g)"/>'
       f'{"".join(dash_groups)}{"".join(parts)}'
       f'<rect width="{W}" height="{H}" fill="url(#r)"/></svg>')

still = svg.replace("</style>", "*{animation-play-state:paused!important}</style>", 1)
out = sys.argv[1]  # e.g. python3 tools/gen_mosaic_scene.py hooks/mosaic-scene  (also writes .svg previews)
import json
open(out + ".svg", "w").write(svg) if "--svg" in sys.argv else None
open(out + "-still.svg", "w").write(still) if "--svg" in sys.argv else None
open(out + ".ts", "w").write("// Generated by gen_scene.py: ASCII-mosaic sharks on grid paper (light).\n"
    "// Cell-rasterised silhouettes adapted from stackedlol/ascii-sharks (MIT).\n"
    "export const SCENE = " + json.dumps(svg) + "\n"
    "export const SCENE_STILL = " + json.dumps(still) + "\n")
print(len(svg), len(still), "chars")
