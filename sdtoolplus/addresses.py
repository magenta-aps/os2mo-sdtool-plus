# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import structlog
from more_itertools import only
from pydantic import BaseModel

from sdtoolplus.mo_org_unit_importer import Address
from sdtoolplus.mo_org_unit_importer import AddressType
from sdtoolplus.mo_org_unit_importer import AddressTypeUUID
from sdtoolplus.mo_org_unit_importer import OrgUnitNode


logger = structlog.get_logger()


class AddressCollection(BaseModel):
    addresses_to_add: list[Address]
    addresses_to_update: list[Address]


def _get_unit_address(org_unit_node: OrgUnitNode, address_type: str) -> Address | None:
    # TODO: add docstring
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
