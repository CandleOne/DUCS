import asyncio
import datetime

import disnake
from disnake.ext import commands
from sqlalchemy.future import select
from sqlalchemy.orm import subqueryload

from dugs import components, log
from dugs.bot import Dugs
from dugs.database import Company

logger = log.get_logger(__name__)


class Admin(commands.Cog):
    def __init__(self, bot: Dugs) -> None:
        self.bot = bot

    @commands.slash_command(name="clear-companies")
    @commands.has_permissions(manage_roles=True)
    @commands.default_member_permissions(manage_roles=True)
    async def clear_all_companies(self, inter: disnake.GuildCommandInteraction) -> None:
        """Delete all companies in this guild"""
        await inter.response.defer(ephemeral=True)

        # remove guild and all companies from cache
        self.bot.companies._cache.pop(inter.guild.id, {}).values()

        session = self.bot.db()
        deleted_count = 0
        async with session.begin_nested() if session.in_transaction() else session.begin() as trans:
            result = await session.execute(
                select(Company)
                .where(Company.guild_id == inter.guild.id)
                .options(subqueryload(Company.opponent), subqueryload(Company.members))
            )
            companies = result.scalars().all()

            for company in companies:
                deleted_count += 1
                await session.delete(company)

            await trans.commit()

        expire_message_sent = False

        for company in companies:
            if not expire_message_sent:
                if (disnake.utils.utcnow() + datetime.timedelta(seconds=2)) >= inter.expires_at:
                    await inter.edit_original_response(
                        f"This is taking longer than expected. A notification will be sent when it's finished."
                    )
                    expire_message_sent = True

            role = inter.guild.get_role(company.id)
            await role.delete(reason=f"Associated company was cleared by {inter.author}")
            await asyncio.sleep(2)

        message = f"{inter.author.mention}, {deleted_count} companies and their associated roles have been deleted."

        if expire_message_sent:
            await inter.channel.send(message)
            return

        await inter.edit_original_response(message)

    @commands.slash_command(name="view-companies")
    async def view_companies(self, inter: disnake.GuildCommandInteraction) -> None:
        """View this guild's companies' rosters"""

        companies = await self.bot.companies.get_guild_companies(inter.guild.id)

        if not companies:
            await inter.response.send_message(
                "This guild does not have any companies", ephemeral=True
            )
            return

        embeds = []

        for company in companies:
            embeds.append(company.get_company_embed())

        if len(embeds) == 1:
            await inter.response.send_message(embed=embeds[0], components=components.TrashButton)
            return

        await inter.response.send_message(
            embed=embeds[0], view=components.Pagination(embeds, inter.author)
        )


def setup(bot: Dugs) -> None:
    bot.add_cog(Admin(bot))
