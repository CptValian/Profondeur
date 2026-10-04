"""
Rendu du jeu avec pygame — version "clicker" plein écran.

Structure de l'écran :
 - Panneau principal (gauche) : la galerie de mine, vue en coupe, avec
   une barre supérieure affichant la profondeur en gros.
 - Panneau latéral (droite) : dock à onglets (Outil / Pierres /
   Artefacts / Stats) avec de vrais boutons cliquables.
 - Fenêtres modales centrées : nommage d'une pierre, combat.

Les blocs et la pioche ont un rendu "travaillé" : texture de
mouchetures procédurale mise en cache par type de pierre (déterministe
via un seed), dégradé/bevel, fissures qui apparaissent au fur et à
mesure qu'un bloc est miné, halo lumineux pour les pioches de haut
niveau.
"""

import math
import random
import pygame
from src import config
from src.items import crafting
from src.ui import pickaxe_art
from src.items import tower as tower_mod


def _clamp(c):
    return max(0, min(255, int(c)))


def _shade(color, factor):
    return tuple(_clamp(c * factor) for c in color)


def _lerp_color(c1, c2, t):
    return tuple(_clamp(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _hsv_to_rgb(h, s=0.8, v=1.0):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


class Renderer:
    def __init__(self, screen, stone_registry, artifact_catalog):
        self.screen = screen
        self.stones = stone_registry
        self.artifacts = artifact_catalog
        self.W, self.H = screen.get_size()

        self.font_tiny = pygame.font.SysFont("georgia", 13)
        self.font_small = pygame.font.SysFont("georgia", 16)
        self.font = pygame.font.SysFont("georgia", 20)
        self.font_big = pygame.font.SysFont("georgia", 30, bold=True)
        self.font_huge = pygame.font.SysFont("georgia", 46, bold=True)

        # --- layout ---
        self.panel_w = config.RIGHT_PANEL_WIDTH
        self.main_w = self.W - self.panel_w
        self.top_bar_h = config.TOP_BAR_HEIGHT

        # taille de tuile adaptée à la largeur disponible
        self.tile = min(config.TILE_SIZE, (self.main_w - 60) // config.GRID_COLS)
        grid_pixel_w = self.tile * config.GRID_COLS
        self.grid_x = (self.main_w - grid_pixel_w) // 2
        self.grid_y = self.top_bar_h + 20
        self.visible_rows = max(6, (self.H - self.grid_y - 20) // self.tile)

        self._texture_cache = {}
        self._crack_cache = {}

        self.active_tab = "tool"   # tool | equip | stones | artifacts | competitors | workshop | stats
        self.active_workshop = "comp"   # comp | troops | tower | war
        self.war_info = {}
        self.rects = {}            # rects cliquables, recalculés à chaque frame utile
        self.scroll = {}           # défilement par onglet
        self.scroll_max = {}
        self._sc = None
        self.last_top_row = 0

    # ==================================================================
    # TEXTURES DE BLOC
    # ==================================================================
    def _get_texture(self, stone):
        if stone.stone_id in self._texture_cache:
            return self._texture_cache[stone.stone_id]
        size = self.tile
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        base = stone.base_color
        # dégradé diagonal léger
        for y in range(size):
            t = y / size
            row_color = _lerp_color(_shade(base, 1.12), _shade(base, 0.82), t)
            pygame.draw.line(surf, row_color, (0, y), (size, y))
        # mouchetures (grains de roche), déterministe via texture_seed
        rng = random.Random(stone.texture_seed)
        n_specks = size // 3
        for _ in range(n_specks):
            x = rng.randint(1, size - 2)
            y = rng.randint(1, size - 2)
            r = rng.choice([1, 1, 2])
            bright = rng.random() < 0.5
            c = _shade(base, 1.4 if bright else 0.6)
            pygame.draw.circle(surf, c, (x, y), r)
        # quelques veines fines
        for _ in range(rng.randint(1, 3)):
            x1, y1 = rng.randint(0, size), rng.randint(0, size)
            x2 = x1 + rng.randint(-size // 2, size // 2)
            y2 = y1 + rng.randint(-size // 2, size // 2)
            pygame.draw.line(surf, _shade(base, 1.5), (x1, y1), (x2, y2), 1)
        self._texture_cache[stone.stone_id] = surf
        return surf

    def _get_cracks(self, seed, level, size):
        """level 0..3 = intensité de fissures (0 = aucune)."""
        key = (seed, level, size)
        if key in self._crack_cache:
            return self._crack_cache[key]
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        if level > 0:
            rng = random.Random(seed * 7 + level)
            cx, cy = size / 2, size / 2
            n_lines = level * 2
            for _ in range(n_lines):
                ang = rng.uniform(0, math.pi * 2)
                length = rng.uniform(size * 0.2, size * 0.45)
                x2 = cx + math.cos(ang) * length
                y2 = cy + math.sin(ang) * length
                pygame.draw.line(surf, (10, 8, 8, 210), (cx, cy), (x2, y2), 2)
                # petite bifurcation
                if rng.random() < 0.6:
                    ang2 = ang + rng.uniform(-0.6, 0.6)
                    x3 = x2 + math.cos(ang2) * length * 0.4
                    y3 = y2 + math.sin(ang2) * length * 0.4
                    pygame.draw.line(surf, (10, 8, 8, 200), (x2, y2), (x3, y3), 1)
        self._crack_cache[key] = surf
        return surf

    # ==================================================================
    # FOND
    # ==================================================================
    def draw_background(self, camera_row, particle_system=None):
        # dégradé de couleur global selon la profondeur : chaud en surface,
        # froid/violet en profondeur, pour renforcer la sensation de descente.
        top_c, bot_c = self._depth_gradient_colors(camera_row)
        for y in range(0, self.H, 4):
            t = y / max(1, self.H)
            c = _lerp_color(top_c, bot_c, t)
            pygame.draw.rect(self.screen, c, (0, y, self.main_w, 4))

        # parois rocheuses en silhouette (parallaxe), mises en cache par
        # profondeur de bande pour ne pas régénérer le bruit à chaque frame
        for layer in range(config.PARALLAX_LAYERS):
            surf = self._get_wall_layer(layer, camera_row)
            offset = int((camera_row * (layer + 1) * 1.3) % surf.get_height())
            self.screen.blit(surf, (0, offset - surf.get_height()))
            self.screen.blit(surf, (0, offset))

        if particle_system:
            particle_system.draw_dust(self.screen)

        pygame.draw.rect(self.screen, (10, 8, 14), (0, 0, self.main_w, self.top_bar_h))

    def _depth_gradient_colors(self, camera_row):
        t = min(1.0, camera_row / 900.0)
        top_c = _lerp_color((46, 34, 30), (18, 16, 34), t)
        bot_c = _lerp_color((22, 16, 16), (8, 6, 18), t)
        return top_c, bot_c

    def _get_wall_layer(self, layer, camera_row):
        band = camera_row // 200  # les parois changent d'apparence tous les 200m
        key = (layer, band)
        if key in getattr(self, "_wall_cache", {}):
            return self._wall_cache[key]
        if not hasattr(self, "_wall_cache"):
            self._wall_cache = {}
        h = 320
        surf = pygame.Surface((self.main_w, h), pygame.SRCALPHA)
        rng = random.Random(f"wall-{layer}-{band}")
        base_shade = 20 + layer * 8
        tint = self._depth_gradient_colors(band * 200)[0]
        col_base = _lerp_color((base_shade, base_shade - 3, base_shade + 5), tint, 0.35)
        # bosses rocheuses (polygones irréguliers) en bas de la couche
        n_bumps = 10
        step = self.main_w / n_bumps
        points = [(0, h)]
        for i in range(n_bumps + 1):
            x = i * step
            y = h - rng.uniform(10, 70) * (1 + layer * 0.3)
            points.append((x, y))
        points.append((self.main_w, h))
        pygame.draw.polygon(surf, (*col_base, 90 - layer * 20), points)
        self._wall_cache[key] = surf
        return surf

    # ==================================================================
    # GALERIE DE MINE
    # ==================================================================
    def draw_grid(self, world_gen, player, hover_cell, mining_cell):
        top_row = max(0, player.row - 2)
        size = self.tile

        asc_limit = player.max_depth_reached - config.MAX_ASCENT
        if not hasattr(self, "_ascent_veil") or self._ascent_veil.get_size() != (size * config.GRID_COLS, size):
            self._ascent_veil = pygame.Surface((size * config.GRID_COLS, size), pygame.SRCALPHA)
            self._ascent_veil.fill((0, 0, 0, 150))

        for r_screen in range(self.visible_rows):
            row = top_row + r_screen
            y = self.grid_y + r_screen * size
            for col in range(config.GRID_COLS):
                x = self.grid_x + col * size
                block = world_gen.get_block(row, col)
                rect = pygame.Rect(x, y, size - 3, size - 3)

                if block.is_empty:
                    pygame.draw.rect(self.screen, (26, 22, 30), rect, border_radius=3)
                    pygame.draw.rect(self.screen, (14, 12, 16), rect, 1, border_radius=3)
                    continue

                stone = self.stones.get_by_id(block.stone_id)
                tex = self._get_texture(stone)
                shade_factor = max(0.4, 1 - r_screen * config.DEPTH_SHADE_STEP)
                shaded = tex.copy()
                dark_overlay = pygame.Surface(tex.get_size(), pygame.SRCALPHA)
                dark_overlay.fill((0, 0, 0, int((1 - shade_factor) * 180)))
                shaded.blit(dark_overlay, (0, 0))
                self.screen.blit(shaded, rect.topleft)

                # bevel
                light = _shade(stone.base_color, 1.5 * shade_factor)
                dark = _shade(stone.base_color, 0.4 * shade_factor)
                pygame.draw.line(self.screen, light, rect.topleft, rect.topright, 2)
                pygame.draw.line(self.screen, light, rect.topleft, rect.bottomleft, 2)
                pygame.draw.line(self.screen, dark, rect.bottomleft, rect.bottomright, 2)
                pygame.draw.line(self.screen, dark, rect.topright, rect.bottomright, 2)

                # fissures selon les dégâts déjà pris
                ratio = block.health_ratio
                if ratio < 0.85:
                    level = 1 if ratio > 0.6 else 2 if ratio > 0.3 else 3
                    cracks = self._get_cracks(hash(stone.stone_id) + row * 31 + col, level, size)
                    self.screen.blit(cracks, rect.topleft)

                if block.contains_monster:
                    pygame.draw.circle(self.screen, (230, 40, 40), rect.center, 7)
                    pygame.draw.circle(self.screen, (90, 10, 10), rect.center, 7, 1)
                if block.contains_artifact and player.artifacts_unlocked:
                    pygame.draw.circle(self.screen, (255, 220, 70), rect.center, 6)
                    pygame.draw.circle(self.screen, (120, 90, 10), rect.center, 6, 1)
                if block.contains_xp_stone:
                    pygame.draw.circle(self.screen, (180, 120, 255), rect.center, 6)
                    pygame.draw.circle(self.screen, (255, 255, 255), rect.center, 3)

                # surbrillance si survolé/accessible
                is_reachable = self._is_adjacent(player, row, col)
                if hover_cell == (row, col) and is_reachable:
                    pygame.draw.rect(self.screen, (255, 255, 255), rect, 3, border_radius=3)
                elif is_reachable and not block.is_empty:
                    pygame.draw.rect(self.screen, (255, 255, 255, 60), rect, 1, border_radius=3)

                # barre de progression de minage
                if mining_cell == (row, col) and block.health_ratio < 1.0:
                    bar_rect = pygame.Rect(rect.x, rect.bottom + 3, rect.width, 6)
                    pygame.draw.rect(self.screen, (40, 20, 20), bar_rect)
                    fill_w = int(rect.width * block.health_ratio)
                    pygame.draw.rect(self.screen, (250, 90, 60), (bar_rect.x, bar_rect.y, fill_w, 6))

        # voile sombre sur les rangées trop hautes (remontée interdite)
        for r_screen in range(self.visible_rows):
            if top_row + r_screen < asc_limit:
                self.screen.blit(self._ascent_veil, (self.grid_x, self.grid_y + r_screen * size))

        # compagnon de mine
        if player.has_companion:
            c_row_screen = player.companion.row - top_row
            if 0 <= c_row_screen < self.visible_rows:
                cx = self.grid_x + player.companion.col * size + size // 2
                cy = self.grid_y + c_row_screen * size + size // 2
                self._draw_companion_on_grid(cx, cy, player.companion)

        # joueur
        p_row_screen = player.row - top_row
        px = self.grid_x + player.col * size + size // 2
        py = self.grid_y + p_row_screen * size + size // 2
        self._draw_player(px, py, player, mining_cell is not None)
        self.last_top_row = top_row
        return top_row

    def _draw_companion_on_grid(self, cx, cy, companion):
        color = companion.color
        pygame.draw.circle(self.screen, (20, 20, 25), (cx + 2, cy + 3), 11)
        pygame.draw.circle(self.screen, color, (cx, cy), 11)
        pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), 11, 2)
        pygame.draw.circle(self.screen, (255, 220, 100), (cx, cy - 2), 3)

    def _is_adjacent(self, player, row, col):
        if row == player.row and col == player.col:
            return False
        if row < player.max_depth_reached - config.MAX_ASCENT:
            return False
        return (row, col) in (
            (player.row, player.col - 1), (player.row, player.col + 1),
            (player.row + 1, player.col), (player.row - 1, player.col)
        )

    def _get_aura_glow(self, color, radius):
        key = (color, radius)
        cache = self.__dict__.setdefault("_aura_cache", {})
        if key not in cache:
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            for r in range(radius, 0, -2):
                t = r / radius
                pygame.draw.circle(surf, (*color, int(22 * (1 - t) ** 1.5) + 2), (radius, radius), r)
            cache[key] = surf
        return cache[key]

    def _draw_aura(self, px, py, player):
        """Aura de l'équipement : très discrète, pour ne pas gêner la lecture des blocs."""
        aura = player.aura
        c = aura.color
        radius = int(self.tile * 0.75)
        glow = self._get_aura_glow(c, radius)
        self.screen.blit(glow, (px - radius, py - radius))
        t = pygame.time.get_ticks() / 900.0
        n = 2 + aura.tier
        for i in range(n):
            ang = t + i * math.tau / n
            ox = px + math.cos(ang) * self.tile * 0.46
            oy = py + math.sin(ang) * self.tile * 0.30
            dot = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(dot, (*c, 110), (4, 4), 3)
            self.screen.blit(dot, (ox - 4, oy - 4))

    def _draw_player(self, px, py, player, is_mining):
        self._draw_aura(px, py, player)
        pygame.draw.circle(self.screen, (40, 30, 20), (px + 3, py + 3 + 12), 15)  # ombre
        pygame.draw.circle(self.screen, (255, 214, 150), (px, py), 15)
        pygame.draw.circle(self.screen, (110, 70, 30), (px, py), 15, 2)
        # yeux
        pygame.draw.circle(self.screen, (30, 20, 15), (px - 5, py - 2), 2)
        pygame.draw.circle(self.screen, (30, 20, 15), (px + 5, py - 2), 2)

        swing = -35 + math.sin(pygame.time.get_ticks() / 75.0) * 42 if is_mining else -35
        self.draw_pickaxe(px + 10, py + 4, player.tool, scale=0.42, angle=swing, pivot="grip")

    # ==================================================================
    # PIOCHE (sprite haute résolution mis en cache : voir pickaxe_art.py)
    # ==================================================================
    def draw_pickaxe(self, x, y, tool, scale=1.0, angle=0.0, pivot="center"):
        """
        Dessine la pioche. angle : degrés, sens anti-horaire (0 = tête en haut).
        pivot="center" : (x, y) est le centre du sprite ; pivot="grip" : (x, y) est la main
        qui tient le manche (la pioche tourne autour de la prise).
        """
        f = 0.30 * scale
        sprite = pickaxe_art.get_scaled(tool.tier, f)
        rot = pygame.transform.rotozoom(sprite, angle, 1.0)
        th = math.radians(angle)
        c, s_ = math.cos(th), math.sin(th)

        def rotv(vx, vy):
            return vx * c + vy * s_, -vx * s_ + vy * c

        if pivot == "grip":
            gx, gy = rotv(0, (pickaxe_art.GRIP_Y - pickaxe_art.CH / 2) * f)
            center = (x - gx, y - gy)
        else:
            center = (x, y)
        self.screen.blit(rot, rot.get_rect(center=(int(center[0]), int(center[1]))))
        hx, hy = rotv(0, (pickaxe_art.HY - pickaxe_art.CH / 2) * f)
        pickaxe_art.draw_fx(self.screen, tool.art, (center[0] + hx, center[1] + hy), f,
                            pygame.time.get_ticks() / 1000.0)

    # ==================================================================
    # BARRE SUPERIEURE (profondeur)
    # ==================================================================
    def draw_top_bar(self, player):
        rect = pygame.Rect(0, 0, self.main_w, self.top_bar_h)
        pygame.draw.rect(self.screen, (12, 10, 16), rect)
        pygame.draw.line(self.screen, (60, 55, 70), (0, self.top_bar_h), (self.main_w, self.top_bar_h), 2)

        depth_txt = self.font_huge.render(f"{player.row} m", True, (240, 225, 190))
        self.screen.blit(depth_txt, (24, self.top_bar_h // 2 - depth_txt.get_height() // 2))
        label = self.font_tiny.render("PROFONDEUR", True, (150, 140, 160))
        self.screen.blit(label, (26, 8))

        # barre de vie compacte
        bx = 230
        bar_w, bar_h = 220, 20
        by = self.top_bar_h // 2 - bar_h // 2
        ratio = max(0, player.health / player.max_health)
        pygame.draw.rect(self.screen, (50, 18, 18), (bx, by, bar_w, bar_h), border_radius=6)
        pygame.draw.rect(self.screen, (215, 70, 70), (bx, by, int(bar_w * ratio), bar_h), border_radius=6)
        pygame.draw.rect(self.screen, (230, 230, 230), (bx, by, bar_w, bar_h), 1, border_radius=6)
        hp_txt = self.font_small.render(f"{int(player.health)}/{int(player.max_health)} PV", True, (255, 255, 255))
        self.screen.blit(hp_txt, (bx + bar_w // 2 - hp_txt.get_width() // 2, by + 1))

        gold_txt = self.font.render(f"{int(player.inventory.gold)} or", True, (255, 215, 90))
        self.screen.blit(gold_txt, (bx + bar_w + 30, self.top_bar_h // 2 - gold_txt.get_height() // 2))

        # niveau de mineur + barre d'XP
        lx = max(bx + bar_w + 190, self.main_w - 250)
        lt = self.font.render(f"Niv. {player.level}", True, (170, 220, 255))
        self.screen.blit(lt, (lx, 10))
        self._draw_player_xp_bar(lx, 44, 210, 12, player)
        xp_str = ("MAX" if player.level >= config.PLAYER_MAX_LEVEL
                  else f"{int(player.xp)}/{int(player.xp_to_next_level())} XP")
        self.screen.blit(self.font_tiny.render(xp_str, True, (150, 170, 200)), (lx, 60))

    # ==================================================================
    # PANNEAU LATERAL A ONGLETS
    # ==================================================================
    def draw_side_panel(self, player, stones, artifacts, competitive_ai, competitors=None):
        self.rects = {}
        self._war_competitors = competitors or []
        px = self.main_w
        panel_rect = pygame.Rect(px, 0, self.panel_w, self.H)
        for y in range(0, self.H, 3):
            t = y / self.H
            c = _lerp_color((24, 20, 30), (14, 12, 18), t)
            pygame.draw.rect(self.screen, c, (px, y, self.panel_w, 3))
        pygame.draw.line(self.screen, (90, 70, 110), (px, 0), (px, self.H), 2)

        tabs = [("tool", "Outil"), ("equip", "Équip."), ("stones", "Pierres"), ("artifacts", "Artef."),
                ("competitors", "Rivaux"), ("workshop", "Atelier"), ("stats", "Stats")]
        tab_w = self.panel_w // len(tabs)
        pulse = 0.65 + 0.35 * math.sin(pygame.time.get_ticks() / 260.0)
        for i, (key, label) in enumerate(tabs):
            r = pygame.Rect(px + i * tab_w, 0, tab_w, 44)
            active = self.active_tab == key
            base_c = (52, 44, 66) if active else (24, 20, 30)
            pygame.draw.rect(self.screen, base_c, r)
            color = (255, 235, 200) if active else (150, 145, 160)
            txt = self.font_tiny.render(label, True, color)
            self.screen.blit(txt, (r.centerx - txt.get_width() // 2, r.centery - txt.get_height() // 2))
            if active:
                glow_c = (int(255 * pulse), int(180 * pulse + 40), int(80 * pulse))
                pygame.draw.rect(self.screen, glow_c, (r.x, r.bottom - 3, r.w, 3))
            self.rects[f"tab_{key}"] = r

        content = pygame.Rect(px + 16, 60, self.panel_w - 32, self.H - 80)

        if self.active_tab == "tool":
            self._draw_tab_tool(content, player)
        elif self.active_tab == "equip":
            self._draw_tab_equipment(content, player)
        elif self.active_tab == "stones":
            self._draw_tab_stones(content, stones)
        elif self.active_tab == "artifacts":
            self._draw_tab_artifacts(content, artifacts, player)
        elif self.active_tab == "competitors":
            self._draw_tab_competitors(content, player, competitors or [])
        elif self.active_tab == "workshop":
            self._draw_tab_workshop(content, player)
        elif self.active_tab == "stats":
            self._draw_tab_stats(content, player, competitive_ai)

    def _draw_tab_tool(self, rect, player):
        tool = player.tool
        # grande icône
        self.draw_pickaxe(rect.centerx, rect.y + 92, tool, scale=1.25, angle=-14)

        y = rect.y + 175
        name = self.font_big.render(tool.name, True, (240, 230, 210))
        self.screen.blit(name, (rect.centerx - name.get_width() // 2, y))
        y += 34

        lvl_txt = self.font_tiny.render(f"Niveau {tool.level}/{tool.max_level} · palier {tool.tier + 1}/{len(config.TOOL_TIERS)}", True, (160, 200, 170))
        self.screen.blit(lvl_txt, (rect.centerx - lvl_txt.get_width() // 2, y))
        y += 18
        self._draw_xp_bar(rect.x, y, rect.width, tool)
        y += 22

        skin = self._wrap_text(tool.skin_description, self.font_tiny, rect.width)
        for line in skin:
            t = self.font_tiny.render(line, True, (170, 165, 185))
            self.screen.blit(t, (rect.centerx - t.get_width() // 2, y))
            y += 16
        y += 8

        stat1 = self.font_small.render(f"Dégâts par coup : {tool.power:.1f}", True, (220, 220, 220))
        self.screen.blit(stat1, (rect.x, y)); y += 24
        stat2 = self.font_small.render(f"Cadence : {tool.speed:.1f} coups/s", True, (220, 220, 220))
        self.screen.blit(stat2, (rect.x, y)); y += 30

        self._draw_upgrade_button(rect, y, tool, player, "btn_upgrade_tool")

    def _draw_xp_bar(self, x, y, width, equip):
        bar = pygame.Rect(x, y, width, 8)
        pygame.draw.rect(self.screen, (40, 38, 46), bar, border_radius=4)
        if equip.level < equip.max_level:
            ratio = equip.xp / equip.xp_to_next_level()
        else:
            ratio = 1.0
        pygame.draw.rect(self.screen, (140, 210, 160), (x, y, int(width * min(1, ratio)), 8), border_radius=4)
        pygame.draw.rect(self.screen, (90, 90, 100), bar, 1, border_radius=4)

    def _draw_upgrade_button(self, rect, y, equip, player, rect_key):
        cost = equip.upgrade_cost()
        btn_rect = pygame.Rect(rect.x, y, rect.width, 46)
        if cost > 0:
            can_afford = player.inventory.gold >= cost
            color = (70, 130, 80) if can_afford else (60, 45, 45)
            pygame.draw.rect(self.screen, color, btn_rect, border_radius=8)
            pygame.draw.rect(self.screen, (255, 255, 255), btn_rect, 1, border_radius=8)
            label = self.font_small.render(f"Améliorer — {cost} or", True, (240, 240, 240))
            self.screen.blit(label, (btn_rect.centerx - label.get_width() // 2, btn_rect.centery - label.get_height() // 2))
            self.rects[rect_key] = btn_rect
        else:
            pygame.draw.rect(self.screen, (60, 55, 30), btn_rect, border_radius=8)
            label = self.font_small.render("Niveau maximum atteint !", True, (255, 210, 90))
            self.screen.blit(label, (btn_rect.centerx - label.get_width() // 2, btn_rect.centery - label.get_height() // 2))
        return btn_rect

    # ------------------------------------------------------------------
    def _draw_tab_equipment(self, rect, player):
        sub_tabs = [("helmet", "Casque"), ("armor", "Armure"), ("aura", "Aura"), ("amulet", "Amulette"),
                    ("gauntlet", "Gantelet"), ("companion", "Compagnon")]
        if not hasattr(self, "active_equip"):
            self.active_equip = "helmet"
        sw = rect.width // len(sub_tabs)
        for i, (key, label) in enumerate(sub_tabs):
            r = pygame.Rect(rect.x + i * sw, rect.y, sw - 4, 30)
            active = self.active_equip == key
            pygame.draw.rect(self.screen, (60, 52, 74) if active else (32, 28, 40), r, border_radius=6)
            txt = self.font_tiny.render(label, True, (240, 230, 210) if active else (150, 145, 165))
            self.screen.blit(txt, (r.centerx - txt.get_width() // 2, r.centery - txt.get_height() // 2))
            self.rects[f"subtab_{key}"] = r

        content = pygame.Rect(rect.x, rect.y + 44, rect.width, rect.height - 44)

        if self.active_equip == "companion":
            comp = player.companion
            if not player.has_companion:
                self._draw_lock_notice(content, content.y, config.LEVEL_COMPANION, "Le compagnon de mine", player.level)
                return
            self._draw_equip_icon(content.centerx, content.y + 58, comp, "companion")
            y = content.y + 126
            name = self.font_big.render(comp.name, True, (240, 230, 210))
            self.screen.blit(name, (content.centerx - name.get_width() // 2, y)); y += 32
            lvl_txt = self.font_tiny.render(f"Niveau XP {comp.level}/{comp.max_level} · Palier or {comp.gold_tier}/{comp.max_gold_tier}", True, (160, 200, 170))
            self.screen.blit(lvl_txt, (content.centerx - lvl_txt.get_width() // 2, y)); y += 18
            self._draw_xp_bar(content.x, y, content.width, comp)
            y += 22
            p_txt = self.font_small.render(f"Dégâts par coup : {comp.mining_power:.1f}", True, (220, 220, 220))
            self.screen.blit(p_txt, (content.x, y)); y += 22
            s_txt = self.font_small.render(f"Cadence de minage : {comp.hits_per_second:.2f} coups/s", True, (220, 220, 220))
            self.screen.blit(s_txt, (content.x, y)); y += 22
            desc = "Mine automatiquement la roche sur la grille en suivant le joueur (même hors-écran). " \
                   "Ne combat pas les monstres mais récolte artefacts et composants."
            for line in self._wrap_text(desc, self.font_tiny, content.width):
                self.screen.blit(self.font_tiny.render(line, True, (150, 145, 165)), (content.x, y)); y += 16
            y += 12
            cost = comp.gold_upgrade_cost()
            btn_rect = pygame.Rect(content.x, y, content.width, 46)
            if cost > 0:
                can = player.inventory.gold >= cost
                pygame.draw.rect(self.screen, (70, 130, 80) if can else (60, 45, 45), btn_rect, border_radius=8)
                pygame.draw.rect(self.screen, (255, 255, 255), btn_rect, 1, border_radius=8)
                bt = self.font_small.render(f"Améliorer vitesse (Or) — {cost} or", True, (240, 240, 240))
                self.screen.blit(bt, (btn_rect.centerx - bt.get_width() // 2, btn_rect.centery - bt.get_height() // 2))
                self.rects["btn_upgrade_companion"] = btn_rect
            else:
                pygame.draw.rect(self.screen, (60, 55, 30), btn_rect, border_radius=8)
                bt = self.font_small.render("Palier d'or maximum atteint !", True, (255, 210, 90))
                self.screen.blit(bt, (btn_rect.centerx - bt.get_width() // 2, btn_rect.centery - bt.get_height() // 2))
            return

        equip = {"helmet": player.helmet, "armor": player.armor,
                 "aura": player.aura, "amulet": player.amulet, "gauntlet": player.gauntlet}[self.active_equip]
        bonus_label = {
            "helmet": lambda v: f"+{v:.0f} PV max",
            "armor": lambda v: f"-{v * 100:.0f}% dégâts reçus",
            "aura": lambda v: f"+{v * 100:.0f}% d'or gagné",
            "amulet": lambda v: "",
            "gauntlet": lambda v: f"+{v:.1f} dégâts contre les monstres",
        }[self.active_equip]
        xp_source = {
            "helmet": "S'améliore en encaissant des dégâts (après réduction de l'armure).",
            "armor": "S'améliore en réduisant des dégâts (proportionnel à ce qu'elle bloque).",
            "aura": "S'améliore en gagnant de l'or.",
            "amulet": "S'améliore en régénérant réellement des PV.",
            "gauntlet": "S'améliore UNIQUEMENT en combattant (dégâts infligés aux monstres).",
        }[self.active_equip]

        content = pygame.Rect(rect.x, rect.y + 44, rect.width, rect.height - 44)
        self._draw_equip_icon(content.centerx, content.y + 58, equip, self.active_equip)
        if not equip.enabled:
            need = config.LEVEL_EQUIP_UNLOCK[self.active_equip]
            veil = pygame.Surface((220, 140), pygame.SRCALPHA)
            veil.fill((10, 8, 14, 205))
            self.screen.blit(veil, (content.centerx - 110, content.y - 12))
            lk = self.font_big.render("VERROUILLÉ", True, (240, 200, 130))
            self.screen.blit(lk, (content.centerx - lk.get_width() // 2, content.y + 44))
            y = content.y + 150
            for line in self._wrap_text(f"Cet équipement se débloque au niveau {need} de mineur "
                                        f"(tu es niveau {player.level}).", self.font_small, content.width):
                t = self.font_small.render(line, True, (210, 200, 180))
                self.screen.blit(t, (content.centerx - t.get_width() // 2, y)); y += 22
            for line in self._wrap_text("Il ne donne aucun bonus et ne gagne pas d'XP tant qu'il est verrouillé.",
                                        self.font_tiny, content.width):
                t = self.font_tiny.render(line, True, (150, 145, 165))
                self.screen.blit(t, (content.centerx - t.get_width() // 2, y)); y += 16
            return

        y = content.y + 126
        name = self.font_big.render(equip.name, True, (240, 230, 210))
        self.screen.blit(name, (content.centerx - name.get_width() // 2, y))
        y += 32
        lvl_txt = self.font_tiny.render(
            f"Niveau {equip.level}/{equip.max_level} · palier {equip.tier + 1}/{len(equip._tiers)}",
            True, (160, 200, 170))
        self.screen.blit(lvl_txt, (content.centerx - lvl_txt.get_width() // 2, y))
        y += 18
        self._draw_xp_bar(content.x, y, content.width, equip)
        y += 22

        skin = self._wrap_text(equip.skin_description, self.font_tiny, content.width)
        for line in skin:
            t = self.font_tiny.render(line, True, (170, 165, 185))
            self.screen.blit(t, (content.centerx - t.get_width() // 2, y))
            y += 16
        y += 6

        m = equip._level_mult()
        col_hdr = (190, 185, 200)
        self.screen.blit(self.font_tiny.render(f"Palier x niveau {equip.level} (x{m:.2f}) + bonus plat = bonus total", True, col_hdr),
                         (content.x, y)); y += 18
        kind = self.active_equip
        rows = []
        if kind == "helmet":
            flat_hp = equip.flat_bonus()
            flat_rg = equip.flat_bonus("regen")
            rows.append(("PV max", f"+{equip.base_bonus:.0f}", f"+{flat_hp:.1f} plat", f"+{equip.effective_bonus:.1f}"))
            rows.append(("Régénération", f"{equip.data['regen']:.2f}/s", f"+{flat_rg:.3f}/s plat", f"{equip.effective_regen:.3f}/s"))
        elif kind == "amulet":
            flat_rg = equip.flat_bonus("regen")
            rows.append(("Régénération", f"{equip.data['regen']:.2f}/s", f"+{flat_rg:.3f}/s plat", f"{equip.effective_regen:.3f}/s"))
        elif kind == "armor":
            flat_arm = equip.flat_bonus()
            rows.append(("Dégâts reçus", f"-{equip.base_bonus * 100:.1f}%", f"-{flat_arm * 100:.2f}% plat", f"-{equip.effective_bonus * 100:.2f}%"))
        elif kind == "aura":
            flat_aur = equip.flat_bonus()
            rows.append(("Or gagné", f"+{equip.base_bonus * 100:.1f}%", f"+{flat_aur * 100:.2f}% plat", f"+{equip.effective_bonus * 100:.2f}%"))
        else:
            flat_gt = equip.flat_bonus()
            rows.append(("Dégâts vs monstres", f"+{equip.base_bonus:.0f}", f"+{flat_gt:.1f} plat", f"+{equip.effective_bonus:.1f}"))
        for row_info in rows:
            label, base_v, flat_v, total_v = row_info
            line = self.font_small.render(f"{label} : {base_v} ({flat_v}) -> {total_v}", True, (220, 220, 220))
            self.screen.blit(line, (content.x, y)); y += 22
        mine_line = self.font_tiny.render(
            f"+ {(equip.level - 1) * config.ITEM_LEVEL_MINING_BONUS * 100:.2f}% de puissance de minage (en plus du bonus ci-dessus)",
            True, (150, 210, 160))
        self.screen.blit(mine_line, (content.x, y)); y += 22

        src_lines = self._wrap_text(xp_source, self.font_tiny, content.width)
        for line in src_lines:
            t = self.font_tiny.render(line, True, (130, 150, 140))
            self.screen.blit(t, (content.x, y)); y += 15
        y += 8

        self._draw_upgrade_button(content, y, equip, player, f"btn_upgrade_{self.active_equip}")

    def _draw_equip_icon(self, x, y, equip, kind):
        c = equip.color
        glow = equip.glow
        if glow:
            surf = pygame.Surface((160, 160), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*glow, 60), (80, 80), 70)
            self.screen.blit(surf, (x - 80, y - 80))
        if kind == "helmet":
            pygame.draw.circle(self.screen, c, (x, y), 34)
            pygame.draw.rect(self.screen, c, (x - 34, y, 68, 20), border_radius=4)
            pygame.draw.circle(self.screen, _shade(c, 1.4), (x, y), 34, 3)
        elif kind == "armor":
            pts = [(x, y - 36), (x + 32, y - 14), (x + 26, y + 36), (x - 26, y + 36), (x - 32, y - 14)]
            pygame.draw.polygon(self.screen, c, pts)
            pygame.draw.polygon(self.screen, _shade(c, 1.4), pts, 3)
        elif kind == "aura":
            t = pygame.time.get_ticks() / 500.0
            for i in range(3):
                ang = t + i * 2.094
                px = x + math.cos(ang) * 40
                py = y + math.sin(ang) * 24
                pygame.draw.circle(self.screen, c, (int(px), int(py)), 8)
            pygame.draw.circle(self.screen, c, (x, y), 16)
            pygame.draw.circle(self.screen, _shade(c, 1.4), (x, y), 16, 2)
        elif kind == "gauntlet":
            pygame.draw.rect(self.screen, c, (x - 26, y - 6, 52, 40), border_radius=8)
            for i in range(4):
                fx = x - 26 + i * 13
                pygame.draw.rect(self.screen, c, (fx, y - 30, 11, 28), border_radius=5)
                pygame.draw.rect(self.screen, _shade(c, 1.4), (fx, y - 30, 11, 28), 1, border_radius=5)
            pygame.draw.rect(self.screen, c, (x + 22, y - 2, 14, 26), border_radius=6)
            pygame.draw.rect(self.screen, _shade(c, 0.6), (x - 26, y + 26, 52, 12), border_radius=3)
            pygame.draw.rect(self.screen, _shade(c, 1.4), (x - 26, y - 6, 52, 40), 2, border_radius=8)
        elif kind == "amulet":
            pulse = 0.85 + 0.15 * math.sin(pygame.time.get_ticks() / 400.0)
            r = int(20 * pulse)
            pygame.draw.line(self.screen, _shade(c, 0.6), (x, y - 50), (x, y - 22), 3)
            pts = [(x, y - 22), (x + 22, y), (x, y + 26), (x - 22, y)]
            pygame.draw.polygon(self.screen, c, pts)
            pygame.draw.polygon(self.screen, _shade(c, 1.5), pts, 2)
            pygame.draw.circle(self.screen, _shade(c, 1.6), (x, y), max(3, r // 3))
        elif kind == "companion":
            c = equip.color
            pygame.draw.circle(self.screen, c, (x, y), 32)
            pygame.draw.circle(self.screen, _shade(c, 1.4), (x, y), 32, 3)
            pygame.draw.circle(self.screen, (255, 230, 120), (x, y - 8), 8)

    def _draw_tab_stones(self, rect, stones):
        title = self.font.render("Pierres", True, (230, 225, 210))
        self.screen.blit(title, (rect.x, rect.y))
        ledger = getattr(self, "ledger", None)
        # pierres que tu as découvertes + celles que ta faction a nommées (même si tu ne les as pas encore minées)
        found = {s.stone_id: s for s in stones.all_discovered()}
        if ledger:
            for sid in ledger.team_stones(0):
                found.setdefault(sid, stones.get_by_id(sid))
        entries = sorted(found.values(), key=lambda s: s.depth_tier)
        bonus_n = len(ledger.team_stones(0)) if ledger else 0
        sub = self.font_tiny.render(f"Bonus de faction : {bonus_n} pierre(s) à +10% de vitesse", True, (150, 200, 160))
        self.screen.blit(sub, (rect.x, rect.y + 24))
        area = pygame.Rect(rect.x, rect.y + 50, rect.width, rect.bottom - rect.y - 50)
        if not entries:
            t = self.font_small.render("Aucune pierre découverte pour l'instant.", True, (150, 150, 160))
            self.screen.blit(t, (rect.x, area.y))
            return
        off = self._scroll_begin("stones", area)
        y = area.y - off
        for s in entries:
            if area.y - 40 < y < area.bottom:
                e = ledger.get(s.stone_id) if ledger else None
                name = e["name"] if e else s.display_name
                pygame.draw.rect(self.screen, s.base_color, (rect.x, y + 2, 14, 14), border_radius=3)
                self.screen.blit(self.font_small.render(name, True, (225, 220, 210)), (rect.x + 22, y))
                rarity_c = config.RARITY_COLORS.get(s.rarity, (200, 200, 200))
                rt = self.font_tiny.render(s.rarity, True, rarity_c)
                self.screen.blit(rt, (rect.x + 22, y + 18))
                x2 = rect.x + 22 + rt.get_width() + 10
                if e:
                    mine = e["team"] == 0
                    self.screen.blit(self.font_tiny.render(f"par {e['by']}", True, (150, 145, 165)), (x2, y + 18))
                    if mine and s.stone_id != config.STONE_NO_BONUS_ID:
                        bt = self.font_tiny.render("+10% vitesse", True, (140, 220, 150))
                        self.screen.blit(bt, (rect.right - bt.get_width() - 8, y + 2))
            y += 40
        self._scroll_end(y + off - area.y)

    def _draw_tab_artifacts(self, rect, artifacts, player):
        title = self.font.render("Artefacts anciens", True, (230, 225, 210))
        self.screen.blit(title, (rect.x, rect.y))
        completion = self.font_tiny.render(f"{len(artifacts.found)}/{len(artifacts.defs)} trouvés  (molette pour défiler)",
                                           True, (170, 165, 185))
        self.screen.blit(completion, (rect.x, rect.y + 26))
        top = rect.y + 54
        if not player.artifacts_unlocked:
            warn = self.font_tiny.render(f"Les artefacts ne seront reconnus qu'au niveau {config.LEVEL_ARTIFACTS}.",
                                         True, (225, 170, 120))
            self.screen.blit(warn, (rect.x, rect.y + 44))
            top = rect.y + 66
        area = pygame.Rect(rect.x, top, rect.width, rect.bottom - top)
        off = self._scroll_begin("artifacts", area)
        y = area.y - off
        for adef in artifacts.defs.values():
            if area.y - 40 < y < area.bottom:
                found = adef.artifact_id in artifacts.found
                color = config.RARITY_COLORS.get(adef.rarity, (200, 200, 200)) if found else (70, 70, 78)
                pygame.draw.circle(self.screen, color, (rect.x + 8, y + 8), 7)
                name = adef.name if found else "Artefact non découvert"
                name_txt = self.font_small.render(name, True, (225, 220, 210) if found else (110, 108, 118))
                self.screen.blit(name_txt, (rect.x + 24, y))
                if found and adef.bonus_type:
                    bonus_txt = self.font_tiny.render(adef.bonus_desc, True, (140, 200, 150))
                    self.screen.blit(bonus_txt, (rect.x + 24, y + 18))
                elif not found:
                    rt = self.font_tiny.render(adef.rarity, True, (90, 88, 100))
                    self.screen.blit(rt, (rect.x + 24, y + 18))
            y += 40
        self._scroll_end(y + off - area.y)

    def _draw_tab_competitors(self, rect, player, competitors):
        title = self.font.render("Classement des mineurs", True, (230, 225, 210))
        self.screen.blit(title, (rect.x, rect.y))
        sub = self.font_tiny.render("Score = profondeur + or + collection", True, (150, 145, 165))
        self.screen.blit(sub, (rect.x, rect.y + 22))

        if not hasattr(self, "team_filter"):
            self.team_filter = None
        filt_y = rect.y + 40
        labels = [("Toutes", None)] + [(config.TEAM_NAMES[i][:10], i) for i in range(4)]
        fx = rect.x
        for label, val in labels:
            w = self.font_tiny.size(label)[0] + 14
            r = pygame.Rect(fx, filt_y, w, 22)
            active = self.team_filter == val
            pygame.draw.rect(self.screen, (60, 52, 40) if active else (30, 27, 36), r, border_radius=5)
            t = self.font_tiny.render(label, True, (255, 225, 180) if active else (150, 145, 165))
            self.screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
            self.rects[f"teamfilter_{val}"] = r
            fx += w + 6

        entries = [{
            "name": "Toi", "color": (255, 214, 150), "depth": player.row, "team": 0,
            "gold": player.inventory.gold, "tier": player.tool.tier,
            "status": "toi", "score": player.row * 2 + player.inventory.gold * 0.5
                       + len(self.artifacts.found) * 20 + len(self.stones.all_discovered()) * 4
                       + player.inventory.war_wins * config.WAR_WIN_SCORE,
        }]
        for ai in competitors:
            entries.append({
                "name": ai.name, "color": ai.color, "depth": ai.state.row, "team": ai.team,
                "gold": ai.inventory.gold, "tier": ai.tool.tier,
                "status": ai.status, "score": ai.score(),
            })
        if self.team_filter is not None:
            entries = [e for e in entries if e["team"] == self.team_filter]
        entries.sort(key=lambda e: e["score"], reverse=True)

        status_labels = {"creuse": "creuse", "combat": "combat !", "fuite": "fuit",
                          "ko": "K.O.", "toi": "en jeu"}
        area = pygame.Rect(rect.x, rect.y + 74, rect.width, rect.bottom - rect.y - 74)
        off = self._scroll_begin("competitors", area)
        y = area.y - off
        for rank, e in enumerate(entries, start=1):
            row_h = 44
            row_rect = pygame.Rect(rect.x, y, rect.width - 8, row_h - 6)
            if area.y - row_h < y < area.bottom:
                if e["name"] == "Toi":
                    pygame.draw.rect(self.screen, (46, 40, 30), row_rect, border_radius=6)
                rank_txt = self.font_tiny.render(f"#{rank}", True, (200, 195, 180))
                self.screen.blit(rank_txt, (row_rect.x, row_rect.y + 4))
                pygame.draw.circle(self.screen, e["color"], (row_rect.x + 40, row_rect.y + 12), 6)
                name_txt = self.font_tiny.render(e["name"], True, (225, 220, 210))
                self.screen.blit(name_txt, (row_rect.x + 52, row_rect.y))
                detail = f"{e['depth']} m · {int(e['gold'])} or · T{e['tier'] + 1}"
                detail_txt = self.font_tiny.render(detail, True, (165, 160, 178))
                self.screen.blit(detail_txt, (row_rect.x + 52, row_rect.y + 17))
                status_c = (150, 220, 150) if e["status"] in ("creuse", "toi") else \
                           (230, 90, 90) if e["status"] in ("combat", "ko") else (220, 190, 100)
                status_txt = self.font_tiny.render(status_labels.get(e["status"], e["status"]), True, status_c)
                self.screen.blit(status_txt, (row_rect.right - status_txt.get_width(), row_rect.y + 4))
            y += row_h
        self._scroll_end(y + off - area.y)

    def _draw_lock_notice(self, rect, y, need, what, level):
        box = pygame.Rect(rect.x, y, rect.width, 84)
        pygame.draw.rect(self.screen, (34, 28, 40), box, border_radius=8)
        pygame.draw.rect(self.screen, (130, 105, 70), box, 1, border_radius=8)
        t = self.font.render("Verrouillé", True, (240, 200, 130))
        self.screen.blit(t, (box.centerx - t.get_width() // 2, box.y + 10))
        for i, line in enumerate(self._wrap_text(f"{what} : niveau {need} requis (tu es niveau {level}).",
                                                 self.font_tiny, box.width)):
            lt = self.font_tiny.render(line, True, (200, 190, 170))
            self.screen.blit(lt, (box.centerx - lt.get_width() // 2, box.y + 42 + i * 16))

    def _draw_tab_workshop(self, rect, player):
        inv = player.inventory
        subs = [("comp", "Composants"), ("troops", "Troupes"), ("hero", "Héros"), ("tower", "Donjon"), ("war", "Guerre")]
        sw = rect.width // len(subs)
        for i, (key, label) in enumerate(subs):
            r = pygame.Rect(rect.x + i * sw, rect.y, sw - 4, 28)
            active = self.active_workshop == key
            pygame.draw.rect(self.screen, (60, 52, 74) if active else (32, 28, 40), r, border_radius=6)
            txt = self.font_tiny.render(label, True, (240, 230, 210) if active else (150, 145, 165))
            self.screen.blit(txt, (r.centerx - txt.get_width() // 2, r.centery - txt.get_height() // 2))
            self.rects[f"wsub_{key}"] = r
        y = rect.y + 40

        if self.active_workshop == "comp":
            t = self.font.render(f"Composants : {inv.total_components()}", True, (230, 225, 210))
            self.screen.blit(t, (rect.x, y)); y += 26
            if player.can_sell or player.can_buy:
                note = "Trouvés en minant/combattant. Marché : vendre / acheter."
            else:
                note = (f"Trouvés en minant ou sur les monstres. Marché : vente niv. {config.LEVEL_SELL},"
                        f" achat niv. {config.LEVEL_BUY}.")
            for line in self._wrap_text(note, self.font_tiny, rect.width):
                self.screen.blit(self.font_tiny.render(line, True, (150, 145, 165)), (rect.x, y)); y += 15
            y += 6
            area = pygame.Rect(rect.x, y, rect.width, rect.bottom - y)
            off = self._scroll_begin("workshop_comp", area)
            y0, y = y, y - off
            for cdef in crafting.COMPONENT_DEFS:
                cid = cdef.component_id
                buyable = player.can_buy and cdef.min_depth <= player.max_depth_reached
                seen = cid in inv.components_seen or buyable
                count = inv.components.get(cid, 0)
                market = seen and (player.can_sell or buyable)
                row_h = 44 + (26 if market else 0)
                if area.y - row_h < y < area.bottom:
                    col = config.RARITY_COLORS.get(cdef.rarity, (200, 200, 200)) if seen else (70, 70, 78)
                    pygame.draw.circle(self.screen, col, (rect.x + 8, y + 9), 7)
                    name = cdef.name if seen else "Composant inconnu"
                    nt = self.font_small.render(name, True, (225, 220, 210) if seen else (110, 108, 118))
                    self.screen.blit(nt, (rect.x + 24, y))
                    if seen:
                        ct = self.font_small.render(f"x{count}", True, (255, 225, 150))
                        self.screen.blit(ct, (rect.right - ct.get_width() - 8, y))
                    desc = cdef.description if seen else f"Se trouve à partir de ~{cdef.min_depth} m"
                    dt = self.font_tiny.render(desc, True, (140, 160, 150) if seen else (100, 98, 108))
                    self.screen.blit(dt, (rect.x + 24, y + 19))
                    if market:
                        bx = rect.x + 24
                        if player.can_sell:
                            b = pygame.Rect(bx, y + 42, 150, 20)
                            ok = count > 0
                            pygame.draw.rect(self.screen, (120, 100, 50) if ok else (50, 44, 44), b, border_radius=5)
                            pygame.draw.rect(self.screen, (255, 255, 255), b, 1, border_radius=5)
                            bt = self.font_tiny.render(f"Vendre +{crafting.sell_price(cid)} or", True, (245, 240, 230))
                            self.screen.blit(bt, (b.centerx - bt.get_width() // 2, b.centery - bt.get_height() // 2))
                            self._reg(f"sell_{cid}", b)
                            bx += 158
                        if buyable:
                            b = pygame.Rect(bx, y + 42, 150, 20)
                            ok = inv.gold >= crafting.buy_price(cid)
                            pygame.draw.rect(self.screen, (70, 130, 80) if ok else (60, 45, 45), b, border_radius=5)
                            pygame.draw.rect(self.screen, (255, 255, 255), b, 1, border_radius=5)
                            bt = self.font_tiny.render(f"Acheter -{crafting.buy_price(cid)} or", True, (245, 245, 245))
                            self.screen.blit(bt, (b.centerx - bt.get_width() // 2, b.centery - bt.get_height() // 2))
                            self._reg(f"buy_{cid}", b)
                y += row_h
            self._scroll_end(y + off - y0)
            return

        if self.active_workshop == "war":
            if not player.workshop_unlocked:
                self._draw_lock_notice(rect, y, config.LEVEL_WORKSHOP, "Les attaques", player.level)
            else:
                self._draw_workshop_war(rect, player, y)
            return

        if self.active_workshop == "hero":
            self._draw_workshop_hero(rect, player, y)
            return

        if self.active_workshop == "tower":
            self._draw_workshop_tower(rect, player, y)
            return

        if not player.workshop_unlocked:
            self._draw_lock_notice(rect, y, config.LEVEL_WORKSHOP, "Le recrutement de troupes", player.level)
            return

        kind = "troop"
        tot = crafting.army_totals(inv)
        t = self.font_small.render(f"Armée : {tot['count']} unités", True, (230, 225, 210))
        self.screen.blit(t, (rect.x, y)); y += 20
        s_ = self.font_tiny.render(f"Total · ATQ {tot['attack']} · PV {tot['health']} · DEF {tot['defense']}",
                                   True, (150, 200, 160))
        self.screen.blit(s_, (rect.x, y)); y += 22
        note = self.font_tiny.render("Elles marchent et se battent vraiment sur le champ de bataille.", True, (130, 125, 145))
        self.screen.blit(note, (rect.x, y)); y += 22

        area = pygame.Rect(rect.x, y, rect.width, rect.bottom - y)
        off = self._scroll_begin("workshop_troops", area)
        y0, y = y, y - off
        for recipe in [r for r in crafting.RECIPES if r.kind == kind]:
            # coût sur plusieurs lignes si nécessaire
            lines, cur, cur_w = [], [], 0
            for cid, n in recipe.cost.items():
                have = inv.components.get(cid, 0)
                txt = f"{n}x {crafting.COMPONENTS[cid].name} ({have})"
                w = self.font_tiny.size(txt)[0] + 12
                if cur and cur_w + w > rect.width - 16:
                    lines.append(cur); cur, cur_w = [], 0
                cur.append((txt, have >= n, w)); cur_w += w
            if cur:
                lines.append(cur)
            row_h = 52 + 15 * len(lines)
            row = pygame.Rect(rect.x, y, rect.width - 8, row_h - 6)
            pygame.draw.rect(self.screen, (30, 26, 38), row, border_radius=6)
            owned = inv.units.get(recipe.recipe_id, 0)
            nt = self.font_small.render(f"{recipe.name}  x{owned}", True, (230, 225, 210))
            self.screen.blit(nt, (row.x + 8, row.y + 4))
            kind_txt = "tir" if recipe.range > 60 else "mêlée"
            st = self.font_tiny.render(f"ATQ {recipe.attack} · PV {recipe.health} · DEF {recipe.defense} · {kind_txt}",
                                       True, (170, 165, 185))
            self.screen.blit(st, (row.x + 8, row.y + 26))
            cy = row.y + 44
            for line in lines:
                cx = row.x + 8
                for txt, ok, w in line:
                    ct = self.font_tiny.render(txt, True, (140, 210, 150) if ok else (210, 110, 110))
                    self.screen.blit(ct, (cx, cy)); cx += w
                cy += 15
            can = crafting.can_craft(inv, recipe)
            btn = pygame.Rect(row.right - 92, row.y + 6, 84, 26)
            pygame.draw.rect(self.screen, (70, 130, 80) if can else (60, 45, 45), btn, border_radius=6)
            pygame.draw.rect(self.screen, (255, 255, 255), btn, 1, border_radius=6)
            bt = self.font_tiny.render("Fabriquer", True, (240, 240, 240))
            self.screen.blit(bt, (btn.centerx - bt.get_width() // 2, btn.centery - bt.get_height() // 2))
            self._reg(f"craft_{recipe.recipe_id}", btn)
            y += row_h
        self._scroll_end(y + off - y0)

    def _draw_workshop_hero(self, rect, player, y):
        hero = player.hero
        if not player.has_hero:
            self._draw_lock_notice(rect, y, config.LEVEL_HERO, "Le Héros de guerre", player.level)
            return

        t = self.font.render(hero.name, True, (240, 230, 210))
        self.screen.blit(t, (rect.x, y)); y += 28
        lvl_txt = self.font_tiny.render(f"Niveau XP {hero.level}/{hero.max_level} · Palier Or {hero.gold_tier}/{hero.max_gold_tier}", True, (160, 200, 170))
        self.screen.blit(lvl_txt, (rect.x, y)); y += 18
        self._draw_xp_bar(rect.x, y, rect.width, hero)
        y += 24

        stats_lines = [
            f"PV max : {hero.max_hp:.0f}",
            f"Dégâts d'attaque : {hero.attack_damage:.1f}",
            f"Armure (Défense) : {hero.armor:.1f}",
            f"Cadence d'attaque : 1 coup toutes les {hero.attack_interval:.2f} s",
            f"Multiplicateur XP : x{hero.xp_multiplier:.2f}",
        ]
        for line in stats_lines:
            self.screen.blit(self.font_small.render(line, True, (220, 220, 220)), (rect.x, y)); y += 22
        y += 8

        desc = "Participe à toutes les attaques lancées contre d'autres joueurs (ne défend jamais). " \
               "Gagne de l'XP en infligeant et en subissant des dégâts lors de ces batailles."
        for line in self._wrap_text(desc, self.font_tiny, rect.width):
            self.screen.blit(self.font_tiny.render(line, True, (150, 145, 165)), (rect.x, y)); y += 16
        y += 14

        cost = hero.gold_upgrade_cost()
        btn_rect = pygame.Rect(rect.x, y, rect.width, 42)
        if cost > 0:
            can = player.inventory.gold >= cost
            pygame.draw.rect(self.screen, (70, 130, 80) if can else (60, 45, 45), btn_rect, border_radius=8)
            pygame.draw.rect(self.screen, (255, 255, 255), btn_rect, 1, border_radius=8)
            bt = self.font_small.render(f"Améliorer Héros (Or) — {cost} or", True, (240, 240, 240))
            self.screen.blit(bt, (btn_rect.centerx - bt.get_width() // 2, btn_rect.centery - bt.get_height() // 2))
            self.rects["btn_upgrade_hero"] = btn_rect
        else:
            pygame.draw.rect(self.screen, (60, 55, 30), btn_rect, border_radius=8)
            bt = self.font_small.render("Palier d'or maximum atteint !", True, (255, 210, 90))
            self.screen.blit(bt, (btn_rect.centerx - bt.get_width() // 2, btn_rect.centery - bt.get_height() // 2))

    def _draw_workshop_tower(self, rect, player, y):
        inv = player.inventory
        st = tower_mod.stats(inv.tower)
        t = self.font.render("Donjon d'archer", True, (230, 225, 210))
        self.screen.blit(t, (rect.x, y)); y += 28
        for line in self._wrap_text("Ta seule défense : il tire depuis l'arrière du champ de bataille sur les "
                                    "ennemis qui t'attaquent. Améliore-le avec de l'or.", self.font_tiny, rect.width):
            self.screen.blit(self.font_tiny.render(line, True, (150, 145, 165)), (rect.x, y)); y += 15
        y += 6
        area = pygame.Rect(rect.x, y, rect.width, rect.bottom - y)
        off = self._scroll_begin("workshop_tower", area)
        y0, y = y, y - off
        for key, spec in tower_mod.TRACKS.items():
            need = config.TOWER_TRACK_UNLOCK[key]
            locked = player.level < need
            lv = inv.tower.get(key, 0)
            cost = tower_mod.upgrade_cost(inv.tower, key)
            supreme = key == "supreme"
            row_h = 62 if locked else (86 if supreme else 78)
            row = pygame.Rect(rect.x, y, rect.width - 8, row_h - 6)
            pygame.draw.rect(self.screen, (24, 21, 30) if locked else (30, 26, 38), row, border_radius=6)
            head_col = (120, 116, 128) if locked else (230, 225, 210)
            self.screen.blit(self.font_small.render(f"{spec['label']}  niv. {lv}/{spec['max']}", True, head_col),
                             (row.x + 8, row.y + 6))
            if locked:
                self.screen.blit(self.font_tiny.render(f"Verrouillé : niveau de mineur {need} requis", True, (200, 150, 100)),
                                 (row.x + 8, row.y + 32))
                y += row_h
                continue
            if supreme:
                cur = tower_mod.SUPREME_DESC[lv - 1] if lv > 0 else "aucun effet"
                nxt = tower_mod.SUPREME_DESC[lv] if cost >= 0 else "max"
                self.screen.blit(self.font_tiny.render(f"Actuel : {cur}", True, (150, 200, 160)), (row.x + 8, row.y + 28))
                self.screen.blit(self.font_tiny.render(f"Suivant : {nxt}", True, (220, 200, 140)), (row.x + 8, row.y + 44))
                by = row.y + 60
            else:
                cur = tower_mod.format_stat(key, st[key])
                nxt_levels = dict(inv.tower); nxt_levels[key] = lv + 1
                nxt = tower_mod.format_stat(key, tower_mod.stats(nxt_levels)[key]) if cost >= 0 else "max"
                self.screen.blit(self.font_tiny.render(f"Actuel : {cur}   ->   Suivant : {nxt}", True, (150, 200, 160)),
                                 (row.x + 8, row.y + 30))
                by = row.y + 50
            btn = pygame.Rect(row.x + 8, by, row.width - 16, 22)
            if cost >= 0:
                can = inv.gold >= cost
                pygame.draw.rect(self.screen, (70, 130, 80) if can else (60, 45, 45), btn, border_radius=6)
                pygame.draw.rect(self.screen, (255, 255, 255), btn, 1, border_radius=6)
                bt = self.font_tiny.render(f"Améliorer — {cost} or", True, (240, 240, 240))
                self._reg(f"towerup_{key}", btn)
            else:
                pygame.draw.rect(self.screen, (60, 55, 30), btn, border_radius=6)
                bt = self.font_tiny.render("Niveau maximum", True, (255, 210, 90))
            self.screen.blit(bt, (btn.centerx - bt.get_width() // 2, btn.centery - bt.get_height() // 2))
            y += row_h
        self._scroll_end(y + off - y0)

    def _draw_workshop_war(self, rect, player, y):
        info = self.war_info or {}
        inv = player.inventory
        troops = crafting.army_totals(inv)
        t = self.font_small.render(f"Troupes : {troops['count']} · ATQ {troops['attack']} · PV {troops['health']}",
                                   True, (230, 225, 210))
        self.screen.blit(t, (rect.x, y)); y += 20
        lv = sum(inv.tower.values())
        t = self.font_small.render(f"Donjon d'archer : niveaux cumulés {lv}", True, (150, 200, 160))
        self.screen.blit(t, (rect.x, y)); y += 20
        cd = info.get("cooldown_left", 0)
        msg = f"Prochaine attaque dans {int(cd) + 1} s" if cd > 0 else "Tes troupes sont prêtes."
        t = self.font_tiny.render(msg + "  (troupes + donjon te défendent des IA)", True, (150, 145, 165))
        self.screen.blit(t, (rect.x, y)); y += 22

        enemies = [ai for ai in self._war_competitors if ai.team != 0]
        shields = info.get("shields", {})
        selected = info.get("selected")
        for i, ai in enumerate(enemies):
            if y > rect.bottom - 150:
                break
            u = crafting.army_totals(ai.inventory)
            atk = u["count"]
            dfn = sum(ai.inventory.tower.values())
            r = pygame.Rect(rect.x, y, rect.width, 22)
            pygame.draw.rect(self.screen, (60, 52, 40) if selected == i else (30, 26, 38), r, border_radius=5)
            pygame.draw.circle(self.screen, ai.color, (r.x + 10, r.centery), 5)
            nt = self.font_tiny.render(ai.name, True, (225, 220, 210))
            self.screen.blit(nt, (r.x + 22, r.centery - nt.get_height() // 2))
            sh = shields.get(ai.name, 0)
            detail = f"{atk} troupes · donjon {dfn}"
            dt_ = self.font_tiny.render(detail if sh <= 0 else f"protégé {int(sh) + 1}s", True,
                                        (165, 160, 178) if sh <= 0 else (220, 190, 100))
            self.screen.blit(dt_, (r.right - dt_.get_width() - 8, r.centery - dt_.get_height() // 2))
            self.rects[f"wartarget_{i}"] = r
            y += 25

        y += 4
        btn = pygame.Rect(rect.x, y, rect.width, 38)
        if selected is not None and 0 <= selected < len(enemies):
            label = f"Attaquer {enemies[selected].name}"
            ready = cd <= 0 and troops["count"] > 0
        else:
            label, ready = "Choisis une cible", False
        pygame.draw.rect(self.screen, (130, 60, 55) if ready else (60, 45, 45), btn, border_radius=8)
        pygame.draw.rect(self.screen, (255, 255, 255), btn, 1, border_radius=8)
        bt = self.font_small.render(label, True, (245, 240, 240))
        self.screen.blit(bt, (btn.centerx - bt.get_width() // 2, btn.centery - bt.get_height() // 2))
        self.rects["war_attack"] = btn
        y += 48

        mine = [r for r in reversed(info.get("log", [])) if "Toi" in (r.attacker, r.defender)][:4]
        for rep in mine:
            col = (140, 210, 150) if rep.good_for("Toi") else (220, 120, 120)
            for line in self._wrap_text(rep.line("Toi"), self.font_tiny, rect.width)[:2]:
                if y > rect.bottom - 14:
                    return
                self.screen.blit(self.font_tiny.render(line, True, col), (rect.x, y))
                y += 15
            y += 3

    def _draw_player_xp_bar(self, x, y, w, h, player):
        pygame.draw.rect(self.screen, (34, 36, 50), (x, y, w, h), border_radius=h // 2)
        if player.level >= config.PLAYER_MAX_LEVEL:
            ratio = 1.0
        else:
            ratio = player.xp / player.xp_to_next_level()
        pygame.draw.rect(self.screen, (110, 190, 255), (x, y, int(w * max(0.0, min(1.0, ratio))), h), border_radius=h // 2)
        pygame.draw.rect(self.screen, (120, 130, 160), (x, y, w, h), 1, border_radius=h // 2)

    def _draw_tab_stats(self, rect, player, competitive_ai):
        title = self.font.render("Statistiques", True, (230, 225, 210))
        self.screen.blit(title, (rect.x, rect.y))
        area = pygame.Rect(rect.x, rect.y + 34, rect.width, rect.bottom - rect.y - 34)
        off = self._scroll_begin("stats", area)
        y = area.y - off

        lvl = self.font.render(f"Niveau de mineur : {player.level}/{config.PLAYER_MAX_LEVEL}", True, (170, 220, 255))
        self.screen.blit(lvl, (rect.x, y)); y += 28
        self._draw_player_xp_bar(rect.x, y, rect.width - 10, 10, player); y += 14
        if player.level < config.PLAYER_MAX_LEVEL:
            xt = f"{int(player.xp)} / {int(player.xp_to_next_level())} XP"
        else:
            xt = "Niveau maximum"
        self.screen.blit(self.font_tiny.render(xt, True, (150, 170, 200)), (rect.x, y)); y += 24

        lines = [
            f"Profondeur actuelle : {player.row} m",
            f"Record de profondeur : {player.max_depth_reached} m",
            f"Or possédé : {int(player.inventory.gold)}",
            f"Ressources minées : {player.inventory.total_resources()}",
            f"Pierres découvertes : {len(self.stones.all_discovered())}",
            f"Pierres d'XP possédées : {player.inventory.xp_stones} (+{player.inventory.xp_stones * 0.8:.1f} XP/s)",
            f"Artefacts trouvés : {len(self.artifacts.found)}/{len(self.artifacts.defs)}",
            f"Puissance de minage : {player.mining_power:.1f}  (dont +{player.level_damage_bonus:.1f} de niveau)",
            f"Dégâts en combat : {player.mining_power + player.combat_bonus:.1f}",
            f"Chance d'artefact inédit : {self.artifacts.pity_chance(player.artifact_pity, player.bonus_artifact_luck, player.new_artifact_flat) * 100:.0f}%",
            f"Composants : {player.inventory.total_components()} · Victoires de guerre : {player.inventory.war_wins}",
            f"Troupes : {crafting.army_totals(player.inventory)['count']} · Donjon : niv. {sum(player.inventory.tower.values())}",
            f"Bonus de minage des niveaux d'objets : +{player.items_level_bonus() * 100:.1f}%",
            f"Niveau de compétence (IA) : {int(competitive_ai.player_rating)}",
        ]
        for line in lines:
            for sub in self._wrap_text(line, self.font_small, rect.width):
                self.screen.blit(self.font_small.render(sub, True, (215, 212, 205)), (rect.x, y))
                y += 22
            y += 5

        y += 6
        self.screen.blit(self.font.render("Déblocages par niveau", True, (230, 225, 210)), (rect.x, y)); y += 30
        for lv in range(1, config.PLAYER_MAX_LEVEL + 1):
            reached = player.level >= lv
            col = (140, 215, 150) if reached else (120, 116, 130)
            text = f"Niv. {lv} : {config.LEVEL_UNLOCK_TEXT.get(lv, '')}"
            for sub in self._wrap_text(text, self.font_tiny, rect.width):
                self.screen.blit(self.font_tiny.render(sub, True, col), (rect.x, y))
                y += 16
            y += 4
        self._scroll_end(y + off - area.y)

    # ------------------------------------------------------------------
    # DEFILEMENT (molette) dans le panneau latéral
    # ------------------------------------------------------------------
    def _scroll_begin(self, key, area):
        self._sc = (key, area)
        off = max(0, min(self.scroll.get(key, 0), self.scroll_max.get(key, 0)))
        self.scroll[key] = off
        self.screen.set_clip(area)
        return off

    def _scroll_end(self, content_h):
        key, area = self._sc
        self.screen.set_clip(None)
        self._sc = None
        max_s = max(0, int(content_h - area.h))
        self.scroll_max[key] = max_s
        if max_s > 0:
            track = pygame.Rect(area.right + 8, area.y, 5, area.h)
            pygame.draw.rect(self.screen, (40, 36, 50), track, border_radius=2)
            hh = max(26, int(area.h * area.h / (area.h + max_s)))
            hy = area.y + int((area.h - hh) * self.scroll[key] / max_s)
            pygame.draw.rect(self.screen, (160, 150, 185), (track.x, hy, 5, hh), border_radius=2)

    def _reg(self, key, rect):
        """Enregistre un rect cliquable, rogné à la zone de défilement courante."""
        if self._sc is not None:
            rect = rect.clip(self._sc[1])
            if rect.w <= 0 or rect.h <= 0:
                return
        self.rects[key] = rect

    def on_wheel(self, pos, dy):
        """Molette : fait défiler l'onglet actif du panneau latéral."""
        if pos[0] < self.main_w:
            return
        key = f"workshop_{self.active_workshop}" if self.active_tab == "workshop" else self.active_tab
        self.scroll[key] = max(0, self.scroll.get(key, 0) - dy * 48)

    # ==================================================================
    # UTILITAIRES
    # ==================================================================
    def _wrap_text(self, text, font, max_width):
        words = text.split(" ")
        lines, current = [], ""
        for w in words:
            test = (current + " " + w).strip()
            if font.size(test)[0] > max_width - 20 and current:
                lines.append(current)
                current = w
            else:
                current = test
        if current:
            lines.append(current)
        return lines

    def draw_message(self, text, sub=None):
        w = min(560, self.main_w - 40)
        overlay = pygame.Surface((w, 64), pygame.SRCALPHA)
        overlay.fill((10, 10, 15, 215))
        x = (self.main_w - w) // 2
        y = self.H - 96
        self.screen.blit(overlay, (x, y))
        pygame.draw.rect(self.screen, (255, 210, 120), (x, y, w, 64), 1, border_radius=6)
        t = self.font_small.render(text, True, (255, 255, 255))
        self.screen.blit(t, (x + 16, y + 10))
        if sub:
            st = self.font_tiny.render(sub, True, (210, 210, 210))
            self.screen.blit(st, (x + 16, y + 36))

    # ==================================================================
    # MODALES
    # ==================================================================
    def draw_naming_dialog(self, stone, text_input, bonus=True):
        w, h = 520, 262
        rect = pygame.Rect((self.W - w) // 2, (self.H - h) // 2, w, h)
        pygame.draw.rect(self.screen, (25, 22, 30), rect, border_radius=12)
        pygame.draw.rect(self.screen, stone.base_color, rect, 3, border_radius=12)

        title = self.font_big.render("Nouvelle pierre découverte !", True, (255, 230, 150))
        self.screen.blit(title, (rect.x + 20, rect.y + 18))
        rarity_color = config.RARITY_COLORS.get(stone.rarity, (200, 200, 200))
        info = self.font.render(f"Rareté : {stone.rarity}", True, rarity_color)
        self.screen.blit(info, (rect.x + 20, rect.y + 60))
        prompt = self.font.render("Donne-lui un nom :", True, (230, 230, 230))
        self.screen.blit(prompt, (rect.x + 20, rect.y + 96))

        box = pygame.Rect(rect.x + 20, rect.y + 128, w - 40, 38)
        pygame.draw.rect(self.screen, (12, 12, 16), box, border_radius=6)
        pygame.draw.rect(self.screen, (160, 160, 170), box, 1, border_radius=6)
        cursor = "_" if pygame.time.get_ticks() % 1000 < 500 else ""
        txt = self.font.render(text_input.text + cursor, True, (255, 255, 255))
        self.screen.blit(txt, (box.x + 8, box.y + 6))

        note = ("Tu es le premier à la trouver : elle porte ton nom pour tout le monde,"
                if bonus else "Tu es le premier à la trouver : elle porte ton nom pour tout le monde.")
        self.screen.blit(self.font_tiny.render(note, True, (200, 190, 150)), (rect.x + 20, rect.y + 176))
        if bonus:
            self.screen.blit(self.font_tiny.render("et ta faction gagne +10% de vitesse de cassage sur cette pierre.",
                                                   True, (150, 220, 160)), (rect.x + 20, rect.y + 194))
        else:
            self.screen.blit(self.font_tiny.render("(la toute première pierre ne donne pas de bonus)",
                                                   True, (150, 150, 160)), (rect.x + 20, rect.y + 194))
        hint = self.font_tiny.render("Entrée pour valider", True, (150, 150, 150))
        self.screen.blit(hint, (rect.x + 20, rect.y + h - 26))

    def _combat_modal_rect(self):
        w, h = min(1000, self.W - 60), min(640, self.H - 60)
        return pygame.Rect((self.W - w) // 2, (self.H - h) // 2, w, h)

    def get_combat_arena_rect(self):
        m = self._combat_modal_rect()
        return pygame.Rect(m.x + 30, m.y + 96, m.w - 60, m.h - 96 - 100)

    def draw_combat(self, player, monster, log, enemy_pos, hit_flash=0.0):
        rect = self._combat_modal_rect()
        pygame.draw.rect(self.screen, (32, 15, 15), rect, border_radius=12)
        border_c = (255, 110, 60) if monster.is_boss else (190, 65, 65)
        pygame.draw.rect(self.screen, border_c, rect, 3, border_radius=12)

        title = self.font_big.render(("BOSS : " if monster.is_boss else "") + monster.name, True, (255, 220, 200))
        self.screen.blit(title, (rect.x + 20, rect.y + 14))
        hint = self.font_tiny.render("Clique sur le monstre pour l'attaquer !", True, (255, 200, 150))
        self.screen.blit(hint, (rect.right - hint.get_width() - 20, rect.y + 22))

        y = rect.y + 56
        ratio = monster.health / monster.max_health if monster.max_health else 0
        pygame.draw.rect(self.screen, (60, 20, 20), (rect.x + 20, y, 320, 16), border_radius=6)
        pygame.draw.rect(self.screen, (215, 65, 65), (rect.x + 20, y, int(320 * ratio), 16), border_radius=6)
        pygame.draw.rect(self.screen, (240, 240, 240), (rect.x + 20, y, 320, 16), 1, border_radius=6)
        self.screen.blit(self.font_tiny.render(f"{monster.health}/{monster.max_health} PV", True, (255, 255, 255)), (rect.x + 350, y))

        # arène de combat
        arena = self.get_combat_arena_rect()
        pygame.draw.rect(self.screen, (14, 8, 8), arena, border_radius=8)
        pygame.draw.rect(self.screen, (90, 40, 40), arena, 2, border_radius=8)

        mx, my = enemy_pos
        radius = 30 if not monster.is_boss else 42
        flash = int(120 * hit_flash)
        base_c = (220, 60 + flash, 60 + flash) if not monster.is_boss else (255, 120 + flash, 60)
        pygame.draw.circle(self.screen, (30, 10, 10), (int(mx) + 4, int(my) + 6), radius)  # ombre
        pygame.draw.circle(self.screen, base_c, (int(mx), int(my)), radius)
        pygame.draw.circle(self.screen, _shade(base_c, 1.4), (int(mx), int(my)), radius, 3)
        # yeux menaçants
        pygame.draw.circle(self.screen, (255, 255, 255), (int(mx) - radius * 0.35, int(my) - 4), 4)
        pygame.draw.circle(self.screen, (255, 255, 255), (int(mx) + radius * 0.35, int(my) - 4), 4)
        pygame.draw.circle(self.screen, (20, 10, 10), (int(mx) - radius * 0.35, int(my) - 4), 2)
        pygame.draw.circle(self.screen, (20, 10, 10), (int(mx) + radius * 0.35, int(my) - 4), 2)

        self.rects["combat_enemy"] = pygame.Rect(mx - radius, my - radius, radius * 2, radius * 2)
        self.rects["combat_arena"] = arena

        log_y = arena.bottom + 8
        for line in log[-3:]:
            self.screen.blit(self.font_tiny.render(line, True, (222, 210, 210)), (rect.x + 20, log_y))
            log_y += 18

        btn_flee = pygame.Rect(rect.right - 150, rect.bottom - 54, 130, 40)
        pygame.draw.rect(self.screen, (60, 60, 70), btn_flee, border_radius=8)
        pygame.draw.rect(self.screen, (255, 255, 255), btn_flee, 1, border_radius=8)
        f_txt = self.font_small.render("Fuir (F)", True, (255, 255, 255))
        self.screen.blit(f_txt, (btn_flee.centerx - f_txt.get_width() // 2, btn_flee.centery - f_txt.get_height() // 2))
        self.rects["btn_flee"] = btn_flee

    def draw_game_over(self):
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((10, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        over = self.font_huge.render("Tu as été vaincu par les profondeurs...", True, (255, 110, 110))
        self.screen.blit(over, (self.W // 2 - over.get_width() // 2, self.H // 2 - 80))

        btn_restart = pygame.Rect(self.W // 2 - 160, self.H // 2, 320, 50)
        pygame.draw.rect(self.screen, (70, 130, 80), btn_restart, border_radius=10)
        t1 = self.font.render("Recommencer", True, (255, 255, 255))
        self.screen.blit(t1, (btn_restart.centerx - t1.get_width() // 2, btn_restart.centery - t1.get_height() // 2))
        self.rects["btn_restart"] = btn_restart

        btn_menu = pygame.Rect(self.W // 2 - 160, self.H // 2 + 64, 320, 50)
        pygame.draw.rect(self.screen, (60, 60, 75), btn_menu, border_radius=10)
        t2 = self.font.render("Menu principal", True, (255, 255, 255))
        self.screen.blit(t2, (btn_menu.centerx - t2.get_width() // 2, btn_menu.centery - t2.get_height() // 2))
        self.rects["btn_menu"] = btn_menu

    # ==================================================================
    # MENU / PAUSE
    # ==================================================================
    def draw_menu(self, ai_difficulties, locked=False, has_save=False):
        from src.ai.competitor import AI_PROFILES, AI_COLORS
        self.rects = {}
        for y in range(0, self.H, 3):
            t = y / self.H
            c = _lerp_color((30, 22, 20), (12, 10, 18), t)
            pygame.draw.rect(self.screen, c, (0, y, self.W, 3))

        title = self.font_huge.render("PROFONDEURS", True, (255, 220, 160))
        self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 24))
        sub = self.font_small.render("Le jeu du mineur — 4 équipes de 4, toi compris", True, (190, 180, 200))
        self.screen.blit(sub, (self.W // 2 - sub.get_width() // 2, 78))

        label_txt = ("Difficulté des 15 IA — verrouillée pour cette partie (choisie à son début)" if locked
                     else "Difficulté individuelle des 15 IA (clique pour changer) :")
        label = self.font.render(label_txt, True, (220, 215, 205))
        self.screen.blit(label, (self.W // 2 - label.get_width() // 2, 108))

        diff_color = {"Facile": (90, 160, 100), "Normal": (150, 140, 70), "Difficile": (170, 70, 70)}

        # regroupement par équipe, 4 colonnes
        cols = 4
        col_w = min(300, (self.W - 100) // cols)
        start_x = self.W // 2 - (col_w * cols) // 2
        top_y = 144
        by_team = {}
        for i, p in enumerate(AI_PROFILES):
            by_team.setdefault(p["team"], []).append(i)

        for team_id, indices in by_team.items():
            cx = start_x + team_id * col_w
            team_c = config.TEAM_COLORS[team_id]
            name_t = self.font_small.render(config.TEAM_NAMES[team_id], True, team_c)
            self.screen.blit(name_t, (cx + col_w // 2 - name_t.get_width() // 2, top_y))
            y = top_y + 26
            if team_id == 0:
                you = self.font_tiny.render("Toi (joueur)", True, (255, 230, 180))
                self.screen.blit(you, (cx + 10, y))
                y += 24
            for i in indices:
                p = AI_PROFILES[i]
                d = ai_difficulties[i]
                r = pygame.Rect(cx + 8, y, col_w - 16, 30)
                pygame.draw.rect(self.screen, (30, 26, 38), r, border_radius=6)
                pygame.draw.circle(self.screen, AI_COLORS[i], (r.x + 14, r.centery), 6)
                name_txt = self.font_tiny.render(p["name"], True, (220, 215, 205))
                self.screen.blit(name_txt, (r.x + 26, r.centery - name_txt.get_height() // 2))
                dc = diff_color[d]
                if locked:
                    dc = tuple(int(c * 0.7) for c in dc)
                d_txt = self.font_tiny.render(d, True, dc)
                self.screen.blit(d_txt, (r.right - d_txt.get_width() - 8, r.centery - d_txt.get_height() // 2))
                self.rects[f"aidiff_{i}"] = r
                y += 34

        quick_y = top_y + 5 * 34 + 40
        if locked:
            for key, label, color, dx in (("btn_continue", "Continuer", (200, 150, 60), -270),
                                           ("btn_newgame", "Nouvelle partie", (90, 70, 60), 10)):
                r = pygame.Rect(self.W // 2 + dx, quick_y + 20, 260, 54)
                pygame.draw.rect(self.screen, color, r, border_radius=10)
                t = self.font.render(label, True, (30, 20, 10) if key == "btn_continue" else (255, 255, 255))
                self.screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
                self.rects[key] = r
        else:
            quick_label = self.font_tiny.render("Réglage rapide :", True, (170, 165, 180))
            self.screen.blit(quick_label, (self.W // 2 - 210, quick_y + 12))
            qx = self.W // 2 - 60
            for key, label, color in (("diff_all_facile", "Tout Facile", (90, 160, 100)),
                                       ("diff_all_normal", "Tout Normal", (150, 140, 70)),
                                       ("diff_all_difficile", "Tout Difficile", (170, 70, 70))):
                r = pygame.Rect(qx, quick_y, 150, 30)
                pygame.draw.rect(self.screen, color, r, border_radius=6)
                t = self.font_tiny.render(label, True, (255, 255, 255))
                self.screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
                self.rects[key] = r
                qx += 158

            btn_w = 340 if has_save else 260
            btn_start = pygame.Rect(self.W // 2 - btn_w // 2, quick_y + 50, btn_w, 54)
            pygame.draw.rect(self.screen, (200, 150, 60), btn_start, border_radius=10)
            t = self.font.render("Lancer la nouvelle partie" if has_save else "Commencer", True, (30, 20, 10))
            self.screen.blit(t, (btn_start.centerx - t.get_width() // 2, btn_start.centery - t.get_height() // 2))
            self.rects["btn_start"] = btn_start
            if has_save:
                warn = self.font_tiny.render("Attention : cela remplace ta sauvegarde actuelle.", True, (220, 150, 130))
                self.screen.blit(warn, (self.W // 2 - warn.get_width() // 2, quick_y + 112))
                btn_cancel = pygame.Rect(self.W // 2 + btn_w // 2 + 16, quick_y + 50, 140, 54)
                pygame.draw.rect(self.screen, (60, 60, 75), btn_cancel, border_radius=10)
                t = self.font.render("Annuler", True, (255, 255, 255))
                self.screen.blit(t, (btn_cancel.centerx - t.get_width() // 2, btn_cancel.centery - t.get_height() // 2))
                self.rects["btn_cancel_new"] = btn_cancel

        hint = self.font_tiny.render(
            "ZQSD (maintenu) pour miner/te déplacer · Clic maintenu pour miner · G pour le graphique · Échap pour la pause",
            True, (140, 135, 150))
        self.screen.blit(hint, (self.W // 2 - hint.get_width() // 2, self.H - 30))

    # ==================================================================
    # GRAPHIQUE DE PROGRESSION
    # ==================================================================
    def draw_chart(self, history_time, history, visible, stat, player, competitors):
        from src.ai.competitor import AI_PROFILES
        self.rects = {}
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((8, 6, 12, 225))
        self.screen.blit(overlay, (0, 0))

        margin = 40
        panel_w = min(1100, self.W - margin * 2)
        panel_h = min(700, self.H - margin * 2)
        rect = pygame.Rect((self.W - panel_w) // 2, (self.H - panel_h) // 2, panel_w, panel_h)
        pygame.draw.rect(self.screen, (20, 17, 26), rect, border_radius=12)
        pygame.draw.rect(self.screen, (120, 110, 140), rect, 2, border_radius=12)

        title = self.font_big.render("Progression dans le temps", True, (240, 230, 210))
        self.screen.blit(title, (rect.x + 24, rect.y + 16))

        btn_close = pygame.Rect(rect.right - 44, rect.y + 14, 30, 30)
        pygame.draw.rect(self.screen, (90, 40, 40), btn_close, border_radius=6)
        xt = self.font_small.render("×", True, (255, 255, 255))
        self.screen.blit(xt, (btn_close.centerx - xt.get_width() // 2, btn_close.centery - xt.get_height() // 2))
        self.rects["chart_close"] = btn_close

        # sélecteur de statistique
        stats = [("depth", "Profondeur"), ("gold", "Or"), ("score", "Score")]
        sx = rect.x + 24
        sy = rect.y + 54
        for key, label in stats:
            w = self.font_tiny.size(label)[0] + 20
            r = pygame.Rect(sx, sy, w, 26)
            active = stat == key
            pygame.draw.rect(self.screen, (70, 60, 40) if active else (32, 28, 40), r, border_radius=6)
            t = self.font_tiny.render(label, True, (255, 220, 160) if active else (170, 165, 185))
            self.screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
            self.rects[f"chart_stat_{key}"] = r
            sx += w + 8

        chart_area = pygame.Rect(rect.x + 24, rect.y + 96, panel_w - 300, panel_h - 130)
        pygame.draw.rect(self.screen, (12, 10, 16), chart_area, border_radius=8)
        pygame.draw.rect(self.screen, (70, 65, 80), chart_area, 1, border_radius=8)

        all_series = {"Toi": (player is not None, (255, 214, 150))}
        colors = {"Toi": (255, 214, 150)}
        for ai in competitors:
            colors[ai.name] = ai.color

        visible_series = {name: [d[stat] for d in pts] for name, pts in history.items() if name in visible and pts}
        max_val = 1
        for pts in visible_series.values():
            if pts:
                max_val = max(max_val, max(pts))
        n = len(history_time)

        # grille + axe Y
        for i in range(5):
            gy = chart_area.y + chart_area.height * i / 4
            pygame.draw.line(self.screen, (35, 32, 42), (chart_area.x, gy), (chart_area.right, gy), 1)
            val = max_val * (1 - i / 4)
            t = self.font_tiny.render(f"{val:.0f}", True, (110, 105, 120))
            self.screen.blit(t, (chart_area.x + 4, gy + 2))

        if n >= 2:
            for name, pts in visible_series.items():
                color = colors.get(name, (200, 200, 200))
                points = []
                m = len(pts)
                for i, v in enumerate(pts):
                    x = chart_area.x + chart_area.width * (i / max(1, m - 1))
                    y = chart_area.bottom - chart_area.height * min(1.0, v / max_val)
                    points.append((x, y))
                if len(points) >= 2:
                    pygame.draw.lines(self.screen, color, False, points, 2)
                if points:
                    pygame.draw.circle(self.screen, color, points[-1], 4)
        elif n == 1:
            info = self.font_tiny.render("Encore un instant... premier point dans quelques secondes.",
                                          True, (150, 145, 165))
            self.screen.blit(info, (chart_area.centerx - info.get_width() // 2, chart_area.centery))

        x_label = self.font_tiny.render("Temps écoulé (s) ->", True, (140, 135, 150))
        self.screen.blit(x_label, (chart_area.x, chart_area.bottom + 6))

        # légende / cases à cocher
        legend = pygame.Rect(chart_area.right + 20, rect.y + 96, panel_w - (chart_area.right - rect.x) - 44, panel_h - 130)
        lt = self.font_small.render("Afficher :", True, (220, 215, 205))
        self.screen.blit(lt, (legend.x, legend.y))

        ba = pygame.Rect(legend.x, legend.y + 26, 60, 22)
        pygame.draw.rect(self.screen, (40, 60, 45), ba, border_radius=5)
        self.screen.blit(self.font_tiny.render("Toutes", True, (200, 230, 200)), (ba.x + 4, ba.y + 4))
        self.rects["chart_all"] = ba
        bn = pygame.Rect(legend.x + 68, legend.y + 26, 60, 22)
        pygame.draw.rect(self.screen, (60, 40, 40), bn, border_radius=5)
        self.screen.blit(self.font_tiny.render("Aucune", True, (230, 200, 200)), (bn.x + 4, bn.y + 4))
        self.rects["chart_none"] = bn

        y = legend.y + 58
        entries = [("Toi", (255, 214, 150), None)] + [(ai.name, ai.color, ai.team) for ai in competitors]
        for name, color, team in entries:
            if y > legend.bottom - 18:
                break
            r = pygame.Rect(legend.x, y, legend.width, 20)
            checked = name in visible
            box = pygame.Rect(r.x, r.y + 3, 14, 14)
            pygame.draw.rect(self.screen, color, box, border_radius=3)
            if not checked:
                pygame.draw.rect(self.screen, (15, 13, 18), box.inflate(-4, -4), border_radius=2)
            pygame.draw.rect(self.screen, (255, 255, 255), box, 1, border_radius=3)
            label = name + (" (toi)" if name == "Toi" else "")
            t = self.font_tiny.render(label, True, (225, 220, 210) if checked else (110, 108, 118))
            self.screen.blit(t, (r.x + 20, r.y + 2))
            self.rects[f"chart_check_{name}"] = r
            y += 20

    def draw_paused(self):
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill((8, 6, 12, 200))
        self.screen.blit(overlay, (0, 0))

        title = self.font_huge.render("Pause", True, (240, 230, 210))
        self.screen.blit(title, (self.W // 2 - title.get_width() // 2, self.H // 2 - 180))

        buttons = [("btn_resume", "Reprendre", (70, 130, 80)),
                   ("btn_restart", "Recommencer", (150, 110, 50)),
                   ("btn_menu", "Menu principal (choisir la difficulté)", (60, 60, 75)),
                   ("btn_quit", "Quitter", (120, 50, 50))]
        y = self.H // 2 - 90
        for key, label, color in buttons:
            r = pygame.Rect(self.W // 2 - 190, y, 380, 52)
            pygame.draw.rect(self.screen, color, r, border_radius=10)
            pygame.draw.rect(self.screen, (255, 255, 255), r, 1, border_radius=10)
            t = self.font_small.render(label, True, (255, 255, 255))
            self.screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
            self.rects[key] = r
            y += 64

    # ------------------------------------------------------------------
    def screen_to_cell(self, mx, my):
        if not (self.grid_x <= mx < self.grid_x + self.tile * config.GRID_COLS and my >= self.grid_y):
            return None
        col = (mx - self.grid_x) // self.tile
        row_screen = (my - self.grid_y) // self.tile
        if row_screen < 0 or row_screen >= self.visible_rows or not (0 <= col < config.GRID_COLS):
            return None
        return self.last_top_row + row_screen, col
