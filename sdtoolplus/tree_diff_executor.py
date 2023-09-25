# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import abc
import datetime
from textwrap import dedent
from typing import Any
from typing import Iterator

from gql import gql
from gql.transport.exceptions import TransportQueryError
from graphql import DocumentNode
from graphql import ExecutionResult
from raclients.graph.client import GraphQLClient

from .diff_org_trees import AddOperation
from .diff_org_trees import AnyOperation
from .diff_org_trees import OrgTreeDiff
from .diff_org_trees import RemoveOperation
from .diff_org_trees import UpdateOperation


class UnsupportedMutation(Exception):
    pass


class Mutation(abc.ABC):
    def __init__(self, session: GraphQLClient, operation: AnyOperation):
        self._session = session
        self.operation = operation

    @property
    def gql(self) -> DocumentNode:
        return gql(self.query)

    @property
    def query(self) -> str:
        raise NotImplementedError("must be implemented by subclass")

    @property
    def query_args(self) -> dict[str, Any]:
        raise NotImplementedError("must be implemented by subclass")


    def execute(self) -> dict[str, Any] | ExecutionResult:
        return self._session.execute(self.gql)

class RemoveOrgUnitMutation(Mutation):
    def __init__(self, session: GraphQLClient, operation: RemoveOperation):
        super().__init__(session, operation)

    def execute(self):
        raise UnsupportedMutation(
            f"cannot terminate org units ({self.operation.uuid=})"
        )


class UpdateOrgUnitMutation(Mutation):
    def __init__(self, session: GraphQLClient, operation: UpdateOperation):
        super().__init__(session, operation)

    @property
    def query(self) -> str:
        return dedent(
            """
            mutation UpdateOrgUnit(
                $uuid: UUID!,
                $name: String!,
                $validity_from: DateTime!
            )
            {
                org_unit_update(
                    input: {
                        uuid: $uuid,
                        name: $name,
                        validity: {from: $validity_from}
                    }
                ) { uuid }
            }
            """
        )

    @property
    def query_args(self) -> dict[str, Any]:
        return {
            "uuid": str(self.operation.uuid),
            "name": self.operation.value,
            "validity_from": str(datetime.date.today()),
        }


class AddOrgUnitMutation(Mutation):
    def __init__(self, session: GraphQLClient, operation: AddOperation):
        super().__init__(session, operation)

    @property
    def query(self) -> str:
        return dedent(
            """
            mutation AddOrgUnit(
                $parent_uuid: UUID!,
                $name: String!,
                $org_unit_type_uuid: UUID!,
                $validity_from: DateTime!
            )
            {
                org_unit_create(
                    input: {
                        parent: $parent_uuid,
                        name: $name,
                        org_unit_type: $org_unit_type_uuid,
                        validity: {from: $validity_from}
                    }
                ) { uuid }
            }
            """
        )

    @property
    def query_args(self) -> dict[str, Any]:
        return {
            "parent_uuid": str(self.operation.parent_uuid),
            "name": self.operation.name,
            "org_unit_type_uuid": str(self.operation.org_unit_type_uuid),
            "validity_from": str(datetime.date.today()),
        }


AnyMutation = AddOrgUnitMutation | UpdateOrgUnitMutation | RemoveOrgUnitMutation


class TreeDiffExecutor:
    def __init__(self, session: GraphQLClient, tree_diff: OrgTreeDiff):
        self._session = session
        self._tree_diff = tree_diff

    def execute(
        self,
    ) -> Iterator[tuple[AnyOperation, AnyMutation, dict[str, Any] | Exception]]:
        for operation in self._tree_diff.get_operations():
            mutation = self.get_mutation(operation)
            try:
                result = mutation.execute()
            except UnsupportedMutation as e:
                yield operation, mutation, e
            except TransportQueryError as e:
                yield operation, mutation, e
            else:
                yield operation, mutation, result

    def execute_dry(self) -> Iterator[tuple[AnyOperation, AnyMutation]]:
        for operation in self._tree_diff.get_operations():
            mutation = self.get_mutation(operation)
            yield operation, mutation

    def get_mutation(self, operation: AnyOperation) -> AnyMutation:
        if isinstance(operation, RemoveOperation):
            return RemoveOrgUnitMutation(self._session, operation)
        if isinstance(operation, UpdateOperation):
            return UpdateOrgUnitMutation(self._session, operation)
        if isinstance(operation, AddOperation):
            return AddOrgUnitMutation(self._session, operation)
        raise ValueError("cannot get mutation for unknown operation %s" % operation)
