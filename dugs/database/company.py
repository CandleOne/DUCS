from __future__ import annotations

import datetime
from typing import List

import disnake
from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dugs import enums

from .base import Base
from .member import Member


class Company(Base):
    """Represents a Guild Company"""

    __tablename__ = "company"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(65))
    color: Mapped[int] = mapped_column(Enum(enums.CompanyColor), nullable=False)
    type: Mapped[enums.CompanyType] = mapped_column(Enum(enums.CompanyType), nullable=False)
    influence: Mapped[int] = mapped_column(Integer, default=0)
    total_influence: Mapped[int] = mapped_column(Integer, default=0)
    at_war: Mapped[bool] = mapped_column(Boolean, default=False)
    war_expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True, default=None)
    opponent_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("company.id"), nullable=True, default=None
    )
    opponent: Mapped[Company] = relationship("Company", lazy="joined", cascade=("all", "delete"))
    members: Mapped[List[Member]] = relationship("Member", lazy="joined", cascade=("all", "delete"))

    @property
    def mention(self) -> str:
        return f"<@&{self.id}>"

    def get_leader(self) -> Member:
        for member in self.members:
            if member.type is enums.RoleType.Leader:
                return member

    def get_privates(self) -> List[Member]:
        return [member for member in self.members if member.type is enums.RoleType.Private]

    def get_company_embed(self) -> disnake.Embed:
        leader = self.get_leader()
        privates = self.get_privates()

        embed = disnake.Embed(title=f"{self.name}: Info", color=self.color)
        embed.add_field(name="Leader", value=leader.mention, inline=False)
        embed.add_field(name="Privates", value="\n".join(m.mention for m in privates), inline=True)

        return embed

    def get_member(self, member_id: int) -> Member:
        for member in self.members:
            if member.member_id == member_id:
                return member

    def company_invite_embed(
        self, inter: disnake.CommandInteraction, member: disnake.Member
    ) -> disnake.Embed:
        embed = disnake.Embed(title=f"You've been invited to join {self.name}", color=self.color)
        embed.description = f"{inter.author.display_name} has invited you to join their company in {inter.guild.name}"
        return embed
