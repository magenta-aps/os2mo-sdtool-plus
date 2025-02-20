# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from typing import Any
from typing import TypeVar

from more_itertools import one
from sdclient.client import SDClient
from sdclient.requests import GetDepartmentRequest
from sdclient.requests import GetEmploymentChangedRequest
from sdclient.responses import DefaultDates

from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import Active
from sdtoolplus.models import combine_intervals
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.models import EngId
from sdtoolplus.models import EngName
from sdtoolplus.models import T
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitId
from sdtoolplus.models import UnitLevel
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitTimeline
from sdtoolplus.models import UnitUUID
from sdtoolplus.sd.tree import ASSUMED_SD_TIMEZONE


D = TypeVar("D", bound=DefaultDates)


def _sd_start_datetime(d: date) -> datetime:
    return datetime.combine(d, time.min, ASSUMED_SD_TIMEZONE)


def _sd_end_datetime(d: date) -> datetime:
    if d == date.max:
        return datetime.max.replace(tzinfo=ASSUMED_SD_TIMEZONE)
    return datetime.combine(d + timedelta(days=1), time.min, ASSUMED_SD_TIMEZONE)


def _get_intervals(
    interval_class: type[T],
    objs: list[D],
    value_attr: str,
    force_value: Any = None,
) -> tuple[T, ...]:
    intervals = tuple(
        interval_class(
            start=_sd_start_datetime(obj.ActivationDate),
            end=_sd_end_datetime(obj.DeactivationDate),
            value=getattr(obj, value_attr) if force_value is None else force_value,
        )
        for obj in objs
    )
    intervals = combine_intervals(intervals)
    return intervals


def get_department_timeline(
    sd_client: SDClient,
    inst_id: str,
    unit_uuid: OrgUnitUUID,
) -> UnitTimeline:
    department = sd_client.get_department(
        GetDepartmentRequest(
            InstitutionIdentifier=inst_id,
            DepartmentUUIDIdentifier=unit_uuid,
            ActivationDate=date.min,
            DeactivationDate=date.max,
            DepartmentNameIndicator=True,
            UUIDIndicator=True,
        )
    )

    active_intervals = _get_intervals(
        Active, department.Department, "DepartmentName", True
    )
    name_intervals = _get_intervals(UnitName, department.Department, "DepartmentName")
    id_intervals = _get_intervals(UnitId, department.Department, "DepartmentIdentifier")
    level_intervals = _get_intervals(
        UnitLevel, department.Department, "DepartmentLevelIdentifier"
    )

    return UnitTimeline(
        active=Timeline[Active](intervals=active_intervals),
        name=Timeline[UnitName](intervals=name_intervals),
        unit_id=Timeline[UnitId](intervals=id_intervals),
        unit_level=Timeline[UnitLevel](intervals=level_intervals),
    )


def get_engagement_timeline(
    sd_client: SDClient,
    inst_id: str,
    cpr: str,
    emp_id: str,
) -> EngagementTimeline:
    engagement = sd_client.get_employment_changed(
        GetEmploymentChangedRequest(
            InstitutionIdentifier=inst_id,
            PersonCivilRegistrationIdentifier=cpr,
            EmploymentIdentifier=emp_id,
            ActivationDate=date.min,
            DeactivationDate=date.max,
            DepartmentIndicator=True,
            EmploymentStatusIndicator=True,
            ProfessionIndicator=True,
            UUIDIndicator=True,
        )
    )

    try:
        employment = one(one(engagement.Person).Employment)
    except ValueError:
        return EngagementTimeline(
            unit_uuid=Timeline[UnitUUID](intervals=tuple()),
            eng_name=Timeline[EngName](intervals=tuple()),
            eng_id=Timeline[EngId](intervals=tuple),
            active=Timeline[Active](intervals=tuple()),
        )

    unit_uuid_intervals = _get_intervals(
        UnitUUID, employment.EmploymentDepartment, "DepartmentUUIDIdentifier"
    )
    name_intervals = _get_intervals(EngName, employment.Profession, "EmploymentName")
    id_intervals = _get_intervals(EngId, employment.Profession, "JobPositionIdentifier")
    active_intervals = _get_intervals(
        Active, employment.EmploymentStatus, "EmploymentStatusCode", True
    )

    return EngagementTimeline(
        unit_uuid=Timeline[UnitUUID](intervals=unit_uuid_intervals),
        eng_name=Timeline[EngName](intervals=name_intervals),
        eng_id=Timeline[EngId](intervals=id_intervals),
        active=Timeline[Active](intervals=active_intervals),
    )
