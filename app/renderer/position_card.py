"""High-fidelity Binance Futures position card renderer matching reference screenshot (1024x732)."""

from io import BytesIO
from typing import Optional
from decimal import Decimal
from PIL import Image, ImageDraw

from app.renderer.theme import THEME, Theme
from app.renderer.typography import get_font
from app.renderer.assets import (
    draw_rounded_rect,
    draw_side_badge,
    draw_coin_badge,
    draw_share_icon_inline,
    draw_swap_icon_inline,
    draw_signal_bars,
    draw_chevron_right,
    draw_dotted_underline,
    draw_diagonal_watermark,
)
from app.simulation.models import PositionResult
from app.simulation.precision import format_price_by_tick


class PositionCardRenderer:
    """Renders deterministic PNG position cards matching Binance Futures mobile app layout (1024x732)."""

    def __init__(
        self,
        theme: Optional[Theme] = None,
        mode: str = "CALIBRATION",
        is_production: Optional[bool] = None,
        show_watermark: Optional[bool] = None,
    ):
        self.theme = theme or THEME
        if is_production is not None:
            self.mode = "PRODUCTION" if is_production else "CALIBRATION"
        elif show_watermark is not None:
            self.mode = "PRODUCTION" if show_watermark else "CALIBRATION"
        else:
            self.mode = mode.upper()
        self.show_watermark = show_watermark is True

    @property
    def is_production(self) -> bool:
        """Returns True if running in production mode."""
        return self.mode == "PRODUCTION"

    def render(self, position: PositionResult) -> Image.Image:
        """Renders complete position card matching the reference visual structure (1024x732)."""
        t = self.theme
        img = Image.new("RGB", (t.width, t.height), t.bg_main)

        # Optional watermark behind metric values (disabled by default for clean card)
        if self.show_watermark:
            img = draw_diagonal_watermark(img, text="NEXO_TRADE", angle=-25.0, alpha=16)

        draw = ImageDraw.Draw(img)

        left_x = 39
        col2_x = 362
        right_x = 984

        # ==========================================
        # 1. HEADER SECTION
        # ==========================================
        # Side badge: Green "B" for LONG, Red "S" for SHORT (matching Binance Futures mobile)
        badge_x, badge_y, badge_size = 39, 42, 42
        badge_font = get_font(30, weight=600)
        side_val = position.side.value if hasattr(position.side, "value") else str(position.side)
        draw_side_badge(draw, badge_x, badge_y, badge_size, side_val, badge_font)

        # Symbol text (e.g. FARTCOINUSDT)
        sym_font = get_font(40, weight=600, width=100)
        sym_x, sym_y = 95, 39
        draw.text((sym_x, sym_y), position.symbol, fill=t.text_primary, font=sym_font)
        sym_bbox = sym_font.getbbox(position.symbol)
        sym_w = sym_bbox[2] - sym_bbox[0]

        # "Perp" badge
        perp_x = sym_x + sym_w + 10
        perp_y, perp_w, perp_h = 43, 87, 41
        draw_rounded_rect(
            draw,
            (perp_x, perp_y, perp_x + perp_w, perp_y + perp_h),
            radius=6,
            fill=t.bg_badge,
            outline=t.border_badge,
            width=1,
        )
        pill_font = get_font(23, weight=400)
        p_box = pill_font.getbbox("Perp")
        pw = p_box[2] - p_box[0]
        draw.text((perp_x + (perp_w - pw) / 2 - p_box[0], 48), "Perp", fill=t.text_badge, font=pill_font)

        # "Cross {leverage}X" badge
        lev_str = f"Cross {int(position.leverage)}X"
        lev_bbox = pill_font.getbbox(lev_str)
        cw = lev_bbox[2] - lev_bbox[0]
        cross_w = max(141, cw + 28)
        cross_x = perp_x + perp_w + 4
        cross_y = 43
        draw_rounded_rect(
            draw,
            (cross_x, cross_y, cross_x + cross_w, cross_y + perp_h),
            radius=6,
            fill=t.bg_badge,
            outline=t.border_badge,
            width=1,
        )
        draw.text((cross_x + (cross_w - cw) / 2 - lev_bbox[0], 48), lev_str, fill=t.text_primary, font=pill_font)

        # 4 Risk signal indicators next to Cross badge
        bars_x = cross_x + cross_w + 18
        draw_signal_bars(draw, start_x=bars_x, start_y=48, color=t.profit)

        # ==========================================
        # 2. PNL AND ROI METRICS
        # ==========================================
        lbl_font = get_font(30, weight=400, width=98)
        big_font = get_font(44, weight=700, width=100)

        pnl_color = t.profit if position.pnl > 0 else (t.loss if position.pnl < 0 else t.neutral)
        roi_color = t.profit if position.roi > 0 else (t.loss if position.roi < 0 else t.neutral)

        # PNL (USDT) label with dotted underline + inline share icon
        pnl_label = "PNL (USDT)"
        draw.text((44, 124), pnl_label, fill=t.text_secondary, font=lbl_font)
        draw_dotted_underline(draw, 41, 166, 159, t.underline_dot)
        draw_share_icon_inline(draw, x=221, y=129, color=t.text_secondary)

        # PNL value
        draw.text((38, 171), position.pnl_formatted, fill=pnl_color, font=big_font)

        # ROI label with dotted underline (right-aligned)
        roi_bbox = lbl_font.getbbox("ROI")
        rw = roi_bbox[2] - roi_bbox[0]
        draw.text((985 - rw - roi_bbox[0], 124), "ROI", fill=t.text_secondary, font=lbl_font)
        draw_dotted_underline(draw, 934, 166, 48, t.underline_dot)

        # ROI value (right-aligned)
        roi_vbox = big_font.getbbox(position.roi_formatted)
        rvw = roi_vbox[2] - roi_vbox[0]
        draw.text((987 - rvw - roi_vbox[0], 171), position.roi_formatted, fill=roi_color, font=big_font)

        # ==========================================
        # 3. SECOND ROW: Size / Margin / Margin Ratio
        # ==========================================
        f_val2 = get_font(36, weight=400, width=98)
        f_val2_mr = get_font(36, weight=400, width=95)

        # Col 1: Size (USDT) (plain label without underline + inline swap arrows)
        draw.text((41, 254), "Size (USDT)", fill=t.text_secondary, font=lbl_font)
        draw_swap_icon_inline(draw, x=221, y=260, color=t.text_secondary)
        draw.text((39, 300), position.size_formatted, fill=t.text_primary, font=f_val2)

        # Col 2: Margin (USDT) (plain label without underline)
        draw.text((364, 253), "Margin (USDT)", fill=t.text_secondary, font=lbl_font)
        draw.text((361, 300), position.margin_formatted, fill=t.text_primary, font=f_val2)

        # Col 3: Margin Ratio (dotted underline, right-aligned, green value)
        mr_bbox = lbl_font.getbbox("Margin Ratio")
        mrw = mr_bbox[2] - mr_bbox[0]
        draw.text((984 - mrw - mr_bbox[0], 254), "Margin Ratio", fill=t.text_secondary, font=lbl_font)
        draw_dotted_underline(draw, 814, 296, 168, t.underline_dot)

        mr_color = t.profit if position.margin_ratio < 80 else t.loss
        mrv_bbox = f_val2_mr.getbbox(position.margin_ratio_formatted)
        mrvw = mrv_bbox[2] - mrv_bbox[0]
        draw.text((987 - mrvw - mrv_bbox[0], 300), position.margin_ratio_formatted, fill=mr_color, font=f_val2_mr)

        # ==========================================
        # 4. THIRD ROW: Entry Price / Mark Price / Liq.Price
        # ==========================================
        f_val3 = get_font(36, weight=400, width=95)
        entry_str = format_price_by_tick(position.entry_price, position.tick_size)
        mark_str = format_price_by_tick(position.mark_price, position.tick_size)
        liq_str = position.liq_price_formatted

        # Col 1: Entry Price (USDT) with dotted underline
        draw.text((40, 370), "Entry Price (USDT)", fill=t.text_secondary, font=lbl_font)
        draw_dotted_underline(draw, 41, 413, 252, t.underline_dot)
        draw.text((39, 416), entry_str, fill=t.text_primary, font=f_val3)

        # Col 2: Mark Price (USDT) (plain label without underline)
        draw.text((363, 370), "Mark Price (USDT)", fill=t.text_secondary, font=lbl_font)
        draw.text((361, 416), mark_str, fill=t.text_primary, font=f_val3)

        # Col 3: Liq.Price (USDT) with dotted underline (right-aligned)
        lp_bbox = lbl_font.getbbox("Liq.Price (USDT)")
        lpw = lp_bbox[2] - lp_bbox[0]
        draw.text((979 - lpw - lp_bbox[0], 370), "Liq.Price (USDT)", fill=t.text_secondary, font=lbl_font)
        draw_dotted_underline(draw, 757, 413, 225, t.underline_dot)

        if liq_str == "--":
            # Exact reference renders two horizontal dashes with dotted underline below
            draw.line([(952, 441), (965, 441)], fill=t.text_primary, width=3)
            draw.line([(968, 441), (981, 441)], fill=t.text_primary, width=3)
            draw_dotted_underline(draw, 951, 466, 33, t.underline_dot)
        else:
            lpv_bbox = f_val3.getbbox(liq_str)
            lpvw = lpv_bbox[2] - lpv_bbox[0]
            draw.text((979 - lpvw - lpv_bbox[0], 416), liq_str, fill=t.text_primary, font=f_val3)

        # ==========================================
        # 5. REALIZED PNL ROW (Full-width rounded card)
        # ==========================================
        draw_rounded_rect(
            draw,
            (left_x, 485, right_x, 568),
            radius=10,
            fill=t.bg_realized,
            outline=t.border_realized,
            width=1,
        )
        draw.text((71, 506), "Realized PNL (USDT)", fill=t.text_secondary, font=lbl_font)

        # Right side: value + chevron >
        f_rpnl = get_font(32, weight=500, width=95)
        rpnl_val = position.realized_pnl_formatted
        rpnl_color = t.loss if position.realized_pnl < 0 else (t.profit if position.realized_pnl > 0 else t.neutral)
        rpnl_bbox = f_rpnl.getbbox(rpnl_val)
        rpnl_w = rpnl_bbox[2] - rpnl_bbox[0]
        draw.text((903 - rpnl_w - rpnl_bbox[0], 504), rpnl_val, fill=rpnl_color, font=f_rpnl)
        draw_chevron_right(draw, apex_x=941, apex_y=526, color=t.text_secondary)

        # ==========================================
        # 6. BOTTOM FOUR ACTION BUTTONS
        # ==========================================
        btn_w = 221
        btn_h = 84
        btn_y = 600
        btn_font = get_font(30, weight=400, width=100)
        buttons = [
            ("Leverage", 39, 149),
            ("TP/SL", 281, 391),
            ("Close", 522, 633),
            ("Market Close", 764, 875),
        ]

        for label, bx, cx in buttons:
            draw_rounded_rect(
                draw,
                (bx, btn_y, bx + btn_w, btn_y + btn_h),
                radius=12,
                fill=t.bg_button,
                outline=t.border_button,
                width=1,
            )
            bbox = btn_font.getbbox(label)
            tw = bbox[2] - bbox[0]
            draw.text((cx - tw / 2 - bbox[0], 622), label, fill=(250, 254, 255), font=btn_font)

        # ==========================================
        # 7. BOTTOM DIVIDER LINE
        # ==========================================
        draw.line([(left_x, 726), (right_x, 726)], fill=t.divider, width=1)

        return img

    def render_to_bytes(self, position: PositionResult) -> bytes:
        """Renders position card and returns raw PNG bytes."""
        img = self.render(position)
        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
