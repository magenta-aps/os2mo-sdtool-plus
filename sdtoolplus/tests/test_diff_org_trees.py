# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import uuid
from unittest.mock import MagicMock

from anytree.render import RenderTree
from freezegun import freeze_time
from more_itertools import first
from ramodels.mo import Validity
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from ..config import SDToolPlusSettings
from ..diff_org_trees import _uuid_to_nodes_map
from ..diff_org_trees import Nodes
from ..diff_org_trees import OrgTreeDiff
from ..mo_class import MOOrgUnitLevelMap
from ..mo_org_unit_importer import MOOrgTreeImport
from ..mo_org_unit_importer import OrgUnitNode
from ..mo_org_unit_importer import OrgUnitUUID
from ..sd.tree import build_tree
from .conftest import _MockGraphQLSession
from .conftest import SharedIdentifier


class TestOrgTreeDiff:
    def test_compare_trees(
        self,
        mock_sd_get_organization_response,
        mock_sd_get_department_response,
        mock_mo_org_unit_level_map,
        sdtoolplus_settings,
    ):
        # Arrange

        mo_tree = build_tree(
            mock_sd_get_organization_response,
            mock_sd_get_department_response,
            mock_mo_org_unit_level_map,
        )
        sd_tree = build_tree(
            mock_sd_get_organization_response,
            mock_sd_get_department_response,
            mock_mo_org_unit_level_map,
        )
        # Add two new units
        dep7 = OrgUnitNode(
            uuid=uuid.UUID("70000000-0000-0000-0000-000000000000"),
            user_key="dep7",
            name="Department 7",
            parent=sd_tree,
        )
        dep8 = OrgUnitNode(
            uuid=uuid.UUID("80000000-0000-0000-0000-000000000000"),
            user_key="dep8",
            name="Department 8",
            parent=dep7,
        )

        org_tree_diff = OrgTreeDiff(
            mo_tree, sd_tree, mock_mo_org_unit_level_map, sdtoolplus_settings
        )

        # Act
        org_tree_diff._compare_trees()

        # Assert
        assert len(org_tree_diff.units_to_add) == 2

        first_to_add = org_tree_diff.units_to_add[0]
        second_to_add = org_tree_diff.units_to_add[1]

        assert isinstance(first_to_add, OrgUnitNode)
        assert first_to_add.uuid == uuid.UUID("70000000-0000-0000-0000-000000000000")
        assert first_to_add.name == "Department 7"
        assert first_to_add.parent.uuid == uuid.UUID(
            "00000000-0000-0000-0000-000000000000"
        )

        assert isinstance(second_to_add, OrgUnitNode)
        assert second_to_add.uuid == uuid.UUID("80000000-0000-0000-0000-000000000000")
        assert second_to_add.name == "Department 8"
        assert second_to_add.parent.uuid == uuid.UUID(
            "70000000-0000-0000-0000-000000000000"
        )

    def test_get_units_to_add(
        self,
        mock_graphql_session: _MockGraphQLSession,
        mock_sd_get_organization_response: GetOrganizationResponse,
        mock_sd_get_department_response: GetDepartmentResponse,
        mock_mo_org_unit_level_map: MOOrgUnitLevelMap,
        sdtoolplus_settings: SDToolPlusSettings,
        expected_units_to_add,
    ):
        # Construct MO and SD trees
        mo_tree = MOOrgTreeImport(mock_graphql_session).as_single_tree(
            SharedIdentifier.root_org_uuid
        )
        sd_tree = build_tree(
            mock_sd_get_organization_response,
            mock_sd_get_department_response,
            mock_mo_org_unit_level_map,
        )

        # Construct tree diff
        tree_diff = OrgTreeDiff(
            mo_tree, sd_tree, mock_mo_org_unit_level_map, sdtoolplus_settings
        )

        # If test fails, print diagnostic information
        print("MO Tree")
        print(RenderTree(mo_tree))
        print()
        print("SD Tree")
        print(RenderTree(sd_tree))
        print()

        for unit in tree_diff.get_units_to_add():
            print(unit)

        # Compare actual emitted operations to expected operations
        actual_operations: list[OrgUnitNode] = list(tree_diff.get_units_to_add())
        assert actual_operations == expected_units_to_add

    @freeze_time("2023-11-15")
    def test_get_operation_for_move_afd_from_ny_to_ny(
        self,
        mock_org_tree_diff_move_afd_from_ny_to_ny,
    ):
        """
        This tests the get_operations function in the case where we
        move Department 4 from Department 2 to Department 5 in the tree below.
        I.e. we test the case where we move an SD "Afdelings-niveau" from
        one "NY-niveau" to another.

        <OrgUnitNode: <root> (00000000-0000-0000-0000-000000000000)>
        └── <OrgUnitNode: Department 1 (10000000-0000-0000-0000-000000000000)>
            ├── <OrgUnitNode: Department 2 (20000000-0000-0000-0000-000000000000)>
            │   ├── <OrgUnitNode: Department 3 (30000000-0000-0000-0000-000000000000)>
            │   └── <OrgUnitNode: Department 4 (40000000-0000-0000-0000-000000000000)>
            └── <OrgUnitNode: Department 5 (50000000-0000-0000-0000-000000000000)>
                └── <OrgUnitNode: Department 6 (60000000-0000-0000-0000-000000000000)>
        """

        # Act
        units_to_update = list(
            mock_org_tree_diff_move_afd_from_ny_to_ny.get_units_to_update()
        )
        unit_to_update = units_to_update[0]

        # Assert
        assert len(units_to_update) == 1
        assert isinstance(unit_to_update, OrgUnitNode)
        assert unit_to_update.uuid == uuid.UUID("40000000-0000-0000-0000-000000000000")
        assert unit_to_update.name == "Department 4"
        assert unit_to_update.user_key == "dep4"
        assert unit_to_update.parent.uuid == uuid.UUID(
            "50000000-0000-0000-0000-000000000000"
        )

    @freeze_time("2023-11-15")
    def test_get_operation_for_move_ny_from_ny_to_ny(
        self,
        mock_org_tree_diff_move_ny_from_ny_to_ny,
    ):
        """
        This tests the get_operations function in the case where we
        move Department 5 (with subunits) from Department 1 to Department 7
        in the tree below. I.e. we test the case where we move an SD
        "NY-niveau" from one "NY-niveau" to another.

        <OrgUnitNode: <root> (00000000-0000-0000-0000-000000000000)>
        ├── <OrgUnitNode: Department 1 (10000000-0000-0000-0000-000000000000)>
        │   ├── <OrgUnitNode: Department 2 (20000000-0000-0000-0000-000000000000)>
        │   │   ├── <OrgUnitNode: Department 3 (30000000-0000-0000-0000-000000000000)>
        │   │   └── <OrgUnitNode: Department 4 (40000000-0000-0000-0000-000000000000)>
        │   └── <OrgUnitNode: Department 5 (50000000-0000-0000-0000-000000000000)>
        │       └── <OrgUnitNode: Department 6 (60000000-0000-0000-0000-000000000000)>
        └── <OrgUnitNode: Department 7 (70000000-0000-0000-0000-000000000000)>
        """

        # Act
        units_to_update = list(
            mock_org_tree_diff_move_ny_from_ny_to_ny.get_units_to_update()
        )
        unit_to_update = units_to_update[0]

        # Assert
        assert len(units_to_update) == 1
        assert isinstance(unit_to_update, OrgUnitNode)
        assert unit_to_update.uuid == uuid.UUID("50000000-0000-0000-0000-000000000000")
        assert unit_to_update.name == "Department 5"
        assert unit_to_update.user_key == "dep5"
        assert unit_to_update.parent.uuid == uuid.UUID(
            "70000000-0000-0000-0000-000000000000"
        )

    @freeze_time("2023-11-15")
    def test_get_operation_for_add_and_move_and_rename(
        self,
        mock_mo_org_unit_level_map,
        mock_org_tree_diff_add_and_move_and_rename,
        sd_expected_validity,
    ):
        """
        This tests the get_operations function in the case where we:

        1) Add Department 7 to the root
        2) Move Department 5 from Department 1 to Department 7
           (i.e. it must be added before Dep 5 can be moved)
        3) Rename Department 5 to Department 8

        The MO tree before any of the operations looks like this:

        <OrgUnitNode: <root> (00000000-0000-0000-0000-000000000000)>
        └── <OrgUnitNode: Department 1 (10000000-0000-0000-0000-000000000000)>
            ├── <OrgUnitNode: Department 2 (20000000-0000-0000-0000-000000000000)>
            │   ├── <OrgUnitNode: Department 3 (30000000-0000-0000-0000-000000000000)>
            │   └── <OrgUnitNode: Department 4 (40000000-0000-0000-0000-000000000000)>
            └── <OrgUnitNode: Department 5 (50000000-0000-0000-0000-000000000000)>
                └── <OrgUnitNode: Department 6 (60000000-0000-0000-0000-000000000000)>

        and the SD tree looks like this:

        <OrgUnitNode: <root> (00000000-0000-0000-0000-000000000000)>
        ├── <OrgUnitNode: Department 1 (10000000-0000-0000-0000-000000000000)>
        │   └── <OrgUnitNode: Department 2 (20000000-0000-0000-0000-000000000000)>
        │       ├── <OrgUnitNode: Department 3 (30000000-0000-0000-0000-000000000000)>
        │       └── <OrgUnitNode: Department 4 (40000000-0000-0000-0000-000000000000)>
        └── <OrgUnitNode: Department 7 (70000000-0000-0000-0000-000000000000)>
            └── <OrgUnitNode: Department 8 (50000000-0000-0000-0000-000000000000)>
                └── <OrgUnitNode: Department 6 (60000000-0000-0000-0000-000000000000)>
        """

        # Act
        units_to_add = list(
            mock_org_tree_diff_add_and_move_and_rename.get_units_to_add()
        )
        units_to_update = list(
            mock_org_tree_diff_add_and_move_and_rename.get_units_to_update()
        )

        # Assert
        assert len(units_to_add) == 1
        assert len(units_to_update) == 1

        unit_to_add = units_to_add[0]
        unit_to_update = units_to_update[0]

        assert isinstance(unit_to_add, OrgUnitNode)
        assert unit_to_add.uuid == uuid.UUID("70000000-0000-0000-0000-000000000000")
        assert (
            unit_to_add.org_unit_level_uuid
            == mock_mo_org_unit_level_map["NY1-niveau"].uuid
        )
        assert unit_to_add.name == "Department 7"
        assert unit_to_add.user_key == "dep7"
        assert unit_to_add.parent_uuid == uuid.UUID(
            "00000000-0000-0000-0000-000000000000"
        )
        assert unit_to_add.validity == sd_expected_validity

        assert isinstance(unit_to_update, OrgUnitNode)
        assert unit_to_update.uuid == uuid.UUID("50000000-0000-0000-0000-000000000000")
        assert unit_to_update.name == "Department 8"
        assert unit_to_update.user_key == "dep8"
        assert unit_to_update.parent.uuid == uuid.UUID(
            "70000000-0000-0000-0000-000000000000"
        )

    def test_subtree_has_active_engagements(
        self,
        mock_graphql_session: _MockGraphQLSession,
        sdtoolplus_settings: SDToolPlusSettings,
        sd_expected_validity: Validity,
    ):
        # Arrange

        # This is just a OU tree required by the OrgTreeDiff constructor. It is
        # not actually used in this test.
        mo_tree = MOOrgTreeImport(mock_graphql_session).as_single_tree(
            SharedIdentifier.root_org_uuid
        )
        org_tree_diff = OrgTreeDiff(mo_tree, mo_tree, MagicMock(), sdtoolplus_settings)

        # Use this subtree for testing _subtree_has_active_engagements
        #            subtree_root
        #               /    \
        #              A      B  <-- B has engagement
        #                    / \
        #                   C   D
        #                        \
        #                         E  <-- E has engagement

        def mock_has_active_engagements(org_unit_node: OrgUnitNode) -> bool:
            return True if org_unit_node.name in ["B", "E"] else False

        org_tree_diff._has_active_engagements = mock_has_active_engagements  # type: ignore

        subtree_root = OrgUnitNode(
            uuid=uuid.UUID("5cb00000-0000-0000-0000-000000000000"),
            parent_uuid=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            user_key="subtree_root",
            name="Subtree Root",
            org_unit_level_uuid=uuid.uuid4(),
            validity=sd_expected_validity,
        )

        A = OrgUnitNode(
            uuid=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            parent=subtree_root,
            user_key="a",
            name="A",
            org_unit_level_uuid=uuid.uuid4(),
            validity=sd_expected_validity,
        )

        B = OrgUnitNode(
            uuid=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            parent=subtree_root,
            user_key="b",
            name="B",
            org_unit_level_uuid=uuid.uuid4(),
            validity=sd_expected_validity,
        )

        C = OrgUnitNode(
            uuid=uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            parent=B,
            user_key="c",
            name="C",
            org_unit_level_uuid=uuid.uuid4(),
            validity=sd_expected_validity,
        )

        D = OrgUnitNode(
            uuid=uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
            parent=B,
            user_key="d",
            name="D",
            org_unit_level_uuid=uuid.uuid4(),
            validity=sd_expected_validity,
        )

        E = OrgUnitNode(
            uuid=uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
            parent=D,
            user_key="e",
            name="E",
            org_unit_level_uuid=uuid.uuid4(),
            validity=sd_expected_validity,
        )

        # Act + Assert
        result = org_tree_diff._subtree_has_active_engagements(subtree_root)
        assert result is True
        assert org_tree_diff.nodes_processed == {
            uuid.UUID("5cb00000-0000-0000-0000-000000000000"),
            uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        }

        # Run again (on B) and make sure that memoization is working
        org_tree_diff._has_active_engagements = MagicMock()  # type: ignore
        result = org_tree_diff._subtree_has_active_engagements(B)
        assert result is True
        assert org_tree_diff.nodes_processed == {
            uuid.UUID("5cb00000-0000-0000-0000-000000000000"),
            uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        }
        org_tree_diff._has_active_engagements.assert_not_called()

        # Run on D and assure both D and E are processed
        org_tree_diff._has_active_engagements = mock_has_active_engagements  # type: ignore
        result = org_tree_diff._subtree_has_active_engagements(D)
        assert result is True
        assert org_tree_diff.nodes_processed == {
            uuid.UUID("5cb00000-0000-0000-0000-000000000000"),
            uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
            uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
        }

        # Make sure sets  nodes are reset on re-instantiation
        org_tree_diff = OrgTreeDiff(mo_tree, mo_tree, MagicMock(), sdtoolplus_settings)
        assert len(org_tree_diff.nodes_processed) == 0
        assert len(org_tree_diff.engs_in_subtree) == 0
        assert len(org_tree_diff.units_with_engs) == 0

    def test_has_active_engagements_return_false_for_email_skip_list(
        self,
        mock_graphql_session: _MockGraphQLSession,
        sdtoolplus_settings: SDToolPlusSettings,
        random_org_unit_node: OrgUnitNode,
    ):
        # Arrange

        # This is just a OU tree required by the OrgTreeDiff constructor. It is
        # not actually used in this test.
        mo_tree = MOOrgTreeImport(mock_graphql_session).as_single_tree(
            SharedIdentifier.root_org_uuid
        )
        sdtoolplus_settings.email_notifications_disabled_units = [
            OrgUnitUUID("10000000-0000-0000-0000-000000000000")
        ]
        org_tree_diff = OrgTreeDiff(mo_tree, mo_tree, MagicMock(), sdtoolplus_settings)

        # Act
        result = org_tree_diff._has_active_engagements(random_org_unit_node)

        # Assert
        assert result is False


def test_uuid_to_nodes_map(
    mock_sd_get_organization_response,
    mock_sd_get_department_response,
    mock_mo_org_unit_level_map,
) -> None:
    """
    Test that _get_patent_map returns the correct map. The
    following tree structure will be used for the test:

    <OrgUnitNode: <root> (00000000-0000-0000-0000-000000000000)>
    └── <OrgUnitNode: Department 1 (10000000-0000-0000-0000-000000000000)>
        ├── <OrgUnitNode: Department 2 (20000000-0000-0000-0000-000000000000)>
        │   ├── <OrgUnitNode: Department 3 (30000000-0000-0000-0000-000000000000)>
        │   └── <OrgUnitNode: Department 4 (40000000-0000-0000-0000-000000000000)>
        └── <OrgUnitNode: Department 5 (50000000-0000-0000-0000-000000000000)>
            └── <OrgUnitNode: Department 6 (60000000-0000-0000-0000-000000000000)>
    """

    # Arrange
    sd_tree = build_tree(
        mock_sd_get_organization_response,
        mock_sd_get_department_response,
        mock_mo_org_unit_level_map,
    )

    # Act
    uuid_to_nodes_map = _uuid_to_nodes_map(sd_tree)

    # Careful here! No logic in the test code!
    map_of_uuids = {
        str(unit_uuid): (str(nodes.unit.uuid), str(nodes.parent.uuid))
        for unit_uuid, nodes in uuid_to_nodes_map.items()
    }

    # Assert
    assert len(uuid_to_nodes_map) == 6

    assert isinstance(first(uuid_to_nodes_map.keys()), uuid.UUID)
    assert isinstance(first(uuid_to_nodes_map.values()), Nodes)

    assert map_of_uuids == {
        "10000000-0000-0000-0000-000000000000": (
            "10000000-0000-0000-0000-000000000000",
            "00000000-0000-0000-0000-000000000000",
        ),
        "20000000-0000-0000-0000-000000000000": (
            "20000000-0000-0000-0000-000000000000",
            "10000000-0000-0000-0000-000000000000",
        ),
        "30000000-0000-0000-0000-000000000000": (
            "30000000-0000-0000-0000-000000000000",
            "20000000-0000-0000-0000-000000000000",
        ),
        "40000000-0000-0000-0000-000000000000": (
            "40000000-0000-0000-0000-000000000000",
            "20000000-0000-0000-0000-000000000000",
        ),
        "50000000-0000-0000-0000-000000000000": (
            "50000000-0000-0000-0000-000000000000",
            "10000000-0000-0000-0000-000000000000",
        ),
        "60000000-0000-0000-0000-000000000000": (
            "60000000-0000-0000-0000-000000000000",
            "50000000-0000-0000-0000-000000000000",
        ),
    }


def test_uuid_to_nodes_map_no_children(sd_expected_validity) -> None:
    # Arrange
    tree = OrgUnitNode(
        uuid=uuid.uuid4(),
        parent_uuid=uuid.uuid4(),
        user_key="user_key",
        name="name",
        org_unit_level_uuid=uuid.uuid4(),
        validity=sd_expected_validity,
    )

    # Act
    parent_map = _uuid_to_nodes_map(tree)

    # Assert
    assert parent_map == dict()
