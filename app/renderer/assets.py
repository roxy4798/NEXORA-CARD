"""Programmatic drawing helpers for icons, badges, indicators, and UI elements."""

from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
from app.renderer.theme import THEME, ColorRGB


def draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float, float, float],
    radius: float,
    fill: Optional[ColorRGB] = None,
    outline: Optional[ColorRGB] = None,
    width: int = 1,
) -> None:
    """Draws a smooth rounded rectangle with optional fill and outline."""
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_text_at(
    draw: ImageDraw.ImageDraw,
    text: str,
    x_target: float,
    y_target: float,
    font: ImageFont.FreeTypeFont,
    fill: ColorRGB,
    align: str = "left",
) -> Tuple[float, float, float, float]:
    """Draws text accurately aligned by glyph bounding box."""
    bbox = font.getbbox(text)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    if align == "left":
        x = x_target - bbox[0]
    elif align == "right":
        x = x_target - bbox[2]
    elif align == "center":
        x = x_target - bbox[0] - w / 2
    else:
        x = x_target - bbox[0]
    y = y_target - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)
    return (x + bbox[0], y + bbox[1], w, h)


def draw_side_badge(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    size: float,
    side: str,
    font: ImageFont.FreeTypeFont,
) -> None:
    """Draws side badge matching Binance mobile: Green 'B' for LONG, Red 'S' for SHORT."""
    radius = 7
    is_short = str(side).upper() in ("SHORT", "SELL", "S")
    bg_color = THEME.badge_short_bg if is_short else THEME.badge_long_bg
    letter = "S" if is_short else "B"

    draw_rounded_rect(draw, (x, y, x + size, y + size), radius=radius, fill=bg_color)
    bbox = font.getbbox(letter)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    tx = x + (size - w) / 2
    ty = y + (size - h) / 2 + 1
    draw.text((tx - bbox[0], ty - bbox[1]), letter, fill=THEME.badge_text, font=font)


def draw_coin_badge(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    size: float,
    symbol: str,
    font: ImageFont.FreeTypeFont,
    side: Optional[str] = None,
) -> None:
    """Compatibility wrapper that draws the side badge (Green 'B' for LONG, Red 'S' for SHORT)."""
    draw_side_badge(draw, x, y, size, side or "LONG", font)


def draw_share_icon_inline(
    draw: ImageDraw.ImageDraw,
    x: float = 221,
    y: float = 129,
    color: Optional[ColorRGB] = None,
) -> None:
    """Draws the hollow-node share icon matching Binance mobile reference screenshot."""
    col = color or THEME.text_secondary
    # Coordinates for the 3 nodes: left-center, top-right, bottom-right
    n1 = (x + 6, y + 14)
    n2 = (x + 24, y + 5)
    n3 = (x + 24, y + 24)

    # Connecting lines behind nodes
    draw.line([n1, n2], fill=col, width=2)
    draw.line([n1, n3], fill=col, width=2)

    # Hollow circular rings for each node
    r = 4.5
    for pt in [n1, n2, n3]:
        draw.ellipse([pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r], fill=THEME.bg_main, outline=col, width=2)


def draw_swap_icon_inline(
    draw: ImageDraw.ImageDraw,
    x: float = 221,
    y: float = 260,
    color: Optional[ColorRGB] = None,
) -> None:
    """Draws opposing horizontal swap arrows matching Binance mobile reference screenshot."""
    col = color or THEME.text_secondary
    # Top arrow pointing left
    draw.line([(x + 2, y + 9), (x + 29, y + 9)], fill=col, width=2)
    draw.line([(x + 2, y + 9), (x + 7, y + 2)], fill=col, width=2)

    # Bottom arrow pointing right
    draw.line([(x, y + 18), (x + 27, y + 18)], fill=col, width=2)
    draw.line([(x + 27, y + 18), (x + 22, y + 25)], fill=col, width=2)


def draw_signal_bars(
    draw: ImageDraw.ImageDraw,
    start_x: float = 658,
    color: Optional[ColorRGB] = None,
    start_y: float = 48,
) -> None:
    """Draws 4 margin-risk indicators matching Binance mobile reference (pill + dot below)."""
    profit_c = color or THEME.profit
    muted_c = THEME.text_muted
    bar_colors = [profit_c, profit_c, muted_c, muted_c]
    bar_centers = [start_x + 2, start_x + 11, start_x + 20, start_x + 30]

    for i in range(4):
        bx = bar_centers[i]
        col = bar_colors[i]
        # Top vertical rounded pill
        draw.rounded_rectangle([bx - 1.5, start_y, bx + 1.5, start_y + 24], radius=1.5, fill=col)
        # Bottom circular dot
        draw.ellipse([bx - 2, start_y + 27, bx + 2, start_y + 31], fill=col)


def draw_signal_bars_red(
    draw: ImageDraw.ImageDraw,
    start_x: float,
    start_y: float = 42,
) -> None:
    """Draws red signal bar indicator next to cross badge in 1080x620 layout."""
    col = THEME.loss
    muted = (80, 86, 98)
    colors = [col, col, muted, muted]
    centers = [start_x + 2, start_x + 9, start_x + 16, start_x + 23]
    for i in range(4):
        bx = centers[i]
        c = colors[i]
        draw.rounded_rectangle([bx - 1.5, start_y, bx + 1.5, start_y + 18], radius=1.5, fill=c)
        draw.ellipse([bx - 2, start_y + 21, bx + 2, start_y + 25], fill=c)



def draw_chevron_right(
    draw: ImageDraw.ImageDraw,
    apex_x: float = 941,
    apex_y: float = 526,
    color: Optional[ColorRGB] = None,
) -> None:
    """Draws chevron '>' arrow matching reference screenshot."""
    col = color or THEME.text_secondary
    lw = 3
    draw.line([(apex_x - 15, apex_y - 11), (apex_x, apex_y)], fill=col, width=lw)
    draw.line([(apex_x, apex_y), (apex_x - 15, apex_y + 11)], fill=col, width=lw)


def draw_dotted_underline(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    width: float,
    color: Optional[ColorRGB] = None,
    dot_len: int = 2,
    gap_len: int = 3,
) -> None:
    """Draws subtle dotted underline matching reference."""
    col = color or THEME.underline_dot
    curr = x
    while curr < x + width:
        draw.line([(curr, y), (min(curr + dot_len, x + width), y)], fill=col, width=1)
        curr += dot_len + gap_len


def draw_diagonal_watermark(
    base_img: Image.Image,
    text: str = "NEXO_TRADE",
    angle: float = -25.0,
    alpha: int = 16,
) -> Image.Image:
    """Draws low-opacity diagonal watermark centered behind metric values."""
    from app.renderer.typography import get_font

    txt_layer = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    font = get_font(110, weight=700, width=100)
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    temp_img = Image.new("RGBA", (tw + 60, th + 60), (0, 0, 0, 0))
    t_draw = ImageDraw.Draw(temp_img)
    t_draw.text((30 - bbox[0], 30 - bbox[1]), text, fill=(245, 248, 252, alpha), font=font)

    rotated = temp_img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    rx = (base_img.width - rotated.width) // 2
    ry = (base_img.height - rotated.height) // 2 + 10
    txt_layer.paste(rotated, (rx, ry), rotated)

    return Image.alpha_composite(base_img.convert("RGBA"), txt_layer).convert("RGB")


