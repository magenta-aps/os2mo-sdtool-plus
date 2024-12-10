# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from contextlib import ExitStack
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID
from uuid import uuid4

import pytest
from anytree import find_by_attr
from fastramqpi.raclients.graph.client import PersistentGraphQLClient
from httpx import Response
from more_itertools import one
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from ..app import _get_mo_root_uuid
from ..app import _get_mo_subtree_path_for_root
from ..app import _get_sd_root_uuid
from ..app import App
from ..config import SDToolPlusSettings
from ..mo_class import MOOrgUnitLevelMap
from ..mo_org_unit_importer import OrgUnitNode
from ..mo_org_unit_importer import OrgUnitUUID
from ..sd.tree import build_tree
from ..tree_diff_executor import AddOrgUnitMutation
from ..tree_diff_executor import TreeDiffExecutor
from ..tree_diff_executor import UpdateOrgUnitMutation
from .conftest import _MockGraphQLSession
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

            mock_as_single_tree = MagicMock(return_value=(MagicMock(), MagicMock()))
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
                UUID("20000000-0000-0000-0000-000000000000"),
                f"{str(SharedIdentifier.child_org_unit_uuid)}/{str(SharedIdentifier.grandchild_org_unit_uuid)}",
                None,
            )

    def test_as_single_tree_called_with_correct_path_for_multiple_inst_ids(
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

            mock_as_single_tree = MagicMock(return_value=(MagicMock(), MagicMock()))
            mock_mo_org_tree_import.as_single_tree = mock_as_single_tree

            app: App = self._get_app_instance(
                sdtoolplus_settings,
                "II",
                mo_subtree_paths_for_root={
                    "II": [
                        SharedIdentifier.child_org_unit_uuid,
                        SharedIdentifier.grandchild_org_unit_uuid,
                    ],
                },
            )

            # Act
            app.get_tree_diff_executor()

            # Assert
            mock_as_single_tree.assert_called_once_with(
                UUID("20000000-0000-0000-0000-000000000000"),
                f"{str(SharedIdentifier.child_org_unit_uuid)}/{str(SharedIdentifier.grandchild_org_unit_uuid)}",
                None,
            )

    @patch("sdtoolplus.app.get_graphql_client")
    def test_get_tree_diff_executor_for_mo_subtree_case(
        self,
        mock_get_graphql_client: MagicMock,
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
        sd_tree.uuid = UUID("11000000-0000-0000-0000-000000000000")

        with ExitStack() as stack:
            mock_get_graphql_client.return_value = mock_graphql_session
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
            apply_ny_logic_response = MagicMock()
            apply_ny_logic_response.is_success = True
            mock_client_post = self._add_obj_mock(
                stack, app.client, "post", apply_ny_logic_response
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
                    for (unit, mutation, res1) in result
                    if isinstance(unit, OrgUnitNode)
                ]
            )
            assert mock_graphql_execute.call_count == num_add_or_update_ops
            assert mock_client_post.call_count == 2  # No of update operations

    def test_execute_filter(
        self,
        mock_tree_diff_executor: TreeDiffExecutor,
        sdtoolplus_settings: SDToolPlusSettings,
    ) -> None:
        # Arrange
        app: App = self._get_app_instance(sdtoolplus_settings)
        with ExitStack() as stack:
            self._add_obj_mock(
                stack, app, "get_tree_diff_executor", mock_tree_diff_executor
            )
            apply_ny_logic_response = MagicMock()
            apply_ny_logic_response.is_success = True
            self._add_obj_mock(stack, app.client, "post", apply_ny_logic_response)

            # Act
            result: list[tuple] = list(
                app.execute(org_unit=UUID("60000000-0000-0000-0000-000000000000"))
            )

            # Assert
            expected_unit_to_process = one(result)[0]
            assert expected_unit_to_process.uuid == UUID(
                "60000000-0000-0000-0000-000000000000"
            )

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

    def test_call_apply_ny_logic(self, sdtoolplus_settings: SDToolPlusSettings) -> None:
        # Arrange
        app: App = self._get_app_instance(sdtoolplus_settings)
        org_unit_uuid: OrgUnitUUID = uuid4()
        mock_response = MagicMock(spec_set=Response)
        with patch.object(
            app.client, "post", return_value=mock_response
        ) as mock_client_post:
            # Act
            app._call_apply_ny_logic(org_unit_uuid)

            # Assert
            mock_client_post.assert_called_once_with(
                f"/trigger/apply-ny-logic/{org_unit_uuid}",
                params={"institution_identifier": "sd_institution_identifier"},
            )
            mock_response.raise_for_status.assert_called_once()

    def _add_mock(self, stack: ExitStack, name: str, value: Any = None):
        """Mock out `name` using `value` (or None)"""
        return stack.enter_context(patch(f"sdtoolplus.app.{name}", return_value=value))

    def _add_obj_mock(self, stack: ExitStack, obj: Any, name: str, value: Any = None):
        """Mock out `name` attr on `obj` using `value` (or None)"""
        return stack.enter_context(patch.object(obj, name, return_value=value))

    def _assert_expected_operations(
        self,
        result: list[tuple],
        expected_units: list[OrgUnitNode],
    ) -> None:
        """Assert that the actual operations in `result` match the expected operations."""
        actual_operations: list[OrgUnitNode] = [item[0] for item in result]
        assert actual_operations == expected_units

    def _get_mock_mutation_response(self) -> MagicMock:
        mock_mutation_response: MagicMock = MagicMock()
        mock_mutation_response.__getitem__.return_value = {"uuid": str(uuid4())}
        return mock_mutation_response

    def _get_app_instance(
        self,
        sdtoolplus_settings: SDToolPlusSettings,
        current_inst_id: str | None = None,
        **kwargs: Any,
    ) -> App:
        for name, value in kwargs.items():
            setattr(sdtoolplus_settings, name, value)
        return App(sdtoolplus_settings, current_inst_id)

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

    @patch("sdtoolplus.app.get_graphql_client")
    @patch("sdtoolplus.app.get_sd_tree")
    def test_get_sd_tree_override_sd_root_uuid(
        self,
        mock_get_sd_tree: MagicMock,
        mock_get_graphql_client: MagicMock,
        mock_graphql_session,
        mock_mo_org_tree_import,
        mock_mo_org_unit_level_map,
        sdtoolplus_settings: SDToolPlusSettings,
    ):
        with ExitStack() as stack:
            # Arrange
            mock_get_graphql_client.return_value = mock_graphql_session
            self._add_mock(stack, "MOOrgUnitLevelMap", mock_mo_org_unit_level_map)
            self._add_mock(stack, "MOOrgTreeImport", mock_mo_org_tree_import)

            mo_org_uuid = uuid4()
            mock_mo_org_tree_import.get_org_uuid = MagicMock(return_value=mo_org_uuid)

            app_: App = self._get_app_instance(
                sdtoolplus_settings, use_mo_root_uuid_as_sd_root_uuid=True
            )

            # Act
            app_.get_sd_tree(MagicMock())

            # Assert
            assert mock_get_sd_tree.call_args.args[3] == mo_org_uuid

    def test_httpx_ny_logic_timeout(
        self,
        sdtoolplus_settings: SDToolPlusSettings,
    ):
        # Arrange
        app_: App = self._get_app_instance(
            sdtoolplus_settings, use_mo_root_uuid_as_sd_root_uuid=True
        )

        # Assert
        assert app_.client.timeout.read == 120

    def test_should_apply_ny_logic_return_false_when_disabled(
        self,
        sdtoolplus_settings: SDToolPlusSettings,
    ):
        # Arrange
        sdtoolplus_settings.apply_ny_logic = False
        app_: App = self._get_app_instance(sdtoolplus_settings)

        # Assert
        assert not app_._should_apply_ny_logic(
            MagicMock(spec=UpdateOrgUnitMutation), MagicMock(return_value=False), False
        )

    def test_should_apply_ny_logic_return_false_for_dry_run(
        self,
        sdtoolplus_settings: SDToolPlusSettings,
    ):
        # Arrange
        app_: App = self._get_app_instance(sdtoolplus_settings)

        # Assert
        assert not app_._should_apply_ny_logic(
            MagicMock(spec=UpdateOrgUnitMutation), MagicMock(return_value=False), True
        )

    def test_should_apply_ny_logic_return_false_for_add_operation(
        self,
        sdtoolplus_settings: SDToolPlusSettings,
        mock_graphql_session: _MockGraphQLSession,
    ):
        # Arrange
        app_: App = self._get_app_instance(sdtoolplus_settings)
        mutation = AddOrgUnitMutation(mock_graphql_session, MagicMock(), MagicMock())

        # Assert
        assert not app_._should_apply_ny_logic(mutation, MagicMock(), False)

    @pytest.mark.parametrize(
        "obsolete_unit_roots, expected",
        [
            ([UUID("10000000-0000-0000-0000-000000000000")], False),
            ([], True),
        ],
    )
    def test_should_apply_ny_logic_for_obsolete_unit(
        self,
        obsolete_unit_roots: list[OrgUnitUUID],
        expected: bool,
        sdtoolplus_settings: SDToolPlusSettings,
        mock_sd_get_organization_response: GetOrganizationResponse,
        mock_sd_get_department_response: GetDepartmentResponse,
        mock_mo_org_unit_level_map: MOOrgUnitLevelMap,
        mock_graphql_session: _MockGraphQLSession,
    ):
        # Arrange
        sd_tree = build_tree(
            mock_sd_get_organization_response,
            mock_sd_get_department_response,
            mock_mo_org_unit_level_map,
        )
        app_: App = self._get_app_instance(
            sdtoolplus_settings,
            # Pretend Department 1 is equivalent to "Udgåede afdelinger"
            obsolete_unit_roots=obsolete_unit_roots,
        )

        dep4 = find_by_attr(
            sd_tree, UUID("40000000-0000-0000-0000-000000000000"), "uuid"
        )

        mutation = UpdateOrgUnitMutation(mock_graphql_session, dep4)

        # Assert
        assert app_._should_apply_ny_logic(mutation, dep4, False) == expected


UNIT_UUID1 = OrgUnitUUID(str(uuid4()))
UNIT_UUID2 = OrgUnitUUID(str(uuid4()))


@pytest.mark.parametrize(
    "mo_subtree_path_for_root, use_mo_root_uuid_as_sd_root_uuid, expected",
    [
        ([], False, None),
        ([], True, SharedIdentifier.root_org_uuid),
        ([UNIT_UUID1], False, UNIT_UUID1),
        ([UNIT_UUID1, UNIT_UUID2], False, UNIT_UUID2),
        ([UNIT_UUID1], True, UNIT_UUID1),
    ],
)
def test_get_sd_root_uuid(
    mo_subtree_path_for_root: list[OrgUnitUUID],
    use_mo_root_uuid_as_sd_root_uuid: bool,
    expected: OrgUnitUUID | None,
):
    """
    Test _get_sd_root_uuid in the case where we use mo_subtree_path_for_root
    and not mo_subtree_paths_for_root
    """
    # Act
    actual = _get_sd_root_uuid(
        SharedIdentifier.root_org_uuid,
        use_mo_root_uuid_as_sd_root_uuid,
        mo_subtree_path_for_root,
        None,
        "II",
    )

    # Assert
    assert actual == expected


def test_get_sd_root_uuid_multiple_institutions():
    """
    Test _get_sd_root_uuid in the case where we use mo_subtree_paths_for_root
    and not mo_subtree_path_for_root
    """
    # Act
    actual = _get_sd_root_uuid(
        SharedIdentifier.root_org_uuid,
        False,
        [],
        {"II": [UNIT_UUID1, UNIT_UUID2]},
        "II",
    )

    # Assert
    assert actual == UNIT_UUID2


@pytest.mark.parametrize(
    "use_mo_root_uuid_as_sd_root_uuid,expected",
    [(False, None), (True, SharedIdentifier.root_org_uuid)],
)
def test_get_sd_root_uuid_empty_path(
    use_mo_root_uuid_as_sd_root_uuid: bool, expected: bool | UUID
):
    # Act
    actual = _get_sd_root_uuid(
        SharedIdentifier.root_org_uuid,
        use_mo_root_uuid_as_sd_root_uuid,
        [],
        {"II": []},
        "II",
    )

    # Assert
    assert actual == expected


@pytest.mark.parametrize(
    "mo_subtree_path_for_root, expected",
    [
        ([], SharedIdentifier.root_org_uuid),
        ([UNIT_UUID1], UNIT_UUID1),
        ([UNIT_UUID1, UNIT_UUID2], UNIT_UUID2),
    ],
)
def test_get_mo_root_uuid(
    mo_subtree_path_for_root: list[OrgUnitUUID],
    expected: OrgUnitUUID | None,
):
    # Act
    actual = _get_mo_root_uuid(
        SharedIdentifier.root_org_uuid,
        mo_subtree_path_for_root,
    )

    # Assert
    assert actual == expected


def test__get_mo_subtree_path_for_root_single_inst_id(
    sdtoolplus_settings: SDToolPlusSettings,
):
    # Arrange
    sdtoolplus_settings.mo_subtree_path_for_root = [
        UUID("10000000-0000-0000-0000-000000000000"),
        UUID("20000000-0000-0000-0000-000000000000"),
    ]

    # Act
    subtree_path_for_root = _get_mo_subtree_path_for_root(sdtoolplus_settings, "II")

    # Assert
    assert subtree_path_for_root == [
        UUID("10000000-0000-0000-0000-000000000000"),
        UUID("20000000-0000-0000-0000-000000000000"),
    ]


def test__get_mo_subtree_path_for_root_multiple_inst_ids(
    sdtoolplus_settings: SDToolPlusSettings,
):
    # Arrange
    sdtoolplus_settings.mo_subtree_paths_for_root = {
        "II": [
            UUID("10000000-0000-0000-0000-000000000000"),
            UUID("20000000-0000-0000-0000-000000000000"),
        ],
        "II2": [
            UUID("30000000-0000-0000-0000-000000000000"),
            UUID("40000000-0000-0000-0000-000000000000"),
        ],
    }

    # Act
    subtree_path_for_root_ii = _get_mo_subtree_path_for_root(sdtoolplus_settings, "II")
    subtree_path_for_root_ii2 = _get_mo_subtree_path_for_root(
        sdtoolplus_settings, "II2"
    )

    # Assert
    assert subtree_path_for_root_ii == [
        UUID("10000000-0000-0000-0000-000000000000"),
        UUID("20000000-0000-0000-0000-000000000000"),
    ]

    assert subtree_path_for_root_ii2 == [
        UUID("30000000-0000-0000-0000-000000000000"),
        UUID("40000000-0000-0000-0000-000000000000"),
    ]
