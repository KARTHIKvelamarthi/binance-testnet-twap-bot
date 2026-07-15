# Binance Futures Testnet Trading Bot

A robust, structured Python CLI for placing **MARKET**, **LIMIT**, and **TWAP** orders on the Binance Futures Testnet (USDT-M). It features guided interactive input entry, strict client-side validation with real-time typo corrections, an active order status polling loop, clean single-line logs, and a completely silent console interface.

> ⚠️ Uses **Binance Futures Testnet** only (`https://testnet.binancefuture.com`).
> No real funds or real orders are involved.

---

## Features & UX Highlights

### 1. Dual Execution Modes
*   **Flag-driven mode:** Provide order details directly via CLI flags for scripting and automation (e.g., `python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 -y`).
*   **Guided Interactive mode:** Run the script without arguments (`python cli.py`) to launch a guided, step-by-step terminal interface.

### 2. Sane CLI Validation & Typo Corrections
The interactive CLI checks inputs in real-time. If you make a typo, it catches the validation error, displays the accepted options, and reprompts you without crashing:
```
Enter symbol (e.g. BTCUSDT): btcusd
Enter side (BUY/SELL): vye
Invalid input: Side must be one of ['BUY', 'SELL'], got 'VYE'. Please try again.
Enter side (BUY/SELL): buy
Enter order type (MARKET/LIMIT/TWAP): mrket
Invalid input: Order type must be one of ['LIMIT', 'MARKET', 'TWAP'], got 'MRKET'. Please try again.
```

### 3. Safety Confirmation Prompt
Every order execution requires explicit approval to prevent fat-finger mistakes. A summary card of the request is printed, followed by a `[y/N]` prompt defaulting to `No`:
```
--- Order Request Summary ---
  Symbol:     BTCUSDT
  Side:       BUY
  Type:       MARKET
  Quantity:   0.01
------------------------------

Confirm and submit? [y/N]: y
```
*Use the `-y` or `--yes` flag to bypass this confirmation in automated environments.*

### 4. Active Status Verification Polling
Binance returns a status of `NEW` immediately upon order acceptance, meaning the executed quantity initially shows as `0.0000`. To log and display the true execution details:
*   The bot implements a polling loop checking the order status up to **5 times** (at 1-second intervals).
*   If the order matches and fills on the exchange (e.g. `MARKET` or marketable `LIMIT` orders), it breaks early and displays the final executed quantity and average price.
*   If the order remains open (e.g. a `LIMIT` order below/above current price), it finishes polling and gracefully displays the current open `NEW` status.

### 5. Responsive Web Frontend (FastAPI & HTML/CSS/JS)
In addition to the CLI, the bot features a lightweight, single-page web interface served by a local FastAPI backend:
*   **Intuitive Order Entry Form**: Support for MARKET, LIMIT, and TWAP orders with dynamic input fields based on the selected type.
*   **Real-time Validations**: Reuses the core validation logic from the bot to ensure correct inputs before submission.
*   **Confirmation Modal**: A review card displays the order details for manual confirmation.
*   **Recent Orders log viewer**: An automatically updated table displaying the status and details of the 10 most recent orders.
*   **Aesthetic Responsive Layout**: Premium, glassmorphic layout styled with vanilla CSS, accommodating side-by-side display on desktop and vertical stacking on mobile/tablet viewports.

---

## Logging & Console Design System

To ensure **high logging quality** ("useful, not noisy"), the system separates terminal visual outputs from deep audit logs:

### 1. Completely Silent Console (Terminal)
The root logger level is set to `DEBUG` to write all events to the file. However, the terminal console handler is set to `WARNING`. 
*   No standard `INFO` or `DEBUG` logs clutter the CLI screen during runs.
*   The terminal output consists purely of user-friendly summary blocks and success/error signs:
```
✅ Order placed successfully.
  Order ID:      21697614683
  Status:        FILLED
  Executed Qty:  0.0100
  Avg Price:     64265.000000
```

### 2. Clean, Structured Single-line Logs
Raw Binance API response dumps have been completely removed from both console and file handlers. They are replaced by clean, structured, single-line event logs showing the lifecycle of the order:
*   `Submitting order: BUY 0.01 BTCUSDT MARKET`
*   `Order accepted: id=21697614683 status=NEW`
*   `Order confirmed filled: id=21697614683 executedQty=0.0100 avgPrice=64265.000000`

### 3. Run Separators (`====================`)
At the end of every bot run, a divider line of `80` equals signs is written. We created a custom `RunSeparatorFormatter` to bypass standard log templates for this separator, ensuring it prints as a clean divider line **without timestamps or metadata prefixes**:
```
2026-07-14 20:32:59,962 | INFO     | trading_bot | Order accepted: id=21697614683 status=NEW
2026-07-14 20:33:01,089 | INFO     | trading_bot | Order confirmed filled: id=21697614683 executedQty=0.0100 avgPrice=64265.000000
================================================================================
```

---

## Project Structure

```
trading_bot/
  bot/
    __init__.py
    client.py          # Binance API client wrapper & order status verification
    orders.py          # Order execution orchestration
    twap.py            # TWAP slice execution & logging orchestration
    validators.py      # Input validation (symbol, side, quantity, price, TWAP params)
    logging_config.py  # RunSeparatorFormatter, console (WARNING) and file (DEBUG) setup
  cli.py               # CLI entry point (argparse & Interactive guided wizard)
  web.py               # FastAPI server backend serving Web UI & APIs
  static/              # Web UI static assets
    index.html         # Frontend HTML structure
    style.css          # Vanilla CSS stylesheet (glassmorphism & responsive layout)
    app.js             # Frontend API request/response & DOM logic
  requirements.txt     # Dependencies (python-binance, fastapi, uvicorn)
  logs/
    trading_bot.log    # Clean structured audit log file
  README.md
```

---

## Setup & Run Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set API Credentials as Environment Variables
```bash
# Linux/macOS
export BINANCE_TESTNET_API_KEY="your_api_key"
export BINANCE_TESTNET_API_SECRET="your_api_secret"

# Windows PowerShell
$env:BINANCE_TESTNET_API_KEY="your_api_key"
$env:BINANCE_TESTNET_API_SECRET="your_api_secret"
```

### 3. Place Orders

#### Market Order
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 -y
```

#### Limit Order (Good-Til-Canceled default)
```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000.0 -y
```

#### TWAP Order (Splits quantity over duration)
```bash
python cli.py --symbol BTCUSDT --side BUY --type TWAP --quantity 0.03 --duration 10 --slices 3 -y
```

### 4. Running the Web UI (Bonus Feature)
The project includes a lightweight, single-page Web UI powered by a FastAPI backend (in `web.py`) and a vanilla HTML/CSS/JS frontend. Note that the CLI remains the primary required interface, and this is a bonus addition.

Start the application server:
```bash
uvicorn web:app --reload
```
Then navigate to:
```
http://localhost:8000
```

---

## Error Handling

Errors are normalized across all paths to display human-readable descriptions rather than raw stack traces:

| Failure Type | Example | Visual Console Output | Log File Recording |
|---|---|---|---|
| **Invalid Input** | negative quantity, missing prices | `❌ Invalid input: Quantity must be positive...` | `ERROR | Input validation failed: ...` |
| **Binance API Rejections** | invalid symbol, price out of bands | `❌ Order failed. Reason: APIError(code=-1121)...` | `ERROR | Order rejected: reason=APIError...` |
| **Network/timeouts** | connection failure | `❌ Binance API error: Connection timeout...` | `ERROR | Order rejected: reason=Connection...` |
