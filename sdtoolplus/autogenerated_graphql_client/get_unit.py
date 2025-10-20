from typing import List
from uuid import UUID

from .base_model import BaseModel


class GetUnit(BaseModel):
    org_units: "GetUnitOrgUnits"


class GetUnitOrgUnits(BaseModel):
    objects: List["GetUnitOrgUnitsObjects"]


class GetUnitOrgUnitsObjects(BaseModel):
    uuid: UUID


GetUnit.update_forward_refs()
GetUnitOrgUnits.update_forward_refs()
GetUnitOrgUnitsObjects.update_forward_refs()
