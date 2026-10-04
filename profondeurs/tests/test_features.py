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

    def test_starting_stones_hp(self):
        reg = StoneRegistry()
        s0 = reg.get_by_id("s0")
        s1 = reg.get_by_id("s1")
        b0 = Block("s0", s0.hardness, 0)
        b1 = Block("s1", s1.hardness, 0)
        self.assertAlmostEqual(b0.max_health, 1.0, delta=0.05)
        self.assertAlmostEqual(b1.max_health, 3.0, delta=0.05)

    def test_mining_rewards(self):
        self.assertEqual(config.GOLD_PER_BLOCK_HP, 0.28)
        self.assertEqual(config.TOOL_XP_PER_DAMAGE, 0.35)

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


if __name__ == "__main__":
    unittest.main()
