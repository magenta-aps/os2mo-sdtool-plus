# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from sdclient.exceptions import SDCallError
from sdclient.requests import GetDepartmentRequest
from sdclient.requests import SDRequest
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from sdtoolplus.sd.importer import get_sd_departments
from sdtoolplus.sd.importer import get_sd_organization


@pytest.mark.parametrize(
    "fetch_postal_addr, fetch_pnumber",
    [
        (False, False),
        (True, False),
        (True, True),
    ],
)
def test_get_sd_departments_calls_client_with_correct_params(
    fetch_postal_addr: bool,
    fetch_pnumber: bool,
) -> None:
    # Arrange
    mock_sd_client = MagicMock()
    activation_date = date(2000, 1, 1)
    deactivation_date = date(2001, 1, 1)

    # Act
    get_sd_departments(
        mock_sd_client,
        "II",
        activation_date,
        deactivation_date,
        fetch_postal_addr,
        fetch_pnumber,
    )

    # Assert
    mock_sd_client.get_department.assert_called_once_with(
        GetDepartmentRequest(
            InstitutionIdentifier="II",
            ActivationDate=activation_date,
            DeactivationDate=deactivation_date,
            DepartmentNameIndicator=True,
            PostalAddressIndicator=fetch_postal_addr,
            ProductionUnitIndicator=fetch_pnumber,
            UUIDIndicator=True,
        )
    )


def test_get_sd_organization_retry_mechanism(
    mock_sd_get_organization_response: GetOrganizationResponse,
) -> None:
    # Arrange
    mock_sd_client = MagicMock()
    mock_sd_client.get_organization = MagicMock(
        side_effect=[
            SDCallError("msg"),
            mock_sd_get_organization_response,
        ]
    )

    # Act
    get_sd_organization(mock_sd_client, "II", date.today(), date.today())

    # Assert
    assert mock_sd_client.get_organization.call_count == 2


def test_get_sd_departments_retry_mechanism(
    mock_sd_get_department_response: GetDepartmentResponse,
) -> None:
    # Arrange
    mock_sd_client = MagicMock()
    mock_sd_client.get_department = MagicMock(
        side_effect=[
            SDCallError("msg"),
            mock_sd_get_department_response,
        ]
    )

    # Act
    get_sd_departments(mock_sd_client, "II", date.today(), date.today())

    # Assert
    assert mock_sd_client.get_department.call_count == 2
