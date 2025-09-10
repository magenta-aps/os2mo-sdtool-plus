from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetManagerTimeline(BaseModel):
    managers: "GetManagerTimelineManagers"


class GetManagerTimelineManagers(BaseModel):
    objects: List["GetManagerTimelineManagersObjects"]


class GetManagerTimelineManagersObjects(BaseModel):
    validities: List["GetManagerTimelineManagersObjectsValidities"]


class GetManagerTimelineManagersObjectsValidities(BaseModel):
    org_unit_uuid: UUID
    validity: "GetManagerTimelineManagersObjectsValiditiesValidity"


class GetManagerTimelineManagersObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


GetManagerTimeline.update_forward_refs()
GetManagerTimelineManagers.update_forward_refs()
GetManagerTimelineManagersObjects.update_forward_refs()
GetManagerTimelineManagersObjectsValidities.update_forward_refs()
GetManagerTimelineManagersObjectsValiditiesValidity.update_forward_refs()
