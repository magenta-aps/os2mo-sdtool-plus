# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4

from ramodels.mo import Validity

from sdtoolplus.addresses import _get_unit_address
from sdtoolplus.mo_org_unit_importer import Address
from sdtoolplus.mo_org_unit_importer import AddressType
from sdtoolplus.mo_org_unit_importer import OrgUnitNode


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
