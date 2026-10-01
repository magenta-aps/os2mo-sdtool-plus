# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from more_itertools import last

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID


def get_sd_institution_unit_uuids(settings: SDToolPlusSettings) -> list[OrgUnitUUID]:
    assert settings.mo_subtree_paths_for_root is not None
    return [
        last(subtree_path)
        for subtree_path in settings.mo_subtree_paths_for_root.values()
    ]
