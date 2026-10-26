from unittest.mock import Mock, patch

import main as game_main
from src import config
from src.renderer import Renderer


class ButtonRenderer:
    def __init__(self):
        self.hovered_button = None

    def button_at(self, point):
        return self.hovered_button


def set_hovered_button(app, button):
    setattr(app.renderer, "hovered_button", button)


def activated_buttons(app):
    return getattr(app, "_activated_buttons")


def make_app():
    app = game_main.App.__new__(game_main.App)
    setattr(app, "renderer", ButtonRenderer())
    app.pointer = (10, 10)
    app.scene = game_main.TITLE
    app.menu_index = 0
    activated = []
    setattr(app, "_activated_buttons", activated)
    setattr(app, "activate", activated.append)
    return app


def test_pointing_moves_hover_without_clicking():
    app = make_app()
    set_hovered_button(app, "single")

    clicked = app._update_button_gesture(True, False)

    assert clicked is False
    assert app.menu_index == 1
    assert activated_buttons(app) == []


def test_open_palm_clicks_the_hovered_button_once():
    app = make_app()
    set_hovered_button(app, "play")

    clicked = app._update_button_gesture(False, True)

    assert clicked is True
    assert activated_buttons(app) == ["play"]


def test_open_palm_clicks_buttons_across_screens():
    app = make_app()
    buttons = ("start", "resume", "again", "reset", "camera")

    for button in buttons:
        set_hovered_button(app, button)
        assert app._update_button_gesture(False, True) is True

    assert activated_buttons(app) == list(buttons)


def test_gameplay_controls_are_clickable_with_open_palm():
    app = game_main.App.__new__(game_main.App)
    renderer = ButtonRenderer()
    setattr(app, "renderer", renderer)
    app.pointer = (10, 10)
    app.scene = game_main.PLAYING
    app.audio = Mock()
    app.restart = Mock()
    app.go = Mock()
    app.toggle_camera = Mock()

    for button in ("reset", "menu", "camera"):
        renderer.hovered_button = button
        assert app._update_button_gesture(False, True) is True

    app.restart.assert_called_once_with()
    app.go.assert_called_once_with(game_main.TITLE)
    app.toggle_camera.assert_called_once_with()


def test_open_palm_outside_a_button_does_not_click_or_consume_board_input():
    app = make_app()
    set_hovered_button(app, None)

    clicked = app._update_button_gesture(False, True)

    assert clicked is False
    assert activated_buttons(app) == []


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


def test_camera_pointer_is_drawn_blue():
    renderer = Renderer.__new__(Renderer)
    renderer.screen = object()
    renderer.palette = {"text": (255, 255, 255)}

    with patch("src.renderer.pygame.draw.circle") as draw_circle:
        renderer.draw_pointer((100, 120))

    assert draw_circle.call_args_list[0].args[1] == config.POINTER_BLUE


def test_gameplay_controls_highlight_under_camera_pointer():
    renderer = Renderer.__new__(Renderer)
    renderer.palette = {
        "highlight": (1, 1, 1),
        "accent_secondary": (2, 2, 2),
        "accent": (3, 3, 3),
        "muted": (4, 4, 4),
    }
    renderer._button = lambda *args: calls.append(args)
    calls = []

    renderer._draw_game_controls((500, 670), camera_on=True)

    assert [call[0] for call in calls] == ["reset", "menu", "camera"]
    assert [call[3] for call in calls] == [False, False, True]


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
    setattr(app, "audio", Audio())
    renderer = StyleRenderer()
    setattr(app, "renderer", renderer)
    app.scene = game_main.TITLE
    app.prev_scene = game_main.TITLE
    app.menu_index = 0
    app.pending_mode = None
    app.selected_game_style = config.GAME_STYLE_MODERN

    app.activate("play")
    assert app.scene == game_main.STYLE_SELECT
    app.activate(config.GAME_STYLE_JUNGLE)
    assert app.selected_game_style == config.GAME_STYLE_JUNGLE
    assert renderer.styles == [config.GAME_STYLE_JUNGLE]
    app.activate("continue")
    assert app.scene == game_main.MODE_SELECT
    app.activate("back")
    assert app.scene == game_main.STYLE_SELECT


def test_direct_single_player_shortcut_still_selects_style_before_side():
    class Audio:
        def play(self, _sound):
            return

    app = game_main.App.__new__(game_main.App)
    setattr(app, "audio", Audio())
    renderer = ButtonRenderer()
    setattr(app, "renderer", renderer)
    app.scene = game_main.TITLE
    app.prev_scene = game_main.TITLE
    app.menu_index = 0
    app.pending_mode = None
    app.selected_game_style = config.GAME_STYLE_MODERN
    setattr(renderer, "set_style", lambda _style: None)

    app.activate("single")
    assert app.scene == game_main.STYLE_SELECT
    assert app.pending_mode == config.MODE_SINGLE
    app.activate("continue")
    assert app.scene == game_main.SIDE_SELECT
