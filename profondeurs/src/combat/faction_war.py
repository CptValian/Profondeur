"""
Guerre entre factions. Une attaque lance une VRAIE bataille (battle_sim.BattleSim) :
les troupes de l'attaquant contre les troupes du défenseur, soutenues par son donjon
d'archer. Le résultat de la simulation décide seul des pertes et du vainqueur ;
le vainqueur gagne un point de guerre et l'attaquant victorieux pille une part de l'or.
"""

import random
from dataclasses import dataclass, field
from typing import Dict

from src import config
from src.combat.battle_sim import BattleSim
from src.items import crafting, tower as tower_mod


def force_power(units) -> float:
    """Estimation grossière de la force d'une troupe (utilisée par les IA et l'interface)."""
    total = 0.0
    for rid, n in units.items():
        r = crafting.RECIPES_BY_ID.get(rid)
        if r and n > 0:
            total += (r.attack / r.interval + r.health / 5 + r.defense * 1.5) * n
    return total


def defense_power(inv) -> float:
    return force_power(inv.units) + tower_mod.tower_power(inv.tower)


@dataclass
class BattleReport:
    attacker: str
    defender: str
    attacker_won: bool
    duration: float
    att_losses: Dict[str, int]
    def_losses: Dict[str, int]
    loot: float = 0.0
    broken: str = ""      # ex. "Pioche d'acier -> Pioche de fer forgé"

    def good_for(self, me: str) -> bool:
        return (self.attacker == me and self.attacker_won) or (self.defender == me and not self.attacker_won)

    def line(self, me: str = "Toi") -> str:
        a_n, d_n = sum(self.att_losses.values()), sum(self.def_losses.values())
        if self.attacker == me:
            txt = f"Attaque sur {self.defender} : {'VICTOIRE' if self.attacker_won else 'DÉFAITE'}. " \
                  f"Pertes {a_n} (ennemi {d_n})"
            if self.loot:
                txt += f", butin +{int(self.loot)} or"
            if self.broken:
                txt += f", {self.broken.split(' -> ')[0]} de l'ennemi rétrogradé"
        elif self.defender == me:
            txt = f"{self.attacker} t'attaque : {'défense échouée' if self.attacker_won else 'défense réussie'}. " \
                  f"Pertes {d_n} (ennemi {a_n})"
            if self.loot:
                txt += f", pillage -{int(self.loot)} or"
            if self.broken:
                txt += f", {self.broken.split(' -> ')[0]} perd un palier"
        else:
            txt = f"{self.attacker} {'bat' if self.attacker_won else 'échoue contre'} {self.defender}"
        return txt


def start_battle(att_inv, def_inv, hero=None, rng=None, record_events=False) -> BattleSim:
    return BattleSim(dict(att_inv.units), dict(def_inv.units), dict(def_inv.tower), hero=hero, rng=rng, record_events=record_events)


def finalize_battle(sim: BattleSim, att_name, att_inv, def_name, def_inv, def_items=None, hero=None, rng=None) -> BattleReport:
    """Applique le résultat de la simulation : pertes définitives, butin, point de guerre."""
    a_loss = {rid: n - sim.survivors("att").get(rid, 0) for rid, n in sim.att_start.items()}
    d_loss = {rid: n - sim.survivors("def").get(rid, 0) for rid, n in sim.def_start.items()}
    a_loss = {k: v for k, v in a_loss.items() if v > 0}
    d_loss = {k: v for k, v in d_loss.items() if v > 0}
    for rid, n in a_loss.items():
        att_inv.units[rid] = max(0, att_inv.units[rid] - n)
    for rid, n in d_loss.items():
        def_inv.units[rid] = max(0, def_inv.units[rid] - n)
    loot = 0.0
    broken = ""
    if hero is not None:
        hero.on_battle_completed(sim.hero_damage_dealt, sim.hero_damage_taken)

    if sim.attacker_won:
        loot = max(0.0, def_inv.gold * config.WAR_LOOT_RATIO)
        def_inv.gold -= loot
        att_inv.gold += loot
        att_inv.war_wins += 1
        # un équipement du vaincu, tiré au hasard, perd un palier (le niveau d'XP est conservé)
        candidates = [it for it in (def_items or []) if it.tier > 0]
        if candidates:
            item = (rng or random).choice(candidates)
            old = item.name
            item.downgrade()
            broken = f"{old} -> {item.name}"
    else:
        def_inv.war_wins += 1
    return BattleReport(att_name, def_name, sim.attacker_won, sim.time, a_loss, d_loss, loot, broken)


def resolve_attack(att_name, att_inv, def_name, def_inv, def_items=None, rng=None) -> BattleReport:
    """Bataille sans affichage (attaques des IA) : même simulation, lancée jusqu'au bout."""
    sim = start_battle(att_inv, def_inv, rng).run(0.1)
    return finalize_battle(sim, att_name, att_inv, def_name, def_inv, def_items, rng)
