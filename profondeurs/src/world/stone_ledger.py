"""
Registre GLOBAL des pierres : le premier mineur (joueur ou IA) qui découvre un type de
pierre la nomme pour tout le monde, et toute sa faction gagne +10 % de vitesse de
cassage sur cette pierre. La toute première pierre (s0) ne donne pas de bonus.
Tous les mineurs partagent la même génération de pierres (même graine de registre),
donc "s7" désigne la même pierre pour le joueur comme pour les IA.
"""

from src import config


class StoneLedger:
    def __init__(self):
        self.entries = {}   # stone_id -> {"name", "by", "team"}

    def get(self, stone_id):
        return self.entries.get(stone_id)

    def claim(self, stone_id, by, team, name) -> bool:
        """Retourne True si ce mineur est bien le premier à découvrir cette pierre."""
        if stone_id in self.entries:
            return False
        self.entries[stone_id] = {"name": name, "by": by, "team": team}
        return True

    def rename(self, stone_id, name):
        if stone_id in self.entries and name.strip():
            self.entries[stone_id]["name"] = name.strip()[:30]

    def team_bonus(self, team, stone_id) -> float:
        e = self.entries.get(stone_id)
        if e and e["team"] == team and stone_id != config.STONE_NO_BONUS_ID:
            return config.STONE_FACTION_BONUS
        return 0.0

    def team_stones(self, team):
        return [sid for sid, e in self.entries.items() if e["team"] == team and sid != config.STONE_NO_BONUS_ID]

    def sync(self, registry):
        """Applique les noms globaux aux pierres déjà connues d'un registre."""
        for sid, e in self.entries.items():
            st = registry._cache.get(sid)
            if st is not None:
                st.custom_name = e["name"]

    def to_dict(self):
        return dict(self.entries)

    def load_dict(self, data):
        self.entries = {sid: dict(e) for sid, e in data.items()}
