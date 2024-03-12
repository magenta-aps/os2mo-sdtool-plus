# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from email.mime.text import MIMEText
from smtplib import SMTP
from smtplib import SMTP_SSL
from smtplib import SMTPException
from ssl import PROTOCOL_TLSv1_2
from ssl import SSLContext

import structlog

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.mo_org_unit_importer import OrgUnitNode

logger = structlog.get_logger()


def build_email_body(units: list[OrgUnitNode]) -> str:
    body = (
        "SDTool+ har detekteret, at følgende enheder skal flyttes til 'Udgåede afdelinger',\n"
        "men enhederne har stadig et eller flere aktive eller fremtidigt aktive engagementer.\n"
        "Følgende enheder er derfor ikke blevet flyttet:\n\n"
    )

    for unit in units:
        logger.debug("Add org unit to email body", name=unit.name, uuid=str(unit.uuid))
        body += f"{unit.name} ({str(unit.uuid)})\n"

    return body


def send_email_notification(settings: SDToolPlusSettings, body: str):
    assert settings.email_from is not None

    recipients = ",".join(settings.email_to)
    logger.info("Sending email notification", recipients=recipients)

    msg = MIMEText(body)
    msg["Subject"] = "SDTool+ advarsel"
    msg["From"] = settings.email_from
    msg["To"] = recipients

    context = SSLContext(PROTOCOL_TLSv1_2)

    try:
        with SMTP(settings.email_host, settings.email_port) as smtp_client:
            smtp_client.starttls(context=context)
            smtp_client.login(
                settings.email_user, settings.email_password.get_secret_value()
            )
            smtp_client.sendmail(settings.email_from, recipients, msg.as_string())
    except SMTPException as error:
        logger.error("Could not send email!", error=str(error))
