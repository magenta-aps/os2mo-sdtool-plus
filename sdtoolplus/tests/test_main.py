# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import re
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from ..app import App
from ..config import SDToolPlusSettings
from ..db.rundb import Status
from ..main import create_app


class TestFastAPIApp:
    @patch("sdtoolplus.main.persist_status")
    @patch("sdtoolplus.main.get_status", return_value=Status.COMPLETED)
    def test_post_trigger(
        self,
        mock_get_status: MagicMock,
        mock_persist_status: MagicMock,
        sdtoolplus_settings: SDToolPlusSettings,
    ) -> None:
        """Test that 'POST /trigger' calls the expected methods on `App`, etc."""
        # Arrange
        mock_sdtoolplus_app = MagicMock(spec=App)
        with patch("sdtoolplus.main.App", return_value=mock_sdtoolplus_app):
            # Arrange
            client: TestClient = TestClient(create_app(settings=sdtoolplus_settings))
            last_run_val_before: float = self._get_last_run_metric(client)

            # Act
            response: Response = client.post("/trigger")

            # Assert: check that we call the expected methods
            mock_sdtoolplus_app.execute.assert_called_once_with(
                org_unit=None, dry_run=False
            )

            # Assert: check status code and response
            assert response.status_code == 200
            assert response.json() == []

            # Assert: check that the "last run" metric has incremented from 0.0
            last_run_val_after: float = self._get_last_run_metric(client)
            assert last_run_val_before == 0.0
            assert last_run_val_after > last_run_val_before

            # Assert: persist_status called twice
            call1, call2 = mock_persist_status.call_args_list
            assert call1.args[1] == Status.RUNNING
            assert call2.args[1] == Status.COMPLETED

            # Assert: URL set correctly for engine
            engine1 = call1.args[0]
            engine2 = call2.args[0]
            assert isinstance(engine1, Engine)
            assert isinstance(engine2, Engine)
            assert (
                str(engine1.url)
                == str(engine2.url)
                == "postgresql+psycopg2://sdtool_plus:***@sd-db/sdtool_plus"
            )

    @patch("sdtoolplus.main.persist_status")
    @patch("sdtoolplus.main.get_status", return_value=Status.RUNNING)
    def test_post_trigger_aborts_when_rundb_status_is_running(
        self,
        mock_get_status: MagicMock,
        mock_persist_status: MagicMock,
        sdtoolplus_settings: SDToolPlusSettings,
    ) -> None:
        """Test that 'POST /trigger' calls the expected methods on `App`, etc."""
        # Arrange
        mock_sdtoolplus_app = MagicMock(spec=App)
        with patch("sdtoolplus.main.App", return_value=mock_sdtoolplus_app):
            client: TestClient = TestClient(create_app(settings=sdtoolplus_settings))

            # Act
            response: Response = client.post("/trigger")

            # Assert
            assert response.status_code == 500
            assert response.json() == {
                "msg": "Previous run did not complete successfully!"
            }

            mock_persist_status.assert_not_called()

    @patch("sdtoolplus.main.persist_status")
    @patch("sdtoolplus.main.get_status", return_value=Status.COMPLETED)
    def test_post_trigger_filter(
        self,
        mock_get_status: MagicMock,
        mock_persist_status: MagicMock,
        sdtoolplus_settings: SDToolPlusSettings,
    ) -> None:
        # Arrange
        mock_sdtoolplus_app = MagicMock(spec=App)
        with patch("sdtoolplus.main.App", return_value=mock_sdtoolplus_app):
            client: TestClient = TestClient(create_app(settings=sdtoolplus_settings))

            # Act
            client.post("/trigger?org_unit=70000000-0000-0000-0000-000000000000")

            # Assert
            mock_sdtoolplus_app.execute.assert_called_once_with(
                org_unit=UUID("70000000-0000-0000-0000-000000000000"), dry_run=False
            )

    @patch("sdtoolplus.main.persist_status")
    @patch("sdtoolplus.main.get_status", return_value=Status.COMPLETED)
    def test_post_trigger_dry(
        self,
        mock_get_status: MagicMock,
        mock_persist_status: MagicMock,
        sdtoolplus_settings: SDToolPlusSettings,
    ) -> None:
        """Test that 'POST /trigger/dry' calls the expected methods on `App`, etc."""
        # Arrange
        mock_sdtoolplus_app = MagicMock(spec=App)
        with patch("sdtoolplus.main.App", return_value=mock_sdtoolplus_app):
            client: TestClient = TestClient(create_app(settings=sdtoolplus_settings))
            # Act
            response: Response = client.post("/trigger?dry_run=true")

            # Assert
            mock_sdtoolplus_app.execute.assert_called_once_with(
                org_unit=None, dry_run=True
            )
            assert response.status_code == 200
            assert response.json() == []
            mock_persist_status.assert_not_called()

    @pytest.mark.parametrize(
        "rundb_status, endpoint_response_status",
        [
            (
                Status.COMPLETED,
                0,
            ),
            (
                Status.RUNNING,
                1,
            ),
        ],
    )
    def test_rundb_get_status(
        self,
        rundb_status: Status,
        endpoint_response_status: int,
        sdtoolplus_settings: SDToolPlusSettings,
    ):
        # Arrange
        client: TestClient = TestClient(create_app(settings=sdtoolplus_settings))

        with patch("sdtoolplus.main.get_status", return_value=rundb_status):
            # Act
            response = client.get("/rundb/status")

            # Assert
            assert response.status_code == 200
            assert response.text == str(endpoint_response_status)

    def test_rundb_get_status_on_error(self, sdtoolplus_settings: SDToolPlusSettings):
        # Arrange
        client: TestClient = TestClient(create_app(settings=sdtoolplus_settings))

        with patch("sdtoolplus.main.get_status", side_effect=SQLAlchemyError()):
            # Act
            response = client.get("/rundb/status")

            # Assert
            assert response.status_code == 200
            assert response.text == str(3)

    def _get_last_run_metric(
        self,
        client: TestClient,
        metric_name: str = "dipex_last_success_timestamp_seconds",
    ) -> float:
        """Parse the response of `GET /metrics`, finding the value of the metric given
        by `metric_name`.
        """
        response: Response = client.get("/metrics")
        match: re.Match = re.search(  # type: ignore
            r"^%s (?P<val>.*?)$" % metric_name,  # Find metric name and value
            response.content.decode("ascii"),  # Convert from `bytes` to `str`
            re.MULTILINE,  # Response consists of multiple lines
        )
        val: float = float(match.groupdict()["val"])
        return val
