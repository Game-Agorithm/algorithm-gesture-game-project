"""Pygame display for the Khla Si Ko board game (modern neon Khmer style).

The renderer only DRAWS. It reads the GameState it is given and never changes
it, and it contains no game rules.

Typical frame (see main.py):
    renderer.draw_game(state, message, gesture, pointer, ...)   # or a menu screen
    renderer.draw_pause() / renderer.draw_game_over(state)      # optional overlays
    renderer.present()
"""

import logging
import math
import random
import textwrap

import pygame

from src import config
from src.game_rules import KhlaSiKoRules

logger = logging.getLogger(__name__)

GESTURE_LABELS = {
    "NONE": "—", "UNKNOWN": "?", "POINT": "POINT", "OPEN_PALM": "OPEN PALM",
    "THUMBS_UP": "THUMBS UP", "FIST": "FIST",
}
GESTURE_COLORS = {
    "POINT": config.NEON_CYAN, "OPEN_PALM": config.NEON_GREEN,
    "THUMBS_UP": config.GOLD, "FIST": config.DANGER_RED,
}


def _scale(color, k):
    return tuple(max(0, min(255, int(c * k))) for c in color)


def _ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


class Renderer:
    BOARD_LEFT = 130
    BOARD_TOP = 160
    BOARD_SIZE = 420
    NODE_RADIUS = 34
    PIECE_SIZE = 74
    CAMERA_PREVIEW_SIZE = (264, 198)

    def __init__(self, width=config.WINDOW_WIDTH, height=config.WINDOW_HEIGHT):
        self.width = width
        self.height = height
        flags = pygame.SCALED | pygame.RESIZABLE
        if config.START_FULLSCREEN:
            flags |= pygame.FULLSCREEN
        self.screen = pygame.display.set_mode((width, height), flags)
        pygame.display.set_caption(config.GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.board_step = self.BOARD_SIZE / (KhlaSiKoRules.BOARD_SIZE - 1)

        self._load_fonts()
        self.title_font = self._font(config.TITLE_FONT_SIZE)
        self.big_font = self._font(config.BIG_FONT_SIZE)
        self.medium_font = self._font(config.MEDIUM_FONT_SIZE)
        self.small_font = self._font(config.SMALL_FONT_SIZE, bold=False)

        self._text_cache = {}
        self._glow_cache = {}
        self._image_cache = {}
        self._pieces = self._load_piece_images()
        self.game_style = config.DEFAULT_GAME_STYLE
        self.palette = config.GAME_STYLES[self.game_style]
        self._style_previews = {}
        self.bg = self._build_background()
        self.board_surface = self._build_board_surface()

        # animation state
        self.t = 0.0
        self.dt = 0.016
        self._last_ticks = pygame.time.get_ticks()
        self.move_anim = None
        self.pops = {}
        self.fades = []
        self.error_flash = None
        self.flash_t0 = -10.0
        self.particles = []
        self.buttons = []
        self._rng = random.Random(3)

    def set_style(self, style):
        if style not in config.GAME_STYLES:
            raise ValueError(f"Unknown game style: {style!r}")
        if style == self.game_style:
            return
        self.game_style = style
        self.palette = config.GAME_STYLES[style]
        self.bg = self._build_background()
        self.board_surface = self._build_board_surface()
        self._glow_cache.clear()

    # ==================================================================
    # Fonts and text
    # ==================================================================

    def _load_fonts(self):
        self.latin_path = None
        if config.FONT_FILE.exists():
            self.latin_path = str(config.FONT_FILE)
        else:
            self.latin_path = pygame.font.match_font(config.SYSTEM_FONTS)
        self._fonts = {}

    def _font(self, size, bold=True):
        key = (size, bold)
        if key not in self._fonts:
            try:
                font = pygame.font.Font(self.latin_path, size)
            except (pygame.error, OSError):
                font = pygame.font.Font(None, int(size * 1.2))
            font.set_bold(bold)
            self._fonts[key] = font
        return self._fonts[key]

    def _render(self, text, font, color):
        key = (text, id(font), color)
        img = self._text_cache.get(key)
        if img is None:
            img = font.render(text, True, color)
            if len(self._text_cache) > 700:
                self._text_cache.clear()
            self._text_cache[key] = img
        return img

    def _text(self, text, position, color=None, font=None, anchor="topleft", glow=False):
        """Draw text. ``anchor`` is any pygame Rect attribute (center, midtop...)."""
        color = self.palette["text"] if color is None else color
        font = font or self.small_font
        img = self._render(text, font, color)
        rect = img.get_rect(**{anchor: position})
        if glow:
            halo = self._render(text, font, _scale(color, 0.6)).copy()
            halo.set_alpha(70)
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-3, 3), (3, -3)):
                self.screen.blit(halo, rect.move(dx, dy))
        self.screen.blit(img, rect)
        return rect

    # ==================================================================
    # Pre-built surfaces
    # ==================================================================

    def _load_piece_images(self):
        images = {}
        for style, palette in config.GAME_STYLES.items():
            for piece, asset_key in (("T", "tiger_image"), ("C", "cow_image")):
                path = palette[asset_key]
                try:
                    images[(style, piece)] = pygame.image.load(str(path)).convert_alpha()
                except (pygame.error, FileNotFoundError, OSError) as error:
                    logger.info("Optional %s image %s unavailable (%s); using a drawn token.",
                                style, path, error)
                    images[(style, piece)] = None
        return images

    def _piece_image(self, piece, size):
        key = (self.game_style, piece, size)
        if key not in self._image_cache:
            source = self._pieces.get((self.game_style, piece))
            if source is not None:
                img = pygame.transform.smoothscale(source, (size, size))
            elif self.game_style == config.GAME_STYLE_JUNGLE:
                img = pygame.Surface((size, size), pygame.SRCALPHA)
                radius = size // 2 - 3
                base = self.palette["tiger"] if piece == "T" else self.palette["cow"]
                pygame.draw.circle(img, (35, 43, 28, 100), (size // 2 + 2, size // 2 + 4), radius)
                pygame.draw.circle(img, base, (size // 2, size // 2), radius)
                border = (83, 56, 37) if piece == "T" else (129, 98, 64)
                pygame.draw.circle(img, border, (size // 2, size // 2), radius, max(2, size // 18))
                if piece == "T":
                    for offset in (-size // 5, size // 5):
                        pygame.draw.line(img, (50, 43, 31), (size // 2 + offset - 4, size // 4),
                                         (size // 2 + offset + 4, size * 3 // 4), max(2, size // 12))
                else:
                    pygame.draw.ellipse(img, (121, 80, 53), (size // 4, size // 4, size // 5, size // 4))
                    pygame.draw.ellipse(img, (121, 80, 53), (size // 2, size // 2, size // 4, size // 5))
                label = self._render(piece, self._font(size // 3), (44, 42, 31))
                img.blit(label, label.get_rect(center=(size // 2, size // 2)))
            else:                                   # fallback: simple drawn token
                img = pygame.Surface((size, size), pygame.SRCALPHA)
                color = config.TIGER_ORANGE if piece == "T" else config.COW_WHITE
                pygame.draw.circle(img, color, (size // 2, size // 2), size // 2 - 3)
                pygame.draw.circle(img, _scale(color, 0.5), (size // 2, size // 2), size // 2 - 3, 3)
                label = self._render(piece, self._font(size // 2), self.palette["ground"])
                img.blit(label, label.get_rect(center=(size // 2, size // 2)))
            self._image_cache[key] = img
        return self._image_cache[key]

    def _glow_surface(self, radius, color):
        key = (radius, color)
        if key not in self._glow_cache:
            surf = pygame.Surface((radius * 2, radius * 2))
            for r in range(radius, 0, -2):
                k = (1 - r / radius) ** 2
                pygame.draw.circle(surf, _scale(color, k * 0.9), (radius, radius), r)
            self._glow_cache[key] = surf
        return self._glow_cache[key]

    def _glow(self, center, radius, color, strength=1.0):
        if not self.palette["glow"]:
            return
        surf = self._glow_surface(radius, color)
        if strength < 1.0:
            surf = surf.copy()
            surf.fill(_scale((255, 255, 255), max(0.0, strength)), special_flags=pygame.BLEND_RGB_MULT)
        self.screen.blit(surf, (int(center[0]) - radius, int(center[1]) - radius),
                         special_flags=pygame.BLEND_RGB_ADD)

    def _ring(self, center, radius, color, width=3, glow=True):
        if glow and config.NEON_MODE and self.palette["glow"]:
            self._glow(center, int(radius) + 26, color, 0.8)
        pygame.draw.circle(self.screen, color, center, int(radius), width)

    def _build_background(self):
        if self.game_style == config.GAME_STYLE_JUNGLE:
            return self._build_jungle_background()
        bg = pygame.Surface((self.width, self.height))
        for y in range(self.height):
            k = y / self.height
            color = tuple(int(a + (b - a) * k) for a, b in zip(config.NEON_BG, (14, 8, 38)))
            pygame.draw.line(bg, color, (0, y), (self.width, y))
        # Khmer-inspired ornamental border: diamonds + dots along top and bottom
        motif = pygame.Surface((self.width, 22), pygame.SRCALPHA)
        for x in range(20, self.width, 36):
            pygame.draw.polygon(motif, (*config.NEON_PURPLE, 150),
                                [(x, 3), (x + 9, 11), (x, 19), (x - 9, 11)])
            pygame.draw.polygon(motif, (*config.NEON_CYAN, 110),
                                [(x, 8), (x + 4, 11), (x, 14), (x - 4, 11)])
            pygame.draw.circle(motif, (*config.NEON_PURPLE, 90), (x + 18, 11), 2)
        pygame.draw.line(motif, (*config.NEON_PURPLE, 70), (0, 11), (self.width, 11), 1)
        bg.blit(motif, (0, 0))
        bg.blit(pygame.transform.flip(motif, False, True), (0, self.height - 22))
        return bg

    def _build_style_preview(self, style, size):
        if style == config.GAME_STYLE_JUNGLE:
            preview = pygame.transform.smoothscale(self._build_jungle_background(), size)
            return preview

        preview = pygame.Surface(size)
        for y in range(size[1]):
            k = y / max(1, size[1])
            color = tuple(int(a + (b - a) * k) for a, b in zip((5, 8, 22), (15, 9, 42)))
            pygame.draw.line(preview, color, (0, y), (size[0], y))
        for x in range(20, size[0], 32):
            pygame.draw.line(preview, (0, 87, 106), (x, 12), (x, size[1] - 12), 1)
        for y in range(20, size[1], 28):
            pygame.draw.line(preview, (0, 87, 106), (12, y), (size[0] - 12, y), 1)
        pygame.draw.rect(preview, (23, 28, 60), (size[0] // 2 - 70, 35, 140, 110), 2, border_radius=10)
        pygame.draw.line(preview, config.NEON_CYAN, (size[0] // 2 - 48, 55), (size[0] // 2 + 48, 55), 3)
        pygame.draw.line(preview, config.NEON_CYAN, (size[0] // 2 - 48, 55), (size[0] // 2 - 48, 122), 3)
        pygame.draw.line(preview, config.NEON_CYAN, (size[0] // 2 + 48, 55), (size[0] // 2 + 48, 122), 3)
        pygame.draw.line(preview, config.NEON_CYAN, (size[0] // 2 - 48, 122), (size[0] // 2 + 48, 122), 3)
        pygame.draw.circle(preview, config.NEON_PURPLE, (size[0] // 2, size[1] // 2), 8)
        return preview

    def draw_style_select(self, selected_style, selected_button=0):
        self._begin_frame()
        self._text("SELECT YOUR GAME STYLE", (self.width // 2, 72),
                   self.palette["accent"], self._font(46), "center", glow=self.palette["glow"])
        self._text("Choose your environment", (self.width // 2, 116),
                   self.palette["muted"], self._font(20, False), "center")

        card_width = min(500, (self.width - 180) // 2)
        card_height = min(390, self.height - 245)
        gap = max(28, min(56, (self.width - card_width * 2) // 3))
        left = (self.width - card_width * 2 - gap) // 2
        top = 155
        styles = (
            (config.GAME_STYLE_MODERN, "MODERN TECH", "Neon • Futuristic • Digital"),
            (config.GAME_STYLE_JUNGLE, "NATURAL MOUNTAIN JUNGLE", "Mountain • Forest • Adventure"),
        )
        for index, (style, title, description) in enumerate(styles):
            rect = pygame.Rect(left + index * (card_width + gap), top, card_width, card_height)
            is_selected = style == selected_style
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            accent = config.GAME_STYLES[style]["accent"]
            panel = config.GAME_STYLES[style]["panel"]
            if hovered or is_selected:
                self._glow(rect.center, card_width // 2, accent, 0.35 if hovered else 0.5)
            pygame.draw.rect(self.screen, panel, rect, border_radius=22)
            pygame.draw.rect(self.screen, accent if is_selected or hovered else _scale(accent, 0.55),
                             rect, 4 if is_selected else 2, border_radius=22)

            preview_rect = pygame.Rect(rect.x + 18, rect.y + 18, rect.w - 36, min(205, rect.h - 145))
            cache_key = (style, preview_rect.size)
            preview = self._style_previews.get(cache_key)
            if preview is None:
                preview = self._build_style_preview(style, preview_rect.size)
                self._style_previews[cache_key] = preview
            self.screen.blit(preview, preview_rect)
            for piece, x in (("T", preview_rect.x + preview_rect.w // 3),
                             ("C", preview_rect.x + preview_rect.w * 2 // 3)):
                image = self._pieces.get((style, piece))
                if image is not None:
                    icon_size = min(58, preview_rect.h // 3)
                    image_key = (style, piece, icon_size)
                    icon = self._image_cache.get(image_key)
                    if icon is None:
                        icon = pygame.transform.smoothscale(image, (icon_size, icon_size))
                        self._image_cache[image_key] = icon
                    center = (x, preview_rect.y + preview_rect.h * 3 // 4)
                    pygame.draw.circle(self.screen, config.GAME_STYLES[style]["panel"],
                                       center, icon_size // 2 + 5)
                    self.screen.blit(icon, icon.get_rect(center=center))
            pygame.draw.rect(self.screen, accent, preview_rect, 2, border_radius=12)
            self._text(title, (rect.centerx, preview_rect.bottom + 32),
                       config.GAME_STYLES[style]["text"], self._font(25), "center")
            self._text(description, (rect.centerx, preview_rect.bottom + 65),
                       config.GAME_STYLES[style]["muted"], self._font(17, False), "center")
            label = "✓ SELECTED" if is_selected else "SELECT"
            self._button(style, (rect.centerx - 100, rect.bottom - 64, 200, 46), label,
                         is_selected or selected_button == index, accent)

        button_y = self.height - 78
        self._button("back", (self.width // 2 - 190, button_y, 150, 48),
                     "BACK", selected_button == 2, self.palette["gold"])
        self._button("continue", (self.width // 2 + 40, button_y, 190, 48),
                     "CONTINUE", selected_button == 3, self.palette["highlight"], "play")

    def _build_jungle_background(self):
        base_width, base_height = 1280, 720
        bg = pygame.Surface((base_width, base_height))
        horizon = int(base_height * 0.58)
        top = self.palette["background_top"]
        bottom = self.palette["background_bottom"]
        for y in range(base_height):
            if y <= horizon:
                k = y / max(1, horizon)
                color = tuple(int(a + (b - a) * k) for a, b in zip(top, (205, 218, 165)))
            else:
                k = (y - horizon) / max(1, self.height - horizon)
                color = tuple(int(a + (b - a) * k) for a, b in zip((102, 137, 72), bottom))
            pygame.draw.line(bg, color, (0, y), (base_width, y))

        sun = pygame.Surface((240, 240), pygame.SRCALPHA)
        for radius in range(118, 0, -4):
            alpha = int(1 + 16 * (1 - radius / 118) ** 2)
            pygame.draw.circle(sun, (255, 238, 168, alpha), (120, 120), radius)
        bg.blit(sun, (int(base_width * 0.67), 55), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(bg, (255, 232, 158), (int(base_width * 0.76), 150), 32)

        pygame.draw.polygon(bg, (133, 157, 132), [
            (0, 380), (0, 300), (140, 180), (245, 295), (370, 135),
            (530, 315), (705, 170), (870, 320), (1030, 205), (1280, 335),
            (1280, 430),
        ])
        pygame.draw.polygon(bg, (79, 119, 91), [
            (0, 408), (115, 284), (220, 369), (390, 238), (565, 402),
            (760, 265), (925, 397), (1080, 278), (1280, 403), (1280, 465),
        ])
        pygame.draw.polygon(bg, (57, 93, 65), [
            (0, 448), (105, 355), (210, 420), (360, 328), (520, 450),
            (690, 354), (850, 448), (1015, 335), (1160, 425), (1280, 370),
            (1280, 490),
        ])

        ground_y = int(base_height * 0.62)
        pygame.draw.rect(bg, (83, 112, 61), (0, ground_y, base_width, base_height - ground_y))
        pygame.draw.ellipse(bg, (118, 130, 72), (-130, ground_y - 20, base_width + 240, 260))
        pygame.draw.ellipse(bg, (92, 111, 58), (120, ground_y + 60, 900, 260))

        # Layered forest canopy behind the game field.
        rng = random.Random(19)
        for layer, (base_y, color, count, radius_range) in enumerate((
            (ground_y + 5, (54, 92, 57), 38, (22, 52)),
            (ground_y + 34, (35, 73, 48), 28, (28, 58)),
        )):
            for i in range(count):
                x = int(i * base_width / max(1, count - 1) + rng.randint(-18, 18))
                radius = rng.randint(*radius_range)
                y = base_y - radius // 2 + rng.randint(-12, 12)
                pygame.draw.rect(bg, (76, 72, 45), (x - 5, y + radius // 2, 10, radius * 2))
                pygame.draw.circle(bg, color, (x, y), radius)
                pygame.draw.circle(bg, _scale(color, 1.13), (x - radius // 3, y - radius // 3), radius // 2)

        # Foreground foliage frames the board without crossing the play area.
        for side in (0, 1):
            edge_x = 0 if side == 0 else base_width
            direction = 1 if side == 0 else -1
            for i in range(8):
                y = ground_y + 35 + i * 38
                reach = 90 + (i % 3) * 24
                pygame.draw.line(bg, (48, 76, 43), (edge_x, y), (edge_x + direction * reach, y - 18), 7)
                for leaf in range(4):
                    lx = edge_x + direction * (reach * (leaf + 1) // 5)
                    ly = y - 18 - leaf * 3
                    pygame.draw.ellipse(bg, (57 + leaf * 4, 105 + leaf * 5, 53), (lx - 18, ly - 8, 38, 16))

        # Scatter quiet stones and grass near the bottom edge.
        for i in range(34):
            x = rng.randrange(base_width)
            y = rng.randrange(int(base_height * 0.84), base_height)
            color = rng.choice(((107, 111, 82), (79, 94, 65), (128, 119, 87)))
            pygame.draw.ellipse(bg, color, (x, y, rng.randrange(8, 24), rng.randrange(4, 10)))
        for i in range(90):
            x = rng.randrange(base_width)
            y = rng.randrange(ground_y, base_height)
            pygame.draw.line(bg, (51, 91, 47), (x, y), (x + rng.randrange(-4, 5), y - rng.randrange(4, 12)), 2)
        return bg if (self.width, self.height) == bg.get_size() else pygame.transform.smoothscale(bg, (self.width, self.height))

    def _board_frame_rect(self):
        return pygame.Rect(self.BOARD_LEFT - 55, self.BOARD_TOP - 55,
                           self.BOARD_SIZE + 110, self.BOARD_SIZE + 110)

    def _build_board_surface(self):
        """Build a reusable board frame in the active environment style."""
        frame = self._board_frame_rect()
        surf = pygame.Surface(frame.size, pygame.SRCALPHA)
        if self.game_style == config.GAME_STYLE_JUNGLE:
            pygame.draw.rect(surf, (61, 78, 45, 245), surf.get_rect(), border_radius=26)
            pygame.draw.rect(surf, (118, 105, 68, 255), surf.get_rect().inflate(-18, -18), border_radius=20)
            pygame.draw.rect(surf, (79, 106, 58, 255), surf.get_rect().inflate(-32, -32), border_radius=18)
            rng = random.Random(41)
            for _ in range(160):
                x = rng.randrange(24, surf.get_width() - 24)
                y = rng.randrange(24, surf.get_height() - 24)
                radius = rng.choice((1, 2, 3))
                pygame.draw.circle(surf, rng.choice(((127, 119, 83, 110), (54, 84, 48, 130), (147, 142, 97, 90))),
                                   (x, y), radius)
            pygame.draw.rect(surf, self.palette["frame"], surf.get_rect(), 5, border_radius=26)
            pygame.draw.rect(surf, (58, 91, 50), surf.get_rect().inflate(-13, -13), 2, border_radius=21)
            ox, oy = frame.x, frame.y
            last = KhlaSiKoRules.BOARD_SIZE - 1
            for index in range(KhlaSiKoRules.BOARD_SIZE):
                for a, b in ((self.board_node(index, 0), self.board_node(index, last)),
                             (self.board_node(0, index), self.board_node(last, index))):
                    a = (a[0] - ox, a[1] - oy)
                    b = (b[0] - ox, b[1] - oy)
                    pygame.draw.line(surf, (63, 80, 48, 160), a, b, 8)
                    pygame.draw.line(surf, self.palette["grid"], a, b, 3)
            return surf

        pygame.draw.rect(surf, (*config.NEON_PANEL, 235), surf.get_rect(), border_radius=26)
        for width, alpha in ((9, 50), (5, 110)):
            pygame.draw.rect(surf, (*config.NEON_PURPLE, alpha), surf.get_rect(), width, border_radius=26)
        pygame.draw.rect(surf, config.NEON_PURPLE, surf.get_rect(), 2, border_radius=26)
        ox, oy = frame.x, frame.y
        last = KhlaSiKoRules.BOARD_SIZE - 1
        for index in range(KhlaSiKoRules.BOARD_SIZE):
            for a, b in ((self.board_node(index, 0), self.board_node(index, last)),
                         (self.board_node(0, index), self.board_node(last, index))):
                a = (a[0] - ox, a[1] - oy)
                b = (b[0] - ox, b[1] - oy)
                pygame.draw.line(surf, (*config.NEON_CYAN, 45), a, b, 11)
                pygame.draw.line(surf, (*config.NEON_CYAN, 120), a, b, 5)
                pygame.draw.line(surf, _scale(config.NEON_CYAN, 0.9), a, b, 2)
        return surf

    # ==================================================================
    # Geometry (kept from the original renderer)
    # ==================================================================

    def board_node(self, row, col):
        return (
            round(self.BOARD_LEFT + col * self.board_step),
            round(self.BOARD_TOP + row * self.board_step),
        )

    def board_position_at(self, point):
        if point is None:
            return None
        x, y = point
        col = round((x - self.BOARD_LEFT) / self.board_step)
        row = round((y - self.BOARD_TOP) / self.board_step)
        if not KhlaSiKoRules.is_valid_position(row, col):
            return None
        node_x, node_y = self.board_node(row, col)
        if (x - node_x) ** 2 + (y - node_y) ** 2 > 62 ** 2:
            return None
        return row, col

    def camera_point_to_screen(self, x, y):
        """Camera coordinates (0..1) -> screen pixels.

        The active camera area maps to the full window for button navigation.
        """
        left, top, right, bottom = config.CAMERA_ACTIVE_AREA
        nx = min(1.0, max(0.0, (x - left) / (right - left)))
        ny = min(1.0, max(0.0, (y - top) / (bottom - top)))
        return (
            round(nx * (self.width - 1)),
            round(ny * (self.height - 1)),
        )

    # ==================================================================
    # Frame control and effects
    # ==================================================================

    def _begin_frame(self):
        ticks = pygame.time.get_ticks()
        self.dt = min(0.1, (ticks - self._last_ticks) / 1000.0)
        self._last_ticks = ticks
        self.t = ticks / 1000.0
        self.buttons = []
        self.screen.blit(self.bg, (0, 0))
        if self.game_style == config.GAME_STYLE_JUNGLE:
            self._draw_jungle_ambience()
        elif config.NEON_MODE:                      # animated grid
            grid = (22, 30, 70)
            for x in range(0, self.width, 64):
                pygame.draw.line(self.screen, grid, (x, 22), (x, self.height - 22))
            offset = (self.t * 18) % 64
            for y in range(int(offset) + 22, self.height - 22, 64):
                pygame.draw.line(self.screen, grid, (0, y), (self.width, y))

    def _draw_jungle_ambience(self):
        for index in range(7):
            direction = -1 if index % 2 else 1
            x = int((index * 197 + self.t * (8 + index % 3) * direction) % self.width)
            y = 165 + (index * 83) % 390 + int(5 * math.sin(self.t * 0.7 + index))
            color = (220, 208, 130) if index % 3 == 0 else (83, 125, 61)
            pygame.draw.ellipse(self.screen, color, (x, y, 7, 3))

    def present(self):
        self._update_particles()
        pygame.display.flip()

    def tick(self, fps=config.FPS):
        self.clock.tick(fps)

    def toggle_fullscreen(self):
        pygame.display.toggle_fullscreen()

    def burst(self, point, color, count=30, speed=260):
        for _ in range(count):
            angle = self._rng.uniform(0, math.tau)
            v = self._rng.uniform(speed * 0.3, speed)
            life = self._rng.uniform(0.4, 0.9)
            self.particles.append([point[0], point[1], math.cos(angle) * v, math.sin(angle) * v,
                                   life, life, color, self._rng.uniform(2, 5)])

    def _update_particles(self):
        alive = []
        for p in self.particles:
            p[0] += p[2] * self.dt
            p[1] += p[3] * self.dt
            p[3] += 240 * self.dt
            p[4] -= self.dt
            if p[4] > 0:
                k = p[4] / p[5]
                self._glow((int(p[0]), int(p[1])), 10, p[6], k)
                pygame.draw.circle(self.screen, p[6], (int(p[0]), int(p[1])), max(1, int(p[7] * k)))
                alive.append(p)
        self.particles = alive[:400]
        age = self.t - self.flash_t0
        if age < 0.25:
            veil = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            veil.fill((*config.TIGER_ORANGE, int(70 * (1 - age / 0.25))))
            self.screen.blit(veil, (0, 0))

    def notify(self, event):
        """Start the animation for a GameState.last_event."""
        if not event:
            return
        kind = event["type"]
        if kind == "place":
            self.pops[event["to"]] = self.t
        elif kind in ("move", "capture"):
            self.move_anim = {"piece": event["piece"], "start": event["start"],
                              "end": event["to"], "t0": self.t, "dur": 0.28}
            if kind == "capture" and event.get("captured"):
                self.fades.append({"pos": event["captured"], "t0": self.t})
                self.burst(self.board_node(*event["captured"]), config.DANGER_RED, 36)
                self.burst(self.board_node(*event["to"]), config.TIGER_ORANGE, 24)
                self.flash_t0 = self.t

    def flash_error(self, position):
        if position is not None:
            self.error_flash = (position, self.t)

    # ==================================================================
    # Buttons
    # ==================================================================

    def button_at(self, point):
        for button_id, rect in self.buttons:
            if rect.collidepoint(point):
                return button_id
        return None

    def draw_pointer(self, point, hold_progress=0.0):
        if point is None:
            return
        pygame.draw.circle(self.screen, config.POINTER_BLUE, point, 10)
        pygame.draw.circle(self.screen, config.COW_WHITE, point, 14, 2)
        if hold_progress > 0:
            pygame.draw.arc(
                self.screen,
                config.POINTER_BLUE,
                pygame.Rect(point[0] - 20, point[1] - 20, 40, 40),
                -math.pi / 2,
                -math.pi / 2 + math.tau * min(1.0, hold_progress),
                4,
            )

    def _glyph(self, kind, center, color, size=11):
        x, y = center
        if kind == "play":
            pygame.draw.polygon(self.screen, color, [(x - size * .6, y - size), (x - size * .6, y + size), (x + size, y)])
        elif kind == "exit":
            pygame.draw.line(self.screen, color, (x - size, y - size), (x + size, y + size), 4)
            pygame.draw.line(self.screen, color, (x - size, y + size), (x + size, y - size), 4)
        elif kind == "gear":
            pygame.draw.circle(self.screen, color, center, size, 4)
            for a in range(0, 360, 45):
                d = math.radians(a)
                pygame.draw.line(self.screen, color, (x + math.cos(d) * size, y + math.sin(d) * size),
                                 (x + math.cos(d) * (size + 5), y + math.sin(d) * (size + 5)), 4)
        elif kind in ("single", "two"):
            for dx in ((0,) if kind == "single" else (-size, size)):
                pygame.draw.circle(self.screen, color, (x + dx, y - size // 2), size // 2 + 1)
                pygame.draw.arc(self.screen, color, (x + dx - size, y + 1, size * 2, size * 1.4), 0, math.pi, 4)
        elif kind == "restart":
            pygame.draw.arc(self.screen, color, (x - size, y - size, size * 2, size * 2), 0.6, 5.6, 4)
            pygame.draw.polygon(self.screen, color, [(x + size, y - 9), (x + size + 6, y + 1), (x + size - 7, y + 1)])
        elif kind == "menu":
            for dy in (-8, 0, 8):
                pygame.draw.line(self.screen, color, (x - size, y + dy), (x + size, y + dy), 4)

    def _button(self, button_id, rect, label, selected=False, color=None, glyph=None):
        color = self.palette["accent"] if color is None else color
        rect = pygame.Rect(rect)
        self.buttons.append((button_id, rect))
        hover = rect.collidepoint(pygame.mouse.get_pos())
        active = selected or hover
        if active and config.NEON_MODE and self.palette["glow"]:
            self._glow(rect.center, max(rect.w, rect.h) // 2 + 30, color, 0.35 + 0.1 * math.sin(self.t * 5))
        fill = _scale(color, 0.30) if active else self.palette["panel"]
        pygame.draw.rect(self.screen, fill, rect, border_radius=14)
        pygame.draw.rect(self.screen, color if active else _scale(color, 0.55), rect, 3 if active else 2,
                         border_radius=14)
        text_color = self.palette["text"] if active else _scale(self.palette["text"], 0.8)
        room = rect.w - (84 if glyph else 24)
        font = self.medium_font
        if self._render(label, font, text_color).get_width() > room:
            font = self._font(22)
        cx = rect.centerx + (24 if glyph else 0)
        self._text(label, (cx, rect.centery), text_color, font, "center")
        if glyph:
            self._glyph(glyph, (rect.x + 30, rect.centery), color)

    def _panel(self, rect, color=None, alpha=225):
        color = self.palette["accent_secondary"] if color is None else color
        rect = pygame.Rect(rect)
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (*self.palette["panel"], alpha), surf.get_rect(), border_radius=18)
        pygame.draw.rect(surf, (*color, 90), surf.get_rect(), 5, border_radius=18)
        pygame.draw.rect(surf, color, surf.get_rect(), 2, border_radius=18)
        self.screen.blit(surf, rect)

    def _draw_piece(self, piece, center, scale=1.0, alpha=255, glow=True):
        size = max(8, int(self.PIECE_SIZE * scale))
        color = self.palette["tiger"] if piece == "T" else self.palette["cow"]
        if glow and config.NEON_MODE and self.palette["glow"]:
            pulse = 0.55 + 0.15 * math.sin(self.t * 3 + center[0] * 0.01)
            self._glow(center, int(size * 0.95), color, pulse * alpha / 255)
        img = self._piece_image(piece, size)
        if alpha < 255:
            img = img.copy()
            img.set_alpha(alpha)
        self.screen.blit(img, img.get_rect(center=(int(center[0]), int(center[1]))))

    # ==================================================================
    # Title / menu screens
    # ==================================================================

    def _title_block(self, y):
        cx = self.width // 2
        self._text("KHLA SI KO", (cx, y), self.palette["accent"], self._font(62), "center", glow=self.palette["glow"])
        self._text(config.GAME_SUBTITLE, (cx, y + 52), self.palette["muted"], self._font(20, bold=False), "center")

    def draw_title(self, selected=0):
        self._begin_frame()
        self._title_block(120)
        bob = 8 * math.sin(self.t * 2)
        self._draw_piece("T", (210, 215 + int(bob)), 1.6)
        self._draw_piece("C", (self.width - 210, 215 - int(bob)), 1.6)
        items = [("play", "PLAY GAME", self.palette["highlight"], "play"),
                 ("single", "SINGLE PLAYER", self.palette["accent"], "single"),
                 ("two", "TWO PLAYER", self.palette["accent_secondary"], "two"),
                 ("settings", "SETTINGS", self.palette["gold"], "gear"),
                 ("exit", "EXIT", self.palette["danger"], "exit")]
        top = 300
        for i, (bid, label, color, glyph) in enumerate(items):
            self._button(bid, (self.width // 2 - 200, top + i * 66, 400, 54), label, i == selected, color, glyph)
        self._text("Mouse  •  Hand gestures  •  Keyboard", (self.width // 2, self.height - 46),
                   self.palette["muted"], self.small_font, "center")

    def _card(self, bid, rect, title, lines, color, selected, piece=None, glyph=None):
        rect = pygame.Rect(rect)
        self.buttons.append((bid, rect))
        active = selected or rect.collidepoint(pygame.mouse.get_pos())
        if active and self.palette["glow"]:
            self._glow(rect.center, rect.w // 2 + 60, color, 0.3 + 0.08 * math.sin(self.t * 5))
        pygame.draw.rect(self.screen, _scale(color, 0.22) if active else self.palette["panel"], rect, border_radius=22)
        pygame.draw.rect(self.screen, color if active else _scale(color, 0.5), rect, 4 if active else 2, border_radius=22)
        if piece:
            self._draw_piece(piece, (rect.centerx, rect.y + 120), 1.6)
        elif glyph:
            self._glyph(glyph, (rect.centerx, rect.y + 110), color, 30)
        self._text(title, (rect.centerx, rect.y + 235), config.COW_WHITE, self.big_font, "center")
        for i, line in enumerate(lines):
            self._text(line, (rect.centerx, rect.y + 285 + i * 26), config.TEXT_MUTED, self.small_font, "center")

    def draw_mode_select(self, selected=0):
        self._begin_frame()
        self._text("SELECT GAME MODE", (self.width // 2, 80), self.palette["accent"], self._font(50), "center", glow=self.palette["glow"])
        self._card("single", (190, 150, 400, 400), "SINGLE PLAYER",
                   ["You against the computer.", "Choose Tiger or Cow."], self.palette["accent"], selected == 0, glyph="single")
        self._card("two", (690, 150, 400, 400), "TWO PLAYER",
                   ["Two people take turns.", "One Tiger, one Cow."], self.palette["accent_secondary"], selected == 1, glyph="two")
        self._button("back", (self.width // 2 - 110, 600, 220, 54), "BACK", selected == 2, self.palette["gold"])

    def draw_side_select(self, selected=0):
        self._begin_frame()
        self._text("CHOOSE YOUR SIDE", (self.width // 2, 80), self.palette["accent"], self._font(50), "center", glow=self.palette["glow"])
        self._card("tiger", (190, 150, 400, 400), "PLAY AS TIGER",
                   ["Jump over cows to capture them.", f"Capture {config.CAPTURES_TO_WIN} cows to win."],
                   self.palette["tiger"], selected == 0, piece="T")
        self._card("cow", (690, 150, 400, 400), "PLAY AS COW",
                   ["Place and move cows safely.", "Trap every tiger to win."],
                   self.palette["cow"], selected == 1, piece="C")
        self._button("back", (self.width // 2 - 110, 600, 220, 54), "BACK", selected == 2, self.palette["gold"])

    def draw_nickname_entry(self, names, sides, active_index, current_input, error="", selected=0):
        self._begin_frame()
        color = config.NEON_CYAN
        self._panel((210, 125, 860, 490), color, 245)
        self._text("CHOOSE YOUR NICKNAME" if len(sides) == 1 else "CHOOSE PLAYER NICKNAMES",
                   (self.width // 2, 175), color, self._font(42), "center", glow=True)
        self._text("Type a nickname, then press ENTER.",
                   (self.width // 2, 218), config.TEXT_MUTED, self.small_font, "center")

        row_top = 285 if len(sides) > 1 else 345
        for index, side in enumerate(sides):
            active = index == active_index
            y = row_top + index * 105
            side_name = "TIGER" if side == "T" else "COW"
            label = "YOUR NICKNAME" if len(sides) == 1 else f"PLAYER {index + 1}  •  {side_name}"
            self._text(label, (self.width // 2, y), color if active else config.TEXT_MUTED,
                       self._font(20), "center")
            field = pygame.Rect(self.width // 2 - 280, y + 16, 560, 58)
            pygame.draw.rect(self.screen, config.NEON_BG, field, border_radius=12)
            pygame.draw.rect(self.screen, color if active else _scale(color, 0.5),
                             field, 3 if active else 2, border_radius=12)
            value = current_input if active else names.get(side, "")
            self._text(value or "Type your nickname...", field.center,
                       config.COW_WHITE if value else config.TEXT_MUTED,
                       self._font(26, bold=bool(value)), "center")

        if error:
            self._text(error, (self.width // 2, 485), config.DANGER_RED, self.small_font, "center")
        else:
            hint = ("Player 2 enters their nickname next." if len(sides) > 1 and active_index == 0
                    else "Names can be up to 16 characters.")
            self._text(hint, (self.width // 2, 485), config.TEXT_MUTED, self.small_font, "center")

        continue_label = "START GAME" if active_index == len(sides) - 1 else "NEXT PLAYER"
        self._button("continue", (330, 525, 265, 58), continue_label, selected == 0, config.NEON_GREEN, "play")
        self._button("back", (685, 525, 265, 58), "BACK", selected == 1, config.GOLD, "menu")

    def draw_settings(self, options, selected=0):
        """options: list of (button_id, label)."""
        self._begin_frame()
        self._text("SETTINGS", (self.width // 2, 90), self.palette["gold"], self._font(54), "center", glow=self.palette["glow"])
        for i, (bid, label) in enumerate(options):
            color = self.palette["gold"] if bid == "back" else self.palette["accent"]
            self._button(bid, (self.width // 2 - 260, 170 + i * 68, 520, 56), label, i == selected, color)

    # ==================================================================
    # Game screen
    # ==================================================================

    def _draw_board(self, state, pointer, hover_pos=None, debug=False):
        """Draws the board, node highlights and all pieces (with animation)."""
        frame = self._board_frame_rect()
        self.screen.blit(self.board_surface, frame)

        valid_destinations = set()
        if state.selected_pos is not None:
            valid_destinations = {m["to"] for m in state.get_valid_moves(state.selected_pos)}
        if hover_pos is None:
            hover_pos = self.board_position_at(pointer)
        anim = self.move_anim
        if anim and self.t - anim["t0"] >= anim["dur"]:
            anim = self.move_anim = None
        self.fades = [f for f in self.fades if self.t - f["t0"] < 0.45]

        pulse = 0.5 + 0.5 * math.sin(self.t * 6)
        for row in range(KhlaSiKoRules.BOARD_SIZE):
            for col in range(KhlaSiKoRules.BOARD_SIZE):
                point = self.board_node(row, col)
                position = (row, col)
                empty = state.board[row][col] is None
                if position in valid_destinations:
                    self._glow(point, 40, self.palette["highlight"], 0.5 + 0.3 * pulse)
                    pygame.draw.circle(self.screen, self.palette["highlight"], point, int(14 + 4 * pulse), 3)
                    pygame.draw.circle(self.screen, self.palette["highlight"], point, 6)
                elif empty:
                    pygame.draw.circle(self.screen, self.palette["ground"], point, 12)
                    pygame.draw.circle(self.screen, self.palette["grid"], point, 12, 3)
                if debug:
                    index = KhlaSiKoRules.node_index(row, col)
                    self._text(str(index), (point[0] + 20, point[1] + 14), self.palette["muted"], self._font(14, False))

        # pieces
        for row in range(KhlaSiKoRules.BOARD_SIZE):
            for col in range(KhlaSiKoRules.BOARD_SIZE):
                piece = state.board[row][col]
                if piece is None or (anim and anim["end"] == (row, col)):
                    continue
                scale = 1.0
                popped = self.pops.get((row, col))
                if popped is not None:
                    k = (self.t - popped) / 0.3
                    if k >= 1:
                        del self.pops[(row, col)]
                    else:
                        scale = 0.3 + 0.7 * _ease_out(k) + 0.12 * math.sin(k * math.pi)
                self._draw_piece(piece, self.board_node(row, col), scale)

        # captured cow: flashes white and shrinks away
        for fade in self.fades:
            k = (self.t - fade["t0"]) / 0.45
            center = self.board_node(*fade["pos"])
            self._glow(center, 60, self.palette["text"], 1 - k)
            self._draw_piece("C", center, 1 - 0.6 * k, int(255 * (1 - k)), glow=False)

        # moving piece with a glow trail
        if anim:
            p = _ease_out((self.t - anim["t0"]) / anim["dur"])
            start, end = self.board_node(*anim["start"]), self.board_node(*anim["end"])
            for lag, alpha in ((0.30, 50), (0.20, 90), (0.10, 140)):
                q = max(0.0, p - lag)
                self._draw_piece(anim["piece"], (start[0] + (end[0] - start[0]) * q,
                                                 start[1] + (end[1] - start[1]) * q), 0.9, alpha, glow=False)
            self._draw_piece(anim["piece"], (round(start[0] + (end[0] - start[0]) * p),
                                             round(start[1] + (end[1] - start[1]) * p)))

        # selection / hover / error rings
        if state.selected_pos is not None:
            self._ring(self.board_node(*state.selected_pos), self.NODE_RADIUS + 8 + 3 * pulse, self.palette["gold"], 4)
        if hover_pos is not None:
            self._ring(self.board_node(*hover_pos), self.NODE_RADIUS + 16, self.palette["accent"], 3)
        if self.error_flash:
            pos, t0 = self.error_flash
            k = (self.t - t0) / 0.5
            if k >= 1:
                self.error_flash = None
            else:
                self._ring(self.board_node(*pos), self.NODE_RADIUS + 6 + 10 * k, self.palette["danger"], 4)

    def _draw_panel(self, state, message, gesture, camera_surface=None, camera_status=None,
                    debug_info=None, winner_name=None):
        left, width = 650, 590
        status = camera_status or {"online": False, "reason": ""}

        # --- turn card
        turn_color = self.palette["tiger"] if state.current_turn == "T" else self.palette["cow"]
        self._panel((left, 100, width, 104), turn_color)
        if state.winner:
            title, sub = "GAME OVER", f"{winner_name or 'Player'} WINS!"
        else:
            title = state.turn_label
            if state.game_mode == config.MODE_SINGLE:
                sub = "YOUR MOVE" if state.is_human_turn else "COMPUTER IS THINKING..."
            else:
                sub = "TWO PLAYER MODE"
            if state.phase == "PLACEMENT" and state.current_turn == "C":
                sub += f"   •   place a cow ({state.cows_to_place} left)"
        self._draw_piece("T" if state.current_turn == "T" else "C", (left + 62, 152), 0.95)
        self._text(title, (left + 120, 128), turn_color, self._font(40), "midleft", glow=True)
        self._text(sub, (left + 120, 176), self.palette["muted"], self.small_font, "midleft")

        # --- stats tiles
        stats = [("COWS REMAINING", str(state.cows_remaining), self.palette["cow"]),
                 ("TO PLACE", str(state.cows_to_place), self.palette["highlight"]),
                 ("CAPTURED", f"{state.captured_cows}/{config.CAPTURES_TO_WIN}", self.palette["danger"])]
        for i, (label, value, tint) in enumerate(stats):
            rect = pygame.Rect(left + i * 200, 216, 190, 96)
            self._panel(rect, tint, 215)
            self._text(label, (rect.centerx, rect.y + 24), self.palette["muted"], self._font(15), "center")
            self._text(value, (rect.centerx, rect.y + 62), tint, self._font(44), "center", glow=True)

        # --- message
        self._panel((left, 324, width, 58), self.palette["accent_secondary"], 215)
        self._text(message[:62], (left + 20, 353), self.palette["text"], self.small_font, "midleft")

        # --- camera + gesture
        self._panel((left, 394, width, 232), self.palette["highlight"] if status["online"] else self.palette["danger"], 215)
        cam_rect = pygame.Rect(left + 14, 408, *self.CAMERA_PREVIEW_SIZE)
        if camera_surface is not None and status["online"]:
            self.screen.blit(camera_surface, cam_rect)
            pygame.draw.rect(self.screen, self.palette["highlight"], cam_rect, 2, border_radius=4)
        else:
            pygame.draw.rect(self.screen, self.palette["ground"], cam_rect, border_radius=8)
            pygame.draw.rect(self.screen, self.palette["muted"], cam_rect, 2, border_radius=8)
            self._text("PREVIEW OFF" if status["online"] else "NO CAMERA", cam_rect.center,
                       self.palette["muted"], self.medium_font, "center")
        x = cam_rect.right + 22
        dot = self.palette["highlight"] if status["online"] else self.palette["danger"]
        pygame.draw.circle(self.screen, dot, (x + 7, 422), 7, 0 if status["online"] else 3)
        if status.get("starting"):
            dot, label = self.palette["gold"], "CAMERA STARTING..."
        else:
            label = "CAMERA ONLINE" if status["online"] else "CAMERA OFFLINE"
        self._text(label, (x + 22, 422), dot, self._font(20), "midleft")
        gesture_y = 482
        hints_y = 546
        reason = ""
        if not status["online"]:
            self._text("MOUSE CONTROL ENABLED", (x, 450), config.GOLD, self._font(17), "midleft")
            reason = status.get("reason", "")
            if reason:
                reason_lines = textwrap.wrap(reason, width=34)
                for i, line in enumerate(reason_lines[:3]):
                    self._text(line, (x, 466 + i * 14), config.TEXT_MUTED, self._font(12), "midleft")
                gesture_y, hints_y = 504, 564
        self._text("GESTURE", (x, gesture_y), config.TEXT_MUTED, self._font(15), "midleft")
        label = GESTURE_LABELS.get(gesture, gesture)
        self._text(label, (x, gesture_y + 30), GESTURE_COLORS.get(gesture, config.COW_WHITE),
                   self._font(32), "midleft", glow=True)
        for i, line in enumerate(("POINT  aim at a point", "OPEN PALM  select", "THUMBS UP  confirm", "FIST  cancel")):
            self._text(line, (x, hints_y + i * (15 if reason else 17)),
                       config.TEXT_MUTED, self._font(14, False), "midleft")

        # --- debug
        if debug_info:
            self._panel((left, 636, width, 78), self.palette["gold"], 220)
            for i, line in enumerate(debug_info[:3]):
                self._text(line, (left + 14, 648 + i * 22), self.palette["text"], self._font(15, False), "midleft")

    def draw_game(self, state, message="", gesture="NONE", pointer=None, hover_pos=None,
                  camera_surface=None, camera_status=None, debug_info=None, camera_on=True,
                  winner_name=None):
        self._begin_frame()
        # header
        pygame.draw.rect(self.screen, self.palette["panel"], (0, 22, self.width, 58))
        pygame.draw.line(self.screen, self.palette["accent_secondary"], (0, 80), (self.width, 80), 2)
        self._draw_piece("T", (52, 52), 0.55, glow=False)
        title_x = 92
        self._text("KHLA SI KO", (title_x, 52), self.palette["accent"], self._font(32), "midleft", glow=self.palette["glow"])
        self._text(f"ROUND {state.round_number:02d}", (self.width - 40, 42), self.palette["gold"], self._font(26), "midright", glow=self.palette["glow"])
        mode = ("SINGLE PLAYER  •  YOU: " + ("TIGER" if state.player_piece == "T" else "COW")
                if state.game_mode == config.MODE_SINGLE else "TWO PLAYER")
        self._text(mode, (self.width - 40, 66), self.palette["muted"], self._font(15, False), "midright")

        self._draw_board(state, pointer, hover_pos, debug=bool(debug_info))
        self._draw_panel(state, message, gesture, camera_surface, camera_status, debug_info, winner_name)

        # bottom buttons
        self._button("reset", (75, 650, 160, 48), "RESET", False, self.palette["highlight"], "restart")
        self._button("menu", (250, 650, 160, 48), "MENU", False, self.palette["accent_secondary"], "menu")
        self._button("camera", (425, 650, 180, 48), f"CAMERA: {'ON' if camera_on else 'OFF'}", False,
                     self.palette["accent"] if camera_on else self.palette["muted"])

    # ==================================================================
    # Overlays (draw after draw_game, before present)
    # ==================================================================

    def _dim(self, alpha=170):
        veil = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        shade = (8, 18, 12) if self.game_style == config.GAME_STYLE_JUNGLE else (3, 5, 15)
        veil.fill((*shade, alpha))
        self.screen.blit(veil, (0, 0))

    def draw_pause(self, selected=0):
        self.buttons = []
        self._dim()
        self._panel((self.width // 2 - 280, 120, 560, 480), self.palette["accent_secondary"], 245)
        self._text("GAME PAUSED", (self.width // 2, 175), self.palette["accent"], self._font(50), "center", glow=self.palette["glow"])
        items = [("resume", "RESUME", self.palette["highlight"], "play"),
                 ("restart", "RESTART", self.palette["gold"], "restart"),
                 ("menu", "MAIN MENU", self.palette["accent_secondary"], "menu"),
                 ("exit", "EXIT", self.palette["danger"], "exit")]
        for i, (bid, label, color, glyph) in enumerate(items):
            self._button(bid, (self.width // 2 - 200, 235 + i * 85, 400, 62), label, i == selected, color, glyph)

    def draw_game_over(self, state, selected=0, winner_name=None):
        self.buttons = []
        self._dim(185)
        tigers = state.winner == "TIGERS"
        color = self.palette["tiger"] if tigers else self.palette["cow"]
        if self._rng.random() < 0.25:
            self.burst((self._rng.randint(200, self.width - 200), self._rng.randint(120, 300)),
                       self._rng.choice([color, self.palette["gold"], self.palette["highlight"], self.palette["accent_secondary"]]), 14, 220)
        self._panel((self.width // 2 - 380, 110, 760, 500), color, 245)
        self._draw_piece("T" if tigers else "C", (self.width // 2, 215), 1.7)
        self._text("TIGER WINS!" if tigers else "COWS WIN!", (self.width // 2, 330), color, self._font(66), "center", glow=self.palette["glow"])
        self._text("THE HUNT IS COMPLETE" if tigers else "THE TIGER IS BLOCKED", (self.width // 2, 385),
                   self.palette["muted"], self._font(24), "center")
        if state.game_mode == config.MODE_SINGLE:
            human_won = (state.winner == "TIGERS") == (state.player_piece == "T")
            self._text("YOU WIN!" if human_won else "THE COMPUTER WINS", (self.width // 2, 435),
                       self.palette["gold"] if human_won else self.palette["danger"], self._font(28), "center")
        items = [("again", "PLAY AGAIN", self.palette["highlight"], "play"),
                 ("menu", "MAIN MENU", self.palette["accent_secondary"], "menu"),
                 ("exit", "EXIT", self.palette["danger"], "exit")]
        for i, (bid, label, c, glyph) in enumerate(items):
            self._button(bid, (self.width // 2 - 345 + i * 235, 495, 215, 60), label, i == selected, c, glyph)

    def close(self):
        pygame.display.quit()
