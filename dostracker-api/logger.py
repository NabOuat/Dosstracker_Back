import logging
import os
import sys

# Créer un logger
logger = logging.getLogger("dostracker")
logger.setLevel(logging.DEBUG)
logger.propagate = False

# Format du log
log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Handler pour console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
console_handler.setFormatter(log_format)

# Ajouter les handlers au logger
logger.addHandler(console_handler)

def get_logger():
    return logger
