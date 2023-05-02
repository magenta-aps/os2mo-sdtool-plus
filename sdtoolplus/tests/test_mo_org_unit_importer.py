# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import uuid

from graphql.language.ast import DocumentNode

from ..mo_org_unit_importer import MOOrgTreeImport


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


class TestMOOrgTreeImport:
    def test_get_org_uuid(self):
        session = _MockGraphQLSession()
        instance = MOOrgTreeImport(session)
        assert instance.get_org_uuid() == session.expected_org_uuid

    def test_get_org_units(self):
        session = _MockGraphQLSession()
        instance = MOOrgTreeImport(session)
        assert len(instance.get_org_units()) == len(session.get_org_units())

    def test_build_trees(self):
        session = _MockGraphQLSession()
        instance = MOOrgTreeImport(session)
        trees = instance._build_trees(session.get_org_units())
        assert len(trees) == 2
        for tree in trees:
            assert tree["uuid"] == session.parent_uuid
            assert tree["parent_uuid"] == session.expected_org_uuid
            for child in tree["children"]:
                assert child["uuid"] not in (session.expected_org_uuid, session.parent_uuid)
                assert child["parent_uuid"] == tree["uuid"]

    def test_as_single_tree(self):
        session = _MockGraphQLSession()
        instance = MOOrgTreeImport(session)
        root = instance.as_single_tree()
        assert isinstance(root, dict)
        assert len(root["children"]) == 2

    def test_as_anytree_root(self):
        session = _MockGraphQLSession()
        instance = MOOrgTreeImport(session)
        anytree_root = instance.as_anytree_root()
        assert anytree_root.is_root
