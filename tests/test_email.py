# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID

from pydantic import EmailStr
from pydantic import SecretStr

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.email import build_email_body
from sdtoolplus.email import send_email_notification
from sdtoolplus.mo_org_unit_importer import OrgUnitNode


def test_build_email_body(random_org_unit_node: OrgUnitNode):
    # Act
    body = build_email_body(
        [random_org_unit_node, random_org_unit_node],
        {
            ("Department A", UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")),
            ("Department B", UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")),
        },
    )
    # Assert
    assert body == (
        "SDTool+ har detekteret, at følgende enheder skal flyttes til 'Udgåede afdelinger',\n"
        "men enhederne eller en af deres underenheder har stadig et eller flere aktive eller\n"
        "fremtidigt aktive engagementer. Følgende enheder er derfor ikke blevet flyttet:\n\n"
        "Department (10000000-0000-0000-0000-000000000000)\n"
        "Department (10000000-0000-0000-0000-000000000000)\n"
        "\n"
        "Der blev fundet engagementer i:\n"
        "Department A (aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa)\n"
        "Department B (bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb)\n"
        "\n"
        "Mvh. SDTool+ (denne email kan ikke besvares)\n"
    )


@patch("sdtoolplus.email.SMTP")
def test_email_to(
    mock_SMTP: MagicMock, sdtoolplus_settings: SDToolPlusSettings
) -> None:
    # Arrange
    sdtoolplus_settings.email_host = "smtp.example.org"
    sdtoolplus_settings.email_port = 2525
    sdtoolplus_settings.email_user = "Bruce"
    sdtoolplus_settings.email_password = SecretStr("secret")
    sdtoolplus_settings.email_from = EmailStr("email@from.dk")
    sdtoolplus_settings.email_to = [EmailStr("email@to1.dk"), EmailStr("email@to2.dk")]

    mock_smtp_client = MagicMock()
    mock_SMTP.return_value.__enter__.return_value = mock_smtp_client

    # Act
    send_email_notification(sdtoolplus_settings, "Email body")

    # Assert
    mock_SMTP.assert_called_once_with("smtp.example.org", 2525)

    mock_smtp_client.login.assert_called_once_with("Bruce", "secret")
    mock_smtp_client.sendmail.assert_called_once_with(
        "email@from.dk",
        ["email@to1.dk", "email@to2.dk"],
        'Content-Type: text/plain; charset="us-ascii"\n'
        "MIME-Version: 1.0\n"
        "Content-Transfer-Encoding: 7bit\n"
        "Subject: SDTool+ advarsel\n"
        "From: SDTool+ <email@from.dk>\n"
        "To: email@to1.dk, email@to2.dk\n\n"
        "Email body",
    )


@patch("sdtoolplus.email.SMTP")
def test_email_login_disabled(
    mock_SMTP: MagicMock, sdtoolplus_settings: SDToolPlusSettings
) -> None:
    # Arrange
    sdtoolplus_settings.email_use_login = False  # This is the important setting
    sdtoolplus_settings.email_host = "smtp.example.org"
    sdtoolplus_settings.email_from = EmailStr("email@from.dk")
    sdtoolplus_settings.email_to = [EmailStr("email@to1.dk"), EmailStr("email@to2.dk")]

    mock_smtp_client = MagicMock()
    mock_SMTP.return_value.__enter__.return_value = mock_smtp_client

    # Act
    send_email_notification(sdtoolplus_settings, "Email body")

    # Assert
    mock_smtp_client.login.assert_not_called()
