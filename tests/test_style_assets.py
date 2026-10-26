from unittest.mock import patch

import pygame

from src import config
from src.renderer import Renderer, _contrast_ratio


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


def test_jungle_preview_uses_jungle_palette_when_modern_is_active():
    renderer = Renderer.__new__(Renderer)
    renderer.palette = config.GAME_STYLES[config.GAME_STYLE_MODERN]

    with (
        patch.object(Renderer, "_build_jungle_background", return_value=object()) as background,
        patch("src.renderer.pygame.transform.smoothscale", return_value=pygame.Surface((300, 180))),
    ):
        renderer._build_style_preview(config.GAME_STYLE_JUNGLE, (300, 180))

    background.assert_called_once_with(config.GAME_STYLES[config.GAME_STYLE_JUNGLE])


def test_theme_font_profiles_define_requested_families_and_fallbacks():
    assert config.GAME_STYLES[config.GAME_STYLE_MODERN]["heading_fonts"] == (
        "Rajdhani", "Segoe UI", "Arial"
    )
    assert config.GAME_STYLES[config.GAME_STYLE_MODERN]["body_fonts"] == (
        "Inter", "Segoe UI", "Arial"
    )
    assert config.GAME_STYLES[config.GAME_STYLE_JUNGLE]["heading_fonts"] == (
        "Cinzel", "Georgia", "Times New Roman", "Segoe UI"
    )
    assert config.GAME_STYLES[config.GAME_STYLE_JUNGLE]["body_fonts"] == (
        "Nunito Sans", "Segoe UI", "Arial"
    )


def test_renderer_selects_font_by_active_theme_and_role():
    renderer = Renderer.__new__(Renderer)
    renderer.game_style = config.GAME_STYLE_MODERN
    renderer._font_paths = {
        (config.GAME_STYLE_MODERN, "heading", True): "modern-heading.ttf",
        (config.GAME_STYLE_MODERN, "body", False): "modern-body.ttf",
        (config.GAME_STYLE_JUNGLE, "heading", True): "jungle-heading.ttf",
    }
    renderer._fonts = {}

    with patch("src.renderer.pygame.font.Font") as make_font:
        renderer._font(28, role="heading")
        renderer._font(16, bold=False)
        renderer.game_style = config.GAME_STYLE_JUNGLE
        renderer._font(40, role="heading")

    assert [call.args[0] for call in make_font.call_args_list] == [
        "modern-heading.ttf", "modern-body.ttf", "jungle-heading.ttf"
    ]


def test_theme_text_and_board_colors_meet_contrast_targets():
    for palette in config.GAME_STYLES.values():
        assert _contrast_ratio(palette["text"], palette["panel"]) >= 4.5
        assert _contrast_ratio(palette["muted"], palette["panel"]) >= 4.5
        assert _contrast_ratio(palette["text"], palette["elevated"]) >= 4.5
        assert _contrast_ratio(palette["button_text"], palette["accent"]) >= 4.5
        assert _contrast_ratio(palette["grid"], palette["board_background"]) >= 3
        assert _contrast_ratio(palette["valid_move"], palette["board_background"]) >= 3
        assert _contrast_ratio(palette["selected"], palette["board_background"]) >= 3
