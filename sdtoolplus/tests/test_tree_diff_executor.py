# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import uuid
from datetime import date
from datetime import datetime
from unittest.mock import patch

import pytest
from freezegun import freeze_time
from gql.transport.exceptions import TransportQueryError
from graphql import GraphQLSchema
from more_itertools import one
from ramodels.mo import Validity

from ..diff_org_trees import AddOperation
from ..diff_org_trees import MoveOperation
from ..diff_org_trees import Operation
from ..diff_org_trees import OrgTreeDiff
from ..diff_org_trees import UpdateOperation
from ..tree_diff_executor import AddOrgUnitMutation
from ..tree_diff_executor import MoveOrgUnitMutation
from ..tree_diff_executor import Mutation
from ..tree_diff_executor import TreeDiffExecutor
from ..tree_diff_executor import UnsupportedMutation
from ..tree_diff_executor import UpdateOrgUnitMutation
from .conftest import _MockGraphQLSession
from .conftest import _MockGraphQLSessionRaisingTransportQueryError


@pytest.fixture()
def mutation_instance(graphql_testing_schema: GraphQLSchema) -> Mutation:
    return Mutation(
        _MockGraphQLSession(graphql_testing_schema),  # type: ignore
        Operation(),  # type: ignore
    )


class TestMutation:
    def test_abstract_methods(self, mutation_instance: Mutation) -> None:
        with pytest.raises(NotImplementedError):
            mutation_instance.dsl_mutation
        with pytest.raises(NotImplementedError):
            mutation_instance.dsl_mutation_input

    def test_get_validity_dict_or_none(self, mutation_instance: Mutation) -> None:
        assert mutation_instance._get_validity_dict_or_none(None) is None  # type: ignore


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
            if isinstance(operation, UpdateOperation):
                assert isinstance(mutation, UpdateOrgUnitMutation)
                assert result == operation.uuid  # Result is UUID of updated org unit
            if isinstance(operation, AddOperation):
                assert isinstance(mutation, AddOrgUnitMutation)
                assert isinstance(result, uuid.UUID)  # Result is UUID of new org unit
                assert result == operation.uuid

    @freeze_time("2023-11-15")
    def test_execute_for_move_ou_scenario(
        self,
        mock_graphql_session: _MockGraphQLSession,
        mock_org_tree_diff_move_case: OrgTreeDiff,
    ):
        # Arrange
        ou_uuid = uuid.UUID("40000000-0000-0000-0000-000000000000")
        new_parent_uuid = uuid.UUID("50000000-0000-0000-0000-000000000000")
        move_date = date(2023, 11, 15)

        tree_diff_executor = TreeDiffExecutor(
            mock_graphql_session,  # type: ignore
            mock_org_tree_diff_move_case,
        )

        # Act
        operation, mutation, result = one(tree_diff_executor.execute())

        # Assert
        assert isinstance(operation, MoveOperation)
        assert operation.uuid == ou_uuid
        assert operation.parent == new_parent_uuid
        assert operation.validity.from_date.date() == move_date

        assert mutation.dsl_mutation_input["uuid"] == str(ou_uuid)
        assert mutation.dsl_mutation_input["parent"] == str(new_parent_uuid)
        assert (
            datetime.fromisoformat(
                mutation.dsl_mutation_input["validity"].get("from")
            ).date()
            == move_date
        )

        assert result == uuid.UUID("40000000-0000-0000-0000-000000000000")

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
            if isinstance(operation, MoveOperation):
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

        # Test `MoveOperation` produces `MoveOrgUnitMutation`
        assert isinstance(
            tree_diff_executor.get_mutation(
                MoveOperation(
                    uuid=uuid.uuid4(),
                    parent=uuid.uuid4(),
                    validity=Validity(from_date=datetime.now()),
                )
            ),
            MoveOrgUnitMutation,
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
                    uuid=uuid.uuid4(),
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
