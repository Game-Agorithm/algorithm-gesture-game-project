"""
Khla Si Ko - Game Configuration

This file contains shared settings used by all modules.
Do not put game logic here.
"""

from pathlib import Path


# ============================================================
# PROJECT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

GAME_TITLE = "Khla Si Ko - Tiger Eat Cow"


# ============================================================
# WINDOW
# ============================================================

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 750

FPS = 60


# ============================================================
# GAME
# ============================================================

WINNING_SCORE = 5

TIGER = "tiger"
COW = "cow"

GESTURE_NONE = "none"


# ============================================================
# GAME RESULTS
# ============================================================

RESULT_PLAYER_WIN = "player_win"
RESULT_COMPUTER_WIN = "computer_win"
RESULT_DRAW = "draw"


# ============================================================
# CAMERA
# ============================================================

CAMERA_INDEX = 0

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480


# ============================================================
# MEDIAPIPE
# ============================================================

MAX_HANDS = 1

MIN_DETECTION_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5


# ============================================================
# ASSETS
# ============================================================

ASSETS_DIR = PROJECT_ROOT / "assets"

IMAGE_DIR = ASSETS_DIR / "images"
ICON_DIR = ASSETS_DIR / "icons"
SOUND_DIR = ASSETS_DIR / "sounds"
FONT_DIR = ASSETS_DIR / "fonts"


# ============================================================
# IMAGE FILES
# ============================================================

TIGER_IMAGE = IMAGE_DIR / "tiger.png"
COW_IMAGE = IMAGE_DIR / "cow.png"

BACKGROUND_IMAGE = IMAGE_DIR / "background.png"


# ============================================================
# SOUND FILES
# ============================================================

WIN_SOUND = SOUND_DIR / "win.wav"
LOSE_SOUND = SOUND_DIR / "lose.wav"
DRAW_SOUND = SOUND_DIR / "draw.wav"
CLICK_SOUND = SOUND_DIR / "click.wav"

TIGER_SOUND = SOUND_DIR / "tiger.wav"
COW_SOUND = SOUND_DIR / "cow.wav"


# ============================================================
# FONT
# ============================================================

FONT_FILE = FONT_DIR / "game_font.ttf"

TITLE_FONT_SIZE = 48
BIG_FONT_SIZE = 40
MEDIUM_FONT_SIZE = 28
SMALL_FONT_SIZE = 20


# ============================================================
# COLORS
# ============================================================

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

GREEN = (40, 180, 90)
RED = (220, 60, 60)

BLUE = (50, 120, 220)
YELLOW = (240, 200, 50)

GRAY = (100, 100, 100)
LIGHT_GRAY = (220, 220, 220)

BACKGROUND_COLOR = (235, 245, 235)

DARK_GREEN = (30, 100, 60)


# ============================================================
# AUDIO
# ============================================================

DEFAULT_VOLUME = 0.7


# ============================================================
# DEBUG
# ============================================================

DEBUG = True

SHOW_CAMERA = True
SHOW_LANDMARKS = True