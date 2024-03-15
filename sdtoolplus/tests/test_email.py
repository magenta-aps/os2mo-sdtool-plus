# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from uuid import UUID

from sdtoolplus.email import build_email_body
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
    )
