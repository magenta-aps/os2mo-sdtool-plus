from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetAssociations(BaseModel):
    associations: "GetAssociationsAssociations"


class GetAssociationsAssociations(BaseModel):
    objects: List["GetAssociationsAssociationsObjects"]


class GetAssociationsAssociationsObjects(BaseModel):
    uuid: UUID
    validities: List["GetAssociationsAssociationsObjectsValidities"]


class GetAssociationsAssociationsObjectsValidities(BaseModel):
    user_key: str
    employee_uuid: Optional[UUID]
    org_unit_uuid: UUID
    validity: "GetAssociationsAssociationsObjectsValiditiesValidity"


class GetAssociationsAssociationsObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


GetAssociations.update_forward_refs()
GetAssociationsAssociations.update_forward_refs()
GetAssociationsAssociationsObjects.update_forward_refs()
GetAssociationsAssociationsObjectsValidities.update_forward_refs()
GetAssociationsAssociationsObjectsValiditiesValidity.update_forward_refs()
