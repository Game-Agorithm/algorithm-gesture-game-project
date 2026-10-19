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

    def _text(self, text, position, color=config.COW_WHITE, font=None, anchor="topleft", glow=False):
        """Draw text. ``anchor`` is any pygame Rect attribute (center, midtop...)."""
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
        for piece, path in (("T", config.TIGER_IMAGE), ("C", config.COW_IMAGE)):
            try:
                images[piece] = pygame.image.load(str(path)).convert_alpha()
            except (pygame.error, FileNotFoundError, OSError) as error:
                logger.warning("Image %s missing (%s); drawing a shape instead.", path, error)
                images[piece] = None
        return images

    def _piece_image(self, piece, size):
        key = (piece, size)
        if key not in self._image_cache:
            source = self._pieces.get(piece)
            if source is not None:
                img = pygame.transform.smoothscale(source, (size, size))
            else:                                   # fallback: simple drawn token
                img = pygame.Surface((size, size), pygame.SRCALPHA)
                color = config.TIGER_ORANGE if piece == "T" else config.COW_WHITE
                pygame.draw.circle(img, color, (size // 2, size // 2), size // 2 - 3)
                pygame.draw.circle(img, _scale(color, 0.5), (size // 2, size // 2), size // 2 - 3, 3)
                label = self._render(piece, self._font(size // 2), config.NEON_BG)
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
        surf = self._glow_surface(radius, color)
        if strength < 1.0:
            surf = surf.copy()
            surf.fill(_scale((255, 255, 255), max(0.0, strength)), special_flags=pygame.BLEND_RGB_MULT)
        self.screen.blit(surf, (int(center[0]) - radius, int(center[1]) - radius),
                         special_flags=pygame.BLEND_RGB_ADD)

    def _ring(self, center, radius, color, width=3, glow=True):
        if glow and config.NEON_MODE:
            self._glow(center, int(radius) + 26, color, 0.8)
        pygame.draw.circle(self.screen, color, center, int(radius), width)

    def _build_background(self):
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

    def _board_frame_rect(self):
        return pygame.Rect(self.BOARD_LEFT - 55, self.BOARD_TOP - 55,
                           self.BOARD_SIZE + 110, self.BOARD_SIZE + 110)

    def _build_board_surface(self):
        """The static neon board (frame + grid lines) drawn once and reused."""
        frame = self._board_frame_rect()
        surf = pygame.Surface(frame.size, pygame.SRCALPHA)
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

        Only the middle part of the camera image (config.CAMERA_ACTIVE_AREA)
        is mapped onto the board, so you never need to reach the camera edge.
        """
        left, top, right, bottom = config.CAMERA_ACTIVE_AREA
        nx = min(1.0, max(0.0, (x - left) / (right - left)))
        ny = min(1.0, max(0.0, (y - top) / (bottom - top)))
        margin = 36
        return (
            round(self.BOARD_LEFT - margin + nx * (self.BOARD_SIZE + 2 * margin)),
            round(self.BOARD_TOP - margin + ny * (self.BOARD_SIZE + 2 * margin)),
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
        if config.NEON_MODE:                        # animated grid
            grid = (22, 30, 70)
            for x in range(0, self.width, 64):
                pygame.draw.line(self.screen, grid, (x, 22), (x, self.height - 22))
            offset = (self.t * 18) % 64
            for y in range(int(offset) + 22, self.height - 22, 64):
                pygame.draw.line(self.screen, grid, (0, y), (self.width, y))

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

    def _button(self, button_id, rect, label, selected=False, color=config.NEON_CYAN, glyph=None):
        rect = pygame.Rect(rect)
        self.buttons.append((button_id, rect))
        hover = rect.collidepoint(pygame.mouse.get_pos())
        active = selected or hover
        if active and config.NEON_MODE:
            self._glow(rect.center, max(rect.w, rect.h) // 2 + 30, color, 0.35 + 0.1 * math.sin(self.t * 5))
        fill = _scale(color, 0.30) if active else config.NEON_PANEL
        pygame.draw.rect(self.screen, fill, rect, border_radius=14)
        pygame.draw.rect(self.screen, color if active else _scale(color, 0.55), rect, 3 if active else 2,
                         border_radius=14)
        text_color = config.COW_WHITE if active else _scale(config.COW_WHITE, 0.8)
        room = rect.w - (84 if glyph else 24)
        font = self.medium_font
        if self._render(label, font, text_color).get_width() > room:
            font = self._font(22)
        cx = rect.centerx + (24 if glyph else 0)
        self._text(label, (cx, rect.centery), text_color, font, "center")
        if glyph:
            self._glyph(glyph, (rect.x + 30, rect.centery), color)

    def _panel(self, rect, color=config.NEON_PURPLE, alpha=225):
        rect = pygame.Rect(rect)
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (*config.NEON_PANEL, alpha), surf.get_rect(), border_radius=18)
        pygame.draw.rect(surf, (*color, 90), surf.get_rect(), 5, border_radius=18)
        pygame.draw.rect(surf, color, surf.get_rect(), 2, border_radius=18)
        self.screen.blit(surf, rect)

    def _draw_piece(self, piece, center, scale=1.0, alpha=255, glow=True):
        size = max(8, int(self.PIECE_SIZE * scale))
        color = config.TIGER_ORANGE if piece == "T" else config.NEON_CYAN
        if glow and config.NEON_MODE:
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
        self._text("KHLA SI KO", (cx, y), config.NEON_CYAN, self._font(62), "center", glow=True)
        self._text(config.GAME_SUBTITLE, (cx, y + 52), config.TEXT_MUTED, self._font(20, bold=False), "center")

    def draw_title(self, selected=0):
        self._begin_frame()
        self._title_block(120)
        bob = 8 * math.sin(self.t * 2)
        self._draw_piece("T", (210, 215 + int(bob)), 1.6)
        self._draw_piece("C", (self.width - 210, 215 - int(bob)), 1.6)
        items = [("play", "PLAY GAME", config.NEON_GREEN, "play"),
                 ("single", "SINGLE PLAYER", config.NEON_CYAN, "single"),
                 ("two", "TWO PLAYER", config.NEON_PURPLE, "two"),
                 ("settings", "SETTINGS", config.GOLD, "gear"),
                 ("exit", "EXIT", config.DANGER_RED, "exit")]
        top = 300
        for i, (bid, label, color, glyph) in enumerate(items):
            self._button(bid, (self.width // 2 - 200, top + i * 66, 400, 54), label, i == selected, color, glyph)
        self._text("Mouse  •  Hand gestures  •  Keyboard", (self.width // 2, self.height - 46),
                   config.TEXT_MUTED, self.small_font, "center")

    def _card(self, bid, rect, title, lines, color, selected, piece=None, glyph=None):
        rect = pygame.Rect(rect)
        self.buttons.append((bid, rect))
        active = selected or rect.collidepoint(pygame.mouse.get_pos())
        if active:
            self._glow(rect.center, rect.w // 2 + 60, color, 0.3 + 0.08 * math.sin(self.t * 5))
        pygame.draw.rect(self.screen, _scale(color, 0.22) if active else config.NEON_PANEL, rect, border_radius=22)
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
        self._text("SELECT GAME MODE", (self.width // 2, 80), config.NEON_CYAN, self._font(50), "center", glow=True)
        self._card("single", (190, 150, 400, 400), "SINGLE PLAYER",
                   ["You against the computer.", "Choose Tiger or Cow."], config.NEON_CYAN, selected == 0, glyph="single")
        self._card("two", (690, 150, 400, 400), "TWO PLAYER",
                   ["Two people take turns.", "One Tiger, one Cow."], config.NEON_PURPLE, selected == 1, glyph="two")
        self._button("back", (self.width // 2 - 110, 600, 220, 54), "BACK", selected == 2, config.GOLD)

    def draw_side_select(self, selected=0):
        self._begin_frame()
        self._text("CHOOSE YOUR SIDE", (self.width // 2, 80), config.NEON_CYAN, self._font(50), "center", glow=True)
        self._card("tiger", (190, 150, 400, 400), "PLAY AS TIGER",
                   ["Jump over cows to capture them.", f"Capture {config.CAPTURES_TO_WIN} cows to win."],
                   config.TIGER_ORANGE, selected == 0, piece="T")
        self._card("cow", (690, 150, 400, 400), "PLAY AS COW",
                   ["Place and move cows safely.", "Trap every tiger to win."],
                   config.NEON_CYAN, selected == 1, piece="C")
        self._button("back", (self.width // 2 - 110, 600, 220, 54), "BACK", selected == 2, config.GOLD)

    def draw_settings(self, options, selected=0):
        """options: list of (button_id, label)."""
        self._begin_frame()
        self._text("SETTINGS", (self.width // 2, 90), config.GOLD, self._font(54), "center", glow=True)
        for i, (bid, label) in enumerate(options):
            color = config.GOLD if bid == "back" else config.NEON_CYAN
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
                    self._glow(point, 40, config.NEON_GREEN, 0.5 + 0.3 * pulse)
                    pygame.draw.circle(self.screen, config.NEON_GREEN, point, int(14 + 4 * pulse), 3)
                    pygame.draw.circle(self.screen, config.NEON_GREEN, point, 6)
                elif empty:
                    pygame.draw.circle(self.screen, config.NEON_BG, point, 12)
                    pygame.draw.circle(self.screen, config.NEON_CYAN, point, 12, 3)
                if debug:
                    index = KhlaSiKoRules.node_index(row, col)
                    self._text(str(index), (point[0] + 20, point[1] + 14), config.TEXT_MUTED, self._font(14, False))

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
            self._glow(center, 60, config.COW_WHITE, 1 - k)
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
            self._ring(self.board_node(*state.selected_pos), self.NODE_RADIUS + 8 + 3 * pulse, config.GOLD, 4)
        if hover_pos is not None:
            self._ring(self.board_node(*hover_pos), self.NODE_RADIUS + 16, config.NEON_CYAN, 3)
        if self.error_flash:
            pos, t0 = self.error_flash
            k = (self.t - t0) / 0.5
            if k >= 1:
                self.error_flash = None
            else:
                self._ring(self.board_node(*pos), self.NODE_RADIUS + 6 + 10 * k, config.DANGER_RED, 4)

        if pointer is not None:                      # glowing hand cursor
            self._glow(pointer, 34, config.NEON_CYAN, 0.9)
            pygame.draw.circle(self.screen, config.COW_WHITE, pointer, 7)
            pygame.draw.circle(self.screen, config.NEON_CYAN, pointer, 15, 3)

    def _draw_panel(self, state, message, gesture, camera_surface=None, camera_status=None, debug_info=None):
        left, width = 650, 590
        status = camera_status or {"online": False, "reason": ""}

        # --- turn card
        turn_color = config.TIGER_ORANGE if state.current_turn == "T" else config.NEON_CYAN
        self._panel((left, 100, width, 104), turn_color)
        if state.winner:
            title, sub = "GAME OVER", ("TIGERS WIN" if state.winner == "TIGERS" else "COWS WIN")
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
        self._text(sub, (left + 120, 176), config.TEXT_MUTED, self.small_font, "midleft")

        # --- stats tiles
        stats = [("COWS REMAINING", str(state.cows_remaining), config.NEON_CYAN),
                 ("TO PLACE", str(state.cows_to_place), config.NEON_GREEN),
                 ("CAPTURED", f"{state.captured_cows}/{config.CAPTURES_TO_WIN}", config.DANGER_RED)]
        for i, (label, value, tint) in enumerate(stats):
            rect = pygame.Rect(left + i * 200, 216, 190, 96)
            self._panel(rect, tint, 215)
            self._text(label, (rect.centerx, rect.y + 24), config.TEXT_MUTED, self._font(15), "center")
            self._text(value, (rect.centerx, rect.y + 62), tint, self._font(44), "center", glow=True)

        # --- message
        self._panel((left, 324, width, 58), config.NEON_PURPLE, 215)
        self._text(message[:62], (left + 20, 353), config.COW_WHITE, self.small_font, "midleft")

        # --- camera + gesture
        self._panel((left, 394, width, 232), config.NEON_GREEN if status["online"] else config.DANGER_RED, 215)
        cam_rect = pygame.Rect(left + 14, 408, *self.CAMERA_PREVIEW_SIZE)
        if camera_surface is not None and status["online"]:
            self.screen.blit(camera_surface, cam_rect)
            pygame.draw.rect(self.screen, config.NEON_GREEN, cam_rect, 2, border_radius=4)
        else:
            pygame.draw.rect(self.screen, config.NEON_BG, cam_rect, border_radius=8)
            pygame.draw.rect(self.screen, config.TEXT_MUTED, cam_rect, 2, border_radius=8)
            self._text("PREVIEW OFF" if status["online"] else "NO CAMERA", cam_rect.center,
                       config.TEXT_MUTED, self.medium_font, "center")
        x = cam_rect.right + 22
        dot = config.NEON_GREEN if status["online"] else config.DANGER_RED
        pygame.draw.circle(self.screen, dot, (x + 7, 422), 7, 0 if status["online"] else 3)
        if status.get("starting"):
            dot, label = config.GOLD, "CAMERA STARTING..."
        else:
            label = "CAMERA ONLINE" if status["online"] else "CAMERA OFFLINE"
        self._text(label, (x + 22, 422), dot, self._font(20), "midleft")
        if not status["online"]:
            self._text("MOUSE CONTROL ENABLED", (x, 450), config.GOLD, self._font(17), "midleft")
        self._text("GESTURE", (x, 482), config.TEXT_MUTED, self._font(15), "midleft")
        label = GESTURE_LABELS.get(gesture, gesture)
        self._text(label, (x, 512), GESTURE_COLORS.get(gesture, config.COW_WHITE), self._font(32), "midleft", glow=True)
        for i, line in enumerate(("POINT  aim at a point", "OPEN PALM  select", "THUMBS UP  confirm", "FIST  cancel")):
            self._text(line, (x, 546 + i * 17), config.TEXT_MUTED, self._font(14, False), "midleft")

        # --- debug
        if debug_info:
            self._panel((left, 636, width, 78), config.GOLD, 220)
            for i, line in enumerate(debug_info[:3]):
                self._text(line, (left + 14, 648 + i * 22), config.COW_WHITE, self._font(15, False), "midleft")

    def draw_game(self, state, message="", gesture="NONE", pointer=None, hover_pos=None,
                  camera_surface=None, camera_status=None, debug_info=None, camera_on=True):
        self._begin_frame()
        # header
        pygame.draw.rect(self.screen, config.NEON_PANEL, (0, 22, self.width, 58))
        pygame.draw.line(self.screen, config.NEON_PURPLE, (0, 80), (self.width, 80), 2)
        self._draw_piece("T", (52, 52), 0.55, glow=False)
        title_x = 92
        self._text("KHLA SI KO", (title_x, 52), config.NEON_CYAN, self._font(32), "midleft", glow=True)
        self._text(f"ROUND {state.round_number:02d}", (self.width - 40, 42), config.GOLD, self._font(26), "midright", glow=True)
        mode = ("SINGLE PLAYER  •  YOU: " + ("TIGER" if state.player_piece == "T" else "COW")
                if state.game_mode == config.MODE_SINGLE else "TWO PLAYER")
        self._text(mode, (self.width - 40, 66), config.TEXT_MUTED, self._font(15, False), "midright")

        self._draw_board(state, pointer, hover_pos, debug=bool(debug_info))
        self._draw_panel(state, message, gesture, camera_surface, camera_status, debug_info)

        # bottom buttons
        self._button("reset", (75, 650, 160, 48), "RESET", False, config.NEON_GREEN, "restart")
        self._button("menu", (250, 650, 160, 48), "MENU", False, config.NEON_PURPLE, "menu")
        self._button("camera", (425, 650, 180, 48), f"CAMERA: {'ON' if camera_on else 'OFF'}", False,
                     config.NEON_CYAN if camera_on else config.TEXT_MUTED)

    # ==================================================================
    # Overlays (draw after draw_game, before present)
    # ==================================================================

    def _dim(self, alpha=170):
        veil = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        veil.fill((3, 5, 15, alpha))
        self.screen.blit(veil, (0, 0))

    def draw_pause(self, selected=0):
        self.buttons = []
        self._dim()
        self._panel((self.width // 2 - 280, 120, 560, 480), config.NEON_PURPLE, 245)
        self._text("GAME PAUSED", (self.width // 2, 175), config.NEON_CYAN, self._font(50), "center", glow=True)
        items = [("resume", "RESUME", config.NEON_GREEN, "play"), ("restart", "RESTART", config.GOLD, "restart"),
                 ("menu", "MAIN MENU", config.NEON_PURPLE, "menu"), ("exit", "EXIT", config.DANGER_RED, "exit")]
        for i, (bid, label, color, glyph) in enumerate(items):
            self._button(bid, (self.width // 2 - 200, 235 + i * 85, 400, 62), label, i == selected, color, glyph)

    def draw_game_over(self, state, selected=0):
        self.buttons = []
        self._dim(185)
        tigers = state.winner == "TIGERS"
        color = config.TIGER_ORANGE if tigers else config.NEON_CYAN
        if self._rng.random() < 0.25:
            self.burst((self._rng.randint(200, self.width - 200), self._rng.randint(120, 300)),
                       self._rng.choice([color, config.GOLD, config.NEON_GREEN, config.NEON_PURPLE]), 14, 220)
        self._panel((self.width // 2 - 380, 110, 760, 500), color, 245)
        self._draw_piece("T" if tigers else "C", (self.width // 2, 215), 1.7)
        self._text("TIGER WINS!" if tigers else "COWS WIN!", (self.width // 2, 330), color, self._font(66), "center", glow=True)
        self._text("THE HUNT IS COMPLETE" if tigers else "THE TIGER IS BLOCKED", (self.width // 2, 385),
                   config.TEXT_MUTED, self._font(24), "center")
        if state.game_mode == config.MODE_SINGLE:
            human_won = (state.winner == "TIGERS") == (state.player_piece == "T")
            self._text("YOU WIN!" if human_won else "THE COMPUTER WINS", (self.width // 2, 435),
                       config.GOLD if human_won else config.DANGER_RED, self._font(28), "center")
        items = [("again", "PLAY AGAIN", config.NEON_GREEN, "play"), ("menu", "MAIN MENU", config.NEON_PURPLE, "menu"),
                 ("exit", "EXIT", config.DANGER_RED, "exit")]
        for i, (bid, label, c, glyph) in enumerate(items):
            self._button(bid, (self.width // 2 - 345 + i * 235, 495, 215, 60), label, i == selected, c, glyph)

    def close(self):
        pygame.display.quit()
