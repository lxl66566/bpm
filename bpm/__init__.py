import logging
import os

LOGLEVEL = os.environ.get("DEBUG")
logging.basicConfig(
    format="%(levelname)s: %(message)s",
    level=logging.INFO if not LOGLEVEL else logging.DEBUG,
)
