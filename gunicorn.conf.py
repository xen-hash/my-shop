# gunicorn.conf.py – GadgetHub PH

import os

# 1 worker + 4 threads = no fork, no inherited dead connections
# This eliminates the 16-second hang caused by SQLAlchemy
# connection pools being copied across forked worker processes.
workers      = 1
worker_class = "gthread"
threads      = 4

timeout          = 30    # fail fast — don't let slow requests pile up
keepalive        = 5
graceful_timeout = 10

bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

accesslog         = "-"
errorlog          = "-"
loglevel          = "warning"   # reduce log noise
access_log_format = '%(h)s "%(r)s" %(s)s %(D)sµs'

worker_tmp_dir      = "/dev/shm"
max_requests        = 500
max_requests_jitter = 50
preload_app         = False     # no fork = no connection inheritance issues