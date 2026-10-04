"""Le mineur incarné par le joueur."""

from collections import defaultdict

from src import config
from src.items.artifact import artifact_effects
from src.items.tool import Tool
from src.items.equipment import Helmet, Armor, Aura, Amulet, Gauntlet
from src.items.inventory import Inventory
from src.entities.companion import MiningCompanion
from src.entities.hero import Hero


class Player:
    def __init__(self):
        # niveau de mineur : alimenté par TOUTE l'XP gagnée par la pioche et les équipements
        self.level = 1
        self.xp = 0.0
        self.pending_levels = []          # niveaux franchis, à annoncer par le jeu

        self.row = 0                      # profondeur actuelle (rangée)
        self.col = config.GRID_COLS // 2  # colonne actuelle
        self.base_max_health = config.PLAYER_START_HEALTH
        self.health = self.base_max_health
        self.tool = Tool(tier=0)
        self.helmet = Helmet(tier=0)
        self.armor = Armor(tier=0)
        self.aura = Aura(tier=0)
        self.amulet = Amulet(tier=0)
        self.gauntlet = Gauntlet(tier=0)   # dégâts bonus contre les monstres (XP en combat uniquement)
        self.inventory = Inventory()
        self.companion = MiningCompanion()
        self.hero = Hero()
        self.max_depth_reached = 0
        # bonus cumulés venant des artefacts
        self.bonus_mining_power = 0.0
        self.bonus_mining_power_pct = 0.0
        self.bonus_artifact_luck = 0.0
        self.bonus_max_health = 0.0
        self.bonus_damage_reduction = 0.0
        self.bonus_gold_pct = 0.0
        self.bonus_combat_damage = 0.0
        self.bonus_component_luck = 0.0
        self.artifact_pity = 0   # doublons d'artefacts d'affilée
        self.perks = defaultdict(float)   # effets uniques des artefacts (crit, jackpot, second souffle...)
        self.blocks_broken = 0
        self.alive = True

        for it in (self.tool,) + self.equipment_items():
            it.xp_listener = self.gain_player_xp
        self.refresh_unlocks()

    # ------------------------------------------------------------------
    # NIVEAUX DE MINEUR
    # ------------------------------------------------------------------
    def xp_to_next_level(self) -> float:
        return config.PLAYER_XP_BASE * (self.level ** config.PLAYER_XP_EXPONENT)

    def gain_player_xp(self, amount: float):
        if amount <= 0 or self.level >= config.PLAYER_MAX_LEVEL:
            return
        self.xp += amount
        leveled = False
        while self.level < config.PLAYER_MAX_LEVEL and self.xp >= self.xp_to_next_level():
            self.xp -= self.xp_to_next_level()
            self.level += 1
            self.pending_levels.append(self.level)
            leveled = True
        if self.level >= config.PLAYER_MAX_LEVEL:
            self.xp = 0.0
        if leveled:
            self.refresh_unlocks()

    def set_total_xp(self, total: float):
        """Migration d'ancienne sauvegarde : recalcule niveau et XP depuis un total."""
        self.level, self.xp = 1, float(total)
        while self.level < config.PLAYER_MAX_LEVEL and self.xp >= self.xp_to_next_level():
            self.xp -= self.xp_to_next_level()
            self.level += 1
        if self.level >= config.PLAYER_MAX_LEVEL:
            self.xp = 0.0

    def refresh_unlocks(self):
        """Active/désactive les équipements selon le niveau, et applique les multiplicateurs d'XP."""
        for key, lv in config.LEVEL_EQUIP_UNLOCK.items():
            if key != "tool":
                getattr(self, key).enabled = self.level >= lv
        self.refresh_xp_mult()

    @property
    def artifacts_unlocked(self) -> bool:
        return self.level >= config.LEVEL_ARTIFACTS

    @property
    def workshop_unlocked(self) -> bool:
        return self.level >= config.LEVEL_WORKSHOP

    @property
    def can_sell(self) -> bool:
        return self.level >= config.LEVEL_SELL

    @property
    def can_buy(self) -> bool:
        return self.level >= config.LEVEL_BUY

    @property
    def has_companion(self) -> bool:
        return self.level >= config.LEVEL_COMPANION

    @property
    def has_hero(self) -> bool:
        return self.level >= config.LEVEL_HERO

    def tower_track_unlocked(self, key: str) -> bool:
        return self.level >= config.TOWER_TRACK_UNLOCK.get(key, 10)

    @property
    def level_damage_bonus(self) -> float:
        return sum(v for lv, v in config.LEVEL_DAMAGE_BONUS.items() if self.level >= lv)

    @property
    def new_artifact_flat(self) -> float:
        return sum(v for lv, v in config.LEVEL_NEW_ARTIFACT_BONUS.items() if self.level >= lv)

    @property
    def block_gold_bonus(self) -> float:
        lv, v = config.LEVEL_BLOCK_GOLD
        return v if self.level >= lv else 0.0

    @property
    def block_xp_bonus(self) -> float:
        lv, v = config.LEVEL_BLOCK_XP
        return v if self.level >= lv else 0.0

    # ------------------------------------------------------------------
    @property
    def max_health(self) -> float:
        return self.base_max_health + self.bonus_max_health + self.helmet.effective_bonus

    @property
    def mining_power(self) -> float:
        base = self.tool.power + self.bonus_mining_power + self.level_damage_bonus
        return base * (1 + self.bonus_mining_power_pct + self.items_level_bonus())

    def war_items(self):
        """Objets pouvant perdre un palier quand on perd une guerre."""
        return [self.tool] + list(self.equipment_items())

    def clamp_health(self):
        self.health = min(self.health, self.max_health)

    def equipment_items(self):
        return (self.helmet, self.armor, self.aura, self.amulet, self.gauntlet)

    def items_level_bonus(self) -> float:
        """Les niveaux d'XP des équipements donnent très légèrement de la puissance de minage."""
        return sum(it.level - 1 for it in self.equipment_items() if it.enabled) * config.ITEM_LEVEL_MINING_BONUS

    def apply_death_penalty(self) -> int:
        """Mort contre un monstre : perte d'or ET de toute l'XP en cours (pioche + équipements)."""
        lost = int(self.inventory.gold * config.DEATH_GOLD_LOSS)
        self.inventory.gold -= lost
        for it in (self.tool,) + self.equipment_items():
            it.xp = 0.0
        return lost

    @property
    def combat_bonus(self) -> float:
        """Dégâts fixes ajoutés à ceux de la pioche contre les monstres."""
        return self.gauntlet.effective_bonus + self.bonus_combat_damage

    def on_combat_damage(self, dealt: float):
        """XP gagnée en combat : la pioche ET le gantelet. Retourne les messages de niveau."""
        msgs = []
        if dealt <= 0:
            return msgs
        if self.tool.add_xp(dealt * config.TOOL_XP_PER_COMBAT_DAMAGE):
            msgs.append(f"Pioche niveau {self.tool.level} !")
        if self.gauntlet.add_xp(dealt * config.GAUNTLET_XP_PER_DAMAGE):
            msgs.append(f"{self.gauntlet.name} : niveau {self.gauntlet.level} !")
        return msgs

    @property
    def damage_reduction(self) -> float:
        """Fraction (0..~0.7) de dégâts en moins en combat."""
        return min(0.7, self.armor.effective_bonus + self.bonus_damage_reduction)

    @property
    def gold_multiplier(self) -> float:
        return 1 + self.aura.effective_bonus + self.bonus_gold_pct

    def can_dig(self, block) -> bool:
        return not block.is_empty

    def take_damage(self, amount: float):
        mitigated = amount * (1 - self.damage_reduction)
        reduced = amount - mitigated  # dégâts effectivement annulés par l'armure
        self.health = max(0, self.health - mitigated)
        # l'armure s'xp sur ce qu'elle a bloqué, le casque sur ce qui est passé
        self.armor.add_xp(reduced * config.ARMOR_XP_PER_DAMAGE_REDUCED)
        self.helmet.add_xp(mitigated * config.HELMET_XP_PER_DAMAGE_TAKEN)
        if self.health <= 0:
            self.alive = False
        return mitigated

    def heal(self, amount: float):
        self.health = min(self.max_health, self.health + amount)

    def passive_regen(self, dt: float):
        """Régénération passive lente : casque + amulette, hors combat comme en combat.
        L'amulette (et seulement elle) gagne de l'XP proportionnellement aux PV
        qu'elle a réellement permis de récupérer.
        Génère également de l'XP passive pour le niveau principal grâce aux pierres d'XP."""
        if not self.alive:
            return
        if self.inventory.xp_stones > 0:
            self.gain_player_xp(dt * self.inventory.xp_stones * 0.8)
        helmet_amt = self.helmet.effective_regen * dt
        amulet_amt = self.amulet.effective_regen * dt
        total = helmet_amt + amulet_amt
        if total <= 0:
            return
        before = self.health
        self.heal(total)
        actually_healed = self.health - before
        amulet_share = actually_healed * (amulet_amt / total)
        self.amulet.add_xp(amulet_share * config.AMULET_XP_PER_HP_REGEN)

    def gain_gold(self, amount: float):
        earned = amount * self.gold_multiplier
        self.inventory.gold += earned
        self.aura.add_xp(earned * 0.5)
        return earned

    def refresh_xp_mult(self):
        m = 1 + self.perks.get("xp_boost", 0.0)
        for it in (self.tool,) + self.equipment_items():
            it.xp_mult = m
        for key, (lv, mult) in config.LEVEL_XP_MULT.items():
            if self.level >= lv:
                getattr(self, key).xp_mult *= mult

    def apply_artifact_bonus(self, artifact_def, heal=True):
        for key, val in artifact_effects(artifact_def).items():
            if key == "mining_power":
                self.bonus_mining_power += val
            elif key == "mining_power_pct":
                self.bonus_mining_power_pct += val
            elif key == "max_health":
                self.bonus_max_health += val
                if heal:
                    self.health += val
            elif key == "damage_reduction":
                self.bonus_damage_reduction += val
            elif key == "gold_pct":
                self.bonus_gold_pct += val
            elif key == "artifact_luck":
                self.bonus_artifact_luck += val
            elif key == "combat_damage":
                self.bonus_combat_damage += val
            elif key == "component_luck":
                self.bonus_component_luck += val
            else:
                self.perks[key] += val
        self.refresh_xp_mult()

    def recompute_artifact_bonuses(self, catalog):
        """Recalcule tous les bonus d'artefacts depuis la liste des artefacts trouvés
        (garde les sauvegardes cohérentes quand les valeurs sont rééquilibrées)."""
        self.bonus_mining_power = self.bonus_mining_power_pct = self.bonus_artifact_luck = 0.0
        self.bonus_max_health = self.bonus_damage_reduction = self.bonus_gold_pct = 0.0
        self.bonus_combat_damage = self.bonus_component_luck = 0.0
        self.perks = defaultdict(float)
        for aid in catalog.found:
            if aid in catalog.defs and catalog.defs[aid].bonus_type:
                self.apply_artifact_bonus(catalog.defs[aid], heal=False)
        self.refresh_xp_mult()

    def descend(self):
        self.row += 1
        self.max_depth_reached = max(self.max_depth_reached, self.row)
