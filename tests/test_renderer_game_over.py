from types import SimpleNamespace
from unittest.mock import Mock

from src import config
from src.renderer import Renderer


def test_game_over_winner_title_uses_winning_players_nickname():
    renderer = Renderer.__new__(Renderer)
    renderer.buttons = []
    renderer.width = 1080
    renderer.palette = {
        "tiger": (255, 0, 0),
        "cow": (0, 255, 0),
        "gold": (255, 255, 0),
        "highlight": (0, 0, 255),
        "accent_secondary": (128, 128, 128),
        "glow": (0, 0, 0),
        "muted": (128, 128, 128),
        "danger": (255, 0, 0),
    }
    renderer._rng = Mock()
    renderer._rng.random.return_value = 0.5
    renderer._dim = Mock()
    renderer._panel = Mock()
    renderer._draw_piece = Mock()
    renderer._font = Mock()
    renderer._button = Mock()
    renderer._text = Mock()

    renderer.draw_game_over(
        SimpleNamespace(winner="COWS", game_mode=config.MODE_TWO),
        player_names={"T": "Tiger Ace", "C": "Cow Player"},
    )

    assert renderer._text.call_args_list[0].args[0] == "Cow Player WINS!"
