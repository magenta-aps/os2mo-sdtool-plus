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
from uuid import UUID
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
    MONTHLY_FULL_TIME = "fuldtid"
    MONTHLY_PART_TIME = "deltid"
    HOURLY = "timelønnet"
    # Work-around due to a bad class state in MO where multiple engagement type classes
    # have been in use. The recalculate key/value can be removed once go into production
    RECALCULATE = "recalculate"

    @classmethod
    def _missing_(cls, value):
        return cls.RECALCULATE


class PersonSyncPayload(BaseModel):
    institution_identifier: str
    cpr: str


class EngagementSyncPayload(BaseModel):
    institution_identifier: str
    cpr: str
    employment_identifier: str


class OrgUnitSyncPayload(BaseModel):
    institution_identifier: str
    org_unit: OrgUnitUUID


class Person(BaseModel):
    cpr: str
    given_name: str
    surname: str
    emails: list[str] | None
    phone_numbers: list[str] | None
    address: str | None


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


class UnitPNumber(Interval[Optional[str]]):
    pass


class UnitPostalAddress(Interval[Optional[str]]):
    pass


class EngagementKey(Interval[str]):
    """
    The SD JobPositionIdentifier corresponding to MOs job_function user_key
    """

    pass


class EngagementName(Interval[Optional[str]]):
    pass


class EngagementUnit(Interval[OrgUnitUUID]):
    pass


class EngagementUnitId(Interval[Optional[str]]):
    pass


class EngagementSDUnit(Interval[Optional[OrgUnitUUID]]):
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
    def has_required_mo_values(self, timestamp: datetime) -> bool:
        """
        Check if the timeline has the sufficient fields in order for the code to be able
        to write to MO.
        """
        raise NotImplementedError()

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

    def get_interval_endpoints(self) -> set[datetime]:
        intervals = [
            cast(tuple[Interval, ...], field.intervals) for _, field in iter(self)
        ]
        return set(collapse((i.start, i.end) for i in chain(*intervals)))


class UnitTimeline(BaseTimeline):
    active: Timeline[Active] = Timeline[Active]()
    name: Timeline[UnitName] = Timeline[UnitName]()
    unit_id: Timeline[UnitId] = Timeline[UnitId]()
    unit_level: Timeline[UnitLevel] = Timeline[UnitLevel]()
    parent: Timeline[UnitParent] = Timeline[UnitParent]()

    def has_required_mo_values(self, timestamp: datetime) -> bool:
        try:
            # Note: not all fields should be included here (e.g. address fields)
            self.active.entity_at(timestamp)
            self.name.entity_at(timestamp)
            self.unit_id.entity_at(timestamp)
            self.unit_level.entity_at(timestamp)
            self.parent.entity_at(timestamp)
            return True
        except NoValueError:
            return False


class EngagementTimeline(BaseTimeline):
    eng_active: Timeline[Active] = Timeline[Active]()
    eng_key: Timeline[EngagementKey] = Timeline[EngagementKey]()
    eng_name: Timeline[EngagementName] = Timeline[EngagementName]()
    eng_unit: Timeline[EngagementUnit] = Timeline[EngagementUnit]()
    eng_sd_unit: Timeline[EngagementSDUnit] = Timeline[EngagementSDUnit]()
    eng_unit_id: Timeline[EngagementUnitId] = Timeline[EngagementUnitId]()
    eng_type: Timeline[EngagementType] = Timeline[EngagementType]()

    def has_required_mo_values(self, timestamp: datetime) -> bool:
        try:
            self.eng_active.entity_at(timestamp)
            self.eng_key.entity_at(timestamp)
            self.eng_name.entity_at(timestamp)
            self.eng_unit.entity_at(timestamp)
            self.eng_sd_unit.entity_at(timestamp)
            self.eng_unit_id.entity_at(timestamp)
            self.eng_type.entity_at(timestamp)
            return True
        except NoValueError:
            return False


class LeaveTimeline(BaseTimeline):
    leave_active: Timeline[Active] = Timeline[Active]()

    def has_required_mo_values(self, timestamp: datetime) -> bool:
        try:
            self.leave_active.entity_at(timestamp)
            return True
        except NoValueError:
            return False


class MOPNumberTimelineObj(BaseModel, frozen=True):
    # MO P-number address UUID
    uuid: UUID | None
    pnumber: Timeline[UnitPNumber] = Timeline[UnitPNumber]()


class MOPostalAddressTimelineObj(BaseModel, frozen=True):
    # MO postal address UUID
    uuid: UUID | None
    postal_address: Timeline[UnitPostalAddress] = Timeline[UnitPostalAddress]()
