# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from uuid import uuid4

from sdtoolplus.filters import remove_by_name
from sdtoolplus.mo_org_unit_importer import OrgUnitNode


def test_remove_by_name(expected_units_to_add):
    # Arrange
    regexs = ["^.*5$", "^.*6$"]  # Filter out units where the name ends in "5" or "6"

    # Act
    kept_units = remove_by_name(regexs, expected_units_to_add)

    # Assert
    assert expected_units_to_add[:2] == kept_units


def test_remove_by_name_special_characters(sd_expected_validity):
    # Arrange
    regexs = ["^%.*$"]
    org_unit_nodes = [
        OrgUnitNode(
            uuid=uuid4(),
            parent_uuid=uuid4(),
            user_key="dep3",
            name="% Department 3",
            org_unit_level_uuid=uuid4(),
            validity=sd_expected_validity,
        )
    ]

    # Act
    kept_units = remove_by_name(regexs, org_unit_nodes)

    # Assert
    assert kept_units == []


def test_remove_by_name_keep_all(expected_units_to_add):
    # Act
    kept_units = remove_by_name([], expected_units_to_add)

    # Assert
    assert expected_units_to_add == kept_units
