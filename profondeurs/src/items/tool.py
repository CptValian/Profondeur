"""Outil de minage du joueur (pioche) et sa logique d'amélioration."""

from src import config


class Tool:
    def __init__(self, tier: int = 0):
        self.tier = tier
        self.xp = 0.0
        self.xp_mult = 1.0   # bonus d'XP (artefact Grimoire des anciens)
        self.level = 1   # niveau de 1 à TOOL_MAX_LEVEL, indépendant du palier acheté
        self.enabled = True
        self.xp_listener = None    # fonction(xp) : alimente le niveau du mineur

    @property
    def max_level(self) -> int:
        return config.TOOL_MAX_LEVEL

    @property
    def data(self) -> dict:
        return config.TOOL_TIERS[self.tier]

    @property
    def name(self) -> str:
        return self.data["name"]

    @property
    def power(self) -> float:
        base = self.data["power"]
        return base * (1 + (self.level - 1) * config.TOOL_LEVEL_POWER_BONUS)

    @property
    def speed(self) -> float:
        """Coups par seconde en maintenant le clic."""
        base = self.data["speed"]
        return base * (1 + (self.level - 1) * config.TOOL_LEVEL_SPEED_BONUS)

    @property
    def attack_interval(self) -> float:
        return 1.0 / self.speed

    @property
    def head_color(self):
        return self.data["head"]

    @property
    def head2_color(self):
        return self.data["head2"]

    @property
    def handle_color(self):
        return self.data["handle"]

    @property
    def art(self) -> dict:
        return self.data["art"]

    @property
    def glow(self):
        return self.data["glow"]

    @property
    def skin_description(self) -> str:
        return self.data["skin"]

    @property
    def is_max_tier(self) -> bool:
        return self.tier >= len(config.TOOL_TIERS) - 1

    def upgrade_cost(self) -> int:
        if self.is_max_tier:
            return -1
        return int(config.UPGRADE_BASE_COST * (config.TOOL_UPGRADE_COST_GROWTH ** self.tier))

    def downgrade(self) -> bool:
        """Perd un palier (niveau acheté en or). L'XP et le niveau d'expérience sont conservés."""
        if self.tier <= 0:
            return False
        self.tier -= 1
        return True

    def upgrade(self) -> bool:
        if self.is_max_tier:
            return False
        self.tier += 1   # l'XP et le niveau sont conservés
        return True

    # ---- XP / niveaux (gagnés en minant, transcendants) ----
    def total_xp(self) -> float:
        tot = self.xp
        for l in range(1, self.level):
            tot += config.TOOL_XP_BASE * (l ** config.TOOL_XP_EXPONENT)
        return tot

    def xp_to_next_level(self) -> float:
        return config.TOOL_XP_BASE * (self.level ** config.TOOL_XP_EXPONENT)

    def add_xp(self, amount: float) -> bool:
        """Retourne True si au moins un niveau vient d'être franchi."""
        if amount <= 0:
            return False
        gained = amount * self.xp_mult
        if self.xp_listener:
            self.xp_listener(gained)
        if self.level >= config.TOOL_MAX_LEVEL:
            return False
        self.xp += gained
        leveled = False
        while self.level < config.TOOL_MAX_LEVEL and self.xp >= self.xp_to_next_level():
            self.xp -= self.xp_to_next_level()
            self.level += 1
            leveled = True
        return leveled
