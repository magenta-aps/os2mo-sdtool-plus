# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import asyncio
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta

import structlog
from more_itertools import only
from sdclient.client import SDClient
from sdclient.exceptions import SDParentNotFound
from sdclient.exceptions import SDRootElementNotFound
from sdclient.requests import GetDepartmentRequest
from sdclient.requests import GetEmploymentChangedRequest

from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import POSITIVE_INFINITY
from sdtoolplus.models import Active
from sdtoolplus.models import EngagementKey
from sdtoolplus.models import EngagementName
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.models import EngagementUnit
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitId
from sdtoolplus.models import UnitLevel
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitParent
from sdtoolplus.models import UnitTimeline
from sdtoolplus.models import combine_intervals
from sdtoolplus.sd.tree import ASSUMED_SD_TIMEZONE

logger = structlog.stdlib.get_logger()


def _sd_start_datetime(d: date) -> datetime:
    return datetime.combine(d, time.min, ASSUMED_SD_TIMEZONE)


def _sd_end_datetime(d: date) -> datetime:
    if d == date.max:
        return POSITIVE_INFINITY
    # We have to add one day to the SD end date when converting to a timeline end
    # datetime, since we are working with a continuous timeline. E.g. the SD end date
    # 1999-12-31 states that the effective end datetime is 1999-12-31T23:59:59.999999,
    # which (due to the continuous timeline) translates into the end datetime
    # t_end = 2000-01-01T00:00:00.000000 in the half-open interval [t_start, t_end)
    return datetime.combine(d, time.min, ASSUMED_SD_TIMEZONE) + timedelta(days=1)


async def get_department_timeline(
    sd_client: SDClient,
    inst_id: str,
    unit_uuid: OrgUnitUUID,
) -> UnitTimeline:
    logger.info("Get SD department timeline", inst_id=inst_id, unit_uuid=str(unit_uuid))

    try:
        department = await asyncio.to_thread(
            sd_client.get_department,
            GetDepartmentRequest(
                InstitutionIdentifier=inst_id,
                DepartmentUUIDIdentifier=unit_uuid,
                ActivationDate=date.min,
                DeactivationDate=date.max,
                DepartmentNameIndicator=True,
                UUIDIndicator=True,
            ),
        )
        parents = sd_client.get_department_parent_history(unit_uuid)
    except (SDRootElementNotFound, SDParentNotFound):
        return UnitTimeline()

    active_intervals = tuple(
        Active(
            start=_sd_start_datetime(dep.ActivationDate),
            end=_sd_end_datetime(dep.DeactivationDate),
            value=True,
        )
        for dep in department.Department
    )

    id_intervals = tuple(
        UnitId(
            start=_sd_start_datetime(dep.ActivationDate),
            end=_sd_end_datetime(dep.DeactivationDate),
            value=dep.DepartmentIdentifier,
        )
        for dep in department.Department
    )

    level_intervals = tuple(
        UnitLevel(
            start=_sd_start_datetime(dep.ActivationDate),
            end=_sd_end_datetime(dep.DeactivationDate),
            value=dep.DepartmentLevelIdentifier,
        )
        for dep in department.Department
    )

    name_intervals = tuple(
        UnitName(
            start=_sd_start_datetime(dep.ActivationDate),
            end=_sd_end_datetime(dep.DeactivationDate),
            value=dep.DepartmentName,
        )
        for dep in department.Department
    )

    parent_intervals = tuple(
        UnitParent(
            start=_sd_start_datetime(parent.startDate),
            end=_sd_end_datetime(parent.endDate),
            value=parent.parentUuid,
        )
        for parent in parents
    )

    timeline = UnitTimeline(
        active=Timeline[Active](intervals=combine_intervals(active_intervals)),
        unit_id=Timeline[UnitId](intervals=combine_intervals(id_intervals)),
        unit_level=Timeline[UnitLevel](intervals=combine_intervals(level_intervals)),
        name=Timeline[UnitName](intervals=combine_intervals(name_intervals)),
        parent=Timeline[UnitParent](intervals=combine_intervals(parent_intervals)),
    )
    logger.debug("SD OU timeline", timeline=timeline)

    return timeline


async def get_employment_timeline(
    sd_client: SDClient,
    inst_id: str,
    cpr: str,
    emp_id: str,
) -> EngagementTimeline:
    logger.info(
        "Get SD employment timeline",
        inst_id=inst_id,
        cpr=cpr,
        emp_id=emp_id,
    )

    r_employment = await asyncio.to_thread(
        sd_client.get_employment_changed,
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
        ),
    )

    person = only(r_employment.Person)
    employment = only(person.Employment) if person is not None else None

    if not employment:
        return EngagementTimeline()

    active_intervals = (
        tuple(
            Active(
                start=_sd_start_datetime(status.ActivationDate),
                end=_sd_end_datetime(status.DeactivationDate),
                value=True,
            )
            for status in employment.EmploymentStatus
            # Only include the periods where the employment is active in SD
            # 0 = hired, but not in pay
            # 1 = hired, in pay
            # 3 = leave
            if status.EmploymentStatusCode in ("0", "1", "3")
        )
        if employment.EmploymentStatus
        else tuple()
    )

    eng_key_intervals = (
        tuple(
            EngagementKey(
                start=_sd_start_datetime(prof.ActivationDate),
                end=_sd_end_datetime(prof.DeactivationDate),
                value=prof.JobPositionIdentifier,
            )
            for prof in employment.Profession
        )
        if employment.Profession
        else tuple()
    )

    eng_name_intervals = (
        tuple(
            EngagementName(
                start=_sd_start_datetime(prof.ActivationDate),
                end=_sd_end_datetime(prof.DeactivationDate),
                value=prof.EmploymentName,
            )
            for prof in employment.Profession
        )
        if employment.Profession
        else tuple()
    )

    eng_unit_intervals = (
        tuple(
            EngagementUnit(
                start=_sd_start_datetime(dep.ActivationDate),
                end=_sd_end_datetime(dep.DeactivationDate),
                value=dep.DepartmentUUIDIdentifier,
            )
            for dep in employment.EmploymentDepartment
        )
        if employment.EmploymentDepartment
        else tuple()
    )

    timeline = EngagementTimeline(
        eng_active=Timeline[Active](intervals=combine_intervals(active_intervals)),
        eng_key=Timeline[EngagementKey](intervals=combine_intervals(eng_key_intervals)),
        eng_name=Timeline[EngagementName](
            intervals=combine_intervals(eng_name_intervals)
        ),
        eng_unit=Timeline[EngagementUnit](
            intervals=combine_intervals(eng_unit_intervals)
        ),
    )
    logger.debug("SD engagement timeline", timeline=timeline)

    return timeline
