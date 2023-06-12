from typing import List

import disnake
from disnake.ext import commands, tasks
from sqlalchemy.future import select
from sqlalchemy.orm import subqueryload

from dugs import errors, log
from dugs.bot import Dugs
from dugs.database import Company

logger = log.get_logger(__name__)


class Tasks(commands.Cog):
    def __init__(self, bot: Dugs) -> None:
        self.bot = bot
        self.check_war_complete.start()
        self.fill_company_cache.start()

    def calculate_winner(self, company: Company):
        opponent = company.opponent

        if company.influence > opponent.influence:
            return company, opponent

        if company.influence < opponent.influence:
            return opponent, company

        raise errors.TieError(company, opponent)

    @tasks.loop(seconds=30)
    async def check_war_complete(self):
        now = disnake.utils.utcnow()

        for guild in self.bot.guilds:
            embeds = []
            embed = disnake.Embed(title="War has completed")

            companies_at_war = await self.bot.companies.get_companies_at_war(guild.id)

            if not companies_at_war:
                continue

            for company in companies_at_war:
                try:
                    winner, loser = self.calculate_winner(company)
                except errors.TieError as e:
                    embed.description = f"The war between {e.company1.role.mention} and {e.company2.role.mention} is over and resulted in a tie!"
                    embed.clear_fields()
                    for company in (e.company1, e.company2):
                        embed.add_field(
                            name=company.name, value=f"{company.influence} influence", inline=True
                        )

                else:
                    embed.description = f"The war between {winner.role.mention} and {loser.role.mention} is over and **{winner.role.mention}** has come away with victory!"
                    embed.color = winner.role.color
                    embed.clear_fields()
                    for company in (winner, loser):
                        embed.add_field(
                            name=company.name, value=f"{company.influence} influence", inline=True
                        )

                finally:
                    for company in (company, company.opponent):
                        company.total_influence += company.influence
                        company.influence = 0

                        await self.bot.companies.update_company(guild.id, company)

                embeds.append(embed)

            war_channel = disnake.utils.get(guild.text_channels, name="war-announcements")
            await war_channel.send(embeds=embeds)

    @tasks.loop(count=1)
    async def fill_company_cache(self) -> None:
        session = self.bot.db()

        async with session.begin() as trans:
            result = await session.execute(
                select(Company).options(
                    subqueryload(Company.members), subqueryload(Company.opponent)
                )
            )
            companies: List[Company] = result.scalars().all()

        if not companies:
            return

        logger.info(f"Caching {len(companies)} companies in {len(self.bot.guilds)} guilds")

        for guild in self.bot.guilds:
            self.bot.companies._cache[guild.id] = {
                c.id: c for c in companies if c.guild_id == guild.id
            }

            added_opponents = set()
            if guild.id not in self.bot.companies._at_war:
                self.bot.companies._at_war[guild.id] = []

            for company in companies:
                if (
                    company.at_war
                    and company.opponent_id
                    and company.opponent_id not in added_opponents
                ):
                    self.bot.companies._at_war[guild.id].append(company)
                    added_opponents.add(company.opponent_id)

    @check_war_complete.before_loop
    @fill_company_cache.before_loop
    async def before_war_check(self) -> None:
        """Ensures bot is ready before war_check task is allowed to start"""
        await self.bot.wait_until_ready()


def setup(bot: Dugs) -> None:
    bot.add_cog(Tasks(bot))
