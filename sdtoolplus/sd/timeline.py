# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta

from more_itertools import one
from sdclient.client import SDClient
from sdclient.requests import GetDepartmentRequest
from sdclient.requests import GetEmploymentChangedRequest

from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import Active
from sdtoolplus.models import combine_intervals
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.models import Profession
from sdtoolplus.models import T
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitTimeline
from sdtoolplus.models import UnitUUID
from sdtoolplus.sd.tree import ASSUMED_SD_TIMEZONE


def _sd_start_datetime(d: date) -> datetime:
    return datetime.combine(d, time.min, ASSUMED_SD_TIMEZONE)


def _sd_end_datetime(d: date) -> datetime:
    if d == date.max:
        return datetime.max.replace(tzinfo=ASSUMED_SD_TIMEZONE)
    return datetime.combine(d + timedelta(days=1), time.min, ASSUMED_SD_TIMEZONE)


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

    active_intervals = tuple(
        Active(
            start=_sd_start_datetime(dep.ActivationDate),
            end=_sd_end_datetime(dep.DeactivationDate),
            value=True,
        )
        for dep in department.Department
    )
    active_intervals = combine_intervals(active_intervals)

    name_intervals = tuple(
        UnitName(
            start=_sd_start_datetime(dep.ActivationDate),
            end=_sd_end_datetime(dep.DeactivationDate),
            value=dep.DepartmentName,
        )
        for dep in department.Department
    )
    name_intervals = combine_intervals(name_intervals)

    return UnitTimeline(
        active=Timeline[Active](intervals=active_intervals),
        name=Timeline[UnitName](intervals=name_intervals),
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
            profession=Timeline[Profession](intervals=tuple()),
            active=Timeline[Active](intervals=tuple()),
        )

    unit_uuid_intervals = tuple(
        UnitUUID(
            start=_sd_start_datetime(dep.ActivationDate),
            end=_sd_end_datetime(dep.DeactivationDate),
            value=dep.DepartmentUUIDIdentifier,
        )
        for dep in employment.EmploymentDepartment
    )
    unit_uuid_intervals = combine_intervals(unit_uuid_intervals)

    profession_intervals = tuple(
        Profession(
            start=_sd_start_datetime(prof.ActivationDate),
            end=_sd_end_datetime(prof.DeactivationDate),
            value=prof.EmploymentName,
        )
        for prof in employment.Profession
    )
    profession_intervals = combine_intervals(profession_intervals)

    active_intervals = tuple(
        Active(
            start=_sd_start_datetime(status.ActivationDate),
            end=_sd_end_datetime(status.DeactivationDate),
            value=True,
        )
        for status in employment.EmploymentStatus
    )
    active_intervals = combine_intervals(active_intervals)

    return EngagementTimeline(
        unit_uuid=Timeline[UnitUUID](intervals=unit_uuid_intervals),
        profession=Timeline[Profession](intervals=profession_intervals),
        active=Timeline[Active](intervals=active_intervals),
    )
