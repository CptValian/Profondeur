"""
Gestionnaire audio pour Profondeurs :
 - Effets sonores de pioche procéduraux avec variation de pitch (+/- 5%) et timbre (métallique vs sourd).
 - Musique et atmosphère dynamique qui évoluent selon la profondeur (Surface -> Caverne -> Abysses).
 - Paramètres d'activation/désactivation de la musique et des bruitages.
"""

import random
import math
import pygame
import numpy as np


class AudioManager:
    def __init__(self):
        self.music_enabled = True
        self.sfx_enabled = True
        self.initialized = False
        self._init_mixer()

        self.current_depth = 0
        self.surface_sound = None
        self.cavern_sound = None
        self.abyss_sound = None
        self.surface_channel = None
        self.cavern_channel = None
        self.abyss_channel = None

        if self.initialized:
            self._generate_ambient_tracks()

    def _init_mixer(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            self.initialized = True
        except Exception:
            self.initialized = False

    def _generate_ambient_tracks(self):
        if not self.initialized:
            return
        sr = 44100
        dur = 4.0  # boucle de 4 secondes

        # Surface : accords doux et lumineux
        t = np.linspace(0, dur, int(sr * dur), False)
        wave_surf = (0.15 * np.sin(2 * np.pi * 261.63 * t) +
                     0.12 * np.sin(2 * np.pi * 329.63 * t) +
                     0.10 * np.sin(2 * np.pi * 392.00 * t))
        env = np.sin(np.pi * t / dur)
        wave_surf *= env
        stereo_surf = np.column_stack((wave_surf, wave_surf))
        surf_bytes = (stereo_surf * 32767).astype(np.int16)
        self.surface_sound = pygame.sndarray.make_sound(surf_bytes)

        # Caverne : tonalité résonnante avec gouttes d'eau
        wave_cav = 0.12 * np.sin(2 * np.pi * 110.0 * t) + 0.08 * np.sin(2 * np.pi * 164.81 * t)
        rng = np.random.RandomState(42)
        for _ in range(3):
            drop_pos = rng.randint(0, len(t) - 4410)
            drop_t = np.linspace(0, 0.1, 4410, False)
            drop_freq = rng.uniform(800, 1400)
            drop_wave = 0.25 * np.sin(2 * np.pi * drop_freq * drop_t) * np.exp(-drop_t * 40)
            wave_cav[drop_pos:drop_pos + 4410] += drop_wave
        wave_cav *= env
        stereo_cav = np.column_stack((wave_cav, wave_cav))
        cav_bytes = (stereo_cav * 32767).astype(np.int16)
        self.cavern_sound = pygame.sndarray.make_sound(cav_bytes)

        # Abysses : bourdonnement grave et oppressant
        wave_aby = 0.20 * np.sin(2 * np.pi * 55.0 * t) + 0.15 * np.sin(2 * np.pi * 82.41 * t) + 0.05 * np.sin(2 * np.pi * 115.0 * t)
        wave_aby *= env
        stereo_aby = np.column_stack((wave_aby, wave_aby))
        aby_bytes = (stereo_aby * 32767).astype(np.int16)
        self.abyss_sound = pygame.sndarray.make_sound(aby_bytes)

        try:
            self.surface_channel = pygame.mixer.Channel(0)
            self.cavern_channel = pygame.mixer.Channel(1)
            self.abyss_channel = pygame.mixer.Channel(2)

            if self.surface_sound:
                self.surface_channel.play(self.surface_sound, loops=-1)
            if self.cavern_sound:
                self.cavern_channel.play(self.cavern_sound, loops=-1)
            if self.abyss_sound:
                self.abyss_channel.play(self.abyss_sound, loops=-1)

            self.update_atmosphere(0)
        except Exception:
            pass

    def play_pickaxe_hit(self, hardness: float = 1.0):
        if not self.initialized or not self.sfx_enabled:
            return

        sr = 44100
        dur = 0.12
        t = np.linspace(0, dur, int(sr * dur), False)
        pitch_factor = random.uniform(0.95, 1.05)

        if hardness > 1.5:
            base_f = 600.0 * pitch_factor
            wave = (0.4 * np.sin(2 * np.pi * base_f * t) +
                    0.3 * np.sin(2 * np.pi * base_f * 2.76 * t) +
                    0.2 * np.sin(2 * np.pi * base_f * 4.12 * t))
            env = np.exp(-t * 35)
        else:
            base_f = 160.0 * pitch_factor
            wave = (0.5 * np.sin(2 * np.pi * base_f * t) +
                    0.25 * np.sin(2 * np.pi * base_f * 2.1 * t))
            env = np.exp(-t * 22)

        wave = wave * env
        stereo = np.column_stack((wave, wave))
        snd_bytes = (stereo * 32767).astype(np.int16)

        try:
            snd = pygame.sndarray.make_sound(snd_bytes)
            snd.set_volume(0.5)
            snd.play()
        except Exception:
            pass

    def update_atmosphere(self, depth: int):
        self.current_depth = depth
        if not self.initialized:
            return

        if not self.music_enabled:
            if self.surface_channel:
                self.surface_channel.set_volume(0.0)
            if self.cavern_channel:
                self.cavern_channel.set_volume(0.0)
            if self.abyss_channel:
                self.abyss_channel.set_volume(0.0)
            return

        if depth <= 150:
            surf_vol = max(0.0, 1.0 - (depth / 150.0))
            cav_vol = min(1.0, depth / 150.0)
            aby_vol = 0.0
        elif depth <= 500:
            surf_vol = 0.0
            p = (depth - 150) / 350.0
            cav_vol = max(0.2, 1.0 - p * 0.8)
            aby_vol = min(1.0, p)
        else:
            surf_vol = 0.0
            cav_vol = 0.2
            aby_vol = 1.0

        try:
            if self.surface_channel:
                self.surface_channel.set_volume(surf_vol * 0.4)
            if self.cavern_channel:
                self.cavern_channel.set_volume(cav_vol * 0.4)
            if self.abyss_channel:
                self.abyss_channel.set_volume(aby_vol * 0.4)
        except Exception:
            pass

    def toggle_music(self) -> bool:
        self.music_enabled = not self.music_enabled
        self.update_atmosphere(self.current_depth)
        return self.music_enabled

    def toggle_sfx(self) -> bool:
        self.sfx_enabled = not self.sfx_enabled
        return self.sfx_enabled
