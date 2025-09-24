# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog.stdlib
from fastramqpi.context import Context
from more_itertools import last
from sdclient.client import SDClient
from sdclient.requests import GetInstitutionRequest
from sdclient.responses import GetInstitutionResponse

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.mo.timelines.org_unit import get_ou_timeline
from sdtoolplus.models import POSITIVE_INFINITY
from sdtoolplus.models import Active
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitId
from sdtoolplus.models import UnitLevel
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitParent
from sdtoolplus.models import UnitTimeline
from sdtoolplus.timeline import sync_ou_intervals

logger = structlog.stdlib.get_logger()


@asynccontextmanager
async def ensure_sd_institution_units(
    settings: SDToolPlusSettings, sd_client: SDClient, context: Context
) -> AsyncIterator[None]:
    logger.info("Ensuring SD institution units...")

    assert settings.mo_subtree_paths_for_root is not None

    graphql_client: GraphQLClient = context["graphql_client"]

    for (
        institution_identifier,
        subtree_path,
    ) in settings.mo_subtree_paths_for_root.items():
        *path, mo_unit_uuid = subtree_path

        institution: GetInstitutionResponse = await asyncio.to_thread(
            sd_client.get_institution,
            GetInstitutionRequest(
                RegionIdentifier=settings.sd_region_identifier,
                InstitutionIdentifier=institution_identifier,
                UUIDIndicator=True,
            ),
        )
        assert institution.Region.Institution.InstitutionUUIDIdentifier is not None

        sd_timeline = UnitTimeline(
            active=Timeline[Active](
                intervals=(
                    Active(
                        start=settings.min_mo_datetime,
                        end=POSITIVE_INFINITY,
                        value=True,
                    ),
                )
            ),
            name=Timeline[UnitName](
                intervals=(
                    UnitName(
                        start=settings.min_mo_datetime,
                        end=POSITIVE_INFINITY,
                        value=settings.sd_to_mo_ou_name_map.get(
                            institution.Region.Institution.InstitutionUUIDIdentifier,
                            institution.Region.Institution.InstitutionName,
                        ),
                    ),
                )
            ),
            unit_id=Timeline[UnitId](
                intervals=(
                    UnitId(
                        start=settings.min_mo_datetime,
                        end=POSITIVE_INFINITY,
                        value=institution_identifier,
                    ),
                )
            ),
            unit_level=Timeline[UnitLevel](
                intervals=(
                    UnitLevel(
                        start=settings.min_mo_datetime,
                        end=POSITIVE_INFINITY,
                        value="TOP",
                    ),
                )
            ),
            parent=Timeline[UnitParent](
                intervals=(
                    UnitParent(
                        start=settings.min_mo_datetime,
                        end=POSITIVE_INFINITY,
                        value=last(path, default=None),
                    ),
                )
            ),
        )

        mo_timeline = await get_ou_timeline(
            gql_client=graphql_client,
            unit_uuid=mo_unit_uuid,
        )

        await sync_ou_intervals(
            gql_client=graphql_client,
            settings=settings,
            org_unit=mo_unit_uuid,
            desired_unit_timeline=sd_timeline,
            mo_unit_timeline=mo_timeline,
            institution_identifier=institution_identifier,
            priority=10000,
            dry_run=False,
        )

    logger.info("Done ensuring SD institution units...")

    yield
