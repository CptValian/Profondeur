"""Inventaire : ressources minées, artefacts, composants de craft et unités fabriquées."""

from collections import defaultdict

from src.items import tower as tower_mod


class Inventory:
    def __init__(self):
        self.resources = defaultdict(int)    # stone_id -> quantité
        self.gold = 0
        self.owned_artifacts = set()
        self.components = defaultdict(int)   # component_id -> quantité
        self.components_seen = set()         # composants déjà découverts (pour le menu)
        self.units = defaultdict(int)        # recipe_id -> nombre de troupes/défenses fabriquées
        self.tower = tower_mod.default_levels()   # niveaux du donjon d'archer
        self.war_wins = 0                    # victoires en guerre (attaque ou défense réussie)
        self.xp_stones = 0                   # pierres d'XP passives pour le niveau principal

    def add_resource(self, stone_id: str, amount: int = 1):
        self.resources[stone_id] += amount

    def add_artifact(self, artifact_id: str):
        self.owned_artifacts.add(artifact_id)

    def add_component(self, component_id: str, amount: int = 1):
        self.components[component_id] += amount
        self.components_seen.add(component_id)

    def spend_gold(self, amount: int) -> bool:
        if self.gold >= amount:
            self.gold -= amount
            return True
        return False

    def total_resources(self) -> int:
        return sum(self.resources.values())

    def total_components(self) -> int:
        return sum(self.components.values())
