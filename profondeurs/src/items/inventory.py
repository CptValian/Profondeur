"""Inventaire : ressources minées, artefacts, composants de craft et unités fabriquées."""

from collections import defaultdict

from src.items import tower as tower_mod


class Inventory:
    def __init__(self):
        self.resources = defaultdict(int)    # stone_id -> quantité
        self.gold = 20
        self.owned_artifacts = set()
        self.components = defaultdict(int)   # component_id -> quantité
        self.components_seen = set()         # composants déjà découverts (pour le menu)
        self.units = defaultdict(int)        # recipe_id -> nombre de troupes/défenses fabriquées
        self.tower = tower_mod.default_levels()   # niveaux du donjon d'archer
        self.war_wins = 0                    # victoires en guerre (attaque ou défense réussie)
        self.xp_stones = 0                   # pierres d'XP passives pour le niveau principal

        # --- Monuments & Bâtisseurs ---
        self.stone_fragments = 0.0           # 1 fragment = 1 HP de pierre
        self.builders = 0                    # nombre de bâtisseurs recrutés
        self.monument_progress = 0.0         # fragments convertis pour le monument actuel
        self.monuments_built = 0             # monuments achevés (+5% de puissance par monument)

    def required_monument_fragments(self) -> int:
        n = self.monuments_built
        if n == 0:
            return 1000
        elif n == 1:
            return 5000
        elif n == 2:
            return 20000
        else:
            return int(20000 * (4 ** (n - 2)))

    def builder_cost(self) -> int:
        return int(50 * (1.6 ** self.builders))

    def recruit_builder(self) -> bool:
        cost = self.builder_cost()
        if self.spend_gold(cost):
            self.builders += 1
            return True
        return False

    def tick_monuments(self, dt: float) -> bool:
        """Retourne True si un monument vient d'être achevé."""
        if self.builders <= 0 or self.stone_fragments <= 0:
            return False
        rate = float(self.builders)
        convertible = min(self.stone_fragments, rate * dt)
        self.stone_fragments -= convertible
        self.monument_progress += convertible

        needed = self.required_monument_fragments()
        if self.monument_progress >= needed:
            self.monument_progress -= needed
            self.monuments_built += 1
            return True
        return False

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
