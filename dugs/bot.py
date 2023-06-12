import datetime
import os
from sys import version as sys_version

import disnake
from disnake import __version__ as disnake_version
from disnake.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dugs import __version__ as bot_version
from dugs import constants, log
from dugs.companies import Companies

logger = log.get_logger(__name__)


class Dugs(commands.InteractionBot):
    def __init__(self, **kwargs: any) -> None:
        super().__init__(**kwargs)

        self.start_time = disnake.utils.utcnow()
        self.db_engine = engine = create_async_engine(constants.Database.sqlite_bind)
        self.db_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        self.companies: Companies = Companies(self.db_session)

    @property
    def db(self) -> async_sessionmaker[AsyncSession]:
        return self.db_session

    async def on_ready(self) -> None:
        message = (
            "----------------------------------------------------------------------\n"
            f'Bot started at: {datetime.datetime.now().strftime("%m/%d/%Y - %H:%M:%S")}\n'
            f"System Version: {sys_version}\n"
            f"Disnake Version: {disnake_version}\n"
            f"Bot Version: {bot_version}\n"
            f"Connected to Discord as {self.user} ({self.user.id})\n"
            "----------------------------------------------------------------------\n"
        )
        for line in message.split("\n"):
            logger.info(line)

    async def load_extensions(self, path: str) -> None:
        """Loads all extensions in a directory"""

        for extension in os.listdir(path):
            if "__" in extension or not extension.endswith("py"):
                continue

            extension = f"dugs.cogs.{extension[:-3]}"
            super().load_extension(extension)
            logger.info(f"Cog loaded: {extension}")
