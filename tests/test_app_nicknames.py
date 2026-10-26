from unittest.mock import Mock, patch

import main as game_main
from src import config


def make_app(scene):
    app = game_main.App.__new__(game_main.App)
    app.audio = Mock()
    app.scene = scene
    app.prev_scene = scene
    app.menu_index = 0
    app.pending_mode = None
    app.nickname_inputs = {"nickname": "", "T": "", "C": ""}
    app.nickname_focus = None
    return app


def test_solo_setup_collects_nickname_on_side_selection_screen():
    app = make_app(game_main.MODE_SELECT)
    started = []
    app.start_game = (
        lambda mode, side=config.COW, round_number=1, player_names=None:
        started.append((mode, side, round_number, player_names))
    )

    with patch("main.pygame.key.start_text_input"):
        app.activate("single")

    assert app.scene == game_main.SIDE_SELECT
    assert app.nickname_focus == "nickname"

    app.nickname_inputs["nickname"] = "  Tiger Ace  "
    app.activate("tiger")

    assert started == [
        (config.MODE_SINGLE, config.TIGER, 1, {"T": "Tiger Ace", "C": "Computer"})
    ]


def test_two_player_setup_uses_both_names_from_side_selection_screen():
    app = make_app(game_main.MODE_SELECT)
    started = []
    app.start_game = (
        lambda mode, side=config.COW, round_number=1, player_names=None:
        started.append((mode, side, round_number, player_names))
    )

    with patch("main.pygame.key.start_text_input"):
        app.activate("two")

    assert app.scene == game_main.SIDE_SELECT
    assert app.nickname_focus == "T"

    app.nickname_inputs["T"] = "Tiger Player"
    app.nickname_inputs["C"] = "Cow Player"
    app.activate("start")

    assert started == [
        (config.MODE_TWO, config.COW, 1, {"T": "Tiger Player", "C": "Cow Player"})
    ]


def test_empty_nickname_uses_default_player_name():
    app = make_app(game_main.SIDE_SELECT)
    app.pending_mode = config.MODE_SINGLE
    started = []
    app.start_game = (
        lambda mode, side=config.COW, round_number=1, player_names=None:
        started.append((mode, side, round_number, player_names))
    )

    app.activate("cow")

    assert started == [
        (config.MODE_SINGLE, config.COW, 1, {"C": "Player 1", "T": "Computer"})
    ]


def test_back_from_solo_setup_returns_to_the_previous_menu():
    app = make_app(game_main.SIDE_SELECT)
    app.prev_scene = game_main.MODE_SELECT
    app.nickname_focus = "nickname"

    with patch("main.pygame.key.stop_text_input"):
        app.activate("back")

    assert app.scene == game_main.MODE_SELECT
    assert app.nickname_focus is None
