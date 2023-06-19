# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import uuid
from copy import deepcopy

import pytest

from ..diff_org_trees import AddOperation
from ..diff_org_trees import OrgTreeDiff
from ..diff_org_trees import UpdateOperation
from ..mo_org_unit_importer import OrgUnit
from ..mo_org_unit_importer import OrgUUID


class TestOrgTreeDiff:
    org_uuid: OrgUUID = uuid.uuid4()

    mo_root = OrgUnit(
        uuid=org_uuid,
        parent_uuid=None,
        name="Root",
    )

    sd_root = OrgUnit(
        uuid=org_uuid,
        parent_uuid=None,
        name="Root",
    )

    def test_only_identical_roots(self):
        instance = OrgTreeDiff(self.mo_root, self.sd_root)
        assert list(instance.get_operations()) == []

    @pytest.mark.xfail
    def test_root_name_change(self):
        sd_root = deepcopy(self.sd_root)
        sd_root.name = "Root 2"
        instance = OrgTreeDiff(self.mo_root, sd_root)
        operations = list(instance.get_operations())
        assert len(operations) == 1
        assert isinstance(operations[0], UpdateOperation)
        assert operations[0].attr == "name"
        assert operations[0].value == "Root 2"

    def test_addition_in_sd(self):
        sd_root = deepcopy(self.sd_root)
        sd_root.children = [
            OrgUnit(
                uuid=uuid.uuid4(),
                parent_uuid=self.sd_root.uuid,
                name="Child",
            )
        ]
        instance = OrgTreeDiff(self.mo_root, sd_root)
        operations = list(instance.get_operations())
        assert len(operations) == 1
        assert isinstance(operations[0], AddOperation)
