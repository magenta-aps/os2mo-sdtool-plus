# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from datetime import timedelta
from uuid import UUID

import structlog
from more_itertools import one
from more_itertools import only

from sdtoolplus.autogenerated_graphql_client import ClassFilter
from sdtoolplus.autogenerated_graphql_client import EmployeeFilter
from sdtoolplus.autogenerated_graphql_client import EngagementCreateInput
from sdtoolplus.autogenerated_graphql_client import EngagementTerminateInput
from sdtoolplus.autogenerated_graphql_client import EngagementUpdateInput
from sdtoolplus.autogenerated_graphql_client import FacetFilter
from sdtoolplus.autogenerated_graphql_client import LeaveCreateInput
from sdtoolplus.autogenerated_graphql_client import LeaveFilter
from sdtoolplus.autogenerated_graphql_client import LeaveTerminateInput
from sdtoolplus.autogenerated_graphql_client import LeaveUpdateInput
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
from sdtoolplus.models import EngagementKey
from sdtoolplus.models import EngagementName
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.models import EngagementType
from sdtoolplus.models import EngagementUnit
from sdtoolplus.models import EngagementUnitId
from sdtoolplus.models import EngType
from sdtoolplus.models import LeaveTimeline
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitId
from sdtoolplus.models import UnitLevel
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitParent
from sdtoolplus.models import UnitTimeline
from sdtoolplus.models import combine_intervals

logger = structlog.stdlib.get_logger()


def mo_end_to_datetime(mo_end: datetime | None) -> datetime:
    """
    Convert a MO end datetime or None to a datetime directly as it is in MO, i.e.
    no +/- timedelta adjustments are performed.
    """
    return mo_end if mo_end is not None else POSITIVE_INFINITY


def datetime_to_mo_end(end_datetime: datetime) -> datetime | None:
    """
    Convert a datetime to a MO end date or None directly as it is, i.e. no +/-
    timedelta adjustments are performed.
    """
    return None if end_datetime == POSITIVE_INFINITY else end_datetime


def _from_mo_end_datetime(d: datetime | None) -> datetime:
    """
    Convert a MO end datetime to the end date required by our timeline objects.
    """
    return d + timedelta(days=1) if d is not None else POSITIVE_INFINITY


def timeline_interval_to_mo_validity(start: datetime, end: datetime) -> RAValidityInput:
    mo_end = datetime_to_mo_end(end)
    # Subtract one day due to MO
    mo_end = mo_end - timedelta(days=1) if mo_end is not None else None
    return RAValidityInput(from_=start, to=mo_end)


def get_patch_validity(
    codegen_validity_from: datetime,
    codegen_validity_to: datetime | None,
    mo_validity: RAValidityInput,
) -> RAValidityInput:
    """
    Get the validity for which the patch update should be performed. We need to truncate
    it with the timeline (start, end) endpoint update validities in order not to write
    beyond these in MO for the particular patch operation.
    """
    codegen_validity_to_datetime = mo_end_to_datetime(codegen_validity_to)
    mo_validity_to = mo_end_to_datetime(mo_validity.to)

    patch_validity_from = max(codegen_validity_from, mo_validity.from_)
    patch_validity_to = min(codegen_validity_to_datetime, mo_validity_to)

    return RAValidityInput(
        from_=patch_validity_from,
        to=None if patch_validity_to is POSITIVE_INFINITY else patch_validity_to,
    )


async def _get_ou_type(
    gql_client: GraphQLClient,
    org_unit_type_user_key: str,
) -> OrgUnitTypeUUID:
    ou_type_classes = await gql_client.get_class(
        ClassFilter(
            facet=FacetFilter(user_key="org_unit_type"),
            user_keys=[org_unit_type_user_key],
        )
    )

    current = one(ou_type_classes.objects).current
    assert current is not None
    return current.uuid


async def _get_ou_level(
    gql_client: GraphQLClient,
    org_unit_level_user_key: str,
) -> OrgUnitLevelUUID:
    ou_level_classes = await gql_client.get_class(
        ClassFilter(
            facet=FacetFilter(user_key="org_unit_level"),
            user_keys=[org_unit_level_user_key],
        )
    )

    current = one(ou_level_classes.objects).current
    assert current is not None
    return current.uuid


async def get_engagement_types(gql_client: GraphQLClient) -> dict[EngType, UUID]:
    """
    Get map from engagement type (Enum) to MO engagement type class UUID
    """
    r_eng_types = await gql_client.get_class(
        ClassFilter(facet=FacetFilter(user_key="engagement_type"))
    )

    relevant_classes = (
        obj.current
        for obj in r_eng_types.objects
        if obj.current is not None
        and obj.current.name in (eng_type.value for eng_type in EngType)
    )

    return {EngType(clazz.name): clazz.uuid for clazz in relevant_classes}


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
            parent=Timeline[UnitParent](),
        )

    validities = one(objects).validities

    activity_intervals = tuple(
        Active(
            start=obj.validity.from_,
            # TODO (#61435): MOs GraphQL subtracts one day from the validity end dates
            # when reading, compared to what was written.
            end=_from_mo_end_datetime(obj.validity.to),
            value=True,
        )
        for obj in validities
    )

    id_intervals = tuple(
        UnitId(
            start=obj.validity.from_,
            end=_from_mo_end_datetime(obj.validity.to),
            value=obj.user_key,
        )
        for obj in validities
    )

    level_intervals = tuple(
        UnitLevel(
            start=obj.validity.from_,
            end=_from_mo_end_datetime(obj.validity.to),
            value=obj.org_unit_level.name if obj.org_unit_level is not None else None,
        )
        for obj in validities
    )

    name_intervals = tuple(
        UnitName(
            start=obj.validity.from_,
            end=_from_mo_end_datetime(obj.validity.to),
            value=obj.name,
        )
        for obj in validities
    )

    parent_intervals = tuple(
        UnitParent(
            start=obj.validity.from_,
            end=_from_mo_end_datetime(obj.validity.to),
            value=obj.parent.uuid if obj.parent is not None else None,
        )
        for obj in validities
    )

    timeline = UnitTimeline(
        active=Timeline[Active](intervals=combine_intervals(activity_intervals)),
        name=Timeline[UnitName](intervals=combine_intervals(name_intervals)),
        unit_id=Timeline[UnitId](intervals=combine_intervals(id_intervals)),
        unit_level=Timeline[UnitLevel](intervals=combine_intervals(level_intervals)),
        parent=Timeline[UnitParent](intervals=combine_intervals(parent_intervals)),
    )
    logger.debug("MO OU timeline", timeline=timeline.dict())

    return timeline


async def create_ou(
    gql_client: GraphQLClient,
    org_unit: OrgUnitUUID,
    start: datetime,
    end: datetime,
    sd_unit_timeline: UnitTimeline,
    org_unit_type_user_key: str,
    dry_run: bool = False,
) -> None:
    logger.info("Creating OU", uuid=str(org_unit))
    logger.debug(
        "Creating OU", start=start, end=end, sd_unit_timeline=sd_unit_timeline.dict()
    )

    # Get the OU type UUID
    ou_type_uuid = await _get_ou_type(gql_client, org_unit_type_user_key)

    # Get the OU level UUID
    unit_level = sd_unit_timeline.unit_level.entity_at(start)
    ou_level_uuid = await _get_ou_level(gql_client, unit_level.value)  # type: ignore

    payload = OrganisationUnitCreateInput(
        uuid=org_unit,
        validity=timeline_interval_to_mo_validity(start, end),
        name=sd_unit_timeline.name.entity_at(start).value,
        user_key=sd_unit_timeline.unit_id.entity_at(start).value,
        parent=sd_unit_timeline.parent.entity_at(start).value,
        org_unit_type=ou_type_uuid,
        org_unit_level=ou_level_uuid,
    )
    logger.debug("OU create payload", payload=payload.dict())
    if not dry_run:
        await gql_client.create_org_unit(payload)


async def update_ou(
    gql_client: GraphQLClient,
    org_unit: OrgUnitUUID,
    start: datetime,
    end: datetime,
    sd_unit_timeline: UnitTimeline,
    org_unit_type_user_key: str,
    dry_run: bool = False,
) -> None:
    logger.info("Updating OU", uuid=str(org_unit))
    logger.debug(
        "Updating OU", start=start, end=end, sd_unit_timeline=sd_unit_timeline.dict()
    )

    mo_validity = timeline_interval_to_mo_validity(start, end)
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
        # The OU already exists in this validity period
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

            payload = OrganisationUnitUpdateInput(
                uuid=org_unit,
                validity=get_patch_validity(
                    validity.validity.from_, validity.validity.to, mo_validity
                ),
                name=sd_unit_timeline.name.entity_at(start).value,
                user_key=sd_unit_timeline.unit_id.entity_at(start).value,
                parent=sd_unit_timeline.parent.entity_at(start).value,
                org_unit_type=ou_type_uuid,
                org_unit_level=ou_level_uuid,
                org_unit_hierarchy=org_unit_hierarchy,
                time_planning=time_planning,
            )
            logger.debug("OU update payload", payload=payload.dict())
            if not dry_run:
                await gql_client.update_org_unit(payload)
        return

    # The OU does not already exist in this validity period
    payload = OrganisationUnitUpdateInput(
        uuid=org_unit,
        validity=mo_validity,
        name=sd_unit_timeline.name.entity_at(start).value,
        user_key=sd_unit_timeline.unit_id.entity_at(start).value,
        parent=sd_unit_timeline.parent.entity_at(start).value,
        org_unit_type=ou_type_uuid,
        org_unit_level=ou_level_uuid,
    )
    logger.debug("OU update payload", payload=payload.dict())
    if not dry_run:
        await gql_client.update_org_unit(payload)


async def terminate_ou(
    gql_client: GraphQLClient,
    org_unit: OrgUnitUUID,
    start: datetime,
    end: datetime,
    dry_run: bool = False,
) -> None:
    logger.info("(Re-)terminate OU", org_unit=str(org_unit))

    mo_validity = timeline_interval_to_mo_validity(start, end)

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

    logger.debug("OU terminate payload", payload=payload.dict())
    if not dry_run:
        await gql_client.terminate_org_unit(payload)


async def get_engagement_timeline(
    gql_client: GraphQLClient,
    person: UUID,
    user_key: str,
) -> EngagementTimeline:
    logger.info("Get MO engagement timeline", person=str(person), emp_id=user_key)

    gql_timeline = await gql_client.get_engagement_timeline(
        person=person, user_key=user_key, from_date=None, to_date=None
    )
    objects = gql_timeline.objects

    if not objects:
        return EngagementTimeline(
            eng_active=Timeline[Active](),
            eng_key=Timeline[EngagementKey](),
            eng_name=Timeline[EngagementName](),
            eng_unit=Timeline[EngagementUnit](),
        )

    object_ = one(objects)
    validities = object_.validities

    activity_intervals = tuple(
        Active(
            start=obj.validity.from_,
            # TODO (#61435): MOs GraphQL subtracts one day from the validity end dates
            # when reading, compared to what was written.
            end=_from_mo_end_datetime(obj.validity.to),
            value=True,
        )
        for obj in validities
    )

    key_intervals = tuple(
        EngagementKey(
            start=obj.validity.from_,
            end=_from_mo_end_datetime(obj.validity.to),
            value=obj.job_function.user_key,
        )
        for obj in validities
    )

    name_intervals = tuple(
        EngagementName(
            start=obj.validity.from_,
            end=_from_mo_end_datetime(obj.validity.to),
            # TODO: introduce name strategy here
            value=obj.extension_1,
        )
        for obj in validities
    )

    unit_intervals = tuple(
        EngagementUnit(
            start=obj.validity.from_,
            end=_from_mo_end_datetime(obj.validity.to),
            value=one(obj.org_unit).uuid,
        )
        for obj in validities
    )

    unit_id_intervals = tuple(
        EngagementUnitId(
            start=obj.validity.from_,
            end=_from_mo_end_datetime(obj.validity.to),
            value=obj.extension_2,
        )
        for obj in validities
    )

    type_intervals = tuple(
        EngagementType(
            start=obj.validity.from_,
            end=_from_mo_end_datetime(obj.validity.to),
            value=EngType(obj.engagement_type.name),
        )
        for obj in validities
    )

    timeline = EngagementTimeline(
        eng_active=Timeline[Active](intervals=combine_intervals(activity_intervals)),
        eng_key=Timeline[EngagementKey](intervals=combine_intervals(key_intervals)),
        eng_name=Timeline[EngagementName](intervals=combine_intervals(name_intervals)),
        eng_unit=Timeline[EngagementUnit](intervals=combine_intervals(unit_intervals)),
        eng_unit_id=Timeline[EngagementUnitId](
            intervals=combine_intervals(unit_id_intervals)
        ),
        eng_type=Timeline[EngagementType](intervals=combine_intervals(type_intervals)),
    )
    logger.debug("MO engagement timeline", timeline=timeline.dict())

    return timeline


async def get_leave_timeline(
    gql_client: GraphQLClient,
    person: UUID,
    user_key: str,
) -> LeaveTimeline:
    gql_timeline = await gql_client.get_leave(
        LeaveFilter(
            employee=EmployeeFilter(uuids=[person]),
            user_keys=[user_key],
            from_date=None,
            to_date=None,
        )
    )
    objects = gql_timeline.objects

    if not objects:
        return LeaveTimeline()

    validities = one(objects).validities

    active_intervals = tuple(
        Active(
            start=obj.validity.from_,
            end=_from_mo_end_datetime(obj.validity.to),
            value=True,
        )
        for obj in validities
    )

    timeline = LeaveTimeline(
        leave_active=Timeline[Active](intervals=combine_intervals(active_intervals)),
    )
    logger.debug("MO leave timeline", timeline=timeline.dict())

    return timeline


async def create_engagement(
    gql_client: GraphQLClient,
    person: UUID,
    user_key: str,
    start: datetime,
    end: datetime,
    sd_eng_timeline: EngagementTimeline,
    eng_types: dict[EngType, UUID],
) -> None:
    logger.info("Creating engagement", person=str(person), emp_id=user_key)
    logger.debug(
        "Creating engagement",
        start=start,
        end=end,
        sd_eng_timeline=sd_eng_timeline.dict(),
    )

    # Get the job_function
    r_job_function = await gql_client.get_class(
        ClassFilter(
            facet=FacetFilter(user_key="engagement_job_function"),
            user_keys=[str(sd_eng_timeline.eng_key.entity_at(start).value)],
        )
    )
    current_job_function = one(r_job_function.objects).current
    assert current_job_function is not None
    job_function_uuid = current_job_function.uuid

    await gql_client.create_engagement(
        EngagementCreateInput(
            user_key=user_key,
            validity=timeline_interval_to_mo_validity(start, end),
            # TODO: introduce extension_1 strategy
            extension_1=sd_eng_timeline.eng_name.entity_at(start).value,
            extension_2=sd_eng_timeline.eng_unit_id.entity_at(start).value,
            person=person,
            # TODO: introduce org_unit strategy
            org_unit=sd_eng_timeline.eng_unit.entity_at(start).value,
            engagement_type=eng_types[sd_eng_timeline.eng_type.entity_at(start).value],  # type: ignore
            # TODO: introduce job_function strategy
            job_function=job_function_uuid,
        )
    )


async def create_leave(
    gql_client: GraphQLClient,
    person: UUID,
    eng_uuid: UUID,
    user_key: str,
    start: datetime,
    end: datetime,
    sd_leave_timeline: LeaveTimeline,
    leave_type: UUID,
    dry_run: bool = False,
) -> None:
    logger.info("Create leave", person=str(person), user_key=user_key)
    logger.debug(
        "Create leave", start=start, end=end, sd_leave_timeline=sd_leave_timeline.dict()
    )

    payload = LeaveCreateInput(
        user_key=user_key,
        person=person,
        engagement=eng_uuid,
        leave_type=leave_type,
        validity=timeline_interval_to_mo_validity(start, end),
    )
    logger.debug("Create leave payload", payload=payload.dict())

    if not dry_run:
        await gql_client.create_leave(payload)


async def update_engagement(
    gql_client: GraphQLClient,
    person: UUID,
    user_key: str,
    start: datetime,
    end: datetime,
    sd_eng_timeline: EngagementTimeline,
    eng_types: dict[EngType, UUID],
) -> None:
    logger.info("Update engagement", person=str(person), emp_id=user_key)
    logger.debug(
        "Update engagement",
        start=start,
        end=end,
        sd_eng_timeline=sd_eng_timeline.dict(),
    )

    # Get the job_function
    r_job_function = await gql_client.get_class(
        ClassFilter(
            facet=FacetFilter(user_key="engagement_job_function"),
            user_keys=[str(sd_eng_timeline.eng_key.entity_at(start).value)],
        )
    )
    current_job_function = one(r_job_function.objects).current
    assert current_job_function is not None
    job_function_uuid = current_job_function.uuid

    mo_validity = timeline_interval_to_mo_validity(start, end)

    eng = await gql_client.get_engagement_timeline(
        person=person, user_key=user_key, from_date=start, to_date=end
    )
    obj = only(eng.objects)

    if obj:
        # The engagement already exists in this validity period
        for validity in one(eng.objects).validities:
            payload = EngagementUpdateInput(
                uuid=obj.uuid,
                user_key=user_key,
                primary=validity.primary.uuid if validity.primary is not None else None,
                validity=get_patch_validity(
                    validity.validity.from_, validity.validity.to, mo_validity
                ),
                # TODO: introduce extention_1 strategy
                extension_1=sd_eng_timeline.eng_name.entity_at(start).value,
                extension_2=sd_eng_timeline.eng_unit_id.entity_at(start).value,
                extension_3=validity.extension_3,
                extension_4=validity.extension_4,
                extension_5=validity.extension_5,
                extension_6=validity.extension_6,
                extension_7=validity.extension_7,
                extension_8=validity.extension_8,
                extension_9=validity.extension_9,
                extension_10=validity.extension_10,
                person=person,
                org_unit=sd_eng_timeline.eng_unit.entity_at(start).value,
                engagement_type=eng_types[
                    sd_eng_timeline.eng_type.entity_at(start).value  # type: ignore
                ],
                job_function=job_function_uuid,
            )
            logger.debug(
                "Update engament in validity interval",
                payload=payload.dict(),
                validity=validity,
            )
            await gql_client.update_engagement(payload)
        return

    # The engagement does not already exist in this validity period
    eng = await gql_client.get_engagement_timeline(
        person=person, user_key=user_key, from_date=None, to_date=None
    )
    payload = EngagementUpdateInput(
        uuid=one(eng.objects).uuid,
        user_key=user_key,
        validity=mo_validity,
        # TODO: introduce extention_1 strategy
        extension_1=sd_eng_timeline.eng_name.entity_at(start).value,
        extension_2=sd_eng_timeline.eng_unit_id.entity_at(start).value,
        person=person,
        org_unit=sd_eng_timeline.eng_unit.entity_at(start).value,
        engagement_type=eng_types[sd_eng_timeline.eng_type.entity_at(start).value],  # type: ignore
        job_function=job_function_uuid,
    )
    logger.debug(
        "Update engament in interval", payload=payload.dict(), mo_validity=mo_validity
    )
    await gql_client.update_engagement(payload)


async def update_leave(
    gql_client: GraphQLClient,
    person: UUID,
    eng_uuid: UUID,
    user_key: str,
    start: datetime,
    end: datetime,
    sd_leave_timeline: LeaveTimeline,
    leave_type: UUID,
    dry_run: bool = False,
) -> None:
    logger.info("Update leave", person=str(person), user_key=user_key)
    logger.debug(
        "Update leave", start=start, end=end, sd_leave_timeline=sd_leave_timeline.dict()
    )

    mo_validity = timeline_interval_to_mo_validity(start, end)

    leave = await gql_client.get_leave(
        LeaveFilter(
            employee=EmployeeFilter(uuids=[person]),
            user_keys=[user_key],
            from_date=start,
            to_date=end,
        )
    )
    objects = leave.objects
    obj = only(objects)

    if obj:
        # The leave already exists in this validity period
        for validity in one(objects).validities:
            payload = LeaveUpdateInput(
                uuid=obj.uuid,
                user_key=user_key,
                person=person,
                engagement=eng_uuid,
                leave_type=leave_type,
                validity=get_patch_validity(
                    validity.validity.from_, validity.validity.to, mo_validity
                ),
            )
            logger.debug("Update leave", payload=payload.dict())
            if not dry_run:
                await gql_client.update_leave(payload)
        return

    # The leave does not already exist in this validity period
    leave = await gql_client.get_leave(
        LeaveFilter(
            employee=EmployeeFilter(uuids=[person]),
            user_keys=[user_key],
            from_date=None,
            to_date=None,
        )
    )
    payload = LeaveUpdateInput(
        uuid=one(leave.objects).uuid,
        user_key=user_key,
        person=person,
        engagement=eng_uuid,
        leave_type=leave_type,
        validity=mo_validity,
    )
    logger.debug("Update leave payload", payload=payload.dict())

    if not dry_run:
        await gql_client.update_leave(payload)


async def terminate_engagement(
    gql_client: GraphQLClient,
    person: UUID,
    user_key: str,
    start: datetime,
    end: datetime,
) -> None:
    logger.info(
        "(Re-)terminate engagement",
        person=str(person),
        user_key=user_key,
        start=start,
        end=end,
    )

    mo_validity = timeline_interval_to_mo_validity(start, end)

    eng = await gql_client.get_engagement_timeline(
        person=person, user_key=user_key, from_date=None, to_date=None
    )
    eng_uuid = one(eng.objects).uuid

    if mo_validity.to is not None:
        payload = EngagementTerminateInput(
            uuid=eng_uuid, from_=mo_validity.from_, to=mo_validity.to
        )
    else:
        payload = EngagementTerminateInput(
            uuid=eng_uuid,
            # Converting from "from" to "to" due to the wierd way terminations in MO work
            to=mo_validity.from_ - timedelta(days=1),
        )
    logger.debug("Terminate engagement", payload=payload.dict())

    await gql_client.terminate_engagement(payload)


async def terminate_leave(
    gql_client: GraphQLClient,
    person: UUID,
    user_key: str,
    start: datetime,
    end: datetime,
    dry_run: bool = False,
) -> None:
    logger.info(
        "(Re-)terminate leave",
        person=str(person),
        user_key=user_key,
        start=start,
        end=end,
    )

    mo_validity = timeline_interval_to_mo_validity(start, end)

    leave = await gql_client.get_leave(
        LeaveFilter(
            employee=EmployeeFilter(uuids=[person]),
            user_keys=[user_key],
            from_date=None,
            to_date=None,
        )
    )
    leave_uuid = one(leave.objects).uuid

    if mo_validity.to is not None:
        payload = LeaveTerminateInput(
            uuid=leave_uuid, from_=mo_validity.from_, to=mo_validity.to
        )
    else:
        payload = LeaveTerminateInput(
            uuid=leave_uuid,
            # Converting from "from" to "to" due to the wierd way terminations in MO work
            to=mo_validity.from_ - timedelta(days=1),
        )
    logger.debug("Terminate leave", payload=payload.dict())

    if not dry_run:
        await gql_client.terminate_leave(payload)
