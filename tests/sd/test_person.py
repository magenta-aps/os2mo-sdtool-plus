# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import pytest
from sdclient.responses import ContactInformation

from sdtoolplus.sd.person import _get_phone_numbers


@pytest.mark.parametrize(
    "telephone_number_identifier, expected",
    [
        ([], (None, None)),
        (["12345678"], ("12345678", None)),
        (["12345678", "23456789"], ("12345678", "23456789")),
        (["12345678", "00000000"], ("12345678", None)),
        (["00000000", "23456789"], (None, "23456789")),
    ],
)
def test__get_phone_numbers(
    telephone_number_identifier: list[str],
    expected: tuple[str | None, str | None],
) -> None:
    # Arrange
    contact_info = ContactInformation(
        TelephoneNumberIdentifier=telephone_number_identifier,
    )

    # Act
    phone_numbers = _get_phone_numbers(contact_info)

    # Assert
    assert phone_numbers == expected
