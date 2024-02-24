# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from enum import Enum
from functools import partial
from typing import AsyncIterator
from typing import Awaitable
from typing import Callable
from typing import TypeAlias
from uuid import UUID

import structlog
from more_itertools import only
from os2mo_dar_client import AsyncDARClient
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
from sdtoolplus.models import AddressTypeUserKey
from sdtoolplus.sd.importer import get_sd_units

DARAddressUUID: TypeAlias = UUID

logger = structlog.get_logger()


class AddressOperation(Enum):
    ADD = "add"
    UPDATE = "update"


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


async def _update_or_add_addresses(
    gql_client: GraphQLClient,
    sd_units: list[OrgUnitNode],
    mo_unit_map: dict[OrgUnitUUID, OrgUnitNode],
    address_type: str,
    update_or_add_coro: Callable[
        [OrgUnitNode, OrgUnitNode, AddressTypeUUID], Awaitable[Address | None]
    ],
    dry_run: bool,
) -> AsyncIterator[tuple[AddressOperation, OrgUnitNode, Address]]:
    # TODO: docstring

    addr_type_uuid = await get_address_type_uuid(gql_client, address_type)
    for sd_unit in sd_units:
        assert sd_unit.validity is not None

        mo_unit = mo_unit_map[sd_unit.uuid]
        addr = await update_or_add_coro(sd_unit, mo_unit, addr_type_uuid)
        if addr is None:
            continue
        if addr.uuid is None:
            logger.info(
                "Add new address",
                org_unit=str(mo_unit.uuid),
                value=addr.value,
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
                value=addr.value,
                addt_type=addr.address_type.user_key,
            )
            if not dry_run:
                await update_address(
                    gql_client, addr, datetime.now(), sd_unit.validity.to_date
                )
            return_address = addr
            yield AddressOperation.UPDATE, mo_unit, return_address


async def _update_or_add_pnumber_address(
    sd_unit: OrgUnitNode,
    mo_unit: OrgUnitNode,
    pnumber_addr_type_uuid: AddressTypeUUID,
) -> Address | None:
    # TODO: docstring

    sd_addr = _get_unit_address(sd_unit, AddressTypeUserKey.PNUMBER_ADDR.value)
    if sd_addr is None:
        return None

    mo_addr = _get_unit_address(mo_unit, AddressTypeUserKey.PNUMBER_ADDR.value)

    if mo_addr is None:
        return Address(
            value=sd_addr.name,
            address_type=AddressType(
                user_key=sd_addr.address_type.user_key, uuid=pnumber_addr_type_uuid
            ),
        )

    if not sd_addr.name == mo_addr.value:
        return Address(
            uuid=mo_addr.uuid,  # If set, we know that we are updating and not creating
            value=sd_addr.name,
            address_type=mo_addr.address_type,
        )
    return None


async def _get_dar_addr_uuid(
    dar_client: AsyncDARClient, addr: Address
) -> DARAddressUUID:
    async with dar_client:
        r = await dar_client.cleanse_single(addr.name)
        # logger.debug("DAR lookup", respos)
        return DARAddressUUID(r["id"])


async def _update_or_add_postal_address(
    dar_client: AsyncDARClient,
    sd_unit: OrgUnitNode,
    mo_unit: OrgUnitNode,
    postal_addr_type_uuid: AddressTypeUUID,
) -> Address | None:
    # TODO: add docstring

    sd_addr = _get_unit_address(sd_unit, AddressTypeUserKey.POSTAL_ADDR.value)
    if sd_addr is None:
        return None

    mo_addr = _get_unit_address(mo_unit, AddressTypeUserKey.POSTAL_ADDR.value)
    if mo_addr is None:
        logger.debug(
            "Create new address",
            addr=sd_addr.name,
            org_unit_name=mo_unit.name,
            org_unit_uuid=str(mo_unit.uuid),
        )
        try:
            # Create a new address
            dar_uuid = await _get_dar_addr_uuid(dar_client, sd_addr)
            return Address(
                value=str(dar_uuid),
                address_type=AddressType(
                    user_key=AddressTypeUserKey.POSTAL_ADDR.value,
                    uuid=postal_addr_type_uuid,
                ),
            )
        except:
            logger.error("Could not get address UUID from DAR!")
            return None

    # Update existing address
    if not sd_addr.name == mo_addr.name:
        # If the postal address string do not match, we have to perform a
        # DAR lookup and compare the address UUIDs. We only do the DAR lookup
        # when necessary due to performance. If the address string match,
        # there is no need to perform a DAR UUID lookup.

        logger.debug(
            "Update address",
            sd_addr=sd_addr.name,
            mo_addr=mo_addr.name,
            org_unit_name=mo_unit.name,
            org_unit_uuid=str(mo_unit.uuid),
        )

        try:
            # Get DAR address UUID
            dar_uuid = await _get_dar_addr_uuid(dar_client, sd_addr)
            if not str(dar_uuid) == mo_addr.value:
                return Address(
                    uuid=mo_addr.uuid,  # If set, we know that we are updating and not creating
                    value=str(dar_uuid),
                    address_type=AddressType(
                        user_key=AddressTypeUserKey.POSTAL_ADDR.value,
                        uuid=postal_addr_type_uuid,
                    ),
                )
        except:
            logger.error("Could not get address UUID from DAR!")
            return None

    return None


class AddressFixer:
    def __init__(
        self,
        gql_client: GraphQLClient,
        sd_client: SDClient,
        dar_client: AsyncDARClient,
        settings: SDToolPlusSettings,
    ):
        self.gql_client = gql_client
        self.sd_client = sd_client
        self.dar_client = dar_client
        self.settings = settings

    async def fix_addresses(
        self,
        org_unit: OrgUnitUUID | None,
        dry_run: bool,
    ):
        logger.info("Add or update addresses")

        # TODO: use auto-generated client instead
        persistent_client = get_graphql_client(self.settings)

        # Get the SD units
        logger.info("Getting SD units...")
        sd_units = get_sd_units(self.sd_client, self.settings.sd_institution_identifier)

        # Get the MO units
        logger.info("Getting MO units...")
        mo_org_tree_import = MOOrgTreeImport(persistent_client)
        mo_org_units = mo_org_tree_import.get_org_units(org_unit)

        mo_units = [OrgUnitNode.from_org_unit(org_unit) for org_unit in mo_org_units]
        mo_units = filter_by_uuid(org_unit, mo_units)
        mo_units = remove_by_name(self.settings.regex_unit_names_to_remove, mo_units)

        mo_unit_map: dict[OrgUnitUUID, OrgUnitNode] = {
            mo_unit.uuid: mo_unit for mo_unit in mo_units
        }

        # Only fix units that are already in MO
        sd_units = [
            sd_unit for sd_unit in sd_units if sd_unit.uuid in mo_unit_map.keys()
        ]

        # Handle P-number addresses
        async for operation, org_unit_node, addr in _update_or_add_addresses(
            self.gql_client,
            sd_units,
            mo_unit_map,
            AddressTypeUserKey.PNUMBER_ADDR.value,
            _update_or_add_pnumber_address,
            dry_run,
        ):
            yield operation, org_unit_node, addr

        # Handle postal addresses
        async for operation, org_unit_node, addr in _update_or_add_addresses(
            self.gql_client,
            sd_units,
            mo_unit_map,
            AddressTypeUserKey.POSTAL_ADDR.value,
            partial(_update_or_add_postal_address, self.dar_client),
            dry_run,
        ):
            yield operation, org_unit_node, addr
