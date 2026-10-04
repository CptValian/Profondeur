"""
Bataille en temps réel sur une ligne (axe x de 0 à WORLD_W).

Les troupes de l'attaquant partent de la gauche, celles du défenseur tiennent la droite,
et le DONJON D'ARCHER du défenseur est tout à l'arrière. Chaque unité agit seule :
 - elle cible l'ennemi le plus proche ;
 - si la cible est hors de portée, elle avance (les défenseurs ne sortent de leur
   position que lorsqu'un ennemi entre dans leur rayon d'alerte) ;
 - sinon elle attaque à sa cadence : coup direct au corps à corps, flèche (projectile
   qui met du temps à arriver) pour les archers ;
 - les dégâts sont réduits par la défense de la cible : x100/(100 + 4 x défense).
Le donjon tire des salves de flèches sur les attaquants les plus proches dans sa portée.
L'attaquant gagne quand TOUT le camp adverse (troupes + donjon) est détruit ; s'il perd
toutes ses troupes, ou si WAR_MAX_TIME est dépassé, le défenseur tient.
C'est cette simulation, et elle seule, qui décide des pertes et du vainqueur.
"""

import bisect
import random

from src import config
from src.items import crafting, tower as tower_mod

WORLD_W = 1000.0
TOWER_X = 955.0
ATT_FRONT = 290.0
DEF_FRONT = 700.0
AGGRO = 380.0            # rayon d'alerte des défenseurs
ARROW_SPEED = 520.0
TOWER_ARROW_SPEED = 640.0
MELEE_MAX_RANGE = 60.0

# --- Amélioration suprême du donjon ---
LAVA_X0, LAVA_X1 = 790.0, 910.0   # lac de lave devant le donjon (niveau suprême 2)
LAVA_DPS = 12.0                   # dégâts de lave par seconde (ignorent la défense)
BURN_TIME = 4.0                   # durée de la brûlure (niveau suprême 1)
SUPREME_PERIOD = 10.0             # renforts / pluie de flèches toutes les 10 s


class Unit:
    __slots__ = ("uid", "side", "rid", "x", "lane", "hp", "max_hp", "atk", "defense", "range", "speed",
                 "interval", "cd", "alive", "state", "attack_t", "hurt_t", "dead_t", "is_tower", "is_hero", "ranged",
                 "burn_t", "burn_dps", "summoned", "attack_type", "armor_type")

    def __init__(self, uid, side, rid, x, lane, rng):
        self.uid, self.side, self.rid, self.x, self.lane = uid, side, rid, x, lane
        self.is_tower = False
        self.is_hero = False
        self.burn_t = 0.0
        self.burn_dps = 0.0
        self.summoned = False
        if rid in crafting.RECIPES_BY_ID:
            r = crafting.RECIPES_BY_ID[rid]
            self.hp = self.max_hp = float(r.health)
            self.atk, self.defense, self.range, self.speed, self.interval = r.attack, r.defense, r.range, r.speed, r.interval
            self.ranged = r.range > MELEE_MAX_RANGE
            self.attack_type = getattr(r, "attack_type", "physical")
            self.armor_type = getattr(r, "armor_type", "light")
        else:
            self.hp = self.max_hp = 100.0
            self.atk = 10.0
            self.defense = 0.0
            self.range = 50.0
            self.speed = 100.0
            self.interval = 1.0
            self.ranged = False
            self.attack_type = "physical"
            self.armor_type = "heavy"
        self.cd = rng.uniform(0, self.interval)
        self.alive = True
        self.state = "idle"
        self.attack_t = self.hurt_t = self.dead_t = -99.0


class Projectile:
    __slots__ = ("src_x", "target", "dmg", "t", "dur", "tower", "src_side", "arc", "fire", "rain", "src_attack_type")

    def __init__(self, src_x, target, dmg, dur, tower, src_side, arc, src_attack_type="piercing"):
        self.src_x, self.target, self.dmg, self.t, self.dur = src_x, target, dmg, 0.0, dur
        self.fire = False
        self.rain = False
        self.tower, self.src_side, self.arc = tower, src_side, arc
        self.src_attack_type = src_attack_type


class BattleSim:
    def __init__(self, att_units: dict, def_units: dict, tower_levels: dict, hero=None, rng=None, record_events=False):
        self.rng = rng or random.Random()
        self.time = 0.0
        self.units = []
        self.projectiles = []
        self.events = []                 # (type, x, side) pour les effets visuels
        self.record = record_events
        self.finished = False
        self.attacker_won = False
        self.hero = hero
        self.hero_damage_dealt = 0.0
        self.hero_damage_taken = 0.0
        self.tower_stats = tower_mod.stats(tower_levels)
        self.att_start = {rid: n for rid, n in att_units.items() if n > 0 and rid in crafting.RECIPES_BY_ID}
        self.def_start = {rid: n for rid, n in def_units.items() if n > 0 and rid in crafting.RECIPES_BY_ID}
        uid = 0

        # Si l'attaquant possède le Héros
        if self.hero is not None:
            hu = Unit(uid, "att", "hero", ATT_FRONT - 10, 0, self.rng)
            hu.is_hero = True
            hu.hp = hu.max_hp = float(self.hero.max_hp)
            hu.atk = float(self.hero.attack_damage)
            hu.defense = float(self.hero.armor)
            hu.interval = float(self.hero.attack_interval)
            hu.range = 50.0
            hu.speed = 100.0
            hu.ranged = False
            hu.cd = 0.1
            self.units.append(hu)
            uid += 1

        for side, start, front, sign in (("att", self.att_start, ATT_FRONT, -1), ("def", self.def_start, DEF_FRONT, 1)):
            roster = []
            for rid, n in start.items():
                roster += [rid] * n
            # corps à corps devant, tireurs derrière
            roster.sort(key=lambda r: crafting.RECIPES_BY_ID[r].range)
            spacing = min(12.0, 250.0 / max(1, len(roster)))
            for i, rid in enumerate(roster):
                self.units.append(Unit(uid, side, rid, front + sign * i * spacing, (i % 3) - 1, self.rng))
                uid += 1
        t = Unit(uid, "def", "star_guardian", TOWER_X, 0, self.rng)     # gabarit ; remplacé ci-dessous
        t.rid, t.is_tower = "tower", True
        t.hp = t.max_hp = float(self.tower_stats["hp"])
        t.defense, t.atk, t.range, t.speed, t.ranged = config.TOWER_DEFENSE, 0, self.tower_stats["range"], 0, True
        t.interval = 1.0 / self.tower_stats["speed"]
        t.cd = t.interval
        self.tower = t
        self.units.append(t)
        self.next_uid = uid + 1
        self.supreme = int(self.tower_stats["supreme"])
        self.summon_timer = SUPREME_PERIOD
        self.rain_timer = SUPREME_PERIOD * 0.6
        self.notice = None               # (texte, temps) : bandeau affiché par la scène
        if not any(u.side == "att" for u in self.units):
            self.finished = True

    # ------------------------------------------------------------------
    def _alive(self, side):
        return [u for u in self.units if u.alive and u.side == side]

    @staticmethod
    def _nearest(sorted_units, keys, x):
        i = bisect.bisect_left(keys, x)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(sorted_units):
                u = sorted_units[j]
                if best is None or abs(u.x - x) < abs(best.x - x):
                    best = u
        return best

    def _direct(self, u, amount):
        """Dégâts directs (feu, lave) : ignorent la défense."""
        if not u.alive:
            return
        u.hp -= amount
        if getattr(u, "is_hero", False):
            self.hero_damage_taken += amount
        if u.hp <= 0:
            u.alive = False
            u.dead_t = self.time

    def _hit(self, target, raw, src_side, fire=False, src_unit=None, attack_type="physical"):
        if not target.alive:
            return
        atk_type = src_unit.attack_type if src_unit else attack_type
        aff_mult = crafting.get_affinity_multiplier(atk_type, target.armor_type)
        dmg = raw * aff_mult * self.rng.uniform(0.85, 1.15) * 100.0 / (100.0 + config.WAR_DEFENSE_FACTOR * target.defense)
        target.hp -= dmg
        target.hurt_t = self.time
        if src_unit and getattr(src_unit, "is_hero", False):
            self.hero_damage_dealt += dmg
        if getattr(target, "is_hero", False):
            self.hero_damage_taken += dmg
        if fire and not target.is_tower and target.side == "att":
            target.burn_t = BURN_TIME
            target.burn_dps = max(target.burn_dps, 0.5 * self.tower_stats["damage"])
        if self.record:
            self.events.append(("hit", target.x, target.side))
        if target.hp <= 0:
            target.alive = False
            target.dead_t = self.time

    # ------------------------------------------------------------------
    def step(self, dt):
        if self.finished:
            return
        self.time += dt
        atts, defs = self._alive("att"), self._alive("def")
        if not atts or not defs:
            self._finish(atts, defs)
            return
        # brûlures (niveau suprême 1) et lac de lave (niveau suprême 2) : touchent les attaquants
        if self.supreme >= 1:
            for u in atts:
                if self.supreme >= 2 and LAVA_X0 <= u.x <= LAVA_X1:
                    u.burn_t = max(u.burn_t, 1.0)
                    self._direct(u, LAVA_DPS * dt)
                if u.burn_t > 0:
                    u.burn_t -= dt
                    self._direct(u, u.burn_dps * dt)
            atts = [u for u in atts if u.alive]
            if not atts:
                self._finish(atts, defs)
                return
        a_sorted, d_sorted = sorted(atts, key=lambda u: u.x), sorted(defs, key=lambda u: u.x)
        a_keys, d_keys = [u.x for u in a_sorted], [u.x for u in d_sorted]

        for u in atts + defs:
            if u.is_tower:
                continue
            enemies, keys = (d_sorted, d_keys) if u.side == "att" else (a_sorted, a_keys)
            tgt = self._nearest(enemies, keys, u.x)
            dist = abs(tgt.x - u.x)
            if dist <= u.range:
                u.state = "attack"
                u.cd -= dt
                if u.cd <= 0:
                    u.cd += u.interval
                    u.attack_t = self.time
                    if u.ranged:
                        dur = max(0.15, dist / ARROW_SPEED)
                        self.projectiles.append(Projectile(u.x, tgt, u.atk, dur, False, u.side, 30.0, src_attack_type=u.attack_type))
                    else:
                        self._hit(tgt, u.atk, u.side, src_unit=u)
            elif u.side == "att" or dist <= AGGRO:
                step = min(u.speed * dt, dist - u.range + 0.5)
                u.x += step if tgt.x > u.x else -step
                u.state = "move"
            else:
                u.state = "idle"

        # donjon d'archer
        tw = self.tower
        if tw.alive and atts:
            tw.cd -= dt
            if tw.cd <= 0:
                in_range = sorted((u for u in atts if abs(u.x - tw.x) <= tw.range), key=lambda u: abs(u.x - tw.x))
                if in_range:
                    tw.cd += tw.interval
                    tw.attack_t = self.time
                    n = int(self.tower_stats["arrows"])
                    for k in range(n):
                        tgt = in_range[k % len(in_range)]
                        dur = max(0.2, abs(tw.x - tgt.x) / TOWER_ARROW_SPEED)
                        p = Projectile(tw.x, tgt, self.tower_stats["damage"], dur + k * 0.03, True, "def", 90.0)
                        p.t = -k * 0.0   # tir simultané ; léger décalage via la durée
                        p.fire = self.supreme >= 1
                        self.projectiles.append(p)
                else:
                    tw.cd = 0.0

        # renforts (niveaux suprêmes 3 et 4) et pluie de flèches (niveau suprême 5) : tant que le donjon tient
        if tw.alive and self.supreme >= 3:
            self.summon_timer -= dt
            if self.summon_timer <= 0:
                self.summon_timer += SUPREME_PERIOD
                self._summon()
        if tw.alive and self.supreme >= 5:
            self.rain_timer -= dt
            if self.rain_timer <= 0:
                self.rain_timer += SUPREME_PERIOD
                self._rain([u for u in atts if u.alive])

        # projectiles
        keep = []
        for p in self.projectiles:
            p.t += dt
            if p.t >= p.dur:
                self._hit(p.target, p.dmg, p.src_side, p.fire, attack_type=p.src_attack_type)
            else:
                keep.append(p)
        self.projectiles = keep

        if self.time >= config.WAR_MAX_TIME:
            self._finish(self._alive("att"), self._alive("def"), timeout=True)
        elif not self._alive("att") or not self._alive("def"):
            self._finish(self._alive("att"), self._alive("def"))

    def _summon(self):
        rids = ["pikeman", "pikeman"] + (["golem"] if self.supreme >= 4 else [])
        for rid in rids:
            u = Unit(self.next_uid, "def", rid, TOWER_X - 45 - self.rng.uniform(0, 30), self.rng.randint(-1, 1), self.rng)
            self.next_uid += 1
            u.summoned = True
            self.units.append(u)
            if self.record:
                self.events.append(("summon", u.x, "def"))
        self.notice = ("Renforts du donjon !", self.time)

    def _rain(self, targets):
        if not targets:
            return
        dmg = self.tower_stats["damage"] * 1.2
        for k in range(12):
            tgt = self.rng.choice(targets)
            p = Projectile(tgt.x + self.rng.uniform(-40, 40), tgt, dmg, 0.45, False, "def", 0.0)
            p.t = -k * 0.06            # les flèches tombent en cascade
            p.fire = True
            p.rain = True
            self.projectiles.append(p)
        self.notice = ("Pluie de flèches !", self.time)

    def _finish(self, atts, defs, timeout=False):
        self.finished = True
        self.attacker_won = bool(atts) and not defs and not timeout

    def run(self, dt=0.1):
        while not self.finished:
            self.step(dt)
        return self

    # ------------------------------------------------------------------
    def survivors(self, side) -> dict:
        out = {}
        for u in self.units:
            if u.side == side and u.alive and not u.is_tower and not u.summoned:
                out[u.rid] = out.get(u.rid, 0) + 1
        return out
