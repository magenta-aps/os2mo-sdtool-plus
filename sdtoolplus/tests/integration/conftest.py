# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from uuid import UUID
from uuid import uuid4

import pytest
from more_itertools import one
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from sdtoolplus.autogenerated_graphql_client import GraphQLClient
from sdtoolplus.tests.conftest import SharedIdentifier


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
            await graphql_client._testing__get_facet_class(
                "engagement_job_function", "Ninja"
            )
        ).objects  # type: ignore
    ).current.uuid


@pytest.fixture
async def engagement_type(graphql_client: GraphQLClient) -> UUID:
    return one(
        (
            await graphql_client._testing__get_facet_class(
                "engagement_type", "TestAnsat"
            )
        ).objects  # type: ignore
    ).current.uuid