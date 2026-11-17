# Python port of hooks/mosaic-shader.ts cell pass, to preview frames: python3 tools/preview_mosaic_shader.py out 10 25
import math, sys
from PIL import Image, ImageDraw, ImageFont

CW, CH = 9, 11
W, H = 1512, 945
SHARKS, NODES, SCHOOLS = 5, 12, 4
SPECIES = [(0.92,0.96,1.07,0),(0.95,0.97,1.03,1),(1.06,0.97,0.84,0),(0.93,0.97,1.06,0),(1.04,0.98,0.88,1)]
ROUTE = [(400,0.055,1.0,1.31),(340,0.061,1.17,0.83),(370,0.047,0.79,1.23),(300,0.068,1.29,0.97),(380,0.051,0.91,1.11)]
ACC = [(0.5,0.61,0.48),(0.73,0.55,0.57),(0.56,0.53,0.7),(0.64,0.55,0.4),(0.48,0.58,0.68)]
RAMP = ":;t%SX8#@"
G = [":", ";", "t", "%", "S", "X", "8", "#", "@", "o", "-", ".", "'"]

def imul(a, b): return (a * b) & 0xffffffff
def hsh(a, b, c):
    a, b, c = int(a) & 0xffffffff, int(b) & 0xffffffff, int(c) & 0xffffffff
    h = (imul(a, 374761393) + imul(b, 668265263) + imul(c, 1442695041)) & 0xffffffff
    h = imul(h ^ (h >> 13), 1274126177)
    h ^= h >> 16
    return h / 4294967296

def path(i, t):
    L, sp, fx, fy = ROUTE[i]; a = t * sp
    px = 0.5 + 0.5*math.sin(a*fx + i*2.1) + 0.1*math.sin(a*2.3 + i)
    py = 0.5 + 0.5*math.sin(a*fy + i*1.3 + 0.7) + 0.1*math.cos(a*1.9 + i*0.5)
    return px*W, py*H

def ss(a, b, x):
    t = max(0, min(1, (x-a)/(b-a))); return t*t*(3-2*t)

def hw(s): return 0.78*hw0(s)
def hw0(s):
    if s < 0.13: return 0.09*math.sqrt(max(0, math.sin(s/0.13*1.5708)))
    if s < 0.3: return 0.09 + 0.016*ss(0.13, 0.3, s)
    if s < 0.84:
        k = 1-(s-0.3)/0.54; return 0.019 + 0.087*k*math.sqrt(math.sqrt(k))
    k = (s-0.84)/0.16; return 0.019*(1-k) + 0.012*math.sin(k*3.1416)

def cell(cx, cy, cxn, cyn, time):
    kind = 0; shade = 0; tag = 0
    for i in range(SHARKS):
        L = ROUTE[i][0]; hx, hy = path(i, time)
        if math.hypot(cx-hx, cy-hy) >= L*1.25: continue
        sp = SPECIES[i]
        ex, ey = path(i, time - 0.05)
        spd = max(math.hypot(hx-ex, hy-ey)/0.05, 1.0)
        dtau = (L/(NODES-1))/spd
        best = (1e9, 0, 0); px, py = hx, hy; arc = 0.0
        for k in range(1, NODES):
            qx, qy = path(i, time - k*dtau)
            sx, sy = qx-px, qy-py
            l2 = max(sx*sx+sy*sy, 1e-4); ln = math.sqrt(l2)
            h = max(0, min(1, ((cx-px)*sx + (cy-py)*sy)/l2))
            ox, oy = px+sx*h, py+sy*h
            d = math.hypot(cx-ox, cy-oy)
            if d < best[0]:
                best = (d, (arc + ln*h)/L, ((cx-ox)*(-sy) + (cy-oy)*sx)/ln)
            arc += ln; px, py = qx, qy
        bd, s, bv = best
        wave = L*0.05*(0.1+0.9*s*s)*math.sin(time*5 + i*1.7 - s*5.2)
        v = bv - wave; sv = abs(v)/L; w = hw(s); edge = CW*0.6/L
        hit = 0; hs = 0
        if sv <= w:
            d = sv/max(w, 1e-4)
            hs = (1-d)*(0.35+0.65*ss(0, 0.25, s))*(1-0.5*ss(0.7, 1, s)); hit = 2
            if 0.1 < s < 0.75 and d < 0.2: hit = 3
            if sp[3] < 0.5 and 0.07 < s < 0.12 and 0.45 < d < 0.85: hit = 5
            if sp[0] > 1 and hsh(math.floor(s*40), math.floor(v/CW), i) > 0.82: hit = 7
        elif sp[3] > 0.5 and s < 0.08 and w < sv < 0.19:
            bar = 0.035 + (sv/0.19)*0.03
            if abs(s-bar) < 0.03:
                hit = 4; hs = 0.55
                if sv > 0.16: hit = 5
        elif 0.24 < s < 0.45 and sv-w < 0.13*(s-0.24)/0.21 and sv-w < 0.13*(1-(s-0.37)/0.08):
            hit = 4; hs = 0.3+0.35*(1-(sv-w)/0.13)
        elif 0.6 < s < 0.7 and sv-w < 0.05*(s-0.6)/0.1:
            hit = 4; hs = 0.3
        elif s > 0.86:
            k = (s-0.86)/0.14; spread = 0.11*math.sin(k*2.8)
            if abs(sv-spread*0.75) < 0.025*(1-k*0.6): hit = 4; hs = 0.4
        if hit == 0 and bd < L and sv <= w+edge and 0 < s < 1:
            hit = 1; hs = 1-(sv-w)/edge
        if hit and not kind:
            kind, shade, tag = hit, hs, i
    if not kind:
        for j in range(SCHOOLS):
            a = time*(0.05+j*0.011)
            ctx = (0.5+0.6*math.sin(a*1.3+j*2.4))*W; cty = (0.5+0.55*math.sin(a*0.9+j*1.1+1))*H
            qx = math.floor((cx-ctx)/CW); qy = math.floor((cy-cty)/CH)
            rx, ry = qx/(9+j*2), qy/(5+j)
            fall = 1-(rx*rx+ry*ry)
            if fall > 0 and hsh(qx, qy, j+50) < 0.55*fall+0.1:
                kind, shade, tag = 6, fall, j
    return kind, max(0, min(1, shade)), tag

def render(time, out):
    S = 2
    img = Image.new("RGB", (W*S, H*S), (246, 246, 244))
    dr = ImageDraw.Draw(img)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 8*S)
    for x in range(0, W, CW): dr.line([(x*S, 0), (x*S, H*S)], fill=(235, 235, 233))
    for y in range(0, H, CH): dr.line([(0, y*S), (W*S, y*S)], fill=(235, 235, 233))
    for r in range(H//CH+1):
        for c in range(W//CW+1):
            cx, cy = (c+0.5)*CW, (r+0.5)*CH
            kind, shade, tag = cell(cx, cy, c, r, time)
            if not kind: continue
            key = hsh(c, r, math.floor(time*2.4 + hsh(c, r, 9)*3))
            tint = SPECIES[tag][:3]
            x0, y0 = c*CW*S, r*CH*S
            ink = (0.11, 0.12, 0.14); g = None; level = None
            if kind == 3: level = 0.27; g = "8#@"[int(key*3)]; ink = (0.9,)*3
            elif kind == 5: level = 0.15; g = "o"; ink = (0.8,)*3
            elif kind == 4: level = 0.84-shade*0.35; g = RAMP[int(key*5)]
            elif kind == 7: level = 0.32; g = "#"; ink = (0.85,)*3
            elif kind == 2:
                level = 0.9-shade*0.68; g = RAMP[int(max(0, min(8, math.floor(shade*8.99+key*2-1))))]
                if level < 0.48: ink = (0.92,)*3
            if level is not None:
                if key < 0.07: ink = ACC[int(key*70)]
                fill = tuple(int(min(1, level*t)*255) for t in tint)
                dr.rectangle([x0+S, y0+S, x0+CW*S-1, y0+CH*S-1], fill=fill)
                dr.text((x0+CW*S/2, y0+CH*S/2), g, font=font, fill=tuple(int(v*255) for v in ink), anchor="mm")
            elif kind == 1:
                g = ":" if shade > 0.5 else ("." if key < 0.5 else "'")
                dr.text((x0+CW*S/2, y0+CH*S/2), g, font=font, fill=(158, 160, 168), anchor="mm")
            elif kind == 6:
                gv = int(246 - (246-80)*(0.35+0.5*shade))
                dr.text((x0+CW*S/2, y0+CH*S/2), "-", font=font, fill=(gv, gv, gv+6), anchor="mm")
    img = img.resize((W, H))
    img.save(out)

for t in sys.argv[2:]:
    render(float(t), f"{sys.argv[1]}-{t}.png")
