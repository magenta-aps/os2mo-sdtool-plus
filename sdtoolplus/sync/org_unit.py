# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from itertools import pairwise

import structlog
from fastramqpi.ramqp.depends import handle_exclusively_decorator
from sdclient.client import SDClient
from sdclient.responses import GetDepartmentResponse

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.exceptions import NoValueError
from sdtoolplus.mo.timelines.org_unit import create_ou
from sdtoolplus.mo.timelines.org_unit import create_phone_number
from sdtoolplus.mo.timelines.org_unit import create_pnumber_address
from sdtoolplus.mo.timelines.org_unit import create_postal_address
from sdtoolplus.mo.timelines.org_unit import delete_address
from sdtoolplus.mo.timelines.org_unit import get_ou_timeline
from sdtoolplus.mo.timelines.org_unit import (
    get_phone_number_timeline as get_mo_phone_number_timeline,
)
from sdtoolplus.mo.timelines.org_unit import (
    get_pnumber_timeline as get_mo_pnumber_timeline,
)
from sdtoolplus.mo.timelines.org_unit import (
    get_postal_address_timeline as get_mo_postal_address_timeline,
)
from sdtoolplus.mo.timelines.org_unit import terminate_ou
from sdtoolplus.mo.timelines.org_unit import update_ou
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitParent
from sdtoolplus.models import UnitPhoneNumber
from sdtoolplus.models import UnitPNumber
from sdtoolplus.models import UnitPostalAddress
from sdtoolplus.models import UnitTimeline
from sdtoolplus.models import combine_intervals
from sdtoolplus.sd.timelines.address import sd_postal_address_strategy
from sdtoolplus.sd.timelines.org_unit import get_department
from sdtoolplus.sd.timelines.org_unit import get_department_timeline
from sdtoolplus.sd.timelines.org_unit import (
    get_phone_number_timeline as get_sd_phone_number_timeline,
)
from sdtoolplus.sd.timelines.org_unit import (
    get_pnumber_timeline as get_sd_pnumber_timeline,
)
from sdtoolplus.sd.timelines.org_unit import (
    get_postal_address_timeline as get_sd_postal_address_timeline,
)
from sdtoolplus.sync.common import prefix_unit_id_with_inst_id

logger = structlog.stdlib.get_logger()


def patch_missing_parents(
    settings: SDToolPlusSettings,
    desired_unit_timeline: UnitTimeline,
) -> UnitTimeline:
    """
    In some cases, an SD unit does not have a parent in its entire validity
    interval. This function patches the unit timeline with the parent "Unknown"
    in the intervals, where the SD unit does not have a parent.
    """
    endpoints = sorted(desired_unit_timeline.get_interval_endpoints())
    parent_intervals = []
    for start, end in pairwise(endpoints):
        try:
            desired_unit_timeline.active.entity_at(start)
        except NoValueError:
            continue
        try:
            parent_uuid = desired_unit_timeline.parent.entity_at(start).value
        except NoValueError:
            parent_uuid = settings.unknown_unit  # type: ignore
        parent_intervals.append(
            UnitParent(
                start=start,
                end=end,
                value=parent_uuid,
            )
        )

    return UnitTimeline(
        active=desired_unit_timeline.active,
        name=desired_unit_timeline.name,
        unit_id=desired_unit_timeline.unit_id,
        unit_level=desired_unit_timeline.unit_level,
        parent=Timeline[UnitParent](
            intervals=combine_intervals(tuple(parent_intervals))
        ),
    )


async def sync_ou_intervals(
    gql_client: GraphQLClient,
    settings: SDToolPlusSettings,
    org_unit: OrgUnitUUID,
    desired_unit_timeline: UnitTimeline,
    mo_unit_timeline: UnitTimeline,
    institution_identifier: str,
    priority: int,
    dry_run: bool,
) -> bool:
    logger.info(
        "Create, update or terminate OU in MO",
        org_unit=str(org_unit),
        priority=priority,
    )

    # Skip synchronisation if OU was never in SD. This ensures we don't delete
    # org-units unrelated to SD in MO. Note that is *is* technically possible
    # to delete OUs in SD, but in that case we don't receive an AMQP event
    # anyway due to limitations in SD.
    if desired_unit_timeline == UnitTimeline():
        logger.info("Skipping sync of OU")
        return False

    sd_interval_endpoints = desired_unit_timeline.get_interval_endpoints()
    mo_interval_endpoints = mo_unit_timeline.get_interval_endpoints()

    endpoints = sorted(sd_interval_endpoints.union(mo_interval_endpoints))
    logger.info("List of endpoints", endpoints=endpoints)

    for start, end in pairwise(endpoints):
        logger.info("Processing endpoint pair", start=start, end=end)

        if desired_unit_timeline.equal_at(start, mo_unit_timeline):
            logger.info("SD and MO equal")
            continue

        try:
            is_active = desired_unit_timeline.active.entity_at(start).value
        except NoValueError:
            is_active = False  # type: ignore

        if not is_active:
            await terminate_ou(
                gql_client=gql_client,
                org_unit=org_unit,
                start=start,
                end=end,
                institution_identifier=institution_identifier,
                priority=priority,
                dry_run=dry_run,
            )
            continue

        if not desired_unit_timeline.has_required_mo_values(start):
            logger.error("Cannot update OU due to missing timeline data")
            return False

        ou = await gql_client.get_org_unit_timeline(
            unit_uuid=org_unit, from_date=None, to_date=None
        )
        if ou.objects:
            await update_ou(
                gql_client=gql_client,
                org_unit=org_unit,
                start=start,
                end=end,
                desired_unit_timeline=desired_unit_timeline,
                org_unit_type_user_key=settings.org_unit_type,
                institution_identifier=institution_identifier,
                priority=priority,
                dry_run=dry_run,
            )
        else:
            await create_ou(
                gql_client=gql_client,
                org_unit=org_unit,
                start=start,
                end=end,
                desired_unit_timeline=desired_unit_timeline,
                org_unit_type_user_key=settings.org_unit_type,
                institution_identifier=institution_identifier,
                priority=priority,
                dry_run=dry_run,
            )

        logger.info("Finished updating unit in interval", org_unit=str(org_unit))

    logger.info("Finished syncing unit", org_unit=str(org_unit))
    return True


async def _sync_ou_pnumber(
    gql_client: GraphQLClient,
    department: GetDepartmentResponse,
    org_unit: OrgUnitUUID,
    dry_run: bool,
) -> None:
    logger.info("Sync P-number timeline", org_unit=str(org_unit))

    sd_pnumber_timeline = get_sd_pnumber_timeline(department)
    mo_pnumber_timeline_obj = await get_mo_pnumber_timeline(
        gql_client=gql_client,
        unit_uuid=org_unit,
    )

    if sd_pnumber_timeline == mo_pnumber_timeline_obj.pnumber:
        logger.info("P-number timelines identical")
        return

    if mo_pnumber_timeline_obj.uuid is not None:
        await delete_address(
            gql_client=gql_client,
            address_uuid=mo_pnumber_timeline_obj.uuid,
            dry_run=dry_run,
        )

    if sd_pnumber_timeline == Timeline[UnitPNumber]():
        return

    await create_pnumber_address(
        gql_client=gql_client,
        org_unit=org_unit,
        address_uuid=mo_pnumber_timeline_obj.uuid,
        sd_pnumber_timeline=sd_pnumber_timeline,
        dry_run=dry_run,
    )


async def _sync_ou_postal_address(
    gql_client: GraphQLClient,
    settings: SDToolPlusSettings,
    department: GetDepartmentResponse,
    org_unit: OrgUnitUUID,
    dry_run: bool,
) -> None:
    logger.info("Sync postal address timeline", org_unit=str(org_unit))

    sd_postal_address_timeline = get_sd_postal_address_timeline(department)
    desired_postal_address_timeline = await sd_postal_address_strategy(
        settings=settings,
        sd_postal_address_timeline=sd_postal_address_timeline,
    )
    mo_postal_address_timeline_obj = await get_mo_postal_address_timeline(
        gql_client=gql_client,
        settings=settings,
        unit_uuid=org_unit,
    )

    if desired_postal_address_timeline == mo_postal_address_timeline_obj.postal_address:
        logger.info("Postal address timelines identical")
        return

    if mo_postal_address_timeline_obj.uuid is not None:
        await delete_address(
            gql_client=gql_client,
            address_uuid=mo_postal_address_timeline_obj.uuid,
            dry_run=dry_run,
        )

    if sd_postal_address_timeline == Timeline[UnitPostalAddress]():
        return

    await create_postal_address(
        gql_client=gql_client,
        settings=settings,
        org_unit=org_unit,
        address_uuid=mo_postal_address_timeline_obj.uuid,
        desired_postal_address_timeline=desired_postal_address_timeline,
        dry_run=dry_run,
    )


async def _sync_ou_phone_number(
    gql_client: GraphQLClient,
    department: GetDepartmentResponse,
    org_unit: OrgUnitUUID,
    dry_run: bool,
) -> None:
    logger.info("Sync phone number timeline", org_unit=str(org_unit))

    sd_phone_number_timeline = get_sd_phone_number_timeline(department)
    mo_phone_number_timeline_obj = await get_mo_phone_number_timeline(
        gql_client=gql_client,
        unit_uuid=org_unit,
    )

    if sd_phone_number_timeline == mo_phone_number_timeline_obj.phone_number:
        logger.info("Phone number timelines identical")
        return

    if mo_phone_number_timeline_obj.uuid is not None:
        await delete_address(
            gql_client=gql_client,
            address_uuid=mo_phone_number_timeline_obj.uuid,
            dry_run=dry_run,
        )

    if sd_phone_number_timeline == Timeline[UnitPhoneNumber]():
        return

    await create_phone_number(
        gql_client=gql_client,
        org_unit=org_unit,
        address_uuid=mo_phone_number_timeline_obj.uuid,
        sd_phone_number_timeline=sd_phone_number_timeline,
        dry_run=dry_run,
    )


@handle_exclusively_decorator(
    key=lambda sd_client,
    gql_client,
    institution_identifier,
    org_unit,
    settings,
    priority,
    dry_run=False: org_unit
)
async def sync_ou(
    sd_client: SDClient,
    gql_client: GraphQLClient,
    institution_identifier: str,
    org_unit: OrgUnitUUID,
    settings: SDToolPlusSettings,
    priority: int,
    dry_run: bool = False,
) -> None:
    """Sync the entire org unit timeline for the given unit."""
    logger.info(
        "Sync OU timeline",
        institution_identifier=institution_identifier,
        org_uuid=str(org_unit),
        dry_run=dry_run,
    )

    department = await get_department(
        sd_client=sd_client,
        institution_identifier=institution_identifier,
        unit_uuid=org_unit,
    )

    sd_unit_timeline = await get_department_timeline(
        department=department,
        sd_client=sd_client,
        inst_id=institution_identifier,
        unit_uuid=org_unit,
        sd_institution_to_mo_root_ou_uuid_map=settings.sd_institution_to_mo_root_ou_uuid_map,
    )
    desired_unit_timeline = prefix_unit_id_with_inst_id(
        settings, sd_unit_timeline, institution_identifier
    )
    desired_unit_timeline = patch_missing_parents(settings, desired_unit_timeline)

    mo_unit_timeline = await get_ou_timeline(gql_client, org_unit)

    ou_sync_successful = await sync_ou_intervals(
        gql_client=gql_client,
        settings=settings,
        org_unit=org_unit,
        desired_unit_timeline=desired_unit_timeline,
        mo_unit_timeline=mo_unit_timeline,
        institution_identifier=institution_identifier,
        priority=priority,
        dry_run=dry_run,
    )

    if department is None:
        logger.warning("Department not found in SD! Skipping OU address sync")
        return
    if not ou_sync_successful:
        logger.warning("OU sync failed! Skipping OU address sync")
        return
    if not settings.enable_ou_address_sync:
        logger.warning("OU address sync disabled! Skipping OU address sync")
        return

    logger.info("Syncing OU addresses", org_unit=str(org_unit))

    await _sync_ou_pnumber(
        gql_client=gql_client,
        department=department,
        org_unit=org_unit,
        dry_run=dry_run,
    )

    await _sync_ou_postal_address(
        gql_client=gql_client,
        settings=settings,
        department=department,
        org_unit=org_unit,
        dry_run=dry_run,
    )

    await _sync_ou_phone_number(
        gql_client=gql_client,
        department=department,
        org_unit=org_unit,
        dry_run=dry_run,
    )

    logger.info("Finished syncing OU addresses", org_unit=str(org_unit))
    logger.info("Finished syncing OU and its addresses!", org_unit=str(org_unit))
