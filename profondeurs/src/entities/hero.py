"""Héros de guerre (débloqué au niveau 20)."""

from src import config


HERO_TIERS = [
    {"name": "Champion Novice",      "color": (220, 180, 100)},
    {"name": "Guerrier Cuivré",      "color": (210, 140, 80)},
    {"name": "Vétéran de Fer",      "color": (180, 185, 195)},
    {"name": "Capitaine d'Acier",    "color": (215, 220, 230)},
    {"name": "Héros Runique",        "color": (120, 160, 255)},
    {"name": "Seigneur de Mithril",  "color": (160, 220, 255)},
    {"name": "Guerrier Abyssal",     "color": (170, 90, 240)},
    {"name": "Champion Solaire",     "color": (255, 190, 80)},
    {"name": "Légende Stellaire",    "color": (255, 230, 140)},
    {"name": "Paladin de la Genèse", "color": (255, 255, 255)},
    {"name": "Héros Inégalé",        "color": (255, 255, 255)},
]


class Hero:
    def __init__(self):
        self.gold_tier = 0
        self.level = 1
        self.xp = 0.0

    @property
    def max_gold_tier(self) -> int:
        return len(HERO_TIERS) - 1

    @property
    def max_level(self) -> int:
        return 100

    @property
    def name(self) -> str:
        return HERO_TIERS[self.gold_tier]["name"]

    @property
    def color(self):
        return HERO_TIERS[self.gold_tier]["color"]

    def gold_upgrade_cost(self) -> int:
        if self.gold_tier >= self.max_gold_tier:
            return -1
        return int(250 * (2.4 ** self.gold_tier))

    def upgrade_gold(self, player) -> bool:
        cost = self.gold_upgrade_cost()
        if cost > 0 and player.inventory.spend_gold(cost):
            self.gold_tier += 1
            return True
        return False

    @property
    def xp_multiplier(self) -> float:
        """Améliorations en or : augmentent le multiplicateur d'XP."""
        return round(1.0 + self.gold_tier * 0.25, 2)

    @property
    def max_hp(self) -> float:
        """Niveaux d'XP + Niveaux d'Or améliorent les PV."""
        return round(120.0 + (self.level - 1) * 12.0 + self.gold_tier * 35.0, 1)

    @property
    def attack_damage(self) -> float:
        """Niveaux d'XP + Niveaux d'Or améliorent les dégâts d'attaque."""
        return round(18.0 + (self.level - 1) * 2.2 + self.gold_tier * 6.0, 1)

    @property
    def armor(self) -> float:
        """Niveaux d'XP améliorent l'armure (défense)."""
        return round(4.0 + (self.level - 1) * 0.5, 1)

    @property
    def attack_interval(self) -> float:
        """Niveaux d'XP améliorent la vitesse d'attaque (intervalle réduit)."""
        return max(0.4, round(1.6 - (self.level - 1) * 0.012, 2))

    def xp_to_next_level(self) -> float:
        return round(150.0 * (self.level ** 1.55), 1)

    def add_xp(self, amount: float) -> bool:
        if self.level >= self.max_level or amount <= 0:
            return False
        gained = amount * self.xp_multiplier
        self.xp += gained
        leveled = False
        while self.level < self.max_level and self.xp >= self.xp_to_next_level():
            self.xp -= self.xp_to_next_level()
            self.level += 1
            leveled = True
        if self.level >= self.max_level:
            self.xp = 0.0
        return leveled

    def on_battle_completed(self, damage_dealt: float, damage_taken: float) -> bool:
        """Gagne de l'XP en infligeant et en subissant des dégâts lors des attaques."""
        total = damage_dealt + damage_taken
        return self.add_xp(total)
