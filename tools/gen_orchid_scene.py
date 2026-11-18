"""Turn the Oncidium screenshot into a crisp vector backdrop.

The app's backdrop frame blocks raster images (CSP img-src 'none'), so the
picture is redrawn as SVG: the source is cut into character cells, each cell
gets a glyph that follows the stripes inside it (| / \\ = ...) and a cleaned-up
colour, and the white readouts are re-set as real text. Glow comes from CSS
drop-shadow and a few sparkles twinkle with CSS keyframes.

    python tools/gen_orchid_scene.py <source.png> hooks/orchid-scene
"""
import colorsys
import sys
from collections import defaultdict

import numpy as np
from PIL import Image

W, H = 1112, 988
CW, CH = 5, 8          # character cell in source pixels
FONT = 9.6
MONO = "Consolas,'Cascadia Mono',Menlo,'DejaVu Sans Mono',monospace"

# White readouts in the source; their cells are skipped and the text redrawn.
LABELS = [(514, 173, 595, 200), (500, 264, 592, 291), (752, 306, 924, 332),
          (735, 349, 851, 393), (764, 672, 855, 698), (594, 144, 622, 164)]
RAMP = " .:-=+oO0@"


def load(path):
    a = np.asarray(Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS)).astype(float) / 255
    mx, mn = a.max(2), a.min(2)
    m = np.zeros((H, W), bool)
    for (x0, y0, x1, y1) in LABELS:
        box = (mx[y0:y1, x0:x1] > 0.35) & ((mx - mn)[y0:y1, x0:x1] / (mx[y0:y1, x0:x1] + 1e-3) < 0.3)
        m[y0:y1, x0:x1] |= box
    for _ in range(3):  # grow the mask over the text's antialiasing
        m = m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
    keep = ~m
    for _ in range(120):  # diffuse surrounding colour into the holes
        if not m.any():
            break
        acc = sum(np.roll(np.roll(a * keep[..., None], dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1))
        cnt = sum(np.roll(np.roll(keep, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1))
        fill = acc / np.maximum(cnt, 1)[..., None]
        newly = m & (cnt > 0)
        a[newly] = fill[newly]
        keep = keep | newly
        m = m & ~newly
    return a


def masked(x0, y0):
    x1, y1 = x0 + CW, y0 + CH
    return y0 > 925


def pick(cell, lum):
    """Glyph for one cell: follow the stripe direction when there is one."""
    gy, gx = np.gradient(lum)
    jxx, jyy, jxy = (gx * gx).sum(), (gy * gy).sum(), (gx * gy).sum()
    tr = jxx + jyy
    m = lum.mean()
    if tr > 0.02:
        coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (tr + 1e-9)
        if coh > 0.35:
            ang = 0.5 * np.degrees(np.arctan2(2 * jxy, jxx - jyy))  # gradient direction
            ang = (ang + 180) % 180
            if ang < 22.5 or ang >= 157.5:
                return "|"
            if ang < 67.5:
                return "\\"
            if ang < 112.5:
                return "=" if m > 0.35 else "-"
            return "/"
    i = int(min(len(RAMP) - 1, max(1, round(m * 1.6 * (len(RAMP) - 1)))))
    return RAMP[i]


def colour(rgb, peak):
    h, s, v = colorsys.rgb_to_hsv(*rgb)
    # enhance: lift value with a soft curve, push saturation, snap to a palette
    v = min(1.0, (peak ** 0.6) * 1.55)
    s = min(1.0, s * 1.2 + 0.05)
    hq = round(h * 72) / 72
    vq = max(0.25, round(v * 8) / 8)
    sq = round(s * 4) / 4
    if peak > 0.8 and s < 0.4:
        return "#fff6dc"
    r, g, b = colorsys.hsv_to_rgb(hq, sq, vq)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def build(src):
    a = load(src)
    lum = a @ np.array([0.2126, 0.7152, 0.0722])
    rows = defaultdict(lambda: defaultdict(list))   # colour -> y -> [(x, ch)]
    sparks = []
    for y0 in range(0, H - CH + 1, CH):
        for x0 in range(0, W - CW + 1, CW):
            if masked(x0, y0):
                continue
            L = lum[y0:y0 + CH, x0:x0 + CW]
            peak = np.percentile(L, 85)
            if peak < 0.085:
                continue
            cell = a[y0:y0 + CH, x0:x0 + CW]
            w = L.reshape(-1) + 1e-6
            rgb = (cell.reshape(-1, 3) * w[:, None]).sum(0) / w.sum()
            ch = pick(cell, L)
            if ch == " ":
                continue
            rows[colour(rgb, peak)][y0 + CH - 1.5].append((x0 + 0.2, ch))
            if L.max() > 0.86:
                sparks.append((x0 + CW / 2, y0 + CH / 2))

    # thin the sparkles: keep local maxima at least 26px apart
    kept = []
    for p in sparks:
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > 26 ** 2 for q in kept):
            kept.append(p)

    out = []
    for col, ys in sorted(rows.items()):
        parts = []
        for y, cells in sorted(ys.items()):
            xs = " ".join(f"{x:g}" for x, _ in cells)
            txt = "".join(c for _, c in cells).replace("&", "&amp;").replace("<", "&lt;")
            parts.append(f'<text y="{y:g}" x="{xs}">{txt}</text>')
        out.append(f'<g fill="{col}">' + "".join(parts) + "</g>")
    return out, kept


def scene(src):
    glyphs, sparks = build(src)
    css = (
        "text{white-space:pre}"
        ".f{filter:drop-shadow(0 0 1.6px rgba(255,205,80,.7)) drop-shadow(0 0 7px rgba(255,176,30,.35)) drop-shadow(0 0 22px rgba(255,160,20,.18))}"
        ".s{animation:tw 4.8s ease-in-out infinite alternate;transform-box:fill-box;transform-origin:center}"
        "@keyframes tw{0%{opacity:.25;transform:scale(.6)}100%{opacity:1;transform:scale(1.15)}}"
        ".l{fill:#eef1f3;font-family:" + MONO + ";letter-spacing:.06em;stroke:#040505;stroke-width:4px;stroke-linejoin:round;paint-order:stroke}"
        ".d{fill:#7d858c}"
    )
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">',
         f"<style>{css}</style>",
         '<defs><radialGradient id="v" cx="50%" cy="42%" r="70%"><stop offset="0" stop-color="#0c0d0b"/>'
         '<stop offset=".6" stop-color="#060707"/><stop offset="1" stop-color="#020303"/></radialGradient>'
         '<radialGradient id="g"><stop offset="0" stop-color="#fffbe8"/><stop offset=".25" stop-color="#ffe9a8" stop-opacity=".85"/>'
         '<stop offset="1" stop-color="#ffc640" stop-opacity="0"/></radialGradient></defs>',
         '<rect x="-4000" y="-4000" width="9112" height="8988" fill="#030404"/>',
         f'<rect width="{W}" height="{H}" fill="url(#v)"/>',
         f'<g class="f" font-family="{MONO}" font-size="{FONT}" font-weight="700">', *glyphs, "</g>"]
    for i, (x, y) in enumerate(sparks):
        s.append(f'<circle class="s" cx="{x:g}" cy="{y:g}" r="7" fill="url(#g)" style="animation-delay:-{(i * 1.37) % 4.8:.2f}s"/>')
    # readouts, re-set crisp
    s.append('<g class="l" font-size="17">'
             '<text x="517" y="196">K 2.95</text>'
             '<text x="504" y="287">θ 80.3°</text>'
             '<text x="757" y="328">X −0.10  Y 0.37</text>'
             '<text x="740" y="369">#430</text>'
             '<text x="740" y="389">0.35/1.00</text>'
             '<text x="767" y="694">∠ −5.8°</text></g>')
    s.append('<g fill="none" stroke="#e9ecef" stroke-width="1.6" opacity=".9">'
             '<path d="M592 283 L656 313" stroke-dasharray="1.5 6" stroke-linecap="round"/>'
             '<path d="M656 320v-7h8M694 313h8v7M656 341v7h8M694 348h8v-7"/>'
             '<path d="M656 378v6h8M694 384h8v-6"/>'
             '<path d="M632 484v6h6M710 484v6h-6"/></g>')
    s.append('<g opacity=".85"><path d="M-4000 938.5H5112" stroke="#8a9096" stroke-width="1"/>'
             '<g class="l" font-size="15"><text x="162" y="957">ONCIDIUM · BF52</text>'
             '<text class="d" x="162" y="976">YELLOW</text></g></g>')
    s.append("</svg>")
    return "".join(s)


if __name__ == "__main__":
    src, base = sys.argv[1], sys.argv[2]
    svg = scene(src)
    open(base + ".svg", "w", encoding="utf-8").write(svg)
    still = svg.replace("<style>", "<style>.s{animation:none!important}")
    import json
    with open(base + ".ts", "w", encoding="utf-8") as f:
        f.write("// Generado por tools/gen_orchid_scene.py. No editar a mano.\n")
        f.write(f"export const SCENE = {json.dumps(svg, ensure_ascii=False)}\n")
        f.write(f"export const SCENE_STILL = {json.dumps(still, ensure_ascii=False)}\n")
    print("scene chars:", len(svg), "still:", len(still))
