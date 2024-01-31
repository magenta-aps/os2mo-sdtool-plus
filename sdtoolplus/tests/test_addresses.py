# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID
from uuid import uuid4

import pytest
from ramodels.mo import Validity

from sdtoolplus.addresses import _add_addresses_for_new_unit
from sdtoolplus.addresses import _get_unit_address
from sdtoolplus.addresses import AddressCollection
from sdtoolplus.addresses import update_or_add_addresses
from sdtoolplus.mo_org_unit_importer import Address
from sdtoolplus.mo_org_unit_importer import AddressType
from sdtoolplus.mo_org_unit_importer import OrgUnitNode


@pytest.mark.parametrize(
    "addresses",
    [
        [
            Address(
                name="Hovedgaden 1, 1000 Andeby",
                address_type=AddressType(user_key="AddressMailUnit"),
            ),
            Address(name="123456789", address_type=AddressType(user_key="Pnummer")),
        ],
        [],
    ],
)
def test_add_addresses_for_new_unit(
    sd_expected_validity: Validity, addresses: list[Address]
):
    # Arrange
    org_unit_node = OrgUnitNode(
        uuid=uuid4(),
        parent_uuid=uuid4(),
        user_key="dep1",
        parent=None,
        name="Department 1",
        org_unit_level_uuid=uuid4(),
        addresses=addresses,
        validity=sd_expected_validity,
    )

    # Act
    addresses_to_add = _add_addresses_for_new_unit(org_unit_node)

    # Assert
    assert addresses_to_add == addresses


@patch("sdtoolplus.addresses.logger")
def test_get_unit_address_logs_error_for_multiple_addr_types(
    mock_logger: MagicMock, sd_expected_validity: Validity
):
    # Arrange
    addresses = [
        Address(
            name="Hovedgaden 1, 1000 Andeby",
            address_type=AddressType(user_key="AddressMailUnit"),
        ),
        Address(name="123456789", address_type=AddressType(user_key="Pnummer")),
        Address(name="123456789", address_type=AddressType(user_key="Pnummer")),
    ]
    org_unit_uuid = uuid4()

    org_unit_node = OrgUnitNode(
        uuid=org_unit_uuid,
        parent_uuid=uuid4(),
        user_key="dep1",
        parent=None,
        name="Department 1",
        org_unit_level_uuid=uuid4(),
        addresses=addresses,
        validity=sd_expected_validity,
    )

    # Act
    addr = _get_unit_address(org_unit_node, "Pnummer")

    # Assert
    assert addr is None

    mock_logger.error.assert_called_once()
    assert mock_logger.error.call_args_list[0].kwargs["org_unit_uuid"] == str(
        org_unit_uuid
    )


@pytest.mark.parametrize(
    "sd_addresses, mo_addresses, expected",
    [
        # Addresses are identical - nothing should happen
        (
            [
                Address(
                    name="Hovedgaden 1, 1000 Andeby",
                    address_type=AddressType(user_key="AddressMailUnit"),
                ),
                Address(name="123456789", address_type=AddressType(user_key="Pnummer")),
            ],
            [
                Address(
                    uuid=UUID("10000000-0000-0000-0000-000000000000"),
                    name="Hovedgaden 1, 1000 Andeby",
                    address_type=AddressType(user_key="AddressMailUnit"),
                ),
                Address(
                    uuid=UUID("20000000-0000-0000-0000-000000000000"),
                    name="123456789",
                    address_type=AddressType(user_key="Pnummer"),
                ),
            ],
            AddressCollection(
                addresses_to_add=[],
                addresses_to_update=[],
            ),
        ),
        # An SD address has changed - should be changed in MO
        # An SD address is added - should be added to MO
        (
            [
                Address(
                    name="Hovedgaden 2, 2000 Gåserød",
                    address_type=AddressType(user_key="AddressMailUnit"),
                ),
                Address(name="123456789", address_type=AddressType(user_key="Pnummer")),
            ],
            [
                Address(
                    uuid=UUID("10000000-0000-0000-0000-000000000000"),
                    name="Hovedgaden 1, 1000 Andeby",
                    address_type=AddressType(
                        uuid=UUID("11111111-1111-1111-1111-111111111111"),
                        user_key="AddressMailUnit",
                    ),
                )
            ],
            AddressCollection(
                addresses_to_add=[
                    Address(
                        name="123456789",
                        address_type=AddressType(
                            uuid=UUID("22222222-2222-2222-2222-222222222222"),
                            user_key="Pnummer",
                        ),
                    ),
                ],
                addresses_to_update=[
                    Address(
                        uuid=UUID("10000000-0000-0000-0000-000000000000"),
                        name="Hovedgaden 2, 2000 Gåserød",
                        address_type=AddressType(
                            uuid=UUID("11111111-1111-1111-1111-111111111111"),
                            user_key="AddressMailUnit",
                        ),
                    ),
                ],
            ),
        ),
    ],
)
def test_update_or_add_addresses_for_existing_unit(
    sd_expected_validity: Validity,
    sd_addresses: list[Address],
    mo_addresses: list[Address],
    expected: AddressCollection,
):
    # Arrange
    sd_unit = OrgUnitNode(
        uuid=uuid4(),
        parent_uuid=uuid4(),
        user_key="dep1",
        parent=None,
        name="Department 1",
        org_unit_level_uuid=uuid4(),
        addresses=sd_addresses,
        validity=sd_expected_validity,
    )

    mo_unit = OrgUnitNode(
        uuid=uuid4(),
        parent_uuid=uuid4(),
        user_key="dep1",
        parent=None,
        name="Department 1",
        org_unit_level_uuid=uuid4(),
        addresses=mo_addresses,
        validity=sd_expected_validity,
    )

    # Act
    addr_collection = update_or_add_addresses(
        sd_unit,
        mo_unit,
        UUID("11111111-1111-1111-1111-111111111111"),  # Postal addr type
        UUID("22222222-2222-2222-2222-222222222222"),  # P-number addr type
    )

    # Assert
    assert addr_collection == expected


def test_update_or_add_addresses_for_new_unit(sd_expected_validity: Validity):
    # Arrange

    sd_addr1 = Address(
        name="Hovedgaden 1, 1000 Andeby",
        address_type=AddressType(user_key="AddressMailUnit"),
    )
    sd_addr2 = Address(name="123456789", address_type=AddressType(user_key="Pnummer"))
    sd_addresses = [sd_addr1, sd_addr2]

    sd_unit = OrgUnitNode(
        uuid=uuid4(),
        parent_uuid=uuid4(),
        user_key="dep1",
        parent=None,
        name="Department 1",
        org_unit_level_uuid=uuid4(),
        addresses=sd_addresses,
        validity=sd_expected_validity,
    )

    # Act
    addr_collection = update_or_add_addresses(
        sd_unit,
        None,
        UUID("11111111-1111-1111-1111-111111111111"),  # Postal addr type
        UUID("22222222-2222-2222-2222-222222222222"),  # P-number addr type
    )

    # Assert
    assert addr_collection == AddressCollection(
        addresses_to_add=[
            Address(
                name="Hovedgaden 1, 1000 Andeby",
                address_type=AddressType(
                    uuid=UUID("11111111-1111-1111-1111-111111111111"),
                    user_key="AddressMailUnit",
                ),
            ),
            Address(
                name="123456789",
                address_type=AddressType(
                    uuid=UUID("22222222-2222-2222-2222-222222222222"),
                    user_key="Pnummer",
                ),
            ),
        ],
        addresses_to_update=[],
    )
