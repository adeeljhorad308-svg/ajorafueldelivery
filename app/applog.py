"""General application log (logs/app.log): status changes and other admin
actions worth a paper trail. Security events (logins, lockouts) go to
logs/security.log via app/security.py instead."""

import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import current_app


def init_app_log(app):
    log_dir = Path(app.config["LOG_DIR"])
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_dir / "app.log", maxBytes=1_000_000, backupCount=5)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    formatter.converter = time.gmtime  # log timestamps are UTC, like the rest of the app
    handler.setFormatter(formatter)
    logger = logging.getLogger("ajora.app")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    app.extensions["app_logger"] = logger


def app_logger():
    return current_app.extensions["app_logger"]
