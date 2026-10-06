"""
Khla Si Ko - Renderer

Responsible for displaying the game.
"""

import pygame

from src import config


class Renderer:

    def __init__(
        self,
        width=config.SCREEN_WIDTH,
        height=config.SCREEN_HEIGHT
    ):

        self.width = width
        self.height = height

        # ----------------------------------------------------
        # Screen
        # ----------------------------------------------------

        self.screen = pygame.display.set_mode(
            (self.width, self.height)
        )

        pygame.display.set_caption(
            config.GAME_TITLE
        )

        # ----------------------------------------------------
        # Clock
        # ----------------------------------------------------

        self.clock = pygame.time.Clock()

        # ----------------------------------------------------
        # Fonts
        # ----------------------------------------------------

        self.title_font = pygame.font.SysFont(
            "arial",
            config.TITLE_FONT_SIZE,
            bold=True
        )

        self.big_font = pygame.font.SysFont(
            "arial",
            config.BIG_FONT_SIZE,
            bold=True
        )

        self.medium_font = pygame.font.SysFont(
            "arial",
            config.MEDIUM_FONT_SIZE,
            bold=True
        )

        self.small_font = pygame.font.SysFont(
            "arial",
            config.SMALL_FONT_SIZE
        )

    # ========================================================
    # CLEAR
    # ========================================================

    def clear(self):

        self.screen.fill(
            config.BACKGROUND_COLOR
        )

    # ========================================================
    # TITLE
    # ========================================================

    def draw_title(self):

        title = self.title_font.render(
            "KHLA SI KO",
            True,
            config.DARK_GREEN
        )

        rect = title.get_rect(
            center=(
                self.width // 2,
                50
            )
        )

        self.screen.blit(
            title,
            rect
        )

    # ========================================================
    # SCORE
    # ========================================================

    def draw_score(
        self,
        player_score,
        computer_score
    ):

        player = self.medium_font.render(
            f"Player: {player_score}",
            True,
            config.BLUE
        )

        computer = self.medium_font.render(
            f"Computer: {computer_score}",
            True,
            config.RED
        )

        self.screen.blit(
            player,
            (40, 100)
        )

        self.screen.blit(
            computer,
            (
                self.width - computer.get_width() - 40,
                100
            )
        )

    # ========================================================
    # TIGER
    # ========================================================

    def draw_tiger(self):

        x = self.width // 2 - 250
        y = 350

        pygame.draw.circle(
            self.screen,
            (230, 150, 40),
            (x, y),
            75
        )

        # Eyes
        pygame.draw.circle(
            self.screen,
            config.BLACK,
            (x - 25, y - 15),
            8
        )

        pygame.draw.circle(
            self.screen,
            config.BLACK,
            (x + 25, y - 15),
            8
        )

        # Nose
        pygame.draw.circle(
            self.screen,
            config.BLACK,
            (x, y + 15),
            10
        )

    # ========================================================
    # COW
    # ========================================================

    def draw_cow(self):

        x = self.width // 2 + 250
        y = 350

        pygame.draw.ellipse(
            self.screen,
            config.WHITE,
            (x - 80, y - 50, 160, 100)
        )

        pygame.draw.circle(
            self.screen,
            config.WHITE,
            (x, y - 70),
            50
        )

        # Spots
        pygame.draw.circle(
            self.screen,
            config.BLACK,
            (x - 35, y - 20),
            18
        )

        pygame.draw.circle(
            self.screen,
            config.BLACK,
            (x + 30, y - 70),
            15
        )

    # ========================================================
    # GESTURE
    # ========================================================

    def draw_gesture(self, gesture):

        if not gesture:
            gesture = config.GESTURE_NONE

        text = self.small_font.render(
            f"Gesture: {gesture}",
            True,
            config.BLACK
        )

        self.screen.blit(
            text,
            (40, self.height - 80)
        )

    # ========================================================
    # RESULT
    # ========================================================

    def draw_result(self, result):

        if not result:
            return

        if result == config.RESULT_PLAYER_WIN:

            message = "YOU WIN!"
            color = config.GREEN

        elif result == config.RESULT_COMPUTER_WIN:

            message = "COMPUTER WINS!"
            color = config.RED

        elif result == config.RESULT_DRAW:

            message = "DRAW!"
            color = config.YELLOW

        else:

            message = str(result)
            color = config.BLACK

        text = self.big_font.render(
            message,
            True,
            color
        )

        rect = text.get_rect(
            center=(
                self.width // 2,
                550
            )
        )

        self.screen.blit(
            text,
            rect
        )

    # ========================================================
    # INSTRUCTIONS
    # ========================================================

    def draw_instructions(self):

        text = self.small_font.render(
            "Show your hand gesture to play",
            True,
            config.GRAY
        )

        rect = text.get_rect(
            center=(
                self.width // 2,
                self.height - 30
            )
        )

        self.screen.blit(
            text,
            rect
        )

    # ========================================================
    # COMPLETE RENDER
    # ========================================================

    def render(
        self,
        player_score=0,
        computer_score=0,
        gesture=None,
        result=None
    ):

        self.clear()

        self.draw_title()

        self.draw_score(
            player_score,
            computer_score
        )

        self.draw_tiger()

        self.draw_cow()

        self.draw_gesture(
            gesture
        )

        self.draw_result(
            result
        )

        self.draw_instructions()

        pygame.display.flip()

    # ========================================================
    # FPS
    # ========================================================

    def tick(self, fps=config.FPS):

        self.clock.tick(fps)

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        pygame.display.quit()