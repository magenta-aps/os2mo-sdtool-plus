# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import abc
import uuid
from typing import Any
from typing import Iterator

from gql.dsl import dsl_gql
from gql.dsl import DSLMutation
from gql.dsl import DSLSchema
from gql.dsl import DSLType
from gql.transport.exceptions import TransportQueryError
from graphql import DocumentNode
from raclients.graph.client import GraphQLClient
from ramodels.mo import Validity

from .diff_org_trees import AddOperation
from .diff_org_trees import AnyOperation
from .diff_org_trees import MoveOperation
from .diff_org_trees import OrgTreeDiff
from .diff_org_trees import UpdateOperation


class UnsupportedMutation(Exception):
    pass


class Mutation(abc.ABC):
    def __init__(self, session: GraphQLClient, operation: AnyOperation):
        self._session = session
        self.operation = operation
        self._dsl_schema = self._get_dsl_schema()

    @property
    def gql(self) -> DocumentNode:
        return dsl_gql(self.dsl_mutation)

    @property
    def dsl_mutation(self) -> DSLMutation:
        raise NotImplementedError("must be implemented by subclass")

    @property
    def dsl_mutation_input(self) -> dict[str, Any]:
        raise NotImplementedError("must be implemented by subclass")

    @property
    def _dsl_schema_mutation(self) -> DSLType:
        return self._dsl_schema.Mutation

    def _get_dsl_schema(self) -> DSLSchema:
        return DSLSchema(self._session.schema)  # type: ignore

    def _get_validity_dict_or_none(
        self, validity: Validity
    ) -> dict[str, str | None] | None:
        if validity is not None:
            return {
                "from": validity.from_date.isoformat(),
                "to": validity.to_date.isoformat() if validity.to_date else None,
            }
        return None


class MoveOrgUnitMutation(Mutation):
    def __init__(self, session: GraphQLClient, operation: MoveOperation):
        super().__init__(session, operation)

    @property
    def dsl_mutation(self) -> DSLMutation:
        expr = self._dsl_schema_mutation.org_unit_update.args(
            input=self.dsl_mutation_input,
        )
        return DSLMutation(expr.select(self._dsl_schema.OrganisationUnitResponse.uuid))

    @property
    def dsl_mutation_input(self) -> dict[str, Any]:
        return {
            "uuid": str(self.operation.uuid),  # type: ignore
            "parent": str(self.operation.parent),  # type: ignore
            "validity": self._get_validity_dict_or_none(self.operation.validity),  # type: ignore
        }

    def execute(self) -> uuid.UUID:
        result: dict = self._session.execute(self.gql)
        return uuid.UUID(result["org_unit_update"]["uuid"])


class UpdateOrgUnitMutation(Mutation):
    def __init__(self, session: GraphQLClient, operation: UpdateOperation):
        super().__init__(session, operation)

    @property
    def dsl_mutation(self) -> DSLMutation:
        expr = self._dsl_schema_mutation.org_unit_update.args(
            input=self.dsl_mutation_input,
        )
        return DSLMutation(expr.select(self._dsl_schema.OrganisationUnitResponse.uuid))

    @property
    def dsl_mutation_input(self) -> dict[str, Any]:
        return {
            "uuid": str(self.operation.uuid),  # type: ignore
            self.operation.attr: self.operation.value,  # type: ignore
            "validity": self._get_validity_dict_or_none(self.operation.validity),  # type: ignore
        }

    def execute(self) -> uuid.UUID:
        result: dict = self._session.execute(self.gql)
        return uuid.UUID(result["org_unit_update"]["uuid"])


class AddOrgUnitMutation(Mutation):
    def __init__(self, session: GraphQLClient, operation: AddOperation):
        super().__init__(session, operation)

    @property
    def dsl_mutation(self) -> DSLMutation:
        return DSLMutation(
            self._dsl_schema_mutation.org_unit_create.args(
                input=self.dsl_mutation_input,
            ).select(self._dsl_schema.OrganisationUnitResponse.uuid)
        )

    @property
    def dsl_mutation_input(self) -> dict[str, Any]:
        return {
            "uuid": str(self.operation.uuid),  # type: ignore
            "parent": str(self.operation.parent_uuid),  # type: ignore
            "name": self.operation.name,  # type: ignore
            "org_unit_type": str(self.operation.org_unit_type_uuid),  # type: ignore
            "org_unit_level": str(self.operation.org_unit_level_uuid),  # type: ignore
            "validity": self._get_validity_dict_or_none(self.operation.validity),  # type: ignore
        }

    def execute(self) -> uuid.UUID:
        result: dict = self._session.execute(self.gql)
        return uuid.UUID(result["org_unit_create"]["uuid"])


AnyMutation = AddOrgUnitMutation | UpdateOrgUnitMutation | MoveOrgUnitMutation


class TreeDiffExecutor:
    def __init__(self, session: GraphQLClient, tree_diff: OrgTreeDiff):
        self._session = session
        self._tree_diff = tree_diff

    def execute(
        self,
    ) -> Iterator[tuple[AnyOperation, AnyMutation, uuid.UUID | Exception]]:
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
        if isinstance(operation, MoveOperation):
            return MoveOrgUnitMutation(self._session, operation)
        if isinstance(operation, UpdateOperation):
            return UpdateOrgUnitMutation(self._session, operation)
        if isinstance(operation, AddOperation):
            return AddOrgUnitMutation(self._session, operation)
        raise ValueError(f"cannot get mutation for unknown operation {operation}")
