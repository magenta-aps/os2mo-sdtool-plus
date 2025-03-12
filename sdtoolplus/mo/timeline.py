# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from datetime import timedelta

import structlog
from more_itertools import one

from sdtoolplus.autogenerated_graphql_client import OrganisationUnitCreateInput
from sdtoolplus.autogenerated_graphql_client import OrganisationUnitTerminateInput
from sdtoolplus.autogenerated_graphql_client import OrganisationUnitUpdateInput
from sdtoolplus.autogenerated_graphql_client import RAValidityInput
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.mo_org_unit_importer import OrgUnitLevelUUID
from sdtoolplus.mo_org_unit_importer import OrgUnitTypeUUID
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import POSITIVE_INFINITY
from sdtoolplus.models import Active
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitId
from sdtoolplus.models import UnitLevel
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitTimeline
from sdtoolplus.models import combine_intervals

logger = structlog.stdlib.get_logger()


def _mo_end_datetime(d: datetime | None) -> datetime:
    return d + timedelta(days=1) if d is not None else POSITIVE_INFINITY


def _get_mo_validity(start: datetime, end: datetime) -> RAValidityInput:
    mo_end: datetime | None = end
    assert mo_end is not None
    if mo_end.replace(tzinfo=None) == datetime.max:
        mo_end = None
    else:
        mo_end = mo_end - timedelta(days=1)  # Subtract one day due to MO
    return RAValidityInput(from_=start, to=mo_end)


async def _get_ou_type(
    gql_client: GraphQLClient,
    org_unit_type_user_key: str,
) -> OrgUnitTypeUUID:
    ou_type_classes = await gql_client.get_facet_class(
        "org_unit_type", org_unit_type_user_key
    )

    current = one(ou_type_classes.objects).current
    assert current is not None
    return current.uuid


async def _get_ou_level(
    gql_client: GraphQLClient,
    org_unit_level_user_key: str,
) -> OrgUnitLevelUUID:
    ou_level_classes = await gql_client.get_facet_class(
        "org_unit_level", org_unit_level_user_key
    )

    current = one(ou_level_classes.objects).current
    assert current is not None
    return current.uuid


async def get_ou_timeline(
    gql_client: GraphQLClient,
    unit_uuid: OrgUnitUUID,
) -> UnitTimeline:
    logger.info("Get MO org unit timeline", unit_uuid=str(unit_uuid))

    gql_timelime = await gql_client.get_org_unit_timeline(
        unit_uuid=unit_uuid, from_date=None, to_date=None
    )
    objects = gql_timelime.objects

    if not objects:
        return UnitTimeline(
            active=Timeline[Active](),
            name=Timeline[UnitName](),
            unit_id=Timeline[UnitId](),
            unit_level=Timeline[UnitLevel](),
        )

    validities = one(objects).validities

    activity_intervals = tuple(
        Active(
            start=obj.validity.from_,
            # TODO (#61435): MOs GraphQL subtracts one day from the validity end dates
            # when reading, compared to what was written.
            end=_mo_end_datetime(obj.validity.to),
            value=True,
        )
        for obj in validities
    )

    id_intervals = tuple(
        UnitId(
            start=obj.validity.from_,
            end=_mo_end_datetime(obj.validity.to),
            value=obj.user_key,
        )
        for obj in validities
    )

    level_intervals = tuple(
        UnitLevel(
            start=obj.validity.from_,
            end=_mo_end_datetime(obj.validity.to),
            value=obj.org_unit_level.name if obj.org_unit_level is not None else "",
        )
        for obj in validities
    )

    name_intervals = tuple(
        UnitName(
            start=obj.validity.from_,
            end=_mo_end_datetime(obj.validity.to),
            value=obj.name,
        )
        for obj in validities
    )

    timeline = UnitTimeline(
        active=Timeline[Active](intervals=combine_intervals(activity_intervals)),
        name=Timeline[UnitName](intervals=combine_intervals(name_intervals)),
        unit_id=Timeline[UnitId](intervals=combine_intervals(id_intervals)),
        unit_level=Timeline[UnitLevel](intervals=combine_intervals(level_intervals)),
    )
    logger.debug("MO OU timeline", timeline=timeline)

    return timeline


async def create_ou(
    gql_client: GraphQLClient,
    org_unit: OrgUnitUUID,
    start: datetime,
    end: datetime,
    sd_unit_timeline: UnitTimeline,
    org_unit_type_user_key: str,
) -> None:
    logger.info("Creating OU", uuid=str(org_unit))
    logger.debug("Creating OU", start=start, end=end, sd_unit_timeline=sd_unit_timeline)

    # Get the OU type UUID
    ou_type_uuid = await _get_ou_type(gql_client, org_unit_type_user_key)

    # Get the OU level UUID
    unit_level = sd_unit_timeline.unit_level.entity_at(start)
    ou_level_uuid = await _get_ou_level(gql_client, unit_level.value)  # type: ignore

    await gql_client.create_org_unit(
        OrganisationUnitCreateInput(
            uuid=org_unit,
            # TODO: move _get_mo_validity to this module
            validity=_get_mo_validity(start, end),
            name=sd_unit_timeline.name.entity_at(start).value,
            user_key=sd_unit_timeline.unit_id.entity_at(start).value,
            # TODO: remove hard-coded value
            parent=OrgUnitUUID("12121212-1212-1212-1212-121212121212"),
            org_unit_type=ou_type_uuid,
            org_unit_level=ou_level_uuid,
        )
    )


async def update_ou(
    gql_client: GraphQLClient,
    org_unit: OrgUnitUUID,
    start: datetime,
    end: datetime,
    sd_unit_timeline: UnitTimeline,
    org_unit_type_user_key: str,
) -> None:
    logger.info("Updating OU", uuid=str(org_unit))
    logger.debug("Updating OU", start=start, end=end, sd_unit_timeline=sd_unit_timeline)

    mo_validity = _get_mo_validity(start, end)
    # TODO: refactor get_org_unit_timeline to take a RAValidityInput object instead of
    # start and end dates
    ou = await gql_client.get_org_unit_timeline(
        org_unit, mo_validity.from_, mo_validity.to
    )

    # Get the OU type UUID
    ou_type_uuid = await _get_ou_type(gql_client, org_unit_type_user_key)

    # Get the OU level UUID
    unit_level = sd_unit_timeline.unit_level.entity_at(start)
    ou_level_uuid = await _get_ou_level(gql_client, unit_level.value)  # type: ignore

    if ou.objects:
        for validity in one(ou.objects).validities:
            org_unit_hierarchy = (
                validity.org_unit_hierarchy_model.uuid
                if validity.org_unit_hierarchy_model is not None
                else None
            )
            time_planning = (
                validity.time_planning.uuid
                if validity.time_planning is not None
                else None
            )

            await gql_client.update_org_unit(
                OrganisationUnitUpdateInput(
                    uuid=org_unit,
                    validity=_get_mo_validity(start, end),
                    name=sd_unit_timeline.name.entity_at(start).value,
                    user_key=sd_unit_timeline.unit_id.entity_at(start).value,
                    # TODO: remove hard-coded value
                    parent=OrgUnitUUID("12121212-1212-1212-1212-121212121212"),
                    org_unit_type=ou_type_uuid,
                    org_unit_level=ou_level_uuid,
                    org_unit_hierarchy=org_unit_hierarchy,
                    time_planning=time_planning,
                )
            )
        return

    await gql_client.update_org_unit(
        OrganisationUnitUpdateInput(
            uuid=org_unit,
            validity=_get_mo_validity(start, end),
            name=sd_unit_timeline.name.entity_at(start).value,
            user_key=sd_unit_timeline.unit_id.entity_at(start).value,
            # TODO: remove hard-coded value
            parent=OrgUnitUUID("12121212-1212-1212-1212-121212121212"),
            org_unit_type=ou_type_uuid,
            org_unit_level=ou_level_uuid,
        )
    )


async def create_or_update_ou(
    gql_client: GraphQLClient,
    org_unit: OrgUnitUUID,
    start: datetime,
    end: datetime,
    sd_unit_timeline: UnitTimeline,
    org_unit_type_user_key: str,
) -> None:
    ou = await gql_client.get_org_unit_timeline(org_unit, None, None)
    if ou.objects:
        await update_ou(
            gql_client=gql_client,
            org_unit=org_unit,
            start=start,
            end=end,
            sd_unit_timeline=sd_unit_timeline,
            org_unit_type_user_key=org_unit_type_user_key,
        )
        return
    await create_ou(
        gql_client=gql_client,
        org_unit=org_unit,
        start=start,
        end=end,
        sd_unit_timeline=sd_unit_timeline,
        org_unit_type_user_key=org_unit_type_user_key,
    )


async def terminate_ou(
    gql_client: GraphQLClient,
    org_unit: OrgUnitUUID,
    start: datetime,
    end: datetime,
) -> None:
    logger.info("(Re-)terminate OU", org_unit=str(org_unit))

    mo_validity = _get_mo_validity(start, end)

    if mo_validity.to is not None:
        payload = OrganisationUnitTerminateInput(
            uuid=org_unit,
            from_=mo_validity.from_,
            to=mo_validity.to,
        )
    else:
        payload = OrganisationUnitTerminateInput(
            uuid=org_unit,
            # Converting from "from" to "to" due to the wierd way terminations in MO work
            to=mo_validity.from_ - timedelta(days=1),
        )

    await gql_client.terminate_org_unit(payload)
