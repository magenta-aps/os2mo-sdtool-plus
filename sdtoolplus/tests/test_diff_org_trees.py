# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import uuid
from unittest.mock import Mock

import pytest
from anytree.render import RenderTree
from deepdiff.helper import CannotCompare
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from ..diff_org_trees import AddOperation
from ..diff_org_trees import AnyOperation
from ..diff_org_trees import Operation
from ..diff_org_trees import OrgTreeDiff
from ..diff_org_trees import RemoveOperation
from ..diff_org_trees import UpdateOperation
from ..mo_class import MOClass
from ..mo_class import MOOrgUnitLevelMap
from ..mo_org_unit_importer import MOOrgTreeImport
from ..mo_org_unit_importer import OrgUnitNode
from ..sd.tree import build_tree
from .conftest import _MockGraphQLSession
from .conftest import _TESTING_MO_VALIDITY
from .conftest import SharedIdentifier


class TestOrgTreeDiff:
    def test_get_operations(
        self,
        mock_graphql_session: _MockGraphQLSession,
        mock_sd_get_organization_response: GetOrganizationResponse,
        mock_sd_get_department_response: GetDepartmentResponse,
        mock_mo_org_unit_level_map: MOOrgUnitLevelMap,
        mock_mo_org_unit_type: MOClass,
        expected_operations: list[AddOperation | UpdateOperation | RemoveOperation],
    ):
        # Construct MO and SD trees
        mo_tree = MOOrgTreeImport(mock_graphql_session).as_single_tree()
        sd_tree = build_tree(
            mock_sd_get_organization_response,
            mock_sd_get_department_response,
            mock_mo_org_unit_level_map,
        )

        # Construct tree diff
        tree_diff = OrgTreeDiff(mo_tree, sd_tree, mock_mo_org_unit_type)

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
        actual_operations: list[AnyOperation] = list(tree_diff.get_operations())
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
        ],
    )
    def test_is_relevant(self, path: str, expected_result: bool):
        """`OrgTreeDiff._is_relevant` is passed to the `DeepDiff` instances used by
        `OrgTreeDiff`, and decides whether a given part of the `DeepDiff` tree is
        relevant.

        `DeepDiff` calls `_is_relevant`, passing it a `path` which corresponds to the
        location in the tree to test for relevance.

        We consider paths relevant if their last part:
        - exactly match one of "uuid", "parent_uuid" or "name"
        - or contains "children".

        We consider paths irrelevant if they begin with `__` (= they come from the
        `anytree`/`NodeMixin` API), or do not satisfy the above criteria otherwise.
        """
        instance = self._get_empty_instance()
        actual_result = instance._is_relevant(None, path)
        assert actual_result == expected_result

    @pytest.mark.parametrize(
        "x,y,expected_result",
        [
            (
                OrgUnitNode(
                    uuid=uuid.uuid4(),
                    parent_uuid=uuid.uuid4(),
                    name="X",
                    validity=_TESTING_MO_VALIDITY,
                ),
                OrgUnitNode(
                    uuid=uuid.uuid4(),
                    parent_uuid=uuid.uuid4(),
                    name="Y",
                    validity=_TESTING_MO_VALIDITY,
                ),
                False,
            ),
            (
                OrgUnitNode(
                    uuid=SharedIdentifier.child_org_unit_uuid,
                    parent_uuid=uuid.uuid4(),
                    name="X",
                    validity=_TESTING_MO_VALIDITY,
                ),
                OrgUnitNode(
                    uuid=SharedIdentifier.child_org_unit_uuid,
                    parent_uuid=uuid.uuid4(),
                    name="Y",
                    validity=_TESTING_MO_VALIDITY,
                ),
                True,
            ),
        ],
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
            None,  # sd_org_tree,
            None,  # mo_org_unit_type
        )


class TestOperation:
    def test_has_diff_level_member(self):
        operation = Operation()
        assert operation._diff_level is None

    def test_from_diff_level(self):
        with pytest.raises(NotImplementedError):
            Operation.from_diff_level(None, None)

    def test_str(self):
        operation = Operation()
        with pytest.raises(NotImplementedError):
            str(operation)


class TestUpdateOperation:
    def test_supported_attrs(self):
        assert UpdateOperation._supported_attrs() == {"name", "org_unit_level_uuid"}

    def test_from_diff_level_can_return_none(self):
        diff_level = Mock()
        diff_level.path = Mock()
        diff_level.path.return_value = "a.b.c"
        assert UpdateOperation.from_diff_level(diff_level, None) is None
