# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import uuid
from copy import deepcopy
from itertools import chain

import pytest
from graphql.language.ast import DocumentNode
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from ..mo_class import MOClass
from ..mo_class import MOOrgUnitLevelMap
from ..mo_class import MOOrgUnitTypeMap
from ..mo_org_unit_importer import OrgUnitNode
from ..mo_org_unit_importer import OrgUnitUUID
from ..mo_org_unit_importer import OrgUUID
from ..mo_org_unit_level import MOOrgUnitLevel
from ..mo_org_unit_level import MOOrgUnitLevelMap


class SharedIdentifier:
    root_org_uuid: OrgUUID = uuid.uuid4()
    child_org_unit_uuid: OrgUnitUUID = uuid.uuid4()
    grandchild_org_unit_uuid: OrgUnitUUID = uuid.uuid4()
    removed_org_unit_uuid: OrgUnitUUID = uuid.uuid4()


class _MockGraphQLSession:
    expected_children: list[OrgUnitNode] = [
        OrgUnitNode(
            uuid=SharedIdentifier.child_org_unit_uuid,
            parent_uuid=SharedIdentifier.root_org_uuid,
            name="Child",
            org_unit_level_uuid=uuid.uuid4(),
        ),
        OrgUnitNode(
            uuid=SharedIdentifier.removed_org_unit_uuid,
            parent_uuid=SharedIdentifier.root_org_uuid,
            name="Child only in MO, should be removed",
            org_unit_level_uuid=uuid.uuid4(),
        ),
    ]

    expected_grandchildren: list[OrgUnitNode] = [
        OrgUnitNode(
            uuid=SharedIdentifier.grandchild_org_unit_uuid,
            parent_uuid=SharedIdentifier.child_org_unit_uuid,
            name="Grandchild",
            org_unit_level_uuid=uuid.uuid4(),
        )
    ]

    def execute(self, query: DocumentNode) -> dict:
        name = query.to_dict()["definitions"][0]["name"]["value"]
        if name == "GetOrgUUID":
            return self._mock_response_for_get_org_uuid
        elif name == "GetOrgUnits":
            return self._mock_response_for_get_org_units
        else:
            raise ValueError("unknown query name %r" % name)

    @property
    def _mock_response_for_get_org_uuid(self) -> dict:
        return {"org": {"uuid": SharedIdentifier.root_org_uuid}}

    @property
    def _mock_response_for_get_org_units(self) -> dict:
        return {
            "org_units": [
                {"objects": [elem]} for elem in self.tree_as_flat_list_of_dicts
            ]
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


@pytest.fixture()
def mock_graphql_session() -> _MockGraphQLSession:
    return _MockGraphQLSession()


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
        return {"classes": self.class_data}


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
