"""
Point d'entrée du jeu du mineur — version clicker.

Lance simplement :
    python3 main.py

Clic gauche maintenu sur un bloc adjacent = le miner en continu.
Clic gauche sur une case vide adjacente = s'y déplacer.
ZQSD = se déplacer dans les galeries déjà creusées.
En combat : clique sur le monstre (qui se déplace) pour l'attaquer.
"""

import sys
import os
import math
import random
import time
import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import config
from src.world.stone_registry import StoneRegistry
from src.world.stone_ledger import StoneLedger
from src.world.world_generator import WorldGenerator
from src.items.artifact import ArtifactCatalog
from src.items import crafting
from src.entities.player import Player
from src.entities.monster import spawn_monster
from src.ai.monster_ai import CompetitiveAI
from src.combat import combat_system as combat
from src.combat import faction_war
from src.items import tower as tower_mod
from src.ui.renderer import Renderer
from src.ui.text_input import TextInput
from src.ui.particles import ParticleSystem
from src.ui.war_scene import WarScene
from src.ai.competitor import create_competitors
from src.save import save_manager


class GameState:
    MENU = "menu"
    PAUSED = "paused"
    EXPLORING = "exploring"
    NAMING_STONE = "naming_stone"
    COMBAT = "combat"
    GAME_OVER = "game_over"
    WAR_SCENE = "war_scene"


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Profondeurs - le jeu du mineur")

        flags = pygame.FULLSCREEN | pygame.DOUBLEBUF if config.FULLSCREEN else 0
        try:
            info = pygame.display.Info()
            size = (info.current_w, info.current_h)
        except pygame.error:
            size = (1280, 800)
        self.screen = pygame.display.set_mode(size, flags)
        self.clock = pygame.time.Clock()

        self.renderer = Renderer(self.screen, StoneRegistry(), ArtifactCatalog())
        self.text_input = TextInput()

        from src.ai.competitor import AI_PROFILES
        self.ai_difficulties = [config.DEFAULT_DIFFICULTY] * len(AI_PROFILES)
        saved_diffs = save_manager.peek_ai_difficulties([p["name"] for p in AI_PROFILES])
        if saved_diffs:
            self.ai_difficulties = saved_diffs
        self.has_save = save_manager.save_exists()
        self.menu_new_game = False       # True : on prépare une nouvelle partie (difficultés modifiables)
        self.autosave_timer = 0.0
        self.state = GameState.MENU
        self.state_before_pause = GameState.EXPLORING

        self.show_chart = False
        self.chart_stat = "depth"
        self.chart_visible = {"Toi"}
        self.history = {}          # nom -> liste de valeurs
        self.history_time = []     # temps (s) correspondant à chaque point
        self.history_timer = 0.0
        self.session_time = 0.0

        self.held_dirs = []        # touches ZQSD actuellement maintenues, dans l'ordre

        self.message = None
        self.message_until = 0

        self.pending_stone = None
        self.current_monster = None
        self.combat_log = []
        self.combat_target_block = None
        self.enemy_pos = [0.0, 0.0]
        self.enemy_vel = [0.0, 0.0]
        self.monster_attack_timer = 0.0
        self.hit_flash = 0.0
        self.enemy_turn_timer = 0.0
        self.last_click_time = 0.0

        self.hover_cell = None
        self.mining_cell = None
        self.mouse_down = False
        self.last_hit_time = 0.0

        self.last_frame_time = time.time()
        self.haste_until = 0.0
        self.second_wind_at = -9999.0
        self.shield_ready = False

        self._new_session(load_existing=False)

    # ------------------------------------------------------------------
    def _new_session(self, load_existing: bool):
        self.stones = StoneRegistry()
        self.ledger = StoneLedger()   # noms de pierres et bonus de faction, communs à tous les mineurs
        self.artifacts = ArtifactCatalog()
        self.world = WorldGenerator(self.stones, self.artifacts)
        self.player = Player()
        self.competitive_ai = CompetitiveAI()
        self.competitors = create_competitors(self.ai_difficulties, self.ledger)
        self.renderer.stones = self.stones
        self.renderer.ledger = self.ledger
        self.renderer.artifacts = self.artifacts
        self.renderer._texture_cache = {}
        self.particles = ParticleSystem(self.renderer.main_w, self.screen.get_height())

        self.war_log = []          # BattleReport
        self.war_cooldown = {}     # nom -> session_time jusqu'auquel il ne peut plus attaquer
        self.war_shield = {}       # nom -> session_time jusqu'auquel il est protégé
        self.war_selected = None   # index dans la liste des ennemis
        self.war_scene = None
        self.war_scene_report = None
        self.war_ai_timer = 0.0
        self.war_scene = None
        self.war_scene_report = None
        self.war_ctx = {}

        self.history = {"Toi": []}
        for ai in self.competitors:
            self.history[ai.name] = []
        self.history_time = []
        self.history_timer = 0.0
        self.session_time = 0.0
        self.chart_visible = {"Toi"}
        self.held_dirs = []

        if load_existing:
            save_manager.load_game(self.player, self.stones, self.artifacts, self.competitive_ai,
                                   self.competitors, world=self.world, ledger=self.ledger)

        self.pending_stone = None
        self.current_monster = None
        self.combat_log = []
        self.combat_target_block = None
        self.mining_cell = None
        self.mouse_down = False

    def _save(self):
        save_manager.save_game(self.player, self.stones, self.artifacts, self.competitive_ai,
                               self.competitors, world=self.world, ledger=self.ledger)
        self.has_save = True

    def _saved_or_current_difficulties(self):
        from src.ai.competitor import AI_PROFILES
        saved = save_manager.peek_ai_difficulties([p["name"] for p in AI_PROFILES])
        return saved or self.ai_difficulties

    def start_game(self, new: bool = False):
        """new=False : reprend la sauvegarde (difficultés relues depuis le fichier, donc
        verrouillées). new=True : nouvelle partie avec les difficultés choisies au menu,
        enregistrées immédiatement."""
        if not new:
            self.ai_difficulties = self._saved_or_current_difficulties()
        self._new_session(load_existing=not new)
        if new:
            self._save()
        self.menu_new_game = False
        self.autosave_timer = 0.0
        self.state = GameState.EXPLORING

    def restart_game(self):
        self._new_session(load_existing=False)
        self._save()
        self.state = GameState.EXPLORING
        self.flash_message("Nouvelle partie lancée !")

    def go_to_menu(self):
        self._save()
        self.menu_new_game = False
        self.ai_difficulties = self._saved_or_current_difficulties()
        self.state = GameState.MENU

    # ------------------------------------------------------------------
    def flash_message(self, text, sub=None, duration=2.2):
        self.message = (text, sub)
        self.message_until = time.time() + duration

    # ------------------------------------------------------------------
    def _attack_interval(self, now):
        iv = self.player.tool.attack_interval
        if now < self.haste_until:
            iv /= 1 + self.player.perks.get("haste_on_break", 0.0)
        return iv

    def _is_adjacent(self, row, col):
        p = self.player
        if row == p.row and col == p.col:
            return False
        return (row, col) in ((p.row, p.col - 1), (p.row, p.col + 1),
                             (p.row + 1, p.col), (p.row - 1, p.col))

    def _ascent_blocked(self, target_row):
        """On ne peut pas remonter à plus de MAX_ASCENT blocs au-dessus de la profondeur max atteinte."""
        return target_row < self.player.max_depth_reached - config.MAX_ASCENT

    def _warn_ascent(self):
        if not (self.message and time.time() < self.message_until):
            self.flash_message("Impossible de remonter plus haut.",
                               f"Limite : {config.MAX_ASCENT} blocs au-dessus de ta profondeur max.", duration=1.6)

    def try_move_zqsd(self, drow, dcol):
        target_row = self.player.row + drow
        target_col = self.player.col + dcol
        if target_row < 0 or not (0 <= target_col < config.GRID_COLS):
            return False
        if self._ascent_blocked(target_row):
            self._warn_ascent()
            return False
        block = self.world.get_block(target_row, target_col)
        if not block.is_empty:
            return False  # on ne peut se déplacer qu'à travers une galerie déjà creusée
        self.player.row, self.player.col = target_row, target_col
        self.player.max_depth_reached = max(self.player.max_depth_reached, target_row)
        return True

    def _update_held_direction(self, now):
        """Maintenir Z/Q/S/D : mine en continu dans cette direction, puis avance
        et enchaîne sur le bloc suivant dans la même direction (tunnel)."""
        if not self.held_dirs or self.state != GameState.EXPLORING:
            return
        drow, dcol = self.held_dirs[-1]
        target_row = self.player.row + drow
        target_col = self.player.col + dcol
        if target_row < 0 or not (0 <= target_col < config.GRID_COLS):
            return
        if self._ascent_blocked(target_row):
            self._warn_ascent()
            return
        block = self.world.get_block(target_row, target_col)

        if block.is_empty:
            self.try_move_zqsd(drow, dcol)
            self.last_hit_time = 0.0
            return

        if block.contains_monster:
            self.start_combat(block)
            return

        if now - self.last_hit_time >= self._attack_interval(now):
            self.last_hit_time = now
            self.apply_hit(target_row, target_col)

    def on_cell_pressed(self, row, col):
        if not self._is_adjacent(row, col):
            return
        if self._ascent_blocked(row):
            self._warn_ascent()
            return
        block = self.world.get_block(row, col)

        if block.is_empty:
            self.player.row, self.player.col = row, col
            self.player.max_depth_reached = max(self.player.max_depth_reached, row)
            return

        if block.contains_monster:
            self.start_combat(block)
            return

        self.mining_cell = (row, col)
        self.last_hit_time = 0.0

    def _cell_center_px(self, row, col):
        r = self.renderer
        row_screen = row - r.last_top_row
        x = r.grid_x + col * r.tile + r.tile // 2
        y = r.grid_y + row_screen * r.tile + r.tile // 2
        return x, y

    def apply_hit(self, row, col):
        block = self.world.get_block(row, col)
        if block.is_empty or block.contains_monster:
            self.mining_cell = None
            return

        if block.contains_artifact and not self.player.artifacts_unlocked:
            # avant le niveau requis, une pierre d'artefact n'est qu'une roche ordinaire
            mult = config.ARTIFACT_BLOCK_HARDNESS_MULT
            block.max_health /= mult
            block.health /= mult
            block.contains_artifact = None
            if not (self.message and time.time() < self.message_until):
                self.flash_message("Tu ne sais pas encore reconnaître les artefacts.",
                                   f"Niveau {config.LEVEL_ARTIFACTS} requis.", duration=2.0)

        # +10 % de vitesse de cassage sur les pierres découvertes par ta faction
        damage = self.player.mining_power * (1 + self.ledger.team_bonus(0, block.stone_id))
        crit = random.random() < self.player.perks.get("crit_chance", 0.0)
        if crit:
            damage *= 3
        broke = block.take_damage(damage)
        px, py = self._cell_center_px(row, col)
        if not broke:
            self.particles.spawn_hit_sparks(px, py, n=14 if crit else 4)
            return
        if crit:
            self.particles.spawn_hit_sparks(px, py, n=14)

        stone = self.stones.get_by_id(block.stone_id)
        self.particles.spawn_break(px, py, stone.base_color)

        first_discovery = self.stones.discover(block.stone_id)
        self.player.inventory.add_resource(block.stone_id, block.resource_amount)
        # or et XP : en moyenne proportionnels à la difficulté du bloc (petit aléa) ; pas d'or sur les pierres d'artefact
        block_gold = block.roll_gold(random) + self.player.block_gold_bonus
        earned = self.player.gain_gold(block_gold)
        if self.player.tool.add_xp(block.roll_xp(random) + self.player.block_xp_bonus):
            self.flash_message(f"Pioche niveau {self.player.tool.level} !",
                               f"Dégâts {self.player.tool.power:.1f} · cadence {self.player.tool.speed:.1f}/s",
                               duration=1.6)
        self.player.max_depth_reached = max(self.player.max_depth_reached, block.depth)

        # --- effets uniques des artefacts ---
        perks = self.player.perks
        self.player.blocks_broken += 1
        if random.random() < perks.get("gold_double_chance", 0.0):
            self.player.gain_gold(block_gold)
        if perks.get("jackpot") and self.player.blocks_broken % 10 == 0:
            self.player.gain_gold(block_gold * 3)
            self.flash_message("Jackpot !", "x4 d'or sur ce bloc", duration=1.4)
        if perks.get("regen_on_break"):
            self.player.heal(perks["regen_on_break"])
        if perks.get("haste_on_break"):
            self.haste_until = time.time() + 3.0

        got_artifact = False
        if block.contains_artifact:
            artifact_id, self.player.artifact_pity = self.artifacts.resolve_drop(
                block.contains_artifact, block.depth, self.player.artifact_pity,
                self.player.bonus_artifact_luck, random, self.player.new_artifact_flat)
            self.grant_artifact(artifact_id)
            got_artifact = True

        self.try_component_drop(block.depth, config.COMPONENT_DROP_CHANCE, announce=not got_artifact, hardness=block.hardness)

        self.mining_cell = None

        if first_discovery:
            entry = self.ledger.get(stone.stone_id)
            if entry is None:
                # premier mineur du monde à la trouver : c'est toi qui la nommes
                self.ledger.claim(stone.stone_id, "Toi", 0, f"Pierre de {stone.depth_tier}")
                self.pending_stone = stone
                self.text_input.open()
                self.state = GameState.NAMING_STONE
            else:
                stone.custom_name = entry["name"]
                mine = entry["team"] == 0 and stone.stone_id != config.STONE_NO_BONUS_ID
                self.flash_message(f"Pierre déjà nommée : {entry['name']}",
                                   f"Découverte par {entry['by']}" + (" · +10% de vitesse pour ta faction" if mine else ""),
                                   duration=3.0)

    def grant_artifact(self, artifact_id, announce=True):
        first = self.artifacts.mark_found(artifact_id)
        self.player.inventory.add_artifact(artifact_id)
        adef = self.artifacts.defs[artifact_id]
        if first and adef.bonus_type:
            self.player.apply_artifact_bonus(adef)
        if not announce:
            return
        if first:
            self.flash_message(f"Nouvel artefact : {adef.name}", adef.bonus_desc, duration=3.0)
        else:
            chance = self.artifacts.pity_chance(self.player.artifact_pity, self.player.bonus_artifact_luck,
                                                self.player.new_artifact_flat)
            self.flash_message(f"Doublon : {adef.name}",
                               f"Chance que le prochain artefact soit inédit : {chance * 100:.0f}%", duration=3.0)

    def _free_artifact(self):
        """Niveau 14 : offre l'artefact de plus faible niveau (profondeur minimale) non encore obtenu."""
        pool = [a for a in self.artifacts.defs.values() if a.artifact_id not in self.artifacts.found]
        if not pool:
            return None
        adef = min(pool, key=lambda a: a.min_depth)
        self.grant_artifact(adef.artifact_id, announce=False)
        return adef

    def _process_level_ups(self):
        p = self.player
        if not p.pending_levels:
            return
        levels, p.pending_levels = p.pending_levels, []
        lv, sub = levels[-1], ""
        for lv in levels:
            sub = config.LEVEL_UNLOCK_TEXT.get(lv, "")
            if lv == config.LEVEL_FREE_ARTIFACT:
                adef = self._free_artifact()
                if adef:
                    sub = f"Artefact offert : {adef.name}"
        title = f"Niveau {lv} !" if len(levels) == 1 else f"Niveau {lv} ! (+{len(levels)} niveaux)"
        self.flash_message(title, sub, duration=4.5)

    def try_component_drop(self, depth, chance, announce=True, hardness=1.0):
        cid = crafting.roll_component(depth, random, chance, self.player.bonus_component_luck, hardness=hardness)
        if not cid:
            return None
        self.player.inventory.add_component(cid)
        if announce:
            cdef = crafting.COMPONENTS[cid]
            self.flash_message(f"Composant trouvé : {cdef.name}", cdef.rarity, duration=2.0)
        return cid

    # ------------------------------------------------------------------
    # GUERRE ENTRE FACTIONS
    # ------------------------------------------------------------------
    def _enemy_list(self):
        return [ai for ai in self.competitors if ai.team != 0]

    def _items_of(self, name):
        """Objets d'un mineur pouvant perdre un palier en cas de défaite."""
        if name == "Toi":
            return self.player.war_items()
        for ai in self.competitors:
            if ai.name == name:
                return ai.war_items()
        return []

    def _inventory_of(self, name):
        if name == "Toi":
            return self.player.inventory
        for ai in self.competitors:
            if ai.name == name:
                return ai.inventory
        return None

    def _register_war(self, rep):
        self.war_log.append(rep)
        self.war_log = self.war_log[-40:]

    def _do_war(self, att_name, def_name):
        """Bataille sans affichage (attaques des IA) : même simulation, menée jusqu'au bout."""
        self.war_cooldown[att_name] = self.session_time + config.WAR_ATTACK_COOLDOWN
        self.war_shield[def_name] = self.session_time + config.WAR_TARGET_SHIELD
        rep = faction_war.resolve_attack(att_name, self._inventory_of(att_name),
                                         def_name, self._inventory_of(def_name), self._items_of(def_name))
        self.player.clamp_health()
        self._register_war(rep)
        return rep

    def launch_attack(self):
        if not self.player.workshop_unlocked:
            self.flash_message("L'atelier n'est pas encore fonctionnel.", f"Niveau {config.LEVEL_WORKSHOP} requis.")
            return
        enemies = self._enemy_list()
        if self.war_selected is None or not (0 <= self.war_selected < len(enemies)):
            self.flash_message("Choisis d'abord une faction ennemie à attaquer.")
            return
        target = enemies[self.war_selected]
        inv = self.player.inventory
        if crafting.army_totals(inv)["count"] <= 0:
            self.flash_message("Il te faut au moins une troupe.", "Fabrique-en à l'Atelier.")
            return
        left = self.war_cooldown.get("Toi", 0) - self.session_time
        if left > 0:
            self.flash_message("Tes troupes se reposent encore.", f"Prochaine attaque dans {int(left) + 1} s.")
            return
        shield = self.war_shield.get(target.name, 0) - self.session_time
        if shield > 0:
            self.flash_message(f"{target.name} est protégé.", f"Encore {int(shield) + 1} s.")
            return
        self.war_cooldown["Toi"] = self.session_time + config.WAR_ATTACK_COOLDOWN
        self.war_shield[target.name] = self.session_time + config.WAR_TARGET_SHIELD
        sim = faction_war.start_battle(inv, target.inventory, record_events=True)
        self.war_ctx = {"att": "Toi", "def": target.name, "role": "att"}
        self._open_war_scene(WarScene(sim, "Tes troupes", f"{target.name} (donjon d'archer)",
                                      (255, 214, 150), target.color, player_role="att"))

    def _open_war_scene(self, scene):
        self.war_scene_report = None
        self.war_scene = scene
        self.held_dirs = []
        self.mouse_down = False
        self.mining_cell = None
        self.state = GameState.WAR_SCENE

    def _finalize_player_battle(self):
        """Applique le résultat de la bataille : c'est la simulation qui décide pertes et vainqueur."""
        if self.war_scene is None or self.war_scene_report is not None:
            return
        ctx = self.war_ctx
        rep = faction_war.finalize_battle(self.war_scene.sim, ctx["att"], self._inventory_of(ctx["att"]),
                                          ctx["def"], self._inventory_of(ctx["def"]), self._items_of(ctx["def"]))
        self.player.clamp_health()
        self.war_scene_report = rep
        self.war_scene.report = rep
        self._register_war(rep)

    def close_war_scene(self):
        rep = self.war_scene_report
        self.war_scene = None
        self.state = GameState.EXPLORING
        if rep is not None:
            extra = f" · {rep.broken}" if rep.broken else ""
            if self.war_ctx.get("role") == "def":
                if rep.attacker_won:
                    self.flash_message(f"{rep.attacker} t'a vaincu !", f"-{int(rep.loot)} or{extra}", duration=4.0)
                else:
                    self.flash_message("Défense réussie !", f"{rep.attacker} repoussé.", duration=3.0)
            elif rep.attacker_won:
                self.flash_message("Victoire !", f"{rep.defender} battu · +{int(rep.loot)} or{extra}", duration=4.0)
            else:
                self.flash_message("Défaite...", f"{rep.defender} a tenu bon.", duration=3.0)

    def try_tower_upgrade(self, key):
        if not self.player.tower_track_unlocked(key):
            self.flash_message("Amélioration verrouillée.", f"Niveau {config.TOWER_TRACK_UNLOCK.get(key, 10)} requis.")
            return
        inv = self.player.inventory
        cost = tower_mod.upgrade_cost(inv.tower, key)
        if cost < 0:
            self.flash_message("Niveau maximum atteint.")
        elif tower_mod.upgrade(inv, key):
            self.flash_message(f"Donjon amélioré : {tower_mod.TRACKS[key]['label']}",
                               f"Niveau {inv.tower[key]}/{tower_mod.TRACKS[key]['max']}", duration=2.0)
        else:
            self.flash_message("Pas assez d'or.", f"Il faut {cost} or.")

    def _update_ai_wars(self, dt):
        """Les IA attaquent parfois les factions adverses (et toi) quand elles se jugent plus fortes."""
        if self.state == GameState.WAR_SCENE:
            return
        self.war_ai_timer += dt
        if self.war_ai_timer < config.WAR_AI_INTERVAL:
            return
        self.war_ai_timer = 0.0
        now = self.session_time
        attackers = [ai for ai in self.competitors
                     if self.war_cooldown.get(ai.name, 0) <= now
                     and crafting.army_totals(ai.inventory)["count"] > 0]
        random.shuffle(attackers)
        done = 0
        for ai in attackers:
            if done >= 2:
                break
            if random.random() > 0.15 + 0.5 * ai.risk_tolerance:
                continue
            my_power = faction_war.force_power(ai.inventory.units)
            cands = [(t.name, t.inventory) for t in self.competitors if t.team != ai.team]
            if ai.team != 0 and self.state == GameState.EXPLORING and self.player.workshop_unlocked:   # pas d'attaque avant que l'atelier soit débloqué
                cands.append(("Toi", self.player.inventory))
            targets = [name for name, inv in cands
                       if self.war_shield.get(name, 0) <= now
                       and faction_war.defense_power(inv) <= my_power * (0.7 + ai.risk_tolerance * 0.8)]
            if not targets:
                continue
            target = random.choice(targets)
            if target == "Toi":
                # tu assistes à la bataille : tes troupes et ton donjon défendent en direct
                self.war_cooldown[ai.name] = now + config.WAR_ATTACK_COOLDOWN
                self.war_shield["Toi"] = now + config.WAR_TARGET_SHIELD
                sim = faction_war.start_battle(ai.inventory, self.player.inventory, record_events=True)
                self.war_ctx = {"att": ai.name, "def": "Toi", "role": "def"}
                self._open_war_scene(WarScene(sim, ai.name, "Tes troupes et ton donjon", ai.color,
                                              (255, 214, 150), player_role="def"))
                return
            self._do_war(ai.name, target)
            done += 1

    def craft_unit(self, recipe_id):
        if not self.player.workshop_unlocked:
            self.flash_message("L'atelier n'est pas encore fonctionnel.", f"Niveau {config.LEVEL_WORKSHOP} requis.")
            return
        recipe = crafting.RECIPES_BY_ID.get(recipe_id)
        if recipe is None:
            return
        if crafting.craft(self.player.inventory, recipe_id):
            self.flash_message(f"Fabriqué : {recipe.name}",
                               f"Tu en possèdes {self.player.inventory.units[recipe_id]}", duration=2.0)
        else:
            self.flash_message("Composants insuffisants.")

    def sell_component(self, cid):
        if not self.player.can_sell:
            self.flash_message("Vente verrouillée.", f"Niveau {config.LEVEL_SELL} requis.")
            return
        price = crafting.sell_price(cid)
        if crafting.sell_component(self.player.inventory, cid):
            self.flash_message(f"Vendu : {crafting.COMPONENTS[cid].name}", f"+{price} or", duration=1.2)
        else:
            self.flash_message("Tu n'en possèdes pas.", duration=1.2)

    def buy_component(self, cid):
        if not self.player.can_buy:
            self.flash_message("Achat verrouillé.", f"Niveau {config.LEVEL_BUY} requis.")
            return
        if crafting.COMPONENTS[cid].min_depth > self.player.max_depth_reached:
            self.flash_message("Ce composant n'est pas encore disponible.", "Descends plus profond.")
            return
        price = crafting.buy_price(cid)
        if crafting.buy_component(self.player.inventory, cid):
            self.flash_message(f"Acheté : {crafting.COMPONENTS[cid].name}", f"-{price} or", duration=1.2)
        else:
            self.flash_message("Pas assez d'or.", f"Il faut {price} or.", duration=1.5)

    def confirm_stone_name(self):
        name = self.text_input.text.strip() or f"Pierre de {self.pending_stone.depth_tier}"
        self.stones.name_stone(self.pending_stone.stone_id, name)
        self.ledger.rename(self.pending_stone.stone_id, name)
        bonus = self.pending_stone.stone_id != config.STONE_NO_BONUS_ID
        self.flash_message(f"Tu as nommé cette pierre : {name}",
                           "+10% de vitesse de cassage sur cette pierre pour ta faction" if bonus else None,
                           duration=3.0)
        self.pending_stone = None
        self.text_input.close()
        self.state = GameState.EXPLORING

    # ------------------------------------------------------------------
    def start_combat(self, block):
        aggressiveness = self.competitive_ai.aggressiveness_for(block.depth)
        self.current_monster = spawn_monster(block.depth, aggressiveness)
        self.combat_target_block = block
        self.combat_log = [f"Un {self.current_monster.name} surgit de la roche !"]

        arena = self.renderer.get_combat_arena_rect()
        self.enemy_pos = [arena.centerx, arena.centery]
        ang = random.uniform(0, math.tau)
        speed = self.current_monster.speed
        self.enemy_vel = [math.cos(ang) * speed, math.sin(ang) * speed]
        self.monster_attack_timer = self.current_monster.attack_interval
        self.shield_ready = self.player.perks.get("block_first_hit", 0) > 0
        self.enemy_turn_timer = random.uniform(0.5, 1.2)
        self.hit_flash = 0.0
        self.state = GameState.COMBAT

    def _update_combat(self, dt):
        arena = self.renderer.get_combat_arena_rect()
        monster = self.current_monster
        radius = 42 if monster.is_boss else 30

        # le monstre change brusquement de direction et de vitesse (sprints)
        self.enemy_turn_timer -= dt
        if self.enemy_turn_timer <= 0:
            self.enemy_turn_timer = random.uniform(0.4, 1.1)
            ang = random.uniform(0, math.tau)
            speed = monster.speed * random.uniform(0.8, 1.6)
            self.enemy_vel = [math.cos(ang) * speed, math.sin(ang) * speed]

        self.enemy_pos[0] += self.enemy_vel[0] * dt
        self.enemy_pos[1] += self.enemy_vel[1] * dt
        if self.enemy_pos[0] - radius < arena.left or self.enemy_pos[0] + radius > arena.right:
            self.enemy_vel[0] *= -1
            self.enemy_pos[0] = max(arena.left + radius, min(arena.right - radius, self.enemy_pos[0]))
        if self.enemy_pos[1] - radius < arena.top or self.enemy_pos[1] + radius > arena.bottom:
            self.enemy_vel[1] *= -1
            self.enemy_pos[1] = max(arena.top + radius, min(arena.bottom - radius, self.enemy_pos[1]))

        self.hit_flash = max(0.0, self.hit_flash - dt * 4)

        self.monster_attack_timer -= dt
        if self.monster_attack_timer <= 0:
            self.monster_attack_timer = monster.attack_interval
            if self.shield_ready:
                self.shield_ready = False
                self.combat_log.append("Ton égide ancestrale absorbe le premier coup !")
            else:
                result = combat.CombatResult()
                combat.monster_auto_attack(self.player, monster, result)
                self.combat_log.extend(result.log)
                if result.finished:
                    self.end_combat(won=False)

    def combat_click_attack(self, pos):
        now = time.time()
        if now - self.last_click_time < config.MONSTER_HIT_COOLDOWN:
            return
        enemy_rect = self.renderer.rects.get("combat_enemy")
        if not enemy_rect or not enemy_rect.collidepoint(pos):
            return
        self.last_click_time = now
        self.hit_flash = 1.0
        self.particles.spawn_hit_sparks(*pos, n=6)

        result = combat.CombatResult()
        combat.player_attack(self.player, self.current_monster, result)
        self.combat_log.extend(result.log)
        if result.events:
            self.flash_message(result.events[0], duration=1.4)
        if result.finished and result.player_won:
            self.end_combat(won=True)

    def combat_flee(self):
        result = combat.CombatResult()
        combat.player_flee(self.player, result)
        self.combat_log.extend(result.log)
        if result.finished:
            self.state = GameState.EXPLORING
            self.current_monster = None

    def end_combat(self, won: bool):
        hp_ratio = self.player.health / self.player.max_health
        self.competitive_ai.update_after_fight(self.combat_target_block.depth, won, hp_ratio)
        if won:
            self.combat_target_block.is_empty = True
            self.combat_target_block.contains_monster = False
            gold_reward = (5 + self.combat_target_block.depth // 10) * (1 + self.player.perks.get("monster_gold_mult", 0.0))
            earned = self.player.gain_gold(gold_reward)
            if self.player.perks.get("heal_on_kill"):
                self.player.heal(self.player.max_health * self.player.perks["heal_on_kill"])
            sub = f"+{int(earned)} or"
            cid = self.try_component_drop(self.combat_target_block.depth,
                                          config.COMPONENT_MONSTER_DROP_CHANCE, announce=False)
            if cid:
                sub += f" · {crafting.COMPONENTS[cid].name}"
                cid2 = self.try_component_drop(self.combat_target_block.depth,
                                               config.COMPONENT_MONSTER_BONUS_CHANCE, announce=False)
                if cid2:
                    sub += f" + {crafting.COMPONENTS[cid2].name}"
            self.flash_message("Victoire !", sub)
        else:
            self.player.alive = True
            if (self.player.perks.get("second_wind") and self.session_time - self.second_wind_at >= 240.0):
                # Souffle des ancêtres : pas de pénalité
                self.second_wind_at = self.session_time
                self.player.health = self.player.max_health // 2
                self.flash_message("Souffle des ancêtres !", "Tu te relèves sans rien perdre.", duration=3.5)
            else:
                lost = self.player.apply_death_penalty()
                self.player.health = self.player.max_health // 2
                self.flash_message("Tu as été vaincu...",
                                   f"-{lost} or · XP en cours de tous tes objets perdue", duration=4.5)
        self.current_monster = None
        self.state = GameState.EXPLORING

    def _handle_chart_click(self, pos):
        for key, rect in self.renderer.rects.items():
            if rect.collidepoint(pos):
                if key.startswith("chart_check_"):
                    name = key[len("chart_check_"):]
                    if name in self.chart_visible:
                        self.chart_visible.discard(name)
                    else:
                        self.chart_visible.add(name)
                elif key.startswith("chart_stat_"):
                    self.chart_stat = key[len("chart_stat_"):]
                elif key == "chart_all":
                    self.chart_visible = {"Toi"} | {ai.name for ai in self.competitors}
                elif key == "chart_none":
                    self.chart_visible = set()
                elif key == "chart_close":
                    self.show_chart = False
                return

    def _record_history(self):
        self.history_time.append(round(self.session_time))
        self.history["Toi"].append(self._stat_values_player())
        for ai in self.competitors:
            self.history[ai.name].append(self._stat_values_ai(ai))
        if len(self.history_time) > config.HISTORY_MAX_POINTS:
            self.history_time.pop(0)
            for series in self.history.values():
                if series:
                    series.pop(0)

    def _stat_values_player(self):
        score = (self.player.row * 2 + self.player.inventory.gold * 0.5
                 + len(self.artifacts.found) * 20 + len(self.stones.all_discovered()) * 4
                 + self.player.inventory.war_wins * config.WAR_WIN_SCORE)
        return {"depth": self.player.row, "gold": self.player.inventory.gold, "score": score}

    def _stat_values_ai(self, ai):
        return {"depth": ai.state.row, "gold": ai.inventory.gold, "score": ai.score()}

    # ------------------------------------------------------------------
    def try_upgrade(self, equip):
        if not equip.enabled:
            self.flash_message("Équipement verrouillé.", "Monte de niveau pour le débloquer.")
            return
        cost = equip.upgrade_cost()
        if cost < 0:
            self.flash_message("Niveau déjà maximum.")
            return
        if self.player.inventory.spend_gold(cost):
            equip.upgrade()
            self.flash_message(f"Amélioration : {equip.name}", equip.skin_description, duration=3.0)
        else:
            self.flash_message("Pas assez d'or.", f"Il faut {cost} or.")

    # ------------------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.quit()

        if event.type == pygame.MOUSEWHEEL:
            if self.state in (GameState.EXPLORING, GameState.COMBAT) and not self.show_chart:
                self.renderer.on_wheel(pygame.mouse.get_pos(), event.y)
            return

        if self.state == GameState.WAR_SCENE and self.war_scene:
            close = False
            if event.type == pygame.KEYDOWN:
                close = self.war_scene.handle_key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                close = self.war_scene.handle_click(event.pos)
            if close:
                self._finalize_player_battle()
                self.close_war_scene()
            return

        if self.state == GameState.MENU:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_menu_click(event.pos)
            return

        if self.state == GameState.PAUSED:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = self.state_before_pause
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_pause_click(event.pos)
            return

        if self.show_chart:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_g, pygame.K_ESCAPE):
                self.show_chart = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_chart_click(event.pos)
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.state == GameState.EXPLORING:
            self.state_before_pause = self.state
            self.state = GameState.PAUSED
            return

        if self.state == GameState.NAMING_STONE:
            if self.text_input.handle_event(event):
                self.confirm_stone_name()
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F5:
                self._save()
                self.flash_message("Partie sauvegardée.")
            if self.state == GameState.EXPLORING:
                if event.key == pygame.K_u:
                    self.try_upgrade(self.player.tool)
                elif event.key == pygame.K_g:
                    self.show_chart = not self.show_chart
            if event.key in (pygame.K_z, pygame.K_q, pygame.K_s, pygame.K_d) and self.state == GameState.EXPLORING:
                d = {pygame.K_z: (-1, 0), pygame.K_s: (1, 0), pygame.K_q: (0, -1), pygame.K_d: (0, 1)}[event.key]
                if d not in self.held_dirs:
                    self.held_dirs.append(d)
                self.last_hit_time = 0.0
            if self.state == GameState.COMBAT and event.key == pygame.K_f:
                self.combat_flee()

        if event.type == pygame.KEYUP and event.key in (pygame.K_z, pygame.K_q, pygame.K_s, pygame.K_d):
            d = {pygame.K_z: (-1, 0), pygame.K_s: (1, 0), pygame.K_q: (0, -1), pygame.K_d: (0, 1)}[event.key]
            if d in self.held_dirs:
                self.held_dirs.remove(d)

        if event.type == pygame.MOUSEMOTION:
            self.hover_cell = self.renderer.screen_to_cell(*event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.mouse_down = True
            self._handle_click(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.mouse_down = False
            self.mining_cell = None

    def _handle_menu_click(self, pos):
        # difficulté verrouillée tant qu'une partie existe (sauf si on lance une nouvelle partie)
        locked = self.has_save and not self.menu_new_game
        for key, rect in self.renderer.rects.items():
            if rect.collidepoint(pos):
                if key.startswith(("aidiff_", "diff_all_")) and locked:
                    return
                if key.startswith("aidiff_"):
                    idx = int(key[len("aidiff_"):])
                    diffs = list(config.DIFFICULTIES.keys())
                    cur = self.ai_difficulties[idx]
                    nxt = diffs[(diffs.index(cur) + 1) % len(diffs)]
                    self.ai_difficulties[idx] = nxt
                elif key == "diff_all_facile":
                    self.ai_difficulties = ["Facile"] * len(self.ai_difficulties)
                elif key == "diff_all_normal":
                    self.ai_difficulties = ["Normal"] * len(self.ai_difficulties)
                elif key == "diff_all_difficile":
                    self.ai_difficulties = ["Difficile"] * len(self.ai_difficulties)
                elif key == "btn_continue":
                    self.start_game(new=False)
                elif key == "btn_newgame":
                    self.menu_new_game = True
                elif key == "btn_cancel_new":
                    self.menu_new_game = False
                    self.ai_difficulties = self._saved_or_current_difficulties()
                elif key == "btn_start":
                    self.start_game(new=True)
                return

    def _handle_pause_click(self, pos):
        for key, rect in self.renderer.rects.items():
            if rect.collidepoint(pos):
                if key == "btn_resume":
                    self.state = self.state_before_pause
                elif key == "btn_restart":
                    self.restart_game()
                elif key == "btn_menu":
                    self.go_to_menu()
                elif key == "btn_quit":
                    self.quit()
                return

    def _handle_click(self, pos):
        for key, rect in self.renderer.rects.items():
            if rect.collidepoint(pos):
                if key.startswith("tab_"):
                    self.renderer.active_tab = key[len("tab_"):]
                    return
                if key.startswith("subtab_"):
                    self.renderer.active_equip = key[len("subtab_"):]
                    return
                if key.startswith("teamfilter_"):
                    val = key[len("teamfilter_"):]
                    self.renderer.team_filter = None if val == "None" else int(val)
                    return
                if key.startswith("wsub_"):
                    self.renderer.active_workshop = key[len("wsub_"):]
                    return
                if key.startswith("wartarget_"):
                    self.war_selected = int(key[len("wartarget_"):])
                    return
                if key == "war_attack" and self.state == GameState.EXPLORING:
                    self.launch_attack()
                    return
                if key.startswith("towerup_") and self.state == GameState.EXPLORING:
                    self.try_tower_upgrade(key[len("towerup_"):])
                    return
                if key.startswith("sell_") and self.state == GameState.EXPLORING:
                    self.sell_component(key[len("sell_"):])
                    return
                if key.startswith("buy_") and self.state == GameState.EXPLORING:
                    self.buy_component(key[len("buy_"):])
                    return
                if key.startswith("craft_") and self.state == GameState.EXPLORING:
                    self.craft_unit(key[len("craft_"):])
                    return
                if key.startswith("btn_upgrade_") and self.state == GameState.EXPLORING:
                    attr = key[len("btn_upgrade_"):]
                    if attr in ("tool", "helmet", "armor", "aura", "amulet", "gauntlet"):
                        self.try_upgrade(getattr(self.player, attr))
                    return
                if key == "btn_flee" and self.state == GameState.COMBAT:
                    self.combat_flee()
                    return
                if key in ("btn_restart", "btn_menu") and self.state == GameState.GAME_OVER:
                    self.restart_game() if key == "btn_restart" else self.go_to_menu()
                    return

        if self.state == GameState.COMBAT:
            self.combat_click_attack(pos)
            return

        if self.state != GameState.EXPLORING:
            return
        cell = self.renderer.screen_to_cell(*pos)
        if cell:
            self.on_cell_pressed(*cell)

    # ------------------------------------------------------------------
    def update(self):
        now = time.time()
        dt = min(0.05, now - self.last_frame_time)
        self.last_frame_time = now

        if self.state in (GameState.MENU, GameState.PAUSED):
            return

        self.session_time += dt
        self.autosave_timer += dt
        if self.autosave_timer >= config.AUTOSAVE_INTERVAL:
            self.autosave_timer = 0.0
            self._save()
        self.history_timer += dt
        if self.history_timer >= config.HISTORY_INTERVAL:
            self.history_timer = 0.0
            self._record_history()

        self.particles.update(dt)
        for ai in self.competitors:
            ai.tick(dt)
        self._update_ai_wars(dt)
        self._process_level_ups()

        if self.player.alive:
            self.player.passive_regen(dt)

        if not self.player.alive and self.state != GameState.GAME_OVER:
            self.state = GameState.GAME_OVER
            return

        if self.state == GameState.WAR_SCENE and self.war_scene:
            self.war_scene.update(dt)
            if self.war_scene.finished:
                self._finalize_player_battle()
            return

        if self.state == GameState.COMBAT and self.current_monster:
            self._update_combat(dt)
            return

        if self.state == GameState.EXPLORING:
            if self.mouse_down and self.mining_cell:
                if self.hover_cell != self.mining_cell:
                    self.mining_cell = None
                elif now - self.last_hit_time >= self._attack_interval(now):
                    self.last_hit_time = now
                    self.apply_hit(*self.mining_cell)
            elif self.held_dirs:
                self._update_held_direction(now)

    # ------------------------------------------------------------------
    def draw(self):
        if self.state == GameState.MENU:
            self.renderer.draw_menu(self.ai_difficulties, locked=self.has_save and not self.menu_new_game,
                                    has_save=self.has_save)
            pygame.display.flip()
            return

        self.renderer.draw_background(self.player.row, self.particles)
        self.renderer.draw_grid(self.world, self.player, self.hover_cell, self.mining_cell)
        self.particles.draw_particles(self.screen)
        self.renderer.draw_top_bar(self.player)
        now = self.session_time
        self.renderer.war_info = {
            "selected": self.war_selected, "log": self.war_log,
            "cooldown_left": max(0.0, self.war_cooldown.get("Toi", 0) - now),
            "shields": {n: v - now for n, v in self.war_shield.items() if v > now},
        }
        self.renderer.draw_side_panel(self.player, self.stones, self.artifacts, self.competitive_ai, self.competitors)

        if self.message and time.time() < self.message_until:
            self.renderer.draw_message(*self.message)

        if self.state == GameState.NAMING_STONE and self.pending_stone:
            self.renderer.draw_naming_dialog(self.pending_stone, self.text_input,
                                             self.pending_stone.stone_id != config.STONE_NO_BONUS_ID)
        elif self.state == GameState.COMBAT and self.current_monster:
            self.renderer.draw_combat(self.player, self.current_monster, self.combat_log, self.enemy_pos, self.hit_flash)
        elif self.state == GameState.WAR_SCENE and self.war_scene:
            self.war_scene.draw(self.renderer)
        elif self.state == GameState.GAME_OVER:
            self.renderer.draw_game_over()
        elif self.state == GameState.PAUSED:
            self.renderer.draw_paused()

        if self.show_chart:
            self.renderer.draw_chart(self.history_time, self.history, self.chart_visible,
                                      self.chart_stat, self.player, self.competitors)

        pygame.display.flip()

    # ------------------------------------------------------------------
    def quit(self):
        if self.state == GameState.WAR_SCENE and self.war_scene:
            self.war_scene.skip()
            self._finalize_player_battle()
        if self.state not in (GameState.MENU,):
            self._save()
        pygame.quit()
        sys.exit()

    def run(self):
        while True:
            for event in pygame.event.get():
                self.handle_event(event)
            self.update()
            self.draw()
            self.clock.tick(config.FPS)


if __name__ == "__main__":
    Game().run()
