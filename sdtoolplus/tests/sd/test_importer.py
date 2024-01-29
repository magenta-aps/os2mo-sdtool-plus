# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from unittest.mock import MagicMock

from sdclient.requests import GetDepartmentRequest

from sdtoolplus.sd.importer import get_sd_departments


def test_get_sd_departments_calls_client_with_correct_params() -> None:
    # Arrange
    mock_sd_client = MagicMock()
    activation_date = date(2000, 1, 1)
    deactivation_date = date(2001, 1, 1)

    # Act
    get_sd_departments(
        mock_sd_client,
        "II",
        activation_date,
        deactivation_date
    )

    # Assert
    mock_sd_client.get_department.assert_called_once_with(
        GetDepartmentRequest(
            InstitutionIdentifier="II",
            ActivationDate=activation_date,
            DeactivationDate=deactivation_date,
            DepartmentNameIndicator=True,
            PostalAddressIndicator=True,
            ProductionUnitIndicator=True,
            UUIDIndicator=True,
        )
    )
