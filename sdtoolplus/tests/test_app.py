# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from contextlib import ExitStack
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import SecretStr
from raclients.graph.client import PersistentGraphQLClient

from ..app import App
from ..config import SDToolPlusSettings
from ..sd.mock_tree import get_mock_sd_tree
from ..tree_diff_executor import TreeDiffExecutor


class TestApp:
    def test_init(self) -> None:
        # Act
        app: App = App()
        # Assert
        assert isinstance(app.settings, SDToolPlusSettings)
        assert isinstance(app.session, PersistentGraphQLClient)

    def test_init_calls_sentry_sdk(self) -> None:
        # Arrange
        mock_sd_tool_plus_settings: SDToolPlusSettings = SDToolPlusSettings()
        mock_sd_tool_plus_settings.sentry_dsn = "sentry_dsn"
        with ExitStack() as stack:
            self._add_mock(stack, "SDToolPlusSettings", mock_sd_tool_plus_settings)
            mock_sentry_sdk_init = self._add_mock(stack, "sentry_sdk.init")
            # Act
            app: App = App()
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
        mock_sd_tool_plus_settings: SDToolPlusSettings = SDToolPlusSettings()
        if sd_credentials:
            mock_sd_tool_plus_settings.sd_username = "sd_username"
            mock_sd_tool_plus_settings.sd_password = SecretStr("sd_password")
            mock_sd_tool_plus_settings.sd_institution_identifier = "sd_institution"

        # Arrange: patch dependencies with mock replacements
        with ExitStack() as stack:
            self._add_mock(stack, "SDToolPlusSettings", mock_sd_tool_plus_settings)
            self._add_mock(stack, "PersistentGraphQLClient", mock_graphql_session)
            self._add_mock(stack, "MOOrgUnitTypeMap", mock_mo_org_unit_type_map)
            self._add_mock(stack, "MOOrgUnitLevelMap", mock_mo_org_unit_level_map)
            self._add_mock(stack, "MOOrgTreeImport", mock_mo_org_tree_import)
            self._add_mock(
                stack, "get_sd_tree", get_mock_sd_tree(mock_mo_org_tree_import)
            )

            # Act
            app: App = App()
            tree_diff_executor: TreeDiffExecutor = app.get_tree_diff_executor()

            # Assert
            operations: list = list(tree_diff_executor.execute())
            assert len(operations) == 0

    def _add_mock(self, stack: ExitStack, name: str, value: Any = None):
        """Mock out `name` using `value` (or None)"""
        return stack.enter_context(patch(f"sdtoolplus.app.{name}", return_value=value))
