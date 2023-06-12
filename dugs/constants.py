import os
from enum import Enum

from dugs.log import get_logger

logger = get_logger(__name__)

try:
    import dotenv
except ModuleNotFoundError:
    pass
else:
    if dotenv.find_dotenv():
        logger.info("Found .env file, loading into environment")
        dotenv.load_dotenv(override=True)


class Client:
    token = os.getenv("TOKEN")


class Database:
    sqlite_bind = os.getenv("SQLITE_BIND")
    alembic_sqlite_bind = os.getenv("ALEMBIC")
