# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from enum import Enum
from itertools import pairwise
from typing import Any
from typing import Generic
from typing import TypeVar
from zoneinfo import ZoneInfo

from more_itertools import first
from more_itertools import last
from more_itertools import only
from more_itertools import split_when
from pydantic import BaseModel
from pydantic import root_validator
from pydantic import validator
from pydantic.generics import GenericModel

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f (%Z)"
V = TypeVar("V")


class AddressTypeUserKey(Enum):
    POSTAL_ADDR = "AddressMailUnit"
    PNUMBER_ADDR = "Pnummer"


class Interval(GenericModel, Generic[V]):
    """
    Interval conventions:
    1) 'start' is included in the interval, but 'end' is not
    2) Infinity will correspond to datetime.max and minus infinity will
       correspond to datetime.min
    3) Timezones must be included
    """

    start: datetime
    end: datetime
    value: V | None

    @root_validator
    def ensure_timezones(cls, values: dict[str, Any]) -> dict[str, Any]:
        start = values["start"]
        end = values["end"]
        if not (
            isinstance(start.tzinfo, ZoneInfo) and isinstance(end.tzinfo, ZoneInfo)
        ):
            raise ValueError("Timezone must be provided")
        if not start.tzinfo == end.tzinfo:
            raise ValueError("Timezones are not identical")
        return values

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"start={self.start.strftime(DATETIME_FORMAT)}, "
            f"end={self.end.strftime(DATETIME_FORMAT)}, "
            f"value={str(self.value)})"
        )

    class Config:
        frozen = True


T = TypeVar("T", bound=Interval)


class Active(Interval[bool]):
    pass


class UnitId(Interval[str]):
    pass


class UnitLevel(Interval[str]):
    pass


class UnitName(Interval[str]):
    pass


def combine_intervals(intervals: tuple[T, ...]) -> tuple[T, ...]:
    """
    Combine adjacent interval entities with same values.

    Example:
        |-------- v1 --------|----- v1 ------|------ v2 ------|
        |---------------- v1 ----------------|------ v2 ------|

    Args:
        intervals: The interval entities to combine.

    Returns:
        Tuple of combined interval entities.
    """
    interval_groups = split_when(
        intervals, lambda i1, i2: i1.end < i2.start or i1.value != i2.value
    )
    return tuple(
        first(group).copy(update={"end": last(group).end}) for group in interval_groups
    )


class Timeline(GenericModel, Generic[T]):
    intervals: tuple[T, ...] = tuple()

    @validator("intervals")
    def entities_must_be_same_type(cls, v):
        if len(v) == 0:
            return v
        if not all(isinstance(entity, type(first(v))) for entity in v):
            raise ValueError("Entities must be of the same type")
        return v

    @validator("intervals")
    def entities_must_be_intervals(cls, v):
        if not all(isinstance(e, Interval) for e in v):
            raise ValueError("Entities must be intervals")
        return v

    @validator("intervals")
    def intervals_must_be_sorted(cls, v):
        starts = [i.start for i in v]
        starts_sorted = sorted(starts)
        if not starts == starts_sorted:
            raise ValueError("Entities must be sorted")
        return v

    @validator("intervals")
    def intervals_cannot_overlap(cls, v):
        if not all(i1.end <= i2.start for i1, i2 in pairwise(v)):
            raise ValueError("Intervals cannot overlap")
        return v

    @validator("intervals")
    def successively_repeated_interval_values_not_allowed(cls, v):
        non_hole_interval_pairs = (
            (i1, i2) for i1, i2 in pairwise(v) if i1.end == i2.start
        )
        if not all(i1.value != i2.value for i1, i2 in non_hole_interval_pairs):
            raise ValueError("Successively repeated interval values are not allowed")
        return v

            )
        return entity

    class Config:
        frozen = True


class UnitTimeline(BaseModel):
    active: Timeline[Active]
    name: Timeline[UnitName]
    unit_id: Timeline[UnitId]
    unit_level: Timeline[UnitLevel]
