from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetAssociationTimeline(BaseModel):
    associations: "GetAssociationTimelineAssociations"


class GetAssociationTimelineAssociations(BaseModel):
    objects: List["GetAssociationTimelineAssociationsObjects"]


class GetAssociationTimelineAssociationsObjects(BaseModel):
    uuid: UUID
    validities: List["GetAssociationTimelineAssociationsObjectsValidities"]


class GetAssociationTimelineAssociationsObjectsValidities(BaseModel):
    user_key: str
    employee_uuid: Optional[UUID]
    org_unit_uuid: UUID
    validity: "GetAssociationTimelineAssociationsObjectsValiditiesValidity"


class GetAssociationTimelineAssociationsObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


GetAssociationTimeline.update_forward_refs()
GetAssociationTimelineAssociations.update_forward_refs()
GetAssociationTimelineAssociationsObjects.update_forward_refs()
GetAssociationTimelineAssociationsObjectsValidities.update_forward_refs()
GetAssociationTimelineAssociationsObjectsValiditiesValidity.update_forward_refs()
