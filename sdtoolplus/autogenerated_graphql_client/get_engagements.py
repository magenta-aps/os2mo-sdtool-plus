from datetime import datetime
from typing import Any
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetEngagements(BaseModel):
    engagements: "GetEngagementsEngagements"


class GetEngagementsEngagements(BaseModel):
    objects: List["GetEngagementsEngagementsObjects"]


class GetEngagementsEngagementsObjects(BaseModel):
    uuid: UUID
    validities: List["GetEngagementsEngagementsObjectsValidities"]


class GetEngagementsEngagementsObjectsValidities(BaseModel):
    user_key: str
    validity: "GetEngagementsEngagementsObjectsValiditiesValidity"
    person: List["GetEngagementsEngagementsObjectsValiditiesPerson"]


class GetEngagementsEngagementsObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


class GetEngagementsEngagementsObjectsValiditiesPerson(BaseModel):
    cpr_number: Optional[Any]


GetEngagements.update_forward_refs()
GetEngagementsEngagements.update_forward_refs()
GetEngagementsEngagementsObjects.update_forward_refs()
GetEngagementsEngagementsObjectsValidities.update_forward_refs()
GetEngagementsEngagementsObjectsValiditiesValidity.update_forward_refs()
GetEngagementsEngagementsObjectsValiditiesPerson.update_forward_refs()
