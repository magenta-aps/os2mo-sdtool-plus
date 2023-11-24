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
from .diff_org_trees import OrgTreeDiff
from .log import setup_logging
from .mo_class import MOClass
from .mo_class import MOOrgUnitLevelMap
from .mo_class import MOOrgUnitTypeMap
from .mo_org_unit_importer import MOOrgTreeImport
from .mo_org_unit_importer import OrgUnitNode
from .mo_org_unit_importer import OrgUnitUUID
from .sd.importer import get_sd_tree
from .tree_diff_executor import AddOrgUnitMutation
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

    def get_sd_tree(self) -> OrgUnitNode:
        mo_org_unit_level_map = MOOrgUnitLevelMap(self.session)
        sd_client = SDClient(
            self.settings.sd_username,
            self.settings.sd_password.get_secret_value(),
        )
        return get_sd_tree(
            sd_client,
            self.settings.sd_institution_identifier,
            mo_org_unit_level_map,
        )

    def get_mo_tree(self) -> OrgUnitNode:
        mo_org_tree_import = MOOrgTreeImport(self.session)
        mo_subtree_path_for_root = App._get_effective_root_path(
            self.settings.mo_subtree_path_for_root
        )
        return mo_org_tree_import.as_single_tree(mo_subtree_path_for_root)

    def get_tree_diff_executor(self) -> TreeDiffExecutor:
        logger.debug("Getting TreeDiffExecutor")

        # Get relevant MO facet/class data
        mo_org_unit_type_map = MOOrgUnitTypeMap(self.session)
        mo_org_unit_type: MOClass = mo_org_unit_type_map[self.settings.org_unit_type]

        # Get the SD tree
        logger.info(event="Fetching SD org tree ...")
        sd_org_tree = self.get_sd_tree()
        logger.debug(
            "SD tree",
            sd_org_tree=repr(sd_org_tree),
            children=[repr(child) for child in sd_org_tree.children],
        )

        # Get the MO tree
        logger.info(event="Fetching MO org tree ...")
        mo_org_tree_as_single = self.get_mo_tree()
        logger.debug(
            "MO tree",
            mo_org_tree=repr(mo_org_tree_as_single),
            children=[repr(child) for child in mo_org_tree_as_single.children],
        )

        # Construct org tree diff
        tree_diff = OrgTreeDiff(
            mo_org_tree_as_single,
            sd_org_tree,
        )

        # Construct tree diff executor
        return TreeDiffExecutor(self.session, tree_diff, mo_org_unit_type)

    def execute(
        self, dry_run: bool = False
    ) -> Iterator[tuple[OrgUnitNode, AnyMutation, UUID | Exception, Optional[bool]]]:
        """Call `TreeDiffExecutor.execute`, and call the SDLøn 'fix_departments' API
        for each 'add' and 'update' operation.
        """
        executor: TreeDiffExecutor = self.get_tree_diff_executor()
        org_unit_node: OrgUnitNode
        mutation: AnyMutation
        result: UUID | Exception
        fix_departments_result: bool | None
        for org_unit_node, mutation, result in executor.execute(dry_run):
            if not dry_run:
                fix_departments_result = self._call_apply_ny_logic(result)  # type: ignore
            else:
                fix_departments_result = True
            yield (
                org_unit_node,
                mutation,
                result,
                fix_departments_result,
            )

    def _call_apply_ny_logic(self, org_unit_uuid: OrgUnitUUID) -> bool:
        url: str = f"/trigger/apply-ny-logic/{org_unit_uuid}"
        response: Response = self.client.post(url)
        if response.status_code >= 400:
            # TODO: we need an RC alarm if this happens
            logger.error(
                "fix_departments returned an error: status_code=%d, response=%r",
                response.status_code,
                response.json(),
            )
        return response.status_code == 200

    @staticmethod
    def _get_effective_root_path(path_ou_uuids: list[OrgUnitUUID]):
        return "/".join([str(ou_uuid) for ou_uuid in path_ou_uuids])
