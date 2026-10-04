"""Représente une case (bloc) de la galerie."""

from dataclasses import dataclass
from typing import Optional

from src import config


@dataclass
class Block:
    stone_id: str
    hardness: float
    depth: int
    is_empty: bool = False
    resource_amount: int = 1
    contains_artifact: Optional[str] = None
    contains_monster: bool = False
    max_health: float = 1.0
    health: float = 1.0

    def __post_init__(self):
        self.max_health = max(1.0, self.hardness * config.BLOCK_HEALTH_SCALE)
        if self.contains_artifact:
            self.max_health *= config.ARTIFACT_BLOCK_HARDNESS_MULT
        self.health = self.max_health

    @property
    def base_hp(self) -> float:
        """Difficulté 'normale' du bloc (sans le x25 des pierres d'artefact)."""
        return max(1.0, self.hardness * config.BLOCK_HEALTH_SCALE)

    def roll_gold(self, rng) -> float:
        """Or du bloc : en moyenne proportionnel à sa difficulté, avec un petit aléa.
        Les blocs d'artefact ne donnent pas d'or."""
        if self.contains_artifact:
            return 0.0
        return config.GOLD_PER_BLOCK_HP * self.base_hp * rng.uniform(*config.BLOCK_VALUE_RANDOM)

    def roll_xp(self, rng) -> float:
        """XP de minage : proportionnelle à la difficulté réelle (points de vie) du bloc."""
        return config.TOOL_XP_PER_DAMAGE * self.max_health * rng.uniform(*config.XP_BLOCK_RANDOM)

    @property
    def health_ratio(self) -> float:
        if self.max_health <= 0:
            return 0.0
        return max(0.0, self.health / self.max_health)

    def take_damage(self, amount: float) -> bool:
        """Retourne True si le bloc vient de se briser."""
        if self.is_empty:
            return False
        self.health -= amount
        if self.health <= 0:
            self.is_empty = True
            return True
        return False
