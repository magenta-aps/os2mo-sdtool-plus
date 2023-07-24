# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import uuid
from unittest.mock import Mock

import pytest
from anytree.render import RenderTree
from deepdiff.helper import CannotCompare
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from .conftest import _MockGraphQLSession
from .conftest import SharedIdentifier
from ..diff_org_trees import AddOperation
from ..diff_org_trees import DEFAULT_ORG_UNIT_TYPE_UUID
from ..diff_org_trees import Operation
from ..diff_org_trees import OrgTreeDiff
from ..diff_org_trees import RemoveOperation
from ..diff_org_trees import UpdateOperation
from ..mo_org_unit_importer import MOOrgTreeImport
from ..mo_org_unit_importer import OrgUnitNode
from ..sd.tree import build_tree


class TestOrgTreeDiff:
    def test_get_operations(
        self,
        mock_graphql_session: _MockGraphQLSession,
        mock_sd_get_organization_response: GetOrganizationResponse,
        mock_sd_get_department_response: GetDepartmentResponse,
    ):
        # Construct MO and SD trees
        mo_tree = MOOrgTreeImport(mock_graphql_session).as_single_tree()
        sd_tree = build_tree(
            mock_sd_get_organization_response,
            mock_sd_get_department_response,
            SharedIdentifier.root_org_uuid,
        )

        # Construct tree diff
        tree_diff = OrgTreeDiff(mo_tree, sd_tree)

        # If test fails, print diagnostic information
        print("MO Tree")
        print(RenderTree(mo_tree))
        print()
        print("SD Tree")
        print(RenderTree(sd_tree))
        print()
        for operation in tree_diff.get_operations():
            print(operation)

        # Compare actual emitted operations to expected operations
        actual_operations: list[Operation] = list(tree_diff.get_operations())
        expected_operations: list[Operation] = [
            # MO unit to be removed is indeed removed
            RemoveOperation(uuid=SharedIdentifier.removed_org_unit_uuid),
            # MO unit "Grandchild" is renamed to "Department 2"
            UpdateOperation(uuid=SharedIdentifier.grandchild_org_unit_uuid, attr="name", value="Department 2"),
            # MO unit "Child" is renamed to "Department 1"
            UpdateOperation(uuid=SharedIdentifier.child_org_unit_uuid, attr="name", value="Department 1"),
            # SD units "Department 3" and "Department 4" are added under MO unit "Grandchild"
            AddOperation(
                parent_uuid=SharedIdentifier.grandchild_org_unit_uuid,
                name="Department 3",
                org_unit_type_uuid=DEFAULT_ORG_UNIT_TYPE_UUID,
            ),
            AddOperation(
                parent_uuid=SharedIdentifier.grandchild_org_unit_uuid,
                name="Department 4",
                org_unit_type_uuid=DEFAULT_ORG_UNIT_TYPE_UUID,
            ),
            # SD unit "Department 5" is added under MO unit "Child"
            AddOperation(
                parent_uuid=SharedIdentifier.child_org_unit_uuid,
                name="Department 5",
                org_unit_type_uuid=DEFAULT_ORG_UNIT_TYPE_UUID,
            ),
        ]
        assert actual_operations == expected_operations

    @pytest.mark.parametrize(
        "path,expected_result",
        [
            ("__", False),
            ("a.b.c", False),
            ("uuid", True),
            ("_uuid", False),
            ("children", True),
            ("_children", True),
        ]
    )
    def test_is_relevant(self, path: str, expected_result: bool):
        instance = self._get_empty_instance()
        actual_result = instance._is_relevant(None, path)
        assert actual_result == expected_result

    @pytest.mark.parametrize(
        "x,y,expected_result",
        [
            (
                OrgUnitNode(uuid=uuid.uuid4(), parent_uuid=uuid.uuid4(), name="X"),
                OrgUnitNode(uuid=uuid.uuid4(), parent_uuid=uuid.uuid4(), name="Y"),
                False,
            ),
            (
                OrgUnitNode(uuid=SharedIdentifier.child_org_unit_uuid, parent_uuid=uuid.uuid4(), name="X"),
                OrgUnitNode(uuid=SharedIdentifier.child_org_unit_uuid, parent_uuid=uuid.uuid4(), name="Y"),
                True,
            ),
        ]
    )
    def test_compare_on_uuid(self, x, y, expected_result: bool):
        instance = self._get_empty_instance()
        assert instance._compare_on_uuid(x, y) == expected_result

    def test_compare_on_uuid_raises_cannotcompare(self):
        instance = self._get_empty_instance()
        with pytest.raises(CannotCompare):
            instance._compare_on_uuid(None, None)

    def _get_empty_instance(self):
        return OrgTreeDiff(
            None,  # mo_org_tree,
            None,  # sd_org_tree
        )


class TestOperation:
    def test_has_diff_level_member(self):
        operation = Operation()
        assert operation._diff_level is None

    def test_from_diff_level(self):
        with pytest.raises(NotImplementedError):
            Operation.from_diff_level(None)

    def test_str(self):
        operation = Operation()
        with pytest.raises(NotImplementedError):
            str(operation)


class TestUpdateOperation:
    def test_supported_attrs(self):
        assert UpdateOperation._supported_attrs() == {"name"}

    def test_from_diff_level_can_return_none(self):
        diff_level = Mock()
        diff_level.path = Mock()
        diff_level.path.return_value = "a.b.c"
        assert UpdateOperation.from_diff_level(diff_level) is None
