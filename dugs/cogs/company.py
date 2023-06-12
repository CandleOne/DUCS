import datetime

import disnake
from disnake.ext import commands
from thefuzz import process

from dugs import components, enums, log, utils
from dugs.bot import Dugs
from dugs.database import Company, Member

logger = log.get_logger(__name__)


class CompanyCommands(commands.Cog):
    def __init__(self, bot: Dugs) -> None:
        self.bot = bot

    @commands.slash_command(name="view-user")
    async def indentify_company_user(
        self, inter: disnake.GuildCommandInteraction, member: disnake.Member
    ) -> None:
        """
        Show company information about a member

        Parameters
        ----------
        member: disnake.Member
            Select a member to see their company info
        """
        company = await self.bot.companies.get_member_company(inter.guild.id, member)

        if company is None:
            await inter.response.send_message(
                f"{member.mention} does not belong to a company.", ephemeral=True
            )

        embed = company.get_member(member.id).member_info_embed(inter.guild)
        await inter.response.send_message(embed=embed)

    @commands.slash_command(name="create-company")
    @commands.has_guild_permissions(manage_roles=True)
    @commands.default_member_permissions(manage_roles=True)
    async def create_company(
        self,
        inter: disnake.GuildCommandInteraction,
        company_name: str = commands.Param(converter=utils.validate_company_name, max_length=40),
        color: enums.CompanyColor = commands.Param(choices=enums.CompanyColor),
        company_type: enums.CompanyType = commands.Param(choices=enums.CompanyType),
    ) -> None:
        """
        Create a new company

        Parameters
        ----------
        company_name: str
            Name of the company. [{type} Company] will be appended to the name
        color: enums.CompanyColor
            Select a color to be used as your company's role color
        company_type: enums.CompanyType
            Select the type of company you are creating
        """

        company_name = company_name.replace("[Company]", f"[{company_type} Company]")
        _company = await self.bot.companies.get_company_named(inter.guild.id, company_name)

        if _company and _company.id in [role.id for role in inter.author.roles]:
            await inter.response.send_message(
                f"You are already a member of `{_company.name}`. You must leave before you can create a new company.",
                ephemeral=True,
            )
            return

        if _company:
            await inter.response.send_message(
                f"A company named `{_company.name}` already exists in the guild. Please choose a new name and try again.",
                ephemeral=True,
            )
            return

        role = await inter.guild.create_role(name=company_name, color=color)
        await inter.author.add_roles(role)

        company = Company(
            id=role.id,
            guild_id=inter.guild.id,
            color=color,
            name=role.name,
            type=company_type,
            members=[
                Member(member_id=inter.author.id, company_id=role.id, type=enums.RoleType.Leader)
            ],
        )
        await self.bot.companies.add_company(inter.guild.id, company)

        invite = self.bot.get_global_command_named("invite-to-company")

        embed = disnake.Embed(
            title="New Company!",
            description=(
                "You are now the leader for your new company.\n\n"
                f"You can invite new members with </{invite.name}:{invite.id}>"
            ),
            color=color,
        )
        embed.add_field(name="Name", value=company.name, inline=True)
        embed.add_field(name="Type", value=company_type, inline=True)

        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="join-company")
    async def join_company(self, inter: disnake.GuildCommandInteraction, company: str) -> None:
        """Join a public company

        Parameters
        ----------
        company: str
            Select a company to join
        """
        try:
            _company = await self.bot.companies.get_company(inter.guild.id, int(company))
        except ValueError:
            await inter.response.send_message(f"{company} is not a valid entry", ephemeral=True)
            return

        if _company is None:
            await inter.response.send_message(
                "I could not find a company with your query", ephemeral=True
            )
            return

        if inter.author in _company.members:
            await inter.response.send_message(f"You are already a member of {_company.mention}")

        if _company.type is enums.CompanyType.Private:
            await inter.response.send_message(
                "This is a private company. You must be invited to join", ephemeral=True
            )
            return

        await inter.author.add_roles(disnake.Object(int(company)))

        member = Member(
            member_id=inter.author.id, company_id=_company.id, type=enums.RoleType.Private
        )
        await self.bot.companies.add_company_member(member)

        await inter.response.send_message(f"Welcome to {_company.mention}, {inter.author.mention}")

    @commands.slash_command(name="leave-company")
    async def leave_company(self, inter: disnake.GuildCommandInteraction) -> None:
        """Leave leave a company that you are associated with"""
        company = await self.bot.companies.get_member_company(inter.guild.id, inter.author)

        if company is None:
            await inter.response.send_message(
                "You're not currently associated with any companies.", ephemeral=True
            )
            return

        role = inter.guild.get_role(company.id)

        await self.bot.companies.remove_company_member(company.id, inter.author.id)
        await inter.author.remove_roles(role)
        message = f"You have been relieved of your duties in {company.name}."

        if len(role.members) == 0:
            await role.delete(reason="Associated company roster was empty")
            message += f"This leaves {company.name} without any members, so it will be deleted."

        await inter.response.send_message(message, ephemeral=True)

    @commands.slash_command(name="invite-to-company")
    async def invite_to_company(
        self, inter: disnake.GuildCommandInteraction, member: disnake.Member
    ) -> None:
        """
        Invite a member to your company

        Parameters
        ----------
        member: disnake.Member
            Select a member to invite
        """
        company = await self.bot.companies.get_member_company(inter.guild.id, inter.author)

        if company is None:
            await inter.response.send_message(
                "You are not a member of any companies.", ephemeral=True
            )
            return

        if member in company.members:
            await inter.response.send_message(
                f"{member.mention} is already on your company's roster", ephemeral=True
            )
            return

        member_company = await self.bot.companies.get_member_company(inter.guild.id, member)

        if member_company:
            await inter.response.send_message(
                f"{member.mention} is already a member of {member_company.mention}. They must leave their company before joining another",
                ephemeral=True,
            )
            return

        confirmation = [
            components.ConfirmationButton("accept", inter.guild.id, company.id, member.id),
            components.ConfirmationButton("decline", inter.guild.id, company.id, member.id),
        ]

        embed = company.company_invite_embed(inter, member)

        try:
            await member.send(embed=embed, components=confirmation)
            await inter.response.send_message(
                f"Your invite has been DM'd to {member.mention}", ephemeral=True
            )
        except disnake.Forbidden:
            await inter.response.send_message(
                f"I was unable to DM the invite to {member.mention}; likely due to their privacy settings. Sending invite to the channel",
                ephemeral=True,
            )
            await inter.channel.send(embed=embed, components=confirmation)

    @commands.slash_command(name="resign-leadership")
    async def resign_leadership(self, inter: disnake.GuildCommandInteraction, member: str) -> None:
        """
        Resign your post as a company leader

        Parameters
        ----------
        member: str
            The company member you wish to promote as your replacement
        """
        company = await self.bot.companies.get_member_company(inter.guild.id, inter.author)

        leader = None
        private = None
        for m in company.members:
            if m.id == inter.author.id:
                m.type = enums.RoleType.Private
                private = m.mention
            if m.id == int(member):
                m.type = enums.RoleType.Leader
                leader = m.mention

            if private and leader:
                break

        await self.bot.companies.update_company(inter.guild.id, company)

        await inter.response.send_message(
            f"{company.mention}, {private} has stepped down and appointed {leader} as your new leader!"
        )

    @commands.slash_command(name="show-company-roster")
    async def show_company_members(
        self, inter: disnake.GuildCommandInteraction, company: str
    ) -> None:
        """
        Show the selected company's roster

        Parameters
        ---------
        company: str
            Select a company
        """
        try:
            _company = await self.bot.companies.get_company(inter.guild.id, int(company))
        except ValueError:
            await inter.response.send_message(
                f"`{company}` is not a valid company name", ephemeral=True
            )

        if _company is None:
            await inter.response.send_message(
                "Company not found. Check spelling and try again.", ephemeral=True
            )
            return

        embed = _company.get_company_embed()
        await inter.response.send_message(embed=embed)

    @commands.slash_command(name="declare-war")
    async def declare_war(
        self,
        inter: disnake.GuildCommandInteraction,
        target_company: str,
        duration: datetime.datetime = commands.Param(converter=utils.convert_duration),
    ) -> None:
        """
        Declare war with your the target company for the set duration.

        Parameters
        ----------
        target_company: str
            The company you wish to declare war with
        duration: datetime.datetime
            The amount of time the war should last (ie. 5 hours 30 minutes)
        """
        try:
            target_company: Company = await self.bot.companies.get_company(
                inter.guild.id, int(target_company)
            )
        except ValueError:
            await inter.response.send_message(f"`{target_company}` is not a valid company name")

        member_company: Company = self.bot.companies.get_member_company(
            inter.guild.id, inter.author
        )

        if not member_company:
            await inter.response.send_message(
                "You are not associated with any companies.", ephemeral=True
            )
            return

        if target_company.id == member_company.id:
            await inter.response.send_message(
                "You cannot declare war with your own company.", ephemeral=True
            )
            return

        if not inter.author.id in [
            m.id for m in member_company.members if m.type is enums.RoleType.Leader
        ]:
            await inter.response.send_message(
                "You are not a company leader. You cannot declare war on other companies",
                ephemeral=True,
            )

        await inter.response.send_message("Not implemented", ephemeral=True)

    @resign_leadership.autocomplete("member")
    async def company_member_autocomplete(
        self, inter: disnake.GuildCommandInteraction, string: str
    ) -> str:
        """Handles autocompleting from a company's roster"""
        company = await self.bot.companies.get_member_company(inter.guild.id, inter.author)
        members = [inter.guild.get_member(m.id) for m in company.members if m.id != inter.author.id]
        output = process.extract(string, {str(m.id): m.display_name for m in members}, limit=25)

        return {o[0]: o[-1] for o in output}

    @declare_war.autocomplete("target_company")
    @show_company_members.autocomplete("company")
    @join_company.autocomplete("company")
    async def company_autocompleter(
        self, inter: disnake.GuildCommandInteraction, string: str
    ) -> str:
        """Handles autocompletion of guilds for the user to select from"""

        companies = await self.bot.companies.get_guild_companies(inter.guild.id)
        if inter.application_command.name == "join-company":
            output = process.extract(
                string,
                {str(c.id): c.name for c in companies if c.type is enums.CompanyType.Public},
                limit=25,
            )

            return {o[0]: o[-1] for o in output}

        output = process.extract(
            string,
            {str(c.id): c.name for c in companies},
            limit=25,
        )

        return {o[0]: o[-1] for o in output}


def setup(bot: Dugs) -> None:
    bot.add_cog(CompanyCommands(bot))
