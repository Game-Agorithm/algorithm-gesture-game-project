from unittest.mock import Mock, patch

import pygame

from main import App
from src import config


def _app_for_start():
    app = App.__new__(App)
    app.renderer = Mock()
    app.selected_game_style = config.DEFAULT_GAME_STYLE
    app.player_names = {"T": "Player 1", "C": "Player 2"}
    app.bot = None
    app.scene = None
    app.pointer = None
    app.hover_pos = None
    app.bot_timer = 0.0
    app.over_at = None
    app.recognizer = Mock()
    app.audio = Mock()
    return app


def test_nickname_is_trimmed_and_empty_input_uses_default():
    assert App._clean_nickname("  Sakreach  ", "Player 1") == "Sakreach"
    assert App._clean_nickname("   ", "Player 1") == "Player 1"


def test_clicking_each_nickname_field_sets_its_focus():
    app = App.__new__(App)
    app.audio = Mock()

    for field_id, expected_focus in (
        ("nickname", "nickname"),
        ("nickname_T", "T"),
        ("nickname_C", "C"),
    ):
        app.activate(field_id)
        assert app.nickname_focus == expected_focus


def test_text_input_updates_the_focused_player_name():
    app = App.__new__(App)
    app.scene = "SIDE_SELECT"
    app.nickname_focus = "C"
    app.nickname_inputs = {"nickname": "", "T": "", "C": ""}
    text_event = Mock(type=pygame.TEXTINPUT, text="Dara")

    with patch.object(pygame.event, "get", return_value=[text_event]):
        app.handle_events()

    assert app.nickname_inputs["C"] == "Dara"


def test_single_player_names_follow_the_selected_animal_and_bot():
    app = _app_for_start()

    with patch.object(pygame.key, "stop_text_input"):
        app.start_game(
            config.MODE_SINGLE,
            config.TIGER,
            player_names={"T": "Sakreach", "C": "Computer"},
        )

    assert app.player_names == {"T": "Sakreach", "C": "Computer"}
    assert app.bot is not None
    assert app.bot.side == "C"


def test_restart_preserves_two_player_nicknames():
    app = _app_for_start()

    with patch.object(pygame.key, "stop_text_input"):
        app.start_game(
            config.MODE_TWO,
            player_names={"T": "Sakreach", "C": "Dara"},
        )
        app.restart(new_round=True)

    assert app.player_names == {"T": "Sakreach", "C": "Dara"}
    assert app.state is not None
    assert app.state.round_number == 2
    assert app.bot is None
