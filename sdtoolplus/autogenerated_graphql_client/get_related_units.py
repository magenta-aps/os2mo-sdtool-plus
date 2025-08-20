from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetRelatedUnits(BaseModel):
    related_units: "GetRelatedUnitsRelatedUnits"


class GetRelatedUnitsRelatedUnits(BaseModel):
    objects: List["GetRelatedUnitsRelatedUnitsObjects"]


class GetRelatedUnitsRelatedUnitsObjects(BaseModel):
    validities: List["GetRelatedUnitsRelatedUnitsObjectsValidities"]


class GetRelatedUnitsRelatedUnitsObjectsValidities(BaseModel):
    uuid: UUID
    validity: "GetRelatedUnitsRelatedUnitsObjectsValiditiesValidity"
    org_unit_uuids: List[UUID]


class GetRelatedUnitsRelatedUnitsObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


GetRelatedUnits.update_forward_refs()
GetRelatedUnitsRelatedUnits.update_forward_refs()
GetRelatedUnitsRelatedUnitsObjects.update_forward_refs()
GetRelatedUnitsRelatedUnitsObjectsValidities.update_forward_refs()
GetRelatedUnitsRelatedUnitsObjectsValiditiesValidity.update_forward_refs()
