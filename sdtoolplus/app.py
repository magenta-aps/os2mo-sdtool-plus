# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from typing import Iterator
from uuid import UUID

import httpx
import sentry_sdk
import structlog
from httpx import Response
from httpx import Timeout
from sdclient.client import SDClient

from .config import SDToolPlusSettings
from .diff_org_trees import in_obsolete_units_subtree
from .diff_org_trees import OrgTreeDiff
from .email import build_email_body
from .email import send_email_notification
from .graphql import get_graphql_client
from .log import setup_logging
from .mo_class import MOClass
from .mo_class import MOOrgUnitLevelMap
from .mo_class import MOOrgUnitTypeMap
from .mo_org_unit_importer import MOOrgTreeImport
from .mo_org_unit_importer import OrgUnitNode
from .mo_org_unit_importer import OrgUnitUUID
from .sd.importer import get_sd_tree
from .tree_diff_executor import AnyMutation
from .tree_diff_executor import TreeDiffExecutor
from .tree_diff_executor import UpdateOrgUnitMutation


logger = structlog.get_logger()


class App:
    def __init__(self, settings: SDToolPlusSettings):
        self.settings: SDToolPlusSettings = settings

        setup_logging(self.settings.log_level)

        if self.settings.sentry_dsn:
            sentry_sdk.init(dsn=self.settings.sentry_dsn)

        self.session = get_graphql_client(settings)

        self.mo_org_tree_import = MOOrgTreeImport(self.session)

        self.client = httpx.Client(
            base_url=str(self.settings.sd_lon_base_url),
            timeout=Timeout(timeout=self.settings.httpx_timeout_ny_logic),
        )
        logger.debug("Configured HTTPX client", base_url=self.client.base_url)

    def get_sd_tree(self, mo_org_unit_level_map: MOOrgUnitLevelMap) -> OrgUnitNode:
        sd_client = SDClient(
            self.settings.sd_username,
            self.settings.sd_password.get_secret_value(),
        )

        sd_root_uuid = (
            self.mo_org_tree_import.get_org_uuid()
            if self.settings.use_mo_root_uuid_as_sd_root_uuid
            else None
        )

        return get_sd_tree(
            sd_client,
            self.settings.sd_institution_identifier,
            mo_org_unit_level_map,
            sd_root_uuid,
            self.settings.build_extra_tree,
        )

    def get_mo_tree(self) -> OrgUnitNode:
        mo_subtree_path_for_root = App._get_effective_root_path(
            self.settings.mo_subtree_path_for_root
        )
        return self.mo_org_tree_import.as_single_tree(mo_subtree_path_for_root)

    def get_tree_diff_executor(self) -> TreeDiffExecutor:
        logger.debug("Getting TreeDiffExecutor")

        # Get relevant MO facet/class data
        mo_org_unit_type_map = MOOrgUnitTypeMap(self.session)
        mo_org_unit_type: MOClass = mo_org_unit_type_map[self.settings.org_unit_type]

        mo_org_unit_level_map = MOOrgUnitLevelMap(self.session)

        # Get the SD tree
        logger.info(event="Fetching SD org tree ...")
        sd_org_tree = self.get_sd_tree(mo_org_unit_level_map)
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
        self.tree_diff = OrgTreeDiff(
            mo_org_tree_as_single,
            sd_org_tree,
            mo_org_unit_level_map,
            self.settings,
        )

        # Construct tree diff executor
        return TreeDiffExecutor(
            self.session,
            self.settings,
            self.tree_diff,
            mo_org_unit_type,
            self.settings.regex_unit_names_to_remove,
        )

    def execute(
        self, org_unit: UUID | None = None, dry_run: bool = False
    ) -> Iterator[tuple[OrgUnitNode, AnyMutation, UUID]]:
        """Call `TreeDiffExecutor.execute`, and call the SDLøn 'fix_departments' API
        for each 'add' and 'update' operation.

        Args:
            org_unit: Unit to be processed (if not None) by TreeDiffExecutor
            dry_run: whether to perform a dry run or not

        Returns:
            Iterator which iterates over the processed units
        """
        executor: TreeDiffExecutor = self.get_tree_diff_executor()
        org_unit_node: OrgUnitNode
        mutation: AnyMutation
        result: UUID
        for org_unit_node, mutation, result in executor.execute(
            org_unit=org_unit, dry_run=dry_run
        ):
            logger.info("Successfully executed mutation", org_unit=str(org_unit))
            if self._should_apply_ny_logic(mutation, org_unit_node, dry_run):
                self._call_apply_ny_logic(result)  # type: ignore
            yield (
                org_unit_node,
                mutation,
                result,
            )

    def send_email_notification(self):
        subtrees_with_engs = self.tree_diff.get_subtrees_with_engs()
        units_with_engs = self.tree_diff.get_units_with_engagements()

        if subtrees_with_engs:
            email_body = build_email_body(subtrees_with_engs, units_with_engs)
            send_email_notification(self.settings, email_body)

    def _should_apply_ny_logic(
        self, mutation: AnyMutation, org_unit_node: OrgUnitNode, dry_run: bool
    ) -> bool:
        if (
            dry_run
            or not isinstance(mutation, UpdateOrgUnitMutation)
            or in_obsolete_units_subtree(
                org_unit_node, self.settings.obsolete_unit_roots
            )
        ):
            return False
        return True

    def _call_apply_ny_logic(self, org_unit_uuid: OrgUnitUUID) -> None:
        logger.info("Apply NY logic", org_unit_uuid=org_unit_uuid)

        url: str = f"/trigger/apply-ny-logic/{org_unit_uuid}"
        response: Response = self.client.post(url)

        # NOTE: if _call_apply_ny_logic fails, you will have to make the
        # failing POST request again manually to make sure the NY logic
        # has been applied properly for the given org unit
        response.raise_for_status()
        logger.info("NY logic applied successfully")

    @staticmethod
    def _get_effective_root_path(path_ou_uuids: list[OrgUnitUUID]):
        return "/".join([str(ou_uuid) for ou_uuid in path_ou_uuids])
