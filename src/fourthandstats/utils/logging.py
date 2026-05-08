"""Logging configuration for FourthandStats."""

import logging
import sys
from datetime import datetime
from pathlib import Path


def get_logger(name: str, log_to_file: bool = True) -> logging.Logger:
    """Return a configured logger.

    Console output is always enabled. File output writes to logs/ with a
    datestamped filename when log_to_file is True.
    """
    from fourthandstats.utils.paths import LOGS_DIR

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    if log_to_file:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = LOGS_DIR / f"fourthandstats_{date_str}.log"
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger
