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
from pydantic import SecretStr
from ramodels.mo import Validity
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from ..config import SDToolPlusSettings
from ..diff_org_trees import AddOperation
from ..diff_org_trees import MoveOperation
from ..diff_org_trees import OrgTreeDiff
from ..diff_org_trees import UpdateOperation
from ..mo_class import MOClass
from ..mo_class import MOOrgUnitLevelMap
from ..mo_class import MOOrgUnitTypeMap
from ..mo_org_unit_importer import MOOrgTreeImport
from ..mo_org_unit_importer import OrgUnitNode
from ..mo_org_unit_importer import OrgUnitUUID
from ..mo_org_unit_importer import OrgUUID
from ..sd.tree import build_tree
from ..tree_diff_executor import TreeDiffExecutor

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
            name="Child",
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


@pytest.fixture()
def mock_tree_diff_executor(
    mock_graphql_session: _MockGraphQLSession,
    mock_org_tree_diff: OrgTreeDiff,
) -> TreeDiffExecutor:
    return TreeDiffExecutor(
        mock_graphql_session,  # type: ignore
        mock_org_tree_diff,
    )


@pytest.fixture()
def expected_operations(
    sd_expected_validity: Validity,
    mock_mo_org_unit_type: MOClass,
    mock_mo_org_unit_level_map: MockMOOrgUnitLevelMap,
) -> list[AddOperation | UpdateOperation | MoveOperation]:
    return [
        # MO unit "Grandchild" is renamed to "Department 2"
        UpdateOperation(
            uuid=SharedIdentifier.grandchild_org_unit_uuid,
            attr="name",
            value="Department 2",
            validity=sd_expected_validity,
        ),
        # MO unit "Grandchild" has its org unit level changed to match SD
        UpdateOperation(
            uuid=SharedIdentifier.grandchild_org_unit_uuid,
            attr="org_unit_level_uuid",
            value=str(mock_mo_org_unit_level_map["NY0-niveau"].uuid),
            validity=sd_expected_validity,
        ),
        # MO unit "Child" is renamed to "Department 1"
        UpdateOperation(
            uuid=SharedIdentifier.child_org_unit_uuid,
            attr="name",
            value="Department 1",
            validity=sd_expected_validity,
        ),
        # MO unit "Child" has its org unit level changed to match SD
        UpdateOperation(
            uuid=SharedIdentifier.child_org_unit_uuid,
            attr="org_unit_level_uuid",
            value=str(mock_mo_org_unit_level_map["NY1-niveau"].uuid),
            validity=sd_expected_validity,
        ),
        # SD units "Department 3" and "Department 4" are added under MO unit "Grandchild"
        AddOperation(
            uuid=uuid.UUID("30000000-0000-0000-0000-000000000000"),
            parent_uuid=SharedIdentifier.grandchild_org_unit_uuid,
            name="Department 3",
            org_unit_type_uuid=mock_mo_org_unit_type.uuid,
            org_unit_level_uuid=mock_mo_org_unit_level_map["Afdelings-niveau"].uuid,
            validity=sd_expected_validity,
        ),
        AddOperation(
            uuid=uuid.UUID("40000000-0000-0000-0000-000000000000"),
            parent_uuid=SharedIdentifier.grandchild_org_unit_uuid,
            name="Department 4",
            org_unit_type_uuid=mock_mo_org_unit_type.uuid,
            org_unit_level_uuid=mock_mo_org_unit_level_map["Afdelings-niveau"].uuid,
            validity=sd_expected_validity,
        ),
        # SD unit "Department 5" is added under MO unit "Child"
        AddOperation(
            uuid=uuid.UUID("50000000-0000-0000-0000-000000000000"),
            parent_uuid=SharedIdentifier.child_org_unit_uuid,
            name="Department 5",
            org_unit_type_uuid=mock_mo_org_unit_type.uuid,
            org_unit_level_uuid=mock_mo_org_unit_level_map["NY0-niveau"].uuid,
            validity=sd_expected_validity,
        ),
    ]


@pytest.fixture()
def sdtoolplus_settings() -> SDToolPlusSettings:
    return SDToolPlusSettings(
        client_secret=SecretStr(""),
        sd_username="sd_username",
        sd_institution_identifier="sd_institution_identifier",
        sd_password=SecretStr(""),
    )
