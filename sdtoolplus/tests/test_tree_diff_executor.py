# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import uuid
from datetime import date
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time
from graphql import GraphQLSchema
from more_itertools import one
from ramodels.mo import Validity

from ..config import SDToolPlusSettings
from ..diff_org_trees import OrgTreeDiff
from ..mo_class import MOClass
from ..mo_org_unit_importer import OrgUnitNode
from ..tree_diff_executor import _truncate_start_date
from ..tree_diff_executor import AddOrgUnitMutation
from ..tree_diff_executor import Mutation
from ..tree_diff_executor import TIMEZONE
from ..tree_diff_executor import TreeDiffExecutor
from ..tree_diff_executor import UpdateOrgUnitMutation
from .conftest import _MockGraphQLSession


@pytest.fixture()
def mutation_instance(graphql_testing_schema: GraphQLSchema) -> Mutation:
    return Mutation(
        _MockGraphQLSession(graphql_testing_schema),  # type: ignore
        OrgUnitNode(
            uuid=uuid.uuid4(),
            user_key="user_key",
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


class TestAddOrgUnitMutation:
    def test_dsl_mutation_input(
        self, mock_graphql_session, sd_expected_validity, mock_mo_org_unit_type
    ) -> None:
        # Arrange
        unit_uuid = uuid.uuid4()
        parent_uuid = uuid.uuid4()
        org_unit_level_uuid = uuid.uuid4()

        parent = OrgUnitNode(
            uuid=parent_uuid,
            parent=None,
            user_key="root",
            name="<root>",
            org_unit_level_uuid=org_unit_level_uuid,
            validity=sd_expected_validity,
        )

        org_unit_node = OrgUnitNode(
            uuid=unit_uuid,
            parent=parent,
            user_key="dep",
            name="Department",
            org_unit_level_uuid=org_unit_level_uuid,
            validity=sd_expected_validity,
        )

        add_mutation = AddOrgUnitMutation(
            mock_graphql_session,
            org_unit_node,
            mock_mo_org_unit_type,
        )

        # Act
        mutation_input = add_mutation.dsl_mutation_input

        # Assert
        assert mutation_input == {
            "uuid": str(unit_uuid),
            "parent": str(parent_uuid),
            "user_key": "dep",
            "name": "Department",
            "org_unit_type": str(mock_mo_org_unit_type.uuid),
            "org_unit_level": str(org_unit_level_uuid),
            "validity": {
                "from": "1999-01-01T00:00:00+01:00",
                "to": None,
            },
        }


class TestTreeDiffExecutor:
    def test_execute(
        self,
        mock_graphql_session: _MockGraphQLSession,
        mock_org_tree_diff: OrgTreeDiff,
        mock_mo_org_unit_type: MOClass,
        sdtoolplus_settings: SDToolPlusSettings,
    ):
        tree_diff_executor = TreeDiffExecutor(
            mock_graphql_session,  # type: ignore
            sdtoolplus_settings,
            mock_org_tree_diff,
            mock_mo_org_unit_type,
            [],
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
        sdtoolplus_settings: SDToolPlusSettings,
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
            sdtoolplus_settings,
            mock_org_tree_diff_move_afd_from_ny_to_ny,
            mock_mo_org_unit_type,
            [],
        )

        # Act
        org_unit_node, mutation, result = one(tree_diff_executor.execute())

        # Assert
        assert isinstance(org_unit_node, OrgUnitNode)
        assert org_unit_node.uuid == ou_uuid
        assert org_unit_node.parent.uuid == new_parent_uuid

        assert mutation.dsl_mutation_input["uuid"] == str(ou_uuid)
        assert mutation.dsl_mutation_input["name"] == "Department 4"
        assert mutation.dsl_mutation_input["user_key"] == "dep4"
        assert mutation.dsl_mutation_input["parent"] == str(new_parent_uuid)
        assert (
            datetime.fromisoformat(
                mutation.dsl_mutation_input["validity"].get("from")
            ).date()
            == move_date
        )

        assert result == uuid.UUID("40000000-0000-0000-0000-000000000000")

    def test_execute_dry(
        self,
        mock_graphql_session: _MockGraphQLSession,
        mock_org_tree_diff: OrgTreeDiff,
        mock_mo_org_unit_type: MOClass,
        sdtoolplus_settings: SDToolPlusSettings,
    ):
        with patch.object(mock_graphql_session, "execute") as mock_session_execute:
            tree_diff_executor = TreeDiffExecutor(
                mock_graphql_session,  # type: ignore
                sdtoolplus_settings,
                mock_org_tree_diff,
                mock_mo_org_unit_type,
                [],
            )
            for org_unit_node, mutation, result in tree_diff_executor.execute(
                dry_run=True
            ):
                assert org_unit_node is not None
                assert mutation is not None
                assert result is not None
                mock_session_execute.assert_not_called()  # type: ignore

    def test_execute_filter_by_uuid(
        self,
        mock_graphql_session: _MockGraphQLSession,
        mock_org_tree_diff: OrgTreeDiff,
        mock_mo_org_unit_type: MOClass,
        sdtoolplus_settings: SDToolPlusSettings,
    ):
        # Arrange
        tree_diff_executor = TreeDiffExecutor(
            mock_graphql_session,  # type: ignore
            sdtoolplus_settings,
            mock_org_tree_diff,
            mock_mo_org_unit_type,
            [],
        )

        # Act
        org_unit_node, mutation, result = one(
            tree_diff_executor.execute(
                org_unit=uuid.UUID("60000000-0000-0000-0000-000000000000")
            )
        )

        # Assert
        assert org_unit_node.uuid == uuid.UUID("60000000-0000-0000-0000-000000000000")

    def test_execute_remove_by_name(
        self,
        mock_graphql_session: _MockGraphQLSession,
        mock_org_tree_diff: OrgTreeDiff,
        mock_mo_org_unit_type: MOClass,
        sdtoolplus_settings: SDToolPlusSettings,
    ):
        # Arrange
        tree_diff_executor = TreeDiffExecutor(
            mock_graphql_session,  # type: ignore
            sdtoolplus_settings,
            mock_org_tree_diff,
            mock_mo_org_unit_type,
            ["^.*5$", "^.*6$"],
        )

        # Act
        units_to_mutate: list[tuple] = list(tree_diff_executor.execute())

        # Assert
        unit_names = [tup[0].name for tup in units_to_mutate]
        assert "Department 5" not in unit_names
        assert "Department 6" not in unit_names


@pytest.mark.parametrize(
    "initial_start_date, expected",
    [
        (datetime(1999, 1, 1, tzinfo=TIMEZONE), datetime(2000, 1, 1, tzinfo=TIMEZONE)),
        (datetime(2001, 1, 1, tzinfo=TIMEZONE), datetime(2001, 1, 1, tzinfo=TIMEZONE)),
    ],
)
def test_truncate_start_date(
    initial_start_date: datetime, expected: datetime, random_org_unit_node: OrgUnitNode
) -> None:
    # Arrange
    random_org_unit_node.validity = Validity(from_date=initial_start_date)

    # Act
    _truncate_start_date(random_org_unit_node, datetime(2000, 1, 1, tzinfo=TIMEZONE))

    # Assert
    assert random_org_unit_node.validity.from_date == expected
