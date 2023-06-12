from typing import List

import disnake
from disnake.ext import commands

from dugs import log
from dugs.bot import Dugs
from dugs.database import Member
from dugs.enums import RoleType

logger = log.get_logger(__name__)

MIN_CHARACTERS = 2
MIN_VALID_WORDS = 3
VALID_WORD_INFLUENCE = 1
VALID_IMAGE_INFLUENCE = 5
VALID_VIDEO_INFLUENCE = 10


class Events(commands.Cog):
    def __init__(self, bot: Dugs) -> None:
        self.bot = bot

    def calculate_influence(self, message: disnake.Message) -> int:
        influence = 0

        valid_words = [word for word in message.content.split() if len(word) >= MIN_CHARACTERS]
        if len(valid_words) >= MIN_VALID_WORDS:
            influence += VALID_WORD_INFLUENCE

        if message.attachments:
            for attachment in message.attachments:
                if "image" in attachment.content_type:
                    influence += VALID_IMAGE_INFLUENCE
                if "video" in attachment.content_type:
                    influence += VALID_VIDEO_INFLUENCE

        return influence

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message) -> None:
        """Executed when a `message_create` event is received from Discord."""

        if message.author.bot:
            return

        companies_at_war = await self.bot.companies.get_companies_at_war(message.guild.id)

        if not companies_at_war:
            return

        for company in companies_at_war:
            if not message.author in company.members:
                continue

            company.influence += self.calculate_influence(message)
            await self.bot.companies.update_company(message.guild.id, company)

    @commands.Cog.listener("on_button_click")
    async def handle_company_invite(self, inter: disnake.MessageInteraction) -> None:
        """Handles confirmation button interactions on company invite messages"""

        if not any(action in inter.component.custom_id for action in ("accept", "decline")):
            return

        component_id = inter.component.custom_id.split(":")

        if len(component_id) > 4:
            # component includes timestamp, likely a war invite and
            # not a comapany invite
            return

        action, guild_id, company_id, member_id = component_id

        if inter.author.id != int(member_id):
            await inter.response.send_message(
                "This invitation is not yours to reply to", ephemeral=True
            )
            return

        company = await self.bot.companies.get_company(int(guild_id), int(company_id))
        guild = inter.guild or self.bot.get_guild(int(guild_id))
        member = inter.author if inter.guild else guild.get_member(inter.author.id)
        await member.add_roles(disnake.Object(id=int(company_id)))

        if action == "decline":
            await inter.response.send_message(
                f"You have denied the invitation to `{company.name}`", ephemeral=True
            )
        else:
            member = Member(member_id=inter.author.id, type=RoleType.Private, company_id=company_id)
            company.members.append(member)
            await self.bot.companies.add_company_member(member)

            await inter.response.send_message(
                f"You are now a member of {company.name}!", ephemeral=True
            )

        # disable the buttons
        rows = disnake.ui.ActionRow.rows_from_message(inter.message)
        for row in rows:
            for component in row:
                component.disabled = True

        await inter.message.edit(components=rows)

    @commands.Cog.listener("on_button_click")
    async def handle_trash_button(self, inter: disnake.MessageInteraction) -> None:
        """Delete a message if the user has permission to do so"""

        if not "trash" in inter.component.custom_id:
            return

        if (
            not str(inter.author.id) in inter.component.custom_id
            or not inter.channel.permissions_for(inter.author).manage_messages
        ):
            await inter.response.send_message(
                "You are not the person that requested this message.", ephemeral=True
            )
            return

        await inter.response.defer()
        await inter.delete_original_response()

    @commands.Cog.listener("on_slash_command")
    async def log_slash_command_usage(self, inter: disnake.CommandInteraction) -> None:
        """Logs slash command usage"""

        def get_invoked_command_name(inter: disnake.CommandInteraction) -> str:
            invoked_command_name = [inter.application_command.name]

            def parse_options(options: List[disnake.Option]) -> None:
                for option in options:
                    print(option.type)
                    if option.type is disnake.OptionType.sub_command:
                        invoked_command_name.append(option.name)
                        return

                    if option.type is disnake.OptionType.sub_command_group:
                        invoked_command_name.append(option.name)
                        parse_options(option.options)
                        return

            parse_options(inter.data.options)

            return " ".join(invoked_command_name)

        invoked_command = get_invoked_command_name(inter)
        logger.info(
            f"`/{invoked_command}` was used in `{inter.guild.name}` by {inter.author.display_name}"
        )


def setup(bot: Dugs) -> None:
    bot.add_cog(Events(bot))
