# gunicorn_conf.py – GadgetHub PH

import os

# ── Workers ───────────────────────────────────────────────────
workers      = 2
worker_class = "gthread"
threads      = 2

# ── Timeouts ──────────────────────────────────────────────────
timeout          = 120
keepalive        = 5
graceful_timeout = 30

# ── Binding ───────────────────────────────────────────────────
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# ── Logging ───────────────────────────────────────────────────
accesslog         = "-"
errorlog          = "-"
loglevel          = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)sµs'

# ── Performance ───────────────────────────────────────────────
worker_tmp_dir      = "/dev/shm"
max_requests        = 1000
max_requests_jitter = 50
preload_app         = True   # load app once before forking (saves RAM)

# ── CRITICAL FIX ─────────────────────────────────────────────
# After forking, child workers inherit the parent's SQLAlchemy
# connection pool. Those inherited connections are invalid in the
# child process and cause every query to hang for 16-25 seconds.
# Disposing the engine immediately after fork forces each worker
# to open fresh connections — this is the standard fix.
def post_fork(server, worker):
    try:
        from models import db
        db.engine.dispose()
        server.log.info(f"[gunicorn] Worker {worker.pid} — engine disposed after fork ✓")
    except Exception as e:
        server.log.warning(f"[gunicorn] Engine dispose failed: {e}")