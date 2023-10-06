# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from uuid import uuid4

from ramodels.mo import Validity

from ..mo_org_unit_importer import MOOrgTreeImport
from ..mo_org_unit_importer import OrgUnitNode
from ..mo_org_unit_importer import OrgUnitUUID


def get_mock_sd_tree(mo_org_tree: MOOrgTreeImport) -> OrgUnitNode:
    mock_sd_validity: Validity = Validity(
        from_date=datetime.fromisoformat("1960-01-01T00:00:00+01:00"),
        to_date=None,
    )
    mock_sd_root: OrgUnitNode = OrgUnitNode(
        uuid=mo_org_tree.get_org_uuid(),
        parent_uuid=None,
        name="<root>",
        validity=mock_sd_validity,
    )
    mock_sd_updated_child: OrgUnitNode = OrgUnitNode(
        uuid=OrgUnitUUID("f06ee470-9f17-566f-acbe-e938112d46d9"),
        parent_uuid=mo_org_tree.get_org_uuid(),
        name="Kolding Kommune II",
        org_unit_level_uuid=uuid4(),
        validity=mock_sd_validity,
    )
    mock_sd_new_child: OrgUnitNode = OrgUnitNode(
        uuid=uuid4(),
        parent_uuid=mo_org_tree.get_org_uuid(),
        name="Something new",
        org_unit_level_uuid=uuid4(),
        validity=mock_sd_validity,
    )
    mock_sd_root.children = [mock_sd_updated_child, mock_sd_new_child]
    return mock_sd_root
