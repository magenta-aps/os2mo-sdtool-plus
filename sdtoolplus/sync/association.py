# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from itertools import pairwise
from uuid import UUID

import structlog

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.exceptions import NoValueError
from sdtoolplus.mo.timelines.association import create_association
from sdtoolplus.mo.timelines.association import get_association_filter
from sdtoolplus.mo.timelines.association import (
    get_association_timeline as get_mo_association_timeline,
)
from sdtoolplus.mo.timelines.association import terminate_association
from sdtoolplus.mo.timelines.association import update_association
from sdtoolplus.mo.timelines.common import get_class
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.sd.timelines.employment import (
    get_association_timeline as get_sd_association_timeline,
)

logger = structlog.stdlib.get_logger()


async def _sync_association_intervals(
    gql_client: GraphQLClient,
    person: UUID,
    user_key: str,
    desired_eng_timeline: EngagementTimeline,
    dry_run: bool,
) -> None:
    """
    Make an association to the unit where the person is employed in SD.
    """
    logger.info(
        "Create, update or terminate association in MO",
        person=str(person),
        user_key=user_key,
    )

    # Get the association type (assuming for now that there is only one)
    association_type_uuid = await get_class(
        gql_client=gql_client,
        facet_user_key="association_type",
        # TODO: check if class_user_keys is municipality dependent
        class_user_key="SD-medarbejder",
    )

    sd_association_timeline = get_sd_association_timeline(desired_eng_timeline)
    mo_association_timeline = await get_mo_association_timeline(
        gql_client=gql_client,
        person=person,
        user_key=user_key,
    )

    sd_interval_endpoints = sd_association_timeline.get_interval_endpoints()
    mo_interval_endpoints = mo_association_timeline.get_interval_endpoints()

    endpoints = sorted(sd_interval_endpoints.union(mo_interval_endpoints))
    logger.debug("List of endpoints", endpoints=endpoints)

    for start, end in pairwise(endpoints):
        logger.debug("Processing endpoint pair", start=start, end=end)

        if sd_association_timeline.equal_at(start, mo_association_timeline):
            logger.debug("SD and MO equal")
            continue

        try:
            is_active = sd_association_timeline.association_active.entity_at(
                start
            ).value
        except NoValueError:
            is_active = False  # type: ignore

        if not is_active:
            await terminate_association(
                gql_client=gql_client,
                person=person,
                user_key=user_key,
                start=start,
                end=end,
                dry_run=dry_run,
            )
            continue

        if not sd_association_timeline.has_required_mo_values(start):
            logger.error(
                "Cannot create/update association due to missing timeline data"
            )
            continue

        mo_association = await gql_client.get_association_timeline(
            get_association_filter(
                person=person, user_key=user_key, from_date=None, to_date=None
            )
        )

        if mo_association.objects:
            await update_association(
                gql_client=gql_client,
                person=person,
                user_key=user_key,
                sd_association_timeline=sd_association_timeline,
                start=start,
                end=end,
                association_type=association_type_uuid,
                dry_run=dry_run,
            )
        else:
            await create_association(
                gql_client=gql_client,
                person=person,
                user_key=user_key,
                sd_association_timeline=sd_association_timeline,
                start=start,
                end=end,
                association_type=association_type_uuid,
                dry_run=dry_run,
            )

    logger.info(
        "Finished syncing association in MO",
        person=str(person),
        user_key=user_key,
    )


async def sync_associations(
    gql_client: GraphQLClient,
    settings: SDToolPlusSettings,
    person: UUID,
    user_key: str,
    desired_eng_timeline: EngagementTimeline,
    dry_run: bool,
) -> None:
    """
    Sync associations (state pattern choosing a strategy based on the application
    settings).
    """
    if settings.apply_ny_logic:
        await _sync_association_intervals(
            gql_client=gql_client,
            person=person,
            user_key=user_key,
            desired_eng_timeline=desired_eng_timeline,
            dry_run=dry_run,
        )
