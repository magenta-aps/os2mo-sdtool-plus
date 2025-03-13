# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from uuid import UUID
from uuid import uuid4

import pytest
from more_itertools import one
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from sdtoolplus.autogenerated_graphql_client import GraphQLClient
from tests.conftest import SharedIdentifier


@pytest.fixture
def sd_get_org_with_2_in_obsolete() -> GetOrganizationResponse:
    sd_org_json = {
        "RegionIdentifier": "RI",
        "InstitutionIdentifier": "II",
        "InstitutionUUIDIdentifier": str(SharedIdentifier.root_org_uuid),
        "DepartmentStructureName": "Dep structure name",
        "OrganizationStructure": {
            "DepartmentLevelIdentifier": "Afdelings-niveau",
            "DepartmentLevelReference": {
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentLevelReference": {"DepartmentLevelIdentifier": "NY1-niveau"},
            },
        },
        "Organization": [
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentReference": [
                    {
                        "DepartmentIdentifier": "Afd",
                        "DepartmentUUIDIdentifier": "30000000-0000-0000-0000-000000000000",
                        "DepartmentLevelIdentifier": "Afdelings-niveau",
                        "DepartmentReference": [
                            {
                                "DepartmentIdentifier": "NY0",
                                "DepartmentUUIDIdentifier": "20000000-0000-0000-0000-000000000000",
                                "DepartmentLevelIdentifier": "NY0-niveau",
                                "DepartmentReference": [
                                    {
                                        "DepartmentIdentifier": "NY1",
                                        "DepartmentUUIDIdentifier": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                                        "DepartmentLevelIdentifier": "NY1-niveau",
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "DepartmentIdentifier": "Afd",
                        "DepartmentUUIDIdentifier": "40000000-0000-0000-0000-000000000000",
                        "DepartmentLevelIdentifier": "Afdelings-niveau",
                        "DepartmentReference": [
                            {
                                "DepartmentIdentifier": "NY0",
                                "DepartmentUUIDIdentifier": "20000000-0000-0000-0000-000000000000",
                                "DepartmentLevelIdentifier": "NY0-niveau",
                                "DepartmentReference": [
                                    {
                                        "DepartmentIdentifier": "NY1",
                                        "DepartmentUUIDIdentifier": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                                        "DepartmentLevelIdentifier": "NY1-niveau",
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "DepartmentIdentifier": "Afd",
                        "DepartmentUUIDIdentifier": "60000000-0000-0000-0000-000000000000",
                        "DepartmentLevelIdentifier": "Afdelings-niveau",
                        "DepartmentReference": [
                            {
                                "DepartmentIdentifier": "NY0",
                                "DepartmentUUIDIdentifier": "50000000-0000-0000-0000-000000000000",
                                "DepartmentLevelIdentifier": "NY0-niveau",
                                "DepartmentReference": [
                                    {
                                        "DepartmentIdentifier": "NY1",
                                        "DepartmentUUIDIdentifier": "10000000-0000-0000-0000-000000000000",
                                        "DepartmentLevelIdentifier": "NY1-niveau",
                                    }
                                ],
                            }
                        ],
                    },
                ],
            }
        ],
    }
    sd_org = GetOrganizationResponse.parse_obj(sd_org_json)
    return sd_org


@pytest.fixture
def sd_get_org_with_3_in_obsolete() -> GetOrganizationResponse:
    sd_org_json = {
        "RegionIdentifier": "RI",
        "InstitutionIdentifier": "II",
        "InstitutionUUIDIdentifier": str(SharedIdentifier.root_org_uuid),
        "DepartmentStructureName": "Dep structure name",
        "OrganizationStructure": {
            "DepartmentLevelIdentifier": "Afdelings-niveau",
            "DepartmentLevelReference": {
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentLevelReference": {"DepartmentLevelIdentifier": "NY1-niveau"},
            },
        },
        "Organization": [
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentReference": [
                    {
                        "DepartmentIdentifier": "Afd",
                        "DepartmentUUIDIdentifier": "30000000-0000-0000-0000-000000000000",
                        "DepartmentLevelIdentifier": "Afdelings-niveau",
                        "DepartmentReference": [
                            {
                                "DepartmentIdentifier": "NY1",
                                "DepartmentUUIDIdentifier": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                                "DepartmentLevelIdentifier": "NY1-niveau",
                            }
                        ],
                    },
                    {
                        "DepartmentIdentifier": "Afd",
                        "DepartmentUUIDIdentifier": "40000000-0000-0000-0000-000000000000",
                        "DepartmentLevelIdentifier": "Afdelings-niveau",
                        "DepartmentReference": [
                            {
                                "DepartmentIdentifier": "NY0",
                                "DepartmentUUIDIdentifier": "20000000-0000-0000-0000-000000000000",
                                "DepartmentLevelIdentifier": "NY0-niveau",
                                "DepartmentReference": [
                                    {
                                        "DepartmentIdentifier": "NY1",
                                        "DepartmentUUIDIdentifier": "10000000-0000-0000-0000-000000000000",
                                        "DepartmentLevelIdentifier": "NY1-niveau",
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "DepartmentIdentifier": "Afd",
                        "DepartmentUUIDIdentifier": "60000000-0000-0000-0000-000000000000",
                        "DepartmentLevelIdentifier": "Afdelings-niveau",
                        "DepartmentReference": [
                            {
                                "DepartmentIdentifier": "NY0",
                                "DepartmentUUIDIdentifier": "50000000-0000-0000-0000-000000000000",
                                "DepartmentLevelIdentifier": "NY0-niveau",
                                "DepartmentReference": [
                                    {
                                        "DepartmentIdentifier": "NY1",
                                        "DepartmentUUIDIdentifier": "10000000-0000-0000-0000-000000000000",
                                        "DepartmentLevelIdentifier": "NY1-niveau",
                                    }
                                ],
                            }
                        ],
                    },
                ],
            }
        ],
    }
    sd_org = GetOrganizationResponse.parse_obj(sd_org_json)
    return sd_org


@pytest.fixture
def sd_get_dep_with_obsolete() -> GetDepartmentResponse:
    sd_departments_json = {
        "RegionIdentifier": "RI",
        "InstitutionIdentifier": "II",
        "Department": [
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "dep1",
                "DepartmentLevelIdentifier": "NY1-niveau",
                "DepartmentName": "Department 1",
                "DepartmentUUIDIdentifier": "10000000-0000-0000-0000-000000000000",
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "dep2",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "Department 2",
                "DepartmentUUIDIdentifier": "20000000-0000-0000-0000-000000000000",
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "dep3",
                "DepartmentLevelIdentifier": "Afdelings-niveau",
                "DepartmentName": "Department 3",
                "DepartmentUUIDIdentifier": "30000000-0000-0000-0000-000000000000",
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "dep4",
                "DepartmentLevelIdentifier": "Afdelings-niveau",
                "DepartmentName": "Department 4",
                "DepartmentUUIDIdentifier": "40000000-0000-0000-0000-000000000000",
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "dep5",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "Department 5",
                "DepartmentUUIDIdentifier": "50000000-0000-0000-0000-000000000000",
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "dep6",
                "DepartmentLevelIdentifier": "Afdelings-niveau",
                "DepartmentName": "Department 6",
                "DepartmentUUIDIdentifier": "60000000-0000-0000-0000-000000000000",
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "udgåede afdelinger",
                "DepartmentLevelIdentifier": "NY1-niveau",
                "DepartmentName": "Udgåede afdelinger",
                "DepartmentUUIDIdentifier": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            },
        ],
    }
    sd_departments = GetDepartmentResponse.parse_obj(sd_departments_json)
    return sd_departments


@pytest.fixture
async def bruce_lee(graphql_client: GraphQLClient) -> UUID:
    r = await graphql_client._testing__create_employee(uuid4(), "Bruce", "Lee")
    return r.uuid


@pytest.fixture
async def job_function(graphql_client: GraphQLClient) -> UUID:
    return one(
        (
            await graphql_client.get_facet_class("engagement_job_function", "Ninja")
        ).objects  # type: ignore
    ).current.uuid


@pytest.fixture
async def engagement_type(graphql_client: GraphQLClient) -> UUID:
    return one(
        (await graphql_client.get_facet_class("engagement_type", "TestAnsat")).objects  # type: ignore
    ).current.uuid


def get_department_response_for_date_range_error(
    department_number: str,
    earliest_start_date: date,
) -> str:
    """
    Generate the GetDepartment response for the date range error integration
    test sdtoolplus.tests.integration.test_tree_structure.test_build_tree_date_range_errors

    Args:
        department_number: the SD department number
        earliest_start_date: the earliest department start date in the SD response
    """

    # Simple asserts to make sure the string is consistent - we are not trying
    # make a generel and more complex solution here!
    assert int(department_number) > 0
    assert date(1950, 1, 1) < earliest_start_date < date(1998, 5, 31)

    dep_id = f"dep{department_number}"
    dep_uuid = f"{department_number}0000000-0000-0000-0000-000000000000"
    dep_name = f"Department {department_number}"

    response = '<?xml version="1.0" encoding="UTF-8" ?>'
    '<GetDepartment20111201 creationDateTime="2024-04-22T10:05:14" >'
    "  <RequestStructure>"
    "    <InstitutionIdentifier>XY</InstitutionIdentifier>"
    "    <DepartmentUUIDIdentifier>50000000-0000-0000-0000-000000000000</DepartmentUUIDIdentifier>"
    "    <ActivationDate>1930-01-01</ActivationDate>"
    "    <DeactivationDate>2024-04-22</DeactivationDate>"
    "    <ContactInformationIndicator>false</ContactInformationIndicator>"
    "    <DepartmentNameIndicator>true</DepartmentNameIndicator>"
    "    <EmploymentDepartmentIndicator>false</EmploymentDepartmentIndicator>"
    "    <PostalAddressIndicator>false</PostalAddressIndicator>"
    "    <ProductionUnitIndicator>false</ProductionUnitIndicator>"
    "    <UUIDIndicator>true</UUIDIndicator>"
    "  </RequestStructure>"
    "  <RegionIdentifier>RI</RegionIdentifier>"
    "  <RegionUUIDIdentifier>4b80fcea-c23f-4d3c-82fd-69c0b180c62d</RegionUUIDIdentifier>"
    "  <InstitutionIdentifier>II</InstitutionIdentifier>"
    "  <InstitutionUUIDIdentifier>3db34422-91bd-4580-975c-ea240adb5dd9</InstitutionUUIDIdentifier>"
    "  <Department>"
    f"    <ActivationDate>{earliest_start_date.strftime('%y-%m-%d')}</ActivationDate>"
    "    <DeactivationDate>1998-05-31</DeactivationDate>"
    f"    <DepartmentIdentifier>{dep_id}</DepartmentIdentifier>"
    f"    <DepartmentUUIDIdentifier>{dep_uuid}</DepartmentUUIDIdentifier>"
    "    <DepartmentLevelIdentifier>NY0-niveau</DepartmentLevelIdentifier>"
    f"    <DepartmentName>Department{department_number}</DepartmentName>"
    "  </Department>"
    "  <Department>"
    "    <ActivationDate>1998-06-01</ActivationDate>"
    "    <DeactivationDate>9999-12-31</DeactivationDate>"
    f"    <DepartmentIdentifier>{dep_id}</DepartmentIdentifier>"
    f"    <DepartmentUUIDIdentifier>{dep_uuid}</DepartmentUUIDIdentifier>"
    "    <DepartmentLevelIdentifier>NY0-niveau</DepartmentLevelIdentifier>"
    f"    <DepartmentName>{dep_name}</DepartmentName>"
    "  </Department>"
    "</GetDepartment20111201>"

    return response


@pytest.fixture
def sd_parent_history_resp() -> list[dict[str, str]]:
    return [
        {
            "startDate": "2001-01-01",
            "endDate": "2002-12-31",
            "parentUuid": "30000000-0000-0000-0000-000000000000",
        },
        {
            "startDate": "2003-01-01",
            "endDate": "2006-12-31",
            "parentUuid": "40000000-0000-0000-0000-000000000000",
        },
    ]
