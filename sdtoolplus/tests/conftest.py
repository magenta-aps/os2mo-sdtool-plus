# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import uuid
from copy import deepcopy
from itertools import chain

import pytest

from graphql.language.ast import DocumentNode

from ..mo_org_unit_importer import OrgUUID
from ..mo_org_unit_importer import OrgUnit
from ..mo_org_unit_importer import OrgUnitUUID


class _MockGraphQLSession:
    expected_org_uuid: OrgUUID = uuid.uuid4()

    _child_uuid: OrgUnitUUID = uuid.uuid4()
    _grandchild_uuid: OrgUnitUUID = uuid.uuid4()

    expected_children: list[OrgUnit] = [
        OrgUnit(
            uuid=_child_uuid,
            parent_uuid=expected_org_uuid,
            name="Child",
        ),
    ]

    expected_grandchildren: list[OrgUnit] = [
        OrgUnit(
            uuid=_grandchild_uuid,
            parent_uuid=_child_uuid,
            name="Grandchild",
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
        return {"org": {"uuid": self.expected_org_uuid}}

    @property
    def _mock_response_for_get_org_units(self) -> dict:
        return {
            "org_units": [
                {"objects": [elem]} for elem in self.tree_as_flat_list_of_dicts
            ]
        }

    @property
    def expected_trees(self) -> list[OrgUnit]:
        children = deepcopy(self.expected_children)
        for child in children:
            child.child_org_units = self.expected_grandchildren
        return children

    @property
    def tree_as_flat_list_of_dicts(self) -> list[dict]:
        return [
            {
                "uuid": str(node.uuid),
                "parent_uuid": str(node.parent_uuid),
                "name": node.name,
            }
            for node in chain(self.expected_children, self.expected_grandchildren)
        ]


@pytest.fixture()
def mock_graphql_session() -> _MockGraphQLSession:
    return _MockGraphQLSession()
