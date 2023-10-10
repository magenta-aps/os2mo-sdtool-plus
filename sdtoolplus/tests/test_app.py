# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from contextlib import ExitStack
from inspect import isgenerator
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import Response
from pydantic import SecretStr
from raclients.graph.client import PersistentGraphQLClient

from ..app import App
from ..config import SDToolPlusSettings
from ..diff_org_trees import AddOperation
from ..diff_org_trees import OrgTreeDiff
from ..diff_org_trees import RemoveOperation
from ..diff_org_trees import UpdateOperation
from ..mo_org_unit_importer import OrgUnitUUID
from ..tree_diff_executor import TreeDiffExecutor


class TestApp:
    def test_init(self) -> None:
        # Act
        app: App = self._get_app_instance()
        # Assert
        assert isinstance(app.settings, SDToolPlusSettings)
        assert isinstance(app.session, PersistentGraphQLClient)

    def test_init_calls_sentry_sdk(self) -> None:
        # Arrange
        with ExitStack() as stack:
            mock_sentry_sdk_init = self._add_mock(stack, "sentry_sdk.init")
            # Act
            app: App = self._get_app_instance(sentry_dsn="sentry_dsn")
            # Assert
            mock_sentry_sdk_init.assert_called_once_with(dsn="sentry_dsn")

    @pytest.mark.parametrize("sd_credentials", [False, True])
    def test_get_tree_diff_executor(
        self,
        mock_graphql_session,
        mock_mo_org_unit_type_map,
        mock_mo_org_unit_level_map,
        mock_mo_org_tree_import,
        sd_credentials: bool,
    ) -> None:
        # Arrange: add mock SD credentials to settings, if part of test run
        sd_credential_values: dict = (
            dict(
                sd_username="sd_username",
                sd_password=SecretStr("sd_password"),
                sd_institution_identifier="sd_institution_identifier",
            )
            if sd_credentials
            else {}
        )

        # Arrange: patch dependencies with mock replacements
        with ExitStack() as stack:
            self._add_mock(stack, "PersistentGraphQLClient", mock_graphql_session)
            self._add_mock(stack, "MOOrgUnitTypeMap", mock_mo_org_unit_type_map)
            self._add_mock(stack, "MOOrgUnitLevelMap", mock_mo_org_unit_level_map)
            self._add_mock(stack, "MOOrgTreeImport", mock_mo_org_tree_import)
            mock_get_sd_tree = self._add_mock(stack, "get_sd_tree", MagicMock())

            # Act
            app: App = self._get_app_instance(**sd_credential_values)
            tree_diff_executor: TreeDiffExecutor = app.get_tree_diff_executor()

            # Assert: check the `TreeDiffExecutor` instance
            assert isinstance(tree_diff_executor, TreeDiffExecutor)
            assert isinstance(tree_diff_executor._tree_diff, OrgTreeDiff)
            assert isgenerator(tree_diff_executor.execute())

            # Assert: check that we called the (mocked) `get_sd_tree` function if SD
            # credentials are available, and not otherwise.
            if sd_credentials:
                mock_get_sd_tree.assert_called_once()
            else:
                mock_get_sd_tree.assert_not_called()

    def test_execute(
        self,
        mock_tree_diff_executor: TreeDiffExecutor,
        expected_operations: list[AddOperation | UpdateOperation | RemoveOperation],
    ) -> None:
        # Arrange
        app: App = App()
        with patch.object(
            app,
            "get_tree_diff_executor",
            return_value=mock_tree_diff_executor,
        ):
            with patch.object(
                app.client,
                "post",
                return_value=Response(status_code=200),
            ) as mock_client_post:
                # Act
                result: list[tuple] = list(app.execute())
                # Assert: check that we see the expected operations
                assert [
                    operation for (operation, mutation, res1, res2) in result
                ] == expected_operations
                # Assert: check that we see a call to "fix_departments" for each
                # `AddOperation` and `UpdateOperation` in the result.
                num_add_or_update_ops = len(
                    [
                        operation
                        for (operation, mutation, res1, res2) in result
                        if isinstance(operation, (AddOperation, UpdateOperation))
                    ]
                )
                assert mock_client_post.call_count == num_add_or_update_ops

    @pytest.mark.parametrize("status_code", [200, 400, 500])
    def test_call_fix_departments(self, status_code: int):
        # Arrange
        app: App = App()
        org_unit_uuid: OrgUnitUUID = uuid4()
        response: Response = Response(status_code=status_code, json={"msg": "msg"})
        with patch.object(
            app.client, "post", return_value=response
        ) as mock_client_post:
            # Act
            success: bool = app._call_fix_departments(org_unit_uuid)
            # Assert
            assert success is (True if status_code == 200 else False)
            mock_client_post.assert_called_once_with(
                f"/trigger/fix-departments/{org_unit_uuid}"
            )

    def _add_mock(self, stack: ExitStack, name: str, value: Any = None):
        """Mock out `name` using `value` (or None)"""
        return stack.enter_context(patch(f"sdtoolplus.app.{name}", return_value=value))

    def _get_app_instance(self, **kwargs: Any) -> App:
        settings: SDToolPlusSettings = SDToolPlusSettings(client_secret=SecretStr(""))
        for name, value in kwargs.items():
            setattr(settings, name, value)
        return App(settings)
