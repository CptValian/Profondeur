"""Sauvegarde/chargement de l'état de la partie (joueur + IA + galeries creusées) en JSON.

Ce qui est sauvegardé :
 - difficulté individuelle de chaque IA (choisie au début de la partie, verrouillée ensuite) ;
 - progression complète de chaque IA : position, PV, or, pioche (palier/niveau/XP), artefacts,
   pierres découvertes, composants, unités fabriquées, compteur anti-doublon, galeries creusées ;
 - progression complète du joueur (idem + équipements, dont le gantelet).
"""

import json
import os
from src import config


def _eq_to_dict(eq):
    return {"tier": eq.tier, "xp": eq.xp, "level": eq.level}


def _eq_from_dict(eq, d, max_level):
    eq.tier = d.get("tier", 0)
    eq.xp = d.get("xp", 0.0)
    eq.level = max(1, min(max_level, d.get("level", 1)))


def _inv_extra_to_dict(inv):
    return {
        "components": dict(inv.components),
        "components_seen": sorted(inv.components_seen),
        "units": dict(inv.units),
        "tower": dict(inv.tower),
        "war_wins": inv.war_wins,
        "xp_stones": inv.xp_stones,
        "stone_fragments": inv.stone_fragments,
        "builders": inv.builders,
        "monument_progress": inv.monument_progress,
        "monuments_built": inv.monuments_built,
    }


def _inv_extra_from_dict(inv, d):
    inv.components.update(d.get("components", {}))
    inv.components_seen = set(d.get("components_seen", [])) | {k for k, v in inv.components.items() if v > 0}
    # les anciennes "défenses" (palissades...) n'existent plus : on ignore les unités inconnues
    from src.items import crafting
    inv.units.update({k: v for k, v in d.get("units", {}).items() if k in crafting.RECIPES_BY_ID})
    inv.tower.update({k: v for k, v in d.get("tower", {}).items() if k in inv.tower})
    inv.war_wins = d.get("war_wins", 0)
    inv.xp_stones = d.get("xp_stones", 0)
    inv.stone_fragments = d.get("stone_fragments", 0.0)
    inv.builders = d.get("builders", 0)
    inv.monument_progress = d.get("monument_progress", 0.0)
    inv.monuments_built = d.get("monuments_built", 0)


def _ai_to_dict(ai):
    d = {
        "name": ai.name,
        "difficulty": ai.difficulty,
        "tool": _eq_to_dict(ai.tool),
        "row": ai.state.row,
        "col": ai.state.col,
        "health": ai.state.health,
        "max_health": ai.state.max_health,
        "gold": ai.inventory.gold,
        "resources": dict(ai.inventory.resources),
        "mining_power_bonus": ai.state.mining_power_bonus,
        "mining_power_pct": ai.state.mining_power_pct,
        "damage_reduction": ai.state.damage_reduction,
        "gold_pct": ai.state.gold_pct,
        "combat_damage": ai.state.combat_damage,
        "component_luck": ai.state.component_luck,
        "artifact_pity": ai.artifact_pity,
        "artifacts_found": list(ai.artifacts.found),
        "stones_discovered": ai.stones.to_dict(),
        "world_dug": ai.world.export_dug(),
    }
    d.update(_inv_extra_to_dict(ai.inventory))
    return d


def _ai_from_dict(ai, d, version=3):
    ai.difficulty = d.get("difficulty", ai.difficulty)
    if "tool" in d:
        _eq_from_dict(ai.tool, d["tool"], config.TOOL_MAX_LEVEL)
    ai.state.row = d.get("row", ai.state.row)
    ai.state.col = d.get("col", ai.state.col)
    ai.state.max_health = d.get("max_health", ai.state.max_health)
    ai.state.health = d.get("health", ai.state.health)
    ai.inventory.gold = d.get("gold", 0)
    ai.inventory.resources.update(d.get("resources", {}))
    ai.state.mining_power_bonus = d.get("mining_power_bonus", 0.0)
    ai.state.mining_power_pct = d.get("mining_power_pct", 0.0)
    ai.state.damage_reduction = d.get("damage_reduction", 0.0)
    ai.state.gold_pct = d.get("gold_pct", 0.0)
    ai.state.combat_damage = d.get("combat_damage", 0.0)
    ai.state.component_luck = d.get("component_luck", 0.0)
    ai.artifact_pity = d.get("artifact_pity", 0)
    ai.artifacts.found = set(d.get("artifacts_found", []))
    ai.recompute_artifact_bonuses()
    if "stones_discovered" in d and version >= 3:   # avant v3, chaque IA avait ses propres pierres
        ai.stones.load_dict(d["stones_discovered"])
    if "world_dug" in d:
        ai.world.import_dug(d["world_dug"])
    _inv_extra_from_dict(ai.inventory, d)
    ai.status = "creuse"
    ai.target_cell = None
    ai.last_cell = None


def save_exists(path=config.SAVE_PATH) -> bool:
    return os.path.exists(path)


def save_game(player, stone_registry, artifact_catalog, competitive_ai, competitors=None, world=None,
              ledger=None, path=config.SAVE_PATH, audio=None):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    pdata = {
        "row": player.row,
        "col": player.col,
        "health": player.health,
        "base_max_health": player.base_max_health,
        "gold": player.inventory.gold,
        "resources": dict(player.inventory.resources),
        "owned_artifacts": list(player.inventory.owned_artifacts),
        "max_depth_reached": player.max_depth_reached,
        "bonus_mining_power": player.bonus_mining_power,
        "bonus_mining_power_pct": player.bonus_mining_power_pct,
        "bonus_artifact_luck": player.bonus_artifact_luck,
        "bonus_max_health": player.bonus_max_health,
        "bonus_damage_reduction": player.bonus_damage_reduction,
        "bonus_gold_pct": player.bonus_gold_pct,
        "bonus_combat_damage": player.bonus_combat_damage,
        "bonus_component_luck": player.bonus_component_luck,
        "artifact_pity": player.artifact_pity,
        "perks": dict(player.perks),
        "blocks_broken": player.blocks_broken,
        "tool": _eq_to_dict(player.tool),
        "helmet": _eq_to_dict(player.helmet),
        "armor": _eq_to_dict(player.armor),
        "aura": _eq_to_dict(player.aura),
        "amulet": _eq_to_dict(player.amulet),
        "gauntlet": _eq_to_dict(player.gauntlet),
        "companion": {
            "gold_tier": player.companion.gold_tier,
            "level": player.companion.level,
            "xp": player.companion.xp,
            "row": player.companion.row,
            "col": player.companion.col,
        },
        "hero": {
            "gold_tier": player.hero.gold_tier,
            "level": player.hero.level,
            "xp": player.hero.xp,
        },
        "level": player.level,
        "xp": player.xp,
    }
    pdata.update(_inv_extra_to_dict(player.inventory))
    data = {
        "version": 3,
        "stone_ledger": ledger.to_dict() if ledger is not None else {},
        "player": pdata,
        "world_dug": world.export_dug() if world is not None else {},
        "stones": stone_registry.to_dict(),
        "artifacts_found": list(artifact_catalog.found),
        "player_rating": competitive_ai.player_rating,
        "competitors": [_ai_to_dict(ai) for ai in (competitors or [])],
        "audio_settings": {
            "music_enabled": audio.music_enabled if audio else True,
            "sfx_enabled": audio.sfx_enabled if audio else True,
        },
    }
    # écriture atomique : une fermeture brutale ne corrompt pas la sauvegarde
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def load_game(player, stone_registry, artifact_catalog, competitive_ai, competitors=None, world=None,
              ledger=None, path=config.SAVE_PATH, audio=None):
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    p = data["player"]
    player.row = p["row"]
    player.col = p["col"]
    player.base_max_health = p.get("base_max_health", config.PLAYER_START_HEALTH)
    player.health = p["health"]
    player.inventory.gold = p["gold"]
    player.inventory.resources.update(p["resources"])
    player.inventory.owned_artifacts = set(p["owned_artifacts"])
    player.max_depth_reached = p["max_depth_reached"]
    player.bonus_mining_power = p.get("bonus_mining_power", 0.0)
    player.bonus_mining_power_pct = p.get("bonus_mining_power_pct", 0.0)
    player.bonus_artifact_luck = p.get("bonus_artifact_luck", 0.0)
    player.bonus_max_health = p.get("bonus_max_health", 0.0)
    player.bonus_damage_reduction = p.get("bonus_damage_reduction", 0.0)
    player.bonus_gold_pct = p.get("bonus_gold_pct", 0.0)
    player.bonus_combat_damage = p.get("bonus_combat_damage", 0.0)
    player.bonus_component_luck = p.get("bonus_component_luck", 0.0)
    player.artifact_pity = p.get("artifact_pity", 0)
    player.blocks_broken = p.get("blocks_broken", 0)
    _inv_extra_from_dict(player.inventory, p)

    for key, max_level in (("tool", config.TOOL_MAX_LEVEL), ("helmet", config.EQUIP_MAX_LEVEL),
                           ("armor", config.EQUIP_MAX_LEVEL), ("aura", config.EQUIP_MAX_LEVEL),
                           ("amulet", config.EQUIP_MAX_LEVEL), ("gauntlet", config.EQUIP_MAX_LEVEL)):
        if key in p:
            _eq_from_dict(getattr(player, key), p[key], max_level)

    if "companion" in p:
        cmp = p["companion"]
        player.companion.gold_tier = max(0, min(player.companion.max_gold_tier, cmp.get("gold_tier", 0)))
        player.companion.level = max(1, min(player.companion.max_level, cmp.get("level", 1)))
        player.companion.xp = cmp.get("xp", 0.0)
        player.companion.row = cmp.get("row", player.row)
        player.companion.col = cmp.get("col", player.col)

    if "hero" in p:
        hr = p["hero"]
        player.hero.gold_tier = max(0, min(player.hero.max_gold_tier, hr.get("gold_tier", 0)))
        player.hero.level = max(1, min(player.hero.max_level, hr.get("level", 1)))
        player.hero.xp = hr.get("xp", 0.0)

    if "level" in p:
        player.level = max(1, min(config.PLAYER_MAX_LEVEL, p["level"]))
        player.xp = p.get("xp", 0.0)
    else:   # ancienne sauvegarde : niveau déduit de l'XP déjà accumulée par les objets
        player.set_total_xp(sum(it.total_xp() for it in (player.tool,) + player.equipment_items()))
    player.pending_levels = []
    player.refresh_unlocks()

    # garde-fou : un joueur sauvegardé à 0 PV repart à moitié de sa vie
    player.alive = True
    if player.health <= 0:
        player.health = max(1, player.max_health // 2)

    stone_registry.load_dict(data["stones"])
    artifact_catalog.found = set(data["artifacts_found"])
    player.recompute_artifact_bonuses(artifact_catalog)
    player.health = min(player.health, player.max_health)
    competitive_ai.player_rating = data.get("player_rating", 1000.0)
    if world is not None and "world_dug" in data:
        world.import_dug(data["world_dug"])

    version = data.get("version", 1)
    if ledger is not None:
        if "stone_ledger" in data:
            ledger.load_dict(data["stone_ledger"])
        else:   # ancienne sauvegarde : les pierres déjà nommées par le joueur deviennent celles de sa faction
            for sid, st in stone_registry._cache.items():
                if st.discovered:
                    ledger.claim(sid, "Toi", 0, st.custom_name or f"Pierre de {st.depth_tier}")
        ledger.sync(stone_registry)

    if audio is not None and "audio_settings" in data:
        audio.music_enabled = data["audio_settings"].get("music_enabled", True)
        audio.sfx_enabled = data["audio_settings"].get("sfx_enabled", True)

    if competitors:
        saved_by_name = {c["name"]: c for c in data.get("competitors", [])}
        for ai in competitors:
            if ai.name in saved_by_name:
                _ai_from_dict(ai, saved_by_name[ai.name], version)
            if ledger is not None:
                ledger.sync(ai.stones)
    return True


def peek_ai_difficulties(profile_names, path=config.SAVE_PATH):
    """Relit uniquement les difficultés IA sauvegardées, pour préremplir le
    menu sans avoir à recréer une partie complète."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    saved_by_name = {c["name"]: c.get("difficulty") for c in data.get("competitors", [])}
    if not saved_by_name:
        return None
    return [saved_by_name.get(name) or config.DEFAULT_DIFFICULTY for name in profile_names]
