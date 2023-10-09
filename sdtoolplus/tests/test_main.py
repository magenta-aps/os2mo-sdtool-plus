# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from unittest.mock import MagicMock
from unittest.mock import patch

from click.testing import CliRunner
from click.testing import Result

from ..__main__ import main
from ..app import App


class TestMain:
    def test_main(self) -> None:
        """Test that `main` calls the expected methods on `App`"""
        # Arrange
        runner: CliRunner = CliRunner()
        mock_sdtoolplus_app: MagicMock = MagicMock(spec=App)
        with patch("sdtoolplus.__main__.App", return_value=mock_sdtoolplus_app):
            # Act
            result: Result = runner.invoke(main)
            # Assert: check that we call the expected methods
            mock_sdtoolplus_app.get_tree_diff_executor.assert_called_once_with()
            mock_sdtoolplus_app.get_tree_diff_executor().execute.assert_called_once_with()
            # Assert: check CLI exit code
            assert result.exit_code == 0
