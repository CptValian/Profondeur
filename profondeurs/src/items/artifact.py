"""
Artefacts de civilisations anciennes.

Le catalogue est fixe (défini ici) : c'est une collection à compléter,
un peu comme un "pokédex". Certains artefacts rares donnent un bonus
passif au joueur (et pourraient être partagés au niveau du Clan côté
serveur, non implémenté dans ce prototype local).
"""

import random
from dataclasses import dataclass
from typing import Optional, List

from src import config


@dataclass
class ArtifactDef:
    artifact_id: str
    name: str
    rarity: str
    min_depth: int
    description: str
    bonus_desc: str
    bonus_type: Optional[str] = None   # ex: "mining_power", "max_health", "move_speed"
    bonus_value: float = 0.0


ARTIFACT_CATALOG_DEFS: List[ArtifactDef] = [
    ArtifactDef("relic_shard", "Éclat de poterie", "Commune", 10,
                "Un fragment de vase d'une civilisation oubliée.",
                "+6 points de vie max", "max_health", 6),
    ArtifactDef("clay_tablet", "Tablette d'argile gravée", "Commune", 25,
                "Des symboles indéchiffrables y sont inscrits.",
                "+8% d'or gagné", "gold_pct", 0.08),
    ArtifactDef("bronze_coin", "Pièce de bronze ancienne", "Peu commune", 40,
                "Une monnaie usée, frappée d'un symbole inconnu.",
                "+5 puissance de minage", "mining_power", 5),
    ArtifactDef("rusted_buckle", "Boucle de ceinturon rouillée", "Peu commune", 60,
                "Elle appartenait sans doute à un mineur comme toi.",
                "+10% de réduction des dégâts", "damage_reduction", 0.10),
    ArtifactDef("stone_idol", "Idole de pierre", "Rare", 120,
                "Une statuette représentant une divinité minière.",
                "+40 points de vie max", "max_health", 40),
    ArtifactDef("miners_lamp", "Lanterne du premier mineur", "Rare", 160,
                "Sa flamme n'a jamais vacillé, même sous terre.",
                "+18% d'or gagné", "gold_pct", 0.18),
    ArtifactDef("obsidian_ring", "Anneau d'obsidienne", "Rare", 220,
                "Froid au toucher, il absorbe la lumière autour de lui.",
                "+18% de réduction des dégâts", "damage_reduction", 0.18),
    ArtifactDef("crystal_compass", "Boussole de cristal", "Épique", 300,
                "Elle vibre légèrement en présence de trésors.",
                "+60% de chance d'artefact inédit après un doublon", "artifact_luck", 0.60),
    ArtifactDef("engraved_pickhead", "Tête de pioche gravée", "Épique", 380,
                "Une relique forgée par un maître mineur disparu.",
                "+14 puissance de minage", "mining_power", 14),
    ArtifactDef("golden_mask", "Masque doré du Roi-Puits", "Légendaire", 600,
                "On raconte qu'il régnait sur les mineurs abyssaux.",
                "+16 puissance de minage, +60 PV max", "combo_king", 0),
    ArtifactDef("phoenix_ember", "Braise de phénix minéral", "Légendaire", 750,
                "Elle reste tiède, comme si quelque chose y dormait encore.",
                "+100 points de vie max", "max_health", 100),
    ArtifactDef("gravity_shard", "Éclat anti-gravité", "Légendaire", 900,
                "Il flotte à quelques millimètres de ta paume.",
                "+35% de puissance de minage", "mining_power_pct", 0.35),
    ArtifactDef("void_seed", "Graine du Vide", "Mythique", 1500,
                "Elle n'a ni poids, ni température, ni logique.",
                "+100% puissance de minage", "mining_power_pct", 1.0),
    ArtifactDef("eternal_core", "Noyau éternel", "Mythique", 2200,
                "Son cœur bat au rythme du tien, désormais.",
                "+35% de réduction des dégâts, +30% d'or", "combo_titan", 0),
    ArtifactDef("pick_handle", "Manche de pioche usé", "Commune", 15,
                "Lissé par des générations de paumes calleuses.",
                "+5% de puissance de minage", "mining_power_pct", 0.05),
    ArtifactDef("bone_flute", "Flûte d'os sculptée", "Commune", 35,
                "Elle ne produit qu'une note, mais les murs l'écoutent.",
                "+10% d'or gagné", "gold_pct", 0.10),
    ArtifactDef("miners_charm", "Gri-gri de mineur", "Peu commune", 70,
                "Des dents et des perles nouées sur une cordelette.",
                "+20 points de vie max", "max_health", 20),
    ArtifactDef("tarnished_medal", "Médaille ternie", "Peu commune", 100,
                "Décernée à un vainqueur dont on a oublié le nom.",
                "+8 dégâts contre les monstres", "combat_damage", 8),
    ArtifactDef("gauntlet_plate", "Plaque de gantelet antique", "Rare", 190,
                "Une articulation de métal qui se souvient des coups.",
                "+16 dégâts contre les monstres", "combat_damage", 16),
    ArtifactDef("scavenger_satchel", "Besace du fouilleur", "Rare", 260,
                "Elle est toujours un peu plus lourde qu'elle ne devrait.",
                "+70% de chance de trouver des composants", "component_luck", 0.70),
    ArtifactDef("seismic_crystal", "Cristal sismique", "Épique", 450,
                "Il tremble une seconde avant chaque éboulement.",
                "+22% de puissance de minage", "mining_power_pct", 0.22),
    ArtifactDef("warlord_banner", "Étendard du seigneur de guerre", "Épique", 520,
                "Un lambeau de tissu qui donne envie de se battre.",
                "+30 dégâts contre les monstres", "combat_damage", 30),
    ArtifactDef("depth_hourglass", "Sablier des profondeurs", "Légendaire", 1100,
                "Le sable y tombe vers le haut.",
                "+80% de chance d'artefact inédit après un doublon", "artifact_luck", 0.80),
    ArtifactDef("mountain_heart", "Cœur de la montagne", "Mythique", 2800,
                "La roche elle-même semble battre autour de lui.",
                "+40% minage, +40 dégâts contre les monstres", "combo_mountain", 0),
    # ---- 10 artefacts à effet UNIQUE ----
    ArtifactDef("thunder_pick", "Pic du Tonnerre", "Rare", 300,
                "Chaque coup résonne une seconde avant de frapper.",
                "15% de chance de coup critique sur les blocs (dégâts x3)", "crit_chance", 0.15),
    ArtifactDef("golden_vein", "Veine dorée", "Peu commune", 140,
                "Une pépite qui attire ses semblables.",
                "15% de chance de doubler l'or d'un bloc", "gold_double_chance", 0.15),
    ArtifactDef("ancestors_breath", "Souffle des ancêtres", "Légendaire", 700,
                "Un soupir figé dans une fiole de verre.",
                "Une fois toutes les 4 min, un KO te ranime à 50% PV, sans aucune pénalité", "second_wind", 1),
    ArtifactDef("miner_frenzy", "Frénésie du mineur", "Épique", 400,
                "Le manche vibre dès qu'un bloc cède.",
                "+35% de cadence pendant 3 s après chaque bloc cassé", "haste_on_break", 0.35),
    ArtifactDef("elder_grimoire", "Grimoire des anciens", "Épique", 550,
                "Les pages se tournent toutes seules quand tu progresses.",
                "+40% d'XP pour la pioche et tous les équipements", "xp_boost", 0.40),
    ArtifactDef("predator_heart", "Cœur du prédateur", "Rare", 240,
                "Il bat plus fort près d'une proie.",
                "Chaque monstre vaincu te soigne de 25% de tes PV max", "heal_on_kill", 0.25),
    ArtifactDef("living_stone", "Pierre vivante", "Peu commune", 110,
                "Elle est tiède, et se nourrit de poussière de roche.",
                "+3 PV à chaque bloc cassé", "regen_on_break", 3),
    ArtifactDef("ancestral_aegis", "Égide ancestrale", "Rare", 200,
                "Le bouclier d'un mineur qui n'a jamais été touché.",
                "Le premier coup de chaque monstre est annulé", "block_first_hit", 1),
    ArtifactDef("hunter_purse", "Bourse du chasseur", "Peu commune", 180,
                "Elle tinte, même vide.",
                "L'or gagné sur les monstres est doublé", "monster_gold_mult", 1.0),
    ArtifactDef("gambler_nugget", "Pépite du joueur", "Épique", 480,
                "Une face lisse, une face rugueuse. Elle retombe toujours du bon côté.",
                "Un bloc sur 10 rapporte x4 d'or (jackpot)", "jackpot", 1),
]


def artifact_effects(adef) -> dict:
    """Décompose un artefact en effets élémentaires {clé: valeur} (partagé joueur / IA)."""
    bt, v = adef.bonus_type, adef.bonus_value
    if bt == "combo_king":
        return {"mining_power": 16, "max_health": 60}
    if bt == "combo_titan":
        return {"damage_reduction": 0.35, "gold_pct": 0.30}
    if bt == "combo_mountain":
        return {"mining_power_pct": 0.40, "combat_damage": 40}
    return {bt: v} if bt else {}


class ArtifactCatalog:
    def __init__(self):
        self.defs = {a.artifact_id: a for a in ARTIFACT_CATALOG_DEFS}
        self.found: set = set()

    RARITY_WEIGHT = {"Commune": 10, "Peu commune": 6, "Rare": 3, "Épique": 1.4, "Légendaire": 0.5, "Mythique": 0.12}

    def _weighted_pick(self, pool, rng) -> Optional[str]:
        if not pool:
            return None
        weights = [self.RARITY_WEIGHT[a.rarity] for a in pool]
        return rng.choices(pool, weights=weights, k=1)[0].artifact_id

    def roll_artifact(self, depth: int, rng: random.Random) -> Optional[str]:
        eligible = [a for a in self.defs.values() if a.min_depth <= depth]
        return self._weighted_pick(eligible, rng)

    # ---- protection contre la malchance (doublons) ----
    def pity_chance(self, pity: int, luck: float = 0.0, flat: float = 0.0) -> float:
        """Chance que le prochain artefact soit inédit, après `pity` doublons d'affilée."""
        return min(config.ARTIFACT_PITY_MAX, pity * config.ARTIFACT_PITY_STEP * (1 + luck) + flat)

    def resolve_drop(self, artifact_id: str, depth: int, pity: int, luck: float, rng, flat: float = 0.0):
        """
        Appelé quand une pierre d'artefact est cassée. Si l'artefact tiré est déjà
        connu (doublon), il peut être remplacé par un artefact inédit avec une
        probabilité qui grandit à chaque doublon successif.
        Retourne (artifact_id_final, nouveau_compteur).
        """
        if artifact_id not in self.found:
            return artifact_id, 0
        if rng.random() < self.pity_chance(pity, luck, flat):
            fresh = self._weighted_pick(
                [a for a in self.defs.values() if a.min_depth <= depth and a.artifact_id not in self.found], rng)
            if fresh:
                return fresh, 0
        return artifact_id, pity + 1

    def mark_found(self, artifact_id: str) -> bool:
        """Retourne True si c'est une toute première découverte de cet artefact."""
        if artifact_id in self.found:
            return False
        self.found.add(artifact_id)
        return True

    def completion_ratio(self) -> float:
        return len(self.found) / len(self.defs)
