"""
Modèle d'IA "compétitif" pour les monstres.

Objectif : que les combats restent intéressants sur la durée sans avoir
à écrire des scripts de comportement pour chaque monstre. On utilise une
approche façon classement ELO :

- Chaque monstre a une "aggressiveness" (probabilité d'attaquer plutôt
  que de se défendre, ce qui influe sur les dégâts pris/rendus).
- On maintient un "skill rating" du joueur (self.player_rating) qui
  monte quand il gagne des combats facilement, descend quand il perd
  ou galère.
- L'aggressiveness des futurs monstres est dérivée de l'écart entre le
  rating du joueur et un rating de référence pour la profondeur
  courante : si le joueur est "trop fort" pour sa profondeur, les
  monstres deviennent plus agressifs (et inversement), ce qui crée une
  difficulté qui s'auto-équilibre au fil de la partie.

C'est un modèle simple mais qui a l'avantage d'être déterministe,
interprétable et pas cher en calcul — adapté à un prototype. Piste
d'évolution : remplacer cette heuristique par une politique entraînée
par renforcement (ex: Q-learning tabulaire sur les états de combat, ou
PPO via stable-baselines3) qui apprendrait à choisir attaque/défense/
esquive en fonction de l'historique du joueur plutôt que par une seule
probabilité scalaire.
"""

from dataclasses import dataclass, field


@dataclass
class CompetitiveAI:
    player_rating: float = 1000.0
    K: float = 24.0   # sensibilité de l'ajustement, comme aux échecs

    def expected_score(self, player_rating: float, monster_rating: float) -> float:
        return 1 / (1 + 10 ** ((monster_rating - player_rating) / 400))

    def reference_rating_for_depth(self, depth: int) -> float:
        # le "niveau attendu" du joueur augmente avec la profondeur
        return 1000 + depth * 1.5

    def update_after_fight(self, depth: int, player_won: bool, hp_ratio_left: float):
        """
        hp_ratio_left : vie restante du joueur (0..1) à l'issue du combat,
        utilisée pour nuancer une victoire écrasante d'une victoire à l'arrache.
        """
        monster_rating = self.reference_rating_for_depth(depth)
        expected = self.expected_score(self.player_rating, monster_rating)
        actual = 1.0 if player_won else 0.0
        if player_won:
            # une victoire avec beaucoup de vie restante vaut "plus" qu'une
            # victoire arrachée de justesse
            actual = 0.7 + 0.3 * hp_ratio_left
        self.player_rating += self.K * (actual - expected)
        self.player_rating = max(400.0, self.player_rating)

    def aggressiveness_for(self, depth: int) -> float:
        ref = self.reference_rating_for_depth(depth)
        diff = self.player_rating - ref
        # diff > 0 : joueur "trop fort" pour sa profondeur -> monstres plus agressifs
        aggressiveness = 0.45 + max(-0.3, min(0.35, diff / 800))
        return round(aggressiveness, 3)
