# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta

from pydantic import BaseModel
from sdclient.client import SDClient
from sdclient.requests import GetDepartmentRequest

from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import Active
from sdtoolplus.models import combine_intervals
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitName
from sdtoolplus.sd.tree import ASSUMED_SD_TIMEZONE


class DepartmentTimeline(BaseModel):
    active: Timeline[Active]
    name: Timeline[UnitName]


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
) -> DepartmentTimeline:
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

    return DepartmentTimeline(
        active=Timeline[Active](intervals=active_intervals),
        name=Timeline[UnitName](intervals=name_intervals),
    )
