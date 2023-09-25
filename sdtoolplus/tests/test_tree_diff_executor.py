# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import uuid
from unittest.mock import Mock

import pytest
from gql.transport.exceptions import TransportQueryError

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
    def test_abstract_methods(self):
        instance = Mutation(Operation())
        with pytest.raises(NotImplementedError):
            instance.query
        with pytest.raises(NotImplementedError):
            instance.query_args


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
                assert result == {"name": "UpdateOrgUnit"}
            if isinstance(operation, AddOperation):
                assert isinstance(mutation, AddOrgUnitMutation)
                assert result == {"name": "AddOrgUnit"}

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

    def test_execute_dry(self, mock_org_tree_diff: OrgTreeDiff):
        mock_session = Mock()
        tree_diff_executor = TreeDiffExecutor(mock_session, mock_org_tree_diff)
        for operation, mutation in tree_diff_executor.execute_dry():
            assert operation is not None
            assert mutation is not None
            tree_diff_executor._session.execute.assert_not_called()  # type: ignore

    def test_get_mutation(self):
        tree_diff_executor = TreeDiffExecutor(
            None,  # type: ignore
            None,  # type: ignore
        )

        assert isinstance(
            tree_diff_executor.get_mutation(RemoveOperation(uuid=uuid.uuid4())),
            RemoveOrgUnitMutation,
        )

        assert isinstance(
            tree_diff_executor.get_mutation(
                UpdateOperation(
                    uuid=uuid.uuid4(),
                    attr="name",
                    value="foo",
                )
            ),
            UpdateOrgUnitMutation,
        )

        assert isinstance(
            tree_diff_executor.get_mutation(
                AddOperation(
                    parent_uuid=uuid.uuid4(),
                    name="foo",
                    org_unit_type_uuid=uuid.uuid4(),
                )
            ),
            AddOrgUnitMutation,
        )

        with pytest.raises(ValueError):
            tree_diff_executor.get_mutation(None)  # type: ignore
