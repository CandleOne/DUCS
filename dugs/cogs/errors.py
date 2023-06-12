import traceback

import disnake
from disnake.ext import commands

from dugs import components, log
from dugs.bot import Dugs

logger = log.get_logger(__name__)


class ErrorHandler(commands.Cog):
    """Handles command errors that are raised"""

    def __init__(self, bot: Dugs) -> None:
        self.bot = bot

    @staticmethod
    def critical_error_embed(error: Exception) -> None:
        error_str = "".join(
            traceback.format_exception(type(error), error, tb=error.__traceback__, limit=-3)
        ).replace("``", "`\u200b`")
        if len(error_str) > 3000:
            error_str = error_str[-3000:]

        msg = (
            "A critical error has occurred internally during the action you were trying to execute. "
            "If this error continues, please report this error and the code below to the support server. "
            f"\n\n```py\n{error_str}\n```"
        )

        embed = disnake.Embed(
            title="Critical Error Occurred",
            description=msg,
            color=disnake.Color.red(),
        )
        return embed

    @commands.Cog.listener("on_slash_command_error")
    async def command_error_handler(
        self, inter: disnake.GuildCommandInteraction, error: Exception
    ) -> None:
        error = getattr(error, "original", error)

        if isinstance(error, commands.MissingPermissions):
            logger.info(
                f"{inter.author} is missing permissions in {inter.guild.name} {tuple(error.missing_permissions)}"
            )
            permissions = ", ".join(
                f"`{p.replace('_',' ').title()}`" for p in error.missing_permissions
            )
            await inter.response.send_message(
                f"You are missing the required permissions to perform this task. {permissions}",
                components=components.TrashButton(inter.author.id),
                ephemeral=True,
            )
            return

        if isinstance(error, ValueError):
            await inter.response.send_message(str(error), ephemeral=True)
            return

        embed = self.critical_error_embed(error)
        error_msg = " ".join(traceback.format_exception(type(error), error, error.__traceback__))
        logger.critical(error_msg)
        if inter.response._response_type is not None:
            await inter.delete_original_response()
            await inter.followup.send(
                embed=embed, components=components.TrashButton(inter.author.id)
            )
            return

        await inter.response.send_message(
            embed=embed, components=components.TrashButton(inter.author.id)
        )


def setup(bot: Dugs) -> None:
    bot.add_cog(ErrorHandler(bot))
