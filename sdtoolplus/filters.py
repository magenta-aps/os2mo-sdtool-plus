# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import re
from typing import Iterable

from sdtoolplus.mo_org_unit_importer import OrgUnitNode
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID


def filter_by_uuid(
    unit_uuid: OrgUnitUUID | None, org_units: Iterable[OrgUnitNode]
) -> list[OrgUnitNode]:
    if unit_uuid is None:
        return list(org_units)

    return [org_unit for org_unit in org_units if org_unit.uuid == unit_uuid]


def remove_by_name(
    regex_strings: list[str], org_units: Iterable[OrgUnitNode]
) -> list[OrgUnitNode]:
    """
    Filter org units by name. The units which does NOT match the regex
    are kept.
    Args:
        regex_strings: List of regex strings
        org_units: Iterator of org units to filter

    Returns:
        List of OrgUnitNodes which does not match the regex's
    """
    compiled_regexs = [re.compile(regex_string) for regex_string in regex_strings]

    return [
        org_unit_node
        for org_unit_node in org_units
        if not any(regex.match(org_unit_node.name) for regex in compiled_regexs)
    ]
