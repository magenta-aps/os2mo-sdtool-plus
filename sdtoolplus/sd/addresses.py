# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from sdclient.responses import Department

from sdtoolplus.mo_org_unit_importer import Address
from sdtoolplus.mo_org_unit_importer import AddressType
from sdtoolplus.models import AddressTypeUserKey


def get_addresses(sd_department: Department) -> list[Address]:
    dep_addr = sd_department.PostalAddress
    dep_prod_unit_id = sd_department.ProductionUnitIdentifier

    # TODO: put magic values into constant
    addresses = []
    # TODO: test missing for the latter part of this expression
    if dep_addr is not None and None not in (
        dep_addr.StandardAddressIdentifier,
        dep_addr.PostalCode,
        dep_addr.DistrictName,
    ):
        addresses.append(
            Address(
                name=f"{dep_addr.StandardAddressIdentifier}, {dep_addr.PostalCode} {dep_addr.DistrictName}",
                address_type=AddressType(user_key=AddressTypeUserKey.POSTAL_ADDR.value),
            )
        )
    if dep_prod_unit_id is not None:
        addresses.append(
            Address(
                name=str(dep_prod_unit_id),
                address_type=AddressType(
                    user_key=AddressTypeUserKey.PNUMBER_ADDR.value
                ),
            )
        )

    return addresses
