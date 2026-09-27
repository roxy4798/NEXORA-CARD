"""Unit tests for position card PNG renderer."""

from decimal import Decimal
from pathlib import Path
from PIL import Image
import pytest

from app.renderer.position_card import PositionCardRenderer
from app.simulation.models import Side, PositionResult


@pytest.fixture
def sample_position_result() -> PositionResult:
    return PositionResult(
        symbol="WUSDT",
        side=Side.LONG,
        entry_price=Decimal("0.0140000"),
        leverage=Decimal("20"),
        margin=Decimal("176.80"),
        margin_ratio=Decimal("8.29"),
        mark_price=Decimal("0.0157539"),
        position_size=Decimal("3536.00"),
        pnl=Decimal("442.99"),
        roi=Decimal("250.56"),
        liquidation_price=Decimal("0.0106400"),
        realized_pnl=Decimal("-0.04"),
        tick_size=Decimal("0.0000001"),
        step_size=Decimal("1"),
    )


@pytest.fixture
def fartcoin_position_result() -> PositionResult:
    return PositionResult(
        symbol="FARTCOINUSDT",
        side=Side.LONG,
        entry_price=Decimal("0.1912999"),
        leverage=Decimal("3"),
        margin=Decimal("5.17"),
        margin_ratio=Decimal("7.64"),
        mark_price=Decimal("0.1980000"),
        position_size=Decimal("15.51"),
        pnl=Decimal("0.54"),
        roi=Decimal("10.51"),
        liquidation_price=Decimal("0"),  # unreachable -> displays '--'
        realized_pnl=Decimal("-0.04"),
        tick_size=Decimal("0.0000001"),
        step_size=Decimal("1"),
    )


def test_renderer_produces_valid_png(sample_position_result):
    """TEST 16: Verify renderer outputs valid PNG binary with correct dimensions (1024x732)."""
    renderer = PositionCardRenderer()
    png_bytes = renderer.render_to_bytes(sample_position_result)

    # Magic PNG header
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    # Load into PIL to verify dimensions
    from io import BytesIO
    img = Image.open(BytesIO(png_bytes))
    assert img.format == "PNG"
    assert img.size == (1024, 732)

    # Save to output for visual inspection
    out_dir = Path(__file__).resolve().parent.parent / "output"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "sample_position_card.png"
    out_path.write_bytes(png_bytes)
    assert out_path.exists() and out_path.stat().st_size > 0


def test_renderer_fartcoin_reference(fartcoin_position_result):
    """Verify FARTCOIN visual acceptance case renders cleanly."""
    renderer = PositionCardRenderer()
    png_bytes = renderer.render_to_bytes(fartcoin_position_result)
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert fartcoin_position_result.liq_price_formatted == "--"
    assert fartcoin_position_result.realized_pnl_formatted == "-0.04"


def test_renderer_does_not_contain_nan_infinity(sample_position_result):
    """TEST 17: Checks formatted values contain no NaN or Infinity."""
    for val_str in [
        sample_position_result.pnl_formatted,
        sample_position_result.roi_formatted,
        sample_position_result.size_formatted,
        sample_position_result.margin_formatted,
        sample_position_result.margin_ratio_formatted,
        sample_position_result.realized_pnl_formatted,
        sample_position_result.liq_price_formatted,
    ]:
        assert "nan" not in val_str.lower()
        assert "inf" not in val_str.lower()


def test_deterministic_rendering(sample_position_result):
    """TEST 18: Same inputs produce deterministic output."""
    renderer = PositionCardRenderer()
    png1 = renderer.render_to_bytes(sample_position_result)
    png2 = renderer.render_to_bytes(sample_position_result)

    assert png1 == png2


def test_visual_regression_mae(fartcoin_position_result):
    """Verify calibrated renderer produces 1024x732 card within regression tolerance."""
    import numpy as np

    ref_path = Path(__file__).resolve().parent.parent / "output" / "reference.png"
    if not ref_path.exists():
        pytest.skip("Reference image not found on disk")

    ref_img = Image.open(ref_path).convert("RGB")
    renderer = PositionCardRenderer()
    rendered_img = renderer.render(fartcoin_position_result)

    assert rendered_img.size == (1024, 732)
    assert ref_img.size == (1024, 732)

    diff = np.abs(np.array(ref_img, dtype=int) - np.array(rendered_img, dtype=int))
    mean_diff = np.mean(diff)
    assert mean_diff <= 10.0, f"Visual regression detected: MAE {mean_diff:.2f} > 10.0"


def test_dual_rendering_modes(fartcoin_position_result):
    """Verify rendering: CALIBRATION vs PRODUCTION modes, side badges, and absence of SIMULATED badge."""
    import numpy as np

    cal_renderer = PositionCardRenderer(mode="CALIBRATION")
    prod_renderer = PositionCardRenderer(mode="PRODUCTION")

    assert not cal_renderer.is_production
    assert prod_renderer.is_production

    cal_img = cal_renderer.render(fartcoin_position_result)
    prod_img = prod_renderer.render(fartcoin_position_result)

    assert cal_img.size == (1024, 732)
    assert prod_img.size == (1024, 732)

    cal_arr = np.array(cal_img, dtype=int)
    prod_arr = np.array(prod_img, dtype=int)

    # Standard production mode generates clean card matching calibration (no SIMULATED text)
    diff = np.abs(prod_arr - cal_arr)
    assert np.max(diff) == 0, "Production card must be clean and identical to calibration reference"

    # Verify side badge is green B for LONG
    badge_slice = prod_arr[42:84, 39:81]
    assert np.mean(badge_slice[:, :, 1]) > np.mean(badge_slice[:, :, 0]), "LONG position must display green B badge"

    # Verify top right area is clean background (no SIMULATED pill)
    top_right = prod_arr[45:80, 850:984]
    bg_diff = np.abs(top_right - np.array([35, 37, 49]))
    assert np.max(bg_diff) == 0, "Top right area must not contain SIMULATED text or badge"


def test_short_position_badge_is_red_s(fartcoin_position_result):
    """Verify that a SHORT position renders a red 'S' side badge matching Binance mobile."""
    import numpy as np
    from app.simulation.models import Side

    short_result = fartcoin_position_result.model_copy(update={"side": Side.SHORT})
    renderer = PositionCardRenderer(mode="PRODUCTION")
    img = renderer.render(short_result)
    arr = np.array(img, dtype=int)

    # Side badge is at (39..81, 42..84)
    badge_slice = arr[42:84, 39:81]

    # Red badge: Red channel significantly exceeds Green channel
    mean_r = np.mean(badge_slice[:, :, 0])
    mean_g = np.mean(badge_slice[:, :, 1])
    assert mean_r > mean_g + 50, f"SHORT badge must be red (R={mean_r}, G={mean_g})"

    # Verify no SIMULATED badge on the card
    top_right = arr[45:80, 850:984]
    bg_diff = np.abs(top_right - np.array([35, 37, 49]))
    assert np.max(bg_diff) == 0, "Card must not contain SIMULATED text or badge"


