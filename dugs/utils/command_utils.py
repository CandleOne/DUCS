import datetime
import functools
import re

import disnake

__all__ = ("convert_duration", "validate_company_name")

DATE_PATTERNS: dict[str, str] = {
    "seconds": r"(?i)(\d+)\s*(?:seconds?|secs?|s)",
    "minutes": r"(?i)(\d+)\s*(?:minutes?|mins?|m)",
    "hours": r"(?i)(\d+)\s*(?:hours?|hrs?|h)",
    "days": r"(?i)(\d+)\s*(?:days?|d)",
    "weeks": r"(?i)(\d+)\s*(?:weeks?|w)",
}

BLOCKED_WORDS: str = ()


def convert_duration(inter: disnake.CommandInteraction, duration: str) -> datetime.datetime:
    """
    Parse a duration string and return a datetime.datetime object representing the duration from now.

    This function extracts time units (weeks, days, hours, minutes, seconds) from the duration string,
    and then generates a future datetime object. If the duration string contains duplicate or invalid time units,
    it sends a failure message back via the provided interaction.

    Parameters
    ----------
    inter : disnake.GuildCommandInteraction
        The command interaction from which the duration string originated. It's also used to send back failure messages.
    duration : str
        The string representing the duration. Time units in the string should be separated by whitespace.
        It supports weeks, days, hours, minutes, and seconds.

    Returns
    -------
    datetime.datetime
        A datetime object that represents the current UTC time plus the duration parsed from the string.
    """
    result = dict.fromkeys(DATE_PATTERNS, 0)
    now = datetime.datetime.now(datetime.timezone.utc)

    def _extract(key: str, match: re.Match[str]) -> str:
        value = int(match.group(1))
        result[key] = value
        return " "

    for key, pattern in DATE_PATTERNS.items():
        extractor = functools.partial(_extract, key)
        duration = re.sub(pattern, extractor, duration, count=1)

    if duration.isspace():
        return now + datetime.timedelta(
            days=7 * result["weeks"] + result["days"],
            hours=result["hours"],
            seconds=60 * result["minutes"] + result["seconds"],
        )

    keys = re.findall(r"\d+\s*\S", duration)
    keys = ", ".join(map(repr, keys))
    raise ValueError(f"Failed to parse duration input {keys}. Might be duplicate or invalid")


def validate_company_name(inter: disnake.CommandInteraction, company_name: str) -> str:
    """Validates the propsed company name submitted by the user

    If "company", in any form is included in the company name, it is removed since this
    validation function will return the company name as `{company_name} [Company]`

    Raises a ValueError if the name is any blocked words are used in the name
    """

    for word in BLOCKED_WORDS:
        if not isinstance(word, str):
            continue
        if word.casefold() in company_name.casefold():
            raise ValueError(f"Company names cannot contain the word {word}.")

    company_name = company_name.lower().replace("company", "")

    return f"{company_name.title()} [Company]"


if __name__ == "__main__":
    duration = "12 hours 30 minutes"
    print(convert_duration(duration))
