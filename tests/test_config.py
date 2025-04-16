# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import pytest

from sdtoolplus.config import SDToolPlusSettings


def test_unknown_unit_is_set_when_municipality_mode_is_false(
    sdtoolplus_settings: SDToolPlusSettings,
):
    # Arrange
    settings = sdtoolplus_settings.dict()
    settings_dict = settings.update({"municipality_mode": False})

    # Act + Assert
    with pytest.raises(ValueError) as error:
        SDToolPlusSettings.parse_obj(settings_dict)
        assert error == ValueError(
            "Unknown unit must be set when MUNICIPALITY_MODE is false"
        )
