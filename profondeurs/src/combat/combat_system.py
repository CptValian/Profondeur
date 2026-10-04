"""Résout un tour de combat entre le joueur et un monstre."""

import random
from src.entities.player import Player
from src.entities.monster import Monster


class CombatResult:
    def __init__(self):
        self.log = []
        self.player_won = False
        self.finished = False
        self.events = []   # messages (montées de niveau...)

    def add(self, msg):
        self.log.append(msg)


def player_attack(player: Player, monster: Monster, result: CombatResult):
    # dégâts de la pioche + bonus de combat (gantelet, artefacts)
    raw = player.mining_power + getattr(player, "combat_bonus", 0.0)
    dmg = int(raw * random.uniform(0.8, 1.2))
    before = monster.health
    monster.take_damage(dmg)
    dealt = before - monster.health
    result.add(f"Tu frappes {monster.name} pour {dealt} dégâts.")
    on_damage = getattr(player, "on_combat_damage", None)
    if on_damage:
        result.events.extend(on_damage(dealt))
    if not monster.alive:
        result.add(f"{monster.name} est vaincu !")
        result.player_won = True
        result.finished = True


def monster_auto_attack(player, monster: Monster, result: CombatResult):
    """Attaque automatique et périodique du monstre pendant l'arène active
    (indépendante des clics du joueur, qui ne servent qu'à l'attaquer)."""
    if not monster.alive:
        return
    dmg = max(1, int(monster.attack * random.uniform(0.7, 1.3)))
    mitigated = player.take_damage(dmg)
    result.add(f"{monster.name} te touche pour {int(mitigated)} dégâts.")
    if not player.alive:
        result.add("Tu as été vaincu...")
        result.finished = True
        result.player_won = False


def monster_turn(player: Player, monster: Monster, result: CombatResult):
    if not monster.alive:
        return
    action = monster.choose_action()
    if action == "attack":
        dmg = max(1, int(monster.attack * random.uniform(0.7, 1.3)))
        player.take_damage(dmg)
        result.add(f"{monster.name} t'attaque pour {dmg} dégâts.")
    else:
        result.add(f"{monster.name} se met en garde.")
    if not player.alive:
        result.add("Tu as été vaincu...")
        result.finished = True
        result.player_won = False


def player_flee(player: Player, result: CombatResult, success_chance: float = 0.6):
    if random.random() < success_chance:
        result.add("Tu prends la fuite avec succès.")
        result.finished = True
    else:
        result.add("Impossible de fuir !")
