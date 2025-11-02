# Gunicorn configuration file for March Madness Madness

import multiprocessing
import os

# Get the application directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging - using local logs directory
accesslog = os.path.join(BASE_DIR, "logs", "access.log")
errorlog = os.path.join(BASE_DIR, "logs", "error.log")
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "march_madness"

# Server mechanics
daemon = False
pidfile = os.path.join(BASE_DIR, "logs", "gunicorn.pid")
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed in future)
# keyfile = None
# certfile = None
