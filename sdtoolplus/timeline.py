# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import asyncio
from datetime import date
from datetime import datetime
from itertools import chain
from itertools import pairwise
from typing import cast
from uuid import UUID

import structlog
from more_itertools import collapse
from more_itertools import one
from more_itertools import only
from sdclient.client import SDClient
from sdclient.requests import GetEmploymentChangedRequest

from sdtoolplus.autogenerated_graphql_client import ClassFilter
from sdtoolplus.autogenerated_graphql_client import EmployeeFilter
from sdtoolplus.autogenerated_graphql_client import LeaveFilter
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.exceptions import PersonNotFoundError
from sdtoolplus.mo.timeline import create_engagement
from sdtoolplus.mo.timeline import create_leave
from sdtoolplus.mo.timeline import create_ou
from sdtoolplus.mo.timeline import get_engagement_timeline
from sdtoolplus.mo.timeline import get_engagement_types
from sdtoolplus.mo.timeline import terminate_engagement
from sdtoolplus.mo.timeline import terminate_leave
from sdtoolplus.mo.timeline import terminate_ou
from sdtoolplus.mo.timeline import update_engagement
from sdtoolplus.mo.timeline import update_leave
from sdtoolplus.mo.timeline import update_ou
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import EngagementSyncPayload
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.models import Interval
from sdtoolplus.models import LeaveTimeline
from sdtoolplus.models import UnitTimeline
from sdtoolplus.sd.timeline import get_employment_timeline

from .mo.timeline import get_leave_timeline as get_mo_leave_timeline
from .sd.timeline import get_leave_timeline as get_sd_leave_timeline

logger = structlog.stdlib.get_logger()


# TODO: move function to UnitTimeline class
def _get_ou_interval_endpoints(ou_timeline: UnitTimeline) -> set[datetime]:
    return set(
        collapse(
            set(
                (i.start, i.end)
                for i in chain(
                    cast(tuple[Interval, ...], ou_timeline.active.intervals),
                    cast(tuple[Interval, ...], ou_timeline.name.intervals),
                    cast(tuple[Interval, ...], ou_timeline.unit_id.intervals),
                    cast(tuple[Interval, ...], ou_timeline.unit_level.intervals),
                    cast(tuple[Interval, ...], ou_timeline.parent.intervals),
                )
            )
        )
    )


# TODO: replace this function with a proper strategy pattern when needed
def prefix_user_key_with_inst_id(user_key: str, inst_id: str) -> str:
    return f"{inst_id}-{user_key}"


async def _sync_eng_intervals(
    gql_client: GraphQLClient,
    person: UUID,
    # TODO: we need to change the arguments to this function later in order to
    #       to handle other triggering mechanisms
    payload: EngagementSyncPayload,
    sd_eng_timeline: EngagementTimeline,
    mo_eng_timeline: EngagementTimeline,
    dry_run: bool,
) -> None:
    user_key = prefix_user_key_with_inst_id(
        payload.employment_identifier, payload.institution_identifier
    )

    logger.info(
        "Create, update or terminate engagement in MO",
        person=str(person),
        user_key=user_key,
    )

    # Get the engagement types
    eng_types = await get_engagement_types(gql_client)

    sd_interval_endpoints = sd_eng_timeline.get_interval_endpoints()
    mo_interval_endpoints = mo_eng_timeline.get_interval_endpoints()

    endpoints = list(sd_interval_endpoints.union(mo_interval_endpoints))
    endpoints.sort()
    logger.debug("List of endpoints", endpoints=endpoints)

    for start, end in pairwise(endpoints):
        logger.debug("Processing endpoint pair", start=start, end=end)
        if sd_eng_timeline.equal_at(start, mo_eng_timeline):
            logger.debug("SD and MO equal")
            continue
        elif sd_eng_timeline.has_value(start):
            logger.debug("SD value available")
            mo_eng = await gql_client.get_engagement_timeline(
                person=person, user_key=user_key, from_date=None, to_date=None
            )
            if mo_eng.objects:
                await update_engagement(
                    gql_client=gql_client,
                    person=person,
                    user_key=user_key,
                    start=start,
                    end=end,
                    sd_eng_timeline=sd_eng_timeline,
                    eng_types=eng_types,
                )
            else:
                await create_engagement(
                    gql_client=gql_client,
                    person=person,
                    user_key=user_key,
                    start=start,
                    end=end,
                    sd_eng_timeline=sd_eng_timeline,
                    eng_types=eng_types,
                )
        else:
            await terminate_engagement(
                gql_client=gql_client,
                person=person,
                user_key=user_key,
                start=start,
                end=end,
            )


async def _sync_leave_intervals(
    gql_client: GraphQLClient,
    person: UUID,
    # TODO: we need to change the arguments to this function later in order to
    #       to handle other triggering mechanisms
    payload: EngagementSyncPayload,
    sd_leave_timeline: LeaveTimeline,
    mo_leave_timeline: LeaveTimeline,
    dry_run: bool,
) -> None:
    user_key = prefix_user_key_with_inst_id(
        payload.employment_identifier, payload.institution_identifier
    )

    logger.info(
        "Create, update or terminate leave in MO",
        person=str(person),
        user_key=user_key,
    )

    # Get the leave type (assuming for now that there is only one)
    r_leave_type = await gql_client.get_class(ClassFilter(user_keys=["Orlov"]))
    leave_type = one(r_leave_type.objects).uuid

    # Get the corresponding engagement
    mo_eng = await gql_client.get_engagement_timeline(
        person=person, user_key=user_key, from_date=None, to_date=None
    )
    eng_uuid = one(mo_eng.objects).uuid

    sd_interval_endpoints = sd_leave_timeline.get_interval_endpoints()
    mo_interval_endpoints = mo_leave_timeline.get_interval_endpoints()

    endpoints = list(sd_interval_endpoints.union(mo_interval_endpoints))
    endpoints.sort()
    logger.debug("List of endpoints", endpoints=endpoints)

    for start, end in pairwise(endpoints):
        logger.debug("Processing endpoint pair", start=start, end=end)
        if sd_leave_timeline.equal_at(start, mo_leave_timeline):
            logger.debug("SD and MO equal")
            continue
        elif sd_leave_timeline.has_value(start):
            logger.debug("SD value available")
            mo_leave = await gql_client.get_leave(
                LeaveFilter(
                    employee=EmployeeFilter(uuids=[person]),
                    user_keys=[user_key],
                    from_date=None,
                    to_date=None,
                )
            )
            if mo_leave.objects:
                await update_leave(
                    gql_client=gql_client,
                    person=person,
                    eng_uuid=eng_uuid,
                    user_key=user_key,
                    start=start,
                    end=end,
                    sd_leave_timeline=sd_leave_timeline,
                    leave_type=leave_type,
                    dry_run=dry_run,
                )
            else:
                await create_leave(
                    gql_client=gql_client,
                    person=person,
                    eng_uuid=eng_uuid,
                    user_key=user_key,
                    start=start,
                    end=end,
                    sd_leave_timeline=sd_leave_timeline,
                    leave_type=leave_type,
                    dry_run=dry_run,
                )
        else:
            await terminate_leave(
                gql_client=gql_client,
                person=person,
                user_key=user_key,
                start=start,
                end=end,
                dry_run=dry_run,
            )


async def _sync_ou_intervals(
    gql_client: GraphQLClient,
    org_unit: OrgUnitUUID,
    org_unit_type_user_key: str,
    sd_unit_timeline: UnitTimeline,
    mo_unit_timeline: UnitTimeline,
    dry_run: bool,
) -> None:
    logger.info("Create, update or terminate OU in MO", org_unit=str(org_unit))

    sd_interval_endpoints = _get_ou_interval_endpoints(sd_unit_timeline)
    mo_interval_endpoints = _get_ou_interval_endpoints(mo_unit_timeline)

    endpoints = list(sd_interval_endpoints.union(mo_interval_endpoints))
    endpoints.sort()
    logger.debug("List of endpoints", endpoints=endpoints)

    for start, end in pairwise(endpoints):
        logger.debug("Processing endpoint pair", start=start, end=end)
        if sd_unit_timeline.equal_at(start, mo_unit_timeline):
            logger.debug("SD and MO equal")
            continue
        elif sd_unit_timeline.has_value(start):
            ou = await gql_client.get_org_unit_timeline(
                unit_uuid=org_unit, from_date=None, to_date=None
            )
            if ou.objects:
                await update_ou(
                    gql_client=gql_client,
                    org_unit=org_unit,
                    start=start,
                    end=end,
                    sd_unit_timeline=sd_unit_timeline,
                    org_unit_type_user_key=org_unit_type_user_key,
                    dry_run=dry_run,
                )
            else:
                await create_ou(
                    gql_client=gql_client,
                    org_unit=org_unit,
                    start=start,
                    end=end,
                    sd_unit_timeline=sd_unit_timeline,
                    org_unit_type_user_key=org_unit_type_user_key,
                    dry_run=dry_run,
                )
        else:
            await terminate_ou(
                gql_client=gql_client,
                org_unit=org_unit,
                start=start,
                end=end,
                dry_run=dry_run,
            )


async def sync_engagement(
    sd_client: SDClient,
    gql_client: GraphQLClient,
    payload: EngagementSyncPayload,
    dry_run: bool = False,
) -> None:
    """
    Sync the entire engagement and leave timelines for the given CPR and
    SD EmploymentIdentifier (corresponding to the MO engagement user_key).

    Args:
        gql_client: The GraphQL client
        payload: The engagement sync payload
        dry_run: If true, nothing will be written to MO.
    """

    logger.info(
        "Sync engagement timeline",
        inst_id=payload.institution_identifier,
        cpr=payload.cpr,
        emp_id=payload.employment_identifier,
        dry_run=dry_run,
    )

    r_employment = await asyncio.to_thread(
        sd_client.get_employment_changed,
        GetEmploymentChangedRequest(
            InstitutionIdentifier=payload.institution_identifier,
            PersonCivilRegistrationIdentifier=payload.cpr,
            EmploymentIdentifier=payload.employment_identifier,
            ActivationDate=date.min,
            DeactivationDate=date.max,
            DepartmentIndicator=True,
            EmploymentStatusIndicator=True,
            ProfessionIndicator=True,
            WorkingTimeIndicator=True,
            UUIDIndicator=True,
        ),
    )

    sd_eng_timeline = await get_employment_timeline(r_employment)

    # TODO: introduce OU strategy

    # Get the person
    r_person = await gql_client.get_person(payload.cpr)
    person = only(r_person.objects)
    if person is None:
        # TODO: Return proper HTTP 5xx error message if this happens
        raise PersonNotFoundError("Could not find person in MO")

    mo_eng_timeline = await get_engagement_timeline(
        gql_client=gql_client,
        person=person.uuid,
        user_key=prefix_user_key_with_inst_id(
            payload.employment_identifier, payload.institution_identifier
        ),
    )

    await _sync_eng_intervals(
        gql_client=gql_client,
        person=person.uuid,
        payload=payload,
        sd_eng_timeline=sd_eng_timeline,
        mo_eng_timeline=mo_eng_timeline,
        dry_run=dry_run,
    )

    sd_leave_timeline = await get_sd_leave_timeline(r_employment)
    mo_leave_timeline = await get_mo_leave_timeline(
        gql_client=gql_client,
        person=person.uuid,
        user_key=prefix_user_key_with_inst_id(
            payload.employment_identifier, payload.institution_identifier
        ),
    )

    await _sync_leave_intervals(
        gql_client=gql_client,
        person=person.uuid,
        payload=payload,
        sd_leave_timeline=sd_leave_timeline,
        mo_leave_timeline=mo_leave_timeline,
        dry_run=dry_run,
    )
