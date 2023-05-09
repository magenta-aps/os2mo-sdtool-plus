# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import anytree
from pydantic import parse_obj_as

from ..mo_org_unit_importer import MOOrgTreeImport
from ..mo_org_unit_importer import OrgUUID
from ..mo_org_unit_importer import OrgUnit


class TestMOOrgTreeImport:
    def test_get_org_uuid(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        assert instance.get_org_uuid() == mock_graphql_session.expected_org_uuid
        assert isinstance(instance.get_org_uuid(), OrgUUID)

    def test_get_org_units(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        assert len(instance.get_org_units()) == len(mock_graphql_session.get_org_units())

    def test_build_trees(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        trees = instance._build_trees(
            parse_obj_as(list[OrgUnit], mock_graphql_session.get_org_units())
        )
        assert len(trees) == 2
        for tree in trees:
            assert tree.uuid != mock_graphql_session.expected_org_uuid
            assert tree.parent_uuid == mock_graphql_session.expected_org_uuid
            for child in tree.children:
                assert child.uuid != mock_graphql_session.expected_org_uuid
                assert child.parent_uuid == tree.uuid

    def test_as_single_tree(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        root = instance.as_single_tree()
        assert isinstance(root, OrgUnit)
        assert isinstance(root, anytree.AnyNode)
        assert len(root.children) == 2
        assert root.is_root
