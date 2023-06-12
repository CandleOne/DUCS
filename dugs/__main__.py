import asyncio
import os
import sys

import alembic.command
import alembic.config
import disnake
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

import dugs.alembic
from dugs.bot import Dugs
from dugs.constants import Client, Database
from dugs.log import get_logger

load_dotenv()

logger = get_logger(__name__)

_intents = disnake.Intents.default()
_intents.members = True


def run_upgrade(connection: AsyncConnection, cfg: alembic.config.Config) -> None:
    cfg.attributes["connection"] = connection
    alembic.command.upgrade(cfg, "head")


async def run_async_upgrade(engine: AsyncEngine) -> None:
    alembic_cfg = alembic.config.Config()
    alembic_cfg.set_main_option("script_location", os.path.dirname(dugs.alembic.__file__))
    async with engine.connect() as conn:
        alembic.command.revision(alembic_cfg, autogenerate=True, message="Initialize database")
        await conn.run_sync(run_upgrade, alembic_cfg)


async def run_alembic(bind: str) -> None:
    engine = create_async_engine(bind)
    await run_async_upgrade(engine)


async def verify_or_create_database(db_path: str) -> None:
    db_file = db_path.split("///")[-1]

    if os.path.isfile(db_file):
        logger.info("Database file found and was previously migrated")
        return
    logger.info(f"Database file created at `{db_file}`")
    open(db_file, "a").close()
    logger.info("Running alembic migrations")
    await run_alembic(db_path)


async def main():
    # check for db file and create if necessary
    logger.info("Checking for database file")
    await verify_or_create_database(Database.sqlite_bind)

    bot = Dugs(intents=_intents, reload=True)

    try:
        await bot.load_extensions("./dugs/cogs")
    except Exception:
        await bot.close()
        raise

    try:
        if os.name != "nt":  # handle bot start process or linux/docker
            loop = asyncio.get_event_loop()

            future = asyncio.ensure_future(bot.start(Client.token), loop=loop)
            loop.add_signal_handler(signal.SIGINT, lambda: future.cancel())
            loop.add_signal_handler(signal.SIGTERM, lambda: future.cancel())

            await future

        else:
            await bot.start(Client.token)

    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.warning("Kill signal received. Bot has been closed.")

    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        pass
