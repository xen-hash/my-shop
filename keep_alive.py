"""
keep_alive.py – GadgetHub PH
==============================
Optional background thread that pings the app every 14 minutes
to prevent Render's free tier from spinning down (it sleeps after 15 min).

HOW TO USE:
  Import and call start_keep_alive() from wsgi.py, OR
  run this as a separate Render cron job / background worker.

RENDER FREE TIER NOTE:
  The best solution is to upgrade to Render's paid tier ($7/mo) which
  disables spin-down entirely. This script is a free workaround.
"""

import threading
import time
import os
import logging

logger = logging.getLogger(__name__)


def _ping_loop(url: str, interval: int = 840):
    """Ping the given URL every `interval` seconds (default 14 min)."""
    import urllib.request
    import urllib.error

    # Wait 30 s after startup before first ping
    time.sleep(30)

    while True:
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                logger.info(f"[KeepAlive] Pinged {url} → {response.status}")
        except Exception as e:
            logger.warning(f"[KeepAlive] Ping failed: {e}")
        time.sleep(interval)


def start_keep_alive():
    """Start the keep-alive background thread (call once at app startup)."""
    app_url = os.environ.get("APP_URL", "").rstrip("/")
    if not app_url:
        logger.info("[KeepAlive] APP_URL not set — keep-alive disabled.")
        return

    ping_url = f"{app_url}/"
    t = threading.Thread(target=_ping_loop, args=(ping_url,), daemon=True)
    t.start()
    logger.info(f"[KeepAlive] Started — pinging {ping_url} every 14 min.")