from typing import List
from uuid import UUID

from .base_model import BaseModel


class GetUnknownUnit(BaseModel):
    org_units: "GetUnknownUnitOrgUnits"


class GetUnknownUnitOrgUnits(BaseModel):
    objects: List["GetUnknownUnitOrgUnitsObjects"]


class GetUnknownUnitOrgUnitsObjects(BaseModel):
    uuid: UUID


GetUnknownUnit.update_forward_refs()
GetUnknownUnitOrgUnits.update_forward_refs()
GetUnknownUnitOrgUnitsObjects.update_forward_refs()
