# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from ..mo_org_unit_importer import MOOrgTreeImport


class TestMOOrgTreeImport:
    def test_get_org_uuid(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        assert instance.get_org_uuid() == mock_graphql_session.expected_org_uuid

    def test_get_org_units(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        assert len(instance.get_org_units()) == len(mock_graphql_session.get_org_units())

    def test_build_trees(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        trees = instance._build_trees(mock_graphql_session.get_org_units())
        assert len(trees) == 2
        for tree in trees:
            assert tree["uuid"] == mock_graphql_session.parent_uuid
            assert tree["parent_uuid"] == mock_graphql_session.expected_org_uuid
            for child in tree["children"]:
                assert child["uuid"] not in (mock_graphql_session.expected_org_uuid, mock_graphql_session.parent_uuid)
                assert child["parent_uuid"] == tree["uuid"]

    def test_as_single_tree(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        root = instance.as_single_tree()
        assert isinstance(root, dict)
        assert len(root["children"]) == 2

    def test_as_anytree_root(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        anytree_root = instance.as_anytree_root()
        assert anytree_root.is_root
