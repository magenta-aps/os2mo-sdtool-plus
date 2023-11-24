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

from ..diff_org_trees import OrgTreeDiff
from ..mo_class import MOClass
from ..mo_org_unit_importer import OrgUnitNode
from ..tree_diff_executor import AddOrgUnitMutation
from ..tree_diff_executor import Mutation
from ..tree_diff_executor import TreeDiffExecutor
from ..tree_diff_executor import UpdateOrgUnitMutation
from .conftest import _MockGraphQLSession
from .conftest import _MockGraphQLSessionRaisingTransportQueryError


@pytest.fixture()
def mutation_instance(graphql_testing_schema: GraphQLSchema) -> Mutation:
    return Mutation(
        _MockGraphQLSession(graphql_testing_schema),  # type: ignore
        OrgUnitNode(
            uuid=uuid.uuid4(),
            name="name",
            parent_uuid=uuid.uuid4(),
        ),  # type: ignore
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
        mock_mo_org_unit_type: MOClass,
    ):
        tree_diff_executor = TreeDiffExecutor(
            mock_graphql_session,  # type: ignore
            mock_org_tree_diff,
            mock_mo_org_unit_type,
        )
        for org_unit_node, mutation, result in tree_diff_executor.execute():
            assert org_unit_node is not None
            assert mutation is not None
            assert result is not None
            if isinstance(mutation, UpdateOrgUnitMutation):
                assert isinstance(org_unit_node, OrgUnitNode)
                assert (
                    result == org_unit_node.uuid
                )  # Result is UUID of updated org unit
            if isinstance(mutation, AddOrgUnitMutation):
                assert isinstance(org_unit_node, OrgUnitNode)
                assert isinstance(result, uuid.UUID)  # Result is UUID of new org unit
                assert result == org_unit_node.uuid

    @freeze_time("2023-11-15")
    def test_execute_for_move_afd_from_ny_to_ny(
        self,
        mock_graphql_session: _MockGraphQLSession,
        mock_org_tree_diff_move_afd_from_ny_to_ny: OrgTreeDiff,
        mock_mo_org_unit_type,
    ):
        """
        Test the case where we move an SD "Afdelings-niveau" from
        one "NY-niveau" to another
        """

        # Arrange
        ou_uuid = uuid.UUID("40000000-0000-0000-0000-000000000000")
        new_parent_uuid = uuid.UUID("50000000-0000-0000-0000-000000000000")
        move_date = date(2023, 11, 15)

        tree_diff_executor = TreeDiffExecutor(
            mock_graphql_session,  # type: ignore
            mock_org_tree_diff_move_afd_from_ny_to_ny,
            mock_mo_org_unit_type,
        )

        # Act
        org_unit_node, mutation, result = one(tree_diff_executor.execute())

        # Assert
        assert isinstance(org_unit_node, OrgUnitNode)
        assert org_unit_node.uuid == ou_uuid
        assert org_unit_node.parent.uuid == new_parent_uuid

        assert mutation.dsl_mutation_input["uuid"] == str(ou_uuid)
        assert mutation.dsl_mutation_input["name"] == "Department 4"
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
        mock_mo_org_unit_type,
    ):
        tree_diff_executor = TreeDiffExecutor(
            mock_graphql_session_raising_transportqueryerror,  # type: ignore
            mock_org_tree_diff,
            mock_mo_org_unit_type,
        )
        for operation, mutation, result in tree_diff_executor.execute():
            assert isinstance(result, TransportQueryError)

    def test_execute_dry(
        self,
        mock_graphql_session: _MockGraphQLSession,
        mock_org_tree_diff: OrgTreeDiff,
        mock_mo_org_unit_type: MOClass,
    ):
        with patch.object(mock_graphql_session, "execute") as mock_session_execute:
            tree_diff_executor = TreeDiffExecutor(
                mock_graphql_session,  # type: ignore
                mock_org_tree_diff,
                mock_mo_org_unit_type,
            )
            for operation, mutation, result in tree_diff_executor.execute(dry_run=True):
                assert operation is not None
                assert mutation is not None
                assert result is not None
                mock_session_execute.assert_not_called()  # type: ignore
