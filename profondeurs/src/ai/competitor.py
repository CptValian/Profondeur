"""
Mineurs IA concurrents.

Objectif de conception : donner à chaque IA "la même interface" que le
joueur, c'est-à-dire qu'elle joue avec exactement les mêmes règles
(mêmes types de pierres par profondeur, mêmes paliers de pioche, même
système de combat/artefacts) — simplement pilotée par une politique de
décision au lieu d'une souris. Chaque IA possède donc son propre monde
(seed différente), son propre inventaire, sa propre pioche, etc.,
et est mise à jour à chaque frame comme un joueur autonome.

Facteurs de compétition / leviers stratégiques implémentés
------------------------------------------------------------
- **Vitesse de forage vs prudence** : une IA agressive fonce et prend
  des risques sur des blocs plus durs (elle "boucle" sur le bloc le
  moins dur accessible mais tente aussi parfois un bloc plus profond
  quand même), une IA prudente attend d'avoir une meilleure pioche.
- **Gestion de l'or : dépenser tôt vs épargner** (`upgrade_readiness`) :
  certaines IA améliorent leur pioche dès que possible (petits gains
  fréquents), d'autres épargnent pour ne upgrader qu'avec une marge de
  sécurité, ce qui les ralentit court terme mais peut payer sur la
  durée si la marge accélère les paliers suivants.
- **Combat vs fuite** (`risk_tolerance`) : face à un monstre, chaque IA
  évalue le rapport de force (ses PV/dégâts vs le monstre) et décide
  de combattre ou fuir. Une IA trop agressive peut mourir et perdre du
  temps (pénalité de KO), une IA trop craintive perd des opportunités
  de gain (or, XP de "compétence" implicite).
- **Chasse aux artefacts vs vitesse pure** (`artifact_focus`) : une IA
  "chasseuse de trésors" dévie parfois latéralement pour explorer
  plutôt que de foncer vers le bas, ce qui ralentit sa profondeur mais
  peut lui donner des bonus permanents (comme pour le joueur).
- **Variance d'exécution** (`efficiency_variance`) : un peu de hasard
  dans la cadence effective, pour que deux IA au même profil ne soient
  jamais parfaitement synchronisées (rend le classement vivant).

Le score d'efficacité utilisé pour le classement combine profondeur,
or et objets de collection, pour éviter qu'une seule stratégie
(foncer sans jamais combattre, par ex.) soit automatiquement optimale.
"""

import random
from dataclasses import dataclass, field
from typing import Optional

from src import config
from src.world.stone_registry import StoneRegistry
from src.world.stone_ledger import StoneLedger
from src.world.world_generator import WorldGenerator
from src.items.artifact import ArtifactCatalog
from src.items.tool import Tool
from src.items import crafting, tower as tower_mod
from src.items.artifact import artifact_effects
from src.items.inventory import Inventory
from src.entities.monster import spawn_monster
from src.combat import combat_system as combat


AI_PROFILES = [
    # -- Équipe 0 : "Ta compagnie" (3 IA + toi) --
    {"name": "Forgemaître Brok",    "team": 0, "risk_tolerance": 0.75,
     "upgrade_readiness": 0.55, "artifact_focus": 0.15, "efficiency_variance": 0.18},
    {"name": "Dame Silice",         "team": 0, "risk_tolerance": 0.35,
     "upgrade_readiness": 0.85, "artifact_focus": 0.55, "efficiency_variance": 0.10},
    {"name": "Le Taupier",          "team": 0, "risk_tolerance": 0.50,
     "upgrade_readiness": 0.65, "artifact_focus": 0.30, "efficiency_variance": 0.14},
    # -- Équipe 1 : "Les Marteaux d'Onyx" --
    {"name": "Vex l'Avide",         "team": 1, "risk_tolerance": 0.55,
     "upgrade_readiness": 0.35, "artifact_focus": 0.10, "efficiency_variance": 0.22},
    {"name": "Grondin le Lourd",    "team": 1, "risk_tolerance": 0.80,
     "upgrade_readiness": 0.45, "artifact_focus": 0.05, "efficiency_variance": 0.16},
    {"name": "Ora Perce-Roche",     "team": 1, "risk_tolerance": 0.60,
     "upgrade_readiness": 0.60, "artifact_focus": 0.20, "efficiency_variance": 0.12},
    {"name": "Kelt le Silencieux",  "team": 1, "risk_tolerance": 0.40,
     "upgrade_readiness": 0.70, "artifact_focus": 0.25, "efficiency_variance": 0.09},
    # -- Équipe 2 : "La Confrérie du Puits" --
    {"name": "Sœur Mira",           "team": 2, "risk_tolerance": 0.30,
     "upgrade_readiness": 0.90, "artifact_focus": 0.60, "efficiency_variance": 0.08},
    {"name": "Frère Odal",          "team": 2, "risk_tolerance": 0.45,
     "upgrade_readiness": 0.75, "artifact_focus": 0.45, "efficiency_variance": 0.11},
    {"name": "L'Ancien Vess",       "team": 2, "risk_tolerance": 0.25,
     "upgrade_readiness": 0.95, "artifact_focus": 0.35, "efficiency_variance": 0.07},
    {"name": "Petite Nyle",         "team": 2, "risk_tolerance": 0.65,
     "upgrade_readiness": 0.50, "artifact_focus": 0.50, "efficiency_variance": 0.20},
    # -- Équipe 3 : "Les Foreurs Écarlates" --
    {"name": "Rax Tranche-Pierre",  "team": 3, "risk_tolerance": 0.85,
     "upgrade_readiness": 0.30, "artifact_focus": 0.05, "efficiency_variance": 0.24},
    {"name": "Ignis la Rouge",      "team": 3, "risk_tolerance": 0.90,
     "upgrade_readiness": 0.40, "artifact_focus": 0.10, "efficiency_variance": 0.19},
    {"name": "Kovan Sans-Peur",     "team": 3, "risk_tolerance": 0.70,
     "upgrade_readiness": 0.55, "artifact_focus": 0.15, "efficiency_variance": 0.15},
    {"name": "Zeph l'Éclair",       "team": 3, "risk_tolerance": 0.60,
     "upgrade_readiness": 0.50, "artifact_focus": 0.20, "efficiency_variance": 0.25},
]


def _profile_color(profile, index_in_team):
    """Chaque IA prend une variation de la couleur de son équipe, pour rester
    identifiable comme membre de l'équipe tout en étant distinguable des
    autres."""
    base = config.TEAM_COLORS[profile["team"]]
    factors = [1.0, 0.8, 1.18, 0.62]
    f = factors[index_in_team % len(factors)]
    return tuple(max(0, min(255, int(c * f))) for c in base)


def _assign_colors():
    counts = {}
    colors = []
    for p in AI_PROFILES:
        i = counts.get(p["team"], 0)
        colors.append(_profile_color(p, i))
        counts[p["team"]] = i + 1
    return colors


AI_COLORS = _assign_colors()


@dataclass
class AIState:
    row: int = 0
    col: int = config.GRID_COLS // 2
    health: float = config.PLAYER_START_HEALTH
    max_health: float = config.PLAYER_START_HEALTH
    alive: bool = True
    mining_power_bonus: float = 0.0
    mining_power_pct: float = 0.0
    damage_reduction: float = 0.0
    gold_pct: float = 0.0
    combat_damage: float = 0.0
    component_luck: float = 0.0


class AIMiner:
    def __init__(self, name: str, color, team: int, risk_tolerance: float, upgrade_readiness: float,
                 artifact_focus: float, efficiency_variance: float, seed_offset: int,
                 power_mult: float = 1.0, speed_mult: float = 1.0, risk_mult: float = 1.0,
                 difficulty: str = "Normal", ledger: StoneLedger = None):
        self.name = name
        self.color = color
        self.team = team
        self.difficulty = difficulty
        self.risk_tolerance = min(1.0, risk_tolerance * risk_mult)
        self.upgrade_readiness = upgrade_readiness
        self.artifact_focus = artifact_focus
        self.efficiency_variance = efficiency_variance
        self.power_mult = power_mult
        self.speed_mult = speed_mult

        self.rng = random.Random(f"ai-{name}-{seed_offset}")
        self.ledger = ledger if ledger is not None else StoneLedger()
        self.stones = StoneRegistry()    # même génération de pierres pour tous les mineurs
        self.artifacts = ArtifactCatalog()
        self.world = WorldGenerator(self.stones, self.artifacts, seed=2000 + seed_offset)
        self.own_world = self.world
        self.joint_grid_callback = None
        self.tool = Tool(tier=0)
        self.inventory = Inventory()
        self.state = AIState()
        self.artifact_pity = 0

        self.status = "creuse"          # creuse / combat / fuite / ko
        self.in_combat_monster = None
        self.combat_target_block = None
        self.target_cell = None
        self.last_cell = None
        self.flee_counts = {}
        self.ko_counts = {}
        self._pending_cell = None
        self._time_since_hit = 0.0
        self._respawn_timer = 0.0

    # ------------------------------------------------------------------
    @property
    def mining_power(self) -> float:
        base = self.tool.power + self.state.mining_power_bonus
        return base * (1 + self.state.mining_power_pct) * self.power_mult

    @property
    def attack_interval(self) -> float:
        return self.tool.attack_interval / self.speed_mult

    def war_items(self):
        return [self.tool]

    _STONE_WORDS = ("Pierre", "Roche", "Granit", "Basalte", "Schiste", "Quartz", "Gneiss", "Silex")
    _STONE_ADJ = ("grise", "veinée", "pâle", "sombre", "rouillée", "scintillante", "froide", "ardente", "moussue", "dorée")

    def _claim_stone(self, stone_id):
        """Le premier mineur à découvrir une pierre la nomme pour tout le monde."""
        stone = self.stones.get_by_id(stone_id)
        entry = self.ledger.get(stone_id)
        if entry is None:
            name = f"{self.rng.choice(self._STONE_WORDS)} {self.rng.choice(self._STONE_ADJ)}"
            self.ledger.claim(stone_id, self.name, self.team, name)
            entry = self.ledger.get(stone_id)
        stone.custom_name = entry["name"]

    def score(self) -> float:
        return (self.state.row * 2.0 + self.inventory.gold * 0.5
                + len(self.artifacts.found) * 20 + len(self.stones.all_discovered()) * 4
                + self.inventory.war_wins * config.WAR_WIN_SCORE)

    # ------------------------------------------------------------------
    def _reachable_cells(self):
        r, c = self.state.row, self.state.col
        cells = [(r, c - 1), (r, c + 1), (r + 1, c)]
        return [(rr, cc) for rr, cc in cells if 0 <= cc < config.GRID_COLS and rr >= 0]

    def _reachable_empty(self):
        empties = []
        for row, col in self._reachable_cells():
            block = self.world.get_block(row, col)
            if block.is_empty:
                empties.append((row, col))
        return empties

    def _choose_target(self):
        """
        Choisit la meilleure case adjacente, qu'elle soit à miner ou déjà
        vide (auquel cas il s'agit simplement de s'y déplacer). Le calcul
        pénalise fortement un retour immédiat sur la dernière case quittée
        pour éviter les allers-retours en boucle entre deux cases creusées.
        """
        options = self._reachable_cells()
        best = None
        best_score = None
        for row, col in options:
            block = self.world.get_block(row, col)
            going_down = row == self.state.row + 1

            if block.is_empty:
                if going_down:
                    desirability = 3.5
                elif self.world.get_block(row + 1, col).is_empty:
                    desirability = 3.0   # case latérale qui mène vers une descente déjà creusée
                else:
                    desirability = -6.0  # aller-retour inutile : mieux vaut miner
            else:
                # une pierre d'artefact est bien plus longue à miner : seuls les "chasseurs" (artifact_focus) l'acceptent
                hardness = block.hardness
                if block.contains_artifact:
                    hardness *= 1 + (config.ARTIFACT_BLOCK_HARDNESS_MULT - 1) * (1 - self.artifact_focus)
                desirability = -hardness + (0.6 if going_down else 0.0)
                if block.contains_monster:
                    # on évite de plus en plus un monstre qui nous a déjà fait fuir/KO
                    desirability -= 0.3 + 2.5 * self.flee_counts.get((row, col), 0)
                    desirability -= 5.0 * self.ko_counts.get((row, col), 0)

            if (row, col) == self.last_cell:
                desirability -= 3.0

            if self.difficulty == "Extrême":
                if going_down:
                    desirability += 2.5
                else:
                    desirability -= 1.5

            if self.rng.random() < self.artifact_focus * 0.4:
                desirability += self.rng.uniform(0, 1.5)

            if best_score is None or desirability > best_score:
                best_score = desirability
                best = (row, col)
        return best

    def _try_upgrade(self):
        cost = self.tool.upgrade_cost()
        if cost >= 0:
            threshold = cost * (1.01 if self.difficulty == "Extrême" else (1 + self.upgrade_readiness))
            if self.inventory.gold >= threshold or self.inventory.gold >= cost * 1.01:
                if self.inventory.spend_gold(cost):
                    self.tool.upgrade()
                    return
        self._try_tower_upgrade()

    @property
    def level(self) -> int:
        """Niveau équivalent du mineur IA calculé à partir de l'XP de sa pioche."""
        l = 1
        xp = getattr(self.tool, "total_xp", lambda: self.tool.xp)()
        while l < config.PLAYER_MAX_LEVEL and xp >= config.PLAYER_XP_BASE * (l ** config.PLAYER_XP_EXPONENT):
            xp -= config.PLAYER_XP_BASE * (l ** config.PLAYER_XP_EXPONENT)
            l += 1
        return l

    def _try_tower_upgrade(self):
        """Quand la pioche attend trop cher, les IA prudentes investissent dans leur donjon d'archer."""
        if self.rng.random() > 0.35 * (1.2 - self.risk_tolerance):
            return
        available_tracks = [
            k for k in tower_mod.TRACKS
            if k != "supreme" or self.level >= config.TOWER_TRACK_UNLOCK.get("supreme", 30)
        ]
        key = self.rng.choice(available_tracks)
        cost = tower_mod.upgrade_cost(self.inventory.tower, key)
        if cost >= 0 and self.inventory.gold >= cost * (1.5 + self.upgrade_readiness):
            tower_mod.upgrade(self.inventory, key)

    def _apply_artifact(self, adef, heal=True):
        for key, val in artifact_effects(adef).items():
            if key == "mining_power":
                self.state.mining_power_bonus += val
            elif key == "mining_power_pct":
                self.state.mining_power_pct += val
            elif key == "max_health":
                self.state.max_health += val
                if heal:
                    self.state.health += val
            elif key == "damage_reduction":
                self.state.damage_reduction += val
            elif key == "gold_pct":
                self.state.gold_pct += val
            elif key == "combat_damage":
                self.state.combat_damage += val
            elif key == "component_luck":
                self.state.component_luck += val
            # les effets uniques (critique, jackpot...) sont réservés au joueur

    def recompute_artifact_bonuses(self):
        st = self.state
        st.mining_power_bonus = st.mining_power_pct = st.damage_reduction = st.gold_pct = 0.0
        st.combat_damage = st.component_luck = 0.0
        st.max_health = config.PLAYER_START_HEALTH
        for aid in self.artifacts.found:
            if aid in self.artifacts.defs and self.artifacts.defs[aid].bonus_type:
                self._apply_artifact(self.artifacts.defs[aid], heal=False)
        st.health = min(st.health, st.max_health)

    def _grant_artifact(self, artifact_id):
        first = self.artifacts.mark_found(artifact_id)
        self.inventory.add_artifact(artifact_id)
        if first:
            self._apply_artifact(self.artifacts.defs[artifact_id])

    # ------------------------------------------------------------------
    def _roll_component(self, depth, chance, hardness=1.0):
        cid = crafting.roll_component(depth, self.rng, chance, self.state.component_luck, hardness=hardness)
        if cid:
            self.inventory.add_component(cid)
            self._try_craft()

    def _try_craft(self):
        """Fabrique automatiquement la meilleure unité accessible (les IA aussi
        se constituent une armée pour les futurs combats entre factions)."""
        affordable = [r for r in crafting.RECIPES if crafting.can_craft(self.inventory, r)]
        if affordable:
            best = max(affordable, key=lambda r: r.attack + r.health / 4 + r.defense * 2)
            crafting.craft(self.inventory, best.recipe_id)

    # ------------------------------------------------------------------
    def _start_combat(self, block):
        monster = spawn_monster(block.depth, aggressiveness=0.5)
        # une IA agressive attire (au sens stratégique) des affrontements plus rentables
        # mais aussi plus risqués : on ne modifie pas le monstre, seulement la décision.
        power_ratio = self.mining_power / max(1.0, monster.max_health / 4)
        danger = monster.attack / max(1.0, self.state.health)
        cell = (block.depth, self._pending_cell[1] if self._pending_cell else -1)
        flees = self.flee_counts.get(cell, 0)
        will_fight = (self.risk_tolerance + power_ratio * 0.3) > danger or (flees >= 2 and self.ko_counts.get(cell, 0) == 0)
        if will_fight:
            self.status = "combat"
            self.in_combat_monster = monster
            self.combat_target_block = block
        else:
            self.flee_counts[cell] = flees + 1
            self.status = "fuite"
            self._respawn_timer = 0.4  # petite pénalité de temps pour la fuite

    def _resolve_combat_tick(self):
        monster = self.in_combat_monster
        result = combat.CombatResult()
        combat.player_attack(_FakePlayer(self), monster, result)
        if result.finished and result.player_won:
            self.combat_target_block.is_empty = True
            self.combat_target_block.contains_monster = False
            gold = (5 + self.combat_target_block.depth // 10) * (1 + self.state.gold_pct)
            self.inventory.gold += gold
            self._roll_component(self.combat_target_block.depth, config.COMPONENT_MONSTER_DROP_CHANCE)
            self.in_combat_monster = None
            self.status = "creuse"
            return
        result2 = combat.CombatResult()
        combat.monster_turn(_FakePlayer(self), monster, result2)
        if result2.finished and not result2.player_won:
            if self.combat_target_block is not None:
                key = (self.combat_target_block.depth, self._pending_cell[1] if self._pending_cell else -1)
                self.ko_counts[key] = self.ko_counts.get(key, 0) + 1
            self.state.health = self.state.max_health
            self.in_combat_monster = None
            self.status = "ko"
            self._respawn_timer = 1.2

    # ------------------------------------------------------------------
    def tick(self, dt: float):
        # régénération lente de santé en dehors des combats
        if self.status == "creuse":
            self.state.health = min(self.state.max_health, self.state.health + 1.5 * dt)
        if self.status == "ko":
            self._respawn_timer -= dt
            if self._respawn_timer <= 0:
                self.status = "creuse"
            return

        if self.status == "fuite":
            self._respawn_timer -= dt
            if self._respawn_timer <= 0:
                self.status = "creuse"
            return

        if self.status == "combat":
            self._time_since_hit += dt
            interval = self.attack_interval * 1.3
            if self._time_since_hit >= interval:
                self._time_since_hit = 0.0
                self._resolve_combat_tick()
            return

        # -- exploration / minage --
        if self.target_cell is None:
            self.target_cell = self._choose_target()
            self._time_since_hit = 0.0
            if self.target_cell is None:
                return

        row, col = self.target_cell
        block = self.world.get_block(row, col)

        if block.is_empty:
            self.last_cell = (self.state.row, self.state.col)
            self.state.row, self.state.col = row, col
            self.target_cell = None
            return

        if block.contains_monster:
            self._pending_cell = (row, col)
            self._start_combat(block)
            self.target_cell = None
            return

        self._time_since_hit += dt
        variance = 1 + self.rng.uniform(-self.efficiency_variance, self.efficiency_variance)
        interval = self.attack_interval * variance
        if self._time_since_hit >= interval:
            self._time_since_hit = 0.0
            dmg = self.mining_power * (1 + self.ledger.team_bonus(self.team, block.stone_id))
            broke = block.take_damage(dmg)
            if broke:
                if self.joint_grid_callback:
                    self.joint_grid_callback(self.team)
                if self.stones.discover(block.stone_id):
                    self._claim_stone(block.stone_id)
                self.inventory.add_resource(block.stone_id, block.resource_amount)
                self.inventory.gold += block.roll_gold(self.rng) * (1 + self.state.gold_pct)
                if block.contains_artifact:
                    aid, self.artifact_pity = self.artifacts.resolve_drop(
                        block.contains_artifact, block.depth, self.artifact_pity, 0.0, self.rng)
                    self._grant_artifact(aid)
                self._roll_component(block.depth, config.COMPONENT_DROP_CHANCE, hardness=block.hardness)
                self.target_cell = None
                self._try_upgrade()


class _FakePlayer:
    """Adaptateur minimal pour réutiliser combat_system avec une IA."""
    def __init__(self, ai: AIMiner):
        self._ai = ai

    @property
    def mining_power(self):
        return self._ai.mining_power

    @property
    def combat_bonus(self):
        return self._ai.state.combat_damage

    @property
    def alive(self):
        return self._ai.state.health > 0

    @alive.setter
    def alive(self, value):
        pass

    def take_damage(self, amount):
        mitigated = amount * (1 - min(0.7, self._ai.state.damage_reduction))
        self._ai.state.health = max(0, self._ai.state.health - mitigated)


def create_competitors(difficulties=None, ledger=None):
    """
    difficulties : liste de 15 chaînes ("Facile"/"Normal"/"Difficile"), une
    par IA dans l'ordre d'AI_PROFILES. None => Normal pour toutes.
    """
    if difficulties is None:
        difficulties = [config.DEFAULT_DIFFICULTY] * len(AI_PROFILES)
    competitors = []
    for i, p in enumerate(AI_PROFILES):
        diff = difficulties[i] if i < len(difficulties) else config.DEFAULT_DIFFICULTY
        mult = config.DIFFICULTIES.get(diff, config.DIFFICULTIES[config.DEFAULT_DIFFICULTY])
        competitors.append(AIMiner(
            p["name"], AI_COLORS[i], p["team"], p["risk_tolerance"], p["upgrade_readiness"],
            p["artifact_focus"], p["efficiency_variance"], i,
            power_mult=mult["power_mult"], speed_mult=mult["speed_mult"], risk_mult=mult["risk_mult"],
            difficulty=diff, ledger=ledger,
        ))
    return competitors
