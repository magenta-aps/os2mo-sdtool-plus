from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetEngagementTimeline(BaseModel):
    engagements: "GetEngagementTimelineEngagements"


class GetEngagementTimelineEngagements(BaseModel):
    objects: List["GetEngagementTimelineEngagementsObjects"]


class GetEngagementTimelineEngagementsObjects(BaseModel):
    uuid: UUID
    validities: List["GetEngagementTimelineEngagementsObjectsValidities"]


class GetEngagementTimelineEngagementsObjectsValidities(BaseModel):
    user_key: str
    primary: Optional["GetEngagementTimelineEngagementsObjectsValiditiesPrimary"]
    validity: "GetEngagementTimelineEngagementsObjectsValiditiesValidity"
    extension_1: Optional[str]
    extension_2: Optional[str]
    extension_3: Optional[str]
    extension_4: Optional[str]
    extension_5: Optional[str]
    extension_6: Optional[str]
    extension_7: Optional[str]
    extension_8: Optional[str]
    extension_9: Optional[str]
    extension_10: Optional[str]
    person: List["GetEngagementTimelineEngagementsObjectsValiditiesPerson"]
    org_unit: List["GetEngagementTimelineEngagementsObjectsValiditiesOrgUnit"]
    engagement_type: "GetEngagementTimelineEngagementsObjectsValiditiesEngagementType"
    job_function: "GetEngagementTimelineEngagementsObjectsValiditiesJobFunction"


class GetEngagementTimelineEngagementsObjectsValiditiesPrimary(BaseModel):
    uuid: UUID


class GetEngagementTimelineEngagementsObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


class GetEngagementTimelineEngagementsObjectsValiditiesPerson(BaseModel):
    uuid: UUID


class GetEngagementTimelineEngagementsObjectsValiditiesOrgUnit(BaseModel):
    uuid: UUID


class GetEngagementTimelineEngagementsObjectsValiditiesEngagementType(BaseModel):
    uuid: UUID
    user_key: str
    name: str


class GetEngagementTimelineEngagementsObjectsValiditiesJobFunction(BaseModel):
    uuid: UUID
    user_key: str


GetEngagementTimeline.update_forward_refs()
GetEngagementTimelineEngagements.update_forward_refs()
GetEngagementTimelineEngagementsObjects.update_forward_refs()
GetEngagementTimelineEngagementsObjectsValidities.update_forward_refs()
GetEngagementTimelineEngagementsObjectsValiditiesPrimary.update_forward_refs()
GetEngagementTimelineEngagementsObjectsValiditiesValidity.update_forward_refs()
GetEngagementTimelineEngagementsObjectsValiditiesPerson.update_forward_refs()
GetEngagementTimelineEngagementsObjectsValiditiesOrgUnit.update_forward_refs()
GetEngagementTimelineEngagementsObjectsValiditiesEngagementType.update_forward_refs()
GetEngagementTimelineEngagementsObjectsValiditiesJobFunction.update_forward_refs()
