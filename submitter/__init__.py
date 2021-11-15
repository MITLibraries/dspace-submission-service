"""
DSpace Submission Service
"""
import logging

from submitter.config import Config

CONFIG = Config()
logging.basicConfig(level=getattr(logging, CONFIG.LOG_LEVEL))
if CONFIG.LOG_FILTER == "true":
    for handler in logging.root.handlers:
        handler.addFilter(logging.Filter(__name__))
logger = logging.getLogger(__name__)
logger.info(
    "Logging configured with level=%s, filter=%s", CONFIG.LOG_LEVEL, CONFIG.LOG_FILTER
)
