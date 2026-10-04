"""
Gère l'ensemble des types de pierres du jeu.

Principe :
- Le type de pierre dépend UNIQUEMENT de la profondeur (pas de la
  colonne) pour la variante "dominante" d'une rangée : à une profondeur
  donnée, la plupart des blocs de la galerie se ressemblent. Quelques
  cases peuvent basculer vers une variante voisine du même palier pour
  qu'une rangée ne soit jamais parfaitement uniforme (uniquement là où
  plusieurs variantes existent pour ce palier).
- Diversité progressive et plafonnée au début : de 0 à 1000m, une bande
  fixe de 100m ne contient qu'UNE SEULE variante possible => au plus 10
  types de pierres différents sur ce segment. Au-delà de 1000m, les
  bandes se resserrent et plusieurs variantes peuvent coexister par
  palier, pour une diversité qui s'accélère en profondeur.
- La dureté et la rareté, elles, dépendent directement de la
  profondeur réelle (pas du nombre de variantes), pour que la
  difficulté progresse indépendamment du plafond de diversité.
- Une pierre n'est "connue" (nom affiché) qu'après une première
  découverte, où le joueur peut lui donner un nom personnalisé.
"""

import hashlib
import random
from dataclasses import dataclass
from typing import Dict, Optional

from src import config


@dataclass
class StoneType:
    stone_id: str
    base_color: tuple
    hardness: float
    rarity: str
    depth_tier: int
    custom_name: Optional[str] = None
    discovered: bool = False
    texture_seed: int = 0

    @property
    def display_name(self) -> str:
        if self.discovered and self.custom_name:
            return self.custom_name
        if self.discovered:
            return f"Pierre inconnue ({self.stone_id})"
        return "???"


class StoneRegistry:
    """
    Chaque pierre k possède une plage de profondeur [début, fin[ qui chevauche
    celles de ses voisines (ex. pierre 0 : 0-270 m, pierre 1 : 100-390 m...).
    À une profondeur donnée, on tire parmi toutes les pierres dont la plage
    contient cette profondeur, avec un poids plus fort au centre de la plage.
    Les 10 premières pierres démarrent avant 1000 m (10 types au total sur
    0-1000 m) ; ensuite elles démarrent plus près les unes des autres.
    """

    def __init__(self, seed: int = 1337):
        self._rng_seed = seed
        self._cache: Dict[str, StoneType] = {}
        self._ranges: Dict[int, tuple] = {}

    # ---- plages de profondeur ----
    def stone_range(self, k: int):
        if k not in self._ranges:
            n, step = config.STONE_SHALLOW_COUNT, config.STONE_SHALLOW_STEP
            if k < n:
                start, lens = k * step, config.STONE_SHALLOW_LEN
            else:
                start = n * step + (k - n) * config.STONE_DEEP_STEP
                lens = config.STONE_DEEP_LEN
            length = random.Random(f"{self._rng_seed}-len-{k}").randint(*lens)
            self._ranges[k] = (start, start + length)
        return self._ranges[k]

    def _candidates(self, depth: int):
        n, step = config.STONE_SHALLOW_COUNT, config.STONE_SHALLOW_STEP
        if depth < n * step:
            k_hi = depth // step
        else:
            k_hi = n + (depth - n * step) // config.STONE_DEEP_STEP
        cands = []
        for k in range(k_hi, max(-1, k_hi - 10), -1):
            start, end = self.stone_range(k)
            if start <= depth < end:
                center, half = (start + end) / 2, (end - start) / 2
                weight = max(0.15, 1 - abs(depth - center) / half)
                cands.append((k, weight))
        return cands

    @staticmethod
    def _pick(cands, u):
        total = sum(w for _, w in cands)
        target = u * total
        acc = 0.0
        for k, w in cands:
            acc += w
            if target <= acc:
                return k
        return cands[-1][0]

    def _u(self, *parts) -> float:
        raw = "-".join(str(x) for x in (self._rng_seed,) + parts).encode()
        return (int(hashlib.sha256(raw).hexdigest(), 16) % 100000) / 100000.0

    def _dominant_k(self, depth: int, cands) -> int:
        # la variante dominante change tous les 4 m : voisinage cohérent
        return self._pick(cands, self._u("dom", depth // 4))

    def stone_id_for_depth(self, depth: int) -> str:
        return f"s{self._dominant_k(depth, self._candidates(depth))}"

    def stone_id_for_cell(self, depth: int, col: int) -> str:
        cands = self._candidates(depth)
        dominant = self._dominant_k(depth, cands)
        if len(cands) == 1 or self._u("cell", depth, col) < 0.62:
            return f"s{dominant}"
        return f"s{self._pick(cands, self._u('alt', depth, col))}"

    def _get(self, stone_id: str) -> StoneType:
        if stone_id not in self._cache:
            self._cache[stone_id] = self._generate_stone(int(stone_id[1:]))
        return self._cache[stone_id]

    def get_or_create_for_depth(self, depth: int) -> StoneType:
        return self._get(self.stone_id_for_depth(depth))

    def get_or_create_for_cell(self, depth: int, col: int) -> StoneType:
        return self._get(self.stone_id_for_cell(depth, col))

    def get_by_id(self, stone_id: str) -> StoneType:
        return self._get(stone_id)

    def _generate_stone(self, k: int) -> StoneType:
        stone_id = f"s{k}"
        rng = random.Random(f"{self._rng_seed}-{stone_id}")
        start, end = self.stone_range(k)
        center = (start + end) / 2
        # la dureté se base sur le DÉBUT de la plage (profondeur la plus
        # précoce où cette pierre peut apparaître), pour rester cohérente
        # avec la difficulté réellement rencontrée à ce stade, même si la
        # pierre continue d'exister plus profondément ; la rareté, elle,
        # suit toujours le centre de la plage.
        base_hardness = 0.45 + start * 0.010 + rng.uniform(0, 0.6)
        rarity_roll = rng.random() + center * 0.0006
        if rarity_roll > 0.985:
            rarity = "Mythique"
        elif rarity_roll > 0.94:
            rarity = "Légendaire"
        elif rarity_roll > 0.82:
            rarity = "Épique"
        elif rarity_roll > 0.6:
            rarity = "Rare"
        elif rarity_roll > 0.3:
            rarity = "Peu commune"
        else:
            rarity = "Commune"

        hue_base = (k * 47 + rng.randint(0, 20)) % 360
        base_color = _hsv_to_rgb(hue_base / 360.0, rng.uniform(0.28, 0.55), rng.uniform(0.35, 0.62))
        return StoneType(
            stone_id=stone_id, base_color=base_color, hardness=round(base_hardness, 2),
            rarity=rarity, depth_tier=k, texture_seed=rng.randint(0, 999999),
        )

    def discover(self, stone_id: str) -> bool:
        stone = self._cache[stone_id]
        if stone.discovered:
            return False
        stone.discovered = True
        return True

    def name_stone(self, stone_id: str, name: str) -> None:
        stone = self._cache.get(stone_id)
        if stone:
            stone.custom_name = name.strip()[:30] or stone.custom_name

    def all_discovered(self):
        return [s for s in self._cache.values() if s.discovered]

    def to_dict(self) -> dict:
        return {
            sid: {
                "hardness": s.hardness, "rarity": s.rarity, "depth_tier": s.depth_tier,
                "color": s.base_color, "custom_name": s.custom_name,
                "discovered": s.discovered, "texture_seed": s.texture_seed,
            }
            for sid, s in self._cache.items() if s.discovered
        }

    def load_dict(self, data: dict) -> None:
        for sid, d in data.items():
            if not (sid.startswith("s") and sid[1:].isdigit()):
                continue  # ancien format de sauvegarde
            self._cache[sid] = StoneType(
                stone_id=sid, base_color=tuple(d["color"]), hardness=d["hardness"],
                rarity=d["rarity"], depth_tier=d["depth_tier"],
                custom_name=d.get("custom_name"), discovered=d.get("discovered", True),
                texture_seed=d.get("texture_seed", 0),
            )


def _hsv_to_rgb(h, s, v):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))
