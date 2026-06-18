import logging
from logging.handlers import RotatingFileHandler


def configure_logging(log_file):
    logger = logging.getLogger("mov2mp4")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s:%(message)s"))
        logger.addHandler(handler)

    return logger
