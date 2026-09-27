"""Font loader and typography styling for position card renderer."""

import os
from pathlib import Path
import logging
from typing import Optional
from PIL import ImageFont

logger = logging.getLogger(__name__)

# Primary bundled font (IBM Plex Sans / Binance Plex variable font)
_FONTS_DIR = Path(__file__).resolve().parent / "fonts"
_PRIMARY_FONT_PATH = _FONTS_DIR / "IBMPlexSans.ttf"

# Preferred font fallbacks
FONT_PATHS = [
    str(_PRIMARY_FONT_PATH),
    str(_FONTS_DIR / "SegoeUI-Bold.ttf"),
    str(_FONTS_DIR / "SegoeUI-Regular.ttf"),
    str(_FONTS_DIR / "Inter-Bold.ttf"),
    str(_FONTS_DIR / "PlusJakartaSans-Bold.ttf"),
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _find_font(paths: list[str]) -> Optional[str]:
    for p in paths:
        if os.path.exists(p):
            return p
    return None


_CHOSEN_FONT_PATH = _find_font(FONT_PATHS)

WEIGHT_MAP = {
    "thin": 200,
    "light": 300,
    "regular": 400,
    "medium": 500,
    "semibold": 600,
    "bold": 700,
}


def get_font(size: int, weight: str | int = "regular", width: int = 100) -> ImageFont.FreeTypeFont:
    """Loads font with requested size, weight (str or int), and width axis."""
    font_path = _CHOSEN_FONT_PATH

    if isinstance(weight, (int, float)):
        target_weight = int(weight)
    else:
        target_weight = WEIGHT_MAP.get(str(weight).lower(), 400)

    if font_path and os.path.exists(font_path):
        try:
            f = ImageFont.truetype(font_path, size)
            try:
                axes = f.get_variation_axes()
                if axes:
                    # IBMPlexSans has 2 axes: [Weight (100..700), Width (75..100)]
                    if len(axes) >= 2:
                        f.set_variation_by_axes([target_weight, width])
                    else:
                        f.set_variation_by_axes([target_weight])
            except Exception:
                pass
            return f
        except Exception as e:
            logger.warning(f"Failed to load font {font_path}: {e}")

    return ImageFont.load_default()

