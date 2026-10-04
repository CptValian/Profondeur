"""Compagnon de mine autonome (débloqué au niveau 15)."""

import math
import random
from src import config
from src.items import crafting

COMPANION_TIERS = [
    {"name": "Drone Rouillé",        "color": (150, 130, 110), "speed_bonus": 0.0},
    {"name": "Automate de Bronze",  "color": (200, 140, 80),  "speed_bonus": 0.2},
    {"name": "Foreuse en Fer",       "color": (175, 178, 188), "speed_bonus": 0.4},
    {"name": "Golem Mécanique",     "color": (210, 215, 225), "speed_bonus": 0.7},
    {"name": "Excavateur de Cristal","color": (100, 220, 240), "speed_bonus": 1.0},
    {"name": "Mineur Runique",      "color": (120, 160, 255), "speed_bonus": 1.4},
    {"name": "Automate en Mithril", "color": (160, 220, 255), "speed_bonus": 1.8},
    {"name": "Construct Abyssal",   "color": (170, 90, 240),  "speed_bonus": 2.3},
    {"name": "Garde Solaire",       "color": (255, 190, 80),  "speed_bonus": 2.9},
    {"name": "Automate Stellaire",  "color": (255, 230, 140), "speed_bonus": 3.6},
    {"name": "Pionnier de l'Infini","color": (255, 255, 255), "speed_bonus": 4.5},
]


class MiningCompanion:
    def __init__(self):
        self.gold_tier = 0
        self.level = 1
        self.xp = 0.0
        self.row = 0
        self.col = config.GRID_COLS // 2
        self.attack_timer = 0.0

    @property
    def max_gold_tier(self) -> int:
        return len(COMPANION_TIERS) - 1

    @property
    def max_level(self) -> int:
        return 100

    @property
    def name(self) -> str:
        return COMPANION_TIERS[self.gold_tier]["name"]

    @property
    def color(self):
        return COMPANION_TIERS[self.gold_tier]["color"]

    def gold_upgrade_cost(self) -> int:
        if self.gold_tier >= self.max_gold_tier:
            return -1
        return int(120 * (2.2 ** self.gold_tier))

    def upgrade_gold(self, player) -> bool:
        cost = self.gold_upgrade_cost()
        if cost > 0 and player.inventory.spend_gold(cost):
            self.gold_tier += 1
            return True
        return False

    @property
    def hits_per_second(self) -> float:
        """Les améliorations en or augmentent la vitesse de minage (coups par seconde)."""
        base = 0.8
        bonus = COMPANION_TIERS[self.gold_tier]["speed_bonus"]
        return round(base + bonus, 2)

    @property
    def attack_interval(self) -> float:
        return 1.0 / max(0.1, self.hits_per_second)

    @property
    def mining_power(self) -> float:
        """Les niveaux d'XP augmentent les dégâts par coup contre les blocs."""
        return round(1.0 + self.gold_tier * 0.5 + (self.level - 1) * 0.6, 1)

    def xp_to_next_level(self) -> float:
        return round(100.0 * (self.level ** 1.5), 1)

    def add_xp(self, amount: float) -> bool:
        if self.level >= self.max_level or amount <= 0:
            return False
        self.xp += amount
        leveled = False
        while self.level < self.max_level and self.xp >= self.xp_to_next_level():
            self.xp -= self.xp_to_next_level()
            self.level += 1
            leveled = True
        if self.level >= self.max_level:
            self.xp = 0.0
        return leveled

    def tick(self, dt: float, player, world, ledger, stones, artifacts, particle_cb=None) -> list:
        msgs = []
        if not player.has_companion:
            return msgs

        self.attack_timer -= dt
        if self.attack_timer > 0:
            return msgs

        self.attack_timer += self.attack_interval

        # Recherche des cases adjacentes valides à miner (pas de monstre, pas vide)
        cands = []
        for drow, dcol in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            tr, tc = self.row + drow, self.col + dcol
            if tr < 0 or not (0 <= tc < config.GRID_COLS):
                continue
            block = world.get_block(tr, tc)
            if block.is_empty or block.contains_monster:
                continue
            dist_to_player = math.hypot(tr - player.row, tc - player.col)
            cands.append((dist_to_player, tr, tc, block))

        if not cands:
            # Si aucun bloc adjacent à miner, se déplace vers le joueur à travers les galeries creusées
            best_move = None
            best_dist = math.hypot(self.row - player.row, self.col - player.col)
            for drow, dcol in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                tr, tc = self.row + drow, self.col + dcol
                if tr < 0 or not (0 <= tc < config.GRID_COLS):
                    continue
                b = world.get_block(tr, tc)
                if b.is_empty:
                    d = math.hypot(tr - player.row, tc - player.col)
                    if d < best_dist:
                        best_dist = d
                        best_move = (tr, tc)
            if best_move:
                self.row, self.col = best_move
            return msgs

        # Trie pour attaquer le bloc le plus proche du joueur
        cands.sort(key=lambda x: x[0])
        _, tr, tc, block = cands[0]

        damage = self.mining_power * (1 + ledger.team_bonus(0, block.stone_id))
        broke = block.take_damage(damage)

        if self.add_xp(damage * 0.25):
            msgs.append(f"{self.name} : niveau {self.level} !")

        if broke:
            stone = stones.get_by_id(block.stone_id)
            first_discovery = stones.discover(block.stone_id)
            player.inventory.add_resource(block.stone_id, block.resource_amount)
            block_gold = block.roll_gold(random) + player.block_gold_bonus
            player.gain_gold(block_gold)

            if block.contains_xp_stone:
                player.inventory.xp_stones += 1
                msgs.append("Le compagnon a déterré une Pierre d'XP !")

            if block.contains_artifact:
                art_id, player.artifact_pity = artifacts.resolve_drop(
                    block.contains_artifact, block.depth, player.artifact_pity,
                    player.bonus_artifact_luck, random, player.new_artifact_flat)
                first = artifacts.mark_found(art_id)
                player.inventory.add_artifact(art_id)
                adef = artifacts.defs[art_id]
                if first and adef.bonus_type:
                    player.apply_artifact_bonus(adef)
                    msgs.append(f"Compagnon : Nouvel artefact trouvé ({adef.name}) !")

            cid = crafting.roll_component(block.depth, random, config.COMPONENT_DROP_CHANCE, player.bonus_component_luck, hardness=block.hardness)
            if cid:
                player.inventory.add_component(cid)

            # Se déplace sur la case nouvellement creusée
            self.row, self.col = tr, tc

        return msgs
