# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import re
from unittest.mock import MagicMock
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from ..app import App
from ..config import SDToolPlusSettings
from ..fastapi import create_app


class TestFastAPIApp:
    def test_create_app(self, sdtoolplus_settings: SDToolPlusSettings) -> None:
        """Test that `create_app` adds an `App` instance to the FastAPI app returned"""
        # Act
        app: FastAPI = self._get_fastapi_app_instance(sdtoolplus_settings)
        # Assert
        assert isinstance(app.extra["sdtoolplus"], App)

    def test_get_root(self, sdtoolplus_settings: SDToolPlusSettings) -> None:
        """Test that 'GET /' returns a JSON doc giving the name of this integration"""
        # Arrange
        client: TestClient = TestClient(
            self._get_fastapi_app_instance(sdtoolplus_settings)
        )
        # Act
        response: Response = client.get("/")
        # Assert
        assert response.status_code == 200
        assert response.json() == {"name": "sdtoolplus"}

    def test_post_trigger(self, sdtoolplus_settings: SDToolPlusSettings) -> None:
        """Test that 'POST /trigger' calls the expected methods on `App`, etc."""
        # Arrange
        mock_sdtoolplus_app = MagicMock(spec=App)
        with patch("sdtoolplus.fastapi.App", return_value=mock_sdtoolplus_app):
            client: TestClient = TestClient(
                self._get_fastapi_app_instance(sdtoolplus_settings)
            )
            # Arrange: get initial value of "last run" metric
            last_run_val_before: float = self._get_last_run_metric(client)
            # Act
            response: Response = client.post("/trigger")
            # Assert: check that we call the expected methods
            mock_sdtoolplus_app.execute.assert_called_once_with(False)
            # Assert: check status code and response
            assert response.status_code == 200
            assert response.json() == []
            # Assert: check that the "last run" metric has incremented from 0.0
            last_run_val_after: float = self._get_last_run_metric(client)
            assert last_run_val_before == 0.0
            assert last_run_val_after > last_run_val_before

    def test_post_trigger_dry(self, sdtoolplus_settings: SDToolPlusSettings) -> None:
        """Test that 'POST /trigger/dry' calls the expected methods on `App`, etc."""
        # Arrange
        mock_sdtoolplus_app = MagicMock(spec=App)
        with patch("sdtoolplus.fastapi.App", return_value=mock_sdtoolplus_app):
            client: TestClient = TestClient(
                self._get_fastapi_app_instance(sdtoolplus_settings)
            )
            # Act
            response: Response = client.post("/trigger?dry_run=true")
            # Assert: check that we call the expected methods
            mock_sdtoolplus_app.execute.assert_called_once_with(True)
            # Assert: check status code and response
            assert response.status_code == 200
            assert response.json() == []

    def _get_fastapi_app_instance(
        self, sdtoolplus_settings: SDToolPlusSettings
    ) -> FastAPI:
        with patch(
            "sdtoolplus.fastapi.SDToolPlusSettings", return_value=sdtoolplus_settings
        ):
            return create_app()

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
