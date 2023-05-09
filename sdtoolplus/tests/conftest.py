# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import uuid

import pytest

from graphql.language.ast import DocumentNode

from ..mo_org_unit_importer import OrgUnitUUID


class _MockGraphQLSession:
    expected_org_uuid: OrgUnitUUID = uuid.uuid4()

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
        def org_unit(uuid, parent_uuid):
            return {
                "uuid": uuid,
                "parent_uuid": parent_uuid,
                "name": f"Name {uuid}",
            }

        # Mock children of root org
        children = [org_unit(uuid.uuid4(), self.expected_org_uuid) for _ in range(2)]

        # Mock grandchildren (== children of parent org units)
        grandchildren = [org_unit(uuid.uuid4(), parent["uuid"]) for parent in children]

        return children + grandchildren


@pytest.fixture()
def mock_graphql_session() -> _MockGraphQLSession:
    return _MockGraphQLSession()
