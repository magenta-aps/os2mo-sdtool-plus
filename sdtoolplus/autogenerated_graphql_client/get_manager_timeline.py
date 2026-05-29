from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetManagerTimeline(BaseModel):
    managers: "GetManagerTimelineManagers"


class GetManagerTimelineManagers(BaseModel):
    objects: List["GetManagerTimelineManagersObjects"]


class GetManagerTimelineManagersObjects(BaseModel):
    uuid: UUID
    validities: List["GetManagerTimelineManagersObjectsValidities"]


class GetManagerTimelineManagersObjectsValidities(BaseModel):
    user_key: str
    validity: "GetManagerTimelineManagersObjectsValiditiesValidity"
    engagement_response: Optional[
        "GetManagerTimelineManagersObjectsValiditiesEngagementResponse"
    ]
    org_unit_uuid: UUID
    employee_uuid: Optional[UUID]
    manager_type_uuid: Optional[UUID]
    manager_level_uuid: Optional[UUID]
    responsibility_uuids: Optional[List[UUID]]


class GetManagerTimelineManagersObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


class GetManagerTimelineManagersObjectsValiditiesEngagementResponse(BaseModel):
    uuid: UUID


GetManagerTimeline.update_forward_refs()
GetManagerTimelineManagers.update_forward_refs()
GetManagerTimelineManagersObjects.update_forward_refs()
GetManagerTimelineManagersObjectsValidities.update_forward_refs()
GetManagerTimelineManagersObjectsValiditiesValidity.update_forward_refs()
GetManagerTimelineManagersObjectsValiditiesEngagementResponse.update_forward_refs()
