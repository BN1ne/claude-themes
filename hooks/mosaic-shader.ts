// Mosaico ASCII: tiburones que nadan en curvas sobre papel cuadriculado.
// Cada celda de la cuadrícula se calcula una vez por cuadro en un buffer
// pequeño; el picture solo pinta bloques y letras. Técnica de tiburones
// rasterizados por celda adaptada de stackedlol/ascii-sharks (MIT).
import {
  abs, buffer, clamp, composer, cos, dot, exp, floor, fract, int, length, max, min, mix,
  picture, range, shader, sin, size, smoothstep, sqrt, table, time, unsigned, vec2, vec3, vec4,
} from 'claude-code/shader'
import type { Buffer, vec2 as V2 } from 'claude-code/shader'

const CW = 9
const CH = 11
const SHARKS = 5
const NODES = 12
const SCHOOLS = 4

// Glyphs, 5 wide x 6 tall, one bit a dot, top row first.
// 0 ':'  1 ';'  2 't'  3 '%'  4 'S'  5 'X'  6 '8'  7 '#'  8 '@'  9 'o'  10 '-'  11 '.'  12 '\''
const GLYPHS = table(
  [
    0b00000_00100_00000_00000_00100_00000,
    0b00000_00100_00000_00000_00100_01000,
    0b00100_01110_00100_00100_00101_00010,
    0b11001_11010_00100_01000_10110_10011,
    0b01111_10000_01110_00001_00001_11110,
    0b10001_01010_00100_00100_01010_10001,
    0b01110_10001_01110_10001_10001_01110,
    0b01010_11111_01010_01010_11111_01010,
    0b01110_10001_10111_10101_10111_01110,
    0b00000_00000_01110_10001_10001_01110,
    0b00000_00000_00000_01110_00000_00000,
    0b00000_00000_00000_00000_00000_00100,
    0b00100_00100_00000_00000_00000_00000,
  ],
  'int',
)

// Species: tint r, g, b, hammer (0/1)
const SPECIES = table([
  [0.92, 0.96, 1.07, 0],
  [0.95, 0.97, 1.03, 1],
  [1.06, 0.97, 0.84, 0],
  [0.93, 0.97, 1.06, 0],
  [1.04, 0.98, 0.88, 1],
])

// Per shark: length (points), speed (rad/s of path), x freq, y freq
const ROUTE = table([
  [400, 0.055, 1.0, 1.31],
  [340, 0.061, 1.17, 0.83],
  [370, 0.047, 0.79, 1.23],
  [300, 0.068, 1.29, 0.97],
  [380, 0.051, 0.91, 1.11],
])

function hash(a: number, b: number, c: number): number {
  let h = int(a) * 374761393 + int(b) * 668265263 + int(c) * 1442695041
  h = (h ^ (h >>> 13)) * 1274126177
  h = h ^ (h >>> 16)
  return unsigned(h) / 4294967296
}

// Where shark i's head is at time t, across the whole window and past its edges.
function path(i: number, t: number): V2 {
  const r = ROUTE.at(i)
  const a = t * r.y
  const px = 0.5 + 0.5 * sin(a * r.z + i * 2.1) + 0.1 * sin(a * 2.3 + i)
  const py = 0.5 + 0.5 * sin(a * r.w + i * 1.3 + 0.7) + 0.1 * cos(a * 1.9 + i * 0.5)
  return vec2(px * size.x, py * size.y)
}

function halfWidth(s: number): number {
  let w = 0.0
  if (s < 0.13) {
    w = 0.09 * sqrt(sin(s / 0.13 * 1.5708))
  } else if (s < 0.3) {
    w = 0.09 + 0.016 * smoothstep(0.13, 0.3, s)
  } else if (s < 0.84) {
    const k = 1.0 - (s - 0.3) / 0.54
    w = 0.019 + 0.087 * k * sqrt(sqrt(k))
  } else {
    const k = (s - 0.84) / 0.16
    w = 0.019 * (1.0 - k) + 0.012 * sin(k * 3.1416)
  }
  return w * 0.78
}

// Kinds written to the buffer, in the red lane as kind / 8.
// 1 edge, 2 skin, 3 ridge, 4 fin, 5 eye, 6 fish, 7 mark
const cells: Buffer = buffer(
  { size: [320, 170], filter: 'nearest' },
  p => {
    const c = vec2((p.cell.x + 0.5) * CW, (p.cell.y + 0.5) * CH)
    let kind = 0.0
    let shade = 0.0
    let tag = 0.0

    for (const i of range(SHARKS)) {
      const L = ROUTE.at(i).x
      const head = path(i, time)
      if (length(c - head) < L * 1.25) {
        const sp = SPECIES.at(i)
        // Walk back along the path so the body is L long and bends with the turn.
        const behind = path(i, time - 0.05)
        const spd = max(length(head - behind) / 0.05, 1.0)
        const dtau = L / (NODES - 1) / spd
        let bestD = 1e9
        let bestS = 0.0
        let bestV = 0.0
        let prev = head
        let arc = 0.0
        for (const k of range(1, NODES)) {
          const cur = path(i, time - k * dtau)
          const seg = vec2(cur - prev)
          const len2 = max(dot(seg, seg), 0.0001)
          const ln = sqrt(len2)
          const h = clamp(dot(c - prev, seg) / len2, 0.0, 1.0)
          const q = prev + seg * h
          const d = length(c - q)
          if (d < bestD) {
            bestD = d
            bestS = (arc + ln * h) / L
            bestV = dot(c - q, vec2(-seg.y, seg.x)) / ln
          }
          arc = arc + ln
          prev = cur
        }
        const s = bestS
        // Tail wave, growing toward the tail.
        const wave = L * 0.05 * (0.1 + 0.9 * s * s) * sin(time * 5.0 + i * 1.7 - s * 5.2)
        const v = bestV - wave
        const sv = abs(v) / L
        const w = halfWidth(s)
        const edge = (CW * 0.6) / L
        let hit = 0.0
        let hs = 0.0
        if (sv <= w) {
          const d = sv / max(w, 0.0001)
          hs = (1.0 - d) * (0.35 + 0.65 * smoothstep(0.0, 0.25, s)) * (1.0 - 0.5 * smoothstep(0.7, 1.0, s))
          hit = 2.0
          if (s > 0.1 && s < 0.75 && d < 0.2) {
            hit = 3.0
          }
          if (sp.w < 0.5 && s > 0.07 && s < 0.12 && d > 0.45 && d < 0.85) {
            hit = 5.0
          }
          if (sp.x > 1.0 && hash(floor(s * 40.0), floor(v / CW), i) > 0.82) {
            hit = 7.0
          }
        } else if (sp.w > 0.5 && s < 0.08 && sv < 0.19 && sv > w) {
          // Hammerhead: a wide swept bar across the head, eyes at its tips.
          const bar = 0.035 + (sv / 0.19) * 0.03
          if (abs(s - bar) < 0.03) {
            hit = 4.0
            hs = 0.55
            if (sv > 0.16) {
              hit = 5.0
            }
          }
        } else if (s > 0.24 && s < 0.45 && sv - w < 0.13 * (s - 0.24) / 0.21 && sv - w < 0.13 * (1.0 - (s - 0.37) / 0.08)) {
          hit = 4.0
          hs = 0.3 + 0.35 * (1.0 - (sv - w) / 0.13)
        } else if (s > 0.6 && s < 0.7 && sv - w < 0.05 * (s - 0.6) / 0.1) {
          hit = 4.0
          hs = 0.3
        } else if (s > 0.86) {
          const k = (s - 0.86) / 0.14
          const spread = 0.11 * sin(k * 2.8)
          if (abs(sv - spread * 0.75) < 0.025 * (1.0 - k * 0.6)) {
            hit = 4.0
            hs = 0.4
          }
        }
        if (hit == 0.0 && bestD < L && sv <= w + edge && s > 0.0 && s < 1.0) {
          hit = 1.0
          hs = 1.0 - (sv - w) / edge
        }
        if (hit > 0.0 && kind == 0.0) {
          kind = hit
          shade = hs
          tag = i
        }
      }
    }

    // Schools of small fish: dashes that ride along together.
    if (kind == 0.0) {
      for (const j of range(SCHOOLS)) {
        const a = time * (0.05 + j * 0.011)
        const ctr = vec2(
          (0.5 + 0.6 * sin(a * 1.3 + j * 2.4)) * size.x,
          (0.5 + 0.55 * sin(a * 0.9 + j * 1.1 + 1.0)) * size.y,
        )
        const q = vec2(floor((c.x - ctr.x) / CW), floor((c.y - ctr.y) / CH))
        const r = q / vec2(9.0 + j * 2.0, 5.0 + j)
        const fall = 1.0 - dot(r, r)
        if (fall > 0.0 && hash(q.x, q.y, j + 50) < 0.55 * fall + 0.1) {
          kind = 6.0
          shade = fall
          tag = j
        }
      }
    }
    const key = hash(p.cell.x, p.cell.y, floor(time * 2.4 + hash(p.cell.x, p.cell.y, 9) * 3.0))
    return vec4(kind / 8.0, clamp(shade, 0.0, 1.0), tag / 8.0, key)
  },
)

const PAPER = vec3(0.965, 0.965, 0.957)
const ACCENTS = table([
  [0.5, 0.61, 0.48],
  [0.73, 0.55, 0.57],
  [0.56, 0.53, 0.7],
  [0.64, 0.55, 0.4],
  [0.48, 0.58, 0.68],
])

function glyphAt(g: number, lx: number, ly: number): number {
  // lx, ly: 0..1 inside the cell. The glyph sits in the middle 5x6 dots.
  const gx = floor((lx - 0.2) / 0.12)
  const gy = floor((ly - 0.18) / 0.11)
  let on = 0.0
  if (gx >= 0.0 && gx < 5.0 && gy >= 0.0 && gy < 6.0) {
    const bit = int(29.0 - (gy * 5.0 + gx))
    on = ((GLYPHS.at(g) >>> bit) & 1) == 1 ? 1.0 : 0.0
  }
  return on
}

export default shader({
  fps: 30,
  passes: [
    cells,
    picture(p => {
      const cell = vec2(floor(p.point.x / CW), floor(p.point.y / CH))
      const lx = fract(p.point.x / CW)
      const ly = fract(p.point.y / CH)
      const data = cells.at(cell)
      const kind = floor(data.x * 8.0 + 0.5)
      const shade = data.y
      const tag = floor(data.z * 8.0 + 0.5)
      let col = PAPER
      // Faint grid.
      if (lx * CW < 1.0 || ly * CH < 1.0) {
        col = vec3(col * 0.955)
      }
      const key = data.w
      const tint = vec3(SPECIES.at(tag).x, SPECIES.at(tag).y, SPECIES.at(tag).z)
      const inBlock = lx * CW >= 1.0 && ly * CH >= 1.0
      if (kind >= 2.0 && kind <= 5.0 || kind == 7.0) {
        let level = 0.0
        let g = 0.0
        let ink = vec3(0.11, 0.12, 0.14)
        if (kind == 3.0) {
          level = 0.27
          g = 6.0 + floor(key * 3.0)
          ink = vec3(0.9)
        } else if (kind == 5.0) {
          level = 0.15
          g = 9.0
          ink = vec3(0.8)
        } else if (kind == 4.0) {
          level = 0.84 - shade * 0.35
          g = floor(key * 5.0)
        } else if (kind == 7.0) {
          level = 0.32
          g = 7.0
          ink = vec3(0.85)
        } else {
          level = 0.9 - shade * 0.68
          g = clamp(floor(shade * 8.99 + key * 2.0 - 1.0), 0.0, 8.0)
          if (level < 0.48) {
            ink = vec3(0.92)
          }
        }
        if (key < 0.07) {
          ink = ACCENTS.at(floor(key * 70.0))
        }
        if (inBlock) {
          col = vec3(clamp(vec3(level) * tint, 0.0, 1.0))
          if (glyphAt(g, lx, ly) > 0.5) {
            col = ink
          }
        }
      } else if (kind == 1.0) {
        const g = shade > 0.5 ? 1.0 : (key < 0.5 ? 11.0 : 12.0)
        if (glyphAt(g, lx, ly) > 0.5) {
          col = key < 0.06 ? ACCENTS.at(floor(key * 80.0)) : vec3(0.62, 0.63, 0.66)
        }
      } else if (kind == 6.0) {
        if (glyphAt(10.0, lx, ly) > 0.5) {
          col = mix(PAPER, vec3(0.3, 0.32, 0.36), 0.35 + 0.5 * shade)
        }
      }
      // Soft white glow around the prompt box; sharks fade beneath it.
      const box = composer
      const ctr = vec2((box.x + box.z) * 0.5, (box.y + box.w) * 0.5)
      const half = vec2(abs(box.z - box.x) * 0.5 + 0.08, abs(box.w - box.y) * 0.5 + 0.16)
      const r = (p.uv - ctr) / half
      const glow = exp(-dot(r, r) * 0.9)
      col = mix(col, vec3(0.985, 0.985, 0.98), glow * 0.85)
      return vec4(col, 1.0)
    }),
  ],
})
