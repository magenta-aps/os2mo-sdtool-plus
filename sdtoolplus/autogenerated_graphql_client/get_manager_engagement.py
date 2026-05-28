from typing import List
from typing import Optional
from uuid import UUID

from .base_model import BaseModel


class GetManagerEngagement(BaseModel):
    managers: "GetManagerEngagementManagers"


class GetManagerEngagementManagers(BaseModel):
    objects: List["GetManagerEngagementManagersObjects"]


class GetManagerEngagementManagersObjects(BaseModel):
    validities: List["GetManagerEngagementManagersObjectsValidities"]


class GetManagerEngagementManagersObjectsValidities(BaseModel):
    engagement_response: Optional[
        "GetManagerEngagementManagersObjectsValiditiesEngagementResponse"
    ]


class GetManagerEngagementManagersObjectsValiditiesEngagementResponse(BaseModel):
    uuid: UUID


GetManagerEngagement.update_forward_refs()
GetManagerEngagementManagers.update_forward_refs()
GetManagerEngagementManagersObjects.update_forward_refs()
GetManagerEngagementManagersObjectsValidities.update_forward_refs()
GetManagerEngagementManagersObjectsValiditiesEngagementResponse.update_forward_refs()
