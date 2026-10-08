"""Launch the Khla Si Ko game."""

import random

import pygame

from src import config
from src.audio_manager import AudioManager
from src.game_rules import KhlaSiKoRules
from src.game_state import GameState
from src.gesture_recognizer import GestureRecognizer
from src.renderer import Renderer


def _start_camera():
    """Start optional camera input; the game remains playable with a mouse."""
    camera = None
    try:
        import cv2

        from src.camera import Camera
        from src.hand_tracker import HandTracker

        camera = Camera(
            config.CAMERA_INDEX,
            config.CAMERA_WIDTH,
            config.CAMERA_HEIGHT,
        )
        tracker = HandTracker(
            max_num_hands=config.MAX_HANDS,
            detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
            draw_landmarks=config.SHOW_LANDMARKS,
        )
        return cv2, camera, tracker
    except (AttributeError, ImportError, OSError, RuntimeError) as error:
        if camera is not None:
            camera.release()
        print(f"Camera input unavailable; use the mouse instead. ({error})")
        return None, None, None


def _computer_move(state):
    """Make one legal tiger move, preferring a capture when available."""
    moves = []
    for row in range(KhlaSiKoRules.BOARD_SIZE):
        for col in range(KhlaSiKoRules.BOARD_SIZE):
            if state.board[row][col] == "T":
                for move in KhlaSiKoRules.get_valid_tiger_moves(
                    state.board, (row, col)
                ):
                    moves.append(((row, col), move))

    if not moves:
        if state.phase == "PLACEMENT":
            state.switch_turn()
        else:
            state.update_winner()
        return False

    captures = [move for move in moves if move[1]["is_capture"]]
    start, move = random.choice(captures or moves)
    return state.move_piece(start, move["to"])


def main():
    pygame.init()
    renderer = Renderer()
    audio = AudioManager()
    state = GameState()
    recognizer = GestureRecognizer()
    cv2, camera, tracker = _start_camera() if config.SHOW_CAMERA else (None, None, None)

    running = True
    message = "Place all 12 cows. Pinch or click an empty point."
    gesture = "NONE"
    pointer = None
    previous_gesture = "NONE"
    previous_winner = None

    def handle_board_click(position):
        nonlocal message
        if position is None or state.winner or state.current_turn != "C":
            return

        row, col = position
        if state.phase == "PLACEMENT":
            if state.place_cow(row, col):
                audio.play_cow()
                message = "Cow placed."
            else:
                message = "Choose an empty point."
            return

        if state.selected_pos is None:
            if state.board[row][col] == "C":
                state.selected_pos = position
                message = "Choose an adjacent empty point."
            else:
                message = "Select one of your cows."
            return

        if position == state.selected_pos:
            state.selected_pos = None
            message = "Selection cleared."
        elif state.move_piece(state.selected_pos, position):
            state.selected_pos = None
            audio.play_cow()
            message = "Cow moved."
        elif state.board[row][col] == "C":
            state.selected_pos = position
            message = "Cow selected. Choose an adjacent empty point."
        else:
            message = "That is not a legal move."

    try:
        while running:
            renderer.tick()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        state = GameState()
                        message = "New game. Place all 12 cows."
                        previous_winner = None
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    handle_board_click(renderer.board_position_at(event.pos))

            if camera is not None and tracker is not None:
                frame = camera.read()
                if frame is None:
                    print("Camera frame capture failed; continuing with mouse input.")
                    camera.release()
                    tracker.close()
                    camera = tracker = cv2 = None
                else:
                    frame = cv2.flip(frame, 1)
                    results = tracker.process(frame)
                    landmarks = tracker.get_landmarks(results)
                    gesture = recognizer.detect_gesture(landmarks)
                    if landmarks:
                        tip_x, tip_y = landmarks[8][:2]
                        pointer = renderer.camera_point_to_screen(tip_x, tip_y)
                    else:
                        pointer = None

                    if gesture == "GRAB" and previous_gesture != "GRAB":
                        handle_board_click(
                            renderer.board_position_at(pointer) if pointer else None
                        )
                    previous_gesture = gesture

                    if config.SHOW_LANDMARKS:
                        tracker.draw_hands(frame, results)
                    cv2.imshow("Khla Si Ko - Camera", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        running = False

            if not state.winner and state.current_turn == "T":
                captured_before = state.captured_cows
                _computer_move(state)
                if state.captured_cows > captured_before:
                    audio.play_tiger()
                    message = "The tiger captured a cow."
                else:
                    message = "Tiger moved."

            if state.winner and state.winner != previous_winner:
                if state.winner == "TIGERS":
                    audio.play_lose()
                    message = "The tiger wins. Press R to play again."
                else:
                    audio.play_win()
                    message = "The cows win. Press R to play again."
                previous_winner = state.winner

            renderer.draw_game(state, message, gesture, pointer)

    finally:
        if camera is not None:
            camera.release()
        if tracker is not None:
            tracker.close()
        if cv2 is not None:
            cv2.destroyAllWindows()
        audio.close()
        renderer.close()
        pygame.quit()


if __name__ == "__main__":
    main()
