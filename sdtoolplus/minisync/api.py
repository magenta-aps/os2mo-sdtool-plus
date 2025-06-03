# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import structlog.stdlib
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Response
from starlette.status import HTTP_200_OK
from starlette.status import HTTP_404_NOT_FOUND
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from .. import depends
from ..exceptions import DepartmentTimelineNotFound
from ..exceptions import EngagementNotActiveError
from ..exceptions import EngagementNotFoundError
from ..exceptions import EngagementSyncTemporarilyDisabled
from ..exceptions import PersonNotFoundError
from ..timeline import sync_engagement
from ..timeline import sync_person
from .engagement import move_engagement
from .models import EngagementMovePayload
from .models import EngagementSyncPayload

logger = structlog.stdlib.get_logger()

minisync_router = APIRouter(dependencies=[Depends(depends.request_id)])


@minisync_router.post("/minisync/move-employment", status_code=HTTP_200_OK)
async def engagement_move(
    response: Response,
    gql_client: depends.GraphQLClient,
    payload: EngagementMovePayload,
    dry_run: bool = False,
) -> dict:
    try:
        await move_engagement(gql_client, payload, dry_run)
    except PersonNotFoundError:
        response.status_code = HTTP_404_NOT_FOUND
        return {"msg": "The person could not be found i MO"}
    except EngagementNotFoundError:
        response.status_code = HTTP_404_NOT_FOUND
        return {"msg": "The engagement could not be found i MO"}
    except EngagementNotActiveError:
        response.status_code = HTTP_500_INTERNAL_SERVER_ERROR
        return {"msg": "The engagement is not active in the entire move interval"}
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

    try:
        await sync_engagement(
            sd_client=sd_client,
            gql_client=gql_client,
            institution_identifier=payload.institution_identifier,
            cpr=payload.cpr,
            employment_identifier=payload.employment_identifier,
            settings=settings,
            dry_run=dry_run,
        )
    except DepartmentTimelineNotFound:
        logger.error(
            "Empty department timeline for employment found in SD",
            institution_identifier=payload.institution_identifier,
            cpr=payload.cpr,
            employment_identifier=payload.employment_identifier,
        )
        response.status_code = HTTP_422_UNPROCESSABLE_ENTITY
        return {"msg": "Empty department timeline for employment found in SD"}

    return {"msg": "success"}
