# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from email.mime.text import MIMEText
from operator import itemgetter
from smtplib import SMTP
from smtplib import SMTPException
from ssl import PROTOCOL_TLSv1_2
from ssl import SSLContext

import structlog

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.mo_org_unit_importer import OrgUnitNode
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID

logger = structlog.stdlib.get_logger()


def build_email_body(
    subtrees_with_engs: list[OrgUnitNode],
    units_with_engs: set[tuple[str, OrgUnitUUID]],
) -> str:
    body = (
        "SDTool+ har detekteret, at følgende enheder skal flyttes til 'Udgåede afdelinger',\n"
        "men enhederne eller en af deres underenheder har stadig et eller flere aktive eller\n"
        "fremtidigt aktive engagementer. Følgende enheder er derfor ikke blevet flyttet:\n\n"
    )

    for unit in subtrees_with_engs:
        logger.debug("Add org unit to email body", name=unit.name, uuid=str(unit.uuid))
        body += f"{unit.name} ({str(unit.uuid)})\n"

    units = list(units_with_engs)
    # Sort by the name of the unit
    units.sort(key=itemgetter(0))

    if units:
        body += "\nDer blev fundet engagementer i:\n"
        for unit_name, unit_uuid in units:
            body += f"{unit_name} ({str(unit_uuid)})\n"

    body += "\nMvh. SDTool+ (denne email kan ikke besvares)\n"

    return body


def send_email_notification(settings: SDToolPlusSettings, body: str):
    assert settings.email_from is not None

    recipients = ", ".join(settings.email_to)
    logger.info("Sending email notification", recipients=recipients)

    msg = MIMEText(body)
    msg["Subject"] = "SDTool+ advarsel"
    msg["From"] = f"SDTool+ <{settings.email_from}>"
    msg["To"] = recipients

    context = SSLContext(PROTOCOL_TLSv1_2)

    try:
        with SMTP(settings.email_host, settings.email_port) as smtp_client:
            smtp_client.starttls(context=context)
            if settings.email_use_login:
                smtp_client.login(
                    settings.email_user, settings.email_password.get_secret_value()
                )
            smtp_client.sendmail(
                settings.email_from, settings.email_to, msg.as_string()
            )
    except SMTPException as error:
        logger.error("Could not send email!", error=str(error))
