from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetParentRoots(BaseModel):
    org_units: "GetParentRootsOrgUnits"


class GetParentRootsOrgUnits(BaseModel):
    objects: List["GetParentRootsOrgUnitsObjects"]


class GetParentRootsOrgUnitsObjects(BaseModel):
    validities: List["GetParentRootsOrgUnitsObjectsValidities"]


class GetParentRootsOrgUnitsObjectsValidities(BaseModel):
    validity: "GetParentRootsOrgUnitsObjectsValiditiesValidity"
    root: Optional[List["GetParentRootsOrgUnitsObjectsValiditiesRoot"]]


class GetParentRootsOrgUnitsObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


class GetParentRootsOrgUnitsObjectsValiditiesRoot(BaseModel):
    name: str
    uuid: UUID
    user_key: str
    validity: "GetParentRootsOrgUnitsObjectsValiditiesRootValidity"


class GetParentRootsOrgUnitsObjectsValiditiesRootValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


GetParentRoots.update_forward_refs()
GetParentRootsOrgUnits.update_forward_refs()
GetParentRootsOrgUnitsObjects.update_forward_refs()
GetParentRootsOrgUnitsObjectsValidities.update_forward_refs()
GetParentRootsOrgUnitsObjectsValiditiesValidity.update_forward_refs()
GetParentRootsOrgUnitsObjectsValiditiesRoot.update_forward_refs()
GetParentRootsOrgUnitsObjectsValiditiesRootValidity.update_forward_refs()
