from enum import Enum


class CompanyType(str, Enum):
    """Available types for a Company"""

    Public = "Public"
    Private = "Private"


class CompanyColor(int, Enum):
    Red = 16711680
    Blue = 255
    Green = 65280
    Cyan = 65535
    Magenta = 16711935
    Yellow = 16776960
    Orange = 16753920
    Purple = 8388736
    Lime = 3329330
    Teal = 32896
    Olive = 8421376
    Maroon = 8388608
    Navy = 128
    Aqua = 8388564
    Pink = 16738740
    Turquoise = 4251856
    Coral = 16744272
    Gold = 16766720
    Violet = 15631086
    Silver = 12632256


class RoleType(str, Enum):
    Leader = "Leader"
    Private = "Private"
