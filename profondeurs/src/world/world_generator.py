"""Génère et fournit à la demande les blocs de la galerie de mine."""

import hashlib
import random
from typing import Dict, Tuple

from src import config
from src.world.block import Block
from src.world.stone_registry import StoneRegistry
from src.items.artifact import ArtifactCatalog


class WorldGenerator:
    def __init__(self, stone_registry: StoneRegistry, artifact_catalog: ArtifactCatalog, seed: int = 1337):
        self.stones = stone_registry
        self.artifacts = artifact_catalog
        self.seed = seed
        self.blocks: Dict[Tuple[int, int], Block] = {}

    def _rng_for(self, row: int, col: int) -> random.Random:
        raw = f"{self.seed}-{row}-{col}".encode()
        h = hashlib.sha256(raw).hexdigest()
        return random.Random(h)

    def get_block(self, row: int, col: int) -> Block:
        key = (row, col)
        if key not in self.blocks:
            self.blocks[key] = self._generate_block(row, col)
        return self.blocks[key]

    # ---- sauvegarde des galeries creusées (un masque de colonnes par rangée) ----
    def export_dug(self) -> dict:
        rows = {}
        for (row, col), b in self.blocks.items():
            if b.is_empty:
                rows[row] = rows.get(row, 0) | (1 << col)
        return {str(r): m for r, m in rows.items()}

    def import_dug(self, data: dict) -> None:
        for r, mask in data.items():
            row = int(r)
            for col in range(config.GRID_COLS):
                if (mask >> col) & 1:
                    b = self.get_block(row, col)
                    b.is_empty = True
                    b.contains_monster = False
                    b.contains_artifact = None

    def _generate_block(self, row: int, col: int) -> Block:
        rng = self._rng_for(row, col)
        stone = self.stones.get_or_create_for_cell(row, col)

        artifact_id = None
        artifact_chance = min(0.015 + row * 0.00004, 0.05) / config.ARTIFACT_RARITY_DIVISOR
        if rng.random() < artifact_chance:
            artifact_id = self.artifacts.roll_artifact(row, rng)

        contains_monster = False
        if row > 5:
            spawn_chance = min(config.MONSTER_SPAWN_CHANCE + row * 0.00006, 0.18)
            if rng.random() < spawn_chance:
                contains_monster = True

        return Block(
            stone_id=stone.stone_id,
            hardness=stone.hardness,
            depth=row,
            resource_amount=rng.randint(1, 3),
            contains_artifact=artifact_id,
            contains_monster=contains_monster,
        )
