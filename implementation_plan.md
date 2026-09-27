# Implementation Plan: Telegram Paper Position Generator

## 1. Executive Summary & Existing State
- **Workspace State**: `c:\NEXORA POSITION` is currently an empty directory (clean slate).
- **Environment**: Python 3.13.12 is active with key packages already installed (`python-telegram-bot 22.8`, `pillow 12.3.0`, `httpx 0.28.1`, `pydantic 2.13.4`, `pytest 8.4.2`, `pytest-asyncio 1.4.0`).
- **Safety Directive**: Market-data and simulation ONLY. Absolute zero trading capability. No private API keys or trade execution endpoints.

---

## 2. System Architecture & Directory Layout

```
c:\NEXORA POSITION\
├── app/
│   ├── __init__.py
│   ├── main.py                     # Application entrypoint (CLI / bot runner)
│   ├── config.py                   # Pydantic Settings & environment variables
│   ├── logging_config.py           # Structured logging setup
│   ├── binance/
│   │   ├── __init__.py
│   │   ├── client.py               # Async HTTP client for Binance Futures public API
│   │   ├── exchange_info.py        # Symbol cache, tick size, step size, precision metadata
│   │   └── websocket.py            # Live mark price stream consumer (public wss)
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── models.py               # Pydantic/dataclass models (Position, Side, PositionResult)
│   │   ├── precision.py            # Decimal helpers, quantize_tick, formatting
│   │   ├── calculator.py           # Orchestrator for financial calculations
│   │   ├── pnl.py                  # PNL calculation (Long / Short) in Decimal
│   │   ├── roi.py                  # ROI calculation (%) in Decimal
│   │   └── liquidation.py          # Deterministic simulated liquidation model
│   ├── renderer/
│   │   ├── __init__.py
│   │   ├── theme.py                # Colors, margins, canvas dimensions, style constants
│   │   ├── typography.py           # Font loaders (Segoe UI / Arial / Roboto fallback)
│   │   ├── assets.py               # Programmatic icon generator (coin badges, share icon)
│   │   └── position_card.py        # High-fidelity 1080x650 PNG card renderer
│   └── bot/
│       ├── __init__.py
│       ├── bot_app.py              # Application builder & lifecycle
│       ├── states.py               # Conversation states enum
│       ├── keyboards.py            # Inline keypads (Side selection, Refresh/Edit/Delete)
│       ├── conversation.py         # Step-by-step wizard (/position and /mock_position)
│       └── handlers.py             # Callback queries (Refresh, Edit, Delete) & error handler
├── docs/
│   ├── architecture.md             # System design and data flows
│   ├── liquidation-model.md        # Mathematical formulation of simulated liquidation price
│   ├── references.md               # Official Binance & Telegram API documentation references
│   └── testing.md                  # Test suite documentation & execution instructions
├── tests/
│   ├── __init__.py
│   ├── test_security_safety.py     # Blocks any occurrence of order execution endpoints
│   ├── test_position_size.py       # Position size calculation tests
│   ├── test_pnl.py                 # PNL calculation tests (Long/Short, +/-, zero)
│   ├── test_roi.py                 # ROI calculation tests
│   ├── test_liquidation.py         # Simulated liquidation price tests
│   ├── test_precision.py           # Decimal arithmetic and tick-size quantization tests
│   ├── test_exchange_info.py       # Symbol validation & metadata parsing tests
│   ├── test_renderer.py            # Image generation, dimensions, valid PNG, determinism tests
│   └── test_acceptance.py          # Full acceptance test case (WUSDT test specification)
├── output/                         # Directory for sample & exported cards
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── Dockerfile
```

---

## 3. Binance Public Market-Data APIs

We exclusively target the public Binance USDⓈ-M Futures market data endpoints:
1. **Exchange Information**:
   - `GET /fapi/v1/exchangeInfo`
   - Cache symbol list, status (`TRADING`), `PRICE_FILTER` (`tickSize`), `LOT_SIZE` (`stepSize`), `pricePrecision`, `quantityPrecision`.
2. **Mark Price & Funding Rate**:
   - `GET /fapi/v1/premiumIndex?symbol={symbol}`
   - Returns real-time `markPrice`, `indexPrice`, `lastFundingRate`, `time`.
3. **Optional WebSocket stream**:
   - `wss://fstream.binance.com/ws/{symbol.lower()}@markPrice`
   - Real-time updates without polling.
4. **Safety enforcement**:
   - No endpoints with `/fapi/v1/order`, `/fapi/v1/batchOrders`, etc.
   - Any attempt to load API keys or call mutating trade endpoints will be rejected and tested against by CI.

---

## 4. Numerical Precision & Mathematical Models

All calculations use Python `decimal.Decimal` and `ROUND_HALF_UP` / tick quantize. Floats are prohibited in all computation layers.

### 4.1 Position Size
$$\text{Position Size} = \text{Margin} \times \text{Leverage}$$

### 4.2 Unrealized PNL
- **LONG**:
  $$\text{PNL} = \text{Position Size} \times \left( \frac{\text{Mark Price} - \text{Entry Price}}{\text{Entry Price}} \right)$$
- **SHORT**:
  $$\text{PNL} = \text{Position Size} \times \left( \frac{\text{Entry Price} - \text{Mark Price}}{\text{Entry Price}} \right)$$

### 4.3 Return on Investment (ROI)
$$\text{ROI} (\%) = \left( \frac{\text{PNL}}{\text{Margin}} \right) \times 100$$

### 4.4 Simulated Liquidation Price
In a real cross-margin account, liquidation occurs when Margin Ratio reaches 100% (Maintenance Margin = Margin Balance).
In our paper simulator, the user enters a hypothetical **Margin Ratio ($MR\%$)**.
We model a deterministic simulated liquidation price:
- For **LONG**:
  The position liquidates when the market drops such that the loss absorbs the margin buffer:
  $$P_{\text{liq}} = P_{\text{entry}} \times \left(1 - \frac{1}{\text{Leverage}} \times \left(1 - \frac{MR}{100}\right)\right)$$
- For **SHORT**:
  The position liquidates when the market rises:
  $$P_{\text{liq}} = P_{\text{entry}} \times \left(1 + \frac{1}{\text{Leverage}} \times \left(1 - \frac{MR}{100}\right)\right)$$
- Safety bounds: $P_{\text{liq}} > 0$. If calculated $P_{\text{liq}} \le 0$ for LONG, clamp to smallest tick size. Never produce NaN, Infinity, or negative numbers.

---

## 5. Visual Renderer (Pillow / PIL)

- **Canvas Size**: 1080 x 650 px (or responsive aspect ratio, configurable).
- **Background**: Deep charcoal `#0B0E14` with subtle rounded card surface `#181A20`.
- **Typography**: Clean modern sans-serif (Segoe UI / Arial fallback) with distinct sizing and weights.
- **Header**:
  - Coin badge (programmatic rounded square with symbol initial or clean glyph)
  - Symbol: e.g. `WUSDT` (Bold, white `#EAECEF`)
  - Type badge: `Perp` (`#848E9C` pill)
  - Leverage badge: `Cross 20x` (dark pill)
  - Share icon placeholder on top right
  - Clear, elegant watermark badge: `[SIMULATED]` / `[PAPER TRADE]`
- **Main Metrics**:
  - Unrealized PNL (USDT): Large bold colored text (`#0ECB81` for profit, `#F6465D` for loss).
  - ROI: Large bold colored text (e.g. `+250.56%` / `-45.12%`).
- **Two-Column Grid**:
  - Size (USDT) | Margin (USDT)
  - Margin Ratio | [value]%
  - Entry Price (USDT) | Mark Price (USDT)
  - Liq. Price (USDT)
- **Bottom Action Buttons**:
  - `[ Leverage ]` `[ TP/SL ]` `[ Close ]` rendered as aesthetic rounded buttons.
- **Separators**: Dotted / dashed or thin crisp divider lines `#2B313A`.

---

## 6. Telegram Bot Architecture

Using `python-telegram-bot` v22 (async):
- **Wizard Flow (`/position` and `/mock_position`)**:
  1. Symbol prompt (e.g. `WUSDT`), auto-upper and validated against Binance symbol list.
  2. Side selection inline buttons: `[ LONG ]` | `[ SHORT ]`.
  3. Entry price input (Decimal validation > 0, tick quantization).
  4. Leverage input (Integer / Decimal > 0, <= MAX_LEVERAGE).
  5. Margin input (Decimal > 0).
  6. Margin Ratio input (Decimal >= 0, <= 100%).
  7. Bot retrieves real-time Mark Price (or mock price in mock mode), generates PNG card in memory (`io.BytesIO`), and transmits via `sendPhoto`.
- **Card Interactive Inline Controls**:
  - `[ REFRESH ]`: Re-fetches Mark Price, recalculates, updates photo via `editMessageMedia`.
  - `[ EDIT ]`: Re-enters wizard to adjust parameters.
  - `[ DELETE ]`: Deletes the generated message and cleans up state.

---

## 7. Testing & Quality Strategy

1. **Security**: `test_security_safety.py` scans codebase for forbidden trade execution strings like `/fapi/v1/order`.
2. **Math & Precision**: Tests covering LONG/SHORT, profit/loss, zero PNL, ROI, position size, tick-size quantizations, extreme leverage, zero margin ratio.
3. **Liquidation**: Monotonicity, non-negativity, deterministic output for both sides.
4. **Acceptance Test**: Validates the exact user prompt scenario (`WUSDT`, LONG, Entry 0.0140000, Leverage 20, Margin 176.80, MR 8.29%, Mark 0.0157539 -> Size 3536.00 USDT, PNL +442.99 USDT, ROI +250.56%).
5. **Renderer**: PNG valid byte headers, correct dimensions, deterministic hashes, fallback fonts.
