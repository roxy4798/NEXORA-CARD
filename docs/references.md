# Documentation References

This project relies strictly on official, verified documentation for Binance Futures public market data and Telegram Bot API.

## 1. Binance USDⓈ-M Futures Public API
- **Official Documentation**: [Binance USDⓈ-M Futures Developer Docs](https://developers.binance.com/docs/derivatives/usds-margined-futures)
- **Base Endpoint**: `https://fapi.binance.com`
- **Date Verified**: 2026-09-27
- **Endpoints Utilized**:
  - `GET /fapi/v1/exchangeInfo`:
    - Purpose: Retrieves all active trading pairs, symbol status, price filter rules (`tickSize`), and lot size rules (`stepSize`).
    - Authentication: None (Public market data).
    - Rate Limit: IP weight 1.
  - `GET /fapi/v1/premiumIndex?symbol={symbol}`:
    - Purpose: Retrieves real-time Mark Price, Index Price, and Funding Rate.
    - Authentication: None (Public market data).
    - Rate Limit: IP weight 1.
  - `GET /fapi/v1/ticker/24hr?symbol={symbol}`:
    - Purpose: 24-hour rolling window price change statistics if needed.
    - Authentication: None (Public market data).

## 2. Binance USDⓈ-M Futures WebSocket Streams
- **Official Documentation**: [Binance WebSocket Market Streams](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams)
- **WebSocket Base URL**: `wss://fstream.binance.com/ws`
- **Streams Utilized**:
  - `<symbol>@markPrice` / `<symbol>@markPrice@1s`: Real-time mark price and funding rate stream.
  - Public access, no authentication required.

## 3. Telegram Bot API & python-telegram-bot
- **Official Documentation**: [python-telegram-bot v20+ / v22 Documentation](https://docs.python-telegram-bot.org/)
- **Telegram Bot API Reference**: [Telegram Bot API](https://core.telegram.org/bots/api)
- **Features Utilized**:
  - `ApplicationBuilder`, `CommandHandler`, `CallbackQueryHandler`, `ConversationHandler`
  - `InlineKeyboardMarkup`, `InlineKeyboardButton`
  - `sendPhoto`: Transmits in-memory rendered PNG card buffer (`io.BytesIO`).
  - `editMessageMedia`: Updates existing position card photo when the user taps `[ REFRESH ]`.
  - `deleteMessage`: Deletes the generated photo when the user taps `[ DELETE ]`.

## 4. Prohibited Endpoints
In accordance with our strict non-custodial and safety policy:
- No trade execution endpoints (e.g., `/fapi/v1/order`, `/fapi/v1/batchOrders`).
- No account or balance endpoints (e.g., `/fapi/v1/account`, `/fapi/v1/balance`).
- No private API keys or signature handling are implemented or allowed in the codebase.
