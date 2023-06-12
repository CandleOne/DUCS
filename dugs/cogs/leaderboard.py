from typing import List

import disnake
from disnake.ext import commands
from tabulate import tabulate

from dugs import components
from dugs.bot import Dugs
from dugs.database import Company


class Leaderboard(commands.Cog):
    def __init__(self, bot: Dugs) -> None:
        self.bot = bot

    def ranked_companies_strings(self, companies: List[Company]) -> List[List[any]]:
        sorted_companies = sorted(
            companies, key=lambda company: company.total_influence, reverse=True
        )

        rank = 0
        last_influence = 0
        chunks = []
        current_chunk = []

        for company in sorted_companies:
            if company.total_influence != last_influence:
                rank += 1

            new_line = (
                f"{rank:<8}",
                f"{company.name:<65}",
                f"{company.total_influence:<8}",
            )

            # calculate current length by joining all the strings in all the tuples in the current_chunk
            current_length = sum(len(" ".join(chunk)) for chunk in current_chunk)
            new_line_length = len(" ".join(new_line))

            if current_length + new_line_length > 2000:
                chunks.append(current_chunk)
                current_chunk = [new_line]
            else:
                current_chunk.append(new_line)

            last_influence = company.total_influence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def leaderboard_embed(self, companies: List[Company]) -> List[disnake.Embed]:
        chunked_companies = self.ranked_companies_strings(companies)
        embeds = []

        for idx, chunk in enumerate(chunked_companies):
            if idx == 0:
                embed = disnake.Embed(title="Company Leaderboard")
            else:
                embed = disnake.Embed(title="Company Leaderboard (continued)")
            table = tabulate(
                chunk,
                headers=["Rank", "Company", "Influence"],
                tablefmt="simple",
                stralign="left",
                numalign="left",
            )
            embed.description = f"```py\n{table}\n```"
            embeds.append(embed)

        return embeds

    @commands.slash_command(name="company-leaderboard")
    async def company_leaderboard(self, inter: disnake.GuildCommandInteraction) -> None:
        """Display the guild's company leaderboard"""

        companies = await self.bot.companies.get_guild_companies(inter.guild.id)

        if not companies:
            await inter.response.send_message(
                "This guild does not have any companies", ephemeral=True
            )
            return

        embeds = self.leaderboard_embed(companies)
        if len(embeds) == 1:
            await inter.response.send_message(
                embed=embeds[0], components=components.TrashButton(inter.author.id)
            )
        else:
            await inter.response.send_message(
                embed=embeds[0], view=components.Pagination(embeds, inter.author)
            )


def setup(bot: Dugs) -> None:
    bot.add_cog(Leaderboard(bot))
