# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from sdtoolplus.email import build_email_body
from sdtoolplus.mo_org_unit_importer import OrgUnitNode


def test_build_email_body(random_org_unit_node: OrgUnitNode):
    # Act
    body = build_email_body([random_org_unit_node, random_org_unit_node])
    print(body)
    # Assert
    assert body == (
        "SDTool+ har detekteret, at følgende enheder skal flyttes til 'Udgåede afdelinger',\n"
        "men enhederne har stadig et eller flere aktive eller fremtidigt aktive engagementer.\n"
        "Følgende enheder er derfor ikke blevet flyttet:\n\n"
        "Department (10000000-0000-0000-0000-000000000000)\n"
        "Department (10000000-0000-0000-0000-000000000000)\n"
    )
