import main as game_main
from src import config
from src.renderer import Renderer


class ButtonRenderer:
    def __init__(self):
        self.hovered_button = None

    def button_at(self, point):
        return self.hovered_button


def make_app():
    app = game_main.App.__new__(game_main.App)
    app.renderer = ButtonRenderer()
    app.pointer = (10, 10)
    app.scene = game_main.TITLE
    app.menu_index = 0
    app._button_hold_target = None
    app._button_hold_started = None
    app._button_hold_progress = 0.0
    app._button_gesture_fired = False
    app.activated = []
    app.activate = app.activated.append
    return app


def test_pointing_must_hold_on_a_button_for_three_seconds():
    app = make_app()
    app.renderer.hovered_button = "play"

    app._update_button_gesture(True, 1.0)
    app._update_button_gesture(True, 1.0 + config.GESTURE_BUTTON_HOLD_SECONDS - 0.01)
    assert app.activated == []

    app._update_button_gesture(True, 1.0 + config.GESTURE_BUTTON_HOLD_SECONDS)
    app._update_button_gesture(True, 5.0)
    assert app.activated == ["play"]


def test_leaving_a_button_restarts_the_hold_timer():
    app = make_app()
    app.renderer.hovered_button = "play"
    app._update_button_gesture(True, 0.0)

    app.renderer.hovered_button = "settings"
    app._update_button_gesture(True, 2.0)
    app._update_button_gesture(True, 4.99)
    assert app.activated == []

    app._update_button_gesture(True, 5.0)
    assert app.activated == ["settings"]


def test_releasing_pointing_allows_another_button_click():
    app = make_app()
    app.renderer.hovered_button = "play"
    app._update_button_gesture(True, 0.0)
    app._update_button_gesture(True, config.GESTURE_BUTTON_HOLD_SECONDS)
    app._update_button_gesture(False, 3.1)
    app.renderer.hovered_button = "exit"
    app._update_button_gesture(True, 4.0)
    app._update_button_gesture(True, 4.0 + config.GESTURE_BUTTON_HOLD_SECONDS)

    assert app.activated == ["play", "exit"]


def test_camera_pointer_maps_active_area_across_the_full_window():
    renderer = Renderer.__new__(Renderer)
    renderer.width, renderer.height = 1280, 720
    left, top, right, bottom = config.CAMERA_ACTIVE_AREA

    assert renderer.camera_point_to_screen(left, top) == (0, 0)
    assert renderer.camera_point_to_screen(right, bottom) == (1279, 719)
    assert renderer.camera_point_to_screen((left + right) / 2, (top + bottom) / 2) == (640, 360)


def test_board_pointer_hits_screen_positions_of_rendered_nodes():
    renderer = Renderer.__new__(Renderer)
    renderer.board_step = renderer.BOARD_SIZE / 3

    assert renderer.board_position_at(renderer.board_node(0, 0)) == (0, 0)
    assert renderer.board_position_at(renderer.board_node(3, 3)) == (3, 3)
    assert renderer.board_position_at((1279, 719)) is None


def test_game_style_flow_continues_to_mode_and_supports_back_navigation():
    class Audio:
        def play(self, _sound):
            return

    class StyleRenderer:
        def __init__(self):
            self.styles = []

        def set_style(self, style):
            self.styles.append(style)

    app = game_main.App.__new__(game_main.App)
    app.audio = Audio()
    app.renderer = StyleRenderer()
    app.scene = game_main.TITLE
    app.prev_scene = game_main.TITLE
    app.menu_index = 0
    app.pending_mode = None
    app.selected_game_style = config.GAME_STYLE_MODERN

    app.activate("play")
    assert app.scene == game_main.STYLE_SELECT
    app.activate(config.GAME_STYLE_JUNGLE)
    assert app.selected_game_style == config.GAME_STYLE_JUNGLE
    assert app.renderer.styles == [config.GAME_STYLE_JUNGLE]
    app.activate("continue")
    assert app.scene == game_main.MODE_SELECT
    app.activate("back")
    assert app.scene == game_main.STYLE_SELECT


def test_direct_single_player_shortcut_still_selects_style_before_side():
    class Audio:
        def play(self, _sound):
            return

    app = game_main.App.__new__(game_main.App)
    app.audio = Audio()
    app.renderer = ButtonRenderer()
    app.scene = game_main.TITLE
    app.prev_scene = game_main.TITLE
    app.menu_index = 0
    app.pending_mode = None
    app.selected_game_style = config.GAME_STYLE_MODERN
    app.renderer.set_style = lambda _style: None

    app.activate("single")
    assert app.scene == game_main.STYLE_SELECT
    assert app.pending_mode == config.MODE_SINGLE
    app.activate("continue")
    assert app.scene == game_main.SIDE_SELECT
