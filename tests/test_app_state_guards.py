import main as game_main


def test_app_state_helpers_are_safe_before_game_starts():
    app = game_main.App.__new__(game_main.App)
    app.state = None

    assert app._prompt() == "Start a game to play."
    app._process_events()
    assert app._debug_lines() == []
