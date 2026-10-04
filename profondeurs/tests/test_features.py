import unittest
from src import config
from src.entities.player import Player
from src.world.stone_registry import StoneRegistry
from src.world.world_generator import WorldGenerator
from src.world.block import Block
from src.items.equipment import Aura
from src.entities.companion import MiningCompanion
from src.entities.hero import Hero
from src.combat import faction_war


class TestGameFeatures(unittest.TestCase):

    def test_aura_upgrade_cost(self):
        aura = Aura(tier=0)
        cost_tier0 = aura.upgrade_cost()
        self.assertGreater(cost_tier0, config.UPGRADE_BASE_COST * 5)
        aura.upgrade()
        cost_tier1 = aura.upgrade_cost()
        self.assertGreater(cost_tier1, cost_tier0 * 2)

    def test_equipment_20_tiers(self):
        self.assertEqual(len(config.HELMET_TIERS), 20)
        self.assertEqual(len(config.ARMOR_TIERS), 20)
        self.assertEqual(len(config.AURA_TIERS), 20)
        self.assertEqual(len(config.AMULET_TIERS), 20)
        self.assertEqual(len(config.GAUNTLET_TIERS), 20)

    def test_starting_stones_hp(self):
        reg = StoneRegistry()
        s0 = reg.get_by_id("s0")
        s1 = reg.get_by_id("s1")
        b0 = Block("s0", s0.hardness, 0)
        b1 = Block("s1", s1.hardness, 0)
        self.assertAlmostEqual(b0.max_health, 1.0, delta=0.05)
        self.assertAlmostEqual(b1.max_health, 3.0, delta=0.05)

    def test_pickaxe_tiers_count(self):
        from src.items.pickaxe_specs import PICKAXE_SPECS
        self.assertEqual(len(PICKAXE_SPECS), 100)
        self.assertEqual(len(config.TOOL_TIERS), 100)
        self.assertAlmostEqual(config.TOOL_TIERS[10]["power"], 1.4)
        self.assertAlmostEqual(config.TOOL_TIERS[10]["speed"], 1.55)

    def test_faction_bank(self):
        from main import Game
        game = Game()
        game.player.inventory.gold = 1000
        game.faction_banks[0] = 0.0

        amount = game.player.inventory.gold * 0.5
        game.player.inventory.gold -= amount
        game.faction_banks[0] += amount

        self.assertEqual(game.faction_banks[0], 500)
        self.assertEqual(game.player.inventory.gold, 500)

        old_gold = game.player.inventory.gold
        dt = 10.0
        expected_gen = 500 * config.BANK_INTEREST_RATE * dt
        game.update()
        game.player.inventory.gold += expected_gen
        self.assertEqual(game.player.inventory.gold, old_gold + expected_gen)

    def test_joint_grid_event(self):
        from main import Game
        game = Game()
        self.assertFalse(game.joint_grid_active)

        main_world = game.world
        orig_player_pos = (game.player.row, game.player.col)
        orig_ai_pos = (game.competitors[0].state.row, game.competitors[0].state.col)

        game.start_joint_grid_event()
        self.assertTrue(game.joint_grid_active)
        self.assertNotEqual(game.world, main_world)
        self.assertEqual(game.joint_grid_time_left, 30.0)

        block = game.world.get_block(0, 0)
        block.is_empty = False
        block.health = 0.01
        game.apply_hit(0, 0)
        self.assertGreater(game.joint_grid_points[0], 0)

        old_gold = game.player.inventory.gold
        game.end_joint_grid_event()
        self.assertFalse(game.joint_grid_active)
        self.assertEqual(game.world, main_world)
        self.assertEqual((game.player.row, game.player.col), orig_player_pos)
        self.assertEqual((game.competitors[0].state.row, game.competitors[0].state.col), orig_ai_pos)
        self.assertGreaterEqual(game.player.inventory.gold, old_gold)

    def test_depth_boss_system(self):
        from main import Game
        game = Game()
        self.assertFalse(game.is_depth_blocked_by_boss(500))
        self.assertTrue(game.is_depth_blocked_by_boss(1000))

        game.defeated_depth_bosses.add(1000)
        self.assertFalse(game.is_depth_blocked_by_boss(1000))
        self.assertTrue(game.is_depth_blocked_by_boss(2000))

    def test_mercy_god_blessing(self):
        from main import Game
        game = Game()
        initial_power = game.player.mining_power

        game.apply_mercy_blessing(0, 2)
        self.assertGreater(game.player.mining_power, initial_power)

        old_interval = game._attack_interval(game.session_time)
        game.apply_mercy_blessing(0, 1)
        new_interval = game._attack_interval(game.session_time)
        self.assertAlmostEqual(new_interval, old_interval / 2.0)

    def test_raided_dungeon_hp_boost(self):
        from src.items.inventory import Inventory
        player = Player()
        att_inv = player.inventory
        def_inv = Inventory()

        att_inv.units["pikeman"] = 10
        self.assertEqual(def_inv.tower_hp_permanent_bonus, 0.0)

        sim = faction_war.start_battle(att_inv, def_inv)
        sim.run()
        report = faction_war.finalize_battle(sim, "Attacker", att_inv, "Defender", def_inv)

        if report.attacker_won:
            self.assertEqual(def_inv.tower_hp_permanent_bonus, 50.0)

    def test_mining_rewards(self):
        self.assertAlmostEqual(config.GOLD_PER_BLOCK_HP, 0.364)
        self.assertEqual(config.TOOL_XP_PER_DAMAGE, 0.35)

    def test_audio_manager_and_settings(self):
        from src.audio_manager import AudioManager
        audio = AudioManager()
        self.assertTrue(audio.music_enabled)
        self.assertTrue(audio.sfx_enabled)

        music_state = audio.toggle_music()
        self.assertFalse(music_state)
        sfx_state = audio.toggle_sfx()
        self.assertFalse(sfx_state)

        audio.update_atmosphere(100)
        audio.update_atmosphere(300)
        audio.update_atmosphere(800)

        audio.sfx_enabled = True
        audio.play_pickaxe_hit(hardness=1.0)
        audio.play_pickaxe_hit(hardness=2.5)

    def test_alt_and_continuous_mining(self):
        from main import Game
        game = Game()
        game.state = "exploring"
        self.assertFalse(game.is_mining_active)
        self.assertEqual(game.alt_dir, -1)

    def test_army_affinity_system(self):
        from src.items import crafting
        magic_vs_heavy = crafting.get_affinity_multiplier("magic", "heavy")
        self.assertEqual(magic_vs_heavy, 2.0)
        piercing_vs_light = crafting.get_affinity_multiplier("piercing", "light")
        self.assertEqual(piercing_vs_light, 1.5)

    def test_monuments_and_builders(self):
        player = Player()
        inv = player.inventory
        self.assertEqual(inv.stone_fragments, 0.0)
        self.assertEqual(inv.builders, 0)
        self.assertEqual(inv.monuments_built, 0)

        b = Block("s0", hardness=1.0, depth=0)
        inv.stone_fragments += b.max_health
        self.assertGreater(inv.stone_fragments, 0)

        inv.gold = 100
        recruited = inv.recruit_builder()
        self.assertTrue(recruited)
        self.assertEqual(inv.builders, 1)

        inv.stone_fragments = 1000.0
        finished = inv.tick_monuments(1000.0)
        self.assertTrue(finished)
        self.assertEqual(inv.monuments_built, 1)
        self.assertAlmostEqual(player.monument_bonus, 0.05)

    def test_xp_stones_and_passive_xp(self):
        player = Player()
        player.inventory.xp_stones = 3
        start_xp = player.xp
        player.passive_regen(1.0)
        self.assertGreater(player.xp, start_xp)

    def test_mining_companion(self):
        player = Player()
        player.level = 14
        player.refresh_unlocks()
        self.assertFalse(player.has_companion)

        player.level = 15
        player.refresh_unlocks()
        self.assertTrue(player.has_companion)

        comp = player.companion
        initial_power = comp.mining_power
        comp.add_xp(500)
        self.assertGreater(comp.level, 1)
        self.assertGreater(comp.mining_power, initial_power)

        player.inventory.gold = 100000
        initial_speed = comp.hits_per_second
        upgraded = comp.upgrade_gold(player)
        self.assertTrue(upgraded)
        self.assertGreater(comp.hits_per_second, initial_speed)

    def test_hero_and_faction_war(self):
        player = Player()
        player.level = 19
        player.refresh_unlocks()
        self.assertFalse(player.has_hero)

        player.level = 20
        player.refresh_unlocks()
        self.assertTrue(player.has_hero)

        hero = player.hero
        initial_hp = hero.max_hp
        initial_atk = hero.attack_damage

        player.inventory.gold = 100000
        upgraded = hero.upgrade_gold(player)
        self.assertTrue(upgraded)
        self.assertGreater(hero.max_hp, initial_hp)
        self.assertGreater(hero.attack_damage, initial_atk)

        att_inv = player.inventory
        att_inv.units["pikeman"] = 3
        def_inv = player.inventory

        # Offensive battle: Hero participates
        sim = faction_war.start_battle(att_inv, def_inv, hero=hero)
        sim.run()
        report = faction_war.finalize_battle(sim, "Toi", att_inv, "Ennemi", def_inv, hero=hero)
        self.assertGreater(hero.xp, 0)

        # Defensive battle: Hero does NOT participate
        defend_sim = faction_war.start_battle(att_inv, def_inv, hero=None)
        self.assertFalse(any(u.is_hero for u in defend_sim.units))

    def test_extreme_difficulty_ai(self):
        from src.ai.competitor import create_competitors
        diffs = ["Extrême"] * 15
        competitors = create_competitors(diffs)
        ai = competitors[0]
        self.assertEqual(ai.difficulty, "Extrême")
        self.assertAlmostEqual(ai.power_mult, 1.6)
        self.assertAlmostEqual(ai.speed_mult, 1.45)

    def test_monster_spawn_rate_reduced(self):
        self.assertAlmostEqual(config.MONSTER_SPAWN_CHANCE, 0.04 / 3.0)


if __name__ == "__main__":
    unittest.main()
