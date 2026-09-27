# Binance Futures Paper Position Generator (Telegram Bot)

A production-grade Telegram bot and quantitative simulation engine that calculates hypothetical cryptocurrency futures positions and renders photorealistic Binance-style PNG position cards using real-time Binance USDⓈ-M Futures market data.

> **CRITICAL SAFETY DIRECTIVE:**
> This project is strictly **read-only / market-data only**. It contains **ZERO** trade execution logic, places **NO** orders, and does not require or accept private trading API keys. CI and automated tests (`tests/test_security_safety.py`) actively enforce this boundary.

---

## 1. Features

- **Live & Mock Modes**:
  - `/position`: Real-time mode fetching live Binance USDⓈ-M Futures Mark Prices.
  - `/mock_position`: Offline/development mode using deterministic test prices.
- **Strict Decimal Precision**:
  - Zero binary floating-point calculations in the financial layer (`decimal.Decimal` throughout).
  - Symbol tick sizes dynamically quantized from Binance exchange metadata (`PRICE_FILTER`).
- **Deterministic Mathematics**:
  - Position Size = $\text{Margin} \times \text{Leverage}$
  - PNL (Long/Short) calculated to exact tick precision.
  - ROI (%) calculated relative to user margin.
  - Simulated Liquidation Price based on a Binance-inspired simulated liquidation model (not real cross-margin account formula).
- **Pixel-Calibrated PNG Card Renderer**:
  - Visually highly matched reference-matched renderer (1024 × 732 px) built with Pillow and IBM Plex Sans.
  - Matches Binance Futures visual structure: Dark slate `#232531` background, badge headers, leverage pills, large colored PNL & ROI, two-column grid, bottom action buttons, and unobtrusive `[SIMULATED]` paper trade safety marker.
  - Zero copyrighted image assets used.
- **Interactive Telegram Experience**:
  - 6-step conversational wizard with full parameter validation.
  - Inline keyboards for side selection (`LONG` / `SHORT`).
  - Generated cards feature `[ 🔄 REFRESH ]`, `[ ✏️ EDIT ]`, and `[ 🗑️ DELETE ]` inline actions.

---

## 2. Project Structure

```
c:\NEXORA POSITION\
├── app/
│   ├── main.py                     # Entrypoint (Bot runner or CLI demo)
│   ├── config.py                   # Environment settings via Pydantic
│   ├── logging_config.py           # Structured logging with secret sanitization
│   ├── binance/
│   │   ├── client.py               # Async HTTP client for Binance Futures public API
│   │   ├── exchange_info.py        # Symbol cache, tick size, step size metadata
│   │   └── websocket.py            # Live mark price stream consumer (wss)
│   ├── simulation/
│   │   ├── models.py               # Pydantic data models (PositionInput, PositionResult)
│   │   ├── precision.py            # Decimal helpers, quantize_tick, formatting
│   │   ├── calculator.py           # Simulation orchestrator
│   │   ├── pnl.py                  # PNL formulas (Long / Short)
│   │   ├── roi.py                  # ROI percentage formula
│   │   └── liquidation.py          # Deterministic simulated liquidation model
│   ├── renderer/
│   │   ├── theme.py                # Colors, margins, canvas dimensions, style constants
│   │   ├── typography.py           # Font loader with system fallbacks
│   │   ├── assets.py               # Programmatic icon generator (coin badges, share icon)
│   │   └── position_card.py        # High-fidelity 1080x650 PNG card renderer
│   ├── bot/
│   │   ├── bot_app.py              # Application builder & lifecycle
│   │   ├── states.py               # Conversation states enum
│   │   ├── keyboards.py            # Inline keyboards
│   │   ├── conversation.py         # Step-by-step wizard (/position and /mock_position)
│   │   └── handlers.py             # Callback queries (Refresh, Edit, Delete) & error handler
│   └── scanner/
│       └── scanner_interface.py    # Interface prepared for future pump/dump scanning
├── docs/
│   ├── architecture.md             # System design and data flows
│   ├── liquidation-model.md        # Mathematical derivation of simulated liquidation price
│   ├── references.md               # Official Binance & Telegram API documentation references
│   └── testing.md                  # Test suite documentation & execution instructions
├── tests/
│   ├── test_security_safety.py     # Blocks trade execution endpoints
│   ├── test_position_size.py       # Position size calculation tests
│   ├── test_pnl.py                 # PNL calculation tests (Long/Short, +/-, zero)
│   ├── test_roi.py                 # ROI calculation tests
│   ├── test_liquidation.py         # Simulated liquidation price tests
│   ├── test_precision.py           # Decimal arithmetic and tick-size quantization tests
│   ├── test_exchange_info.py       # Symbol validation & metadata parsing tests
│   ├── test_renderer.py            # Image generation, dimensions, valid PNG, determinism
│   └── test_acceptance.py          # Full acceptance test case (WUSDT test scenario)
├── output/                         # Directory for sample & exported cards
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## 3. Installation & Quick Start

### 3.1 Prerequisites
- Python 3.12 or 3.13
- Git

### 3.2 Setup Virtual Environment
```bash
git clone <repo-url>
cd "NEXORA POSITION"

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3.3 Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in your Telegram Bot Token:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=
BINANCE_BASE_URL=https://fapi.binance.com
BINANCE_WS_URL=wss://fstream.binance.com/ws
DEFAULT_MAX_LEVERAGE=125
DEFAULT_MODE=MOCK
IMAGE_WIDTH=1080
IMAGE_HEIGHT=650
LOG_LEVEL=INFO
```

### 3.4 Run Local Demo (No Telegram Token Required)
You can test the entire simulation engine and PNG renderer immediately from the command line:
```bash
python -m app.main --demo
```
This generates a photorealistic sample card at `output/demo_position_card.png`.

### 3.5 Run Telegram Bot
Once `TELEGRAM_BOT_TOKEN` is configured:
```bash
python -m app.main
```

---

## 4. Telegram Bot Usage

1. Open Telegram and message your bot.
2. Send `/start` or `/help` to view available commands.
3. Send `/position` for Live Binance market data, or `/mock_position` for mock development.
4. Follow the conversational prompts:
   - **Coin**: e.g., `WUSDT` (validated against Binance Futures)
   - **Side**: Tap `[ 🟢 LONG ]` or `[ 🔴 SHORT ]`
   - **Entry Price**: e.g., `0.0140000`
   - **Leverage**: e.g., `20`
   - **Margin (USDT)**: e.g., `176.80`
   - **Margin Ratio (%)**: e.g., `8.29`
5. The bot renders and sends the PNG card with inline buttons:
   - `[ 🔄 REFRESH ]`: Re-fetches the latest Mark Price and updates the card.
   - `[ ✏️ EDIT ]`: Opens a submenu to modify parameters.
   - `[ 🗑️ DELETE ]`: Removes the message from the chat.

---

## 5. Mathematical Formulations

### 5.1 Unrealized PNL
- **LONG**:
  $$\text{PNL} = \text{Position Size} \times \left( \frac{\text{Mark Price} - \text{Entry Price}}{\text{Entry Price}} \right)$$
- **SHORT**:
  $$\text{PNL} = \text{Position Size} \times \left( \frac{\text{Entry Price} - \text{Mark Price}}{\text{Entry Price}} \right)$$

### 5.2 ROI (%)
$$\text{ROI} (\%) = \left( \frac{\text{PNL}}{\text{Margin}} \right) \times 100$$

### 5.3 Simulated Liquidation Price
See [docs/liquidation-model.md](docs/liquidation-model.md) for full derivation:
- **LONG**:
  $$P_{\text{liq}} = P_{\text{entry}} \times \left[ 1 - \frac{1}{\text{Leverage}} \times \left( 1 - \frac{\text{Margin Ratio}}{100} \right) \right]$$
- **SHORT**:
  $$P_{\text{liq}} = P_{\text{entry}} \times \left[ 1 + \frac{1}{\text{Leverage}} \times \left( 1 - \frac{\text{Margin Ratio}}{100} \right) \right]$$

---

## 6. Running Tests

Run the complete test suite:
```bash
pytest -v
```

All 43 tests verify:
- Security safety against order endpoints
- Long/Short profit, loss, and zero-pnl edge cases
- Position Size calculations and validation
- Dynamic multi-coin rendering (BTC, ETH, SOL, FARTCOIN across 3x, 10x, 20x leverage and various margins)
- Binance Mark Price API retrieval & failure handling
- Telegram conversation state flow
- Decimal precision & tick-size quantization
- Simulated liquidation model non-negativity & monotonicity
- Acceptance test scenario (`WUSDT` Long 20x)
- Deterministic rendering and visual regression (MAE <= 6.0 against reference)
