# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import asyncio
from datetime import date
from itertools import pairwise

import structlog
from more_itertools import collapse
from more_itertools import first
from more_itertools import only
from sdclient.client import SDClient
from sdclient.exceptions import SDParentNotFound
from sdclient.exceptions import SDRootElementNotFound
from sdclient.requests import GetDepartmentRequest
from sdclient.responses import GetDepartmentResponse

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import Active
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitId
from sdtoolplus.models import UnitLevel
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitParent
from sdtoolplus.models import UnitPhoneNumber
from sdtoolplus.models import UnitPNumber
from sdtoolplus.models import UnitPostalAddress
from sdtoolplus.models import UnitTimeline
from sdtoolplus.models import combine_intervals
from sdtoolplus.sd.timelines.common import sd_end_to_timeline_end
from sdtoolplus.sd.timelines.common import sd_start_to_timeline_start

logger = structlog.stdlib.get_logger()


def condense_multiple_parents_to_unknown_unit(
    parent_intervals: tuple[UnitParent, ...],
    unknown_unit: OrgUnitUUID,
) -> tuple[UnitParent, ...]:
    """
    In some cases we get multiple parents back for certain intervals, e.g. SD parent
    history data looking like this:

    $ curl -u <user>:<pwd> "https://service.sd.dk/api-gateway/organization/public/api/v1/organizations/uuids/e9ba3e1a-4e79-4dda-b159-fc689f792115/department-parent-history" | jq
    [
      {
        "parentUuid": "52c2032b-f654-438c-9ce3-2e138ca7bdf8",
        "startDate": "2006-09-01",
        "endDate": "2012-12-31"
      },
      {
        "parentUuid": "72c2b7df-6982-4a00-9600-000001300001",
        "startDate": "2006-09-01",
        "endDate": "2013-06-30"
      }
    ]

    This function replaces the multiple parents with the "unknown" unit in the
    overlapping intervals.

    Args:
        parent_intervals: the department parent intervals as-is in SD
        unknown_unit: UUID of the unknown unit

    Returns:
        A tuple of UnitParent intervals where the "unknown" unit is used as a
        substitute for the multiple parents in the overlapping intervals.
    """
    endpoints = sorted(set(collapse((i.start, i.end) for i in parent_intervals)))
    condensed_intervals = []
    for start, end in pairwise(endpoints):
        try:
            parent_in_endpoint_interval = only(
                interval
                for interval in parent_intervals
                if interval.start < end and interval.end > start
            )
        except ValueError:
            unit_parent = UnitParent(start=start, end=end, value=unknown_unit)
            condensed_intervals.append(unit_parent)
        else:
            if parent_in_endpoint_interval is not None:
                unit_parent = UnitParent(
                    start=start, end=end, value=parent_in_endpoint_interval.value
                )
                condensed_intervals.append(unit_parent)

    return combine_intervals(tuple(condensed_intervals))


async def get_department(
    sd_client: SDClient,
    institution_identifier: str,
    unit_uuid: OrgUnitUUID,
) -> GetDepartmentResponse | None:
    try:
        department = await asyncio.to_thread(
            sd_client.get_department,
            GetDepartmentRequest(
                InstitutionIdentifier=institution_identifier,
                DepartmentUUIDIdentifier=unit_uuid,
                ActivationDate=date.min,
                DeactivationDate=date.max,
                DepartmentNameIndicator=True,
                PostalAddressIndicator=True,
                ProductionUnitIndicator=True,
                ContactInformationIndicator=True,
                UUIDIndicator=True,
            ),
        )
        if not department.Department:
            logger.warning("Empty department response from SD!")
            return None
        return department
    except SDRootElementNotFound as error:
        logger.error("Error getting department from SD", error=error)
        return None


async def get_department_timeline(
    department: GetDepartmentResponse | None,
    sd_client: SDClient,
    inst_id: str,
    unit_uuid: OrgUnitUUID,
    settings: SDToolPlusSettings,
) -> UnitTimeline:
    logger.info("Get SD department timeline", inst_id=inst_id, unit_uuid=str(unit_uuid))

    if department is None:
        return UnitTimeline()

    try:
        parents = await asyncio.to_thread(
            sd_client.get_department_parent_history, unit_uuid
        )
    except SDParentNotFound as error:
        logger.warning("Error getting department parent(s) from SD", error=error)
        return UnitTimeline()

    active_intervals = tuple(
        Active(
            start=sd_start_to_timeline_start(dep.ActivationDate),
            end=sd_end_to_timeline_end(dep.DeactivationDate),
            value=True,
        )
        for dep in department.Department
    )

    id_intervals = tuple(
        UnitId(
            start=sd_start_to_timeline_start(dep.ActivationDate),
            end=sd_end_to_timeline_end(dep.DeactivationDate),
            value=dep.DepartmentIdentifier,
        )
        for dep in department.Department
    )

    level_intervals = tuple(
        UnitLevel(
            start=sd_start_to_timeline_start(dep.ActivationDate),
            end=sd_end_to_timeline_end(dep.DeactivationDate),
            value=dep.DepartmentLevelIdentifier,
        )
        for dep in department.Department
    )

    name_intervals = tuple(
        UnitName(
            start=sd_start_to_timeline_start(dep.ActivationDate),
            end=sd_end_to_timeline_end(dep.DeactivationDate),
            value=dep.DepartmentName,
        )
        for dep in department.Department
    )

    parent_intervals = tuple(
        UnitParent(
            start=sd_start_to_timeline_start(parent.startDate),
            end=sd_end_to_timeline_end(parent.endDate),
            value=settings.sd_institution_to_mo_root_ou_uuid_map.get(
                parent.parentUuid, parent.parentUuid
            ),
        )
        for parent in parents
    )
    # Introduce proper state/strategy pattern if more variability is needed later
    if settings.condense_multiple_ou_parents_to_unknown_unit:
        assert settings.unknown_unit is not None
        parent_intervals = condense_multiple_parents_to_unknown_unit(
            unknown_unit=settings.unknown_unit, parent_intervals=parent_intervals
        )

    timeline = UnitTimeline(
        active=Timeline[Active](intervals=combine_intervals(active_intervals)),
        unit_id=Timeline[UnitId](intervals=combine_intervals(id_intervals)),
        unit_level=Timeline[UnitLevel](intervals=combine_intervals(level_intervals)),
        name=Timeline[UnitName](intervals=combine_intervals(name_intervals)),
        parent=Timeline[UnitParent](intervals=combine_intervals(parent_intervals)),
    )
    logger.info("SD OU timeline", timeline=timeline.dict())

    return timeline


def get_pnumber_timeline(department: GetDepartmentResponse) -> Timeline[UnitPNumber]:
    timeline = Timeline[UnitPNumber](
        intervals=combine_intervals(
            tuple(
                UnitPNumber(
                    start=sd_start_to_timeline_start(dep.ActivationDate),
                    end=sd_end_to_timeline_end(dep.DeactivationDate),
                    value=dep.ProductionUnitIdentifier,
                )
                for dep in department.Department
                if dep.ProductionUnitIdentifier is not None
                # P-number zero is not allowed by MO
                and dep.ProductionUnitIdentifier != 0
            )
        )
    )
    logger.info("SD P-number timeline", timeline=timeline.dict())

    return timeline


def get_postal_address_timeline(
    department: GetDepartmentResponse,
) -> Timeline[UnitPostalAddress]:
    timeline = Timeline[UnitPostalAddress](
        intervals=combine_intervals(
            tuple(
                UnitPostalAddress(
                    start=sd_start_to_timeline_start(dep.ActivationDate),
                    end=sd_end_to_timeline_end(dep.DeactivationDate),
                    value=f"{dep.PostalAddress.StandardAddressIdentifier}, {dep.PostalAddress.PostalCode}, {dep.PostalAddress.DistrictName}",
                )
                for dep in department.Department
                if dep.PostalAddress is not None
                and dep.PostalAddress.StandardAddressIdentifier is not None
                and dep.PostalAddress.PostalCode is not None
                and dep.PostalAddress.DistrictName is not None
            )
        )
    )
    logger.info("SD postal address timeline", timeline=timeline.dict())

    return timeline


def get_phone_number_timeline(
    department: GetDepartmentResponse,
) -> Timeline[UnitPhoneNumber]:
    # According to the spec we will always only sync the *first* phone number in the
    # SD response (unless it equals "00000000" which means that it has not been set)
    timeline = Timeline[UnitPhoneNumber](
        intervals=combine_intervals(
            tuple(
                UnitPhoneNumber(
                    start=sd_start_to_timeline_start(dep.ActivationDate),
                    end=sd_end_to_timeline_end(dep.DeactivationDate),
                    value=first(dep.ContactInformation.TelephoneNumberIdentifier),
                )
                for dep in department.Department
                if dep.ContactInformation is not None
                and dep.ContactInformation.TelephoneNumberIdentifier is not None
                and first(dep.ContactInformation.TelephoneNumberIdentifier)
                != "00000000"
            )
        )
    )
    logger.info("SD phone number timeline", timeline=timeline.dict())

    return timeline
