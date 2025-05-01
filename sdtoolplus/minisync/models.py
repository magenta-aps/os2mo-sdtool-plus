# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date

from pydantic import BaseModel
from pydantic import Extra

from sdtoolplus.mo_org_unit_importer import OrgUnitUUID


class EngagementSyncPayload(BaseModel, frozen=True, extra=Extra.forbid):
    institution_identifier: str
    cpr: str
    employment_identifier: str


class EngagementMovePayload(EngagementSyncPayload):
    org_unit_uuid: OrgUnitUUID
    start: date
    end: date
