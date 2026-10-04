"""Créatures rencontrées dans les profondeurs."""

import random
from dataclasses import dataclass
from src import config


MONSTER_NAMES = [
    "Rampant des galeries", "Larve de silex", "Golem fissuré",
    "Spectre de charbon", "Ver abyssal", "Sentinelle de magma",
]

BOSS_NAMES = [
    "Gardien de la Faille", "Dévoreur de Roche", "Le Cœur Incandescent",
]


@dataclass
class Monster:
    name: str
    depth: int
    max_health: int
    health: int
    attack: int
    defense: int
    is_boss: bool = False
    # "difficulté" personnelle du monstre, ajustée par le système adaptatif
    aggressiveness: float = 0.5
    speed: float = 90.0             # vitesse de déplacement dans l'arène (px/s)
    attack_interval: float = 1.4    # secondes entre deux attaques automatiques

    @property
    def alive(self) -> bool:
        return self.health > 0

    def take_damage(self, amount: int):
        dmg = max(1, amount - self.defense)
        self.health = max(0, self.health - dmg)

    def choose_action(self) -> str:
        """Action très simple pilotée par l'agressivité (utilisée par les IA
        concurrentes, qui résolvent leurs combats sans arène visuelle)."""
        return "attack" if random.random() < self.aggressiveness else "defend"


def spawn_monster(depth: int, aggressiveness: float = 0.5) -> Monster:
    is_boss = depth > 0 and depth % config.BOSS_DEPTH_INTERVAL == 0
    scale = 1 + depth / 60.0
    if is_boss:
        name = random.choice(BOSS_NAMES)
        hp = int(60 * scale)
        atk = int(8 * scale)
        de = int(3 * scale)
        speed = config.MONSTER_BASE_SPEED * 0.7
    else:
        name = random.choice(MONSTER_NAMES)
        hp = int(12 * scale)
        atk = int(3 * scale)
        de = int(1 * scale)
        speed = config.MONSTER_BASE_SPEED * (1 + aggressiveness * 0.6)
    attack_interval = max(0.55, 1.7 - aggressiveness * 0.8)
    return Monster(name=name, depth=depth, max_health=hp, health=hp,
                    attack=atk, defense=de, is_boss=is_boss,
                    aggressiveness=aggressiveness, speed=speed, attack_interval=attack_interval)
