# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from fastramqpi.pytest_util import retry
from httpx import Response
from more_itertools import one
from respx import MockRouter
from sdclient.responses import Department
from sdclient.responses import DepartmentReference
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from sdtoolplus.autogenerated_graphql_client import GraphQLClient
from sdtoolplus.tests.conftest import SharedIdentifier


@pytest.mark.integration_test
@patch("sdtoolplus.main.get_engine")
@patch("sdtoolplus.sd.importer.get_sd_departments")
@patch("sdtoolplus.sd.importer.get_sd_organization")
@patch("sdtoolplus.main.run_db_end_operations")
@patch("sdtoolplus.main.run_db_start_operations", return_value=None)
async def test_two_new_departments_in_sd(
    mock_run_db_start_operations: MagicMock,
    mock_run_db_end_operations: MagicMock,
    mock_get_sd_organization: MagicMock,
    mock_get_sd_departments: MagicMock,
    mock_get_engine: MagicMock,
    test_client: TestClient,
    graphql_client: GraphQLClient,
    base_tree_builder: None,
    mock_sd_get_organization_response: GetOrganizationResponse,
    mock_sd_get_department_response: GetDepartmentResponse,
    respx_mock: MockRouter,
) -> None:
    """
    Two new units, Department 7 and Department 8, are added to the root of the
    SD tree
    """

    # Arrange
    org_uuid = (await graphql_client.get_organization()).uuid
    mock_sd_get_organization_response.InstitutionUUIDIdentifier = org_uuid

    get_org_dep7_and_dep8 = {
        "DepartmentIdentifier": "Afd",
        "DepartmentUUIDIdentifier": "80000000-0000-0000-0000-000000000000",
        "DepartmentLevelIdentifier": "Afdelings-niveau",
        "DepartmentReference": [
            {
                "DepartmentIdentifier": "NY0",
                "DepartmentUUIDIdentifier": "70000000-0000-0000-0000-000000000000",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentReference": [
                    {
                        "DepartmentIdentifier": "NY1",
                        "DepartmentUUIDIdentifier": str(
                            SharedIdentifier.child_org_unit_uuid
                        ),
                        "DepartmentLevelIdentifier": "NY1-niveau",
                    }
                ],
            }
        ],
    }
    mock_sd_get_organization_response.Organization[0].DepartmentReference.append(
        DepartmentReference.parse_obj(get_org_dep7_and_dep8)
    )

    get_dep_dep7_and_dep8 = [
        {
            "ActivationDate": "1999-01-01",
            "DeactivationDate": "9999-12-31",
            "DepartmentIdentifier": "dep7",
            "DepartmentLevelIdentifier": "NY0-niveau",
            "DepartmentName": "Department 7",
            "DepartmentUUIDIdentifier": "70000000-0000-0000-0000-000000000000",
        },
        {
            "ActivationDate": "1999-01-01",
            "DeactivationDate": "9999-12-31",
            "DepartmentIdentifier": "dep8",
            "DepartmentLevelIdentifier": "Afdelings-niveau",
            "DepartmentName": "Department 8",
            "DepartmentUUIDIdentifier": "80000000-0000-0000-0000-000000000000",
        },
    ]
    mock_sd_get_department_response.Department.extend(
        [Department.parse_obj(dep) for dep in get_dep_dep7_and_dep8]
    )

    mock_get_sd_organization.return_value = mock_sd_get_organization_response
    mock_get_sd_departments.return_value = mock_sd_get_department_response

    respx_mock.post(
        "http://sdlon:8000/trigger/apply-ny-logic/70000000-0000-0000-0000-000000000000"
    ).mock(return_value=Response(200))
    respx_mock.post(
        "http://sdlon:8000/trigger/apply-ny-logic/80000000-0000-0000-0000-000000000000"
    ).mock(return_value=Response(200))

    # Act
    test_client.post("/trigger")

    # Assert
    @retry()
    async def verify() -> None:
        # Verify Department 7 is correct
        dep7 = await graphql_client._testing__get_org_unit(
            UUID("70000000-0000-0000-0000-000000000000")
        )
        current = one(dep7.objects).current
        assert current is not None
        assert current.uuid == UUID("70000000-0000-0000-0000-000000000000")
        assert current.user_key == "dep7"
        assert current.name == "Department 7"
        assert current.validity.from_ == datetime(
            1999, 1, 1, tzinfo=ZoneInfo("Europe/Copenhagen")
        )
        assert current.validity.to is None
        assert current.org_unit_level.name == "NY0-niveau"  # type: ignore
        assert current.parent.uuid == UUID("10000000-0000-0000-0000-000000000000")  # type: ignore

        # Verify Department 8 is correct
        dep7 = await graphql_client._testing__get_org_unit(
            UUID("80000000-0000-0000-0000-000000000000")
        )
        current = one(dep7.objects).current
        assert current is not None
        assert current.uuid == UUID("80000000-0000-0000-0000-000000000000")
        assert current.user_key == "dep8"
        assert current.name == "Department 8"
        assert current.validity.from_ == datetime(
            1999, 1, 1, tzinfo=ZoneInfo("Europe/Copenhagen")
        )
        assert current.validity.to is None
        assert current.org_unit_level.name == "Afdelings-niveau"  # type: ignore
        assert current.parent.uuid == UUID("70000000-0000-0000-0000-000000000000")  # type: ignore

    await verify()
