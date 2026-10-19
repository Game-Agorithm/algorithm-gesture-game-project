"""
Khla Si Ko - Audio Manager

Responsible only for loading and playing sounds.

Every sound in config.SOUND_FILES is loaded from assets/sounds/ when the file
exists; otherwise a short tone is synthesized with NumPy, so the game always
has sound effects and never crashes because a file is missing.
"""

import logging

import numpy as np
import pygame

from src import config

logger = logging.getLogger(__name__)

SAMPLE_RATE = 44100

# Old sound names used elsewhere in the project -> current names.
ALIASES = {
    "win": "cow_win",
    "lose": "tiger_win",
    "draw": "game_over",
    "click": "button_click",
    "tiger": "tiger_roar",
    "cow": "cow_move",
}


def _tone(freq, dur, vol=0.35, wave="sine", end_freq=None):
    """One synthesized note (optionally gliding from freq to end_freq)."""
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    freqs = np.linspace(freq, end_freq or freq, t.size)
    phase = 2 * np.pi * np.cumsum(freqs) / SAMPLE_RATE
    if wave == "square":
        signal = np.sign(np.sin(phase))
    elif wave == "saw":
        signal = 2 * ((phase / (2 * np.pi)) % 1.0) - 1
    else:
        signal = np.sin(phase) + 0.3 * np.sin(2 * phase)
    envelope = np.minimum(1.0, t / 0.01) * np.exp(-3.0 * t / dur)
    return signal * envelope * vol


def _seq(*notes):
    return np.concatenate([_tone(*note) for note in notes])


def _synth_recipes():
    c5, e5, g5, c6 = 523.25, 659.25, 783.99, 1046.5
    return {
        "button_click": _seq((520, 0.05, 0.25)),
        "tiger_move": _seq((180, 0.12, 0.4, "saw", 120)),
        "tiger_roar": _seq((320, 0.55, 0.45, "saw", 70)),
        "cow_move": _seq((330, 0.08, 0.3), (392, 0.08, 0.3)),
        "cow_select": _seq((500, 0.06, 0.3), (700, 0.08, 0.3)),
        "tiger_win": _seq((220, 0.15, 0.4, "saw"), (277, 0.15, 0.4, "saw"),
                          (330, 0.15, 0.4, "saw"), (440, 0.5, 0.45, "saw")),
        "cow_win": _seq((c5, 0.12, 0.35), (e5, 0.12, 0.35), (g5, 0.12, 0.35), (c6, 0.4, 0.4)),
        "game_over": _seq((392, 0.2, 0.35), (330, 0.2, 0.35), (262, 0.45, 0.4)),
        "error": _seq((140, 0.22, 0.35, "square")),
    }


class AudioManager:

    def __init__(self, volume=None):
        """
        Initialize the audio system.
        """

        self.enabled = True      # False when no audio device is available
        self.muted = not config.SOUND_ENABLED

        if volume is None:
            volume = config.SFX_VOLUME

        self.volume = volume

        self.sounds = {}

        self._initialize_mixer()
        self._load_sounds()
        self._start_music()

    # ========================================================
    # INITIALIZE
    # ========================================================

    def _initialize_mixer(self):

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

        except pygame.error as error:

            logger.warning("Audio initialization failed: %s", error)

            self.enabled = False

    # ========================================================
    # LOAD SOUNDS
    # ========================================================

    def _load_sounds(self):

        if not self.enabled:
            return

        synthesized = None
        for name, path in config.SOUND_FILES.items():
            sound = self._load(path)
            if sound is None:
                if synthesized is None:
                    synthesized = _synth_recipes()
                sound = self._synthesize(synthesized.get(name))
            self.sounds[name] = sound

    # ========================================================
    # LOAD ONE SOUND
    # ========================================================

    def _load(self, path):

        try:

            if not path.exists():
                return None

            sound = pygame.mixer.Sound(str(path))

            sound.set_volume(self.volume)

            return sound

        except (pygame.error, OSError) as error:

            logger.warning("Could not load sound %s: %s", path, error)

            return None

    def _synthesize(self, wave):
        """Turn a NumPy wave into a pygame Sound (None if that fails)."""
        if wave is None:
            return None
        try:
            channels = pygame.mixer.get_init()[2]
            data = (np.clip(wave, -1, 1) * 32767).astype(np.int16)
            if channels > 1:
                data = np.column_stack([data] * channels)
            sound = pygame.mixer.Sound(buffer=np.ascontiguousarray(data).tobytes())
            sound.set_volume(self.volume)
            return sound
        except (pygame.error, ValueError, TypeError) as error:
            logger.warning("Could not synthesize sound: %s", error)
            return None

    # ========================================================
    # BACKGROUND MUSIC (optional file)
    # ========================================================

    def _start_music(self):

        if not self.enabled:
            return

        for path in config.MUSIC_FILES:
            if path.exists():
                try:
                    pygame.mixer.music.load(str(path))
                    pygame.mixer.music.set_volume(config.MUSIC_VOLUME)
                    if not self.muted:
                        pygame.mixer.music.play(-1)
                    return
                except pygame.error as error:
                    logger.warning("Could not play music %s: %s", path, error)

    # ========================================================
    # PLAY
    # ========================================================

    def play(self, name):

        if not self.enabled or self.muted:
            return

        sound = self.sounds.get(ALIASES.get(name, name))

        if sound is None:
            return

        sound.play()

    # ========================================================
    # GAME SOUNDS
    # ========================================================

    def play_win(self):
        self.play("cow_win")

    def play_lose(self):
        self.play("tiger_win")

    def play_draw(self):
        self.play("game_over")

    def play_click(self):
        self.play("button_click")

    def play_tiger(self):
        self.play("tiger_roar")

    def play_cow(self):
        self.play("cow_move")

    # ========================================================
    # MUTE / VOLUME
    # ========================================================

    def set_muted(self, muted):

        self.muted = bool(muted)

        if self.enabled and pygame.mixer.get_init():
            if self.muted:
                pygame.mixer.stop()
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()
                if config.MUSIC_FILES and not pygame.mixer.music.get_busy():
                    self._start_music()

    def toggle_muted(self):
        self.set_muted(not self.muted)
        return self.muted

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
