from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetManagerEngagements(BaseModel):
    engagements: "GetManagerEngagementsEngagements"


class GetManagerEngagementsEngagements(BaseModel):
    objects: List["GetManagerEngagementsEngagementsObjects"]


class GetManagerEngagementsEngagementsObjects(BaseModel):
    uuid: UUID
    validities: List["GetManagerEngagementsEngagementsObjectsValidities"]


class GetManagerEngagementsEngagementsObjectsValidities(BaseModel):
    user_key: str
    validity: "GetManagerEngagementsEngagementsObjectsValiditiesValidity"


class GetManagerEngagementsEngagementsObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


GetManagerEngagements.update_forward_refs()
GetManagerEngagementsEngagements.update_forward_refs()
GetManagerEngagementsEngagementsObjects.update_forward_refs()
GetManagerEngagementsEngagementsObjectsValidities.update_forward_refs()
GetManagerEngagementsEngagementsObjectsValiditiesValidity.update_forward_refs()
