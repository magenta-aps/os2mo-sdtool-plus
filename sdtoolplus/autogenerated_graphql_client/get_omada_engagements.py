from typing import List
from uuid import UUID

from .base_model import BaseModel


class GetOmadaEngagements(BaseModel):
    engagements: "GetOmadaEngagementsEngagements"


class GetOmadaEngagementsEngagements(BaseModel):
    objects: List["GetOmadaEngagementsEngagementsObjects"]


class GetOmadaEngagementsEngagementsObjects(BaseModel):
    validities: List["GetOmadaEngagementsEngagementsObjectsValidities"]


class GetOmadaEngagementsEngagementsObjectsValidities(BaseModel):
    user_key: str
    employee_uuid: UUID


GetOmadaEngagements.update_forward_refs()
GetOmadaEngagementsEngagements.update_forward_refs()
GetOmadaEngagementsEngagementsObjects.update_forward_refs()
GetOmadaEngagementsEngagementsObjectsValidities.update_forward_refs()
