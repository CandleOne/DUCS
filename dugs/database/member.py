from typing import Optional

import disnake
from sqlalchemy import BigInteger, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from dugs import enums

from .base import Base


class Member(Base):
    """Represents a Company member"""

    __tablename__ = "member"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(BigInteger)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id"))
    type: Mapped[enums.RoleType] = mapped_column(Enum(enums.RoleType))

    def __init__(
        self, *, id: Optional[int] = None, member_id: int, company_id: int, type: enums.RoleType
    ):
        self.id = id
        self.member_id = member_id
        self.company_id = company_id
        self.type = type

    def __eq__(self, object: disnake.Member) -> bool:
        if isinstance(object, disnake.Member):
            return self.member_id == object.id
        return False

    @property
    def mention(self) -> str:
        return f"<@{self.member_id}>"

    def member_info_embed(self, guild: disnake.Guild) -> disnake.Embed:
        member = guild.get_member(self.id)
        embed = disnake.Embed(title=f"Company info for {member.display_name}")
        embed.add_field(name="Company", value=f"<@&{self.company_id}>", inline=True)
        embed.add_field(name="Role", value=self.type)

        return embed
