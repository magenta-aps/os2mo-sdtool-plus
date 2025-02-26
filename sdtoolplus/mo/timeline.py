# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from datetime import timedelta
from datetime import tzinfo

import structlog
from more_itertools import first
from more_itertools import one

from sdtoolplus.depends import GraphQLClient
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import Active
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitTimeline
from sdtoolplus.models import combine_intervals

logger = structlog.stdlib.get_logger()


def _mo_end_datetime(d: datetime | None, tz: tzinfo) -> datetime:
    return d + timedelta(days=1) if d is not None else datetime.max.replace(tzinfo=tz)


async def get_ou_timeline(
    gql_client: GraphQLClient,
    unit_uuid: OrgUnitUUID,
) -> UnitTimeline:
    logger.info("Get MO org unit timeline", unit_uuid=str(unit_uuid))

    gql_timelime = await gql_client.get_org_unit_timeline(unit_uuid)
    objects = gql_timelime.objects

    if not objects:
        return UnitTimeline(
            active=Timeline[Active](),
            name=Timeline[UnitName](),
        )

    validities = one(objects).validities
    tz = first(validities).validity.from_.tzinfo
    assert tz is not None

    activity_intervals = tuple(
        Active(
            start=obj.validity.from_,
            # TODO (#61435): MOs GraphQL subtracts one day from the validity end dates
            # when reading, compared to what was written.
            end=_mo_end_datetime(obj.validity.to, tz),
            value=True,
        )
        for obj in validities
    )

    name_intervals = tuple(
        UnitName(
            start=obj.validity.from_,
            end=_mo_end_datetime(obj.validity.to, tz),
            value=obj.name,
        )
        for obj in validities
    )

    timeline = UnitTimeline(
        active=Timeline[Active](intervals=combine_intervals(activity_intervals)),
        name=Timeline[UnitName](intervals=combine_intervals(name_intervals)),
    )
    logger.debug("MO OU timeline", timeline=timeline)

    return timeline
