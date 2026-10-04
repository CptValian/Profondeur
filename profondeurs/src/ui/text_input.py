"""Champ de saisie de texte minimal pour pygame."""

import pygame


class TextInput:
    def __init__(self, max_len=24):
        self.text = ""
        self.max_len = max_len
        self.active = False

    def open(self, prefill=""):
        self.text = prefill
        self.active = True

    def close(self):
        self.active = False

    def handle_event(self, event) -> bool:
        """Retourne True si Entrée a été pressée (validation)."""
        if not self.active:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                return True
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_ESCAPE:
                self.close()
            else:
                if len(self.text) < self.max_len and event.unicode.isprintable():
                    self.text += event.unicode
        return False
