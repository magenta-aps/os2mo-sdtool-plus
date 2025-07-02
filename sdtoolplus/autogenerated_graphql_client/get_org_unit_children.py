from typing import List
from uuid import UUID

from .base_model import BaseModel


class GetOrgUnitChildren(BaseModel):
    org_units: "GetOrgUnitChildrenOrgUnits"


class GetOrgUnitChildrenOrgUnits(BaseModel):
    objects: List["GetOrgUnitChildrenOrgUnitsObjects"]


class GetOrgUnitChildrenOrgUnitsObjects(BaseModel):
    uuid: UUID


GetOrgUnitChildren.update_forward_refs()
GetOrgUnitChildrenOrgUnits.update_forward_refs()
GetOrgUnitChildrenOrgUnitsObjects.update_forward_refs()
