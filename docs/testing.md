# Testing Guide

## 1. Running the Test Suite

To run all unit tests:
```bash
pytest -v
```

To run with coverage (if installed):
```bash
pytest --cov=app -v
```

## 2. Test Coverage Overview

- **`tests/test_security_safety.py`**:
  - Scans entire repository for dangerous Binance trading endpoints (e.g. `/order`, `/allOrders`, `/batchOrders`).
  - Ensures no API keys or secret keys are required or referenced.
- **`tests/test_pnl.py`**:
  - Long PNL positive
  - Long PNL negative
  - Short PNL positive
  - Short PNL negative
  - Zero PNL when Mark Price equals Entry Price
- **`tests/test_roi.py`**:
  - ROI calculation positive & negative
  - Zero margin guard / division guard
- **`tests/test_position_size.py`**:
  - Margin x Leverage calculation
  - Decimal precision and bounds
- **`tests/test_precision.py`**:
  - Decimal parsing
  - Quantization against arbitrary Binance tick sizes (e.g. 0.000001, 0.01, 1.0)
  - Signed formatting (+ / -)
- **`tests/test_liquidation.py`**:
  - Deterministic liquidation for Long & Short
  - Margin ratio impact
  - Zero margin ratio edge cases
  - Non-negative bounds protection
- **`tests/test_renderer.py`**:
  - Generates valid PNG byte stream
  - Verifies image dimensions (1080 x 650)
  - Layout determinism
  - Rejection of NaN / Infinity
- **`tests/test_acceptance.py`**:
  - Replicates user specification case:
    - Symbol: WUSDT, Side: LONG, Entry: 0.0140000, Leverage: 20x, Margin: 176.80 USDT, Margin Ratio: 8.29%, Mark: 0.0157539
    - Asserts Position Size = 3536.00 USDT
    - Asserts Unrealized PNL = +442.99 USDT (approximate independent formula check)
    - Asserts ROI = +250.56%
