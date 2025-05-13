from typing import List
from uuid import UUID

from .base_model import BaseModel


class GetParentRoots(BaseModel):
    org_units: "GetParentRootsOrgUnits"


class GetParentRootsOrgUnits(BaseModel):
    objects: List["GetParentRootsOrgUnitsObjects"]


class GetParentRootsOrgUnitsObjects(BaseModel):
    uuid: UUID


GetParentRoots.update_forward_refs()
GetParentRootsOrgUnits.update_forward_refs()
GetParentRootsOrgUnitsObjects.update_forward_refs()
