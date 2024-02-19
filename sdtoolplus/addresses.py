# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from enum import Enum
from typing import TypeAlias
from uuid import UUID

import structlog
from more_itertools import only
from os2mo_dar_client import AsyncDARClient
from pydantic import BaseModel
from sdclient.client import SDClient

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.filters import filter_by_uuid
from sdtoolplus.filters import remove_by_name
from sdtoolplus.graphql import add_address
from sdtoolplus.graphql import get_address_type_uuid
from sdtoolplus.graphql import get_graphql_client
from sdtoolplus.graphql import update_address
from sdtoolplus.mo_org_unit_importer import Address
from sdtoolplus.mo_org_unit_importer import AddressType
from sdtoolplus.mo_org_unit_importer import AddressTypeUUID
from sdtoolplus.mo_org_unit_importer import MOOrgTreeImport
from sdtoolplus.mo_org_unit_importer import OrgUnitNode
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.sd.importer import get_sd_units

DARAddressUUID: TypeAlias = UUID

logger = structlog.get_logger()


class AddressOperation(Enum):
    ADD = "add"
    UPDATE = "update"


class AddressCollection(BaseModel):
    addresses_to_add: list[Address]
    addresses_to_update: list[Address]


def _get_unit_address(org_unit_node: OrgUnitNode, address_type: str) -> Address | None:
    # TODO: add docstring
    # TODO: filter on address type UUID instead of address type string
    try:
        addr = only(
            addr
            for addr in org_unit_node.addresses
            if addr.address_type.user_key == address_type
        )
    except ValueError as error:
        logger.error(
            f"More than one {address_type} address",
            org_unit_uuid=str(org_unit_node.uuid),
            error=error,
        )
        return None
    return addr


def _add_addresses_for_new_unit(org_unit_node: OrgUnitNode) -> list[Address]:
    # TODO: Docstring
    # TODO: get rid of magic values

    addresses_to_add = []
    for address_type in ["AddressMailUnit", "Pnummer"]:
        addr = _get_unit_address(org_unit_node, address_type)
        if addr is not None:
            addresses_to_add.append(addr)

    return addresses_to_add


def update_or_add_addresses(
    sd_unit: OrgUnitNode,
    mo_unit: OrgUnitNode | None,
    postal_addr_type_uuid: AddressTypeUUID,
    pnumber_addr_type_uuid: AddressTypeUUID,
) -> AddressCollection:
    # TODO: docstring

    addresses_to_add = []
    addresses_to_update = []

    if mo_unit is None:
        addresses_to_add.extend(_add_addresses_for_new_unit(sd_unit))
        return AddressCollection(
            addresses_to_add=[
                Address(
                    name=addr.name,
                    address_type=AddressType(
                        user_key=addr.address_type.user_key,
                        uuid=postal_addr_type_uuid
                        if addr.address_type.user_key == "AddressMailUnit"
                        else pnumber_addr_type_uuid,
                    ),
                )
                for addr in addresses_to_add
            ],
            addresses_to_update=[],
        )

    for address_type in ["AddressMailUnit", "Pnummer"]:
        sd_addr = _get_unit_address(sd_unit, address_type)
        mo_addr = _get_unit_address(mo_unit, address_type)

        if sd_addr is None:
            continue

        if mo_addr is None:
            addresses_to_add.append(
                Address(
                    name=sd_addr.name,
                    address_type=AddressType(
                        user_key=sd_addr.address_type.user_key,
                        uuid=postal_addr_type_uuid
                        if sd_addr.address_type.user_key == "AddressMailUnit"
                        else pnumber_addr_type_uuid,
                    ),
                )
            )
        else:
            if not sd_addr.name == mo_addr.name:
                addresses_to_update.append(
                    Address(
                        uuid=mo_addr.uuid,
                        name=sd_addr.name,
                        address_type=mo_addr.address_type,
                    )
                )

    return AddressCollection(
        addresses_to_add=addresses_to_add, addresses_to_update=addresses_to_update
    )


def update_or_add_pnumber_address(
    sd_unit: OrgUnitNode,
    mo_unit: OrgUnitNode,
    pnumber_addr_type_uuid: AddressTypeUUID,
) -> Address | None:
    # TODO: docstring

    sd_addr = _get_unit_address(sd_unit, "Pnummer")
    if sd_addr is None:
        return None

    mo_addr = _get_unit_address(mo_unit, "Pnummer")

    if mo_addr is None:
        return Address(
            name=sd_addr.name,
            address_type=AddressType(
                user_key=sd_addr.address_type.user_key, uuid=pnumber_addr_type_uuid
            ),
        )

    if not sd_addr.name == mo_addr.name:
        return Address(
            uuid=mo_addr.uuid,  # If set, we know that we are updating and not creating
            name=sd_addr.name,
            address_type=mo_addr.address_type,
        )
    return None


async def get_dar_addr_uuid(
    dar_client: AsyncDARClient, addr: Address
) -> DARAddressUUID:
    async with dar_client:
        r = await dar_client.cleanse_single(addr.name)
        return DARAddressUUID(r["id"])


async def update_or_add_postal_address(
    dar_client: AsyncDARClient,
    sd_unit: OrgUnitNode,
    mo_unit: OrgUnitNode,
    postal_addr_type_uuid: AddressTypeUUID,
) -> Address | None:
    # TODO: add docstring

    sd_addr = _get_unit_address(sd_unit, "AddressMailUnit")
    if sd_addr is None:
        return None

    # Get DAR address UUID
    dar_uuid = await get_dar_addr_uuid(dar_client, sd_addr)

    mo_addr = _get_unit_address(mo_unit, "AddressMailUnit")
    if mo_addr is None:
        # Create a new address
        return Address(
            name=str(dar_uuid),
            address_type=AddressType(
                user_key="AddressMailUnit", uuid=postal_addr_type_uuid
            ),
        )

    # Update existing address
    if not sd_addr.name == mo_addr.name:
        return Address(
            uuid=mo_addr.uuid,  # If set, we know that we are updating and not creating
            name=str(dar_uuid),
            address_type=AddressType(
                user_key="AddressMailUnit", uuid=postal_addr_type_uuid
            ),
        )

    return None


async def fix_addresses(
    gql_client: GraphQLClient,
    dar_client: AsyncDARClient,
    settings: SDToolPlusSettings,
    org_unit: OrgUnitUUID | None,
    dry_run: bool,
):
    logger.info("Add or update addresses")

    # Get the SD and MO clients
    sd_client = SDClient(
        settings.sd_username,
        settings.sd_password.get_secret_value(),
    )
    # TODO: use auto-generated client instead
    persistent_client = get_graphql_client(settings)

    # Get the SD units
    logger.info("Getting SD units...")
    sd_units = get_sd_units(sd_client, settings.sd_institution_identifier)

    # Get the MO units
    logger.info("Getting MO units...")
    mo_org_tree_import = MOOrgTreeImport(persistent_client)
    mo_org_units = mo_org_tree_import.get_org_units(org_unit)

    mo_units = [OrgUnitNode.from_org_unit(org_unit) for org_unit in mo_org_units]
    mo_units = filter_by_uuid(org_unit, mo_units)
    mo_units = remove_by_name(settings.regex_unit_names_to_remove, mo_units)

    mo_unit_map: dict[OrgUnitUUID, OrgUnitNode] = {
        mo_unit.uuid: mo_unit for mo_unit in mo_units
    }

    # Only fix units that are already in MO
    sd_units = [sd_unit for sd_unit in sd_units if sd_unit.uuid in mo_unit_map.keys()]

    # Handle P-number addresses
    addr_type_uuid = await get_address_type_uuid(gql_client, "Pnummer")
    for sd_unit in sd_units:
        assert sd_unit.validity is not None

        mo_unit = mo_unit_map[sd_unit.uuid]
        addr = update_or_add_pnumber_address(sd_unit, mo_unit, addr_type_uuid)
        if addr is None:
            continue
        if addr.uuid is None:
            logger.info(
                "Add new address",
                org_unit=str(mo_unit.uuid),
                addr=addr.name,
                addr_type=addr.address_type.user_key,
            )
            if not dry_run:
                return_address = await add_address(
                    gql_client,
                    mo_unit,
                    addr,
                    sd_unit.validity.from_date,
                    sd_unit.validity.to_date,
                )
            else:
                return_address = addr
            yield AddressOperation.ADD, mo_unit, return_address
        else:
            logger.info(
                "Updating address",
                org_unit=str(mo_unit.uuid),
                addr=addr.name,
                addt_type=addr.address_type.user_key,
            )
            if not dry_run:
                await update_address(
                    gql_client, addr, datetime.now(), sd_unit.validity.to_date
                )
            return_address = addr
            yield AddressOperation.UPDATE, mo_unit, return_address

    # Handle postal addresses
    addr_type_uuid = await get_address_type_uuid(gql_client, "AddressMailUnit")
    for sd_unit in sd_units:
        assert sd_unit.validity is not None

        mo_unit = mo_unit_map[sd_unit.uuid]
        addr = await update_or_add_postal_address(
            dar_client, sd_unit, mo_unit, addr_type_uuid
        )
        if addr is None:
            continue
        if addr.uuid is None:
            logger.info(
                "Add new address",
                org_unit=str(mo_unit.uuid),
                addr=addr.name,
                addr_type=addr.address_type.user_key,
            )
            if not dry_run:
                return_address = await add_address(
                    gql_client,
                    mo_unit,
                    addr,
                    sd_unit.validity.from_date,
                    sd_unit.validity.to_date,
                )
            else:
                return_address = addr
            yield AddressOperation.ADD, mo_unit, return_address
        else:
            logger.info(
                "Updating address",
                org_unit=str(mo_unit.uuid),
                addr=addr.name,
                addt_type=addr.address_type.user_key,
            )
            if not dry_run:
                await update_address(
                    gql_client, addr, datetime.now(), sd_unit.validity.to_date
                )
            return_address = addr
            yield AddressOperation.UPDATE, mo_unit, return_address
