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
GAME_SUBTITLE = "KHMER TRADITION × COMPUTER VISION"


# ============================================================
# WINDOW
# ============================================================

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# Old names kept so existing code keeps working.
SCREEN_WIDTH = WINDOW_WIDTH
SCREEN_HEIGHT = WINDOW_HEIGHT

FPS = 60
START_FULLSCREEN = False


# ============================================================
# GAME RULES  (change these to try other rule variants)
# ============================================================

BOARD_SIZE = 4              # 4 x 4 nodes, indexed 0..15 (row * 4 + col)
INITIAL_TIGERS = 4          # tigers start on the corners (1..4)
INITIAL_COWS = 12           # cows the cow player places during PLACEMENT
CAPTURES_TO_WIN = 4         # tigers win after capturing this many cows

TIGER = "tiger"
COW = "cow"

MODE_SINGLE = "single_player"
MODE_TWO = "two_player"

GESTURE_NONE = "none"

# Chance (0..1) that a bot plays a random legal action instead of its best one.
# Keeps the game beatable: a perfect cow bot can never lose.
BOT_MISTAKE_RATE = {"T": 0.20, "C": 0.30}

# Bot thinking delay (seconds) so the player can follow what happened.
BOT_DELAY = 0.7
GAME_OVER_DELAY = 1.2       # let the last animation play before the win screen


# ============================================================
# CAMERA
# ============================================================

CAMERA_INDEX = 0

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

CAMERA_FLIP = True          # mirror image so moving right moves the cursor right
CAMERA_MAX_FAILED_READS = 45
CAMERA_RETRY_INTERVAL = 2.0


# ============================================================
# MEDIAPIPE
# ============================================================

MAX_HANDS = 1

MIN_DETECTION_CONFIDENCE = 0.45
MIN_TRACKING_CONFIDENCE = 0.5
MODEL_COMPLEXITY = 0        # 0 = fastest


# ============================================================
# GESTURES
# ============================================================

# A finger counts as "extended" when its tip is this many times farther from
# the wrist than its knuckle is (about 2.0 when open, 0.7-1.1 when curled).
FINGER_EXTENDED_RATIO = 1.5
THUMB_EXTENDED_RATIO = 1.2

GESTURE_SMOOTHING_FRAMES = 5    # majority vote over the last N camera frames
GESTURE_HOLD_SECONDS = 0.35     # SELECT / CONFIRM / CANCEL need a short hold
GESTURE_COOLDOWN_SECONDS = 0.8  # then the same command waits before repeating

# Part of the camera image that maps onto the board (so you never have to
# reach the very edge of the camera view): (left, top, right, bottom).
CAMERA_ACTIVE_AREA = (0.15, 0.10, 0.85, 0.90)
POINTER_SMOOTHING = 0.45        # 0 = frozen, 1 = no smoothing
HOVER_RELEASE_SECONDS = 1.2     # keep last hovered node this long without a hand


# ============================================================
# ASSETS
# ============================================================

ASSETS_DIR = PROJECT_ROOT / "assets"

IMAGE_DIR = ASSETS_DIR / "images"
ICON_DIR = ASSETS_DIR / "icons"
SOUND_DIR = ASSETS_DIR / "sounds"
FONT_DIR = ASSETS_DIR / "fonts"


# ============================================================
# IMAGE FILES  (missing images fall back to drawn shapes)
# ============================================================

TIGER_IMAGE = ICON_DIR / "tiger.png"
COW_IMAGE = ICON_DIR / "cow.png"

BACKGROUND_IMAGE = IMAGE_DIR / "background.png"


# ============================================================
# SOUND FILES  (missing sounds fall back to synthesized tones)
# ============================================================

SOUND_FILES = {
    "button_click": SOUND_DIR / "button_click.wav",
    "tiger_move": SOUND_DIR / "tiger_move.wav",
    "tiger_roar": SOUND_DIR / "tiger_roar.wav",
    "cow_move": SOUND_DIR / "cow_move.wav",
    "cow_select": SOUND_DIR / "cow_select.wav",
    "tiger_win": SOUND_DIR / "tiger_win.wav",
    "cow_win": SOUND_DIR / "cow_win.wav",
    "game_over": SOUND_DIR / "game_over.wav",
    "error": SOUND_DIR / "error.wav",
}

# Optional looping background music (first file that exists is used).
MUSIC_FILES = [
    SOUND_DIR / "background.ogg",
    SOUND_DIR / "background.mp3",
    SOUND_DIR / "background.wav",
]

# Older names kept for compatibility with existing code.
WIN_SOUND = SOUND_FILES["cow_win"]
LOSE_SOUND = SOUND_FILES["tiger_win"]
DRAW_SOUND = SOUND_DIR / "draw.wav"
CLICK_SOUND = SOUND_FILES["button_click"]
TIGER_SOUND = SOUND_FILES["tiger_roar"]
COW_SOUND = SOUND_FILES["cow_move"]


# ============================================================
# FONT
# ============================================================

FONT_FILE = FONT_DIR / "Poppins-Regular.ttf"
SYSTEM_FONTS = "poppins,segoeui,arial,helveticaneue,dejavusans,liberationsans,freesans"
TITLE_FONT_SIZE = 48
BIG_FONT_SIZE = 40
MEDIUM_FONT_SIZE = 28
SMALL_FONT_SIZE = 20


# ============================================================
# COLORS  (modern neon palette - define every colour here)
# ============================================================

NEON_BG = (5, 8, 22)             # #050816
NEON_PANEL = (11, 16, 38)        # #0B1026
NEON_CYAN = (0, 245, 255)        # #00F5FF
NEON_PURPLE = (139, 92, 246)     # #8B5CF6
NEON_GREEN = (34, 255, 136)      # #22FF88
TIGER_ORANGE = (255, 122, 24)    # #FF7A18
COW_WHITE = (244, 247, 255)      # #F4F7FF
DANGER_RED = (255, 49, 88)       # #FF3158
GOLD = (255, 200, 87)
TEXT_MUTED = (140, 150, 190)

# Old names kept so existing code keeps working.
WHITE = COW_WHITE
BLACK = (0, 0, 0)
GREEN = NEON_GREEN
RED = DANGER_RED
BLUE = NEON_CYAN
YELLOW = GOLD
GRAY = TEXT_MUTED
LIGHT_GRAY = (220, 224, 240)
BACKGROUND_COLOR = NEON_BG
DARK_GREEN = NEON_GREEN

NEON_MODE = True                 # glow effects, animated grid, particles


# ============================================================
# AUDIO
# ============================================================

SOUND_ENABLED = True
DEFAULT_VOLUME = 0.7
SFX_VOLUME = 0.8
MUSIC_VOLUME = 0.5


# ============================================================
# DEBUG
# ============================================================

DEBUG = False                    # F3 toggles it in game

SHOW_CAMERA = True               # small camera preview in the game screen
SHOW_LANDMARKS = True            # draw the hand skeleton on the preview
