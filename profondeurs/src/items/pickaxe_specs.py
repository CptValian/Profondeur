"""
Description artistique des 100 pioches (aucune dépendance : lue par config.py).

mat    = (reflet, base, ombre, arête)   couleurs de la lame
handle = (clair, base, sombre)          couleurs du manche
head   = forme de la tête : flint | wood | stone | adze | hammer | pick | curved | winged | crystal
deco   = ornements dessinés par pickaxe_art.py
fx     = effet animé autour de la tête : sparkle | embers | frost | bolt | void | stars | rainbow
"""


def _p(name, skin, mat, handle, hstyle, head, deco=(), glow=None, gem=None, fx=None, **geo):
    d = dict(name=name, skin=skin, mat=mat, handle=handle, hstyle=hstyle, head=head,
             deco=list(deco), glow=glow, gem=gem, fx=fx)
    d.update(geo)
    return d


WOOD = ((176, 132, 88), (126, 88, 52), (74, 48, 28))
DKWOOD = ((120, 88, 62), (84, 58, 38), (44, 28, 18))
LEATHER = ((120, 86, 60), (84, 56, 38), (44, 28, 20))
BONE = ((250, 244, 224), (222, 210, 180), (160, 146, 118))
DKMETAL = ((110, 112, 128), (70, 72, 86), (34, 36, 48))
SILVER = ((250, 252, 255), (200, 206, 222), (130, 138, 164))
GOLDH = ((255, 240, 160), (232, 186, 66), (140, 96, 22))

ROTTEN_WOOD = ((140, 110, 80), (100, 72, 46), (56, 36, 20))
PALE_WOOD = ((200, 180, 140), (150, 130, 95), (90, 75, 50))
STRAW_ROPE = ((210, 190, 130), (160, 140, 85), (100, 85, 45))
RUSTY_METAL = ((180, 110, 80), (130, 70, 45), (75, 38, 22))

PICKAXE_SPECS = [
    # --- Paliers extrêmement faibles (1 à 13) ---
    _p("Bâton de bois vermoulu", "Un simple bâton creux trouvé par terre. Il menace de casser à la moindre pierre.",
       ((150, 120, 90), (100, 72, 46), (56, 36, 20), (170, 140, 105)), ROTTEN_WOOD, "wood", "wood", ["crack"], span=100, thick=38),
    _p("Tige de roseau séchée", "Une tige desséchée et légère, presque pliée en deux.",
       ((160, 140, 90), (110, 90, 50), (60, 45, 25), (180, 150, 110)), PALE_WOOD, "wood", "wood", ["crack"], span=105, thick=40),
    _p("Branche fourchue effilochée", "Une branche tordue en fourche, à peine aiguisée contre un caillou.",
       ((170, 140, 100), (118, 88, 52), (68, 46, 26), (190, 155, 115)), ROTTEN_WOOD, "wood", "wood", ["crack"], span=110, thick=42),
    _p("Pieu de bois calciné", "Le bout a été durci au feu, mais c'est surtout du charbon effritable.",
       ((110, 90, 80), (60, 48, 42), (32, 24, 20), (140, 120, 110)), DKWOOD, "wood", "flint", ["crack"]),
    _p("Tige de bambou fendu", "Une tige de bambou effilée qui plie affreusement à chaque impact.",
       ((180, 200, 130), (130, 150, 85), (75, 95, 45), (200, 220, 150)), PALE_WOOD, "wood", "flint", ["rope"]),
    _p("Branche de sapin durcie", "Une branche noueuse et poisseuse de résine.",
       ((140, 130, 90), (90, 80, 50), (50, 40, 25), (160, 145, 105)), WOOD, "wood", "wood", ["rope", "crack"]),
    _p("Silex brut mal ficelé", "Un caillou coupant attaché à un bout de bois avec de l'herbe séchée.",
       ((160, 150, 140), (105, 98, 90), (58, 52, 48), (185, 175, 165)), STRAW_ROPE, "wood", "flint", ["rope"], span=130),
    _p("Grattoir de schiste effrité", "Un morceau de schiste plat et coupant, sujet aux pannes.",
       ((150, 145, 140), (100, 95, 90), (55, 50, 48), (170, 165, 160)), STRAW_ROPE, "wood", "stone", ["crack"]),
    _p("Piquet d'enclos pointu", "Un piquet arraché à une barrière, à peine taillé en pointe.",
       ((185, 148, 105), (135, 96, 60), (80, 52, 30), (205, 168, 125)), WOOD, "wood", "wood", ["rope", "crack"], thick=48),
    _p("Clou rouillé sur manche", "Un gros clou tordu enfiché dans une branchette.",
       ((175, 105, 75), (125, 65, 40), (70, 34, 18), (195, 125, 90)), RUSTY_METAL, "wood", "flint", ["rope", "crack"]),
    _p("Os de rongeur ébréché", "Un petit os pointu, fragile et un peu dégoûtant.",
       ((240, 230, 205), (200, 185, 155), (140, 128, 100), (250, 242, 220)), BONE, "bone", "pick", ["crack"], span=140, thick=46),
    _p("Cerclage de tonneau plié", "Un morceau de fer de tonneau plié en deux, souple et bancal.",
       ((165, 155, 150), (110, 102, 98), (62, 56, 52), (185, 175, 170)), DKWOOD, "wrap", "adze", ["rope"]),
    _p("Grattoir en pierre friable", "Une pierre tendre qui s'effrite presque aussi vite que la roche minée.",
       ((180, 175, 170), (128, 122, 118), (75, 70, 68), (200, 195, 190)), WOOD, "wood", "stone", ["speckle", "crack"]),

    # --- Bois, os et pierres travaillées ---
    _p("Éclat de silex fendu", "Un simple éclat de silex lié à un bout de bois fendu.",
       ((176, 166, 154), (118, 110, 102), (66, 60, 58), (206, 196, 180)), WOOD, "wood", "flint", ["rope", "crack"]),
    _p("Pioche de bois fissuré", "Le manche se fissure un peu plus à chaque coup, mais tient encore.",
       ((198, 156, 112), (146, 104, 66), (90, 60, 36), (220, 182, 138)), WOOD, "wood", "wood", ["rope", "crack"]),
    _p("Pioche de bois cerclé", "De solides cerclages en cuir maintiennent la tête de bois bien en place.",
       ((200, 160, 120), (150, 110, 70), (90, 60, 35), (220, 180, 140)), LEATHER, "wood", "wood", ["rope", "rivets"]),
    _p("Pioche de bois reinforced", "Des liens de corde et des rivets renforcent les fissures.",
       ((204, 162, 116), (152, 110, 70), (94, 64, 38), (226, 188, 144)), WOOD, "wood", "wood", ["rope", "rivets"], thick=60),
    _p("Pioche d'os poli", "Taillée dans l'os d'une créature des galeries, lisse et froide.",
       ((255, 252, 240), (226, 214, 184), (164, 150, 122), (255, 255, 248)), BONE, "bone", "pick", ["engrave"], thick=64),
    _p("Pioche d'os sculpté", "Incrustée de petites runes primitives taillées à la main.",
       ((250, 245, 230), (220, 210, 180), (160, 145, 120), (255, 250, 240)), BONE, "bone", "pick", ["engrave", "rope"], thick=64),
    _p("Pioche à tête de pierre", "Une tête de pierre taillée, enfin un peu solide.",
       ((200, 200, 196), (146, 146, 144), (92, 92, 96), (222, 222, 218)), WOOD, "wood", "stone", ["rope", "speckle"]),
    _p("Pioche de grès massif", "Un bloc de grès très dense taillé avec soin.",
       ((210, 190, 160), (160, 140, 110), (100, 80, 60), (230, 210, 180)), WOOD, "wood", "hammer", ["speckle"]),
    _p("Pioche de pierre taillée", "Un tranchant de pierre éclatée, net comme du verre.",
       ((206, 208, 214), (150, 154, 164), (88, 92, 104), (232, 234, 240)), DKWOOD, "wood", "adze", ["rope", "speckle"]),

    # --- Paliers Cuivre et Bronze ---
    _p("Pioche de cuivre", "Une tête de cuivre brut, encore tendre.",
       ((255, 196, 138), (210, 124, 68), (134, 66, 36), (255, 220, 170)), WOOD, "wood", "pick", ["rivets"]),
    _p("Pioche de cuivre poli", "Brillante et polie, le cuivre glisse mieux contre la roche.",
       ((255, 210, 150), (220, 135, 75), (140, 75, 40), (255, 230, 180)), WOOD, "wood", "pick", ["rivets", "engrave"]),
    _p("Pioche de cuivre trempé", "Le cuivre a été trempé pour durcir le tranchant.",
       ((255, 206, 128), (228, 142, 72), (146, 70, 36), (255, 228, 176)), WOOD, "wood", "pick", ["rivets", "engrave"], span=195),
    _p("Pioche de laiton martelé", "Alliage éclatant aux reflets dorés chauds.",
       ((240, 210, 120), (190, 150, 60), (120, 90, 30), (250, 225, 140)), WOOD, "wood", "hammer", ["rivets"]),
    _p("Pioche de bronze", "Un alliage de bronze : plus lourd, plus résistant.",
       ((255, 222, 128), (208, 152, 62), (132, 90, 32), (255, 238, 176)), WOOD, "wood", "hammer", ["rivets"]),
    _p("Pioche de bronze gravé", "Des motifs sont gravés sur toute la tête de bronze.",
       ((255, 230, 140), (216, 160, 68), (136, 92, 34), (255, 242, 184)), DKWOOD, "wrap", "pick", ["engrave", "inlay"], span=200, droop=70),

    # --- Paliers Fer et Acier ---
    _p("Pioche de fer", "Une tête de fer massif, simple et efficace.",
       ((228, 231, 238), (162, 168, 180), (94, 100, 114), (248, 250, 254)), DKWOOD, "wrap", "pick", ["rivets"]),
    _p("Pioche de fer forgé", "Le fer a été martelé : on voit encore les coups du forgeron.",
       ((222, 226, 236), (150, 158, 174), (84, 92, 108), (246, 248, 255)), DKWOOD, "wrap", "adze", ["rivets", "engrave"]),
    _p("Pioche de fer trempé au charbon", "Noircie au charbon de bois pour une solidité accrue.",
       ((180, 185, 195), (120, 125, 135), (60, 65, 75), (200, 205, 215)), DKMETAL, "wrap", "pick", ["rivets"]),
    _p("Pioche d'acier", "De l'acier trempé, froid et implacable.",
       ((246, 249, 255), (188, 198, 214), (106, 116, 140), (255, 255, 255)), LEATHER, "wrap", "curved", []),
    _p("Pioche d'acier poli", "L'acier poli renvoie un éclat presque aveuglant.",
       ((255, 255, 255), (214, 222, 236), (130, 142, 168), (255, 255, 255)), LEATHER, "wrap", "curved", ["engrave"], span=215),
    _p("Pioche d'acier noir", "Un acier sombre aux reflets ténébreux et tranchants.",
       ((140, 145, 160), (80, 85, 100), (35, 40, 50), (170, 175, 190)), DKMETAL, "wrap", "curved", ["engrave"], span=215),
    _p("Pioche d'acier damas", "Des ondes sombres courent dans l'acier replié mille fois.",
       ((216, 222, 234), (150, 158, 178), (68, 74, 94), (240, 244, 252)), DKMETAL, "wrap", "curved", ["damascus"], span=215, thick=68),

    # --- Paliers Métaux Nobles et Gemmes ---
    _p("Pioche d'argent", "L'argent orne le manche d'un reflet froid.",
       ((255, 255, 255), (222, 226, 238), (152, 158, 184), (255, 255, 255)), SILVER, "metal", "curved", ["inlay"], glow=(170, 190, 255), fx="sparkle"),
    _p("Pioche d'argent ouvragé", "Un orfèvre y a sculpté des ailerons et serti un saphir.",
       ((255, 255, 255), (226, 230, 242), (156, 164, 192), (255, 255, 255)), SILVER, "metal", "winged", ["inlay"], glow=(170, 200, 255), gem=(70, 130, 240), fx="sparkle"),
    _p("Pioche de platine étincelant", "Le platine résiste à l'usure de la roche la plus dure.",
       ((240, 245, 255), (200, 210, 225), (140, 150, 170), (255, 255, 255)), SILVER, "metal", "winged", ["inlay"], glow=(200, 220, 255), fx="sparkle"),
    _p("Pioche d'or royal", "Une pioche de roi : le métal est trop beau pour creuser.",
       ((255, 246, 176), (242, 198, 72), (162, 114, 26), (255, 252, 210)), GOLDH, "gold", "winged", ["spikes", "inlay"], glow=(255, 215, 100), gem=(230, 40, 70), fx="sparkle"),
    _p("Pioche de mithril", "Le mithril rend la pioche étonnamment légère.",
       ((232, 248, 255), (156, 206, 244), (84, 124, 190), (255, 255, 255)), SILVER, "metal", "curved", ["engrave", "inlay"], glow=(150, 200, 255), fx="sparkle", span=225, hook=22),
    _p("Pioche d'adamant", "Un métal vert sombre qui n'a jamais été rayé.",
       ((160, 238, 210), (62, 164, 134), (20, 92, 84), (198, 255, 236)), DKMETAL, "metal", "winged", ["engrave"], glow=(80, 230, 190), fx="sparkle"),
    _p("Pioche de cobalt profond", "Un bleu métallique intense vibrant sous l'effort.",
       ((120, 160, 240), (50, 90, 180), (15, 40, 110), (160, 190, 255)), DKMETAL, "metal", "winged", ["engrave"], glow=(60, 110, 230), fx="sparkle"),
    _p("Pioche runique", "Des runes bleutées pulsent le long de la tête.",
       ((176, 206, 255), (104, 144, 238), (52, 72, 164), (214, 232, 255)), ((104, 96, 160), (66, 58, 112), (34, 28, 64)), "wrap", "curved", ["runes"], glow=(120, 160, 255), fx="sparkle"),
    _p("Pioche runique éveillée", "Les runes se sont éveillées et chuchotent à chaque coup.",
       ((196, 222, 255), (124, 164, 250), (64, 88, 184), (230, 242, 255)), ((120, 112, 180), (78, 70, 128), (40, 34, 74)), "metal", "winged", ["runes", "fins"], glow=(130, 175, 255), gem=(150, 210, 255), fx="sparkle"),

    # --- Paliers Gemmes et Minéraux d'exception ---
    _p("Pioche de jade étincelant", "Un vert translucide apaisant et affûté.",
       ((180, 250, 190), (60, 190, 100), (15, 100, 50), (210, 255, 220)), GOLDH, "gold", "crystal", [], glow=(80, 240, 120), gem=(50, 210, 100), fx="sparkle"),
    _p("Pioche d'émeraude", "Une émeraude brute taillée en lame, d'un vert profond.",
       ((196, 255, 208), (72, 204, 122), (20, 112, 72), (226, 255, 236)), GOLDH, "gold", "crystal", [], glow=(90, 255, 150), gem=(60, 230, 130), fx="sparkle"),
    _p("Pioche de topaze embrasée", "Une lueur ambrée chaleureuse irradiant la roche.",
       ((255, 210, 140), (230, 150, 50), (140, 80, 20), (255, 230, 170)), GOLDH, "gold", "crystal", [], glow=(255, 170, 60), gem=(255, 160, 40), fx="sparkle"),
    _p("Pioche de rubis", "Le cœur du rubis bat comme une braise.",
       ((255, 176, 176), (222, 52, 72), (122, 16, 42), (255, 214, 214)), GOLDH, "gold", "crystal", [], glow=(255, 80, 100), gem=(255, 70, 90), fx="sparkle"),
    _p("Pioche de saphir", "Un bleu si pur qu'on y distingue le fond de la mer.",
       ((176, 214, 255), (54, 114, 232), (16, 52, 144), (214, 232, 255)), SILVER, "metal", "crystal", [], glow=(90, 150, 255), gem=(80, 150, 255), fx="sparkle"),
    _p("Pioche d'améthyste", "Les facettes violettes dévient la lumière.",
       ((234, 194, 255), (164, 84, 224), (82, 32, 134), (246, 220, 255)), SILVER, "metal", "crystal", ["stars"], glow=(190, 110, 255), gem=(200, 120, 255), fx="sparkle"),
    _p("Pioche d'obsidienne tranchante", "Un verre volcanique noir acéré comme un rasoir.",
       ((100, 90, 110), (40, 35, 50), (15, 10, 20), (150, 140, 160)), DKMETAL, "metal", "crystal", ["spikes"], glow=(120, 90, 150), fx="sparkle"),

    # --- Paliers Élémentaires et Forces de la Nature ---
    _p("Pioche de flamme", "La tête incandescente crépite, suintant de lave figée.",
       ((255, 232, 130), (255, 134, 44), (156, 44, 16), (255, 244, 176)), ((92, 52, 40), (58, 32, 26), (28, 16, 14)), "wrap", "winged", ["flames"], glow=(255, 140, 50), gem=(255, 190, 60), fx="embers"),
    _p("Pioche de magma", "La roche noire se fend sur un cœur de lave vivante.",
       ((120, 84, 76), (66, 42, 38), (30, 18, 18), (255, 130, 50)), ((70, 44, 36), (44, 28, 24), (22, 14, 12)), "wrap", "hammer", ["magma", "flames"], glow=(255, 100, 30), fx="embers", thick=84),
    _p("Pioche de givre", "Un froid mordant émane de la tête cristalline.",
       ((236, 252, 255), (156, 218, 246), (72, 142, 204), (255, 255, 255)), SILVER, "metal", "crystal", ["ice"], glow=(160, 225, 255), fx="frost"),
    _p("Pioche du blizzard", "Des éclats de glace tourbillonnent en permanence autour d'elle.",
       ((226, 244, 255), (118, 176, 240), (54, 96, 176), (255, 255, 255)), ((150, 176, 210), (96, 124, 170), (54, 74, 116)), "metal", "winged", ["ice", "stars"], glow=(150, 210, 255), gem=(210, 240, 255), fx="frost"),
    _p("Pioche de glace éternelle", "Un gel si intense qu'il cryogénise la roche sur l'impact.",
       ((210, 245, 255), (100, 190, 245), (40, 110, 180), (240, 255, 255)), SILVER, "metal", "crystal", ["ice", "stars"], glow=(120, 220, 255), fx="frost"),
    _p("Pioche de foudre", "Des arcs électriques courent sur toute la longueur du manche.",
       ((255, 255, 206), (250, 216, 62), (162, 122, 12), (255, 255, 236)), ((70, 60, 40), (44, 38, 26), (22, 18, 12)), "metal", "curved", ["bolt"], glow=(255, 240, 110), fx="bolt", span=215),
    _p("Pioche de tempête", "Elle gronde avant chaque coup, comme un ciel d'orage.",
       ((206, 216, 240), (112, 128, 174), (50, 58, 104), (232, 238, 255)), DKMETAL, "metal", "winged", ["bolt", "fins"], glow=(170, 190, 255), gem=(255, 245, 140), fx="bolt"),
    _p("Pioche d'énergie arcanique", "Un flux de pure magie canalisé dans une lame d'éther.",
       ((220, 180, 255), (140, 80, 230), (60, 20, 140), (240, 210, 255)), ((80, 50, 130), (45, 25, 80), (20, 10, 40)), "metal", "winged", ["runes", "vortex"], glow=(180, 120, 255), fx="sparkle"),

    # --- Paliers Abysses, Chaos et Ténèbres ---
    _p("Pioche de cristal d'onyx", "Un cristal noir mystérieux résonnant avec les profondeurs.",
       ((120, 110, 130), (50, 45, 60), (20, 15, 25), (160, 150, 170)), DKMETAL, "metal", "crystal", ["spikes"], glow=(110, 80, 140), fx="void"),
    _p("Pioche abyssale", "Forgée dans un métal venu des abysses, elle chuchote.",
       ((196, 136, 255), (112, 52, 194), (46, 16, 94), (226, 190, 255)), ((50, 34, 74), (30, 18, 46), (14, 8, 24)), "wrap", "winged", ["spikes", "eye"], glow=(160, 90, 255), fx="void"),
    _p("Pioche démoniaque", "Des visages hurlants semblent se former dans le métal.",
       ((210, 70, 100), (124, 22, 54), (52, 6, 28), (255, 120, 130)), ((60, 22, 34), (36, 12, 20), (18, 6, 10)), "wrap", "winged", ["spikes", "eye", "fins"], glow=(255, 60, 90), fx="void"),
    _p("Pioche du chaos", "Elle absorbe la lumière autour d'elle, indifférente à tout.",
       ((150, 88, 210), (74, 22, 116), (22, 6, 44), (236, 160, 255)), ((40, 24, 60), (22, 12, 36), (10, 6, 18)), "metal", "winged", ["vortex", "eye", "spikes"], glow=(170, 90, 255), fx="void"),
    _p("Pioche du cataclysme", "Elle ébranle les fondations des cavernes à chaque frappe.",
       ((230, 100, 80), (140, 40, 30), (60, 15, 10), (255, 140, 120)), ((50, 20, 15), (30, 10, 8), (15, 5, 4)), "wrap", "hammer", ["magma", "vortex"], glow=(240, 80, 50), fx="embers"),

    # --- Paliers Astronomiques et Stellaires ---
    _p("Pioche stellaire", "Des éclats d'étoile morte tournoient autour de la tête.",
       ((255, 252, 210), (246, 218, 124), (172, 132, 44), (255, 255, 240)), GOLDH, "gold", "winged", ["stars", "inlay"], glow=(255, 245, 190), gem=(255, 255, 220), fx="stars"),
    _p("Pioche nébuleuse", "Une galaxie entière tourne lentement dans la lame.",
       ((236, 170, 255), (110, 80, 214), (36, 28, 112), (255, 220, 255)), ((60, 50, 120), (36, 28, 82), (18, 14, 44)), "metal", "crystal", ["nebula", "stars"], glow=(170, 130, 255), gem=(255, 190, 255), fx="stars"),
    _p("Pioche céleste", "Deux ailes de lumière pure jaillissent du manche.",
       ((255, 255, 255), (238, 242, 255), (176, 186, 226), (255, 255, 255)), ((255, 255, 255), (236, 240, 252), (190, 198, 230)), "white", "winged", ["feathers", "inlay"], glow=(255, 250, 220), gem=(255, 240, 180), fx="sparkle"),
    _p("Pioche solaire", "Elle porte en elle un petit soleil qui ne se couche jamais.",
       ((255, 252, 196), (255, 208, 76), (226, 126, 24), (255, 255, 230)), GOLDH, "gold", "winged", ["corona", "flames", "inlay"], glow=(255, 224, 112), gem=(255, 250, 200), fx="embers"),
    _p("Pioche de plasma solaire", "Une chaleur solaire condensée capable de fondre le granit.",
       ((255, 230, 150), (255, 160, 30), (190, 80, 10), (255, 245, 190)), GOLDH, "gold", "winged", ["corona", "flames"], glow=(255, 180, 50), fx="embers"),
    _p("Pioche divine", "Elle n'existe qu'à moitié dans notre plan de réalité, et pourtant elle brille de tout son être.",
       ((255, 255, 255), (252, 252, 255), (206, 210, 240), (255, 255, 255)), ((255, 255, 255), (250, 246, 232), (218, 208, 190)), "white", "winged", ["feathers", "halo", "corona", "inlay"], glow=(255, 255, 255), gem=(255, 255, 255), fx="rainbow", span=215),
    _p("Pioche d'aurore", "Des rubans verts et violets ondulent dans le cristal, comme un ciel polaire figé.",
       ((206, 255, 236), (96, 224, 196), (44, 120, 176), (240, 255, 250)), ((190, 214, 230), (130, 160, 190), (70, 96, 130)), "metal", "crystal", ["aurora", "stars"], glow=(120, 255, 220), gem=(170, 255, 236), fx="sparkle"),

    # --- Paliers Mythiques et Légendaires ---
    _p("Pioche de l'éclipse", "Un soleil noir couronné d'or : quand elle frappe, le jour recule.",
       ((120, 108, 140), (44, 36, 60), (14, 10, 24), (255, 222, 124)), ((70, 60, 90), (36, 28, 54), (16, 12, 28)), "metal", "winged", ["eclipse", "inlay"], glow=(255, 200, 90), fx="stars", inlay=(255, 214, 110)),
    _p("Pioche draconique", "Forgée dans une écaille de dragon : elle garde la chaleur de son feu.",
       ((255, 196, 126), (214, 72, 40), (112, 22, 22), (255, 224, 156)), ((96, 36, 30), (60, 20, 18), (30, 10, 10)), "wrap", "winged", ["horns", "scales", "eye"], glow=(255, 100, 40), fx="embers"),
    _p("Pioche du wyrm céleste", "Ailes draconiques dorées pulsant de magies ancestrales.",
       ((255, 220, 140), (220, 130, 30), (130, 60, 10), (255, 240, 180)), GOLDH, "gold", "winged", ["horns", "feathers"], glow=(255, 180, 70), fx="sparkle"),
    _p("Pioche du phénix", "Ses ailes de flammes se consument sans jamais s'éteindre.",
       ((255, 244, 160), (255, 154, 44), (196, 54, 22), (255, 252, 206)), GOLDH, "gold", "curved", ["firewings", "flames"], glow=(255, 160, 60), gem=(255, 214, 96), fx="embers", span=220),
    _p("Pioche du titan de pierre", "Une masse titanique pulvérisant le sol à des lieues à la ronde.",
       ((180, 170, 160), (110, 100, 90), (50, 45, 40), (210, 200, 190)), WOOD, "wood", "hammer", ["spikes"], glow=(160, 150, 140), thick=90),
    _p("Pioche du temps", "Ses rouages tournent à l'envers quand tu hésites.",
       ((246, 226, 178), (196, 154, 84), (112, 78, 36), (255, 242, 206)), GOLDH, "gold", "curved", ["gears", "engrave", "inlay"], glow=(255, 226, 150), gem=(120, 232, 255), fx="sparkle"),
    _p("Pioche du Léviathan", "Elle sent l'abîme : des tentacules luisantes s'enroulent autour de la tête.",
       ((160, 255, 242), (34, 156, 176), (8, 52, 94), (206, 255, 255)), ((40, 74, 90), (24, 46, 60), (10, 22, 32)), "wrap", "winged", ["tendrils", "scales"], glow=(60, 224, 232), gem=(130, 255, 242), fx="bubbles"),
    _p("Pioche de l'éternité", "La durée absolue cristallisée en une pointe indestructible.",
       ((240, 230, 255), (180, 150, 240), (100, 70, 170), (255, 245, 255)), SILVER, "metal", "crystal", ["stars", "infinity"], glow=(200, 160, 255), fx="sparkle"),
    _p("Pioche de l'infini", "Un ruban de lumière sans début ni fin tourne autour d'une lame de nébuleuse.",
       ((242, 204, 255), (124, 84, 224), (32, 22, 112), (255, 232, 255)), ((70, 58, 130), (40, 32, 92), (20, 16, 52)), "metal", "crystal", ["nebula", "infinity", "stars"], glow=(190, 150, 255), gem=(255, 200, 255), fx="stars"),
    _p("Pioche primordiale", "Feu, eau, terre et vent : les quatre éléments dorment dans sa lame.",
       ((236, 244, 236), (156, 176, 156), (74, 94, 74), (252, 255, 252)), ((220, 206, 170), (170, 150, 104), (96, 78, 48)), "gold", "winged", ["elements", "inlay"], glow=(255, 255, 240), gem=(255, 255, 255), fx="sparkle"),
    _p("Pioche du créateur", "Des anneaux d'astrolabe veillent sur chaque coup : rien n'est laissé au hasard.",
       ((255, 253, 238), (252, 232, 166), (204, 162, 74), (255, 255, 252)), ((255, 255, 252), (246, 238, 214), (206, 196, 168)), "white", "winged", ["feathers", "astrolabe", "corona", "inlay"], glow=(255, 248, 204), gem=(255, 255, 255), fx="stars", span=225),
    _p("Pioche de la genèse", "Le premier matin du monde, condensé en une seule pioche.",
       ((255, 255, 255), (250, 250, 255), (214, 218, 246), (255, 255, 255)), ((255, 255, 255), (250, 246, 236), (222, 212, 196)), "white", "winged", ["prism", "feathers", "halo", "corona", "astrolabe", "inlay"], glow=(255, 255, 255), gem=(255, 255, 255), fx="rainbow", span=232),

    # --- Paliers Ultimes, Cosmiques et Transcendants (84 à 100) ---
    _p("Pioche de l'Aube Cosmique", "Une lueur dorée primordiale qui pulvérise la roche avant même l'impact.",
       ((255, 245, 210), (255, 215, 120), (200, 150, 50), (255, 255, 240)), GOLDH, "gold", "winged", ["corona", "stars", "inlay"], glow=(255, 230, 150), gem=(255, 240, 180), fx="sparkle"),
    _p("Pioche du Supernova", "Une explosion stellaire contenue dans une lame de feu incandescent.",
       ((255, 220, 100), (255, 120, 30), (180, 40, 10), (255, 250, 180)), GOLDH, "gold", "winged", ["flames", "corona", "stars"], glow=(255, 140, 40), gem=(255, 200, 80), fx="embers"),
    _p("Pioche de Singularité", "Un point d'infinité gravitationnel qui attire et désintègre la pierre.",
       ((200, 150, 255), (120, 50, 220), (50, 10, 120), (240, 210, 255)), DKMETAL, "metal", "crystal", ["vortex", "nebula"], glow=(180, 100, 255), gem=(210, 150, 255), fx="void"),
    _p("Pioche d'Aiguille Temporelle", "Le temps se fige autour du manche : chaque coup frappe dix fois en une seconde.",
       ((255, 240, 180), (210, 170, 90), (130, 95, 40), (255, 250, 210)), GOLDH, "gold", "curved", ["gears", "astrolabe"], glow=(255, 220, 140), gem=(150, 230, 255), fx="sparkle"),
    _p("Pioche de la constante cosmique", "Rien ne peut modifier sa trajectoire ni freiner sa frappe.",
       ((240, 230, 255), (170, 140, 230), (90, 60, 160), (255, 245, 255)), GOLDH, "gold", "winged", ["astrolabe", "stars"], glow=(210, 170, 255), fx="stars"),
    _p("Pioche de l'Archonte", "Portée par les gardiens des abysses suprêmes, ceinturée d'oranges célestes.",
       ((240, 250, 255), (180, 210, 255), (100, 140, 210), (255, 255, 255)), SILVER, "metal", "winged", ["feathers", "halo"], glow=(160, 210, 255), gem=(200, 230, 255), fx="sparkle"),
    _p("Pioche du Vide Absolu", "Elle déchire la matière même de la galerie d'un simple effleurement.",
       ((160, 120, 220), (80, 30, 150), (25, 5, 60), (210, 170, 255)), DKMETAL, "metal", "winged", ["eye", "vortex", "spikes"], glow=(150, 70, 240), fx="void"),
    _p("Pioche de l'éther primordial", "Substance Originelle capable de façonner ou dissoudre le monde.",
       ((230, 250, 255), (150, 220, 240), (70, 150, 180), (250, 255, 255)), SILVER, "white", "crystal", ["nebula", "aurora"], glow=(160, 230, 255), fx="sparkle"),
    _p("Pioche du monarque céleste", "Couronnée d'étoiles filantes et réservée aux souverains des profondeurs.",
       ((255, 240, 170), (240, 190, 70), (160, 120, 20), (255, 250, 200)), GOLDH, "gold", "winged", ["feathers", "corona", "halo"], glow=(255, 220, 110), gem=(255, 240, 180), fx="stars"),
    _p("Pioche de la Réalité", "Une pioche forgée à partir des règles fondamentales de l'univers.",
       ((255, 255, 255), (230, 240, 255), (160, 180, 220), (255, 255, 255)), SILVER, "white", "crystal", ["prism", "infinity", "stars"], glow=(220, 240, 255), gem=(255, 255, 255), fx="rainbow"),
    _p("Pioche de l'horizon des événements", "Là où la lumière s'incline et le sous-sol capitule.",
       ((180, 130, 240), (100, 40, 180), (30, 10, 80), (220, 180, 255)), DKMETAL, "metal", "winged", ["vortex", "eclipse"], glow=(170, 80, 240), fx="void"),
    _p("Pioche de l'éventail d'étoiles", "Un faisceau de lumière constellée découpant la roche.",
       ((255, 250, 220), (250, 220, 140), (180, 150, 60), (255, 255, 240)), GOLDH, "gold", "winged", ["stars", "prism"], glow=(255, 235, 160), fx="stars"),
    _p("Pioche de l'Olympe Souterrain", "Les Dieux de la Mine s'en servent pour façonner le monde sous-terrain.",
       ((255, 235, 160), (240, 180, 60), (160, 110, 20), (255, 248, 200)), GOLDH, "gold", "winged", ["astrolabe", "corona", "feathers"], glow=(255, 210, 100), gem=(255, 235, 140), fx="sparkle"),
    _p("Pioche du Premier Filon", "Le filon originel cristallisé en une lame indestructible.",
       ((220, 255, 230), (120, 230, 160), (50, 150, 90), (240, 255, 245)), GOLDH, "gold", "crystal", ["elements", "aurora"], glow=(140, 255, 180), gem=(180, 255, 210), fx="sparkle"),
    _p("Pioche de la matrice divine", "Structure géométrique sacrée ordonnant les atomes de la pierre.",
       ((255, 255, 255), (240, 245, 255), (190, 200, 230), (255, 255, 255)), SILVER, "white", "crystal", ["prism", "halo", "astrolabe"], glow=(230, 245, 255), fx="rainbow"),
    _p("Pioche de l'Omnipotence", "Aucun obstacle de ce monde ou d'un autre ne peut ralentir son tranchant.",
       ((255, 255, 255), (255, 245, 220), (210, 180, 140), (255, 255, 255)), GOLDH, "white", "winged", ["prism", "corona", "halo", "astrolabe"], glow=(255, 250, 210), gem=(255, 255, 255), fx="rainbow"),
    _p("Pioche Transcendante Ultime", "La perfection absolue de l'art du mineur, brillant d'un éclat d'éternité.",
       ((255, 255, 255), (255, 250, 240), (210, 190, 230), (255, 255, 255)), ((255, 255, 255), (245, 240, 250), (200, 190, 220)), "white", "winged", ["prism", "feathers", "halo", "corona", "astrolabe", "infinity", "inlay"], glow=(255, 255, 255), gem=(255, 255, 255), fx="rainbow", span=240),
]
assert len(PICKAXE_SPECS) == 100
