from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetOrgUnitParents(BaseModel):
    org_units: "GetOrgUnitParentsOrgUnits"


class GetOrgUnitParentsOrgUnits(BaseModel):
    objects: List["GetOrgUnitParentsOrgUnitsObjects"]


class GetOrgUnitParentsOrgUnitsObjects(BaseModel):
    validities: List["GetOrgUnitParentsOrgUnitsObjectsValidities"]


class GetOrgUnitParentsOrgUnitsObjectsValidities(BaseModel):
    uuid: UUID
    parent_response: Optional[
        "GetOrgUnitParentsOrgUnitsObjectsValiditiesParentResponse"
    ]
    validity: "GetOrgUnitParentsOrgUnitsObjectsValiditiesValidity"


class GetOrgUnitParentsOrgUnitsObjectsValiditiesParentResponse(BaseModel):
    uuid: UUID


class GetOrgUnitParentsOrgUnitsObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


GetOrgUnitParents.update_forward_refs()
GetOrgUnitParentsOrgUnits.update_forward_refs()
GetOrgUnitParentsOrgUnitsObjects.update_forward_refs()
GetOrgUnitParentsOrgUnitsObjectsValidities.update_forward_refs()
GetOrgUnitParentsOrgUnitsObjectsValiditiesParentResponse.update_forward_refs()
GetOrgUnitParentsOrgUnitsObjectsValiditiesValidity.update_forward_refs()
