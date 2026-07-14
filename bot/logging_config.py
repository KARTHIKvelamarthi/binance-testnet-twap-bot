"""
Centralized logging configuration for the trading bot.

All API requests, responses, and errors are logged to a rotating file
so a single run doesn't produce an unbounded log, while still keeping
enough history to debug past runs.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the bot's shared logger.

    Logs go to both a rotating file (logs/trading_bot.log) and the
    console, so the CLI still shows a clean summary while the file
    keeps the full request/response detail for later debugging.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(level)

    # Avoid adding duplicate handlers if setup_logging() is called more than once
    if logger.handlers:
        return logger

    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    console_formatter = logging.Formatter("%(levelname)-8s | %(message)s")

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
