"""
Finnhub Real-Time FX Websocket Streaming Daemon.

Runs as a standalone background process:
    python -m src.ingestion.finnhub_stream

Connects to Finnhub OANDA FX websocket and writes live ticks
into the fx_rates_live SQLite table for Streamlit to poll.
"""
import json
import logging
import time
import datetime
import sqlite3

import websocket

from src.config import get_finnhub_api_key, FINNHUB_FX_SYMBOLS, DB_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] finnhub_stream: %(message)s"
)
logger = logging.getLogger(__name__)

SYMBOL_TO_PAIR = {v: k for k, v in FINNHUB_FX_SYMBOLS.items()}


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    return conn


def _upsert_tick(conn, symbol, price, prev_price):
    now = datetime.datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO fx_rates_live (symbol, price, prev_price, timestamp, ingested_at) VALUES (?, ?, ?, ?, ?)",
        (symbol, price, prev_price, now, now)
    )
    conn.execute(
        "DELETE FROM fx_rates_live WHERE symbol = ? AND id NOT IN (SELECT id FROM fx_rates_live WHERE symbol = ? ORDER BY id DESC LIMIT 500)",
        (symbol, symbol)
    )
    conn.commit()


class FinnhubStream:
    def __init__(self):
        self.api_key = get_finnhub_api_key()
        self.conn = _get_conn()
        self._last_price = {}

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if data.get("type") != "trade":
                return
            for trade in data.get("data", []):
                finnhub_symbol = trade.get("s")
                price = trade.get("p")
                if finnhub_symbol not in SYMBOL_TO_PAIR or price is None:
                    continue
                pair = SYMBOL_TO_PAIR[finnhub_symbol]
                prev = self._last_price.get(pair, price)
                self._last_price[pair] = price
                _upsert_tick(self.conn, pair, price, prev)
                direction = "UP" if price >= prev else "DOWN"
                logger.info(f"  {pair}: {price:.4f} {direction} (prev {prev:.4f})")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"WebSocket closed: {close_status_code}")

    def on_open(self, ws):
        logger.info("Connected to Finnhub WebSocket. Subscribing to FX pairs...")
        for finnhub_symbol in FINNHUB_FX_SYMBOLS.values():
            ws.send(json.dumps({"type": "subscribe", "symbol": finnhub_symbol}))
            logger.info(f"  Subscribed to {finnhub_symbol}")

    def run(self):
        url = f"wss://ws.finnhub.io?token={self.api_key}"
        while True:
            try:
                logger.info("Connecting to Finnhub websocket...")
                ws_app = websocket.WebSocketApp(
                    url,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close,
                    on_open=self.on_open,
                )
                ws_app.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                logger.error(f"Stream crashed: {e}")
            logger.info("Reconnecting in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    stream = FinnhubStream()
    stream.run()
