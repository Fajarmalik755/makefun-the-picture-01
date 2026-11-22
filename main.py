#!/usr/bin/env python3
"""One perfect orange half — macro style, dark teal background.

Stdlib only (zlib, struct, math, os). Renders a single orange half, cut
face toward the viewer, and writes it to $MAKEFUN_OUTPUT_DIR/entry.png
(default /output). 768x768 RGBA PNG, hand-rolled encoder.
"""
import math
import os
import struct
import zlib

W = H = 768
CX, CY = 384, 372          # orange centre (slightly above middle)
R_OUT = 272                # outer rind radius
R_PITH_OUT = 252           # outer edge of white pith ring
R_FLESH = 232              # flesh radius
N_SEG = 9                  # radial segments

# --- palette ---
BG_TOP = (13, 52, 58)
BG_BOT = (6, 28, 34)
RIND_A = (196, 82, 14)     # dark rind
RIND_B = (238, 138, 34)    # lit rind
PITH = (252, 246, 226)
FLESH_OUT = (255, 138, 26)
FLESH_IN = (255, 196, 92)
MEMBRANE = (255, 243, 214)
CORE = (250, 240, 210)


def clamp(v, lo=0, hi=255):
    return lo if v < lo else hi if v > hi else v


def mix(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def h32(x, y):
    """Deterministic integer hash -> [0, 1)."""
    h = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 4294967296.0


def render():
    # droplet specs: (x, y, r) — glossy juice beads clinging to the rind edge
    drops = [(596, 522, 11), (176, 540, 8)]
    # gloss crescent on the flesh (upper-left), as (cx, cy, rx, ry, angle)
    gx, gy, grx, gry = 280, 246, 128, 30
    ga = math.radians(-32)
    gcos, gsin = math.cos(ga), math.sin(ga)

    rows = []
    for y in range(H):
        row = bytearray()
        row.append(0)  # filter: none
        dy = y - CY
        # background vertical gradient
        tbg = y / (H - 1)
        bg = mix(BG_TOP, BG_BOT, tbg)
        for x in range(W):
            dx = x - CX
            r = math.hypot(dx, dy)
            # vignette: darken toward corners
            vx = (x - W / 2) / (W / 2)
            vy = (y - H / 2) / (H / 2)
            vig = 1.0 - 0.22 * max(0.0, vx * vx + vy * vy - 0.55)
            cr, cg, cb = int(bg[0] * vig), int(bg[1] * vig), int(bg[2] * vig)

            # soft shadow ellipse under the orange
            shx, shy = dx, (y - (CY + R_OUT + 14)) / 22.0
            if abs(shx) < 260 and abs(shy) < 1.0:
                s = math.sqrt(max(0.0, 1.0 - (shx / 260.0) ** 2 - shy * shy))
                k = 0.42 * s
                cr = int(cr * (1 - k))
                cg = int(cg * (1 - k))
                cb = int(cb * (1 - k))

            if r <= R_OUT:
                ang = math.atan2(dy, dx)
                # warm rim light on the lower-right rind
                rim = max(0.0, math.cos(ang - math.radians(55))) ** 3
                if r > R_PITH_OUT:
                    # rind: radial gradient + speckle + rim light
                    t = (r - R_PITH_OUT) / (R_OUT - R_PITH_OUT)
                    base = mix(RIND_B, RIND_A, t)
                    speck = (h32(x // 5, y // 5) - 0.5) * 26
                    cr = clamp(int(base[0] + speck + rim * 70))
                    cg = clamp(int(base[1] + speck + rim * 42))
                    cb = clamp(int(base[2] + speck + rim * 10))
                elif r > R_FLESH:
                    # white pith ring
                    p = (h32(x // 4, y // 4) - 0.5) * 14
                    cr = clamp(int(PITH[0] + p))
                    cg = clamp(int(PITH[1] + p))
                    cb = clamp(int(PITH[2] + p))
                else:
                    # ---- flesh ----
                    # segment wedge: membrane near each boundary.
                    # Curved membranes: boundary angle warps with radius.
                    warp = 0.10 * math.sin(r / R_FLESH * math.pi)
                    seg = (ang + warp + math.pi) / (2 * math.pi) * N_SEG
                    frac = seg - math.floor(seg)
                    edge = min(frac, 1.0 - frac)
                    # membrane: wide near the pith, tapering toward centre
                    mw = 0.028 + 0.055 * (r / R_FLESH)
                    tf = r / R_FLESH
                    base = mix(FLESH_IN, FLESH_OUT, tf ** 0.8)
                    # per-segment tint variation
                    si = int(math.floor(seg)) % N_SEG
                    tint = (h32(si, 7) - 0.5) * 18
                    cr = int(base[0] + tint)
                    cg = int(base[1] + tint * 0.6)
                    cb = int(base[2] + tint * 0.3)
                    # domed segments: brighter mid-wedge, shading near membranes
                    dome = 1.0 - (edge / 0.5) ** 2
                    cr = clamp(int(cr + 26 * dome))
                    cg = clamp(int(cg + 18 * dome))
                    cb = clamp(int(cb + 6 * dome))
                    # fine radial fibre streaks inside each segment
                    fib = math.sin(ang * 90.0 + si * 2.3) * 0.5 + 0.5
                    cr = clamp(int(cr + (fib - 0.5) * 16))
                    cg = clamp(int(cg + (fib - 0.5) * 12))
                    if edge < mw and r > 26:
                        # white membrane between segments
                        m = 1.0 - edge / mw
                        cr = int(cr + (MEMBRANE[0] - cr) * m * 0.9)
                        cg = int(cg + (MEMBRANE[1] - cg) * m * 0.9)
                        cb = int(cb + (MEMBRANE[2] - cb) * m * 0.9)
                    # juice vesicles: tiny bright dots, denser, radially
                    # elongated (juice sacs radiate outward from the core)
                    cell = 8
                    cxv, cyv = x // cell, y // cell
                    hv = h32(cxv, cyv)
                    if hv < 0.22:
                        # dot centre inside this cell
                        ox = (h32(cxv, 101) - 0.5) * cell
                        oy = (h32(cxv, 202) - 0.5) * cell
                        ddx = x - (cxv * cell + cell / 2 + ox)
                        ddy = y - (cyv * cell + cell / 2 + oy)
                        # stretch along the radial direction
                        ca, sa = math.cos(ang), math.sin(ang)
                        er = ddx * ca + ddy * sa
                        et = -ddx * sa + ddy * ca
                        dd = math.hypot(er / 1.9, et)
                        rad = 2.0 + h32(cxv, 303) * 0.9
                        if dd < rad:
                            b = (1.0 - dd / rad) * 0.55
                            cr = clamp(int(cr + (255 - cr) * b))
                            cg = clamp(int(cg + (238 - cg) * b))
                            cb = clamp(int(cb + (175 - cb) * b))
                    # curved gloss highlight (upper-left of the flesh):
                    # a bright crescent hugging the pith, fading outward
                    ex = (x - gx) * gcos + (y - gy) * gsin
                    ey = -(x - gx) * gsin + (y - gy) * gcos
                    ge = (ex / grx) ** 2 + (ey / gry) ** 2
                    if ge < 1.0:
                        g = (1.0 - ge) ** 1.5 * 0.5
                        cr = clamp(int(cr + (255 - cr) * g))
                        cg = clamp(int(cg + (250 - cg) * g))
                        cb = clamp(int(cb + (225 - cb) * g))
                    # pale centre core
                    if r < 26:
                        k = 1.0 - r / 26.0
                        cr = int(cr + (CORE[0] - cr) * k * 0.85)
                        cg = int(cg + (CORE[1] - cg) * k * 0.85)
                        cb = int(cb + (CORE[2] - cb) * k * 0.85)
                    # subtle radial darkening near the pith edge
                    if tf > 0.92:
                        d = (tf - 0.92) / 0.08
                        cr = int(cr * (1 - 0.10 * d))
                        cg = int(cg * (1 - 0.10 * d))
                        cb = int(cb * (1 - 0.10 * d))

            # juice droplets (drawn on top of background / rind edge)
            for (dx0, dy0, dr) in drops:
                ddx, ddy = x - dx0, y - dy0
                dd = math.hypot(ddx, ddy)
                if dd < dr:
                    t = dd / dr
                    base = mix((255, 205, 110), (235, 120, 20), t)
                    cr, cg, cb = base
                    # specular dot upper-left of the droplet
                    sx, sy = ddx + dr * 0.35, ddy + dr * 0.35
                    if math.hypot(sx, sy) < dr * 0.42:
                        s = 1.0 - math.hypot(sx, sy) / (dr * 0.42)
                        cr = clamp(int(cr + (255 - cr) * s * 0.9))
                        cg = clamp(int(cg + (255 - cg) * s * 0.9))
                        cb = clamp(int(cb + (240 - cb) * s * 0.9))

            row += bytes((clamp(cr), clamp(cg), clamp(cb), 255))
        rows.append(bytes(row))
    return b"".join(rows)


def chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    c += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return c


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    raw = render()
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6))
           + chunk(b"IEND", b""))
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(png)
    print(f"wrote {path}: {len(png)} bytes, {W}x{H}")


if __name__ == "__main__":
    main()
