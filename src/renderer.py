"""Pygame display for the Khla Si Ko board game."""

import pygame

from src import config
from src.game_rules import KhlaSiKoRules


class Renderer:
    BOARD_LEFT = 70
    BOARD_TOP = 145
    BOARD_SIZE = 560
    NODE_RADIUS = 25

    def __init__(self, width=config.SCREEN_WIDTH, height=config.SCREEN_HEIGHT):
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(config.GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("arial", 42, bold=True)
        self.big_font = pygame.font.SysFont("arial", 32, bold=True)
        self.medium_font = pygame.font.SysFont("arial", 24, bold=True)
        self.small_font = pygame.font.SysFont("arial", 18)
        self.board_step = self.BOARD_SIZE / (KhlaSiKoRules.BOARD_SIZE - 1)

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
        if (x - node_x) ** 2 + (y - node_y) ** 2 > 55 ** 2:
            return None
        return row, col

    def camera_point_to_screen(self, x, y):
        return (
            round(self.BOARD_LEFT + x * self.BOARD_SIZE),
            round(self.BOARD_TOP + y * self.BOARD_SIZE),
        )

    def _text(self, text, position, color=config.BLACK, font=None):
        rendered = (font or self.small_font).render(text, True, color)
        self.screen.blit(rendered, position)

    def _draw_board(self, state, pointer):
        board_rect = pygame.Rect(
            self.BOARD_LEFT - 40,
            self.BOARD_TOP - 40,
            self.BOARD_SIZE + 80,
            self.BOARD_SIZE + 80,
        )
        pygame.draw.rect(self.screen, (249, 246, 232), board_rect, border_radius=20)
        pygame.draw.rect(self.screen, (194, 155, 91), board_rect, 4, border_radius=20)

        for index in range(KhlaSiKoRules.BOARD_SIZE):
            start = self.board_node(index, 0)
            end = self.board_node(index, KhlaSiKoRules.BOARD_SIZE - 1)
            pygame.draw.line(self.screen, (115, 86, 53), start, end, 5)
            start = self.board_node(0, index)
            end = self.board_node(KhlaSiKoRules.BOARD_SIZE - 1, index)
            pygame.draw.line(self.screen, (115, 86, 53), start, end, 5)

        valid_destinations = set()
        if state.selected_pos is not None:
            valid_destinations = {
                move["to"] for move in state.get_valid_moves(state.selected_pos)
            }

        for row in range(KhlaSiKoRules.BOARD_SIZE):
            for col in range(KhlaSiKoRules.BOARD_SIZE):
                point = self.board_node(row, col)
                position = (row, col)
                if position in valid_destinations:
                    pygame.draw.circle(self.screen, config.GREEN, point, 17)
                else:
                    pygame.draw.circle(self.screen, (115, 86, 53), point, 12)

                piece = state.board[row][col]
                if piece == "T":
                    pygame.draw.circle(self.screen, (218, 112, 38), point, self.NODE_RADIUS)
                    pygame.draw.circle(self.screen, (112, 55, 27), point, self.NODE_RADIUS, 3)
                    self._text("T", (point[0] - 9, point[1] - 15), config.WHITE, self.medium_font)
                elif piece == "C":
                    pygame.draw.circle(self.screen, config.WHITE, point, self.NODE_RADIUS)
                    pygame.draw.circle(self.screen, (75, 75, 75), point, self.NODE_RADIUS, 3)
                    self._text("C", (point[0] - 9, point[1] - 15), config.BLACK, self.medium_font)

                if position == state.selected_pos:
                    pygame.draw.circle(self.screen, config.YELLOW, point, self.NODE_RADIUS + 5, 4)
                if position == pointer:
                    pygame.draw.circle(self.screen, config.BLUE, point, self.NODE_RADIUS + 9, 3)

    def _draw_panel(self, state, message, gesture):
        left = 735
        self._text("KHLA SI KO", (left, 55), config.DARK_GREEN, self.title_font)
        self._text(
            "You: Cows",
            (left, 130),
            config.BLUE,
            self.medium_font,
        )
        self._text(
            "Opponent: Tigers",
            (left, 165),
            (185, 80, 35),
            self.medium_font,
        )
        phase_text = "Place cows" if state.phase == "PLACEMENT" else "Move pieces"
        if state.winner:
            phase_text = f"{state.winner.title()} win"
        self._text(f"Phase: {phase_text}", (left, 225), config.BLACK, self.medium_font)
        self._text(f"Cows left to place: {state.cows_to_place}", (left, 270))
        self._text(f"Cows captured: {state.captured_cows} / 4", (left, 300))
        self._text(f"Turn: {'You (Cows)' if state.current_turn == 'C' else 'Tiger'}", (left, 330))

        pygame.draw.rect(
            self.screen,
            (249, 246, 232),
            pygame.Rect(left - 12, 385, self.width - left - 28, 88),
            border_radius=10,
        )
        self._text(message, (left, 398), config.BLACK)
        self._text(f"Gesture: {gesture}", (left, 432), config.GRAY)

        instructions = (
            "Click a point or pinch over it to place/select.",
            "Select a cow, then choose a highlighted point.",
            "Tiger captures by jumping over a cow.",
            "R: restart     Esc: quit     Q: close camera",
        )
        for index, line in enumerate(instructions):
            self._text(line, (left, 520 + index * 32), config.GRAY)

    def draw_game(self, state, message="", gesture="NONE", pointer=None):
        self.screen.fill(config.BACKGROUND_COLOR)
        self._draw_board(state, self.board_position_at(pointer))
        self._draw_panel(state, message, gesture)
        pygame.display.flip()

    def tick(self, fps=config.FPS):
        self.clock.tick(fps)

    def close(self):
        pygame.display.quit()
