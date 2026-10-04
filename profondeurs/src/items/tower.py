"""
Donjon d'archer : la seule défense d'une faction. Placé à l'arrière du champ de bataille,
il tire sur les attaquants. Caractéristiques améliorables avec de l'or :
dégâts des flèches, cadence de tir, portée, PV du donjon, nombre de flèches par salve,
et (niveau de mineur 30) l'amélioration SUPRÊME aux 5 effets cumulatifs.
"""

from src import config

TRACKS = {
    "damage":  dict(label="Dégâts des flèches", max=20, base_cost=80, growth=1.45),
    "speed":   dict(label="Cadence de tir", max=15, base_cost=100, growth=1.50),
    "range":   dict(label="Portée", max=15, base_cost=70, growth=1.40),
    "hp":      dict(label="PV du donjon", max=20, base_cost=90, growth=1.45),
    "arrows":  dict(label="Flèches par salve", max=6, base_cost=150, growth=1.80),
    "supreme": dict(label="Amélioration suprême", max=5, base_cost=1500, growth=2.5),
}

# effet débloqué à chaque niveau de l'amélioration suprême (cumulatif)
SUPREME_DESC = [
    "Flèches enflammées (brûlure)",
    "Lac de lave devant le donjon",
    "Renforts : 2 piquiers / 10 s",
    "+ un Golem à chaque renfort",
    "Pluie de flèches / 10 s",
]


def default_levels() -> dict:
    return {k: 0 for k in TRACKS}


def stats(levels: dict) -> dict:
    lv = {k: levels.get(k, 0) for k in TRACKS}
    return {
        "damage": 6.0 * (1 + 0.25 * lv["damage"]),     # par flèche
        "speed": 0.4 + 0.06 * lv["speed"],              # salves par seconde
        "range": 240.0 + 22.0 * lv["range"],            # unités du champ de bataille
        "arrows": 1 + lv["arrows"],                     # flèches par salve
        "hp": config.TOWER_HP * (1 + 0.25 * lv["hp"]),  # points de vie du donjon
        "supreme": lv["supreme"],
    }


def format_stat(key: str, value: float) -> str:
    if key in ("damage", "hp", "range"):
        return f"{value:.0f}"
    if key == "speed":
        return f"{value:.2f}/s"
    return f"{int(value)}"


def upgrade_cost(levels: dict, key: str) -> int:
    """Coût de l'amélioration suivante, ou -1 si le niveau maximum est atteint."""
    t = TRACKS[key]
    lv = levels.get(key, 0)
    if lv >= t["max"]:
        return -1
    return int(t["base_cost"] * (t["growth"] ** lv))


def upgrade(inv, key: str) -> bool:
    cost = upgrade_cost(inv.tower, key)
    if cost < 0 or not inv.spend_gold(cost):
        return False
    inv.tower[key] = inv.tower.get(key, 0) + 1
    return True


def tower_power(levels: dict) -> float:
    """Estimation de la force du donjon (décisions des IA)."""
    st = stats(levels)
    return (st["damage"] * st["arrows"] * st["speed"] * 8
            + (st["hp"] - config.TOWER_HP) / 20 + st["supreme"] * 15)
