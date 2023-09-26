# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import uuid
from typing import Any
from unittest.mock import patch

import pytest
from gql.transport.exceptions import TransportQueryError
from graphql import GraphQLSchema
from ramodels.mo import Validity

from ..diff_org_trees import AddOperation
from ..diff_org_trees import Operation
from ..diff_org_trees import OrgTreeDiff
from ..diff_org_trees import RemoveOperation
from ..diff_org_trees import UpdateOperation
from ..tree_diff_executor import AddOrgUnitMutation
from ..tree_diff_executor import Mutation
from ..tree_diff_executor import RemoveOrgUnitMutation
from ..tree_diff_executor import TreeDiffExecutor
from ..tree_diff_executor import UnsupportedMutation
from ..tree_diff_executor import UpdateOrgUnitMutation
from .conftest import _MockGraphQLSession
from .conftest import _MockGraphQLSessionRaisingTransportQueryError


class TestMutation:
    def test_abstract_methods(
        self,
        graphql_testing_schema: GraphQLSchema,
    ):
        instance = Mutation(
            _MockGraphQLSession(graphql_testing_schema),  # type: ignore
            Operation(),  # type: ignore
        )
        with pytest.raises(NotImplementedError):
            instance.dsl_mutation
        with pytest.raises(NotImplementedError):
            instance.dsl_mutation_input


class TestTreeDiffExecutor:
    def test_execute(
        self,
        mock_graphql_session: _MockGraphQLSession,
        mock_org_tree_diff: OrgTreeDiff,
    ):
        tree_diff_executor = TreeDiffExecutor(
            mock_graphql_session,  # type: ignore
            mock_org_tree_diff,
        )
        for operation, mutation, result in tree_diff_executor.execute():
            assert operation is not None
            assert mutation is not None
            assert result is not None
            if isinstance(operation, RemoveOperation):
                assert isinstance(mutation, RemoveOrgUnitMutation)
                assert isinstance(result, UnsupportedMutation)
            if isinstance(operation, UpdateOperation):
                assert isinstance(mutation, UpdateOrgUnitMutation)
                self._assert_mutation_is(
                    "org_unit_update",
                    result,  # type: ignore
                )
            if isinstance(operation, AddOperation):
                assert isinstance(mutation, AddOrgUnitMutation)
                self._assert_mutation_is(
                    "org_unit_create",
                    result,  # type: ignore
                )

    def test_execute_handles_transportqueryerror(
        self,
        mock_graphql_session_raising_transportqueryerror: _MockGraphQLSessionRaisingTransportQueryError,
        mock_org_tree_diff: OrgTreeDiff,
    ):
        tree_diff_executor = TreeDiffExecutor(
            mock_graphql_session_raising_transportqueryerror,  # type: ignore
            mock_org_tree_diff,
        )
        for operation, mutation, result in tree_diff_executor.execute():
            if isinstance(operation, RemoveOperation):
                assert isinstance(result, UnsupportedMutation)
            else:
                assert isinstance(result, TransportQueryError)

    def test_execute_dry(
        self,
        mock_graphql_session: _MockGraphQLSession,
        mock_org_tree_diff: OrgTreeDiff,
    ):
        with patch.object(mock_graphql_session, "execute") as mock_session_execute:
            tree_diff_executor = TreeDiffExecutor(
                mock_graphql_session,  # type: ignore
                mock_org_tree_diff,
            )
            for operation, mutation in tree_diff_executor.execute_dry():
                assert operation is not None
                assert mutation is not None
                mock_session_execute.assert_not_called()  # type: ignore

    def test_get_mutation(
        self,
        mock_graphql_session: _MockGraphQLSession,
        mock_org_tree_diff: OrgTreeDiff,
        sd_expected_validity: Validity,
    ):
        tree_diff_executor = TreeDiffExecutor(
            mock_graphql_session,  # type: ignore
            mock_org_tree_diff,
        )

        # Test `RemoveOperation` produces `RemoveOrgUnitMutation`
        assert isinstance(
            tree_diff_executor.get_mutation(RemoveOperation(uuid=uuid.uuid4())),
            RemoveOrgUnitMutation,
        )

        # Test `UpdateOperation` produces `UpdateOrgUnitMutation`
        assert isinstance(
            tree_diff_executor.get_mutation(
                UpdateOperation(
                    uuid=uuid.uuid4(),
                    attr="name",
                    value="foo",
                    validity=sd_expected_validity,
                )
            ),
            UpdateOrgUnitMutation,
        )

        # Test `AddOperation` produces `AddOrgUnitMutation`
        assert isinstance(
            tree_diff_executor.get_mutation(
                AddOperation(
                    parent_uuid=uuid.uuid4(),
                    name="foo",
                    org_unit_type_uuid=uuid.uuid4(),
                    org_unit_level_uuid=uuid.uuid4(),
                    validity=sd_expected_validity,
                )
            ),
            AddOrgUnitMutation,
        )

        with pytest.raises(ValueError):
            tree_diff_executor.get_mutation(None)  # type: ignore

    def _assert_mutation_is(
        self,
        expected_name: str,
        actual_result: dict[str, Any],
    ) -> None:
        assert actual_result["name"]["value"] == expected_name
