# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st
from pydantic import parse_obj_as

from ..mo_org_unit_importer import MOOrgTreeImport
from ..mo_org_unit_importer import OrgUnit
from ..mo_org_unit_importer import OrgUnitNode
from ..mo_org_unit_importer import OrgUUID
from .conftest import SharedIdentifier


@st.composite
def flat_org_units(draw, uuids=st.uuids()) -> tuple[OrgUUID, list[OrgUnit]]:
    """Construct an flat `OrgUnit` list, representing a tree consisting of three levels:
    - a single root node
    - one or more child nodes, whose parent is the root node
    - one or more grandchild nodes, whose parent is one of the child nodes above it
    """
    root_org_uuid = draw(uuids)
    root_org_unit = draw(st.builds(OrgUnit, uuid=st.just(root_org_uuid)))
    children = draw(
        st.lists(
            st.builds(OrgUnit, parent_uuid=st.just(root_org_unit.uuid)),
            min_size=1,
        )
    )
    grandchildren = draw(
        st.lists(
            st.builds(OrgUnit, parent_uuid=st.sampled_from([c.uuid for c in children]))
        )
    )
    return root_org_uuid, [root_org_unit] + children + grandchildren


class TestMOOrgTreeImport:
    def test_get_org_uuid(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        assert instance.get_org_uuid() == SharedIdentifier.root_org_uuid
        assert isinstance(instance.get_org_uuid(), OrgUUID)

    def test_get_org_units(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        assert instance.get_org_units() == [
            OrgUnit(uuid=n.uuid, parent_uuid=n.parent_uuid, name=n.name)
            for n in (
                mock_graphql_session.expected_children
                + mock_graphql_session.expected_grandchildren
            )
        ]

    def test_build_trees(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        trees = instance._build_trees(
            parse_obj_as(list[OrgUnit], mock_graphql_session.tree_as_flat_list_of_dicts)
        )
        assert trees == mock_graphql_session.expected_trees

    @given(flat_org_units())
    def test_build_trees_robustness(
        self, flat_org_units: tuple[OrgUUID, list[OrgUnit]]
    ):
        org_uuid, org_units = flat_org_units
        with patch.object(MOOrgTreeImport, "get_org_uuid", return_value=org_uuid):
            instance = MOOrgTreeImport(None)
            instance._build_trees(org_units)

    def test_as_single_tree(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        root = instance.as_single_tree()
        assert isinstance(root, OrgUnitNode)
        assert root.children == tuple(mock_graphql_session.expected_trees)
        assert root.is_root
        assert [child.is_leaf for child in root.children]
