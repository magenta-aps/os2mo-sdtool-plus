# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from sdtoolplus.mo_org_unit_importer import OrgUnitNode


def build_email_body(units: list[OrgUnitNode]) -> str:
    body = (
        "SDTool+ har detekteret, at følgende enheder skal flyttes til 'Udgåede afdelinger',\n"
        "men enhederne har stadig et eller flere aktive eller fremtidigt aktive engagementer.\n"
        "Følgende enheder er derfor ikke blevet flyttet:\n\n"
    )

    for unit in units:
        body += f"{unit.name} ({str(unit.uuid)})\n"

    return body
