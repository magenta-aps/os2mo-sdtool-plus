from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetOrgUnit(BaseModel):
    org_units: "GetOrgUnitOrgUnits"


class GetOrgUnitOrgUnits(BaseModel):
    objects: List["GetOrgUnitOrgUnitsObjects"]


class GetOrgUnitOrgUnitsObjects(BaseModel):
    uuid: UUID
    validities: List["GetOrgUnitOrgUnitsObjectsValidities"]


class GetOrgUnitOrgUnitsObjectsValidities(BaseModel):
    name: str
    user_key: str
    children: List["GetOrgUnitOrgUnitsObjectsValiditiesChildren"]
    validity: "GetOrgUnitOrgUnitsObjectsValiditiesValidity"


class GetOrgUnitOrgUnitsObjectsValiditiesChildren(BaseModel):
    uuid: UUID


class GetOrgUnitOrgUnitsObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


GetOrgUnit.update_forward_refs()
GetOrgUnitOrgUnits.update_forward_refs()
GetOrgUnitOrgUnitsObjects.update_forward_refs()
GetOrgUnitOrgUnitsObjectsValidities.update_forward_refs()
GetOrgUnitOrgUnitsObjectsValiditiesChildren.update_forward_refs()
GetOrgUnitOrgUnitsObjectsValiditiesValidity.update_forward_refs()
