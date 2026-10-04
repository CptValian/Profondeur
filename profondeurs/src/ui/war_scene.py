"""
Bataille en direct : on regarde la vraie simulation (battle_sim.BattleSim) se dérouler.
Les troupes de l'attaquant (gauche) marchent sur la ligne vers celles du défenseur (droite),
chaque unité vise l'ennemi le plus proche, frappe au corps à corps ou tire ses flèches ;
le donjon d'archer du défenseur, tout à l'arrière, arrose les attaquants de salves.
Le résultat affiché est celui qui sera appliqué (pertes, butin, vainqueur).
"""

import math
import random
import pygame

from src.items import crafting
from src.combat.battle_sim import LAVA_X0, LAVA_X1

RANGED = {"crystal_archer", "crystal_turret", "star_bastion"}

# rid -> (type de sprite, couleur, taille, arme)
SPRITES = {
    "militia":        ("man",     (196, 150, 100), 1.0,  "pick"),
    "pikeman":        ("man",     (180, 186, 198), 1.05, "spear"),
    "crystal_archer": ("man",     (120, 205, 235), 1.0,  "bow"),
    "golem":          ("giant",   (150, 140, 128), 1.5,  "fist"),
    "rune_knight":    ("man",     (125, 165, 255), 1.25, "sword"),
    "abyss_stalker":  ("man",     (175, 95, 240),  1.25, "blade"),
    "star_guardian":  ("giant",   (255, 232, 150), 1.7,  "sword"),
}


def _lerp(c1, c2, t):
    return tuple(max(0, min(255, int(c1[i] + (c2[i] - c1[i]) * t))) for i in range(3))


def _sprite(kind, color, size, weapon, phase, swing, flash, shoot=0.0):
    """Dessine un personnage / une structure tourné vers la DROITE sur une surface 96x96."""
    S = 96
    surf = pygame.Surface((S, S), pygame.SRCALPHA)
    fx, fy = S // 2, S - 8
    s = size
    col = _lerp(color, (255, 255, 255), flash * 0.75)
    dark = _lerp(col, (0, 0, 0), 0.45)
    steel = _lerp((200, 205, 215), (255, 255, 255), flash)
    skin = _lerp((240, 205, 165), (255, 255, 255), flash)

    if kind in ("man", "giant"):
        step = math.sin(phase) * 3 * s
        if kind == "man":
            hip = (fx, fy - 12 * s)
            sh = (fx, fy - 26 * s)
            w = max(2, int(2 * s))
            pygame.draw.line(surf, dark, hip, (fx - 5 * s + step, fy), w)
            pygame.draw.line(surf, dark, hip, (fx + 5 * s - step, fy), w)
            pygame.draw.line(surf, col, hip, sh, max(3, int(4 * s)))
            pygame.draw.circle(surf, skin, (fx, int(sh[1] - 6 * s)), int(5.5 * s))
            pygame.draw.arc(surf, dark, (fx - 6 * s, sh[1] - 13 * s, 12 * s, 10 * s), 0.2, math.pi - 0.2, 2)
        else:
            sh = (fx, fy - 34 * s / 1.5 * 1.0)
            pygame.draw.rect(surf, dark, (fx - 7 * s + step, fy - 12 * s, 5 * s, 12 * s))
            pygame.draw.rect(surf, dark, (fx + 2 * s - step, fy - 12 * s, 5 * s, 12 * s))
            pygame.draw.rect(surf, col, (fx - 8 * s, fy - 30 * s, 16 * s, 20 * s), border_radius=int(3 * s))
            pygame.draw.rect(surf, skin, (fx - 4.5 * s, fy - 38 * s, 9 * s, 9 * s), border_radius=int(2 * s))
            sh = (fx, fy - 26 * s)
        hand = (fx + 8 * s, sh[1] + 4 * s)
        a = -1.1 + swing * 1.9 if weapon != "bow" else -0.1
        if weapon == "pick":
            tip = (hand[0] + math.cos(a) * 14 * s, hand[1] + math.sin(a) * 14 * s)
            pygame.draw.line(surf, (110, 80, 50), hand, tip, 3)
            pygame.draw.line(surf, steel, (tip[0] - 4 * s, tip[1] - 3 * s), (tip[0] + 4 * s, tip[1] + 3 * s), 3)
        elif weapon == "spear":
            a = -0.35 + swing * 0.35
            tip = (hand[0] + math.cos(a) * 28 * s, hand[1] + math.sin(a) * 28 * s)
            pygame.draw.line(surf, (110, 80, 50), (hand[0] - 6 * s, hand[1]), tip, 2)
            pygame.draw.polygon(surf, steel, [tip, (tip[0] - 6 * s, tip[1] - 2 * s), (tip[0] - 6 * s, tip[1] + 2 * s)])
        elif weapon in ("sword", "blade"):
            tip = (hand[0] + math.cos(a) * 20 * s, hand[1] + math.sin(a) * 20 * s)
            pygame.draw.line(surf, _lerp(steel, color, 0.35), hand, tip, 3 if weapon == "sword" else 2)
            pygame.draw.circle(surf, _lerp(color, (255, 255, 255), 0.5), (int(tip[0]), int(tip[1])), 2)
        elif weapon == "bow":
            bx = hand[0] + 3 * s
            pygame.draw.arc(surf, (140, 100, 60), (bx - 7 * s, hand[1] - 11 * s, 14 * s, 22 * s), -1.3, 1.3, 2)
            pygame.draw.line(surf, (230, 230, 230), (bx + 4 * s - shoot * 5 * s, hand[1]),
                             (bx + 1.5 * s, hand[1] - 10 * s), 1)
            pygame.draw.line(surf, (230, 230, 230), (bx + 4 * s - shoot * 5 * s, hand[1]),
                             (bx + 1.5 * s, hand[1] + 10 * s), 1)
        elif weapon == "fist":
            pygame.draw.circle(surf, skin, (int(hand[0] + swing * 8 * s), int(hand[1])), int(4 * s))
    elif kind == "wall":
        for dx in (-9, 0, 9):
            x = fx + dx * s
            pygame.draw.polygon(surf, col, [(x - 4 * s, fy), (x + 4 * s, fy), (x, fy - 26 * s)])
            pygame.draw.polygon(surf, dark, [(x - 4 * s, fy), (x + 4 * s, fy), (x, fy - 26 * s)], 1)
        pygame.draw.line(surf, dark, (fx - 13 * s, fy - 9 * s), (fx + 13 * s, fy - 9 * s), 3)
    elif kind == "gate":
        r = pygame.Rect(fx - 9 * s, fy - 30 * s, 18 * s, 30 * s)
        pygame.draw.rect(surf, col, r, border_radius=3)
        for i in range(1, 4):
            x = r.x + i * r.w / 4
            pygame.draw.line(surf, dark, (x, r.y + 2), (x, r.bottom), 2)
        pygame.draw.line(surf, dark, (r.x, r.y + r.h * 0.5), (r.right, r.y + r.h * 0.5), 2)
        pygame.draw.rect(surf, dark, r, 2, border_radius=3)
    elif kind == "turret":
        pygame.draw.rect(surf, col, (fx - 9 * s, fy - 16 * s, 18 * s, 16 * s))
        pygame.draw.circle(surf, dark, (fx, int(fy - 18 * s)), int(7 * s))
        pygame.draw.circle(surf, col, (fx, int(fy - 18 * s)), int(5 * s))
        L = (16 - shoot * 4) * s
        pygame.draw.line(surf, steel, (fx, fy - 18 * s), (fx + L * 0.95, fy - 18 * s - L * 0.3), 4)
    elif kind == "totem":
        pygame.draw.rect(surf, dark, (fx - 6 * s, fy - 40 * s, 12 * s, 40 * s), border_radius=2)
        glow = pygame.Surface((S, S), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*col, 90), (fx, int(fy - 28 * s)), int(9 * s))
        surf.blit(glow, (0, 0))
        pygame.draw.circle(surf, col, (fx, int(fy - 28 * s)), int(4.5 * s))
        pygame.draw.circle(surf, col, (fx, int(fy - 12 * s)), int(3 * s))
    elif kind == "bastion":
        pygame.draw.rect(surf, col, (fx - 14 * s, fy - 24 * s, 28 * s, 24 * s))
        for i in range(3):
            pygame.draw.rect(surf, col, (fx - 14 * s + i * 11 * s, fy - 30 * s, 6 * s, 6 * s))
        pygame.draw.rect(surf, dark, (fx - 5 * s, fy - 14 * s, 10 * s, 14 * s), border_top_left_radius=int(5 * s),
                         border_top_right_radius=int(5 * s))
        pygame.draw.rect(surf, dark, (fx - 14 * s, fy - 24 * s, 28 * s, 24 * s), 2)
        L = (14 - shoot * 4) * s
        pygame.draw.line(surf, steel, (fx + 4 * s, fy - 34 * s), (fx + 4 * s + L, fy - 34 * s - L * 0.25), 4)
    return surf


SC = 1.5    # agrandissement des sprites à l'écran

_TOWER_CACHE = {}


def _tower_sprite(flash=0.0, ruined=False):
    key = (round(flash, 1), ruined)
    if key in _TOWER_CACHE:
        return _TOWER_CACHE[key]
    W, H = 150, 230
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx, base = W // 2, H - 6
    stone = _lerp((128, 120, 118), (255, 255, 255), flash * 0.7)
    dark = _lerp(stone, (0, 0, 0), 0.4)
    light = _lerp(stone, (255, 255, 255), 0.25)
    if ruined:
        for i, (dx, h, w) in enumerate(((-34, 26, 30), (-6, 40, 34), (24, 22, 28), (4, 14, 40))):
            pygame.draw.polygon(surf, dark, [(cx + dx - w // 2, base), (cx + dx - w // 3, base - h), (cx + dx + w // 3, base - h + 6), (cx + dx + w // 2, base)])
        _TOWER_CACHE[key] = surf
        return surf
    # fût
    body = [(cx - 40, base), (cx - 30, 70), (cx + 30, 70), (cx + 40, base)]
    pygame.draw.polygon(surf, stone, body)
    pygame.draw.polygon(surf, light, [(cx - 40, base), (cx - 30, 70), (cx - 8, 70), (cx - 14, base)])
    pygame.draw.polygon(surf, dark, [(cx + 14, base), (cx + 8, 70), (cx + 30, 70), (cx + 40, base)])
    for row in range(8):                                  # joints de pierre
        y = 80 + row * 19
        pygame.draw.line(surf, dark, (cx - 36 + row * 0.6, y), (cx + 36 - row * 0.6, y), 1)
        for k in range(3):
            xo = -22 + k * 22 + (row % 2) * 11
            pygame.draw.line(surf, dark, (cx + xo, y), (cx + xo, y + 19), 1)
    pygame.draw.polygon(surf, dark, body, 3)
    # meurtrières et porte
    for y in (95, 130):
        pygame.draw.rect(surf, (20, 14, 14), (cx - 3, y, 6, 20))
    pygame.draw.rect(surf, (52, 34, 24), (cx - 11, base - 36, 22, 36), border_top_left_radius=11, border_top_right_radius=11)
    pygame.draw.rect(surf, dark, (cx - 11, base - 36, 22, 36), 2, border_top_left_radius=11, border_top_right_radius=11)
    # plate-forme crénelée
    pygame.draw.rect(surf, stone, (cx - 42, 52, 84, 22))
    pygame.draw.rect(surf, dark, (cx - 42, 52, 84, 22), 2)
    for k in range(5):
        pygame.draw.rect(surf, stone, (cx - 42 + k * 20, 38, 12, 16))
        pygame.draw.rect(surf, dark, (cx - 42 + k * 20, 38, 12, 16), 2)
    # petit toit et drapeau
    pygame.draw.polygon(surf, (150, 52, 44), [(cx - 22, 40), (cx, 6), (cx + 22, 40)])
    pygame.draw.polygon(surf, (110, 34, 30), [(cx, 6), (cx + 22, 40), (cx, 40)])
    pygame.draw.line(surf, (60, 50, 40), (cx, 6), (cx, -2), 2)
    pygame.draw.polygon(surf, (230, 190, 80), [(cx, -2), (cx + 16, 3), (cx, 8)])
    # archers sur la plate-forme
    for dx in (-26, 0, 26):
        pygame.draw.circle(surf, (230, 200, 160), (cx + dx, 44), 4)
        pygame.draw.line(surf, (120, 90, 60), (cx + dx, 48), (cx + dx, 56), 3)
        pygame.draw.arc(surf, (170, 130, 80), (cx + dx + 1, 40, 12, 18), -1.3, 1.3, 2)
    _TOWER_CACHE[key] = surf
    return surf


class WarScene:
    STEP = 1.0 / 30.0

    def __init__(self, sim, att_label, def_label, att_color, def_color, player_role="att"):
        self.role = player_role   # "att" : tu attaques ; "def" : tu es attaqué
        self.sim = sim
        self.att_label, self.def_label = att_label, def_label
        self.att_color, self.def_color = att_color, def_color
        self.speed = 1.0
        self.acc = 0.0
        self.sparks = []
        self.report = None
        self.skip_rect = self.close_rect = None
        self.speed_rects = {}
        self.rng = random.Random(5)
        self.att_hp0 = max(1.0, sum(u.max_hp for u in sim.units if u.side == "att"))
        self.def_hp0 = max(1.0, sum(u.max_hp for u in sim.units if u.side == "def"))

    @property
    def finished(self):
        return self.sim.finished

    # ------------------------------------------------------------------
    def update(self, dt):
        sim = self.sim
        if sim.finished:
            self._decay(dt)
            return
        self.acc += dt * self.speed
        n = 0
        while self.acc >= self.STEP and not sim.finished and n < 16:
            sim.step(self.STEP)
            self.acc -= self.STEP
            n += 1
        self.acc = min(self.acc, self.STEP * 4)
        for ev in sim.events:
            self.sparks.append({"x": ev[1], "side": ev[2], "t0": sim.time, "vx": self.rng.uniform(-60, 60),
                                "vy": self.rng.uniform(-100, -20)})
        sim.events.clear()
        self._decay(dt)

    def _decay(self, dt):
        self.sparks = [p for p in self.sparks if self.sim.time - p["t0"] < 0.35 or self.sim.finished and False]
        if len(self.sparks) > 160:
            self.sparks = self.sparks[-160:]

    def skip(self):
        self.sim.record = False
        self.sim.run(0.05)
        self.sim.events.clear()
        self.sparks.clear()

    def handle_click(self, pos) -> bool:
        for sp, r in self.speed_rects.items():
            if r.collidepoint(pos):
                self.speed = sp
                return False
        if not self.finished and self.skip_rect and self.skip_rect.collidepoint(pos):
            self.skip()
        elif self.finished and self.close_rect and self.close_rect.collidepoint(pos):
            return True
        return False

    def handle_key(self, key) -> bool:
        if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
            if not self.finished:
                self.skip()
            else:
                return True
        elif key == pygame.K_1:
            self.speed = 1.0
        elif key == pygame.K_2:
            self.speed = 2.0
        elif key == pygame.K_3:
            self.speed = 4.0
        return False

    # ------------------------------------------------------------------
    def draw(self, rd):
        scr, sim = rd.screen, self.sim
        rect = rd._combat_modal_rect()
        pygame.draw.rect(scr, (24, 16, 20), rect, border_radius=12)
        pygame.draw.rect(scr, (200, 120, 70), rect, 3, border_radius=12)
        head_txt = f"Assaut sur {self.def_label}" if self.role == "att" else f"{self.att_label} t'attaque !"
        title = rd.font_big.render(head_txt, True, (255, 225, 190))
        scr.blit(title, (rect.x + 20, rect.y + 12))
        it = rd.font_small.render(f"{sim.time:4.0f} s", True, (230, 200, 170))
        scr.blit(it, (rect.right - it.get_width() - 20, rect.y + 20))

        # barres de force (somme des PV restants de chaque camp)
        bar_w = (rect.w - 60) // 2 - 20
        att_hp = sum(max(0.0, u.hp) for u in sim.units if u.side == "att")
        def_hp = sum(max(0.0, u.hp) for u in sim.units if u.side == "def")
        for side, bx, label, color, ratio in (
                ("att", rect.x + 20, self.att_label, self.att_color, att_hp / self.att_hp0),
                ("def", rect.right - 20 - bar_w, self.def_label, self.def_color, def_hp / self.def_hp0)):
            by = rect.y + 58
            pygame.draw.rect(scr, (40, 20, 20), (bx, by, bar_w, 14), border_radius=5)
            fw = int(bar_w * max(0.0, min(1.0, ratio)))
            fx = bx if side == "att" else bx + bar_w - fw
            pygame.draw.rect(scr, color, (fx, by, fw, 14), border_radius=5)
            pygame.draw.rect(scr, (235, 235, 235), (bx, by, bar_w, 14), 1, border_radius=5)
            lt = rd.font_tiny.render(label, True, (235, 230, 220))
            scr.blit(lt, (bx if side == "att" else bx + bar_w - lt.get_width(), by - 16))

        arena = pygame.Rect(rect.x + 20, rect.y + 92, rect.w - 40, rect.h - 92 - 84)
        for i in range(0, arena.h, 6):
            pygame.draw.rect(scr, _lerp((22, 14, 22), (50, 30, 30), i / arena.h), (arena.x, arena.y + i, arena.w, 6))
        line_y = arena.bottom - 44
        pygame.draw.rect(scr, (30, 22, 20), (arena.x, line_y, arena.w, arena.bottom - line_y))
        pygame.draw.line(scr, (210, 170, 120), (arena.x, line_y), (arena.right, line_y), 3)
        pygame.draw.rect(scr, (110, 70, 60), arena, 2, border_radius=8)

        def sx(x):
            return arena.x + 24 + x / 1000.0 * (arena.w - 48)

        scr.set_clip(arena)
        t = sim.time
        # lac de lave (amélioration suprême 2)
        if sim.supreme >= 2:
            lx0, lx1 = int(sx(LAVA_X0)), int(sx(LAVA_X1))
            lava = pygame.Rect(lx0, line_y - 4, lx1 - lx0, arena.bottom - line_y + 4)
            pygame.draw.rect(scr, (120, 30, 10), lava)
            for i in range(0, lava.w, 10):
                h = 4 + int(3 * math.sin(t * 3 + i * 0.3))
                pygame.draw.rect(scr, (255, 130 + int(60 * math.sin(t * 2 + i)), 30), (lava.x + i, lava.y + 4 - h, 8, h + 6))
            pygame.draw.rect(scr, (255, 110, 40), lava, 2)
        # donjon d'archer : à l'arrière-plan (assombri par la distance)
        tw = sim.tower
        flash = max(0.0, 1.0 - (t - tw.hurt_t) / 0.25)
        tsp = _tower_sprite(flash, ruined=not tw.alive)
        k = 1.05
        tsp = pygame.transform.smoothscale(tsp, (int(tsp.get_width() * k), int(tsp.get_height() * k)))
        tx = sx(tw.x)
        scr.blit(tsp, (tx - tsp.get_width() // 2, line_y - tsp.get_height() + 6))
        if tw.alive:
            bw = 64
            by = line_y - tsp.get_height() - 8
            pygame.draw.rect(scr, (50, 20, 20), (tx - bw // 2, by, bw, 6))
            pygame.draw.rect(scr, (220, 90, 70), (tx - bw // 2, by, int(bw * max(0, tw.hp) / tw.max_hp), 6))
            pygame.draw.rect(scr, (240, 240, 240), (tx - bw // 2, by, bw, 6), 1)
        tower_top = (tx, line_y - tsp.get_height() + 34)

        # unités
        order = sorted((u for u in sim.units if not u.is_tower and (u.alive or t - u.dead_t < 0.9)),
                       key=lambda u: (u.lane, u.x))
        for u in order:
            kind, color, size, weapon = SPRITES[u.rid]
            since = t - u.attack_t
            swing = shoot = 0.0
            if since < 0.3 and u.alive:
                v = math.sin(math.pi * since / 0.3)
                if u.ranged:
                    shoot = v
                else:
                    swing = v
            phase = t * 10 + u.uid if u.state == "move" else t * 2 + u.uid
            fl = max(0.0, 1.0 - (t - u.hurt_t) / 0.2) if u.alive else 0.0
            spr = _sprite(kind, color, size, weapon, phase, swing, fl, shoot)
            spr = pygame.transform.smoothscale(spr, (int(96 * SC), int(96 * SC)))
            if u.side == "def":
                spr = pygame.transform.flip(spr, True, False)
            y = line_y + 2 + u.lane * 5
            x = sx(u.x)
            if not u.alive:
                prog = min(1.0, (t - u.dead_t) / 0.9)
                spr.set_alpha(int(255 * (1 - prog)))
                y += prog * 12
            elif swing:
                x += swing * 7 * (1 if u.side == "att" else -1)
            scr.blit(spr, (x - 48 * SC, y - 88 * SC))
            if u.alive and u.burn_t > 0:       # brûlure : petites flammes au-dessus de l'unité
                for k in range(2):
                    fx_ = x + math.sin(t * 12 + u.uid + k * 2) * 6
                    fy_ = y - 88 * SC + 30 - k * 7 - abs(math.sin(t * 9 + k)) * 4
                    pygame.draw.circle(scr, (255, 150 - 60 * k, 40), (int(fx_), int(fy_)), 4 - k)
            if u.alive and u.hp < u.max_hp:
                bw = 22
                pygame.draw.rect(scr, (50, 20, 20), (x - bw // 2, y - 88 * SC + 26, bw, 3))
                pygame.draw.rect(scr, (110, 220, 110), (x - bw // 2, y - 88 * SC + 26, int(bw * u.hp / u.max_hp), 3))

        # flèches (projectiles réels de la simulation)
        for p in sim.projectiles:
            if p.t < 0:
                continue
            u_ = max(0.0, min(1.0, p.t / p.dur))
            x0, x1 = sx(p.src_x), sx(p.target.x)
            y0 = arena.y + 4 if p.rain else (tower_top[1] if p.tower else line_y - 34)
            y1 = line_y - 26

            def pos(uu):
                return (x0 + (x1 - x0) * uu, y0 + (y1 - y0) * uu - math.sin(math.pi * uu) * p.arc * 0.8)

            a, b = pos(u_), pos(max(0.0, u_ - 0.06))
            col = (255, 150, 60) if p.fire else ((255, 232, 160) if p.tower else (150, 215, 240))
            pygame.draw.line(scr, col, b, a, 2)
            pygame.draw.circle(scr, (255, 255, 255), (int(a[0]), int(a[1])), 2)
        # étincelles d'impact
        for sp_ in self.sparks:
            age = t - sp_["t0"]
            if age < 0:
                continue
            x = sx(sp_["x"]) + sp_["vx"] * age
            y = line_y - 24 + sp_["vy"] * age + 300 * age * age
            pygame.draw.circle(scr, (255, 220 - int(150 * age), 120), (int(x), int(y)), max(1, int(3 * (1 - age / 0.35))))
        if sim.notice and t - sim.notice[1] < 1.8:
            nt = rd.font_big.render(sim.notice[0], True, (255, 190, 90))
            scr.blit(nt, (arena.centerx - nt.get_width() // 2, arena.y + 12))
        scr.set_clip(None)

        # bas de fenêtre
        self.skip_rect = self.close_rect = None
        self.speed_rects = {}
        if not self.finished:
            for i, sp in enumerate((1.0, 2.0, 4.0)):
                r = pygame.Rect(rect.x + 24 + i * 62, rect.bottom - 62, 54, 38)
                pygame.draw.rect(scr, (90, 70, 40) if self.speed == sp else (50, 46, 58), r, border_radius=8)
                pygame.draw.rect(scr, (255, 255, 255), r, 1, border_radius=8)
                tt = rd.font_small.render(f"x{int(sp)}", True, (255, 255, 255))
                scr.blit(tt, (r.centerx - tt.get_width() // 2, r.centery - tt.get_height() // 2))
                self.speed_rects[sp] = r
            hint = rd.font_tiny.render("Chaque unité vise l'ennemi le plus proche. Le donjon tire depuis l'arrière.", True, (190, 170, 150))
            scr.blit(hint, (rect.x + 24 + 3 * 62 + 10, rect.bottom - 50))
            self.skip_rect = pygame.Rect(rect.right - 170, rect.bottom - 62, 150, 42)
            pygame.draw.rect(scr, (70, 70, 85), self.skip_rect, border_radius=8)
            pygame.draw.rect(scr, (255, 255, 255), self.skip_rect, 1, border_radius=8)
            tt = rd.font_small.render("Passer (Espace)", True, (255, 255, 255))
            scr.blit(tt, (self.skip_rect.centerx - tt.get_width() // 2, self.skip_rect.centery - tt.get_height() // 2))
        else:
            good = sim.attacker_won if self.role == "att" else not sim.attacker_won
            if self.role == "att":
                label = "VICTOIRE !" if good else "DÉFAITE"
            else:
                label = "DÉFENSE RÉUSSIE !" if good else "DÉFENSE ÉCHOUÉE"
            ht = rd.font_huge.render(label, True, (150, 240, 160) if good else (240, 120, 110))
            ov = pygame.Surface((ht.get_width() + 60, ht.get_height() + 20), pygame.SRCALPHA)
            ov.fill((8, 6, 10, 190))
            ox, oy = arena.centerx - ov.get_width() // 2, arena.y + 40
            scr.blit(ov, (ox, oy))
            scr.blit(ht, (ox + 30, oy + 10))
            rep = self.report
            if rep:
                mine, theirs = ((rep.att_losses, rep.def_losses) if self.role == "att" else (rep.def_losses, rep.att_losses))
                txt = f"Pertes : {sum(mine.values())} chez toi, {sum(theirs.values())} chez l'ennemi"
                if rep.loot:
                    txt += f" · {'butin +' if self.role == 'att' else 'pillage -'}{int(rep.loot)} or"
                if rep.broken:
                    txt += f" · {rep.broken}"
            else:
                txt = ""
            tt = rd.font_small.render(txt, True, (235, 225, 210))
            scr.blit(tt, (rect.x + 24, rect.bottom - 52))
            self.close_rect = pygame.Rect(rect.right - 170, rect.bottom - 62, 150, 42)
            pygame.draw.rect(scr, (70, 130, 80), self.close_rect, border_radius=8)
            pygame.draw.rect(scr, (255, 255, 255), self.close_rect, 1, border_radius=8)
            tt = rd.font_small.render("Continuer", True, (255, 255, 255))
            scr.blit(tt, (self.close_rect.centerx - tt.get_width() // 2, self.close_rect.centery - tt.get_height() // 2))
