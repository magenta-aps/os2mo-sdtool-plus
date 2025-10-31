from datetime import datetime
from typing import Any
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from ..types import CPRNumber
from .base_model import BaseModel


class GetEngagements(BaseModel):
    engagements: "GetEngagementsEngagements"


class GetEngagementsEngagements(BaseModel):
    page_info: "GetEngagementsEngagementsPageInfo"
    objects: List["GetEngagementsEngagementsObjects"]


class GetEngagementsEngagementsPageInfo(BaseModel):
    next_cursor: Optional[Any]


class GetEngagementsEngagementsObjects(BaseModel):
    uuid: UUID
    validities: List["GetEngagementsEngagementsObjectsValidities"]


class GetEngagementsEngagementsObjectsValidities(BaseModel):
    user_key: str
    validity: "GetEngagementsEngagementsObjectsValiditiesValidity"
    person: List["GetEngagementsEngagementsObjectsValiditiesPerson"]
    engagement_type_uuid: UUID


class GetEngagementsEngagementsObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


class GetEngagementsEngagementsObjectsValiditiesPerson(BaseModel):
    cpr_number: Optional[CPRNumber]


GetEngagements.update_forward_refs()
GetEngagementsEngagements.update_forward_refs()
GetEngagementsEngagementsPageInfo.update_forward_refs()
GetEngagementsEngagementsObjects.update_forward_refs()
GetEngagementsEngagementsObjectsValidities.update_forward_refs()
GetEngagementsEngagementsObjectsValiditiesValidity.update_forward_refs()
GetEngagementsEngagementsObjectsValiditiesPerson.update_forward_refs()
