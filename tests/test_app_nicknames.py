from types import SimpleNamespace

import main as game_main
from src import config


class AudioStub:
    def play(self, _sound):
        pass


def make_app(scene):
    app = game_main.App.__new__(game_main.App)
    app.audio = AudioStub()
    app.scene = scene
    app.prev_scene = scene
    app.menu_index = 0
    app.pending_mode = config.MODE_SINGLE
    app.pending_side = config.COW
    app.nickname_sides = []
    app.nickname_values = {}
    app.nickname_index = 0
    app.nickname_input = ""
    app.nickname_error = ""
    app.nickname_return_scene = game_main.MODE_SELECT
    app.nickname_return_parent = game_main.TITLE
    return app


def test_solo_side_selection_requests_nickname_before_starting_game():
    app = make_app(game_main.SIDE_SELECT)
    started = []
    app.start_game = lambda mode, side, player_names=None: started.append(
        (mode, side, player_names)
    )

    app.activate("tiger")

    assert app.scene == game_main.NICKNAME_ENTRY
    assert app.nickname_sides == ["T"]
    assert not started

    app.nickname_input = "  Tiger Ace  "
    app.activate("continue")

    assert started == [(config.MODE_SINGLE, config.TIGER, {"T": "Tiger Ace"})]


def test_two_player_flow_collects_both_names_before_starting():
    app = make_app(game_main.MODE_SELECT)
    started = []
    app.start_game = lambda mode, side, player_names=None: started.append(
        (mode, side, player_names)
    )

    app.activate("two")
    app.nickname_input = "Tiger Player"
    app.activate("continue")

    assert app.scene == game_main.NICKNAME_ENTRY
    assert app.nickname_index == 1
    assert app.nickname_input == ""
    assert not started

    app.nickname_input = "Cow Player"
    app.activate("continue")

    assert started == [(config.MODE_TWO, config.COW, {"T": "Tiger Player", "C": "Cow Player"})]


def test_winner_name_uses_player_nickname_or_computer():
    app = make_app(game_main.PLAYING)
    app.player_names = {"T": "Tiger Player", "C": "Cow Player"}

    tiger_winner = SimpleNamespace(
        winner="TIGERS", game_mode=config.MODE_TWO, player_piece=None
    )
    cow_winner = SimpleNamespace(
        winner="COWS", game_mode=config.MODE_SINGLE, player_piece="C"
    )
    bot_winner = SimpleNamespace(
        winner="TIGERS", game_mode=config.MODE_SINGLE, player_piece="C"
    )

    assert app._winner_name(tiger_winner) == "Tiger Player"
    assert app._winner_name(cow_winner) == "Cow Player"
    assert app._winner_name(bot_winner) == "Computer"


def test_empty_nickname_does_not_start_game():
    app = make_app(game_main.SIDE_SELECT)
    started = []
    app.start_game = lambda *args, **kwargs: started.append((args, kwargs))
    app.activate("cow")

    app.activate("continue")

    assert app.nickname_error
    assert not started


def test_canceling_solo_nickname_returns_to_the_original_side_menu():
    app = make_app(game_main.SIDE_SELECT)
    app.prev_scene = game_main.MODE_SELECT
    app.activate("cow")

    app.activate("back")

    assert app.scene == game_main.SIDE_SELECT
    assert app.prev_scene == game_main.MODE_SELECT
