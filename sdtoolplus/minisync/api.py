# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import structlog.stdlib
from fastapi import APIRouter
from fastapi import Response
from starlette.status import HTTP_200_OK

from .. import depends
from ..exceptions import EngagementSyncTemporarilyDisabled
from ..timeline import sync_engagement
from ..timeline import sync_person
from .engagement import move_engagement
from .models import EngagementMovePayload
from .models import EngagementSyncPayload

logger = structlog.stdlib.get_logger()

minisync_router = APIRouter()


@minisync_router.post("/minisync/move-employment", status_code=HTTP_200_OK)
async def engagement_move(
    response: Response,
    gql_client: depends.GraphQLClient,
    payload: EngagementMovePayload,
    dry_run: bool = False,
) -> dict:
    await move_engagement(gql_client, payload, dry_run)
    return {"msg": "success"}


@minisync_router.post("/minisync/sync-person-and-employment", status_code=HTTP_200_OK)
async def sync_person_and_engagement(
    response: Response,
    settings: depends.Settings,
    sd_client: depends.SDClient,
    gql_client: depends.GraphQLClient,
    payload: EngagementSyncPayload,
    dry_run: bool = False,
) -> dict:
    """
    Sync the person with the given CPR from the given institution identifier and the
    EmploymentIdentifier provided in the payload.

    Args:
        gql_client: The GraphQL client

        payload:
            institution_identifier: The SD institution
            cpr: CPR number of the person
            employment_identifier: The SD EmploymentIdentifier

        dry_run: If true, nothing will be written to MO.

    Returns:
        Dictionary with status
    """
    if not settings.recalc_mo_unit_when_sd_employment_moved:
        raise EngagementSyncTemporarilyDisabled()

    # TODO: add integration test when endpoint fully implemented.

    await sync_person(
        sd_client=sd_client,
        gql_client=gql_client,
        institution_identifier=payload.institution_identifier,
        cpr=payload.cpr,
        dry_run=dry_run,
    )

    await sync_engagement(
        sd_client=sd_client,
        gql_client=gql_client,
        institution_identifier=payload.institution_identifier,
        cpr=payload.cpr,
        employment_identifier=payload.employment_identifier,
        settings=settings,
        dry_run=dry_run,
    )

    return {"msg": "success"}
