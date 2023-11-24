# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from contextlib import ExitStack
from inspect import isgenerator
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID
from uuid import uuid4

import pytest
from httpx import Response
from raclients.graph.client import PersistentGraphQLClient

from ..app import App
from ..config import SDToolPlusSettings
from ..diff_org_trees import OrgTreeDiff
from ..mo_org_unit_importer import OrgUnitNode
from ..mo_org_unit_importer import OrgUnitUUID
from ..sd.tree import build_tree
from ..tree_diff_executor import TreeDiffExecutor
from .conftest import mock_graphql_session
from .conftest import SharedIdentifier


class TestApp:
    def test_init(self, sdtoolplus_settings: SDToolPlusSettings) -> None:
        # Act
        app: App = self._get_app_instance(sdtoolplus_settings)
        # Assert
        assert isinstance(app.settings, SDToolPlusSettings)
        assert isinstance(app.session, PersistentGraphQLClient)

    def test_init_calls_sentry_sdk(
        self, sdtoolplus_settings: SDToolPlusSettings
    ) -> None:
        # Arrange
        with ExitStack() as stack:
            mock_sentry_sdk_init = self._add_mock(stack, "sentry_sdk.init")
            # Act
            app: App = self._get_app_instance(
                sdtoolplus_settings, sentry_dsn="sentry_dsn"
            )
            # Assert
            mock_sentry_sdk_init.assert_called_once_with(dsn="sentry_dsn")

    def test_get_tree_diff_executor(
        self,
        mock_graphql_session,
        mock_mo_org_unit_type_map,
        mock_mo_org_unit_level_map,
        mock_mo_org_tree_import,
        sdtoolplus_settings: SDToolPlusSettings,
    ) -> None:
        # Arrange: patch dependencies with mock replacements
        with ExitStack() as stack:
            self._add_mock(stack, "PersistentGraphQLClient", mock_graphql_session)
            self._add_mock(stack, "MOOrgUnitTypeMap", mock_mo_org_unit_type_map)
            self._add_mock(stack, "MOOrgUnitLevelMap", mock_mo_org_unit_level_map)
            self._add_mock(stack, "MOOrgTreeImport", mock_mo_org_tree_import)
            mock_get_sd_tree = self._add_mock(stack, "get_sd_tree", MagicMock())

            # Act
            app: App = self._get_app_instance(sdtoolplus_settings)
            tree_diff_executor: TreeDiffExecutor = app.get_tree_diff_executor()

            # Assert: check the `TreeDiffExecutor` instance
            assert isinstance(tree_diff_executor, TreeDiffExecutor)
            assert isinstance(tree_diff_executor._tree_diff, OrgTreeDiff)
            assert isgenerator(tree_diff_executor.execute())

            # Assert: check that we called the (mocked) `get_sd_tree` function
            mock_get_sd_tree.assert_called_once()

    def test_as_single_tree_called_with_correct_path(
        self,
        mock_mo_org_unit_type_map,
        mock_mo_org_unit_level_map,
        mock_mo_org_tree_import,
        sdtoolplus_settings: SDToolPlusSettings,
    ) -> None:
        with ExitStack() as stack:
            # Arrange
            self._add_mock(stack, "MOOrgUnitTypeMap", mock_mo_org_unit_type_map)
            self._add_mock(stack, "MOOrgUnitLevelMap", mock_mo_org_unit_level_map)
            self._add_mock(stack, "MOOrgTreeImport", mock_mo_org_tree_import)
            self._add_mock(stack, "get_sd_tree", MagicMock())

            mock_as_single_tree = MagicMock()
            mock_mo_org_tree_import.as_single_tree = mock_as_single_tree

            app: App = self._get_app_instance(
                sdtoolplus_settings,
                mo_subtree_path_for_root=[
                    SharedIdentifier.child_org_unit_uuid,
                    SharedIdentifier.grandchild_org_unit_uuid,
                ],
            )

            # Act
            app.get_tree_diff_executor()

            # Assert
            mock_as_single_tree.assert_called_once_with(
                f"{str(SharedIdentifier.child_org_unit_uuid)}/{str(SharedIdentifier.grandchild_org_unit_uuid)}"
            )

    def test_get_tree_diff_executor_for_mo_subtree_case(
        self,
        mock_graphql_session,
        mock_mo_org_unit_type_map,
        mock_mo_org_unit_level_map,
        mock_sd_get_organization_response,
        mock_sd_get_department_response,
        mock_mo_org_tree_import_subtree_case,
        sdtoolplus_settings: SDToolPlusSettings,
    ):
        # Arrange

        # The SD tree
        sd_tree = build_tree(
            mock_sd_get_organization_response,
            mock_sd_get_department_response,
            mock_mo_org_unit_level_map,
        )

        with ExitStack() as stack:
            self._add_mock(stack, "PersistentGraphQLClient", mock_graphql_session)
            self._add_mock(stack, "MOOrgUnitTypeMap", mock_mo_org_unit_type_map)
            self._add_mock(stack, "MOOrgUnitLevelMap", mock_mo_org_unit_level_map)
            self._add_mock(
                stack, "MOOrgTreeImport", mock_mo_org_tree_import_subtree_case
            )
            self._add_mock(stack, "get_sd_tree", sd_tree)

            app: App = self._get_app_instance(
                sdtoolplus_settings,
                mo_subtree_path_for_root=[UUID("11000000-0000-0000-0000-000000000000")],
            )

            # Act
            actual_iter = app.get_tree_diff_executor().execute()

            # Assert
            assert list(actual_iter) == []

    def test_execute(
        self,
        mock_tree_diff_executor: TreeDiffExecutor,
        expected_units_to_add: list[OrgUnitNode],
        expected_units_to_update: list[OrgUnitNode],
        sdtoolplus_settings: SDToolPlusSettings,
    ) -> None:
        # Arrange
        app: App = self._get_app_instance(sdtoolplus_settings)
        with ExitStack() as stack:
            self._add_obj_mock(
                stack, app, "get_tree_diff_executor", mock_tree_diff_executor
            )
            mock_graphql_execute = self._add_obj_mock(
                stack,
                mock_tree_diff_executor._session,
                "execute",
                self._get_mock_mutation_response(),
            )
            mock_client_post = self._add_obj_mock(
                stack, app.client, "post", Response(status_code=200)
            )
            # Act
            result: list[tuple] = list(app.execute())
            # Assert: check that we see the expected operations
            self._assert_expected_operations(
                result, expected_units_to_add + expected_units_to_update
            )
            # Assert: check that we see a call to the GraphQL API, as well as a call to
            # "fix_departments", for each `AddOperation` and `UpdateOperation` in the
            # result.
            num_add_or_update_ops = len(
                [
                    unit
                    for (unit, mutation, res1, res2) in result
                    if isinstance(unit, OrgUnitNode)
                ]
            )
            assert mock_graphql_execute.call_count == num_add_or_update_ops
            assert mock_client_post.call_count == num_add_or_update_ops

    def test_execute_dry(
        self,
        mock_tree_diff_executor: TreeDiffExecutor,
        expected_units_to_add: list[OrgUnitNode],
        expected_units_to_update: list[OrgUnitNode],
        sdtoolplus_settings: SDToolPlusSettings,
    ) -> None:
        # Arrange
        app: App = self._get_app_instance(sdtoolplus_settings)
        with ExitStack() as stack:
            self._add_obj_mock(
                stack, app, "get_tree_diff_executor", mock_tree_diff_executor
            )
            mock_graphql_execute = self._add_obj_mock(
                stack, mock_tree_diff_executor._session, "execute"
            )
            mock_client_post = self._add_obj_mock(stack, app.client, "post")
            # Act
            result: list[tuple] = list(app.execute(dry_run=True))
            # Assert: check that we see the expected operations
            self._assert_expected_operations(
                result, expected_units_to_add + expected_units_to_update
            )
            # Assert: check that we did not make any calls to the GraphQL API, or to
            # "fix_departments".
            mock_graphql_execute.assert_not_called()
            mock_client_post.assert_not_called()

    @pytest.mark.parametrize("status_code", [200, 400, 500])
    def test_call_apply_ny_logic(
        self, sdtoolplus_settings: SDToolPlusSettings, status_code: int
    ) -> None:
        # Arrange
        app: App = self._get_app_instance(sdtoolplus_settings)
        org_unit_uuid: OrgUnitUUID = uuid4()
        response: Response = Response(status_code=status_code, json={"msg": "msg"})
        with patch.object(
            app.client, "post", return_value=response
        ) as mock_client_post:
            # Act
            success: bool = app._call_apply_ny_logic(org_unit_uuid)
            # Assert
            assert success is (True if status_code == 200 else False)
            mock_client_post.assert_called_once_with(
                f"/trigger/apply-ny-logic/{org_unit_uuid}"
            )

    def _add_mock(self, stack: ExitStack, name: str, value: Any = None):
        """Mock out `name` using `value` (or None)"""
        return stack.enter_context(patch(f"sdtoolplus.app.{name}", return_value=value))

    def _add_obj_mock(self, stack: ExitStack, obj: Any, name: str, value: Any = None):
        """Mock out `name` attr on `obj` using `value` (or None)"""
        return stack.enter_context(patch.object(obj, name, return_value=value))

    def _assert_expected_operations(
        self,
        result: list[tuple],
        expected_units_to_add: list[OrgUnitNode],
    ) -> None:
        """Assert that the actual operations in `result` match the expected operations."""
        actual_operations: list[OrgUnitNode] = [item[0] for item in result]
        assert actual_operations == expected_units_to_add

    def _get_mock_mutation_response(self) -> MagicMock:
        mock_mutation_response: MagicMock = MagicMock()
        mock_mutation_response.__getitem__.return_value = {"uuid": str(uuid4())}
        return mock_mutation_response

    def _get_app_instance(
        self,
        sdtoolplus_settings: SDToolPlusSettings,
        **kwargs: Any,
    ) -> App:
        for name, value in kwargs.items():
            setattr(sdtoolplus_settings, name, value)
        return App(sdtoolplus_settings)

    def test_get_effective_root_path(self):
        # Arrange
        ou_uuid1 = UUID("10000000-0000-0000-0000-000000000000")
        ou_uuid2 = UUID("20000000-0000-0000-0000-000000000000")
        ou_uuid3 = UUID("30000000-0000-0000-0000-000000000000")

        # Act
        path: str = App._get_effective_root_path([ou_uuid1, ou_uuid2, ou_uuid3])

        # Assert
        assert path == (
            "10000000-0000-0000-0000-000000000000/"
            "20000000-0000-0000-0000-000000000000/"
            "30000000-0000-0000-0000-000000000000"
        )

    def test_get_effective_root_path_for_empty_list(self):
        assert App._get_effective_root_path([]) == ""
