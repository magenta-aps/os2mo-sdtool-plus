# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import abc
import datetime
from typing import Any
from typing import Iterator

import structlog
from fastramqpi.raclients.graph.client import GraphQLClient
from gql.dsl import dsl_gql
from gql.dsl import DSLMutation
from gql.dsl import DSLSchema
from gql.dsl import DSLType
from graphql import DocumentNode
from ramodels.mo import Validity

from .diff_org_trees import OrgTreeDiff
from .filters import filter_by_uuid
from .filters import remove_by_name
from .mo_class import MOClass
from .mo_org_unit_importer import OrgUnitNode
from .mo_org_unit_importer import OrgUnitUUID

logger = structlog.get_logger()


class Mutation(abc.ABC):
    def __init__(self, session: GraphQLClient, org_unit_node: OrgUnitNode):
        self._session = session
        self.org_unit_node = org_unit_node
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


class UpdateOrgUnitMutation(Mutation):
    def __init__(self, session: GraphQLClient, org_unit_node: OrgUnitNode):
        super().__init__(session, org_unit_node)

    @property
    def dsl_mutation(self) -> DSLMutation:
        logger.info("Updating org unit...", input=self.dsl_mutation_input)
        expr = self._dsl_schema_mutation.org_unit_update.args(
            input=self.dsl_mutation_input,
        )
        return DSLMutation(expr.select(self._dsl_schema.OrganisationUnitResponse.uuid))

    @property
    def dsl_mutation_input(self) -> dict[str, Any]:
        return {
            "uuid": str(self.org_unit_node.uuid),  # type: ignore
            "name": self.org_unit_node.name,  # type: ignore
            "user_key": self.org_unit_node.user_key,  # type: ignore
            "parent": str(self.org_unit_node.parent.uuid),
            "validity": {
                "from": datetime.datetime.now().date().strftime("%Y-%m-%d"),
                "to": self.org_unit_node.validity.to_date.date().strftime("%Y-%m-%d")  # type: ignore
                if self.org_unit_node.validity.to_date is not None  # type: ignore
                else None,
            },
        }

    def execute(self) -> OrgUnitUUID:
        result: dict = self._session.execute(self.gql)
        return OrgUnitUUID(result["org_unit_update"]["uuid"])


class AddOrgUnitMutation(Mutation):
    def __init__(
        self,
        session: GraphQLClient,
        org_unit_node: OrgUnitNode,
        mo_org_unit_type: MOClass,
    ):
        super().__init__(session, org_unit_node)
        self.mo_org_unit_type = mo_org_unit_type

    @property
    def dsl_mutation(self) -> DSLMutation:
        logger.info("Creating org unit...", input=self.dsl_mutation_input)
        return DSLMutation(
            self._dsl_schema_mutation.org_unit_create.args(
                input=self.dsl_mutation_input,
            ).select(self._dsl_schema.OrganisationUnitResponse.uuid)
        )

    @property
    def dsl_mutation_input(self) -> dict[str, Any]:
        return {
            "uuid": str(self.org_unit_node.uuid),  # type: ignore
            "parent": str(self.org_unit_node.parent_uuid),  # type: ignore
            "user_key": self.org_unit_node.user_key,
            "name": self.org_unit_node.name,  # type: ignore
            "org_unit_type": str(self.mo_org_unit_type.uuid),  # type: ignore
            "org_unit_level": str(self.org_unit_node.org_unit_level_uuid),  # type: ignore
            "validity": self._get_validity_dict_or_none(self.org_unit_node.validity),  # type: ignore
        }

    def execute(self) -> OrgUnitUUID:
        result: dict = self._session.execute(self.gql)
        return OrgUnitUUID(result["org_unit_create"]["uuid"])


AnyMutation = AddOrgUnitMutation | UpdateOrgUnitMutation


class TreeDiffExecutor:
    def __init__(
        self,
        session: GraphQLClient,
        tree_diff: OrgTreeDiff,
        mo_org_unit_type: MOClass,
        regex_unit_names_to_remove: list[str],
    ):
        self._session = session
        self._tree_diff = tree_diff
        self.mo_org_unit_type = mo_org_unit_type
        self.regex_unit_names_to_remove = regex_unit_names_to_remove

        logger.debug(
            "Regexs for units to remove by name", regexs=regex_unit_names_to_remove
        )

    def execute(
        self, org_unit: OrgUnitUUID | None = None, dry_run: bool = False
    ) -> Iterator[tuple[OrgUnitNode, AnyMutation, OrgUnitUUID]]:
        # Add new units first
        units_to_add = filter_by_uuid(org_unit, self._tree_diff.get_units_to_add())
        units_to_add = remove_by_name(self.regex_unit_names_to_remove, units_to_add)
        for unit in units_to_add:
            add_mutation = AddOrgUnitMutation(
                self._session, unit, self.mo_org_unit_type
            )
            if not dry_run:
                result = add_mutation.execute()
            else:
                result = unit.uuid
            yield unit, add_mutation, result

        # ... and then update modified units (name or parent changed)
        units_to_update = filter_by_uuid(
            org_unit, self._tree_diff.get_units_to_update()
        )
        units_to_update = remove_by_name(
            self.regex_unit_names_to_remove, units_to_update
        )
        for unit in units_to_update:
            update_mutation = UpdateOrgUnitMutation(self._session, unit)
            if not dry_run:
                result = update_mutation.execute()
            else:
                result = unit.uuid
            yield unit, update_mutation, result
