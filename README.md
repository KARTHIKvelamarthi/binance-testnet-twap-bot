# Binance Futures Testnet Trading Bot

A small, structured Python CLI for placing MARKET and LIMIT orders on
Binance Futures Testnet (USDT-M), with input validation, structured
logging, and clean error handling.

> ⚠️ Uses **Binance Futures Testnet** only (`https://testnet.binancefuture.com`).
> No real funds or real orders are involved.

---

## Project Structure

```
trading_bot/
  bot/
    __init__.py
    client.py          # Binance API client wrapper (Futures Testnet only)
    orders.py           # Order execution orchestration
    validators.py        # Input validation, independent of CLI/API layers
    logging_config.py     # Rotating file + console logging setup
  cli.py                 # CLI entry point (argparse)
  requirements.txt
  logs/                   # Generated at runtime — request/response/error logs
  README.md
```

Each layer has one job: `validators.py` only checks input is sane,
`client.py` only talks to Binance, `orders.py` only orchestrates the two
and shapes the result, and `cli.py` only handles user interaction. This
keeps each file independently testable and means the API layer could be
reused (e.g. behind a future web endpoint) without touching CLI code.

---

## Setup

### 1. Create a Binance Futures Testnet account & API keys

1. Go to https://testnet.binancefuture.com and log in (GitHub login supported).
2. Generate an API Key + Secret from the testnet dashboard.
3. Your testnet account starts with test USDT balance automatically.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your API credentials as environment variables

Credentials are read from environment variables rather than CLI flags, so
they never end up in shell history or logs.

```bash
# Linux/macOS
export BINANCE_TESTNET_API_KEY="your_key_here"
export BINANCE_TESTNET_API_SECRET="your_secret_here"

# Windows PowerShell
$env:BINANCE_TESTNET_API_KEY="your_key_here"
$env:BINANCE_TESTNET_API_SECRET="your_secret_here"
```

---

## Running

### Market order

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Limit order

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 60000
```

Every run prints:
- an order request summary (what's about to be sent)
- the order response (order ID, status, executed quantity, average price)
- a clear ✅ success / ❌ failure message

Full request/response/error detail is additionally written to `logs/trading_bot.log`.

---

## Error handling

The bot handles three distinct failure categories, each with a clear message:

| Failure type | Example | Where it's caught |
|---|---|---|
| Invalid input | negative quantity, missing price for LIMIT, bad side value | `validators.py`, before any network call |
| Binance API error | invalid symbol, insufficient testnet balance | `client.py`, wraps `BinanceAPIException` |
| Network/unexpected error | timeout, connection failure | `client.py`, catches and re-raises as `BinanceClientError` |

All three are logged to `logs/trading_bot.log` with full detail, while the
CLI only shows a short, human-readable message.

---

## Assumptions

- Only `MARKET` and `LIMIT` order types are implemented, per the core
  requirements; no bonus order type (Stop-Limit/OCO/TWAP/Grid) is included
  in this submission.
- Quantity and price precision/step-size rules (Binance's `LOT_SIZE` /
  `PRICE_FILTER` exchange filters) are not independently validated
  client-side beyond "must be a positive number" — Binance's own API will
  reject a request that violates exchange filters, and that rejection is
  surfaced via the standard error-handling path above rather than
  duplicated client-side.
- `timeInForce=GTC` (Good-Til-Canceled) is used as the default for LIMIT
  orders, since the task didn't specify a time-in-force policy and GTC is
  the standard default.
- Credentials are expected as environment variables, not CLI arguments or
  a committed config file, to avoid accidentally leaking them in shell
  history or version control.

---

## Sample logs

See `logs/trading_bot.log` for real request/response logs from a
successful MARKET order and a successful LIMIT order placed on Testnet.
