from platform import python_version

import disnake
import psutil
from disnake.ext import commands

from dugs import __version__ as bot_version
from dugs import components, log
from dugs.bot import Dugs

logger = log.get_logger(__name__)


class General(commands.Cog):
    def __init__(self, bot: Dugs) -> None:
        self.bot = bot
        self.process = psutil.Process()

    @commands.slash_command(name="botinfo")
    async def botinfo(self, interaction: disnake.CommandInteraction) -> None:
        """View stats and information about CSV,Roles"""
        await interaction.response.defer()

        e = disnake.Embed(title=f"{self.bot.user.name} Status", color=disnake.Colour.random())
        e.set_footer(
            text=f"{self.bot.user} | v{bot_version}", icon_url=self.bot.user.display_avatar.url
        )

        memory = self.process.memory_info()
        memory = memory.rss / 1024**2

        embed = self.format_status_embed(
            e,
            resource_info=f"CPU: `{self.process.cpu_percent():.1f}%`\nRAM: `{memory:.2f} MB`",
            latency=f"`{self.bot.latency * 1000:.2f}ms`",
            python_version=f"`v{python_version()}`",
            disnake_version=f"`v{disnake.__version__}`",
            commands=f"`{len(self.bot.application_commands)}`",
            uptime=f"Since {disnake.utils.format_dt(self.bot.start_time, 'R')}",
            guilds=f"`{len(self.bot.guilds):,}`",
            users=f"`{sum(g.member_count for g in self.bot.guilds):,}`",
        )

        await interaction.edit_original_response(
            embed=embed, components=components.TrashButton(interaction.author.id)
        )

    def format_status_embed(self, embed: disnake.Embed, **kwargs: any) -> disnake.Embed:
        for k, v in kwargs.items():
            name = k.replace("_", " ").title()
            value = v

            embed.add_field(name=name, value=value)

        return embed

    @commands.slash_command(name="ping")
    async def ping_ping(self, inter: disnake.CommandInteraction) -> None:
        """Ping the bot to see its response latency"""
        await inter.response.send_message(
            f"Pong! It took me {(inter.bot.latency*1000):.2f}ms to respond."
        )


def setup(bot: Dugs) -> None:
    bot.add_cog(General(bot))
