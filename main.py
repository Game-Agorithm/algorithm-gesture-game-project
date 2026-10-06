"""
Khla Si Ko - Main Application

Main controller that connects:

Camera
Hand Tracker
Gesture Recognizer
Game Rules
Game State
Renderer
Audio Manager
"""

import pygame

from src import config

from src.camera import Camera
from src.hand_tracker import HandTracker
from src.gesture_recognizer import GestureRecognizer

from src.game_rules import determine_winner
from src.game_state import GameState

from src.renderer import Renderer
from src.audio_manager import AudioManager


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # INITIALIZE PYGAME
    # --------------------------------------------------------

    pygame.init()

    # --------------------------------------------------------
    # CREATE COMPONENTS
    # --------------------------------------------------------

    camera = Camera()

    hand_tracker = HandTracker()

    gesture_recognizer = GestureRecognizer()

    game_state = GameState()

    renderer = Renderer()

    audio = AudioManager()

    # --------------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------------

    while game_state.running:

        # ====================================================
        # 1. HANDLE EVENTS
        # ====================================================

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                game_state.running = False

            elif event.type == pygame.KEYDOWN:

                # ESC = exit
                if event.key == pygame.K_ESCAPE:

                    game_state.running = False

                # R = reset
                elif event.key == pygame.K_r:

                    game_state.reset_game()

                    audio.play_click()

        # ====================================================
        # 2. GET CAMERA FRAME
        # ====================================================

        frame = camera.read()

        if frame is None:

            continue

        # ====================================================
        # 3. TRACK HAND
        # ====================================================

        hand_results = hand_tracker.process(
            frame
        )

        # ====================================================
        # 4. RECOGNIZE GESTURE
        # ====================================================

        player_gesture = gesture_recognizer.recognize(
            hand_results
        )

        game_state.player_gesture = player_gesture

        # ====================================================
        # 5. GAME LOGIC
        # ====================================================

        # Only process a valid gesture.
        if (
            player_gesture != config.GESTURE_NONE
            and game_state.can_play
        ):

            # Your game_state / game_rules team code
            # should control when a round is played.

            computer_gesture = (
                game_state.generate_computer_gesture()
            )

            game_state.computer_gesture = (
                computer_gesture
            )

            # ----------------------------------------------
            # Determine winner
            # ----------------------------------------------

            result = determine_winner(
                player_gesture,
                computer_gesture
            )

            game_state.result = result

            # ----------------------------------------------
            # Update score
            # ----------------------------------------------

            game_state.update_score(
                result
            )

            # ----------------------------------------------
            # Play sound
            # ----------------------------------------------

            if result == config.RESULT_PLAYER_WIN:

                audio.play_win()

            elif result == config.RESULT_COMPUTER_WIN:

                audio.play_lose()

            elif result == config.RESULT_DRAW:

                audio.play_draw()

        # ====================================================
        # 6. RENDER
        # ====================================================

        renderer.render(
            player_score=game_state.player_score,

            computer_score=game_state.computer_score,

            gesture=game_state.player_gesture,

            result=game_state.result
        )

        # ====================================================
        # 7. FPS
        # ====================================================

        renderer.tick(
            config.FPS
        )

    # ========================================================
    # CLEAN UP
    # ========================================================

    camera.release()

    hand_tracker.close()

    audio.close()

    renderer.close()

    pygame.quit()


# ============================================================
# PROGRAM ENTRY
# ============================================================

if __name__ == "__main__":

    main()