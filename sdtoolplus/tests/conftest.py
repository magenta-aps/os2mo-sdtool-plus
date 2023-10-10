# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import os
import uuid
from copy import deepcopy
from datetime import datetime
from itertools import chain
from typing import Any

import pytest
from gql.transport.exceptions import TransportQueryError
from graphql import build_schema as build_graphql_schema
from graphql import GraphQLSchema
from graphql.language.ast import DocumentNode
from ramodels.mo import Validity
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from ..diff_org_trees import OrgTreeDiff
from ..mo_class import MOClass
from ..mo_class import MOOrgUnitLevelMap
from ..mo_class import MOOrgUnitTypeMap
from ..mo_org_unit_importer import MOOrgTreeImport
from ..mo_org_unit_importer import OrgUnitNode
from ..mo_org_unit_importer import OrgUnitUUID
from ..mo_org_unit_importer import OrgUUID
from ..sd.tree import build_tree


_TESTING_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "mo.v7.graphql")
_TESTING_MO_VALIDITY = Validity(from_date=datetime.now(), to_date=None)


@pytest.fixture(scope="session")
def graphql_testing_schema() -> GraphQLSchema:
    with open(_TESTING_SCHEMA_PATH) as schema:
        return build_graphql_schema(schema.read())


class SharedIdentifier:
    root_org_uuid: OrgUUID = uuid.uuid4()
    child_org_unit_uuid: OrgUnitUUID = uuid.uuid4()
    grandchild_org_unit_uuid: OrgUnitUUID = uuid.uuid4()
    removed_org_unit_uuid: OrgUnitUUID = uuid.uuid4()


class _MockGraphQLSession:
    def __init__(self, schema: GraphQLSchema):
        self.schema = schema

    expected_children: list[OrgUnitNode] = [
        OrgUnitNode(
            uuid=SharedIdentifier.child_org_unit_uuid,
            parent_uuid=SharedIdentifier.root_org_uuid,
            name="Child",
            org_unit_level_uuid=uuid.uuid4(),
            validity=_TESTING_MO_VALIDITY,
        ),
        OrgUnitNode(
            uuid=SharedIdentifier.removed_org_unit_uuid,
            parent_uuid=SharedIdentifier.root_org_uuid,
            name="Child only in MO, should be removed",
            org_unit_level_uuid=uuid.uuid4(),
            validity=_TESTING_MO_VALIDITY,
        ),
    ]

    expected_grandchildren: list[OrgUnitNode] = [
        OrgUnitNode(
            uuid=SharedIdentifier.grandchild_org_unit_uuid,
            parent_uuid=SharedIdentifier.child_org_unit_uuid,
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
        if name == "org_unit_create":
            # Pretend we have created a new org unit, and return a new UUID
            return {name: {"uuid": str(uuid.uuid4())}}
        elif name == "org_unit_update":
            # Pretend we have updated an existing org unit, and returns its original
            # UUID.
            arguments: list[dict] = definition["selection_set"]["selections"][0][
                "arguments"
            ][0]["value"]["fields"]
            for arg in arguments:
                if arg["name"]["value"] == "uuid":
                    return {name: {"uuid": arg["value"]["value"]}}
            raise ValueError("could not find org unit UUID in %r" % arguments)
        else:
            raise ValueError("don't know how to mock response for mutation %r" % name)

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
                "name": node.name,
                "org_unit_level_uuid": str(node.org_unit_level_uuid),
            }
            for node in chain(self.expected_children, self.expected_grandchildren)
        ]


class _MockGraphQLSessionRaisingTransportQueryError(_MockGraphQLSession):
    def execute(
        self, query: DocumentNode, variable_values: dict[str, Any] | None = None
    ) -> dict:
        raise TransportQueryError("testing")


@pytest.fixture()
def mock_graphql_session(graphql_testing_schema: GraphQLSchema) -> _MockGraphQLSession:
    return _MockGraphQLSession(graphql_testing_schema)


@pytest.fixture()
def mock_graphql_session_raising_transportqueryerror(
    graphql_testing_schema: GraphQLSchema,
) -> _MockGraphQLSessionRaisingTransportQueryError:
    return _MockGraphQLSessionRaisingTransportQueryError(graphql_testing_schema)


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
                "DeactivationDate": "2000-01-01",
                "DepartmentIdentifier": "NY1",
                "DepartmentLevelIdentifier": "NY1-niveau",
                "DepartmentName": "Department 1",
                "DepartmentUUIDIdentifier": str(SharedIdentifier.child_org_unit_uuid),
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "2000-01-01",
                "DepartmentIdentifier": "NY0",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "Department 2",
                "DepartmentUUIDIdentifier": str(
                    SharedIdentifier.grandchild_org_unit_uuid
                ),
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "2000-01-01",
                "DepartmentIdentifier": "Afd",
                "DepartmentLevelIdentifier": "Afdelings-niveau",
                "DepartmentName": "Department 3",
                "DepartmentUUIDIdentifier": "30000000-0000-0000-0000-000000000000",
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "2000-01-01",
                "DepartmentIdentifier": "Afd",
                "DepartmentLevelIdentifier": "Afdelings-niveau",
                "DepartmentName": "Department 4",
                "DepartmentUUIDIdentifier": "40000000-0000-0000-0000-000000000000",
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "2000-01-01",
                "DepartmentIdentifier": "NY0",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "Department 5",
                "DepartmentUUIDIdentifier": "50000000-0000-0000-0000-000000000000",
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "2000-01-01",
                "DepartmentIdentifier": "Afd",
                "DepartmentLevelIdentifier": "Afdelings-niveau",
                "DepartmentName": "Department 6",
                "DepartmentUUIDIdentifier": "60000000-0000-0000-0000-000000000000",
            },
        ],
    }
    sd_departments = GetDepartmentResponse.parse_obj(sd_departments_json)
    return sd_departments


@pytest.fixture()
def sd_expected_validity() -> Validity:
    """Construct a `Validity` instance corresponding to the periods indicated by the
    `ActivationDate`/`DeactivationDate` pairs returned by
    `mock_sd_get_organization_response` and `mock_sd_get_department_response`.
    """
    from_dt = datetime.fromisoformat("1999-01-01T00:00:00+01:00")
    to_dt = datetime.fromisoformat("2000-01-01T00:00:00+01:00")
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
        return {"classes": {"objects": [{"current": cls} for cls in self.class_data]}}


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
    mock_sd_get_department_response,
) -> MockMOOrgUnitLevelMap:
    valid_dep_level_identifiers: list[str] = [
        dep.DepartmentLevelIdentifier
        for dep in mock_sd_get_department_response.Department
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
def mock_org_tree_diff(
    mock_graphql_session: _MockGraphQLSession,
    mock_sd_get_organization_response: GetOrganizationResponse,
    mock_sd_get_department_response: GetDepartmentResponse,
    mock_mo_org_unit_level_map: MockMOOrgUnitLevelMap,
    mock_mo_org_unit_type: MOClass,
) -> OrgTreeDiff:
    # Construct MO and SD trees
    mo_tree = MOOrgTreeImport(mock_graphql_session).as_single_tree()
    sd_tree = build_tree(
        mock_sd_get_organization_response,
        mock_sd_get_department_response,
        mock_mo_org_unit_level_map,
    )
    # Construct tree diff
    return OrgTreeDiff(mo_tree, sd_tree, mock_mo_org_unit_type)


def get_mock_sd_tree(mo_org_tree: MOOrgTreeImport) -> OrgUnitNode:
    # This function is not a pytest fixture, as it is being called from "application"
    # code (`App`.)
    mock_sd_validity: Validity = Validity(
        from_date=datetime.fromisoformat("1960-01-01T00:00:00+01:00"),
        to_date=None,
    )
    mock_sd_root: OrgUnitNode = OrgUnitNode(
        uuid=mo_org_tree.get_org_uuid(),
        parent_uuid=None,
        name="<root>",
        validity=mock_sd_validity,
    )
    mock_sd_updated_child: OrgUnitNode = OrgUnitNode(
        uuid=OrgUnitUUID("f06ee470-9f17-566f-acbe-e938112d46d9"),
        parent_uuid=mo_org_tree.get_org_uuid(),
        name="Kolding Kommune II",
        org_unit_level_uuid=uuid.uuid4(),
        validity=mock_sd_validity,
    )
    mock_sd_new_child: OrgUnitNode = OrgUnitNode(
        uuid=uuid.uuid4(),
        parent_uuid=mo_org_tree.get_org_uuid(),
        name="Something new",
        org_unit_level_uuid=uuid.uuid4(),
        validity=mock_sd_validity,
    )
    mock_sd_root.children = [mock_sd_updated_child, mock_sd_new_child]
    return mock_sd_root
