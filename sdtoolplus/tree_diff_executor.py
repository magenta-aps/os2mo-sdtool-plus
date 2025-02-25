# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import abc
import datetime
from typing import Any
from typing import Iterator

import structlog
from fastramqpi.raclients.graph.client import GraphQLClient
from fastramqpi.raclients.graph.client import PersistentGraphQLClient
from gql.dsl import DSLMutation
from gql.dsl import DSLSchema
from gql.dsl import DSLType
from gql.dsl import dsl_gql
from gql.transport.exceptions import TransportQueryError
from graphql import DocumentNode
from ramodels.mo import Validity
from sdclient.client import SDClient
from sdclient.date_utils import sd_date_to_mo_date_str
from sdclient.requests import GetDepartmentRequest

from .config import TIMEZONE
from .config import SDToolPlusSettings
from .diff_org_trees import OrgTreeDiff
from .filters import filter_by_uuid
from .filters import remove_by_name
from .graphql import UPDATE_ORG_UNIT
from .mo_class import MOClass
from .mo_org_unit_importer import OrgUnitNode
from .mo_org_unit_importer import OrgUnitUUID

V_DATE_OUTSIDE_ORG_UNIT_RANGE = "ErrorCodes.V_DATE_OUTSIDE_ORG_UNIT_RANGE"

logger = structlog.stdlib.get_logger()


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
        logger.debug("Updating org unit...", input=self.dsl_mutation_input)
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
        logger.debug("Creating org unit...", input=self.dsl_mutation_input)
        return DSLMutation(
            self._dsl_schema_mutation.org_unit_create.args(
                input=self.dsl_mutation_input,
            ).select(self._dsl_schema.OrganisationUnitResponse.uuid)
        )

    @property
    def dsl_mutation_input(self) -> dict[str, Any]:
        return {
            "uuid": str(self.org_unit_node.uuid),  # type: ignore
            "parent": str(self.org_unit_node.parent.uuid),  # type: ignore
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


def _fix_parent_unit_validity(
    mo_client: PersistentGraphQLClient,
    sd_client: SDClient,
    settings: SDToolPlusSettings,
    current_inst_id: str,
    org_unit_node: OrgUnitNode,
) -> None:
    if org_unit_node.parent is None:
        logger.warning("Parent is None. No-op")
        return

    logger.debug(
        "Fixing validity for parent unit",
        unit=str(org_unit_node.uuid),
        parent=str(org_unit_node.parent.uuid),
    )

    r_get_department = sd_client.get_department(
        GetDepartmentRequest(
            InstitutionIdentifier=current_inst_id,
            DepartmentUUIDIdentifier=org_unit_node.parent.uuid,
            ActivationDate=settings.min_mo_datetime.date(),
            DeactivationDate=datetime.datetime.now(tz=TIMEZONE).date(),
            DepartmentNameIndicator=True,
            UUIDIndicator=True,
        )
    )

    # Get earliest SD start date for the department
    earliest_start_date = min(dep.ActivationDate for dep in r_get_department.Department)

    # Make sure the parent validity covers the unit validity
    assert org_unit_node.validity is not None
    start_date = min(earliest_start_date, org_unit_node.validity.from_date.date())
    start_date = max(start_date, settings.min_mo_datetime.date())

    # Get latest end date for the department
    # TODO: we could potentially run into issues with an end date being smaller
    #       than the end date for the org unit itself
    end_date = max(dep.DeactivationDate for dep in r_get_department.Department)

    logger.debug(
        "Update parent org unit with new dates",
        start_date=start_date,
        end_date=end_date,
    )

    try:
        mo_client.execute(
            UPDATE_ORG_UNIT,
            variable_values={
                "input": {
                    "uuid": str(org_unit_node.parent.uuid),
                    "validity": {
                        "from": sd_date_to_mo_date_str(start_date),
                        "to": sd_date_to_mo_date_str(end_date),
                    },
                }
            },
        )
    except TransportQueryError as error:
        # TODO: there is a problem with this recursion since the following need
        #   to be addressed:
        #   1) If the call to the below _fix_parent_unit_validity raises a
        #      TransportQueryError, we need to call the above mo_client.execute
        #      again, which is currently not happening
        #   2) we also need to provide the widest validity date range to the
        #      recursion function and retry the UPDATE_ORG_UNIT call with these
        #      dates
        #   3) It has been suggested that the problem described in Redmine case
        #      #60582 can be circumvented by adding the parent to the
        #      UPDATE_ORG_UNIT in which case we effectively (maybe) trigger
        #      a correct date range validation for edit operations - this
        #      option will however not currently be pursued due to time issues
        #   Due to the issue in #60582 the call below to to
        #   _fix_parent_unit_validity will never raise an exception, i.e.
        #   we will current not run into any issues - other than inconsistent
        #   data in MO requiring fixing by custom scripts :-)
        if V_DATE_OUTSIDE_ORG_UNIT_RANGE in str(error):
            _fix_parent_unit_validity(
                mo_client, sd_client, settings, current_inst_id, org_unit_node.parent
            )
        else:
            raise error


def _truncate_start_date(
    org_unit_node: OrgUnitNode, min_start_date: datetime.datetime
) -> None:
    """
    Truncate the start date of the unit to min_start_date, if the start date
    of the unit is before this date.

    Args:
        org_unit_node: the unit to truncate
        min_start_date: the minimum start date of the unit
    """
    assert org_unit_node.validity is not None
    org_unit_node.validity = Validity(
        from_date=max(org_unit_node.validity.from_date, min_start_date),
        to_date=org_unit_node.validity.to_date,
    )


class TreeDiffExecutor:
    def __init__(
        self,
        session: PersistentGraphQLClient,
        settings: SDToolPlusSettings,
        current_inst_id: str,
        tree_diff: OrgTreeDiff,
        mo_org_unit_type: MOClass,
    ):
        self._session = session
        self.settings = settings
        self.current_inst_id = current_inst_id
        self._tree_diff = tree_diff
        self.mo_org_unit_type = mo_org_unit_type

        self.sd_client = SDClient(
            self.settings.sd_username,
            self.settings.sd_password.get_secret_value(),
        )

        logger.debug(
            "Regexs for units to remove by name",
            regexs=self.settings.regex_unit_names_to_remove,
        )

    def _add_unit(self, add_mutation: AnyMutation, unit: OrgUnitNode) -> OrgUnitUUID:
        try:
            result = add_mutation.execute()
        except TransportQueryError as error:
            logger.warning(
                "Date outside org unit range",
                unit_uuid=str(unit.uuid),
                parent_uuid=str(unit.parent.uuid),
            )
            if V_DATE_OUTSIDE_ORG_UNIT_RANGE in str(error):
                _fix_parent_unit_validity(
                    self._session,
                    self.sd_client,
                    self.settings,
                    self.current_inst_id,
                    unit,
                )
            else:
                raise error
            result = add_mutation.execute()
        return result

    def execute(
        self, org_unit: OrgUnitUUID | None = None, dry_run: bool = False
    ) -> Iterator[tuple[OrgUnitNode, AnyMutation, OrgUnitUUID]]:
        # Add new units first
        units_to_add = filter_by_uuid(org_unit, self._tree_diff.get_units_to_add())
        units_to_add = remove_by_name(
            self.settings.regex_unit_names_to_remove, units_to_add
        )
        for unit in units_to_add:
            logger.info(
                "Add unit",
                unit=str(unit.uuid),
                name=unit.name,
                parent=str(unit.parent.uuid),
            )

            # Not optimal - we are mutating the loop variable...
            _truncate_start_date(unit, self.settings.min_mo_datetime)

            add_mutation = AddOrgUnitMutation(
                self._session, unit, self.mo_org_unit_type
            )
            if not dry_run:
                # TODO: remove if-clause below once the integration test
                #  sdtoolplus.tests.integration.test_tree_structure
                #  .test_build_tree_date_range_errors
                #  is passing (awaiting #60582)
                if self.settings.extend_parent_validities:
                    result = self._add_unit(add_mutation, unit)
                else:
                    result = add_mutation.execute()
            else:
                result = unit.uuid
            yield unit, add_mutation, result

        # ... and then update modified units (name or parent changed)
        units_to_update = filter_by_uuid(
            org_unit, self._tree_diff.get_units_to_update()
        )
        if self.settings.apply_name_filter_on_update:
            units_to_update = remove_by_name(
                self.settings.regex_unit_names_to_remove, units_to_update
            )
        for unit in units_to_update:
            logger.info("Update unit", unit=str(unit.uuid), name=unit.name)
            update_mutation = UpdateOrgUnitMutation(self._session, unit)
            if not dry_run:
                result = update_mutation.execute()
            else:
                result = unit.uuid
            yield unit, update_mutation, result
