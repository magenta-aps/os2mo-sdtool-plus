# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import re
from unittest.mock import MagicMock
from unittest.mock import call
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from sdtoolplus.app import App
from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.db.rundb import Status
from sdtoolplus.main import background_run
from sdtoolplus.main import create_app


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

    @patch("sdtoolplus.main.get_engine")
    @patch("sdtoolplus.main.background_run")
    @patch("sdtoolplus.main.persist_status")
    @patch("sdtoolplus.main.get_status", return_value=Status.COMPLETED)
    def test_post_trigger_all_inst_ids(
        self,
        mock_get_status: MagicMock,
        mock_persist_status: MagicMock,
        mock_background_run: MagicMock,
        mock_get_engine: MagicMock,
        sdtoolplus_settings: SDToolPlusSettings,
    ) -> None:
        # Arrange
        sdtoolplus_settings.mo_subtree_paths_for_root = {
            "AB": [],
            "CD": [],
        }

        mock_sdtoolplus_app = MagicMock(spec=App)

        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        with patch("sdtoolplus.main.App", return_value=mock_sdtoolplus_app):
            client: TestClient = TestClient(create_app(settings=sdtoolplus_settings))

            # Act
            response: Response = client.post("/trigger-all-inst-ids")

            # Assert
            mock_persist_status.assert_called_once_with(mock_engine, Status.RUNNING)
            mock_background_run.assert_called_once_with(
                sdtoolplus_settings, mock_engine, ["AB", "CD"], None, False
            )
            assert response.json() == {"msg": "Org tree sync started in background"}

    @pytest.mark.parametrize(
        "org_unit, inst_id, dry_run, expected_inst_id_list",
        [
            (UUID("10000000-0000-0000-0000-000000000000"), "AB", False, ["AB"]),
            (UUID("20000000-0000-0000-0000-000000000000"), "CD", True, ["CD"]),
        ],
    )
    @patch("sdtoolplus.main.get_engine")
    @patch("sdtoolplus.main.background_run")
    @patch("sdtoolplus.main.persist_status")
    @patch("sdtoolplus.main.get_status", return_value=Status.COMPLETED)
    def test_post_trigger_all_inst_ids_dry_and_inst_id(
        self,
        mock_get_status: MagicMock,
        mock_persist_status: MagicMock,
        mock_background_run: MagicMock,
        mock_get_engine: MagicMock,
        org_unit: UUID | None,
        inst_id: str | None,
        dry_run: bool,
        expected_inst_id_list: list[str],
        sdtoolplus_settings: SDToolPlusSettings,
    ) -> None:
        # Arrange
        sdtoolplus_settings.mo_subtree_paths_for_root = {
            "AB": [],
            "CD": [],
        }

        mock_sdtoolplus_app = MagicMock(spec=App)

        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        with patch("sdtoolplus.main.App", return_value=mock_sdtoolplus_app):
            client: TestClient = TestClient(create_app(settings=sdtoolplus_settings))

            # Act
            response: Response = client.post(
                "/trigger-all-inst-ids",
                params={
                    "org_unit": str(org_unit),
                    "inst_id": inst_id,
                    "dry_run": dry_run,
                },
            )

            # Assert
            if not dry_run:
                mock_persist_status.assert_called_once_with(mock_engine, Status.RUNNING)
            mock_background_run.assert_called_once_with(
                sdtoolplus_settings,
                mock_engine,
                expected_inst_id_list,
                org_unit,
                dry_run,
            )
            assert response.json() == {"msg": "Org tree sync started in background"}

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


@pytest.mark.parametrize(
    "org_unit, dry_run",
    [
        (None, False),
        (UUID("10000000-0000-0000-0000-000000000000"), False),
        (UUID("10000000-0000-0000-0000-000000000000"), True),
        (UUID("10000000-0000-0000-0000-000000000000"), True),
    ],
)
@patch("sdtoolplus.main.persist_status")
def test_background_run(
    mock_persist_status: MagicMock,
    sdtoolplus_settings: SDToolPlusSettings,
    org_unit: UUID | None,
    dry_run: bool,
):
    # Arrange
    mock_sdtoolplus_app = MagicMock(spec=App)
    mock_engine = MagicMock()

    with patch("sdtoolplus.main.App", return_value=mock_sdtoolplus_app) as m_app:
        # Act
        background_run(
            sdtoolplus_settings, mock_engine, ["AB", "CD"], org_unit, dry_run
        )

        # Assert

        # Make sure the constructor is called once with the correct args
        assert m_app.call_count == 1
        call1 = m_app.call_args_list[0]
        assert call1 == call(sdtoolplus_settings, "AB")

        call1, call2 = mock_sdtoolplus_app.set_inst_id.call_args_list
        assert call1 == call("AB")
        assert call2 == call("CD")

        # Careful here - no logic in the test code!
        if not dry_run:
            mock_persist_status.assert_called_once_with(mock_engine, Status.COMPLETED)
        else:
            mock_persist_status.assert_not_called()
