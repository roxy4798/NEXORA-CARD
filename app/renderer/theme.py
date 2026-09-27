"""Theme constants, color palettes, and dimensions matching the single-source-of-truth reference."""

from dataclasses import dataclass
from typing import Tuple

ColorRGB = Tuple[int, int, int]
ColorRGBA = Tuple[int, int, int, int]


@dataclass(frozen=True)
class Theme:
    # Canvas - matching reference 1024 x 732
    width: int = 1024
    height: int = 732
    card_margin: int = 0
    card_radius: int = 0

    # Backgrounds - Binance Futures dark slate palette
    bg_main: ColorRGB = (35, 37, 49)           # Exact reference background #232531
    bg_card: ColorRGB = (35, 37, 49)           # Seamless continuous surface
    bg_badge: ColorRGB = (40, 48, 60)          # Badges #28303C
    border_badge: ColorRGB = (64, 70, 82)      # Badge subtle outline #404652
    bg_realized: ColorRGB = (35, 37, 49)       # Realized PNL container (seamless background)
    border_realized: ColorRGB = (52, 59, 69)   # Realized container subtle outline #343B45
    bg_button: ColorRGB = (50, 58, 71)         # Action buttons #323A47
    border_button: ColorRGB = (47, 51, 62)     # Button subtle border #2F333E
    divider: ColorRGB = (47, 49, 61)           # Bottom divider line #2F313D

    # Text Colors
    text_primary: ColorRGB = (245, 248, 252)   # Crisp light white #F5F8FC
    text_secondary: ColorRGB = (145, 152, 166) # Muted label gray #9198A6
    text_muted: ColorRGB = (108, 115, 127)     # Dim gray #6C737F
    text_badge: ColorRGB = (220, 226, 236)     # Pill text #DCE2EC

    # Financial Status
    profit: ColorRGB = (44, 202, 140)          # Binance Green #2CCA8C
    loss: ColorRGB = (246, 75, 96)             # Binance Red #F64B60
    neutral: ColorRGB = (245, 248, 252)

    # Dotted underline color
    underline_dot: ColorRGB = (115, 124, 138)  # Noticeable dotted underline #737C8A

    # Coin avatar / Side badge (Binance mobile: B for Long/Buy, S for Short/Sell)
    coin_bg: ColorRGB = (50, 187, 133)         # Vibrant Green #32BB85
    coin_text: ColorRGB = (255, 255, 255)      # Pure white
    badge_long_bg: ColorRGB = (50, 187, 133)   # Binance Green #32BB85 (B badge)
    badge_short_bg: ColorRGB = (237, 72, 95)   # Binance Red #ED485F (S badge)
    badge_text: ColorRGB = (255, 255, 255)     # Pure white


THEME = Theme()
