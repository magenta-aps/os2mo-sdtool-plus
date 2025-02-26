# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta

import structlog
from sdclient.client import SDClient
from sdclient.requests import GetDepartmentRequest

from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import Active
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitId
from sdtoolplus.models import UnitLevel
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitTimeline
from sdtoolplus.models import combine_intervals
from sdtoolplus.sd.tree import ASSUMED_SD_TIMEZONE

logger = structlog.stdlib.get_logger()


def _sd_start_datetime(d: date) -> datetime:
    return datetime.combine(d, time.min, ASSUMED_SD_TIMEZONE)


def _sd_end_datetime(d: date) -> datetime:
    if d == date.max:
        return datetime.max.replace(tzinfo=ASSUMED_SD_TIMEZONE)
    # We have to add one day to the SD end date when converting to a timeline end
    # datetime, since we are working with a continuous timeline. E.g. the SD end date
    # 1999-12-31 states that the effective end datetime is 1999-12-31T23:59:59.999999,
    # which (due to the continuous timeline) translates into the end datetime
    # t_end = 2000-01-01T00:00:00.000000 in the half-open interval [t_start, t_end)
    return datetime.combine(d, time.min, ASSUMED_SD_TIMEZONE) + timedelta(days=1)


def get_department_timeline(
    sd_client: SDClient,
    inst_id: str,
    unit_uuid: OrgUnitUUID,
) -> UnitTimeline:
    logger.info("Get SD department timeline", inst_id=inst_id, unit_uuid=str(unit_uuid))

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

    timeline = UnitTimeline(
        active=Timeline[Active](intervals=combine_intervals(active_intervals)),
        unit_id=Timeline[UnitId](intervals=combine_intervals(id_intervals)),
        unit_level=Timeline[UnitLevel](intervals=combine_intervals(level_intervals)),
        name=Timeline[UnitName](intervals=combine_intervals(name_intervals)),
    )
    logger.debug("SD OU timeline", timeline=timeline)

    return timeline
