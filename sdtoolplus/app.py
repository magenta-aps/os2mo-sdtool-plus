# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import sentry_sdk
import structlog
from anytree import RenderTree
from raclients.graph.client import PersistentGraphQLClient
from sdclient.client import SDClient

from .config import SDToolPlusSettings
from .diff_org_trees import OrgTreeDiff
from .mo_class import MOClass
from .mo_class import MOOrgUnitLevelMap
from .mo_class import MOOrgUnitTypeMap
from .mo_org_unit_importer import MOOrgTreeImport
from .sd.importer import get_sd_tree
from .sd.mock_tree import get_mock_sd_tree
from .tree_diff_executor import TreeDiffExecutor


logger = structlog.get_logger()


class App:
    def __init__(self, settings: SDToolPlusSettings):
        self.settings: SDToolPlusSettings = settings
        self.settings.start_logging_based_on_settings()

        if self.settings.sentry_dsn:
            sentry_sdk.init(dsn=self.settings.sentry_dsn)

        self.session = PersistentGraphQLClient(
            url=f"{self.settings.mora_base}/graphql/v7",
            client_id=self.settings.client_id,
            client_secret=self.settings.client_secret,  # type: ignore
            auth_realm=self.settings.auth_realm,
            auth_server=self.settings.auth_server,  # type: ignore
            sync=True,
            httpx_client_kwargs={"timeout": None},
            fetch_schema_from_transport=True,
        )

    def get_tree_diff_executor(self) -> TreeDiffExecutor:
        # Get relevant MO facet/class data
        mo_org_unit_type_map = MOOrgUnitTypeMap(self.session)
        mo_org_unit_type: MOClass = mo_org_unit_type_map[self.settings.org_unit_type]
        mo_org_unit_level_map = MOOrgUnitLevelMap(self.session)

        # Get actual MO tree
        mo_org_tree = MOOrgTreeImport(self.session)

        if (
            self.settings.sd_username
            and self.settings.sd_password
            and self.settings.sd_institution_identifier
        ):
            # Get actual SD tree
            logger.info(event="Fetching SD org tree ...")
            sd_client = SDClient(self.settings.sd_username, self.settings.sd_password)
            sd_org_tree = get_sd_tree(
                sd_client,
                self.settings.sd_institution_identifier,
                mo_org_unit_level_map,
            )
            print(RenderTree(sd_org_tree).by_attr("uuid"))
        else:
            # Mock SD tree (remove when appropriate)
            logger.info(event="Using mock SD org tree")
            sd_org_tree = get_mock_sd_tree(mo_org_tree)

        # Construct org tree diff
        tree_diff = OrgTreeDiff(
            mo_org_tree.as_single_tree(), sd_org_tree, mo_org_unit_type
        )

        # Construct tree diff executor
        return TreeDiffExecutor(self.session, tree_diff)
