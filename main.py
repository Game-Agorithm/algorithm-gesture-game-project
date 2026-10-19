"""Launch the Khla Si Ko game.

main.py only coordinates the modules; the rules live in src/game_rules.py,
the state in src/game_state.py, drawing in src/renderer.py, and so on.

Per frame:
    events -> camera frame -> hand tracking -> gesture -> command
           -> game state (rules) -> sounds/animation -> renderer
"""

import logging
import threading
import time

import pygame

from src import config
from src.audio_manager import AudioManager
from src.game_rules import KhlaSiKoRules, SimpleBot
from src.game_state import GameState
from src.gesture_recognizer import (
    CMD_CANCEL, CMD_CONFIRM, CMD_SELECT, POINT, GestureRecognizer,
)
from src.hand_tracker import LandmarkSmoother
from src.renderer import Renderer

logger = logging.getLogger("khla")

TITLE, MODE_SELECT, SIDE_SELECT, SETTINGS, PLAYING, PAUSED, GAME_OVER = (
    "TITLE", "MODE_SELECT", "SIDE_SELECT", "SETTINGS", "PLAYING", "PAUSED", "GAME_OVER")

# Button ids on each menu screen, in the order the renderer draws them
# (used for keyboard navigation).
MENU_IDS = {
    TITLE: ["play", "single", "two", "settings", "exit"],
    MODE_SELECT: ["single", "two", "back"],
    SIDE_SELECT: ["tiger", "cow", "back"],
    PAUSED: ["resume", "restart", "menu", "exit"],
    GAME_OVER: ["again", "menu", "exit"],
}


def _start_camera():
    """Start camera + hand tracker. Returns (camera, tracker, error_text).

    On any problem camera/tracker are None and the game stays playable
    with the mouse.
    """
    camera = None
    try:
        from src.camera import Camera
        from src.hand_tracker import HandTracker

        camera = Camera(
            config.CAMERA_INDEX,
            config.CAMERA_WIDTH,
            config.CAMERA_HEIGHT,
            flip=config.CAMERA_FLIP,
        )
        tracker = HandTracker(
            max_num_hands=config.MAX_HANDS,
            detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
            draw_landmarks=config.SHOW_LANDMARKS,
            model_complexity=config.MODEL_COMPLEXITY,
        )
        return camera, tracker, ""
    except Exception as error:      # missing webcam, missing/wrong mediapipe, cv2 errors...
        if camera is not None:
            camera.release()
        logger.warning("Camera input unavailable; use the mouse instead. (%s)", error)
        return None, None, str(error)


def _computer_move(state, bot):
    """Let the bot play one legal action. Returns True if it acted."""
    action = bot.choose_action(state.board, state.cows_to_place)
    if action is None:
        return False
    if action["type"] == "place":
        return state.place_cow(*action["position"])
    return state.move_piece(action["start"], action["end"])


class VisionWorker:
    """Camera + MediaPipe in a background thread, so a slow webcam never
    freezes the 60 FPS interface. The main loop just asks for the latest result."""

    def __init__(self, preview_size):
        self.preview_size = preview_size
        self.online = False
        self.starting = False
        self.error = ""
        self.paused = False
        self.draw_landmarks = config.SHOW_LANDMARKS
        self.fps = 0.0
        self._lock = threading.Lock()
        self._latest = (0, None, None)           # (frame id, preview RGB, landmarks)
        self._stop = threading.Event()
        self._thread = None
        self._camera = self._tracker = None

    def start(self):
        self.starting = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="vision", daemon=True)
        self._thread.start()

    def latest(self):
        with self._lock:
            return self._latest

    def stop(self):
        self._stop.set()
        if self._thread is None:
            self._cleanup()
            return True
        self._thread.join(timeout=2.0)
        if self._thread.is_alive():
            logger.warning(
                "Vision thread did not stop within 2 seconds; it will release its resources when it exits."
            )
            return False
        return True

    def _cleanup(self):
        tracker, camera = self._tracker, self._camera
        self._camera = self._tracker = None
        self.online = False
        if tracker is not None:
            try:
                tracker.close()
            except Exception:
                logger.exception("Could not close the hand tracker.")
        if camera is not None:
            try:
                camera.release()
            except Exception:
                logger.exception("Could not release the camera.")

    def _run(self):
        failed, frames, started, frame_id = 0, 0, time.time(), 0
        try:
            import cv2

            while not self._stop.is_set():
                if self._camera is None:
                    self.starting = True
                    self._camera, self._tracker, self.error = _start_camera()
                    self.starting = False
                    if self._camera is None or self._tracker is None:
                        self._cleanup()
                        self._stop.wait(config.CAMERA_RETRY_INTERVAL)
                        continue
                    self.online = True
                    failed = 0

                if self.paused:
                    self._stop.wait(0.05)
                    continue
                camera, tracker = self._camera, self._tracker
                if camera is None or tracker is None:
                    self._cleanup()
                    continue
                try:
                    frame = camera.read()
                    if frame is None:
                        failed += 1
                        if failed > config.CAMERA_MAX_FAILED_READS:
                            self.error = "The camera stopped sending frames."
                            logger.warning(
                                "%s Reconnecting in %.1f seconds.",
                                self.error, config.CAMERA_RETRY_INTERVAL,
                            )
                            self._cleanup()
                            self._stop.wait(config.CAMERA_RETRY_INTERVAL)
                            continue
                        self._stop.wait(0.01)
                        continue
                    failed = 0
                    results = tracker.process(frame)
                    landmarks = tracker.get_landmarks(results)
                    if self.draw_landmarks and landmarks:
                        tracker.draw_hands(frame, results)
                    preview = cv2.cvtColor(cv2.resize(frame, self.preview_size), cv2.COLOR_BGR2RGB)
                    frame_id += 1
                    with self._lock:
                        self._latest = (frame_id, preview, landmarks)
                    frames += 1
                    if time.time() - started >= 1.0:
                        self.fps, frames, started = frames, 0, time.time()
                except Exception as error:
                    self.error = str(error)
                    logger.exception(
                        "Vision processing failed; reconnecting in %.1f seconds.",
                        config.CAMERA_RETRY_INTERVAL,
                    )
                    self._cleanup()
                    self._stop.wait(config.CAMERA_RETRY_INTERVAL)
        except Exception as error:
            logger.exception("Vision thread stopped: %s", error)
            self.error = str(error)
        finally:
            self.starting = False
            self._cleanup()


class App:
    def __init__(self):
        pygame.init()
        self.renderer = Renderer()
        self.audio = AudioManager()
        self.audio.set_muted(not config.SOUND_ENABLED)
        self.recognizer = GestureRecognizer()
        self.smoother = LandmarkSmoother(config.POINTER_SMOOTHING)

        self.running = True
        self.scene = TITLE
        self.prev_scene = TITLE
        self.menu_index = 0
        self.pending_mode = config.MODE_SINGLE

        self.state = None
        self.bot = None
        self.message = ""
        self.gesture = "NONE"
        self.pointer = None
        self.hover_pos = None
        self.last_hand_time = 0.0
        self.bot_timer = 0.0
        self.over_at = None
        self.debug = config.DEBUG
        self.camera_enabled = config.SHOW_CAMERA
        self._preview_id = -1
        self._preview_surface = None
        self._last_update = time.time()

        self.vision = VisionWorker(self.renderer.CAMERA_PREVIEW_SIZE)
        if self.camera_enabled:
            self.vision.start()

    # ==================================================================
    # Game control
    # ==================================================================

    def start_game(self, mode, side=config.COW, round_number=1):
        self.state = GameState(mode, side, round_number)
        self.bot = None
        if mode == config.MODE_SINGLE:
            bot_piece = self.state.bot_piece
            self.bot = SimpleBot(bot_piece, mistake_rate=config.BOT_MISTAKE_RATE[bot_piece])
        self.scene = PLAYING
        self.pointer = self.hover_pos = None
        self.bot_timer = 0.0
        self.over_at = None
        self.recognizer.reset()
        self.message = self._prompt()
        self.audio.play("button_click")

    def restart(self, new_round=False):
        if self.state is None:
            return
        number = self.state.round_number + (1 if new_round else 0)
        self.start_game(self.state.game_mode, self.state.player_side, number)

    def _prompt(self):
        state = self.state
        if state.winner:
            return "Game over."
        if not state.is_human_turn:
            return "Computer's turn."
        if state.current_turn == "C":
            return "Place a cow." if state.phase == "PLACEMENT" else "Move a cow."
        return "Move a tiger."

    def invalid(self, text, position=None):
        self.audio.play("error")
        self.renderer.flash_error(position)
        self.message = text

    def handle_board_click(self, position):
        """A mouse click, an OPEN PALM (SELECT) or a THUMBS UP (CONFIRM) on a node."""
        state = self.state
        if position is None or state is None or state.winner or not state.is_human_turn:
            return
        row, col = position
        side = state.current_turn

        if state.phase == "PLACEMENT" and side == "C":
            if not state.place_cow(row, col):
                self.invalid("Choose an empty point.", position)
            return

        if state.selected_pos is None:
            if state.board[row][col] != side:
                self.invalid("Select one of your pieces.", position)
            elif not state.get_valid_moves(position):
                self.invalid("That piece cannot move.", position)
            else:
                state.selected_pos = position
                self.audio.play("cow_select")
                self.message = "Selected. Choose a green point."
            return

        if position == state.selected_pos:
            state.selected_pos = None
            self.message = "Selection cleared."
        elif state.move_piece(state.selected_pos, position):
            pass                                    # sounds/animation come from the event
        elif state.board[row][col] == side and state.get_valid_moves(position):
            state.selected_pos = position
            self.audio.play("cow_select")
            self.message = "Selected. Choose a green point."
        else:
            self.invalid("That is not a legal move.", position)

    def cancel_selection(self):
        if self.state is not None and self.state.selected_pos is not None:
            self.state.selected_pos = None
            self.message = "Selection cancelled."
            self.audio.play("button_click")

    def _process_events(self):
        """React to what the rules engine reported: sound, animation, message."""
        state = self.state
        for event in state.pop_events():
            kind = event["type"]
            self.renderer.notify(event)
            if kind == "place":
                self.audio.play("cow_move")
                text = "Cow placed."
            elif kind == "move":
                self.audio.play("tiger_move" if event["piece"] == "T" else "cow_move")
                text = "Tiger moved." if event["piece"] == "T" else "Cow moved."
            elif kind == "capture":
                self.audio.play("tiger_roar")
                text = "The tiger captured a cow!"
            elif kind == "pass":
                text = ("Cows" if event["side"] == "C" else "Tigers") + " cannot move - turn passes."
            elif kind == "win":
                self.over_at = time.time() + config.GAME_OVER_DELAY
                text = "Game over."
            else:
                continue
            self.message = f"{text} {self._prompt()}" if kind != "win" else text
            self.bot_timer = 0.0

    # ==================================================================
    # Menus
    # ==================================================================

    def settings_options(self):
        on = lambda flag: "ON" if flag else "OFF"
        return [
            ("sound", f"SOUND: {on(not self.audio.muted)}"),
            ("camera", f"CAMERA CONTROL: {on(self.camera_enabled)}"),
            ("landmarks", f"HAND SKELETON: {on(self.vision.draw_landmarks)}"),
            ("debug", f"DEBUG MODE: {on(self.debug)}"),
            ("retry", "RETRY CAMERA" + ("  (online)" if self.vision.online else "")),
            ("back", "BACK"),
        ]

    def menu_ids(self):
        if self.scene == SETTINGS:
            return [bid for bid, _ in self.settings_options()]
        return MENU_IDS.get(self.scene, [])

    def go(self, scene):
        self.prev_scene, self.scene, self.menu_index = self.scene, scene, 0

    def start_vision(self):
        self.vision.stop()
        self.vision = VisionWorker(self.renderer.CAMERA_PREVIEW_SIZE)
        self.vision.paused = not self.camera_enabled
        self.vision.start()

    def toggle_camera(self):
        self.camera_enabled = not self.camera_enabled
        if self.camera_enabled and not (self.vision.online or self.vision.starting):
            self.start_vision()
        self.vision.paused = not self.camera_enabled
        self.pointer = None
        self.recognizer.reset()

    def activate(self, bid):
        self.audio.play("button_click")
        if bid == "play":
            self.go(MODE_SELECT)
        elif bid == "single":
            self.pending_mode = config.MODE_SINGLE
            self.go(SIDE_SELECT)
        elif bid == "two":
            self.start_game(config.MODE_TWO)
        elif bid in ("tiger", "cow"):
            self.start_game(config.MODE_SINGLE, config.TIGER if bid == "tiger" else config.COW)
        elif bid == "settings":
            self.go(SETTINGS)
        elif bid == "back":
            self.go(MODE_SELECT if self.scene == SIDE_SELECT and self.prev_scene == MODE_SELECT else TITLE)
        elif bid == "exit":
            self.running = False
        elif bid == "resume":
            self.scene = PLAYING
        elif bid == "restart":
            self.restart()
        elif bid == "again":
            self.restart(new_round=True)
        elif bid == "reset":
            self.restart()
        elif bid == "menu":
            self.go(TITLE)
        elif bid == "camera":
            self.toggle_camera()
        elif bid == "sound":
            self.audio.toggle_muted()
        elif bid == "landmarks":
            self.vision.draw_landmarks = not self.vision.draw_landmarks
        elif bid == "debug":
            self.debug = not self.debug
        elif bid == "retry":
            self.camera_enabled = True
            self.start_vision()

    # ==================================================================
    # Input
    # ==================================================================

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.handle_key(event.key)
            elif event.type == pygame.MOUSEMOTION:
                bid = self.renderer.button_at(event.pos)
                ids = self.menu_ids()
                if bid in ids and self.scene != PLAYING:
                    self.menu_index = ids.index(bid)
                elif self.scene == PLAYING and self.state and self.state.is_human_turn:
                    self.hover_pos = self.renderer.board_position_at(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                bid = self.renderer.button_at(event.pos)
                if bid:
                    self.activate(bid)
                elif self.scene == PLAYING:
                    self.handle_board_click(self.renderer.board_position_at(event.pos))

    def handle_key(self, key):
        scene = self.scene
        if key == pygame.K_F11:
            self.renderer.toggle_fullscreen()
        elif key == pygame.K_F3:
            self.debug = not self.debug
        elif key == pygame.K_s:
            self.audio.toggle_muted()

        elif scene == PLAYING:
            if key == pygame.K_ESCAPE:
                self.scene, self.menu_index = PAUSED, 0
            elif key == pygame.K_r:
                self.restart()
            elif key == pygame.K_m:
                self.go(TITLE)
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.handle_board_click(self.hover_pos)

        else:                                       # menus, pause, game over
            ids = self.menu_ids()
            if key in (pygame.K_UP, pygame.K_LEFT) and ids:
                self.menu_index = (self.menu_index - 1) % len(ids)
                self.audio.play("button_click")
            elif key in (pygame.K_DOWN, pygame.K_RIGHT) and ids:
                self.menu_index = (self.menu_index + 1) % len(ids)
                self.audio.play("button_click")
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and ids:
                self.activate(ids[self.menu_index])
            elif key == pygame.K_ESCAPE:
                if scene == TITLE:
                    self.running = False
                elif scene == PAUSED:
                    self.scene = PLAYING
                elif scene == GAME_OVER:
                    self.go(TITLE)
                else:
                    self.go(TITLE)
            elif key == pygame.K_1 and scene in (TITLE, MODE_SELECT, SIDE_SELECT):
                self.activate("single")
            elif key == pygame.K_2 and scene in (TITLE, MODE_SELECT, SIDE_SELECT):
                self.activate("two")
            elif key == pygame.K_t and scene == SIDE_SELECT:
                self.activate("tiger")
            elif key == pygame.K_c and scene == SIDE_SELECT:
                self.activate("cow")
            elif key == pygame.K_r and scene in (PAUSED, GAME_OVER):
                self.restart(new_round=scene == GAME_OVER)
            elif key == pygame.K_m and scene in (PAUSED, GAME_OVER):
                self.go(TITLE)

    # ==================================================================
    # Per-frame update
    # ==================================================================

    def _update_gestures(self, now):
        """Camera frame -> landmarks -> gesture -> command -> game action."""
        frame_id, preview, landmarks = self.vision.latest()
        if frame_id != self._preview_id and preview is not None:
            self._preview_id = frame_id
            self._preview_surface = pygame.image.frombuffer(
                preview.tobytes(), self.renderer.CAMERA_PREVIEW_SIZE, "RGB")

        if not (self.vision.online and self.camera_enabled):
            self.gesture, self.pointer = "NONE", None
            return
        if self.scene != PLAYING or self.state is None or not self.state.is_human_turn:
            self.gesture = self.recognizer.recognize(landmarks, now).gesture
            self.pointer = None
            return

        result = self.recognizer.recognize(landmarks, now)
        self.gesture = result.gesture
        if landmarks:
            self.last_hand_time = now
            if result.gesture == POINT and result.raw_gesture == POINT:
                # Only the pointing finger moves the cursor. Once the hand
                # changes to another gesture the hovered node stays frozen, so
                # opening the palm cannot drag the selection off the node.
                tip = self.smoother.smooth([tuple(landmarks[8][:2])])[0]
                self.pointer = self.renderer.camera_point_to_screen(*tip)
                node = self.renderer.board_position_at(self.pointer)
                if node is not None:
                    self.hover_pos = node
        else:
            self.pointer = None
            self.smoother.smooth([])
            if now - self.last_hand_time > config.HOVER_RELEASE_SECONDS and self.hover_pos is not None:
                self.hover_pos = None

        if result.command in (CMD_SELECT, CMD_CONFIRM):
            self.handle_board_click(self.hover_pos)
        elif result.command == CMD_CANCEL:
            self.cancel_selection()

    def update(self):
        now = time.time()
        dt = min(0.1, now - self._last_update)
        self._last_update = now

        self._update_gestures(now)
        if self.scene != PLAYING or self.state is None:
            return

        if self.bot is not None and not self.state.winner and self.state.current_turn == self.bot.side:
            self.bot_timer += dt
            if self.bot_timer >= config.BOT_DELAY:
                self.bot_timer = 0.0
                if not _computer_move(self.state, self.bot):
                    self.state.update_winner()
        self._process_events()

        if self.over_at is not None and now >= self.over_at:
            self.over_at = None
            self.scene, self.menu_index = GAME_OVER, 0
            tigers = self.state.winner == "TIGERS"
            self.audio.play("tiger_win" if tigers else "cow_win")
            if self.state.player_piece is not None and tigers != (self.state.player_piece == "T"):
                self.audio.play("game_over")

    # ==================================================================
    # Drawing
    # ==================================================================

    def _debug_lines(self):
        s = self.state
        index = lambda positions: [self._index(p) for p in positions]
        legal = ([self._index(m["to"]) for m in s.get_valid_moves(s.selected_pos)]
                 if s.selected_pos else [])
        return [
            f"FPS: {self.renderer.clock.get_fps():.0f}  Cam: {self.vision.fps:.0f}  Gesture: {self.gesture}  "
            f"Turn: {s.current_turn}  Phase: {s.phase}",
            f"Tiger: {index(s.tiger_positions)}  Cows: {index(s.cow_positions)}",
            f"Selected: {self._index(s.selected_pos)}  Hover: {self._index(self.hover_pos)}  Legal: {legal}",
        ]

    @staticmethod
    def _index(position):
        return None if position is None else KhlaSiKoRules.node_index(*position)

    def draw(self):
        r = self.renderer
        if self.scene == TITLE:
            r.draw_title(self.menu_index)
        elif self.scene == MODE_SELECT:
            r.draw_mode_select(self.menu_index)
        elif self.scene == SIDE_SELECT:
            r.draw_side_select(self.menu_index)
        elif self.scene == SETTINGS:
            r.draw_settings(self.settings_options(), self.menu_index)
        elif self.state is not None:
            status = {
                "online": self.vision.online and self.camera_enabled,
                "starting": self.vision.starting and self.camera_enabled,
                "reason": self.vision.error,
            }
            r.draw_game(
                self.state, self.message, self.gesture, self.pointer, self.hover_pos,
                self._preview_surface, status,
                self._debug_lines() if self.debug else None, self.camera_enabled,
            )
            if self.scene == PAUSED:
                r.draw_pause(self.menu_index)
            elif self.scene == GAME_OVER:
                r.draw_game_over(self.state, self.menu_index)
        r.present()
        r.tick()

    def run(self):
        try:
            while self.running:
                self.handle_events()
                self.update()
                self.draw()
        finally:
            self.vision.stop()
            self.audio.close()
            self.renderer.close()
            pygame.quit()


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    App().run()


if __name__ == "__main__":
    main()
