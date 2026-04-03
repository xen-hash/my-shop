# gunicorn.conf.py – GadgetHub PH
# Place this file in your project root.
# Render will use it automatically when you set the start command to:
#   gunicorn wsgi:app -c gunicorn.conf.py

import multiprocessing

# ── Workers ───────────────────────────────────────────────────
# Render free tier gives 0.1 CPU / 512 MB RAM.
# 2 workers is the sweet spot — enough for concurrency without
# exceeding Supabase's free-tier connection limit.
workers     = 2
worker_class = "gthread"   # threaded workers handle I/O better than sync
threads      = 2           # 2 threads per worker = 4 total concurrent requests

# ── Timeouts ──────────────────────────────────────────────────
timeout      = 120   # Render's health check allows up to 120 s on cold start
keepalive    = 5     # Keep HTTP connections alive for 5 s (reduces TCP overhead)
graceful_timeout = 30

# ── Binding ───────────────────────────────────────────────────
# Render sets the PORT env var automatically.
import os
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# ── Logging ───────────────────────────────────────────────────
accesslog   = "-"   # stdout so Render captures it
errorlog    = "-"
loglevel    = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)sµs'

# ── Performance ───────────────────────────────────────────────
worker_tmp_dir  = "/dev/shm"   # use RAM for worker heartbeat files (faster)
max_requests    = 1000         # restart workers after 1000 requests (prevents memory leaks)
max_requests_jitter = 50       # stagger restarts so not all workers restart at once
preload_app     = True         # load app once before forking — faster cold start
                               # + workers share memory (lower RAM usage)