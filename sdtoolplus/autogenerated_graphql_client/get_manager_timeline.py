from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from ..types import CPRNumber
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
    person: Optional[List["GetManagerTimelineManagersObjectsValiditiesPerson"]]
    validity: "GetManagerTimelineManagersObjectsValiditiesValidity"


class GetManagerTimelineManagersObjectsValiditiesPerson(BaseModel):
    uuid: UUID
    cpr_number: Optional[CPRNumber]
    engagements: List["GetManagerTimelineManagersObjectsValiditiesPersonEngagements"]


class GetManagerTimelineManagersObjectsValiditiesPersonEngagements(BaseModel):
    user_key: str
    validity: "GetManagerTimelineManagersObjectsValiditiesPersonEngagementsValidity"


class GetManagerTimelineManagersObjectsValiditiesPersonEngagementsValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


class GetManagerTimelineManagersObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


GetManagerTimeline.update_forward_refs()
GetManagerTimelineManagers.update_forward_refs()
GetManagerTimelineManagersObjects.update_forward_refs()
GetManagerTimelineManagersObjectsValidities.update_forward_refs()
GetManagerTimelineManagersObjectsValiditiesPerson.update_forward_refs()
GetManagerTimelineManagersObjectsValiditiesPersonEngagements.update_forward_refs()
GetManagerTimelineManagersObjectsValiditiesPersonEngagementsValidity.update_forward_refs()
GetManagerTimelineManagersObjectsValiditiesValidity.update_forward_refs()
