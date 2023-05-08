# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import uuid

import pytest

from graphql.language.ast import DocumentNode


class _MockGraphQLSession:
    expected_org_uuid = str(uuid.uuid4())
    parent_uuid = str(uuid.uuid4())

    def __init__(self) -> None:
        self._get_org_uuid_response = {"org": {"uuid": self.expected_org_uuid}}
        self._get_org_units_response = {
            "org_units": [{"objects": [elem]} for elem in self.get_org_units()]
        }

    def execute(self, query: DocumentNode) -> dict:
        name = query.to_dict()['definitions'][0]['name']['value']
        if name == "GetOrgUUID":
            return self._get_org_uuid_response
        elif name == "GetOrgUnits":
            return self._get_org_units_response
        else:
            raise ValueError("unknown query name %r" % name)

    def get_org_units(self) -> list[dict]:
        # Mock children of root org
        org_units = [
            {"uuid": self.parent_uuid, "parent_uuid": self.expected_org_uuid}
            for _ in range(2)
        ]
        # Mock grandchildren (== children of parent org units)
        org_units.extend(
            [
                {"uuid": str(uuid.uuid4()), "parent_uuid": self.parent_uuid}
                for _ in range(2)
            ]
        )
        return org_units


@pytest.fixture()
def mock_graphql_session() -> _MockGraphQLSession:
    return _MockGraphQLSession()
