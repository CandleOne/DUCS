import datetime
from typing import Literal, Optional

import disnake

__all__ = (
    "ConfirmationButton",
    "TrashButton",
)


class ConfirmationButton(disnake.ui.Button):
    def __init__(
        self,
        type: Literal["accept", "decline"],
        guild_id: int,
        company_id: int,
        member_id: int,
        expires_at: Optional[datetime.datetime] = None,
    ) -> None:
        custom_id = f"{type}:{guild_id}:{company_id}:{member_id}"

        if expires_at:
            timestamp = datetime.datetime.timestamp(expires_at)
            custom_id += f":{timestamp}"

        if type == "accept":
            label = type.title()
            style = disnake.ButtonStyle.success
        else:
            label = type.title()
            style = disnake.ButtonStyle.danger

        super().__init__(label=label, style=style, custom_id=custom_id)


class TrashButton(disnake.ui.Button):
    """Creates a Trash button to delete the message it's attached to"""

    def __init__(self, member_id: int):
        super().__init__(
            emoji="🪓",
            style=disnake.ButtonStyle.gray,
            custom_id=f"{member_id}_trash",
        )
