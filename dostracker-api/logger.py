import logging
import logging.handlers
import os
from datetime import datetime

# Créer le répertoire logs s'il n'existe pas
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Créer un logger
logger = logging.getLogger("dostracker")
logger.setLevel(logging.DEBUG)

# Format du log
log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Handler pour fichier (rotation quotidienne)
log_file = os.path.join(logs_dir, f"dostracker_{datetime.now().strftime('%Y-%m-%d')}.log")
file_handler = logging.handlers.RotatingFileHandler(
    log_file,
    maxBytes=10485760,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_format)

# Handler pour console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_format)

# Ajouter les handlers au logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def get_logger():
    return logger
