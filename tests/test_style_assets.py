from unittest.mock import patch

from src import config
from src.renderer import Renderer


def test_styles_use_their_matching_tiger_and_cow_assets():
    assert config.GAME_STYLES[config.GAME_STYLE_MODERN]["tiger_image"] == (
        config.ICON_DIR / "tiger_tech.png"
    )
    assert config.GAME_STYLES[config.GAME_STYLE_MODERN]["cow_image"] == (
        config.ICON_DIR / "cow_tech.png"
    )
    assert config.GAME_STYLES[config.GAME_STYLE_JUNGLE]["tiger_image"] == (
        config.ICON_DIR / "tiger_jungle.png"
    )
    assert config.GAME_STYLES[config.GAME_STYLE_JUNGLE]["cow_image"] == (
        config.ICON_DIR / "cow_jungle.png"
    )


def test_renderer_uses_the_selected_style_asset_pair():
    for style in (config.GAME_STYLE_MODERN, config.GAME_STYLE_JUNGLE):
        assets = {"T": object(), "C": object()}
        renderer = Renderer.__new__(Renderer)
        renderer.game_style = style
        renderer._pieces = {
            (other_style, piece): object()
            for other_style in config.GAME_STYLES
            for piece in ("T", "C")
        }
        renderer._pieces.update({(style, piece): image for piece, image in assets.items()})
        renderer._image_cache = {}

        with patch(
            "src.renderer.pygame.transform.smoothscale",
            side_effect=lambda image, size: (image, size),
        ):
            for piece, expected_image in assets.items():
                rendered = renderer._piece_image(piece, 40)
                assert rendered[0] is expected_image
