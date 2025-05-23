# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import os
import uuid
from copy import deepcopy
from datetime import datetime
from itertools import chain
from typing import Any

import pytest
from anytree import Resolver  # type: ignore
from graphql import GraphQLSchema
from graphql import build_schema as build_graphql_schema
from graphql.language.ast import DocumentNode
from pytest import MonkeyPatch
from ramodels.mo import Validity
from sdclient.requests import GetDepartmentParentRequest
from sdclient.responses import DepartmentParent
from sdclient.responses import GetDepartmentParentResponse
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.diff_org_trees import OrgTreeDiff
from sdtoolplus.mo_class import MOClass
from sdtoolplus.mo_class import MOOrgUnitLevelMap
from sdtoolplus.mo_class import MOOrgUnitTypeMap
from sdtoolplus.mo_org_unit_importer import MOOrgTreeImport
from sdtoolplus.mo_org_unit_importer import OrgUnitNode
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.mo_org_unit_importer import OrgUUID
from sdtoolplus.sd.tree import build_tree
from sdtoolplus.tree_diff_executor import TreeDiffExecutor

_TESTING_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "mo.v7.graphql")
_TESTING_MO_VALIDITY = Validity(from_date=datetime.now(), to_date=None)


@pytest.fixture(scope="session")
def graphql_testing_schema() -> GraphQLSchema:
    with open(_TESTING_SCHEMA_PATH) as schema:
        return build_graphql_schema(schema.read())


class SharedIdentifier:
    root_org_uuid: OrgUUID = uuid.UUID("00000000-0000-0000-0000-000000000000")
    child_org_unit_uuid: OrgUnitUUID = uuid.UUID("10000000-0000-0000-0000-000000000000")
    grandchild_org_unit_uuid: OrgUnitUUID = uuid.UUID(
        "20000000-0000-0000-0000-000000000000"
    )


class _MockGraphQLSession:
    def __init__(self, schema: GraphQLSchema):
        self.schema = schema

    expected_children: list[OrgUnitNode] = [
        OrgUnitNode(
            uuid=SharedIdentifier.child_org_unit_uuid,
            parent_uuid=SharedIdentifier.root_org_uuid,
            user_key="child",
            name="Child",
            org_unit_level_uuid=uuid.uuid4(),
            validity=_TESTING_MO_VALIDITY,
        ),
    ]

    expected_grandchildren: list[OrgUnitNode] = [
        OrgUnitNode(
            uuid=SharedIdentifier.grandchild_org_unit_uuid,
            parent_uuid=SharedIdentifier.child_org_unit_uuid,
            user_key="grandchild",
            name="Grandchild",
            org_unit_level_uuid=uuid.uuid4(),
            validity=_TESTING_MO_VALIDITY,
        )
    ]

    def execute(
        self, query: DocumentNode, variable_values: dict[str, Any] | None = None
    ) -> dict:
        definition: dict = query.to_dict()["definitions"][0]
        if definition["name"] is not None:
            # If we are executing a "named" query (== not using DSL), check the query
            # name and return a suitable mock response.
            return self._execute_named_query(definition)
        elif definition["operation"] == "mutation":
            # If we are executing a mutation (== using DSL), check the mutation name and
            # return a suitable mock response.
            return self._execute_mutation(definition)
        else:
            raise ValueError("don't know how to mock response for %r" % query.to_dict())

    def _execute_named_query(self, definition: dict) -> dict:
        # Extract name of GraphQL query, e.g. "Foo" from "query Foo { ... }"
        name: str = definition["name"]["value"]
        if name == "GetOrgUUID":
            return self._mock_response_for_get_org_uuid
        elif name == "GetOrgUnits":
            return self._mock_response_for_get_org_units
        else:
            raise ValueError(
                "don't know how to mock response for named query %r" % name
            )

    def _execute_mutation(self, definition: dict) -> dict:
        # Extract mutation name, e.g. "org_unit_create", "org_unit_update", etc.
        name: str = definition["selection_set"]["selections"][0]["name"]["value"]
        arguments: list[dict] = definition["selection_set"]["selections"][0][
            "arguments"
        ][0]["value"]["fields"]
        for arg in arguments:
            if arg["name"]["value"] == "uuid":
                return {name: {"uuid": arg["value"]["value"]}}
        raise ValueError("could not find org unit UUID in %r" % arguments)

    @property
    def _mock_response_for_get_org_uuid(self) -> dict:
        return {"org": {"uuid": SharedIdentifier.root_org_uuid}}

    @property
    def _mock_response_for_get_org_units(self) -> dict:
        return {
            "org_units": {
                "objects": [
                    {"current": elem} for elem in self.tree_as_flat_list_of_dicts
                ]
            }
        }

    @property
    def expected_trees(self) -> list[OrgUnitNode]:
        children = deepcopy(self.expected_children)
        for child in children:
            child.children = self.expected_grandchildren
        return children

    @property
    def tree_as_flat_list_of_dicts(self) -> list[dict]:
        return [
            {
                "uuid": str(node.uuid),
                "parent_uuid": str(node.parent_uuid),
                "user_key": node.user_key,
                "name": node.name,
                "org_unit_level_uuid": str(node.org_unit_level_uuid),
                "addresses": [
                    {
                        "name": "Grønnegade 2, 1000 Andeby",
                        "uuid": "599ce718-5ba9-48f1-958f-17ed39b13d27",
                        "address_type": {
                            "user_key": "AddressMailUnit",
                            "uuid": "7bd066ea-e8e5-42b1-9211-73562da54b9b",
                        },
                    },
                ],
            }
            for node in chain(self.expected_children, self.expected_grandchildren)
        ]


@pytest.fixture()
def mock_graphql_session(graphql_testing_schema: GraphQLSchema) -> _MockGraphQLSession:
    return _MockGraphQLSession(graphql_testing_schema)


@pytest.fixture()
def mock_sd_get_organization_response() -> GetOrganizationResponse:
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
                "DeactivationDate": "2000-01-01",
                "DepartmentReference": [
                    {
                        "DepartmentIdentifier": "Afd",
                        "DepartmentUUIDIdentifier": "30000000-0000-0000-0000-000000000000",
                        "DepartmentLevelIdentifier": "Afdelings-niveau",
                        "DepartmentReference": [
                            {
                                "DepartmentIdentifier": "NY0",
                                "DepartmentUUIDIdentifier": str(
                                    SharedIdentifier.grandchild_org_unit_uuid
                                ),
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
                    },
                    {
                        "DepartmentIdentifier": "Afd",
                        "DepartmentUUIDIdentifier": "40000000-0000-0000-0000-000000000000",
                        "DepartmentLevelIdentifier": "Afdelings-niveau",
                        "DepartmentReference": [
                            {
                                "DepartmentIdentifier": "NY0",
                                "DepartmentUUIDIdentifier": str(
                                    SharedIdentifier.grandchild_org_unit_uuid
                                ),
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
                                        "DepartmentUUIDIdentifier": str(
                                            SharedIdentifier.child_org_unit_uuid
                                        ),
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


@pytest.fixture()
def mock_sd_get_department_response() -> GetDepartmentResponse:
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
                "DepartmentUUIDIdentifier": str(SharedIdentifier.child_org_unit_uuid),
                "PostalAddress": {
                    "StandardAddressIdentifier": "Baggesensvej 14",
                    "PostalCode": 6000,
                    "DistrictName": "Kolding",
                    "MunicipalityCode": 2000,
                },
                "ProductionUnitIdentifier": 1234567890,
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "dep2",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "Department 2",
                "DepartmentUUIDIdentifier": str(
                    SharedIdentifier.grandchild_org_unit_uuid
                ),
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
        ],
    }
    sd_departments = GetDepartmentResponse.parse_obj(sd_departments_json)
    return sd_departments


@pytest.fixture()
def mock_sd_get_department_response_extra_units() -> GetDepartmentResponse:
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
                "DepartmentUUIDIdentifier": str(SharedIdentifier.child_org_unit_uuid),
                "PostalAddress": {
                    "StandardAddressIdentifier": "Baggesensvej 14",
                    "PostalCode": 6000,
                    "DistrictName": "Kolding",
                    "MunicipalityCode": 2000,
                },
                "ProductionUnitIdentifier": 1234567890,
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "dep2",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "Department 2",
                "DepartmentUUIDIdentifier": str(
                    SharedIdentifier.grandchild_org_unit_uuid
                ),
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
                "DepartmentIdentifier": "dep95",
                "DepartmentLevelIdentifier": "NY1-niveau",
                "DepartmentName": "Department 95",
                "DepartmentUUIDIdentifier": "95000000-0000-0000-0000-000000000000",
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "dep96",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "Department 96",
                "DepartmentUUIDIdentifier": "96000000-0000-0000-0000-000000000000",
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "dep97",
                "DepartmentLevelIdentifier": "Afdelings-niveau",
                "DepartmentName": "Department 97",
                "DepartmentUUIDIdentifier": "97000000-0000-0000-0000-000000000000",
            },
            # SD unit with no parent
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "dep51",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "Department 51",
                "DepartmentUUIDIdentifier": "51000000-0000-0000-0000-000000000000",
            },
            # SD unit with parent, but child does not have parent
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "dep52",
                "DepartmentLevelIdentifier": "NY1-niveau",
                "DepartmentName": "Department 52",
                "DepartmentUUIDIdentifier": "52000000-0000-0000-0000-000000000000",
            },
            # SD unit with no parent, but its parent has a parent
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "dep53",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "Department 53",
                "DepartmentUUIDIdentifier": "53000000-0000-0000-0000-000000000000",
            },
        ],
    }
    sd_departments = GetDepartmentResponse.parse_obj(sd_departments_json)
    return sd_departments


@pytest.fixture()
def mock_sd_get_department_response_date_range_errors() -> GetDepartmentResponse:
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
                "DepartmentUUIDIdentifier": str(SharedIdentifier.child_org_unit_uuid),
                "PostalAddress": {
                    "StandardAddressIdentifier": "Baggesensvej 14",
                    "PostalCode": 6000,
                    "DistrictName": "Kolding",
                    "MunicipalityCode": 2000,
                },
                "ProductionUnitIdentifier": 1234567890,
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "dep2",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "Department 2",
                "DepartmentUUIDIdentifier": str(
                    SharedIdentifier.grandchild_org_unit_uuid
                ),
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
                "ActivationDate": "1997-01-01",  # Extend parents ActivationDates
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "dep6",
                "DepartmentLevelIdentifier": "Afdelings-niveau",
                "DepartmentName": "Department 6",
                "DepartmentUUIDIdentifier": "60000000-0000-0000-0000-000000000000",
            },
        ],
    }
    sd_departments = GetDepartmentResponse.parse_obj(sd_departments_json)
    return sd_departments


@pytest.fixture
def mock_sd_employment_response_dict() -> dict[str, Any]:
    return {
        "Person": [
            {
                "PersonCivilRegistrationIdentifier": "0101011234",
                "Employment": [
                    {
                        "EmploymentIdentifier": "12345",
                        "EmploymentDate": "2000-01-01",
                        "AnniversaryDate": "2000-01-01",
                        "EmploymentDepartment": [
                            {
                                "ActivationDate": "2000-01-01",
                                "DeactivationDate": "9999-12-31",
                                "DepartmentIdentifier": "ABCD",
                                "DepartmentUUIDIdentifier": "fa4a3454-54e6-43b8-92c4-9979bf41a386",
                            }
                        ],
                        "Profession": [
                            {
                                "ActivationDate": "2000-01-01",
                                "DeactivationDate": "2021-12-31",
                                "JobPositionIdentifier": "2",
                                "EmploymentName": "Ninja",
                                "AppointmentCode": "0",
                            },
                            {
                                "ActivationDate": "2022-01-01",
                                "DeactivationDate": "9999-12-31",
                                "JobPositionIdentifier": "4",
                                "EmploymentName": "Kung Fu Master",
                                "AppointmentCode": "0",
                            },
                        ],
                        "EmploymentStatus": [
                            {
                                "ActivationDate": "2000-01-01",
                                "DeactivationDate": "2000-12-31",
                                "EmploymentStatusCode": "0",
                            },
                            {
                                "ActivationDate": "2001-01-01",
                                "DeactivationDate": "2001-12-31",
                                "EmploymentStatusCode": "1",
                            },
                            {
                                "ActivationDate": "2002-01-01",
                                "DeactivationDate": "2002-12-31",
                                "EmploymentStatusCode": "3",
                            },
                            {
                                "ActivationDate": "2003-01-01",
                                "DeactivationDate": "9999-12-31",
                                "EmploymentStatusCode": "8",
                            },
                        ],
                        "WorkingTime": [
                            {
                                "ActivationDate": "2000-01-01",
                                "DeactivationDate": "2021-12-31",
                                "OccupationRate": "1.0000",
                                "SalaryRate": "1.0000",
                                "SalariedIndicator": False,
                                "FullTimeIndicator": True,
                            },
                            {
                                "ActivationDate": "2022-01-01",
                                "DeactivationDate": "9999-12-31",
                                "OccupationRate": "1.0000",
                                "SalaryRate": "1.0000",
                                "SalariedIndicator": True,
                                "FullTimeIndicator": True,
                            },
                        ],
                    }
                ],
            }
        ]
    }


def mock_get_department_parent(
    query_params: GetDepartmentParentRequest,
) -> GetDepartmentParentResponse:
    parent_map = {
        "95000000-0000-0000-0000-000000000000": "10000000-0000-0000-0000-000000000000",
        "96000000-0000-0000-0000-000000000000": "95000000-0000-0000-0000-000000000000",
        "97000000-0000-0000-0000-000000000000": "96000000-0000-0000-0000-000000000000",
        "53000000-0000-0000-0000-000000000000": "52000000-0000-0000-0000-000000000000",
    }

    unit_uuid = query_params.DepartmentUUIDIdentifier
    parent_uuid = parent_map.get(str(unit_uuid))

    if parent_uuid is not None:
        return GetDepartmentParentResponse(
            DepartmentParent=DepartmentParent(
                DepartmentUUIDIdentifier=uuid.UUID(parent_uuid)
            )
        )

    raise ValueError()


@pytest.fixture()
def sd_expected_validity() -> Validity:
    """Construct a `Validity` instance corresponding to the periods indicated by the
    `ActivationDate`/`DeactivationDate` pairs returned by
    `mock_sd_get_organization_response` and `mock_sd_get_department_response`.
    """
    from_dt = datetime.fromisoformat("1999-01-01T00:00:00+01:00")
    to_dt = None
    return Validity(from_date=from_dt, to_date=to_dt)


class _MockGraphQLSessionGetClassesInFacet:
    class_data = [
        {
            "uuid": str(uuid.uuid4()),
            "user_key": str("N%s") % num,
            "name": str("N%s") % num,
        }
        for num in range(2)
    ]

    def execute(self, query: DocumentNode, variable_values: dict) -> dict:
        return {
            "facets": {
                "objects": [{"current": {"classes": [cls for cls in self.class_data]}}]
            }
        }


@pytest.fixture()
def mock_graphql_session_get_classes_in_facet() -> _MockGraphQLSessionGetClassesInFacet:
    return _MockGraphQLSessionGetClassesInFacet()


class MockMOOrgUnitLevelMap(MOOrgUnitLevelMap):
    def __init__(self, department_level_identifiers: list[str]):
        self.classes = [
            MOClass(
                uuid=uuid.uuid4(),
                user_key=department_level_identifier,
                name=department_level_identifier,
            )
            for department_level_identifier in department_level_identifiers
        ]


@pytest.fixture()
def mock_mo_org_unit_level_map(
    mock_sd_get_department_response_extra_units,
) -> MockMOOrgUnitLevelMap:
    valid_dep_level_identifiers: list[str] = [
        dep.DepartmentLevelIdentifier
        for dep in mock_sd_get_department_response_extra_units.Department
    ]
    return MockMOOrgUnitLevelMap(valid_dep_level_identifiers)


@pytest.fixture()
def mock_mo_org_unit_type() -> MOClass:
    return MOClass(uuid=uuid.uuid4(), name="Enhed", user_key="Enhed")


class MockMOOrgUnitTypeMap(MOOrgUnitTypeMap):
    def __init__(self, classes: list[MOClass]):
        self.classes = classes


@pytest.fixture()
def mock_mo_org_unit_type_map(mock_mo_org_unit_type: MOClass) -> MockMOOrgUnitTypeMap:
    return MockMOOrgUnitTypeMap([mock_mo_org_unit_type])


@pytest.fixture()
def mock_mo_org_tree_import(
    mock_graphql_session: _MockGraphQLSession,
) -> MOOrgTreeImport:
    return MOOrgTreeImport(mock_graphql_session)


@pytest.fixture()
def mock_mo_org_tree_import_subtree_case(
    mock_sd_get_organization_response,
    mock_sd_get_department_response,
    mock_mo_org_unit_level_map,
    mock_graphql_session: _MockGraphQLSession,
) -> MOOrgTreeImport:
    # The MO tree
    mo_root = OrgUnitNode(
        uuid=SharedIdentifier.root_org_uuid, name="<root>", user_key="root"
    )
    mo_root_sub = OrgUnitNode(
        uuid=uuid.UUID("11000000-0000-0000-0000-000000000000"),
        name="mo_root_sub",
        user_key="mo_root_sub",
        parent=mo_root,
        children=build_tree(
            mock_sd_get_organization_response,
            mock_sd_get_department_response,
            mock_mo_org_unit_level_map,
        ).children,
    )

    mo_org_tree_import = MOOrgTreeImport(mock_graphql_session)
    mo_org_tree_import._build_trees = lambda org_units: [mo_root_sub]  # type: ignore

    return mo_org_tree_import


@pytest.fixture()
def mock_org_tree_diff(
    mock_graphql_session: _MockGraphQLSession,
    mock_sd_get_organization_response: GetOrganizationResponse,
    mock_sd_get_department_response: GetDepartmentResponse,
    mock_mo_org_unit_level_map: MockMOOrgUnitLevelMap,
    sdtoolplus_settings,
) -> OrgTreeDiff:
    # Construct MO and SD trees
    mo_tree, _ = MOOrgTreeImport(mock_graphql_session).as_single_tree(
        SharedIdentifier.root_org_uuid, "", None
    )
    sd_tree = build_tree(
        mock_sd_get_organization_response,
        mock_sd_get_department_response,
        mock_mo_org_unit_level_map,
    )
    # Construct tree diff
    return OrgTreeDiff(
        mo_tree, sd_tree, mock_mo_org_unit_level_map, sdtoolplus_settings
    )


@pytest.fixture()
def mock_org_tree_diff_move_afd_from_ny_to_ny(
    mock_sd_get_organization_response,
    mock_sd_get_department_response,
    mock_mo_org_unit_level_map,
    mock_mo_org_unit_type,
    sdtoolplus_settings,
) -> OrgTreeDiff:
    """
    OrgTreeDiff instance for the scenario where we move Department 4
    from Department 2 to Department 5 in the tree below:

    <OrgUnitNode: <root> (00000000-0000-0000-0000-000000000000)>
    └── <OrgUnitNode: Department 1 (10000000-0000-0000-0000-000000000000)>
        ├── <OrgUnitNode: Department 2 (20000000-0000-0000-0000-000000000000)>
        │   ├── <OrgUnitNode: Department 3 (30000000-0000-0000-0000-000000000000)>
        │   └── <OrgUnitNode: Department 4 (40000000-0000-0000-0000-000000000000)>
        └── <OrgUnitNode: Department 5 (50000000-0000-0000-0000-000000000000)>
            └── <OrgUnitNode: Department 6 (60000000-0000-0000-0000-000000000000)>
    """

    resolver = Resolver("name")

    mo_tree = build_tree(
        mock_sd_get_organization_response,
        mock_sd_get_department_response,
        mock_mo_org_unit_level_map,
    )
    sd_tree = build_tree(
        mock_sd_get_organization_response,
        mock_sd_get_department_response,
        mock_mo_org_unit_level_map,
    )

    # Move Department 4 to Department 5 in the SD tree, so it differs
    # from the MO tree
    dep4 = resolver.get(sd_tree, "Department 1/Department 2/Department 4")
    dep5 = resolver.get(sd_tree, "Department 1/Department 5")
    dep4.parent = dep5
    # Dangerous: dep4.parent_uuid is now wrong

    org_tree_diff = OrgTreeDiff(
        mo_tree, sd_tree, mock_mo_org_unit_level_map, sdtoolplus_settings
    )
    return org_tree_diff


@pytest.fixture()
def mock_org_tree_diff_move_ny_from_ny_to_ny(
    mock_sd_get_organization_response,
    mock_sd_get_department_response,
    mock_mo_org_unit_level_map,
    mock_mo_org_unit_type,
    sdtoolplus_settings,
    sd_expected_validity,
) -> OrgTreeDiff:
    """
    OrgTreeDiff instance for the scenario where we move Department 5
    from Department 1 to Department 7 in the tree below. I.e. we move
    a NY-level (with subunits) from one NY-level to another NY-level.

    <OrgUnitNode: <root> (00000000-0000-0000-0000-000000000000)>
    ├── <OrgUnitNode: Department 1 (10000000-0000-0000-0000-000000000000)>
    │   ├── <OrgUnitNode: Department 2 (20000000-0000-0000-0000-000000000000)>
    │   │   ├── <OrgUnitNode: Department 3 (30000000-0000-0000-0000-000000000000)>
    │   │   └── <OrgUnitNode: Department 4 (40000000-0000-0000-0000-000000000000)>
    │   └── <OrgUnitNode: Department 5 (50000000-0000-0000-0000-000000000000)>
    │       └── <OrgUnitNode: Department 6 (60000000-0000-0000-0000-000000000000)>
    └── <OrgUnitNode: Department 7 (70000000-0000-0000-0000-000000000000)>
    """

    resolver = Resolver("name")

    mo_tree = build_tree(
        mock_sd_get_organization_response,
        mock_sd_get_department_response,
        mock_mo_org_unit_level_map,
    )
    OrgUnitNode(
        uuid=uuid.UUID("70000000-0000-0000-0000-000000000000"),
        parent_uuid=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        user_key="dep7",
        parent=mo_tree,
        name="Department 7",
        org_unit_level_uuid=mock_mo_org_unit_level_map["Afdelings-niveau"].uuid,
        validity=sd_expected_validity,
    )
    sd_tree = build_tree(
        mock_sd_get_organization_response,
        mock_sd_get_department_response,
        mock_mo_org_unit_level_map,
    )
    sd_dep7 = OrgUnitNode(
        uuid=uuid.UUID("70000000-0000-0000-0000-000000000000"),
        parent_uuid=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        user_key="dep7",
        parent=sd_tree,
        name="Department 7",
        org_unit_level_uuid=mock_mo_org_unit_level_map["Afdelings-niveau"].uuid,
        validity=sd_expected_validity,
    )

    # Move Department 5 to Department 7 in the SD tree, so it differs
    # from the MO tree
    sd_dep5 = resolver.get(sd_tree, "Department 1/Department 5")
    sd_dep5.parent = sd_dep7
    # Dangerous: sd_dep5.parent_uuid is now wrong

    org_tree_diff = OrgTreeDiff(
        mo_tree, sd_tree, mock_mo_org_unit_level_map, sdtoolplus_settings
    )
    return org_tree_diff


@pytest.fixture()
def mock_org_tree_diff_add_and_move_and_rename(
    mock_sd_get_organization_response,
    mock_sd_get_department_response,
    mock_mo_org_unit_level_map,
    mock_mo_org_unit_type,
    sdtoolplus_settings,
    sd_expected_validity,
) -> OrgTreeDiff:
    """
    OrgTreeDiff instance for the scenario where we:
    1) Add Department 7 to the root
    2) Move Department 5 from Department 1 to Department 7
       (i.e. it must be added before Dep 5 can be moved)
    3) Rename Department 5 to Department 8

    The MO tree before any of the operations looks like this:

    <OrgUnitNode: <root> (00000000-0000-0000-0000-000000000000)>
    └── <OrgUnitNode: Department 1 (10000000-0000-0000-0000-000000000000)>
        ├── <OrgUnitNode: Department 2 (20000000-0000-0000-0000-000000000000)>
        │   ├── <OrgUnitNode: Department 3 (30000000-0000-0000-0000-000000000000)>
        │   └── <OrgUnitNode: Department 4 (40000000-0000-0000-0000-000000000000)>
        └── <OrgUnitNode: Department 5 (50000000-0000-0000-0000-000000000000)>
            └── <OrgUnitNode: Department 6 (60000000-0000-0000-0000-000000000000)>

    and the SD tree looks like this:

    <OrgUnitNode: <root> (00000000-0000-0000-0000-000000000000)>
    ├── <OrgUnitNode: Department 1 (10000000-0000-0000-0000-000000000000)>
    │   └── <OrgUnitNode: Department 2 (20000000-0000-0000-0000-000000000000)>
    │       ├── <OrgUnitNode: Department 3 (30000000-0000-0000-0000-000000000000)>
    │       └── <OrgUnitNode: Department 4 (40000000-0000-0000-0000-000000000000)>
    └── <OrgUnitNode: Department 7 (70000000-0000-0000-0000-000000000000)>
        └── <OrgUnitNode: Department 8 (50000000-0000-0000-0000-000000000000)>
            └── <OrgUnitNode: Department 6 (60000000-0000-0000-0000-000000000000)>
    """

    resolver = Resolver("name")

    mo_tree = build_tree(
        mock_sd_get_organization_response,
        mock_sd_get_department_response,
        mock_mo_org_unit_level_map,
    )
    sd_tree = build_tree(
        mock_sd_get_organization_response,
        mock_sd_get_department_response,
        mock_mo_org_unit_level_map,
    )
    sd_dep7 = OrgUnitNode(
        uuid=uuid.UUID("70000000-0000-0000-0000-000000000000"),
        parent_uuid=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        user_key="dep7",
        parent=sd_tree,
        name="Department 7",
        org_unit_level_uuid=mock_mo_org_unit_level_map["NY1-niveau"].uuid,
        validity=sd_expected_validity,
    )

    # Move and rename Department 5 to Department 7 in the SD tree, so it differs
    # from the MO tree
    sd_dep5 = resolver.get(sd_tree, "Department 1/Department 5")
    sd_dep5.parent = None
    sd_dep5_children = sd_dep5.children
    new_sd_dep5 = OrgUnitNode(
        uuid=uuid.UUID("50000000-0000-0000-0000-000000000000"),
        parent_uuid=uuid.UUID("70000000-0000-0000-0000-000000000000"),
        user_key="dep8",
        parent=sd_dep7,
        name="Department 8",
        org_unit_level_uuid=mock_mo_org_unit_level_map["NY0-niveau"].uuid,
        validity=sd_expected_validity,
    )
    new_sd_dep5.children = sd_dep5_children

    org_tree_diff = OrgTreeDiff(
        mo_tree, sd_tree, mock_mo_org_unit_level_map, sdtoolplus_settings
    )
    return org_tree_diff


@pytest.fixture()
def mock_tree_diff_executor(
    mock_graphql_session: _MockGraphQLSession,
    mock_org_tree_diff: OrgTreeDiff,
    mock_mo_org_unit_type: MOClass,
    sdtoolplus_settings: SDToolPlusSettings,
) -> TreeDiffExecutor:
    return TreeDiffExecutor(
        mock_graphql_session,  # type: ignore
        sdtoolplus_settings,
        sdtoolplus_settings.sd_institution_identifier,
        mock_org_tree_diff,
        mock_mo_org_unit_type,
    )


@pytest.fixture()
def expected_units_to_add(
    sd_expected_validity: Validity,
    mock_mo_org_unit_type: MOClass,
    mock_mo_org_unit_level_map: MockMOOrgUnitLevelMap,
) -> list[OrgUnitNode]:
    return [
        # SD units "Department 3" and "Department 4" are added under MO unit "Grandchild"
        OrgUnitNode(
            uuid=uuid.UUID("30000000-0000-0000-0000-000000000000"),
            parent_uuid=SharedIdentifier.grandchild_org_unit_uuid,
            user_key="dep3",
            name="Department 3",
            org_unit_level_uuid=mock_mo_org_unit_level_map["Afdelings-niveau"].uuid,
            validity=sd_expected_validity,
        ),
        OrgUnitNode(
            uuid=uuid.UUID("40000000-0000-0000-0000-000000000000"),
            parent_uuid=SharedIdentifier.grandchild_org_unit_uuid,
            user_key="dep4",
            name="Department 4",
            org_unit_level_uuid=mock_mo_org_unit_level_map["Afdelings-niveau"].uuid,
            validity=sd_expected_validity,
        ),
        # SD unit "Department 5" is added under MO unit "Child"
        OrgUnitNode(
            uuid=uuid.UUID("50000000-0000-0000-0000-000000000000"),
            parent_uuid=SharedIdentifier.child_org_unit_uuid,
            user_key="dep5",
            name="Department 5",
            org_unit_level_uuid=mock_mo_org_unit_level_map["NY0-niveau"].uuid,
            validity=sd_expected_validity,
        ),
        OrgUnitNode(
            uuid=uuid.UUID("60000000-0000-0000-0000-000000000000"),
            parent_uuid=uuid.UUID("50000000-0000-0000-0000-000000000000"),
            user_key="dep6",
            name="Department 6",
            org_unit_level_uuid=mock_mo_org_unit_level_map["NY0-niveau"].uuid,
            validity=sd_expected_validity,
        ),
    ]


@pytest.fixture()
def expected_units_to_update(
    sd_expected_validity: Validity,
    mock_mo_org_unit_type: MOClass,
    mock_mo_org_unit_level_map: MockMOOrgUnitLevelMap,
) -> list[OrgUnitNode]:
    return [
        # MO unit "Grandchild" is renamed to "Department 2"
        # MO unit "Child" is renamed to "Department 1"
        OrgUnitNode(
            uuid=uuid.UUID("10000000-0000-0000-0000-000000000000"),
            parent_uuid=uuid.UUID("10000000-0000-0000-0000-000000000000"),
            user_key="dep1",
            name="Department 1",
            org_unit_level_uuid=mock_mo_org_unit_level_map["NY1-niveau"].uuid,
            validity=sd_expected_validity,
        ),
        OrgUnitNode(
            uuid=uuid.UUID("20000000-0000-0000-0000-000000000000"),
            parent_uuid=uuid.UUID("20000000-0000-0000-0000-000000000000"),
            user_key="dep2",
            name="Department 2",
            org_unit_level_uuid=mock_mo_org_unit_level_map["NY0-niveau"].uuid,
            validity=sd_expected_validity,
        ),
    ]


@pytest.fixture()
def sdtoolplus_settings(monkeypatch: MonkeyPatch) -> SDToolPlusSettings:
    monkeypatch.setenv("FASTRAMQPI__CLIENT_ID", "unused")
    monkeypatch.setenv("FASTRAMQPI__CLIENT_SECRET", "unused")
    monkeypatch.setenv("FASTRAMQPI__AMQP__URL", "amqp://unused")
    monkeypatch.setenv("SD_USERNAME", "sd_username")
    monkeypatch.setenv("SD_INSTITUTION_IDENTIFIER", "sd_institution_identifier")
    monkeypatch.setenv("SD_PASSWORD", "")
    monkeypatch.setenv("DB_PASSWORD", "secret")
    monkeypatch.setenv("MO_SUBTREE_PATH_FOR_ROOT", "[]")
    monkeypatch.setenv("OBSOLETE_UNIT_ROOTS", f'["{uuid.uuid4()}"]')
    return SDToolPlusSettings()


@pytest.fixture()
def random_org_unit_node(sd_expected_validity) -> OrgUnitNode:
    return OrgUnitNode(
        uuid=uuid.UUID("10000000-0000-0000-0000-000000000000"),
        parent_uuid=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        user_key="dep",
        name="Department",
        org_unit_level_uuid=uuid.uuid4(),
        validity=sd_expected_validity,
    )
