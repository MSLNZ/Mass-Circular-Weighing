from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from msl.equipment import Equipment


def get_specification(equipment: Equipment, tag: str) -> str:
    return equipment.specifications.find(tag).text


# Environmental monitoring equipment
from .ambient_fromwebapp import get_t_rh_now, get_t_rh_during, get_aliases
from .ambient_checks import check_ambient_pre, check_ambient_post
from .vaisala import Vaisala

# Hierarchy of balance classes which each inherit from each other
from .mdebalance import Balance
from .mettler import MettlerToledo
from .aw_carousel import AWBalCarousel
from .aw_linear import AWBalLinear
from .at106 import AT106
