"""Particules : débris de roche à l'impact, poussière ambiante en fond."""

import random
import pygame


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "gravity")

    def __init__(self, x, y, vx, vy, life, color, size, gravity=420):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity

    def update(self, dt):
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        ratio = max(0.0, self.life / self.max_life)
        alpha = int(255 * ratio)
        s = max(1, int(self.size * ratio))
        surf = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (s, s), s)
        surface.blit(surf, (self.x - s, self.y - s))


class DustMote:
    __slots__ = ("x", "y", "speed", "size", "alpha", "drift")

    def __init__(self, w, h, rng):
        self.x = rng.uniform(0, w)
        self.y = rng.uniform(0, h)
        self.speed = rng.uniform(6, 18)
        self.size = rng.uniform(1, 2.4)
        self.alpha = rng.uniform(20, 60)
        self.drift = rng.uniform(-4, 4)

    def update(self, dt, w, h):
        self.y -= self.speed * dt
        self.x += self.drift * dt
        if self.y < 0:
            self.y = h
        if self.x < 0:
            self.x = w
        elif self.x > w:
            self.x = 0

    def draw(self, surface):
        s = int(self.size)
        surf = pygame.Surface((s * 2 + 2, s * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (220, 210, 230, int(self.alpha)), (s + 1, s + 1), s)
        surface.blit(surf, (self.x - s, self.y - s))


class ParticleSystem:
    def __init__(self, area_w, area_h, n_dust=36):
        self.particles = []
        rng = random.Random(42)
        self.dust = [DustMote(area_w, area_h, rng) for _ in range(n_dust)]
        self.area_w, self.area_h = area_w, area_h

    def spawn_break(self, x, y, color, n=14):
        for _ in range(n):
            ang = random.uniform(0, 6.283)
            speed = random.uniform(60, 220)
            vx = speed * random.uniform(-1, 1)
            vy = -abs(speed * random.uniform(0.3, 1.0))
            life = random.uniform(0.35, 0.75)
            size = random.uniform(2, 5)
            shade = tuple(max(0, min(255, c + random.randint(-25, 25))) for c in color)
            self.particles.append(Particle(x, y, vx, vy, life, shade, size))

    def spawn_hit_sparks(self, x, y, n=4):
        for _ in range(n):
            vx = random.uniform(-90, 90)
            vy = random.uniform(-140, -40)
            self.particles.append(Particle(x, y, vx, vy, random.uniform(0.15, 0.3),
                                            (255, 220, 140), random.uniform(1.5, 3), gravity=600))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]
        for d in self.dust:
            d.update(dt, self.area_w, self.area_h)

    def draw_dust(self, surface):
        for d in self.dust:
            d.draw(surface)

    def draw_particles(self, surface):
        for p in self.particles:
            p.draw(surface)
