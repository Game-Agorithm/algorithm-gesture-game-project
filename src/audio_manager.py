"""
Khla Si Ko - Audio Manager

Responsible only for loading and playing sounds.
"""

import pygame

from src import config


class AudioManager:

    def __init__(self, volume=None):
        """
        Initialize the audio system.
        """

        self.enabled = True

        if volume is None:
            volume = config.DEFAULT_VOLUME

        self.volume = volume

        self.sounds = {}

        self._initialize_mixer()
        self._load_sounds()

    # ========================================================
    # INITIALIZE
    # ========================================================

    def _initialize_mixer(self):

        try:
            pygame.mixer.init()

        except pygame.error as error:

            print("Audio initialization failed:")
            print(error)

            self.enabled = False

    # ========================================================
    # LOAD SOUNDS
    # ========================================================

    def _load_sounds(self):

        if not self.enabled:
            return

        self.sounds["win"] = self._load(
            config.WIN_SOUND
        )

        self.sounds["lose"] = self._load(
            config.LOSE_SOUND
        )

        self.sounds["draw"] = self._load(
            config.DRAW_SOUND
        )

        self.sounds["click"] = self._load(
            config.CLICK_SOUND
        )

        self.sounds["tiger"] = self._load(
            config.TIGER_SOUND
        )

        self.sounds["cow"] = self._load(
            config.COW_SOUND
        )

    # ========================================================
    # LOAD ONE SOUND
    # ========================================================

    def _load(self, path):

        try:

            if not path.exists():

                if config.DEBUG:
                    print(f"[Audio] File not found: {path}")

                return None

            sound = pygame.mixer.Sound(str(path))

            sound.set_volume(self.volume)

            return sound

        except pygame.error as error:

            print(f"[Audio] Could not load: {path}")
            print(error)

            return None

    # ========================================================
    # PLAY
    # ========================================================

    def play(self, name):

        if not self.enabled:
            return

        sound = self.sounds.get(name)

        if sound is None:
            return

        sound.play()

    # ========================================================
    # GAME SOUNDS
    # ========================================================

    def play_win(self):
        self.play("win")

    def play_lose(self):
        self.play("lose")

    def play_draw(self):
        self.play("draw")

    def play_click(self):
        self.play("click")

    def play_tiger(self):
        self.play("tiger")

    def play_cow(self):
        self.play("cow")

    # ========================================================
    # VOLUME
    # ========================================================

    def set_volume(self, volume):

        volume = max(0.0, min(1.0, volume))

        self.volume = volume

        for sound in self.sounds.values():

            if sound is not None:
                sound.set_volume(volume)

    # ========================================================
    # STOP
    # ========================================================

    def stop_all(self):

        if self.enabled:
            pygame.mixer.stop()

    # ========================================================
    # CLEAN UP
    # ========================================================

    def close(self):

        if self.enabled:
            pygame.mixer.quit()

            self.enabled = False