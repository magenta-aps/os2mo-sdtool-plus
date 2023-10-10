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
from ..tree_diff_executor import TreeDiffExecutor
from .conftest import get_mock_sd_tree


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
            self._add_mock(
                stack, "get_sd_tree", get_mock_sd_tree(mock_mo_org_tree_import)
            )

            # Act
            app: App = self._get_app_instance(**sd_credential_values)
            tree_diff_executor: TreeDiffExecutor = app.get_tree_diff_executor()

            # Assert
            operations: list = list(tree_diff_executor.execute())
            assert len(operations) == 0

    def _add_mock(self, stack: ExitStack, name: str, value: Any = None):
        """Mock out `name` using `value` (or None)"""
        return stack.enter_context(patch(f"sdtoolplus.app.{name}", return_value=value))

    def _get_app_instance(self, **kwargs: Any) -> App:
        settings: SDToolPlusSettings = SDToolPlusSettings()
        for name, value in kwargs.items():
            setattr(settings, name, value)
        return App(settings)
