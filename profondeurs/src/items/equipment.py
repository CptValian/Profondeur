"""
Équipements secondaires : casque, armure, aura.

Chaque équipement suit une double progression, comme la pioche :
 - un PALIER (tier), débloqué contre de l'or, qui change le skin et le(s)
   bonus de base ;
 - un NIVEAU d'expérience TRANSCENDANT (1 à 100), gagné en utilisant
   l'objet pendant la partie (encaisser des coups, gagner de l'or...), qui
   augmente progressivement le bonus. Ce niveau est CONSERVÉ quand on
   achète un nouveau palier (il ne repart pas de 1), exactement comme pour
   la pioche : seul le palier change le skin/le bonus de base, le niveau
   grimpe indépendamment et de plus en plus lentement (courbe d'XP).
"""

from src import config


class Equipment:
    def __init__(self, tiers: list, tier: int = 0):
        self._tiers = tiers
        self.tier = tier
        self.xp = 0.0
        self.xp_mult = 1.0   # bonus d'XP (artefact Grimoire des anciens)
        self.level = 1   # transcendant : 1 à EQUIP_MAX_LEVEL, indépendant du palier
        self.enabled = True        # False tant que le niveau de mineur requis n'est pas atteint
        self.xp_listener = None    # fonction(xp) : l'XP gagnée alimente aussi le niveau du mineur

    @property
    def max_level(self) -> int:
        return config.EQUIP_MAX_LEVEL

    @property
    def data(self) -> dict:
        return self._tiers[self.tier]

    @property
    def name(self) -> str:
        return self.data["name"]

    @property
    def base_bonus(self) -> float:
        return self.data["bonus"]

    @property
    def color(self):
        return self.data["color"]

    @property
    def glow(self):
        return self.data["glow"]

    @property
    def skin_description(self) -> str:
        return self.data["skin"]

    def _level_mult(self) -> float:
        return 1 + (self.level - 1) * config.EQUIP_LEVEL_BONUS_PCT

    def flat_bonus(self, key: str = None) -> float:
        if key is None:
            kind_key = self.__class__.__name__.lower()
        else:
            kind_key = f"{self.__class__.__name__.lower()}_{key}"
        flat_rate = config.EQUIP_LEVEL_FLAT_BONUS.get(kind_key, 0.0)
        return (self.level - 1) * flat_rate

    @property
    def effective_bonus(self) -> float:
        """Bonus du palier (amplifié par le multiplicateur de niveau) + bonus plat de niveau."""
        if not self.enabled:
            return 0.0
        return self.base_bonus * self._level_mult() + self.flat_bonus()

    def effective_stat(self, key: str) -> float:
        """Pour un second stat éventuel du palier (ex: 'regen' du casque)."""
        if not self.enabled:
            return 0.0
        return self.data.get(key, 0.0) * self._level_mult() + self.flat_bonus(key)

    @property
    def is_max_tier(self) -> bool:
        return self.tier >= len(self._tiers) - 1

    def upgrade_cost(self) -> int:
        if self.is_max_tier:
            return -1
        return int(config.UPGRADE_BASE_COST * 1.4 * (config.UPGRADE_COST_GROWTH ** self.tier))

    def downgrade(self) -> bool:
        """Perd un palier (niveau acheté en or). L'XP et le niveau d'expérience sont conservés."""
        if self.tier <= 0:
            return False
        self.tier -= 1
        return True

    def upgrade(self) -> bool:
        if self.is_max_tier:
            return False
        self.tier += 1   # l'XP et le niveau sont conservés (transcendants)
        return True

    # ---- XP / niveaux transcendants ----
    def total_xp(self) -> float:
        """XP cumulée depuis le début (sert à migrer les anciennes sauvegardes)."""
        tot = self.xp
        for l in range(1, self.level):
            tot += config.EQUIP_XP_BASE * (l ** config.EQUIP_XP_EXPONENT)
        return tot

    def xp_to_next_level(self) -> float:
        return config.EQUIP_XP_BASE * (self.level ** config.EQUIP_XP_EXPONENT)

    def add_xp(self, amount: float) -> bool:
        """Retourne True si au moins un niveau vient d'être franchi."""
        if not self.enabled or amount <= 0:
            return False
        gained = amount * self.xp_mult
        if self.xp_listener:
            self.xp_listener(gained)
        if self.level >= config.EQUIP_MAX_LEVEL:
            return False
        self.xp += gained
        leveled = False
        while self.level < config.EQUIP_MAX_LEVEL and self.xp >= self.xp_to_next_level():
            self.xp -= self.xp_to_next_level()
            self.level += 1
            leveled = True
        return leveled


class Helmet(Equipment):
    """Bonus : points de vie maximum supplémentaires + régénération passive lente."""
    def __init__(self, tier: int = 0):
        super().__init__(config.HELMET_TIERS, tier)

    @property
    def effective_regen(self) -> float:
        """PV régénérés par seconde, hors combat — augmente avec le palier et le niveau."""
        return self.effective_stat("regen")


class Armor(Equipment):
    """Bonus : réduction (%) des dégâts reçus en combat."""
    def __init__(self, tier: int = 0):
        super().__init__(config.ARMOR_TIERS, tier)


class Aura(Equipment):
    """Bonus : pourcentage d'or supplémentaire gagné sur chaque ressource/combat."""
    def __init__(self, tier: int = 0):
        super().__init__(config.AURA_TIERS, tier)

    def upgrade_cost(self) -> int:
        if self.is_max_tier:
            return -1
        return int(config.UPGRADE_BASE_COST * 8.0 * (3.0 ** self.tier))


class Amulet(Equipment):
    """Bonus : régénération de PV passive dédiée. S'xp en régénérant réellement des PV
    (contrairement au casque, qui s'xp lui en ENCAISSANT des dégâts)."""
    def __init__(self, tier: int = 0):
        super().__init__(config.AMULET_TIERS, tier)

    @property
    def effective_regen(self) -> float:
        return self.effective_stat("regen")


class Gauntlet(Equipment):
    """Bonus : dégâts FIXES supplémentaires contre les monstres, ajoutés à ceux de la pioche.
    S'xp UNIQUEMENT en combat (proportionnellement aux dégâts infligés aux monstres)."""
    def __init__(self, tier: int = 0):
        super().__init__(config.GAUNTLET_TIERS, tier)
