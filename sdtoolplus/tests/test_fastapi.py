# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from unittest.mock import MagicMock
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from pydantic import SecretStr

from ..app import App
from ..config import SDToolPlusSettings
from ..fastapi import create_app


class TestFastAPIApp:
    def test_create_app(self) -> None:
        """Test that `create_app` adds an `App` instance to the FastAPI app returned"""
        # Act
        app: FastAPI = self._get_fastapi_app_instance()
        # Assert
        assert isinstance(app.extra["sdtoolplus"], App)

    def test_get_root(self) -> None:
        """Test that 'GET /' returns a JSON doc giving the name of this integration"""
        # Arrange
        client: TestClient = TestClient(self._get_fastapi_app_instance())
        # Act
        response: Response = client.get("/")
        # Assert
        assert response.status_code == 200
        assert response.json() == {"name": "sdtoolplus"}

    def test_post_trigger(self) -> None:
        """Test that 'POST /trigger' calls the expected methods on `App`, etc."""
        # Arrange
        mock_sdtoolplus_app = MagicMock(spec=App)
        with patch("sdtoolplus.fastapi.App", return_value=mock_sdtoolplus_app):
            client: TestClient = TestClient(self._get_fastapi_app_instance())
            # Act
            response: Response = client.post("/trigger")
            # Assert: check that we call the expected methods
            mock_sdtoolplus_app.execute.assert_called_once_with()
            mock_sdtoolplus_app.execute_dry.assert_not_called()
            # Assert: check status code and response
            assert response.status_code == 200
            assert response.json() == []

    def test_post_trigger_dry(self) -> None:
        """Test that 'POST /trigger/dry' calls the expected methods on `App`, etc."""
        # Arrange
        mock_sdtoolplus_app = MagicMock(spec=App)
        with patch("sdtoolplus.fastapi.App", return_value=mock_sdtoolplus_app):
            client: TestClient = TestClient(self._get_fastapi_app_instance())
            # Act
            response: Response = client.post("/trigger/dry")
            # Assert: check that we call the expected methods
            mock_sdtoolplus_app.execute_dry.assert_called_once_with()
            mock_sdtoolplus_app.execute.assert_not_called()
            # Assert: check status code and response
            assert response.status_code == 200
            assert response.json() == []

    def _get_fastapi_app_instance(self) -> FastAPI:
        settings: SDToolPlusSettings = SDToolPlusSettings(client_secret=SecretStr(""))
        with patch("sdtoolplus.fastapi.SDToolPlusSettings", return_value=settings):
            return create_app()
