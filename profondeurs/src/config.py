"""
Configuration globale du jeu.
Toutes les constantes de gameplay et d'affichage vivent ici.
"""

# --- Fenêtre / rendu ---
FULLSCREEN = True
FPS = 60

TILE_SIZE = 64            # taille d'un bloc à l'écran (px), ajusté au lancement si besoin
GRID_COLS = 17             # largeur de la galerie visible (en blocs) — 8 de chaque côté du centre

RIGHT_PANEL_WIDTH = 380
TOP_BAR_HEIGHT = 84

# Effet de profondeur simulé (pas de vraie 3D) :
DEPTH_SHADE_STEP = 0.02
PARALLAX_LAYERS = 3

# --- Monde ---
MAX_DEPTH = 100_000

# Chaque type de pierre existe sur une PLAGE de profondeur qui chevauche celle
# des voisines (ex. pierre 1 : 0-250 m, pierre 2 : 100-380 m...). À une
# profondeur donnée, plusieurs pierres coexistent, avec une probabilité plus
# forte au centre de leur plage et plus faible sur les bords.
# 10 types au total entre 0 et 1000 m, puis des types plus rapprochés.
STONE_SHALLOW_COUNT = 10       # nombre de pierres qui démarrent avant 1000 m
STONE_SHALLOW_STEP = 100       # une nouvelle pierre démarre tous les 100 m
STONE_SHALLOW_LEN = (250, 350) # longueur de plage (m)
STONE_DEEP_STEP = 60           # au-delà de 1000 m : une nouvelle pierre tous les 60 m
STONE_DEEP_LEN = (200, 320)

BLOCK_HEALTH_SCALE = 18     # points de vie d'un bloc = dureté * ce facteur (minage plus lent qu'au début, mais jouable)

# --- Joueur / minage à la souris ---
PLAYER_START_HEALTH = 100

# --- Niveaux du mineur (XP = somme de toute l'XP gagnée par la pioche et les équipements) ---
PLAYER_MAX_LEVEL = 30
PLAYER_XP_BASE = 120
PLAYER_XP_EXPONENT = 1.55        # XP requise = BASE * niveau ** EXPONENT

LEVEL_EQUIP_UNLOCK = {"tool": 1, "helmet": 2, "armor": 3, "aura": 4, "amulet": 5, "gauntlet": 6}
LEVEL_ARTIFACTS = 7             # avant : les pierres d'artefact ne sont que de la roche
LEVEL_WORKSHOP = 8              # recruter des troupes et attaquer
LEVEL_DAMAGE_BONUS = {9: 0.5, 13: 0.5, 16: 0.5, 19: 0.5, 21: 0.5, 27: 1.0}   # dégâts fixes par coup
TOWER_TRACK_UNLOCK = {"damage": 10, "speed": 10, "range": 10, "hp": 11, "arrows": 12, "supreme": 30}
LEVEL_FREE_ARTIFACT = 14        # offre l'artefact le plus faible non obtenu
LEVEL_COMPANION = 15            # compagnon de mine (prochain patch)
LEVEL_HERO = 20                 # héros (prochain patch)
LEVEL_NEW_ARTIFACT_BONUS = {17: 0.04, 28: 0.04}   # chance permanente d'artefact inédit
LEVEL_XP_MULT = {"armor": (18, 1.5), "amulet": (22, 1.2), "tool": (29, 1.1)}
LEVEL_BLOCK_GOLD = (23, 1.0)    # (niveau, or bonus par roche cassée)
LEVEL_BLOCK_XP = (24, 1.0)      # (niveau, XP bonus par roche cassée)
LEVEL_SELL = 25
LEVEL_BUY = 26
LEVEL_SUPREME = 30

LEVEL_UNLOCK_TEXT = {
    1: "Pioche", 2: "Casque débloqué", 3: "Armure débloquée", 4: "Aura débloquée",
    5: "Amulette débloquée", 6: "Gantelet débloqué",
    7: "Tu peux enfin acquérir des artefacts",
    8: "Atelier fonctionnel : troupes et attaques",
    9: "+0,5 dégât par coup",
    10: "Donjon améliorable (dégâts, cadence, portée)",
    11: "PV du donjon améliorables",
    12: "Flèches par salve améliorables",
    13: "+0,5 dégât par coup",
    14: "Artefact le plus faible non obtenu offert",
    15: "Compagnon de mine débloqué (prochain patch)",
    16: "+0,5 dégât par coup",
    17: "+4% de chance d'artefact inédit (permanent)",
    18: "XP de l'armure x1,5 (permanent)",
    19: "+0,5 dégât par coup",
    20: "Héros débloqué (prochain patch)",
    21: "+0,5 dégât par coup",
    22: "XP de l'amulette x1,2 (permanent)",
    23: "+1 or par roche cassée",
    24: "+1 XP par roche cassée",
    25: "Vente de composants contre de l'or",
    26: "Achat de composants contre de l'or",
    27: "+1 dégât par coup",
    28: "+4% de chance d'artefact inédit (permanent)",
    29: "XP de la pioche x1,1 (permanent)",
    30: "Amélioration suprême du donjon",
}

# --- Outils (pioches) ---
# power = dégâts par coup, speed = coups par seconde en maintenant le clic.
from src.items.pickaxe_specs import PICKAXE_SPECS

# 40 paliers : puissance exponentielle douce, cadence quasi linéaire.
# Les champs "head/head2/handle/glow" restent exposés pour l'interface ; "art" décrit le rendu.
TOOL_TIERS = []
for _i, _spec in enumerate(PICKAXE_SPECS):
    TOOL_TIERS.append({
        "name": _spec["name"], "skin": _spec["skin"],
        "power": round(1.4 * (1.15 ** _i), 1),
        "speed": round(1.55 + 0.13 * _i, 2),
        "head": _spec["mat"][1], "head2": _spec["mat"][0], "handle": _spec["handle"][1],
        "glow": _spec["glow"], "art": _spec,
    })

UPGRADE_BASE_COST = 40
UPGRADE_COST_GROWTH = 1.8
TOOL_UPGRADE_COST_GROWTH = 1.28   # la pioche a 40 paliers : une croissance plus douce

# --- Équipements secondaires (casque, armure, aura) ---
# Comme la pioche : amélioration par palier (achetée en or) ET montée en
# niveau par l'usage (XP), transcendante (1 à 100, conservée à travers les
# achats de palier), qui offre un bonus continu et progressif.
# --- Niveaux de pioche (transcendants : conservés à travers les achats) ---
TOOL_MAX_LEVEL = 100
TOOL_XP_BASE = 200            # XP pour passer du niveau 1 au niveau 2
TOOL_XP_EXPONENT = 1.6        # XP requise = BASE * niveau ** EXPONENT
TOOL_XP_PER_DAMAGE = 0.25     # XP gagnée par point de dégât infligé aux blocs
TOOL_LEVEL_POWER_BONUS = 0.015  # +1,5 % de dégâts par niveau
TOOL_LEVEL_SPEED_BONUS = 0.003  # +0,3 % de cadence par niveau

# --- Niveaux des équipements (casque/armure/aura), même principe que la pioche ---
EQUIP_MAX_LEVEL = 100
EQUIP_XP_BASE = 150
EQUIP_XP_EXPONENT = 1.55
EQUIP_LEVEL_BONUS = 0.015     # +1,5 % du/des bonus par niveau

# Sources d'XP des équipements de survie :
ARMOR_XP_PER_DAMAGE_REDUCED = 1.0   # l'armure s'xp sur les dégâts qu'elle a annulés
HELMET_XP_PER_DAMAGE_TAKEN = 1.0    # le casque s'xp sur les dégâts réellement encaissés (après réduction)
AMULET_XP_PER_HP_REGEN = 4.0        # l'amulette s'xp en régénérant réellement des PV

HELMET_TIERS = [
    {"name": "Casque de cuir",     "bonus": 10, "regen": 0.05, "color": (140, 100, 70),
     "glow": None, "skin": "Un casque de cuir bouilli, cabossé mais solide."},
    {"name": "Casque en fer",      "bonus": 22, "regen": 0.10, "color": (175, 178, 188),
     "glow": None, "skin": "Renforcé de bandes de fer rivetées."},
    {"name": "Casque runique",     "bonus": 38, "regen": 0.18, "color": (120, 160, 255),
     "glow": (120, 160, 255), "skin": "Des symboles protecteurs y sont gravés."},
    {"name": "Heaume abyssal",     "bonus": 60, "regen": 0.30, "color": (170, 90, 240),
     "glow": (170, 90, 255), "skin": "Il semble regarder dans le noir à ta place."},
    {"name": "Couronne stellaire", "bonus": 90, "regen": 0.48, "color": (255, 230, 140),
     "glow": (255, 245, 180), "skin": "Un fragment d'étoile ceint ton front."},
]

ARMOR_TIERS = [
    {"name": "Veste matelassée", "bonus": 0.04, "color": (110, 90, 70),
     "glow": None, "skin": "Rembourrée de chiffons et de cuir tanné."},
    {"name": "Cotte de mailles", "bonus": 0.09, "color": (170, 172, 182),
     "glow": None, "skin": "Des anneaux de fer serrés, lourds mais fiables."},
    {"name": "Plates runiques",  "bonus": 0.15, "color": (110, 150, 240),
     "glow": (110, 150, 240), "skin": "Chaque plaque absorbe le choc en vibrant."},
    {"name": "Carapace abyssale", "bonus": 0.23, "color": (160, 80, 230),
     "glow": (160, 80, 230), "skin": "Une carapace organique venue des failles profondes."},
    {"name": "Égide stellaire",  "bonus": 0.33, "color": (250, 225, 130),
     "glow": (255, 240, 170), "skin": "Elle dévie les coups comme la lumière dévie une étoile."},
]

AURA_TIERS = [
    {"name": "Étincelle timide",  "bonus": 0.05, "color": (140, 220, 140),
     "glow": (140, 220, 140), "skin": "Une faible lueur verte flotte autour de toi."},
    {"name": "Aura cuivrée",      "bonus": 0.11, "color": (220, 150, 90),
     "glow": (220, 150, 90), "skin": "Elle crépite doucement à chaque coup de pioche."},
    {"name": "Aura runique",      "bonus": 0.18, "color": (120, 160, 255),
     "glow": (120, 160, 255), "skin": "Des runes tournoient lentement à tes côtés."},
    {"name": "Aura abyssale",     "bonus": 0.27, "color": (170, 90, 240),
     "glow": (170, 90, 255), "skin": "Une brume violette semble te suivre avec intention."},
    {"name": "Aura stellaire",    "bonus": 0.40, "color": (255, 230, 140),
     "glow": (255, 245, 180), "skin": "Des particules dorées orbitent autour de toi."},
]

AMULET_TIERS = [
    {"name": "Pendentif fêlé",       "regen": 0.10, "color": (150, 180, 150),
     "glow": None, "skin": "Un simple caillou percé, tiède au toucher."},
    {"name": "Amulette de sève",     "regen": 0.20, "color": (110, 200, 130),
     "glow": (110, 200, 130), "skin": "Une résine ambrée y palpite doucement."},
    {"name": "Talisman de vie",      "regen": 0.34, "color": (90, 220, 160),
     "glow": (90, 220, 160), "skin": "Il bat presque comme un second cœur."},
    {"name": "Cœur de source",       "regen": 0.52, "color": (80, 230, 220),
     "glow": (80, 230, 220), "skin": "Une eau claire semble couler sous sa surface."},
    {"name": "Relique de renaissance", "regen": 0.80, "color": (255, 240, 200),
     "glow": (255, 250, 220), "skin": "Chaque battement repousse un peu plus la mort."},
]

GAUNTLET_TIERS = [
    {"name": "Brassard de fortune",   "bonus": 2,  "color": (150, 120, 90),
     "glow": None, "skin": "Des lanières de cuir autour du poignet : mieux que rien."},
    {"name": "Gantelet clouté",       "bonus": 5,  "color": (175, 178, 188),
     "glow": None, "skin": "Hérissé de clous, il laisse des marques."},
    {"name": "Gantelet runique",      "bonus": 10, "color": (120, 160, 255),
     "glow": (120, 160, 255), "skin": "Chaque coup réveille une rune de force."},
    {"name": "Poing abyssal",         "bonus": 18, "color": (170, 90, 240),
     "glow": (170, 90, 255), "skin": "Il frappe un peu avant toi, comme s'il avait faim."},
    {"name": "Main stellaire",        "bonus": 30, "color": (255, 230, 140),
     "glow": (255, 245, 180), "skin": "Une main d'étoile : les monstres s'en souviennent."},
]
# Le gantelet ne gagne de l'XP QUE en combat (par dégât réellement infligé à un monstre).
GAUNTLET_XP_PER_DAMAGE = 1.5
# La pioche gagne aussi de l'XP en combat (en plus du minage).
TOOL_XP_PER_COMBAT_DAMAGE = 0.3

# --- Artefacts : protection contre la malchance ---
# Chaque fois qu'on casse une pierre d'artefact et qu'on obtient un DOUBLON,
# la chance que le prochain artefact soit INÉDIT augmente de ce pas (x chance d'artefact).
ARTIFACT_PITY_STEP = 0.08
ARTIFACT_PITY_MAX = 0.9

# Pierres d'artefact : 25x plus dures, 2x plus rares
ARTIFACT_BLOCK_HARDNESS_MULT = 25
ARTIFACT_RARITY_DIVISOR = 2

# Remontée limitée : on ne peut pas dépasser MAX_ASCENT blocs au-dessus de la profondeur max atteinte
MAX_ASCENT = 10

# --- Guerre entre factions : bataille en temps réel (troupes contre troupes + donjon d'archer) ---
WAR_MAX_TIME = 90.0           # durée max d'une bataille (s) ; au-delà, le défenseur tient
WAR_DEFENSE_FACTOR = 4        # dégâts reçus x 100/(100 + FACTOR x défense de l'unité)
TOWER_HP = 700                # points de vie du donjon d'archer
TOWER_DEFENSE = 10
WAR_LOOT_RATIO = 0.50         # part de l'or du vaincu volée par l'attaquant vainqueur
# (l'attaquant vainqueur fait aussi perdre un palier à un équipement tiré au hasard chez le vaincu)
WAR_ATTACK_COOLDOWN = 45.0    # secondes entre deux attaques d'un même mineur
WAR_TARGET_SHIELD = 110.0     # secondes de protection d'une cible après avoir été attaquée
WAR_AI_INTERVAL = 30.0        # les IA envisagent une attaque toutes les X secondes
WAR_WIN_SCORE = 25            # points de score par victoire (attaque réussie ou défense réussie)

# --- Valeur des blocs : or et XP proportionnels à la difficulté (points de vie du bloc) ---
GOLD_PER_BLOCK_HP = 0.18        # or moyen = HP de base du bloc x ce facteur (les blocs d'artefact ne donnent pas d'or)
BLOCK_VALUE_RANDOM = (0.7, 1.3)  # petit aléa autour de la moyenne (moyenne = 1)
XP_BLOCK_RANDOM = (0.8, 1.2)

# --- Pierres : nommées par le premier qui les trouve ---
STONE_FACTION_BONUS = 0.10       # +10 % de vitesse de cassage sur cette pierre pour toute sa faction
STONE_NO_BONUS_ID = "s0"         # la toute première pierre ne donne pas de bonus

# --- Mort contre un monstre : pénalités ---
DEATH_GOLD_LOSS = 0.40          # part de l'or perdue
# (l'XP en cours du niveau actuel de la pioche et de tous les équipements est aussi perdue)

# Les niveaux d'XP des équipements (casque, armure, aura, amulette, gantelet) donnent un peu de puissance de minage
ITEM_LEVEL_MINING_BONUS = 0.0003   # par niveau et par équipement (+0,03 %)

# --- Composants (craft de troupes) ---
COMPONENT_DROP_CHANCE = 0.045          # par bloc cassé
COMPONENT_MONSTER_DROP_CHANCE = 0.70   # par monstre vaincu (beaucoup plus qu'en minant)
COMPONENT_MONSTER_BONUS_CHANCE = 0.30  # chance d'un second composant sur le même monstre

# --- Sauvegarde ---
AUTOSAVE_INTERVAL = 20.0   # secondes

# --- Raretés ---
RARITIES = ["Commune", "Peu commune", "Rare", "Épique", "Légendaire", "Mythique"]
RARITY_COLORS = {
    "Commune":     (190, 190, 195),
    "Peu commune": (110, 210, 130),
    "Rare":        (100, 150, 240),
    "Épique":      (180, 100, 230),
    "Légendaire":  (245, 185, 65),
    "Mythique":    (235, 70, 70),
}

# --- Combat ---
MONSTER_SPAWN_CHANCE = 0.04
BOSS_DEPTH_INTERVAL = 250

# arène de combat : le monstre se déplace, il faut cliquer dessus
COMBAT_ARENA_W = 520
COMBAT_ARENA_H = 220
MONSTER_BASE_SPEED = 300         # px/s
MONSTER_HIT_COOLDOWN = 0.12      # anti spam-clic côté joueur

# --- Difficulté des IA concurrentes ---
DIFFICULTIES = {
    "Facile":    {"power_mult": 0.7, "speed_mult": 0.8, "risk_mult": 0.75},
    "Normal":    {"power_mult": 1.0, "speed_mult": 1.0, "risk_mult": 1.0},
    "Difficile": {"power_mult": 1.35, "speed_mult": 1.25, "risk_mult": 1.25},
}
DEFAULT_DIFFICULTY = "Normal"

# --- Équipes ---
# 4 équipes de 4 : le joueur + 3 IA dans l'équipe 0, et 3 équipes 100% IA.
# Soit 15 IA au total. Chaque IA a sa propre difficulté, choisie individuellement.
TEAM_NAMES = ["Ta compagnie", "Les Marteaux d'Onyx", "La Confrérie du Puits", "Les Foreurs Écarlates"]
TEAM_COLORS = [(255, 214, 150), (150, 200, 230), (200, 140, 230), (230, 130, 110)]

# --- Historique / graphique de progression ---
HISTORY_INTERVAL = 4.0     # secondes entre deux points enregistrés
HISTORY_MAX_POINTS = 300

SAVE_PATH = "data/save.json"
