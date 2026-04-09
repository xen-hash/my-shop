"""
keep_alive.py – GadgetHub PH
==============================
Two background threads:
  1. HTTP ping — hits the app URL every 14 min so Render never spins down.
  2. DB ping   — runs SELECT 1 every 4 min so Neon never auto-suspends.

Neon free tier suspends compute after 5 min of inactivity, causing
1-3 second delays on the next query. Pinging every 4 min prevents this.
"""

import threading
import time
import os
import logging

logger = logging.getLogger(__name__)


def _http_ping_loop(url: str, interval: int = 840):
    """Ping the app URL every 14 min (Render spins down after 15 min)."""
    import urllib.request
    time.sleep(30)  # let app fully start first
    while True:
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                logger.info(f"[KeepAlive] HTTP → {r.status}")
        except Exception as e:
            logger.warning(f"[KeepAlive] HTTP ping failed: {e}")
        time.sleep(interval)


def _db_ping_loop(app, interval: int = 240):
    """Run SELECT 1 every 4 min inside app context to keep Neon awake."""
    from sqlalchemy import text
    time.sleep(60)  # let DB init complete first
    while True:
        try:
            with app.app_context():
                from models import db
                db.session.execute(text("SELECT 1"))
                db.session.remove()
            logger.info("[KeepAlive] DB ping ✓")
        except Exception as e:
            logger.warning(f"[KeepAlive] DB ping failed: {e}")
        time.sleep(interval)


def start_keep_alive(app=None):
    """Start keep-alive threads. Pass the Flask app for DB pinging."""

    # HTTP thread — keeps Render from spinning down
    app_url = os.environ.get("APP_URL", "").rstrip("/")
    if app_url:
        t1 = threading.Thread(
            target=_http_ping_loop,
            args=(f"{app_url}/",),
            daemon=True
        )
        t1.start()
        logger.info(f"[KeepAlive] HTTP thread started — pinging every 14 min")
    else:
        logger.info("[KeepAlive] APP_URL not set — HTTP keep-alive disabled")

    # DB thread — keeps Neon from suspending
    if app and os.environ.get("DATABASE_URL"):
        t2 = threading.Thread(
            target=_db_ping_loop,
            args=(app,),
            daemon=True
        )
        t2.start()
        logger.info("[KeepAlive] DB thread started — pinging Neon every 4 min")