from datetime import datetime
from typing import Any
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetAllEngagements(BaseModel):
    engagements: "GetAllEngagementsEngagements"


class GetAllEngagementsEngagements(BaseModel):
    objects: List["GetAllEngagementsEngagementsObjects"]


class GetAllEngagementsEngagementsObjects(BaseModel):
    uuid: UUID
    validities: List["GetAllEngagementsEngagementsObjectsValidities"]


class GetAllEngagementsEngagementsObjectsValidities(BaseModel):
    user_key: str
    validity: "GetAllEngagementsEngagementsObjectsValiditiesValidity"
    person: List["GetAllEngagementsEngagementsObjectsValiditiesPerson"]


class GetAllEngagementsEngagementsObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


class GetAllEngagementsEngagementsObjectsValiditiesPerson(BaseModel):
    cpr_number: Optional[Any]


GetAllEngagements.update_forward_refs()
GetAllEngagementsEngagements.update_forward_refs()
GetAllEngagementsEngagementsObjects.update_forward_refs()
GetAllEngagementsEngagementsObjectsValidities.update_forward_refs()
GetAllEngagementsEngagementsObjectsValiditiesValidity.update_forward_refs()
GetAllEngagementsEngagementsObjectsValiditiesPerson.update_forward_refs()
