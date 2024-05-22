import sys
import logging

from prometheus_client import Gauge

from utils.config import DEBUG

# Prometheus
APP_RUNNING = Gauge('up', '1 - app is running, 0 - app is down', labelnames=['name'])


# Logging configuration
def set_logging_configuration():
    log_level = logging.DEBUG if DEBUG else logging.INFO
    logging.basicConfig(stream=sys.stdout, level=log_level, format='[%(asctime)s] %(levelname)s - %(name)s - %(module)s:%(funcName)s - %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
