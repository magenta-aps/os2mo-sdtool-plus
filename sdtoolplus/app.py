# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from typing import Iterator
from typing import Optional
from uuid import UUID

import httpx
import sentry_sdk
import structlog
from httpx import Response
from raclients.graph.client import PersistentGraphQLClient
from sdclient.client import SDClient

from .config import SDToolPlusSettings
from .diff_org_trees import AddOperation
from .diff_org_trees import AnyOperation
from .diff_org_trees import OrgTreeDiff
from .diff_org_trees import UpdateOperation
from .log import setup_logging
from .mo_class import MOClass
from .mo_class import MOOrgUnitLevelMap
from .mo_class import MOOrgUnitTypeMap
from .mo_org_unit_importer import MOOrgTreeImport
from .mo_org_unit_importer import OrgUnitUUID
from .sd.importer import get_sd_tree
from .tree_diff_executor import AnyMutation
from .tree_diff_executor import TreeDiffExecutor


logger = structlog.get_logger()


class App:
    def __init__(self, settings: SDToolPlusSettings):
        self.settings: SDToolPlusSettings = settings

        setup_logging(self.settings.log_level)

        if self.settings.sentry_dsn:
            sentry_sdk.init(dsn=self.settings.sentry_dsn)

        self.session = PersistentGraphQLClient(
            url=f"{self.settings.mora_base}/graphql/v7",
            client_id=self.settings.client_id,
            client_secret=self.settings.client_secret.get_secret_value(),
            auth_realm=self.settings.auth_realm,
            auth_server=self.settings.auth_server,  # type: ignore
            sync=True,
            httpx_client_kwargs={"timeout": None},
            fetch_schema_from_transport=True,
        )

        self.client = httpx.Client(base_url=self.settings.sd_lon_base_url)

    def get_tree_diff_executor(self) -> TreeDiffExecutor:
        # Get relevant MO facet/class data
        mo_org_unit_type_map = MOOrgUnitTypeMap(self.session)
        mo_org_unit_type: MOClass = mo_org_unit_type_map[self.settings.org_unit_type]
        mo_org_unit_level_map = MOOrgUnitLevelMap(self.session)

        # Get the MO tree
        logger.info(event="Fetching MO org tree ...")
        mo_org_tree = MOOrgTreeImport(self.session)

        # Get the SD tree
        logger.info(event="Fetching SD org tree ...")
        sd_client = SDClient(
            self.settings.sd_username,
            self.settings.sd_password.get_secret_value(),
        )
        sd_org_tree = get_sd_tree(
            sd_client,
            self.settings.sd_institution_identifier,
            mo_org_unit_level_map,
        )

        # Construct org tree diff
        tree_diff = OrgTreeDiff(
            mo_org_tree.as_single_tree(), sd_org_tree, mo_org_unit_type
        )

        # Construct tree diff executor
        return TreeDiffExecutor(self.session, tree_diff)

    def execute(
        self,
    ) -> Iterator[tuple[AnyOperation, AnyMutation, UUID | Exception, Optional[bool]]]:
        """Call `TreeDiffExecutor.execute`, and call the SDLøn 'fix_departments' API
        for each 'add' and 'update' operation.
        """
        executor: TreeDiffExecutor = self.get_tree_diff_executor()
        operation: AnyOperation
        mutation: AnyMutation
        result: UUID | Exception
        fix_departments_result: bool | None
        for operation, mutation, result in executor.execute():
            fix_departments_result = None
            if isinstance(operation, (AddOperation, UpdateOperation)):
                fix_departments_result = self._call_fix_departments(result)  # type: ignore
            yield (
                operation,
                mutation,
                result,
                fix_departments_result,
            )

    def execute_dry(self) -> Iterator[tuple[AnyOperation, AnyMutation]]:
        executor: TreeDiffExecutor = self.get_tree_diff_executor()
        operation: AnyOperation
        mutation: AnyMutation
        for operation, mutation in executor.execute_dry():
            yield operation, mutation

    def _call_fix_departments(self, org_unit_uuid: OrgUnitUUID) -> bool:
        url: str = f"/trigger/fix-departments/{org_unit_uuid}"
        response: Response = self.client.post(url)
        if response.status_code >= 400:
            logger.error(
                "fix_departments returned an error: status_code=%d, response=%r",
                response.status_code,
                response.json(),
            )
        return response.status_code == 200

    @staticmethod
    def _get_effective_root_path(path_ou_uuids: list[OrgUnitUUID]):
        return "/".join([str(ou_uuid) for ou_uuid in path_ou_uuids])
