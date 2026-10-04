"""
Rendu des 40 pioches.

Chaque pioche est dessinée UNE fois en haute résolution (supersampling x3 puis réduction =
bords lissés) dans un repère unique : le manche est strictement vertical, centré sur l'axe
x = CX, et la tête (symétrique ou non) est centrée sur ce même axe, avec une virole qui
enserre le manche. Le sprite est ensuite mis en cache, mis à l'échelle et pivoté autour
de la prise en main (grip) ou de son centre. Les effets animés (étincelles, braises...)
sont ajoutés à chaque frame autour de la tête.
"""

import math
import random
import colorsys
import pygame

from src import config

SS = 3
CW, CH = 480, 430
CX = 240            # axe du manche
HY = 128            # hauteur de la virole (centre de la tête)
H_TOP, H_BOT = HY - 44, 410
GRIP_Y = 335        # point tenu en main

_BASE_CACHE = {}
_SCALED_CACHE = {}


def _lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _grad(light, base, dark, t, pivot=0.4):
    return _lerp(light, base, t / pivot) if t < pivot else _lerp(base, dark, (t - pivot) / (1 - pivot))


def _hsv(h, s=0.7, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


class _Cv:
    def __init__(self):
        self.s = pygame.Surface((CW * SS, CH * SS), pygame.SRCALPHA)

    def _p(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def poly(self, pts, col, w=0):
        pygame.draw.polygon(self.s, col, self._p(pts), int(w * SS) if w else 0)

    def line(self, a, b, col, w=1.0):
        pygame.draw.line(self.s, col, (a[0] * SS, a[1] * SS), (b[0] * SS, b[1] * SS), max(1, int(w * SS)))

    def lines(self, pts, col, w=1.0):
        if len(pts) > 1:
            pygame.draw.lines(self.s, col, False, self._p(pts), max(1, int(w * SS)))

    def circle(self, c, r, col, w=0):
        pygame.draw.circle(self.s, col, (int(c[0] * SS), int(c[1] * SS)), max(1, int(r * SS)), int(w * SS) if w else 0)

    def ellipse(self, rect, col, w=0):
        x, y, ww, hh = rect
        pygame.draw.ellipse(self.s, col, (x * SS, y * SS, ww * SS, hh * SS), int(w * SS) if w else 0)

    def arc(self, rect, a0, a1, col, w=1.0):
        x, y, ww, hh = rect
        pygame.draw.arc(self.s, col, (x * SS, y * SS, ww * SS, hh * SS), a0, a1, max(1, int(w * SS)))

    def rrect(self, rect, col, rad=3, w=0):
        x, y, ww, hh = rect
        pygame.draw.rect(self.s, col, (x * SS, y * SS, ww * SS, hh * SS), int(w * SS) if w else 0,
                         border_radius=int(rad * SS))

    def glow(self, c, r, col, alpha, steps=14):
        size = int(r * 2 * SS)
        tmp = pygame.Surface((size, size), pygame.SRCALPHA)
        for i in range(steps, 0, -1):
            rr = r * SS * i / steps
            a = int(alpha * ((1 - i / steps) ** 1.6) / 3.2) + 1
            pygame.draw.circle(tmp, (*col, a), (size // 2, size // 2), int(rr))
        self.s.blit(tmp, (c[0] * SS - size // 2, c[1] * SS - size // 2))

    def star(self, c, r, col, thin=0.28):
        pts = []
        for i in range(8):
            a = i * math.pi / 4 - math.pi / 2
            rr = r if i % 2 == 0 else r * thin
            pts.append((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr))
        self.poly(pts, col)


# ----------------------------------------------------------------------
# GÉOMÉTRIE DES LAMES
# ----------------------------------------------------------------------
HEAD_DEFAULTS = {
    "wood":    dict(span=150, droop=46, thick=54, q=1.2),
    "stone":   dict(span=150, droop=40, thick=92, q=1.05),
    "pick":    dict(span=185, droop=62, thick=74, q=1.45),
    "curved":  dict(span=210, droop=56, thick=66, q=1.6, hook=14),
    "winged":  dict(span=200, droop=42, thick=70, q=1.5, hook=10),
    "crystal": dict(span=190, droop=50, thick=80, q=1.25),
    "adze":    dict(span=185, droop=58, thick=70, q=1.45),
    "hammer":  dict(span=185, droop=58, thick=70, q=1.45),
}


def _blade(span, droop, thick, q=1.5, hook=0.0, side=1, n=30, up=0.55, oy=0.0):
    U, L = [], []
    for i in range(n + 1):
        t = i / n
        x = CX + side * span * t
        cy = HY + oy + droop * t * t - hook * t ** 5
        th = thick * (1 - t) ** q
        U.append((x, cy - th * up))
        L.append((x, cy + th * (1 - up)))
    return U, L


def _quad_blade(p_top_in, p_top_out, p_bot_out, p_bot_in, n=8):
    U = [(p_top_in[0] + (p_top_out[0] - p_top_in[0]) * i / n, p_top_in[1] + (p_top_out[1] - p_top_in[1]) * i / n) for i in range(n + 1)]
    L = [(p_bot_in[0] + (p_bot_out[0] - p_bot_in[0]) * i / n, p_bot_in[1] + (p_bot_out[1] - p_bot_in[1]) * i / n) for i in range(n + 1)]
    return U, L


def _mid(U, L, i, f):
    i = min(len(U) - 1, max(0, i))
    return (U[i][0] + (L[i][0] - U[i][0]) * f, U[i][1] + (L[i][1] - U[i][1]) * f)


def _shade_blade(cv, U, L, mat, bands=8, facet=False):
    light, base, dark, rim = mat
    n = len(U)
    for k in range(bands):
        a, b = k / bands, (k + 1) / bands
        top = [(U[i][0] + (L[i][0] - U[i][0]) * a, U[i][1] + (L[i][1] - U[i][1]) * a) for i in range(n)]
        bot = [(U[i][0] + (L[i][0] - U[i][0]) * b, U[i][1] + (L[i][1] - U[i][1]) * b) for i in range(n)]
        cv.poly(top + bot[::-1], _grad(light, base, dark, (k + 0.5) / bands))
    if facet:
        for i in range(0, n - 1, 3):
            j = min(n - 1, i + 3)
            col = _lerp(base, light if (i // 3) % 2 == 0 else dark, 0.42)
            cv.poly([_mid(U, L, i, 0.0), _mid(U, L, j, 0.0), _mid(U, L, j, 1.0), _mid(U, L, i, 1.0)], col)
            cv.line(_mid(U, L, i, 0.0), _mid(U, L, i, 1.0), _lerp(light, (255, 255, 255), 0.5), 1.0)
        cv.lines([_mid(U, L, i, 0.5) for i in range(n)], _lerp(light, (255, 255, 255), 0.4), 1.0)
    edge = _lerp(dark, (0, 0, 0), 0.55)
    cv.lines(U, edge, 2.2)
    cv.lines(L, edge, 2.2)
    cv.lines([(x, y + 1.8) for x, y in U], _lerp(light, (255, 255, 255), 0.65), 1.5)
    cv.lines([(x, y - 1.4) for x, y in L], rim, 1.2)


def _decor_blade(cv, U, L, art, mat, rng):
    deco = art["deco"]
    light, base, dark, rim = mat
    n = len(U)
    dk = _lerp(dark, (0, 0, 0), 0.35)
    if "engrave" in deco:
        for i in range(3, n - 4, 4):
            cv.line(_mid(U, L, i, 0.3), _mid(U, L, i + 1, 0.7), dk, 1.2)
            cv.line(_mid(U, L, i + 1, 0.3), _mid(U, L, i + 2, 0.7), _lerp(light, (255, 255, 255), 0.4), 0.8)
    if "damascus" in deco:
        for r in (0.22, 0.4, 0.58, 0.76):
            cv.lines([(U[i][0] + (L[i][0] - U[i][0]) * r, U[i][1] + (L[i][1] - U[i][1]) * r + math.sin(i * 0.9 + r * 9) * 2.4)
                      for i in range(2, n - 2)], _lerp(base, dark, 0.7), 1.2)
            cv.lines([(U[i][0] + (L[i][0] - U[i][0]) * (r + 0.06), U[i][1] + (L[i][1] - U[i][1]) * (r + 0.06) + math.sin(i * 0.9 + r * 9 + 1) * 2.4)
                      for i in range(2, n - 2)], _lerp(light, (255, 255, 255), 0.3), 0.9)
    if "inlay" in deco:
        col = art.get("inlay", (255, 226, 140))
        cv.lines([_mid(U, L, i, 0.42) for i in range(2, n - 3)], col, 1.8)
        cv.lines([_mid(U, L, i, 0.42) for i in range(2, n - 3)], _lerp(col, (255, 255, 255), 0.6), 0.7)
    if "speckle" in deco:
        for _ in range(55):
            i = rng.randint(1, max(1, n - 3))
            f = rng.random()
            x, y = _mid(U, L, i, f)
            cv.circle((x, y), rng.choice([0.8, 1.2, 1.8]), _lerp(base, light if rng.random() < 0.5 else dark, 0.7))
    if "crack" in deco:
        for _ in range(2):
            i = rng.randint(min(4, n - 3), max(min(4, n - 3), n - 8))
            pts = [_mid(U, L, i, 0.0)]
            f = 0.0
            for s in range(4):
                f = min(1.0, f + rng.uniform(0.15, 0.3))
                pts.append((_mid(U, L, i + s, f)[0] + rng.uniform(-4, 4), _mid(U, L, i + s, f)[1]))
            cv.lines(pts, (30, 20, 14), 1.5)
    if "runes" in deco:
        g = art.get("glow") or (120, 160, 255)
        for i in range(5, n - 4, 5):
            x, y = _mid(U, L, i, 0.5)
            cv.glow((x, y), 11, g, 150, 8)
            cv.line((x, y - 6), (x, y + 6), _lerp(g, (255, 255, 255), 0.7), 1.5)
            cv.line((x - 4, y - 2), (x + 4, y + 3), _lerp(g, (255, 255, 255), 0.7), 1.3)
            cv.line((x + 4, y - 4), (x - 1, y - 1), _lerp(g, (255, 255, 255), 0.7), 1.2)
    if "magma" in deco:
        for _ in range(4):
            i = rng.randint(min(3, n - 3), max(min(3, n - 3), n - 8))
            pts = [_mid(U, L, i, 0.05)]
            f = 0.05
            for s in range(4):
                f = min(0.95, f + rng.uniform(0.18, 0.3))
                pts.append((_mid(U, L, i + s, f)[0] + rng.uniform(-5, 5), _mid(U, L, i + s, f)[1]))
            cv.lines(pts, (255, 90, 20), 3.2)
            cv.lines(pts, (255, 220, 110), 1.2)
    if "aurora" in deco or "prism" in deco:
        full = "prism" in deco
        bands = 7
        for i in range(2, n - 1):
            for k in range(bands):
                a, b = k / bands, (k + 1) / bands
                h = (0.0 + i / n * 0.9 + k * 0.03) if full else (0.42 + 0.30 * (0.5 + 0.5 * math.sin(i * 0.35 + k * 0.5)))
                col = _hsv(h, 0.55 if full else 0.6, 1.0)
                base_c = _grad(light, base, dark, (k + 0.5) / bands)
                cv.poly([(U[i][0] + (L[i][0] - U[i][0]) * a, U[i][1] + (L[i][1] - U[i][1]) * a),
                         (U[i + 1][0] + (L[i + 1][0] - U[i + 1][0]) * a, U[i + 1][1] + (L[i + 1][1] - U[i + 1][1]) * a),
                         (U[i + 1][0] + (L[i + 1][0] - U[i + 1][0]) * b, U[i + 1][1] + (L[i + 1][1] - U[i + 1][1]) * b),
                         (U[i][0] + (L[i][0] - U[i][0]) * b, U[i][1] + (L[i][1] - U[i][1]) * b)],
                        _lerp(base_c, col, 0.5))
        cv.lines(U, _lerp(dark, (0, 0, 0), 0.5), 2.0)
        cv.lines(L, _lerp(dark, (0, 0, 0), 0.5), 2.0)
        cv.lines([(x, y + 1.8) for x, y in U], (255, 255, 255), 1.4)
    if "scales" in deco:
        for f in (0.28, 0.5, 0.72):
            for i in range(3, n - 3, 3):
                x, y = _mid(U, L, i, f)
                cv.arc((x - 3.5, y - 3.5, 7, 7), 3.4, 6.0, _lerp(light, (255, 255, 255), 0.35), 1.1)
                cv.arc((x - 3.5, y - 2.5, 7, 7), 3.4, 6.0, _lerp(dark, (0, 0, 0), 0.4), 1.0)
    if "rivets" in deco:
        for i in (4, 8):
            x, y = _mid(U, L, i, 0.5)
            cv.circle((x, y), 2.4, _lerp(dark, (0, 0, 0), 0.4))
            cv.circle((x - 0.5, y - 0.5), 1.6, rim)
    if "nebula" in deco:
        for _ in range(7):
            i = rng.randint(min(2, n - 3), max(min(2, n - 3), n - 5))
            x, y = _mid(U, L, i, rng.uniform(0.2, 0.8))
            cv.glow((x, y), rng.uniform(10, 18), rng.choice([(255, 120, 220), (120, 200, 255), (200, 140, 255)]), 140, 8)


# ----------------------------------------------------------------------
# TÊTES
# ----------------------------------------------------------------------
def _params(art, kind):
    p = dict(HEAD_DEFAULTS.get(kind, HEAD_DEFAULTS["pick"]))
    for k in ("span", "droop", "thick", "q", "hook"):
        if k in art:
            p[k] = art[k]
    return p


def _head_flint(cv, art, mat, rng):
    light, base, dark, rim = mat
    A, B, C, D, E = (CX - 24, HY + 14), (CX - 32, HY - 22), (CX + 28, HY - 50), (CX + 100, HY - 4), (CX + 44, HY + 16)
    poly = [A, B, C, D, E]
    cv.poly(poly, base)
    cv.poly([B, C, E, A], _lerp(base, light, 0.45))
    cv.poly([C, D, E], _lerp(base, dark, 0.55))
    cv.poly([C, D, (CX + 60, HY - 16)], _lerp(light, (255, 255, 255), 0.35))
    for k in range(3):
        cv.arc((CX + 20 + k * 10, HY - 40 + k * 6, 60, 50), 5.3, 6.1, _lerp(dark, (0, 0, 0), 0.3), 1.0)
    cv.lines(poly + [poly[0]], _lerp(dark, (0, 0, 0), 0.55), 2.2)
    cv.lines([D, C], rim, 1.4)
    return []


def _head_generic(cv, art, mat, rng, kind):
    p = _params(art, kind)
    facet = kind == "crystal"
    out = []
    R = _blade(**p, side=1)
    if kind == "adze":
        Lb = _quad_blade((CX, HY - 28), (CX - 104, HY - 44), (CX - 104, HY + 40), (CX, HY + 26))
        _shade_blade(cv, *Lb, mat)
        cv.line((CX - 104, HY - 44), (CX - 104, HY + 40), _lerp(mat[3], (255, 255, 255), 0.4), 2.2)
    elif kind == "hammer":
        Lb = _quad_blade((CX, HY - 34), (CX - 78, HY - 36), (CX - 78, HY + 36), (CX, HY + 34))
        _shade_blade(cv, *Lb, mat)
        cv.rrect((CX - 92, HY - 40, 16, 80), _lerp(mat[1], mat[2], 0.5), 3)
        cv.rrect((CX - 92, HY - 40, 16, 80), _lerp(mat[2], (0, 0, 0), 0.5), 3, 1.6)
        cv.line((CX - 90, HY - 36), (CX - 90, HY + 36), _lerp(mat[0], (255, 255, 255), 0.5), 1.4)
    else:
        Lb = _blade(**p, side=-1)
        _shade_blade(cv, *Lb, mat, facet=facet)
    _shade_blade(cv, *R, mat, facet=facet)
    out = [R, Lb]
    return out


def _head_winged(cv, art, mat, rng):
    p = _params(art, "winged")
    light, base, dark, rim = mat
    fm = (_lerp(light, base, 0.3), _lerp(base, dark, 0.2), dark, rim)
    out = []
    for side in (-1, 1):
        up_fin = _blade(span=p["span"] * 0.72, droop=-38, thick=34, q=1.4, side=side, oy=-26)
        lo_fin = _blade(span=p["span"] * 0.55, droop=64, thick=24, q=1.3, side=side, oy=18)
        _shade_blade(cv, *up_fin, fm)
        _shade_blade(cv, *lo_fin, fm)
    for side in (-1, 1):
        b = _blade(**p, side=side)
        _shade_blade(cv, *b, mat)
        out.append(b)
    return out


HEADS = {
    "flint": lambda cv, a, m, r: _head_flint(cv, a, m, r),
    "winged": _head_winged,
}


# ----------------------------------------------------------------------
# MANCHE, VIROLE, GEMME
# ----------------------------------------------------------------------
def _handle(cv, art):
    light, base, dark = art["handle"]
    style = art["hstyle"]
    wt, wb = 17, 21
    S = 9
    for j in range(S):
        a, b = j / S, (j + 1) / S
        t = (j + 0.5) / S
        col = _grad(light, base, dark, t, 0.3)
        cv.poly([(CX - wt / 2 + wt * a, H_TOP), (CX - wt / 2 + wt * b, H_TOP),
                 (CX - wb / 2 + wb * b, H_BOT), (CX - wb / 2 + wb * a, H_BOT)], col)
    edge = _lerp(dark, (0, 0, 0), 0.55)
    cv.line((CX - wt / 2, H_TOP), (CX - wb / 2, H_BOT), edge, 2.0)
    cv.line((CX + wt / 2, H_TOP), (CX + wb / 2, H_BOT), edge, 2.0)
    cv.line((CX - wt / 2 + 3, H_TOP + 6), (CX - wb / 2 + 3.5, H_BOT - 6), _lerp(light, (255, 255, 255), 0.5), 1.2)
    rng = random.Random(art["name"] + "h")

    def hw(y):
        return wt + (wb - wt) * (y - H_TOP) / (H_BOT - H_TOP)

    if style == "wood":
        for _ in range(7):
            x = CX + rng.uniform(-5, 5)
            y0 = rng.uniform(H_TOP + 30, H_BOT - 60)
            cv.lines([(x, y0), (x + rng.uniform(-1.5, 1.5), y0 + 25), (x + rng.uniform(-1.5, 1.5), y0 + 50)],
                     _lerp(base, dark, 0.7), 1.0)
        cv.ellipse((CX - 2, 250, 5, 8), _lerp(base, dark, 0.6), 1.2)
        cv.ellipse((CX - wb / 2, H_BOT - 3, wb, 8), _lerp(base, dark, 0.35))
    elif style == "bone":
        for y in range(190, 400, 38):
            cv.rrect((CX - hw(y) / 2 - 2, y, hw(y) + 4, 8), _lerp(light, (255, 255, 255), 0.3), 3)
            cv.rrect((CX - hw(y) / 2 - 2, y, hw(y) + 4, 8), _lerp(dark, (0, 0, 0), 0.3), 3, 1.2)
        cv.circle((CX, H_BOT + 2), 11, _lerp(base, light, 0.4))
        cv.circle((CX, H_BOT + 2), 11, _lerp(dark, (0, 0, 0), 0.3), 1.4)
    elif style == "wrap":
        for y in range(238, H_BOT - 6, 9):
            w = hw(y)
            cv.line((CX - w / 2 - 1, y), (CX + w / 2 + 1, y + 6), _lerp(dark, (0, 0, 0), 0.4), 2.6)
            cv.line((CX - w / 2 - 1, y + 2.4), (CX + w / 2 + 1, y + 8.4), _lerp(light, (255, 255, 255), 0.25), 1.0)
        cv.rrect((CX - hw(232) / 2 - 3, 230, hw(232) + 6, 7), _lerp(dark, (0, 0, 0), 0.2), 2)
        cv.ellipse((CX - wb / 2 - 1, H_BOT - 4, wb + 2, 10), _lerp(dark, (0, 0, 0), 0.2))
        cv.ellipse((CX - wb / 2 - 1, H_BOT - 4, wb + 2, 10), _lerp(light, (255, 255, 255), 0.2), 1.0)
    elif style in ("metal", "gold", "white"):
        band = _lerp(light, (255, 255, 255), 0.35) if style != "gold" else (255, 232, 130)
        for y in (150, 200, 262, 330, 398):
            w = hw(y)
            cv.rrect((CX - w / 2 - 3, y, w + 6, 7), band, 2)
            cv.rrect((CX - w / 2 - 3, y, w + 6, 7), _lerp(dark, (0, 0, 0), 0.4), 2, 1.1)
        cv.line((CX, 160), (CX, 395), _lerp(base, dark, 0.5), 1.0)
        for y in range(215, 330, 18):
            cv.circle((CX, y), 1.6, band)
        pom = {"metal": (light, base, dark), "gold": ((255, 245, 170), (236, 190, 70), (150, 100, 24)),
               "white": ((255, 255, 255), (245, 248, 255), (200, 206, 236))}[style]
        cv.circle((CX, H_BOT + 6), 13, pom[2])
        cv.circle((CX, H_BOT + 5), 11.5, pom[1])
        cv.circle((CX - 3, H_BOT + 2), 4.5, pom[0])
        cv.circle((CX, H_BOT + 6), 13, _lerp(pom[2], (0, 0, 0), 0.5), 1.5)
    if "inlay" in art["deco"] and style in ("gold", "metal", "wrap", "white"):
        col = art.get("inlay", (255, 226, 140))
        cv.line((CX - 3, 262), (CX - 3, 328), col, 1.1)
        cv.line((CX + 3, 262), (CX + 3, 328), col, 1.1)


def _hub(cv, art, mat):
    light, base, dark, rim = mat
    deco = art["deco"]
    if "rope" in deco:
        rope = (214, 182, 124)
        rd = (120, 88, 50)
        for i in range(6):
            y = HY - 28 + i * 10
            cv.line((CX - 19, y), (CX + 19, y + 9), rd, 4.0)
            cv.line((CX - 19, y), (CX + 19, y + 9), rope, 2.6)
            cv.line((CX + 19, y), (CX - 19, y + 9), rd, 3.2)
            cv.line((CX + 19, y), (CX - 19, y + 9), _lerp(rope, (255, 255, 255), 0.2), 1.8)
        return
    hm = _lerp(base, dark, 0.25)
    S = 8
    for j in range(S):
        a, b = j / S, (j + 1) / S
        cv.poly([(CX - 20 + 40 * a, HY - 34), (CX - 20 + 40 * b, HY - 34), (CX - 20 + 40 * b, HY + 36), (CX - 20 + 40 * a, HY + 36)],
                _grad(_lerp(light, hm, 0.3), hm, dark, (j + 0.5) / S, 0.3))
    edge = _lerp(dark, (0, 0, 0), 0.5)
    cv.rrect((CX - 20, HY - 34, 40, 70), edge, 5, 2.0)
    for y in (HY - 24, HY + 25):
        cv.line((CX - 20, y), (CX + 20, y), edge, 1.8)
        cv.line((CX - 19, y + 1.8), (CX + 19, y + 1.8), _lerp(light, (255, 255, 255), 0.5), 1.0)
    cv.line((CX - 14, HY - 30), (CX - 14, HY + 32), _lerp(light, (255, 255, 255), 0.5), 1.2)
    # fleuron au sommet
    cv.poly([(CX - 8, HY - 33), (CX, HY - 62), (CX + 8, HY - 33)], hm)
    cv.poly([(CX - 8, HY - 33), (CX, HY - 62), (CX, HY - 33)], _lerp(light, hm, 0.3))
    cv.lines([(CX - 8, HY - 33), (CX, HY - 62), (CX + 8, HY - 33)], edge, 1.8)


def _gem(cv, col, big=False):
    r = 14 if big else 12
    top, left, right, bot = _lerp(col, (255, 255, 255), 0.6), _lerp(col, (255, 255, 255), 0.25), _lerp(col, (0, 0, 0), 0.25), _lerp(col, (0, 0, 0), 0.45)
    cx, cy = CX, HY
    cv.glow((cx, cy), 28, col, 140, 10)
    cv.poly([(cx, cy - r - 2), (cx + r, cy), (cx, cy + r + 4), (cx - r, cy)], col)
    cv.poly([(cx, cy - r - 2), (cx - r, cy), (cx, cy)], top)
    cv.poly([(cx, cy - r - 2), (cx + r, cy), (cx, cy)], left)
    cv.poly([(cx - r, cy), (cx, cy + r + 4), (cx, cy)], right)
    cv.poly([(cx + r, cy), (cx, cy + r + 4), (cx, cy)], bot)
    cv.poly([(cx, cy - r - 2), (cx + r, cy), (cx, cy + r + 4), (cx - r, cy)], _lerp(col, (0, 0, 0), 0.6), 1.6)
    cv.circle((cx - 4, cy - 6), 2.4, (255, 255, 255))


def _eye(cv, art):
    g = art.get("glow") or (200, 80, 255)
    cv.glow((CX, HY), 34, g, 170, 10)
    cv.poly([(CX - 20, HY), (CX - 8, HY - 11), (CX + 8, HY - 11), (CX + 20, HY), (CX + 8, HY + 11), (CX - 8, HY + 11)],
            _lerp(g, (255, 255, 255), 0.75))
    cv.poly([(CX - 20, HY), (CX - 8, HY - 11), (CX + 8, HY - 11), (CX + 20, HY), (CX + 8, HY + 11), (CX - 8, HY + 11)],
            _lerp(g, (0, 0, 0), 0.6), 1.8)
    cv.ellipse((CX - 6, HY - 10, 12, 20), _lerp(g, (0, 0, 0), 0.35))
    cv.ellipse((CX - 2, HY - 9, 4, 18), (10, 4, 18))
    cv.circle((CX - 5, HY - 4), 1.8, (255, 255, 255))


# ----------------------------------------------------------------------
# ORNEMENTS D'ENSEMBLE
# ----------------------------------------------------------------------
def _corona(cv, col):
    cv.glow((CX, HY), 120, col, 120, 12)
    for i in range(18):
        a = i * math.tau / 18
        r1, r2 = 44, 88 if i % 2 == 0 else 66
        w = 0.1
        pts = [(CX + math.cos(a - w) * r1, HY + math.sin(a - w) * r1), (CX + math.cos(a) * r2, HY + math.sin(a) * r2),
               (CX + math.cos(a + w) * r1, HY + math.sin(a + w) * r1)]
        cv.poly(pts, _lerp(col, (255, 255, 255), 0.5 if i % 2 == 0 else 0.15))


def _vortex(cv, col):
    cv.glow((CX, HY), 100, col, 130, 12)
    for k, r in enumerate((52, 66, 82)):
        for s in range(3):
            a0 = s * 2.1 + k * 0.7
            cv.arc((CX - r, HY - r, 2 * r, 2 * r), a0, a0 + 1.2, _lerp(col, (255, 255, 255), 0.25 * (2 - k) / 2 + 0.2), 3.0 - k * 0.6)


def _feathers(cv, mat, art):
    light, base, dark, rim = mat
    gold = art["name"] in ("Pioche divine", "Pioche céleste", "Pioche du créateur", "Pioche de la genèse")
    fire = "firewings" in art["deco"]
    for side in (-1, 1):
        for i in range(7):
            ang = math.radians(-16 - i * 14)
            L = 62 + i * 13
            ox, oy = CX + side * (16 + i * 2), HY - 14 - i * 2
            dx, dy = math.cos(ang) * side, math.sin(ang)
            tip = (ox + dx * L, oy + dy * L)
            px, py = -dy, dx
            w = 9 + i * 0.6
            pts = [(ox, oy), (ox + dx * L * 0.45 + px * w, oy + dy * L * 0.45 + py * w), tip,
                   (ox + dx * L * 0.45 - px * w, oy + dy * L * 0.45 - py * w)]
            col = _lerp((255, 244, 160), (226, 60, 24), i / 6.5) if fire else _lerp((255, 255, 255), (214, 222, 255), i / 7)
            cv.poly(pts, col)
            cv.poly([pts[0], pts[1], tip], _lerp(col, (255, 255, 255), 0.6))
            cv.lines(pts + [pts[0]], (150, 40, 20) if fire else _lerp((170, 178, 220), (214, 170, 80) if gold else (170, 178, 220), 0.7), 1.4)
            cv.line((ox, oy), tip, _lerp((190, 196, 230), (255, 214, 120), 0.6 if gold else 0.0), 1.0)


def _flames(cv, art, blades):
    cols = [(210, 40, 16), (255, 120, 24), (255, 210, 70)]
    spots = []
    for U, L in blades:
        n = len(U)
        for i in (int(n * 0.38), int(n * 0.62), int(n * 0.88)):
            spots.append((U[i][0], U[i][1] + 2, 1.0 - i / n * 0.45))
    spots.append((CX, HY - 62, 1.3))
    for (x, y, s) in spots:
        h = 38 * s + 6
        for k, c in enumerate(cols):
            sc = 1 - k * 0.27
            pts = [(x - 9 * sc, y), (x - 6 * sc, y - h * 0.45 * sc), (x - 1 * sc, y - h * 0.7 * sc), (x + 2 * sc, y - h * sc),
                   (x + 5 * sc, y - h * 0.62 * sc), (x + 9 * sc, y - h * 0.3 * sc), (x + 8 * sc, y)]
            cv.poly(pts, c)


def _ice(cv, art, blades, rng):
    for U, L in blades:
        n = len(U)
        for i in range(4, n - 3, 5):
            x, y = U[i]
            sgn = 1 if x > CX else -1
            h = 30 - i * 0.6
            w = 5
            pts = [(x - w, y), (x - w * 0.6, y - h * 0.7), (x + sgn * 3, y - h), (x + w * 0.7, y - h * 0.65), (x + w, y)]
            cv.poly(pts, (214, 244, 255))
            cv.poly([pts[0], pts[1], pts[2], (x, y)], (255, 255, 255))
            cv.poly([pts[2], pts[3], pts[4], (x, y)], (120, 190, 235))
            cv.lines(pts + [pts[0]], (70, 130, 190), 1.1)


def _bolt(cv, art, blades, rng):
    g = art.get("glow") or (255, 240, 110)
    paths = []
    for U, L in blades:
        n = len(U)
        paths.append([_mid(U, L, i, 0.5) for i in range(0, n, 3)])
    paths.append([(CX, 300), (CX, H_TOP)])
    for pts in paths:
        zz = [pts[0]]
        for k in range(1, len(pts)):
            zz.append((pts[k][0] + rng.uniform(-6, 6), pts[k][1] + rng.uniform(-6, 6)))
        for x, y in zz[::2]:
            cv.glow((x, y), 12, g, 120, 6)
        cv.lines(zz, g, 3.4)
        cv.lines(zz, (255, 255, 255), 1.3)


def _halo(cv, art):
    cv.glow((CX, HY - 92), 80, (255, 255, 255), 110, 10)
    for i in range(36):
        a0 = i * math.tau / 36
        cv.arc((CX - 70, HY - 112, 140, 40), a0, a0 + 0.2, _hsv(i / 36, 0.55, 1.0), 5.0)
    cv.arc((CX - 70, HY - 112, 140, 40), 0, math.tau, (255, 255, 255), 1.5)


def _spikes(cv, blades, mat):
    light, base, dark, rim = mat
    for U, L in blades:
        n = len(U)
        for i in range(5, n - 4, 6):
            x, y = U[i]
            sgn = 1 if x > CX else -1
            h = 22 - i * 0.4
            cv.poly([(x - 4, y + 1), (x + sgn * 2, y - h), (x + 5, y + 1)], _lerp(light, base, 0.4))
            cv.poly([(x - 4, y + 1), (x + sgn * 2, y - h), (x + 0.5, y + 1)], _lerp(light, (255, 255, 255), 0.5))
            cv.lines([(x - 4, y + 1), (x + sgn * 2, y - h), (x + 5, y + 1)], _lerp(dark, (0, 0, 0), 0.4), 1.2)


def _stars(cv, blades, art, rng):
    col = _lerp(art["mat"][0], (255, 255, 255), 0.7)
    for U, L in blades:
        n = len(U)
        for i in (6, 12, 19):
            x, y = _mid(U, L, i, 0.5)
            cv.glow((x, y), 12, col, 120, 6)
            cv.star((x, y), 6.5 - i * 0.12, (255, 255, 255))


def _crystal_shards(cv, art):
    light, base, dark, rim = art["mat"]
    for dx, h in ((-18, 40), (0, 60), (18, 42)):
        pts = [(CX + dx - 6, HY - 34), (CX + dx - 3, HY - 34 - h * 0.7), (CX + dx, HY - 34 - h), (CX + dx + 4, HY - 34 - h * 0.7), (CX + dx + 6, HY - 34)]
        cv.poly(pts, base)
        cv.poly([pts[0], pts[1], pts[2], (CX + dx, HY - 34)], _lerp(light, (255, 255, 255), 0.4))
        cv.poly([pts[2], pts[3], pts[4], (CX + dx, HY - 34)], dark)
        cv.lines(pts + [pts[0]], _lerp(dark, (0, 0, 0), 0.5), 1.2)


def _eclipse(cv, art):
    g = art.get("glow") or (255, 200, 90)
    cv.glow((CX, HY), 130, g, 150, 14)
    for i in range(24):
        a = i * math.tau / 24
        r1, r2 = 66, 118 if i % 2 == 0 else 90
        w = 0.07
        cv.poly([(CX + math.cos(a - w) * r1, HY + math.sin(a - w) * r1), (CX + math.cos(a) * r2, HY + math.sin(a) * r2),
                 (CX + math.cos(a + w) * r1, HY + math.sin(a + w) * r1)], _lerp(g, (255, 255, 255), 0.3))
    cv.circle((CX, HY), 68, _lerp(g, (255, 255, 255), 0.55))
    cv.circle((CX, HY), 62, (10, 6, 16))
    cv.circle((CX, HY), 62, g, 3)
    cv.circle((CX - 24, HY - 30), 14, (28, 20, 40))


def _horns(cv, blades, mat):
    light, base, dark, rim = mat
    for U, L in blades:
        n = len(U)
        sgn = 1 if U[-1][0] > CX else -1
        x, y = U[int(n * 0.9)]
        pts_o, pts_i = [], []
        for k in range(12):
            t = k / 11
            hx = x + sgn * (4 + 26 * t - 22 * t * t) * 1.0
            hy = y - 66 * t
            w = 17 * (1 - t) ** 0.7
            pts_o.append((hx + sgn * w * 0.4, hy))
            pts_i.append((hx - sgn * w * 0.6, hy))
        poly = pts_o + pts_i[::-1]
        cv.poly(poly, _lerp(base, light, 0.35))
        cv.poly(pts_o + [(p[0] - sgn * 3, p[1]) for p in pts_o[::-1]], _lerp(light, (255, 255, 255), 0.4))
        cv.lines(poly + [poly[0]], _lerp(dark, (0, 0, 0), 0.5), 1.6)


def _gear(cv, c, r, teeth, col, hole=0.35):
    dk = _lerp(col, (0, 0, 0), 0.45)
    pts = []
    for i in range(teeth * 4):
        a = i * math.tau / (teeth * 4)
        rr = r if (i % 4) in (0, 1) else r * 0.82
        pts.append((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr))
    cv.poly(pts, col)
    cv.poly(pts, dk, 1.6)
    cv.circle(c, r * 0.62, _lerp(col, (255, 255, 255), 0.2))
    cv.circle(c, r * 0.62, dk, 1.4)
    cv.circle(c, r * hole, dk)
    cv.circle(c, r * hole * 0.55, _lerp(col, (255, 255, 255), 0.4))


def _gears(cv, art):
    col = _lerp(art["mat"][1], (255, 226, 150), 0.25)
    _gear(cv, (CX - 62, HY - 44), 30, 10, col)
    _gear(cv, (CX + 62, HY - 44), 24, 8, _lerp(col, (200, 150, 70), 0.3))
    _gear(cv, (CX, HY + 62), 22, 8, _lerp(col, (255, 240, 190), 0.2))


def _tendrils(cv, art):
    g = art.get("glow") or (60, 224, 232)
    base = _lerp(art["mat"][2], art["mat"][1], 0.4)
    for side in (-1, 1):
        for k in range(2):
            pts = []
            for i in range(26):
                t = i / 25
                x = CX + side * (14 + 74 * t + 10 * math.sin(t * 7 + k * 2))
                y = HY + 24 + k * 14 + 98 * t - 28 * math.sin(t * 3.1)
                pts.append((x, y, 8.5 * (1 - t) + 1.2))
            for x, y, r in pts:
                cv.circle((x, y), r, base)
            for x, y, r in pts[::2]:
                cv.circle((x - r * 0.25, y - r * 0.3), r * 0.4, _lerp(base, (255, 255, 255), 0.35))
            for i in range(4, 24, 5):
                x, y, r = pts[i]
                cv.glow((x, y + r * 0.4), 8, g, 150, 6)
                cv.circle((x, y + r * 0.4), 1.8, _lerp(g, (255, 255, 255), 0.7))


def _infinity(cv, art):
    g = art.get("glow") or (190, 150, 255)
    pts = []
    for i in range(90):
        t = i * math.tau / 90
        d = 1 + math.sin(t) ** 2
        pts.append((CX + 120 * math.cos(t) / d, HY - 8 + 70 * math.sin(t) * math.cos(t) / d))
    for x, y in pts[::6]:
        cv.glow((x, y), 12, g, 140, 6)
    cv.lines(pts + [pts[0]], _lerp(g, (0, 0, 0), 0.3), 5.5)
    cv.lines(pts + [pts[0]], g, 3.4)
    cv.lines(pts + [pts[0]], (255, 255, 255), 1.3)


def _elements(cv, blades):
    orbs = [((255, 104, 40), 0.55, 0), ((70, 160, 255), 0.55, 1), ((116, 206, 92), 0.82, 0), ((238, 244, 255), 0.82, 1)]
    for col, tf, bi in orbs:
        U, L = blades[bi % len(blades)]
        n = len(U)
        i = int(n * tf)
        x, y = _mid(U, L, i, 0.5)
        cv.glow((x, y), 18, col, 170, 8)
        cv.circle((x, y), 7, _lerp(col, (0, 0, 0), 0.35))
        cv.circle((x, y), 6, col)
        cv.circle((x - 2, y - 2.5), 2.2, (255, 255, 255))
        cv.circle((x, y), 7, _lerp(col, (0, 0, 0), 0.6), 1.2)
    # le deuxième jeu d'orbes sur l'autre lame
    for col, tf in (((255, 104, 40), 0.82), ((70, 160, 255), 0.82)):
        U, L = blades[1] if len(blades) > 1 else blades[0]
        x, y = _mid(U, L, int(len(U) * tf), 0.5)
        cv.glow((x, y), 16, col, 150, 8)
        cv.circle((x, y), 6, col)
        cv.circle((x - 2, y - 2), 2, (255, 255, 255))


def _astrolabe(cv, art):
    gold = (240, 204, 110)
    dk = (140, 100, 34)
    for k, (w, h, a0) in enumerate(((236, 86, 0.0), (190, 140, 0.0), (140, 190, 0.0))):
        rect = (CX - w / 2, HY - h / 2 - 6, w, h)
        cv.ellipse(rect, dk, 4.4)
        cv.ellipse(rect, gold, 2.8)
        cv.ellipse((rect[0] + 1.5, rect[1] + 1.5, rect[2] - 3, rect[3] - 3), (255, 244, 190), 0.9)
        for i in range(16):
            ang = i * math.tau / 16 + k * 0.2
            x = CX + math.cos(ang) * w / 2
            y = HY - 6 + math.sin(ang) * h / 2
            cv.circle((x, y), 2.2 if i % 4 else 3.6, (255, 250, 220))
    for ang in (0.8, 2.6, 4.4):
        x = CX + math.cos(ang) * 118
        y = HY - 6 + math.sin(ang) * 43
        cv.glow((x, y), 14, (255, 240, 180), 170, 6)
        cv.circle((x, y), 4.5, (255, 255, 240))


# ----------------------------------------------------------------------
def build_base(art):
    cv = _Cv()
    rng = random.Random(art["name"])
    mat = art["mat"]
    deco = art["deco"]
    glow = art.get("glow")
    kind = art["head"]

    if glow:
        cv.glow((CX, HY), 118, glow, 150, 14)
    if "corona" in deco:
        _corona(cv, glow or mat[1])
    if "eclipse" in deco:
        _eclipse(cv, art)
    if "feathers" in deco or "firewings" in deco:
        _feathers(cv, mat, art)
    if "vortex" in deco:
        _vortex(cv, glow or mat[1])
    if "gears" in deco:
        _gears(cv, art)
    if "tendrils" in deco:
        _tendrils(cv, art)
    if "infinity" in deco:
        _infinity(cv, art)
    if "astrolabe" in deco:
        _astrolabe(cv, art)

    _handle(cv, art)

    if kind == "flint":
        blades = _head_flint(cv, art, mat, rng)
    elif kind == "winged":
        blades = _head_winged(cv, art, mat, rng)
    else:
        blades = _head_generic(cv, art, mat, rng, kind)

    for U, L in blades:
        _decor_blade(cv, U, L, art, mat, rng)
    if "speckle" in deco and kind == "flint":
        pass

    if "horns" in deco:
        _horns(cv, blades, mat)
    if "ice" in deco:
        _ice(cv, art, blades, rng)
    if "spikes" in deco:
        _spikes(cv, blades, mat)
    if "bolt" in deco:
        _bolt(cv, art, blades, rng)

    _hub(cv, art, mat)
    if kind == "crystal":
        _crystal_shards(cv, art)
    if "rivets" in deco and "rope" not in deco:
        for dx in (-11, 11):
            cv.circle((CX + dx, HY - 12), 2.2, _lerp(mat[2], (0, 0, 0), 0.4))
            cv.circle((CX + dx - 0.4, HY - 12.4), 1.4, mat[3])
            cv.circle((CX + dx, HY + 16), 2.2, _lerp(mat[2], (0, 0, 0), 0.4))
            cv.circle((CX + dx - 0.4, HY + 15.6), 1.4, mat[3])
    if "elements" in deco:
        _elements(cv, blades)
    if "flames" in deco:
        _flames(cv, art, blades)
    if "eye" in deco:
        _eye(cv, art)
    elif art.get("gem"):
        _gem(cv, art["gem"], big=kind in ("crystal", "winged"))
    if "stars" in deco:
        _stars(cv, blades, art, rng)
    if "halo" in deco:
        _halo(cv, art)

    return pygame.transform.smoothscale(cv.s, (CW, CH))


def get_base(tier):
    if tier not in _BASE_CACHE:
        _BASE_CACHE[tier] = build_base(config.TOOL_TIERS[tier]["art"])
    return _BASE_CACHE[tier]


def get_scaled(tier, f):
    key = (tier, round(f, 3))
    if key not in _SCALED_CACHE:
        base = get_base(tier)
        _SCALED_CACHE[key] = pygame.transform.smoothscale(base, (max(2, int(CW * f)), max(2, int(CH * f))))
        if len(_SCALED_CACHE) > 160:
            _SCALED_CACHE.pop(next(iter(_SCALED_CACHE)))
    return _SCALED_CACHE[key]


# ----------------------------------------------------------------------
# EFFETS ANIMÉS
# ----------------------------------------------------------------------
def _star_pts(c, r, thin=0.3):
    pts = []
    for i in range(8):
        a = i * math.pi / 4 - math.pi / 2
        rr = r if i % 2 == 0 else r * thin
        pts.append((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr))
    return pts


def draw_fx(screen, art, head, f, t):
    fx = art.get("fx")
    if not fx:
        return
    R = int(120 * f * 3.3) + 20
    surf = pygame.Surface((R * 2, R * 2), pygame.SRCALPHA)
    c = (R, R)
    g = art.get("glow") or (255, 255, 255)
    sc = max(0.5, f * 3.2)
    if fx == "sparkle":
        for i in range(6):
            a = t * 1.3 + i * math.tau / 6
            r = (60 + 14 * math.sin(t * 2 + i)) * f * 3.0
            p = (c[0] + math.cos(a) * r, c[1] + math.sin(a) * r * 0.65)
            al = int(120 + 120 * math.sin(t * 4 + i * 1.7))
            pygame.draw.polygon(surf, (*_lerp(g, (255, 255, 255), 0.6), max(0, min(255, al))), _star_pts(p, 4.5 * sc))
    elif fx == "embers":
        for i in range(9):
            ph = (t * 0.7 + i / 9) % 1.0
            x = c[0] + ((i * 37) % 90 - 45) * f * 3.0 + math.sin(t * 3 + i) * 5 * sc
            y = c[1] - ph * 105 * f * 3.0
            col = _lerp((255, 220, 90), (230, 50, 20), ph)
            pygame.draw.circle(surf, (*col, int(230 * (1 - ph))), (int(x), int(y)), max(1, int(3.2 * sc * (1 - ph * 0.6))))
    elif fx == "frost":
        for i in range(9):
            ph = (t * 0.45 + i / 9) % 1.0
            x = c[0] + ((i * 53) % 130 - 65) * f * 3.0 + math.sin(t * 2 + i) * 6 * sc
            y = c[1] - 50 * f * 3.0 + ph * 130 * f * 3.0
            pygame.draw.circle(surf, (235, 250, 255, int(220 * math.sin(ph * math.pi))), (int(x), int(y)), max(1, int(2.6 * sc)))
    elif fx == "bolt":
        if math.sin(t * 6.3) > 0.55:
            ang = (int(t * 6.3) * 2.399) % math.tau
            pts = [c]
            x, y = c
            for k in range(5):
                ang += math.sin(t * 40 + k) * 0.7
                x += math.cos(ang) * 22 * sc
                y += math.sin(ang) * 22 * sc
                pts.append((x, y))
            pygame.draw.lines(surf, (*g, 220), False, pts, max(2, int(3 * sc)))
            pygame.draw.lines(surf, (255, 255, 255, 255), False, pts, max(1, int(1.4 * sc)))
    elif fx == "void":
        for i in range(8):
            ph = (t * 0.5 + i / 8) % 1.0
            a = i * 0.9 + t * 1.6
            r = (1 - ph) * 70 * f * 3.0 + 6
            p = (c[0] + math.cos(a) * r, c[1] + math.sin(a) * r * 0.8)
            pygame.draw.circle(surf, (*_lerp(g, (20, 0, 40), 0.5), int(220 * math.sin(ph * math.pi))), (int(p[0]), int(p[1])), max(1, int(3.4 * sc)))
    elif fx == "stars":
        for i in range(7):
            a = -t * 0.9 + i * math.tau / 7
            r = (62 + 16 * math.sin(t * 1.5 + i * 2)) * f * 3.0
            p = (c[0] + math.cos(a) * r, c[1] + math.sin(a) * r * 0.7)
            al = int(130 + 120 * math.sin(t * 3 + i))
            pygame.draw.polygon(surf, (255, 246, 200, max(0, min(255, al))), _star_pts(p, 5 * sc))
    elif fx == "bubbles":
        for i in range(8):
            ph = (t * 0.4 + i / 8) % 1.0
            x = c[0] + ((i * 47) % 100 - 50) * f * 3.0 + math.sin(t * 2 + i * 1.3) * 6 * sc
            y = c[1] + 40 * f * 3.0 - ph * 150 * f * 3.0
            r = max(2, int((3 + (i % 3) * 1.6) * sc))
            pygame.draw.circle(surf, (180, 255, 250, int(190 * math.sin(ph * math.pi))), (int(x), int(y)), r, 1)
            pygame.draw.circle(surf, (255, 255, 255, int(150 * math.sin(ph * math.pi))), (int(x - r * 0.3), int(y - r * 0.3)), max(1, r // 3))
    elif fx == "rainbow":
        for i in range(14):
            a = t * 1.1 + i * math.tau / 14
            r = 70 * f * 3.0
            p = (c[0] + math.cos(a) * r, c[1] + math.sin(a) * r * 0.55 - 26 * f * 3.0)
            pygame.draw.circle(surf, (*_hsv(t * 0.3 + i / 14, 0.5, 1.0), 200), (int(p[0]), int(p[1])), max(1, int(3.2 * sc)))
    screen.blit(surf, (head[0] - R, head[1] - R))
