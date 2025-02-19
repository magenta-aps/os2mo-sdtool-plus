# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from enum import Enum
from itertools import chain
from itertools import pairwise
from typing import Any
from typing import Generic
from typing import TypeVar

from more_itertools import first
from more_itertools import last
from more_itertools import only
from more_itertools import split_when
from pydantic import BaseModel
from pydantic import root_validator
from pydantic import validator
from pydantic.generics import GenericModel

from sdtoolplus.mo_org_unit_importer import OrgUnitUUID

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
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("Timezone must be provided")
        if not start.tzinfo == end.tzinfo:
            raise ValueError("Timezones are not identical")
        return values

    class Config:
        frozen = True


T = TypeVar("T", bound=Interval)


class Active(Interval[bool]):
    pass


class UnitName(Interval[str]):
    pass


class UnitUUID(Interval[OrgUnitUUID]):
    pass


class Profession(Interval[str]):
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
    intervals: tuple[T, ...]

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

    def entity_at(self, timestamp: datetime) -> T | None:
        return only(e for e in self.intervals if e.start <= timestamp < e.end)

    def diff(self, other: "Timeline[T]") -> "Timeline[T]":
        """
        The method will return a timeline containing intervals where the 'other'
        timeline differs from this one. See ASCII examples drawings in the unittests
        for this method.

        Args:
            other: The timeline to compare to ours.

        Returns:
             A (typically non-continuous) timeline representing the difference between
             our timeline and their timeline.
        """

        endpoints: list[datetime] = list(
            set(
                chain(
                    (i.start for i in self.intervals),
                    (i.end for i in self.intervals),
                    (i.start for i in other.intervals),
                    (i.end for i in other.intervals),
                )
            )
        )
        endpoints.sort()

        interval_list = []
        for endpoint1, endpoint2 in pairwise(endpoints):
            our_entity = self.entity_at(endpoint1)
            their_entity = other.entity_at(endpoint1)

            our_value = our_entity.value if our_entity is not None else None
            their_value = their_entity.value if their_entity is not None else None

            if not our_value == their_value:
                template_entity = our_entity if our_value is not None else their_entity
                interval_list.append(
                    template_entity.copy(  # type: ignore
                        update={
                            "start": endpoint1,
                            "end": endpoint2,
                            "value": our_value,
                        }
                    )
                )

        intervals = combine_intervals(tuple(interval_list))

        return self.__class__(intervals=intervals)

    class Config:
        frozen = True


class UnitTimeline(BaseModel):
    active: Timeline[Active]
    name: Timeline[UnitName]


class EngagementTimeline(BaseModel):
    unit_uuid: Timeline[UnitUUID]
    profession: Timeline[Profession]
    active: Timeline[Active]
    # TODO: add WorkTime if required
