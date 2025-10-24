# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from uuid import uuid4

import pytest

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.sync.common import prefix_eng_user_key
from sdtoolplus.sync.common import split_engagement_user_key


@pytest.mark.parametrize(
    "user_key,prefix_eng_user_key,expected_inst_id,expected_emp_id",
    [
        ("12345", False, "sd_institution_identifier", "12345"),
        ("II-12345", True, "II", "12345"),
    ],
)
def test_split_engagement_user_key(
    user_key: str,
    prefix_eng_user_key: bool,
    expected_inst_id: str,
    expected_emp_id: str,
    sdtoolplus_settings: SDToolPlusSettings,
) -> None:
    # Arrange
    settings = sdtoolplus_settings.dict()
    settings.update(
        {
            "prefix_engagement_user_keys": prefix_eng_user_key,
            "unknown_unit": uuid4(),
            "apply_ny_logic": False,
            "mo_subtree_paths_for_root": {},
        }
    )

    # Act
    inst_id, emp_id = split_engagement_user_key(
        SDToolPlusSettings.parse_obj(settings), user_key
    )

    # Assert
    assert inst_id == expected_inst_id
    assert emp_id == expected_emp_id


@pytest.mark.parametrize(
    "emp_id,prefix_engagement_user_key,expected_user_key",
    [
        ("12345", False, "12345"),
        ("12345", True, "II-12345"),
    ],
)
def test_prefix_eng_user_key(
    emp_id: str,
    prefix_engagement_user_key: bool,
    expected_user_key: str,
    sdtoolplus_settings: SDToolPlusSettings,
) -> None:
    # Arrange
    settings = sdtoolplus_settings.dict()
    settings.update(
        {
            "prefix_engagement_user_keys": prefix_engagement_user_key,
            "unknown_unit": uuid4(),
            "apply_ny_logic": False,
            "mo_subtree_paths_for_root": {},
        }
    )

    # Act
    actual_user_key = prefix_eng_user_key(
        settings=SDToolPlusSettings.parse_obj(settings), user_key=emp_id, inst_id="II"
    )

    # Assert
    assert actual_user_key == expected_user_key
