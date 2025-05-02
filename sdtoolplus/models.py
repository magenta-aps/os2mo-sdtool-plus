# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from enum import Enum
from itertools import chain
from itertools import pairwise
from typing import Any
from typing import Generic
from typing import Optional
from typing import Self
from typing import TypeVar
from typing import cast
from zoneinfo import ZoneInfo

import structlog.stdlib
from more_itertools import collapse
from more_itertools import first
from more_itertools import last
from more_itertools import only
from more_itertools import split_when
from pydantic import BaseModel
from pydantic import root_validator
from pydantic import validator
from pydantic.generics import GenericModel

from sdtoolplus.exceptions import NoValueError
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID

NEGATIVE_INFINITY = datetime.min.replace(tzinfo=ZoneInfo("UTC"))
POSITIVE_INFINITY = datetime.max.replace(tzinfo=ZoneInfo("UTC"))

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f (%Z)"

V = TypeVar("V")

logger = structlog.stdlib.get_logger()


class AddressTypeUserKey(Enum):
    POSTAL_ADDR = "AddressMailUnit"
    PNUMBER_ADDR = "Pnummer"


class EngType(Enum):
    MONTHLY_FULL_TIME = "Månedslønnet, fuldtid"
    MONTHLY_PART_TIME = "Månedslønnet, deltid"
    HOURLY = "Timelønnet"


class PersonSyncPayload(BaseModel):
    institution_identifier: str
    cpr: str


class Person(BaseModel):
    cpr: str
    given_name: str
    surname: str
    emails: list[str]
    phone_numbers: list[str]
    addresses: list[str]


class Interval(GenericModel, Generic[V], frozen=True):
    """
    Interval conventions:
    1) 'start' is included in the interval, but 'end' is not
    2) Infinity will correspond to datetime.max and minus infinity will
       correspond to datetime.min
    3) Timezones must be included
    """

    start: datetime
    end: datetime
    value: V

    @root_validator
    def ensure_timezones(cls, values: dict[str, Any]) -> dict[str, Any]:
        start = values["start"]
        end = values["end"]
        if not (
            isinstance(start.tzinfo, ZoneInfo) and isinstance(end.tzinfo, ZoneInfo)
        ):
            raise ValueError("Timezone must be provided")
        return values

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"start={self.start.strftime(DATETIME_FORMAT)}, "
            f"end={self.end.strftime(DATETIME_FORMAT)}, "
            f"value={str(self.value)})"
        )


T = TypeVar("T", bound=Interval)


class Active(Interval[bool]):
    pass


class UnitId(Interval[str]):
    pass


class UnitLevel(Interval[Optional[str]]):
    pass


class UnitName(Interval[str]):
    pass


class UnitParent(Interval[Optional[OrgUnitUUID]]):
    pass


class EngagementKey(Interval[str]):
    """
    The SD JobPositionIdentifier corresponding to MOs job_function user_key
    """

    pass


class EngagementName(Interval[str]):
    pass


class EngagementUnit(Interval[OrgUnitUUID]):
    pass


class EngagementUnitId(Interval[Optional[str]]):
    pass


class EngagementType(Interval[EngType]):
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


class Timeline(GenericModel, Generic[T], frozen=True):
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

    def entity_at(self, timestamp: datetime) -> T:
        entity = only(e for e in self.intervals if e.start <= timestamp < e.end)
        if entity is None:
            raise NoValueError(
                f"No value found at {timestamp.strftime(DATETIME_FORMAT)}"
            )
        return entity


class BaseTimeline(BaseModel, frozen=True):
    def has_value(self, timestamp: datetime) -> bool:
        # TODO: unit test
        fields = [field for _, field in iter(self)]
        try:
            for field in fields:
                field.entity_at(timestamp)
            return True
        except NoValueError:
            return False

    def equal_at(self, timestamp: datetime, other: Self) -> bool:
        # TODO: unit test <-- maybe we should do this anytime soon now...
        missing = object()
        self_fields = [field for _, field in iter(self)]
        other_fields = [field for _, field in iter(other)]
        for self_field, other_field in zip(self_fields, other_fields):
            try:
                v1: Any = self_field.entity_at(timestamp).value
            except NoValueError:
                v1 = missing
            try:
                v2 = other_field.entity_at(timestamp).value
            except NoValueError:
                v2 = missing

            if v1 != v2:
                return False
        return True


class UnitTimeline(BaseTimeline):
    active: Timeline[Active] = Timeline[Active]()
    name: Timeline[UnitName] = Timeline[UnitName]()
    unit_id: Timeline[UnitId] = Timeline[UnitId]()
    unit_level: Timeline[UnitLevel] = Timeline[UnitLevel]()
    parent: Timeline[UnitParent] = Timeline[UnitParent]()


class EngagementTimeline(BaseTimeline):
    eng_active: Timeline[Active] = Timeline[Active]()
    eng_key: Timeline[EngagementKey] = Timeline[EngagementKey]()
    eng_name: Timeline[EngagementName] = Timeline[EngagementName]()
    eng_unit: Timeline[EngagementUnit] = Timeline[EngagementUnit]()
    eng_unit_id: Timeline[EngagementUnitId] = Timeline[EngagementUnitId]()
    eng_type: Timeline[EngagementType] = Timeline[EngagementType]()

    def get_interval_endpoints(self) -> set[datetime]:
        return set(
            collapse(
                set(
                    (i.start, i.end)
                    for i in chain(
                        cast(tuple[Interval, ...], self.eng_active.intervals),
                        cast(tuple[Interval, ...], self.eng_key.intervals),
                        cast(tuple[Interval, ...], self.eng_name.intervals),
                        cast(tuple[Interval, ...], self.eng_unit.intervals),
                        cast(tuple[Interval, ...], self.eng_unit_id.intervals),
                        cast(tuple[Interval, ...], self.eng_type.intervals),
                    )
                )
            )
        )


class LeaveTimeline(BaseTimeline):
    leave_active: Timeline[Active] = Timeline[Active]()

    def get_interval_endpoints(self) -> set[datetime]:
        return set(
            collapse(
                set(
                    (i.start, i.end)
                    for i in chain(
                        cast(tuple[Interval, ...], self.leave_active.intervals)
                    )
                )
            )
        )
