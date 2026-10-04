"""
Composants trouvés au hasard (en minant ou sur les monstres) et recettes
permettant de fabriquer des TROUPES. Ce sont de vraies unités de combat :
elles marchent, se battent et meurent sur le champ de bataille (battle_sim.py).
La défense d'une faction est un donjon d'archer améliorable (tower.py).
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

from src import config


@dataclass(frozen=True)
class ComponentDef:
    component_id: str
    name: str
    rarity: str
    min_depth: int
    description: str


COMPONENT_DEFS = [
    ComponentDef("bone_shard", "Éclat d'os", "Commune", 5, "Fragment d'une créature des galeries."),
    ComponentDef("iron_rivet", "Rivet de fer", "Commune", 10, "Un rivet de l'ancien temps, encore solide."),
    ComponentDef("tanned_hide", "Cuir tanné", "Peu commune", 40, "Peau épaisse de ver des profondeurs."),
    ComponentDef("raw_crystal", "Cristal brut", "Peu commune", 80, "Il vibre quand on le tape."),
    ComponentDef("golem_core", "Noyau de golem", "Rare", 150, "Un cœur de pierre qui bat lentement."),
    ComponentDef("rune_cord", "Cordon runique", "Rare", 250, "Une corde gravée de runes tièdes."),
    ComponentDef("abyssal_scale", "Écaille abyssale", "Épique", 450, "Plus dure que n'importe quel métal connu."),
    ComponentDef("star_fragment", "Fragment stellaire", "Légendaire", 800, "Un éclat d'étoile morte, encore chaud."),
]
COMPONENTS = {c.component_id: c for c in COMPONENT_DEFS}
COMPONENT_RARITY_WEIGHT = {"Commune": 10, "Peu commune": 5, "Rare": 2.2, "Épique": 0.8, "Légendaire": 0.25}


@dataclass(frozen=True)
class Recipe:
    recipe_id: str
    name: str
    kind: str                 # "troop"
    cost: Dict[str, int]
    attack: int               # dégâts par coup (ou par flèche)
    health: int
    defense: int              # réduit les dégâts reçus : x100/(100 + 4 x défense)
    speed: float              # vitesse de marche (unités du champ de bataille / s)
    range: float              # portée d'attaque (<= 60 : corps à corps)
    interval: float           # secondes entre deux attaques
    description: str = ""


RECIPES = [
    Recipe("militia", "Milicien de roche", "troop", {"bone_shard": 3, "iron_rivet": 2},
           4, 20, 1, 60, 22, 0.8, "Une recrue armée d'un pic ébréché."),
    Recipe("pikeman", "Piquier de fer", "troop", {"iron_rivet": 4, "tanned_hide": 2},
           9, 40, 3, 55, 40, 1.0, "Tient la ligne avec une longue pique."),
    Recipe("crystal_archer", "Archer cristallin", "troop", {"raw_crystal": 3, "tanned_hide": 2, "bone_shard": 2},
           16, 30, 2, 50, 230, 1.4, "Tire ses flèches de cristal depuis l'arrière."),
    Recipe("golem", "Golem de roche", "troop", {"golem_core": 2, "iron_rivet": 4},
           22, 120, 8, 38, 28, 1.5, "Lent, massif, presque indestructible."),
    Recipe("rune_knight", "Chevalier runique", "troop", {"rune_cord": 3, "golem_core": 2, "raw_crystal": 3},
           38, 90, 10, 62, 28, 1.0, "Un champion gravé de runes."),
    Recipe("abyss_stalker", "Rôdeur abyssal", "troop", {"abyssal_scale": 3, "rune_cord": 2},
           70, 160, 14, 82, 30, 0.9, "Il frappe depuis l'ombre."),
    Recipe("star_guardian", "Gardien stellaire", "troop", {"star_fragment": 2, "abyssal_scale": 2, "rune_cord": 2},
           130, 300, 25, 55, 34, 1.1, "Une légende debout."),
]
RECIPES_BY_ID = {r.recipe_id: r for r in RECIPES}


def roll_component(depth: int, rng, chance: float, luck: float = 0.0) -> Optional[str]:
    """Tire (ou non) un composant. rng : module random ou random.Random."""
    if rng.random() >= min(1.0, chance * (1 + luck)):
        return None
    eligible = [c for c in COMPONENT_DEFS if c.min_depth <= depth]
    if not eligible:
        return None
    weights = [COMPONENT_RARITY_WEIGHT[c.rarity] for c in eligible]
    return rng.choices(eligible, weights=weights, k=1)[0].component_id


def can_craft(inv, recipe: Recipe) -> bool:
    return all(inv.components.get(cid, 0) >= n for cid, n in recipe.cost.items())


def craft(inv, recipe_id: str) -> bool:
    recipe = RECIPES_BY_ID.get(recipe_id)
    if recipe is None or not can_craft(inv, recipe):
        return False
    for cid, n in recipe.cost.items():
        inv.components[cid] -= n
    inv.units[recipe_id] += 1
    return True


def army_totals(inv) -> dict:
    """Totaux (attaque, PV, défense, nombre) des troupes possédées."""
    out = {"attack": 0, "health": 0, "defense": 0, "count": 0}
    for rid, n in inv.units.items():
        r = RECIPES_BY_ID.get(rid)
        if not r or n <= 0:
            continue
        out["attack"] += r.attack * n
        out["health"] += r.health * n
        out["defense"] += r.defense * n
        out["count"] += n
    return out


# --- Marché de composants (vente dès le niveau 25, achat dès le niveau 26) ---
COMPONENT_VALUE = {"Commune": 4, "Peu commune": 15, "Rare": 50, "Épique": 160, "Légendaire": 500}
BUY_MARKUP = 4


def sell_price(cid: str) -> int:
    return COMPONENT_VALUE[COMPONENTS[cid].rarity]


def buy_price(cid: str) -> int:
    return sell_price(cid) * BUY_MARKUP


def sell_component(inv, cid: str) -> bool:
    if inv.components.get(cid, 0) <= 0:
        return False
    inv.components[cid] -= 1
    inv.gold += sell_price(cid)
    return True


def buy_component(inv, cid: str) -> bool:
    if not inv.spend_gold(buy_price(cid)):
        return False
    inv.add_component(cid)
    return True
