import disnake

from dugs import components, log

__all__ = ("Pagination",)

logger = log.get_logger(__name__)


class Pagination(disnake.ui.View):
    def __init__(self, embeds: list[disnake.Embed], author: disnake.Member | disnake.User) -> None:
        super().__init__(timeout=None)
        self.author = author
        self.embeds = embeds
        self.index = 0
        self.add_item(components.TrashButton(author.id))

        self._update_state()

    def _update_state(self) -> None:
        self.first_page.disabled = self.prev_page.disabled = self.index == 0
        self.last_page.disabled = self.next_page.disabled = self.index == len(self.embeds) - 1
        self.page_num.label = f"[{self.index+1}/{len(self.embeds)}]"
        self.page_num.disabled = True

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if "trash" in inter.component.custom_id:
            return False

        if self.author.id == inter.author.id:
            return True

        await inter.response.send_message(
            "Sorry. This is not your message to control", ephemeral=True
        )
        return False

    @disnake.ui.button(label="First Page", style=disnake.ButtonStyle.primary)
    async def first_page(
        self, button: disnake.ui.Button, inter: disnake.MessageInteraction
    ) -> None:
        self.index = 0
        self._update_state()

        await inter.response.edit_message(embed=self.embeds[self.index], view=self)

    @disnake.ui.button(label="Previous", style=disnake.ButtonStyle.secondary)
    async def prev_page(self, button: disnake.ui.Button, inter: disnake.MessageInteraction) -> None:
        self.index -= 1
        self._update_state()

        await inter.response.edit_message(embed=self.embeds[self.index], view=self)

    @disnake.ui.button(label="1", style=disnake.ButtonStyle.secondary, disabled=True)
    async def page_num(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        """Just a button that acts as a display to show current page/total pages. Not clickable"""

    @disnake.ui.button(label="Next", style=disnake.ButtonStyle.secondary)
    async def next_page(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.index += 1
        self._update_state()

        await inter.response.edit_message(embed=self.embeds[self.index], view=self)

    @disnake.ui.button(label="Last Page", style=disnake.ButtonStyle.primary)
    async def last_page(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.index = len(self.embeds) - 1
        self._update_state()

        await inter.response.edit_message(embed=self.embeds[self.index], view=self)
