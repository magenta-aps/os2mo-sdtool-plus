# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from datetime import timezone

import pytest

from sdtoolplus.config import TIMEZONE
from sdtoolplus.config import SDToolPlusSettings


def test_unknown_unit_is_set_when_municipality_mode_is_false(
    sdtoolplus_settings: SDToolPlusSettings,
):
    # Arrange
    settings = sdtoolplus_settings.dict()
    settings.update({"municipality_mode": False})

    # Act + Assert
    with pytest.raises(ValueError) as error:
        SDToolPlusSettings.parse_obj(settings)
        assert error == ValueError(
            "Unknown unit must be set when MUNICIPALITY_MODE is false"
        )


def test_min_mo_datetime_validator(sdtoolplus_settings: SDToolPlusSettings):
    # Arrange
    settings = sdtoolplus_settings.dict()
    settings.update(
        {"min_mo_datetime": datetime(1970, 1, 1, 11, 0, 0, tzinfo=timezone.utc)}
    )

    # Act
    validated_settings = SDToolPlusSettings.parse_obj(settings)

    # Assert
    assert validated_settings.min_mo_datetime == datetime(
        1970, 1, 1, 12, 0, 0, tzinfo=TIMEZONE
    )
