import logging
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(os.path.join(LOG_DIR, "steganography.log")), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def log_event(action, status, details=""):
    msg = f"Action: {action} | Status: {status} | Details: {details}"
    if status == "SUCCESS": logger.info(msg)
    else: logger.error(msg)
