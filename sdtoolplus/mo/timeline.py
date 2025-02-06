# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime

from more_itertools import first
from more_itertools import one

from sdtoolplus.depends import GraphQLClient
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import Active
from sdtoolplus.models import combine_intervals
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitTimeline


async def get_ou_timeline(
    gql_client: GraphQLClient,
    unit_uuid: OrgUnitUUID,
) -> UnitTimeline:
    gql_timelime = await gql_client.get_org_unit_timeline([unit_uuid])
    objects = gql_timelime.objects

    if not objects:
        return UnitTimeline(
            active=Timeline[Active](intervals=tuple()),
            name=Timeline[UnitName](intervals=tuple()),
        )

    validities = one(objects).validities
    tz = first(validities).validity.from_.tzinfo
    assert tz is not None

    activity_intervals = tuple(
        Active(
            start=obj.validity.from_,
            end=obj.validity.to
            if obj.validity.to is not None
            else datetime.max.replace(tzinfo=tz),
            value=True,
        )
        for obj in validities
    )
    activity_intervals = combine_intervals(activity_intervals)

    name_intervals = tuple(
        UnitName(
            start=obj.validity.from_,
            end=obj.validity.to
            if obj.validity.to is not None
            else datetime.max.replace(tzinfo=tz),
            value=obj.name,
        )
        for obj in validities
    )
    name_intervals = combine_intervals(name_intervals)

    return UnitTimeline(
        active=Timeline[Active](intervals=activity_intervals),
        name=Timeline[UnitName](intervals=name_intervals),
    )
