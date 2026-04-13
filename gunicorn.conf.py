# gunicorn.conf.py – GadgetHub PH

import os

# ── Workers ───────────────────────────────────────────────────
# Using 1 worker + 4 threads instead of 2 workers.
# WHY: With preload_app=True, gunicorn forks the parent process into
# child workers. SQLAlchemy's connection pool is inherited across the
# fork, making all connections invalid in child processes — causing
# every DB query to hang for 16+ seconds while it times out.
# 1 worker = no forking = no inherited connections = fast queries.
# 4 threads handles the same concurrency without the fork problem.
workers      = 1
worker_class = "gthread"
threads      = 4

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
max_requests        = 500
max_requests_jitter = 50
preload_app         = False   # disabled — not needed with 1 worker, avoids fork issues