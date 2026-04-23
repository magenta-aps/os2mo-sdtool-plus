# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.models import Person
from sdtoolplus.sync.person import _sync_addresses


@pytest.mark.parametrize(
    "environment_variable, class_user_key",
    [
        ("disable_person_phone_number_sync", "person_telefon"),
        ("disable_person_phone_number_sync", "person_telefon_anden"),
        ("disable_person_postal_address_sync", "AdresseSDEmployee"),
        ("disable_person_email_address_sync", "person_email"),
        ("disable_person_email_address_sync", "person_email_anden"),
    ],
)
@patch("sdtoolplus.sync.person._sync_address")
@patch("sdtoolplus.sync.person.get_class")
async def test_person_address_sync_flags(
    mock_get_class: AsyncMock,
    mock__sync_address: AsyncMock,
    sdtoolplus_settings: SDToolPlusSettings,
    environment_variable: str,
    class_user_key: str,
) -> None:
    # Arrange
    mock_gql_client = AsyncMock(spec=GraphQLClient)

    settings = sdtoolplus_settings.dict()
    settings.update({environment_variable: True})

    sd_person = Person(
        cpr="2711401111",
        given_name="Bruce",
        surname="Lee",
    )

    # Act
    await _sync_addresses(
        gql_client=mock_gql_client,
        settings=SDToolPlusSettings.parse_obj(settings),
        person_uuid=uuid4(),
        sd_person=sd_person,
    )

    # Assert
    class_user_keys_fetched = [
        call_args.kwargs["class_user_key"]
        for call_args in mock_get_class.call_args_list
    ]
    assert class_user_key not in class_user_keys_fetched


@patch("sdtoolplus.sync.person._sync_address")
@patch("sdtoolplus.sync.person._sync_engagement_phone_numbers")
@patch("sdtoolplus.sync.person.get_class")
async def test_engagement_address_sync_flags(
    mock_get_class: AsyncMock,
    mock__sync_engagement_phone_numbers: AsyncMock,
    mock__sync_address: AsyncMock,
    sdtoolplus_settings: SDToolPlusSettings,
) -> None:
    # Arrange
    mock_gql_client = AsyncMock(spec=GraphQLClient)

    settings = sdtoolplus_settings.dict()
    settings.update({"disable_engagement_phone_number_sync": True})

    sd_person = Person(
        cpr="2711401111",
        given_name="Bruce",
        surname="Lee",
    )

    # Act
    await _sync_addresses(
        gql_client=mock_gql_client,
        settings=SDToolPlusSettings.parse_obj(settings),
        person_uuid=uuid4(),
        sd_person=sd_person,
    )

    # Assert
    mock__sync_engagement_phone_numbers.assert_not_awaited()
