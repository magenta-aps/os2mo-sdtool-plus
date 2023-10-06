# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
"""
To run:

    $ cd os2mo-sdtool-plus
    $ poetry shell
    $ export MORA_BASE=http://localhost:5000
    $ export AUTH_SERVER=...
    $ export CLIENT_SECRET=...
    $ python -m sdtoolplus

"""
import logging
from uuid import uuid4

import click
from anytree import RenderTree
from raclients.graph.client import GraphQLClient
from sdclient.client import SDClient

from .config import SDToolPlusSettings
from .diff_org_trees import OrgTreeDiff
from .mo_class import MOClass
from .mo_class import MOOrgUnitLevelMap
from .mo_class import MOOrgUnitTypeMap
from .mo_org_unit_importer import MOOrgTreeImport
from .mo_org_unit_importer import OrgUnitNode
from .mo_org_unit_importer import OrgUnitUUID
from .sd.importer import get_sd_tree
from .tree_diff_executor import TreeDiffExecutor


logger = logging.getLogger(__name__)


def _get_mock_sd_org_tree(mo_org_tree: MOOrgTreeImport) -> OrgUnitNode:
    mock_sd_root: OrgUnitNode = OrgUnitNode(
        uuid=mo_org_tree.get_org_uuid(),
        parent_uuid=None,
        name="<root>",
    )
    mock_sd_updated_child: OrgUnitNode = OrgUnitNode(
        uuid=OrgUnitUUID("f06ee470-9f17-566f-acbe-e938112d46d9"),
        parent_uuid=mo_org_tree.get_org_uuid(),
        name="Kolding Kommune II",
        org_unit_level_uuid=uuid4(),
    )
    mock_sd_new_child: OrgUnitNode = OrgUnitNode(
        uuid=uuid4(),
        parent_uuid=mo_org_tree.get_org_uuid(),
        name="Something new",
        org_unit_level_uuid=uuid4(),
    )
    mock_sd_root.children = [mock_sd_updated_child, mock_sd_new_child]
    return mock_sd_root


@click.command()
def main() -> None:
    settings = SDToolPlusSettings()
    settings.start_logging_based_on_settings()

    session = GraphQLClient(
        url=f"{settings.mora_base}/graphql/v7",
        client_id=settings.client_id,
        client_secret=settings.client_secret,  # type: ignore
        auth_realm=settings.auth_realm,
        auth_server=settings.auth_server,  # type: ignore
        sync=True,
        httpx_client_kwargs={"timeout": None},
        fetch_schema_from_transport=True,
    )

    mo_org_unit_type_map = MOOrgUnitTypeMap(session)
    mo_org_unit_type: MOClass = mo_org_unit_type_map[settings.org_unit_type]
    mo_org_unit_level_map = MOOrgUnitLevelMap(session)

    # Get actual MO tree
    mo_org_tree = MOOrgTreeImport(session)

    if (
        settings.sd_username
        and settings.sd_password
        and settings.sd_institution_identifier
    ):
        # Get actual SD tree
        logger.info("Fetching SD org tree ...")
        sd_client = SDClient(settings.sd_username, settings.sd_password)
        sd_org_tree = get_sd_tree(
            sd_client, settings.sd_institution_identifier, mo_org_unit_level_map
        )
        print(RenderTree(sd_org_tree).by_attr("uuid"))
    else:
        logger.info("Using mock SD org tree")
        # Mock SD tree (remove when appropriate)
        sd_org_tree = _get_mock_sd_org_tree(mo_org_tree)

    # Construct org tree diff
    tree_diff = OrgTreeDiff(mo_org_tree.as_single_tree(), sd_org_tree, mo_org_unit_type)

    # Execute org tree diff against current MO state
    executor = TreeDiffExecutor(session, tree_diff)
    for operation, mutation, result in executor.execute():
        print(operation, result)


if __name__ == "__main__":
    main()
