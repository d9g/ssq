# Gunicorn 配置文件
import multiprocessing
import os

# 服务器socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker进程
# 计算公式: (2 x CPU核心数) + 1
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# 日志
# 确保 logs 目录存在
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

accesslog = os.path.join(log_dir, "gunicorn_access.log")
errorlog = os.path.join(log_dir, "gunicorn_error.log")
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 进程命名
proc_name = "ssq_webapp"

# 守护进程模式（生产环境建议使用 systemd 管理，这里设为 False）
daemon = False

# 用户和组（如果使用专用用户，取消注释并修改）
# user = "ssq"
# group = "ssq"

# 临时目录
tmp_upload_dir = None

# 预加载应用（提高性能，但会增加内存使用）
preload_app = False

# Worker 超时设置
graceful_timeout = 30
