from typing import List
from uuid import UUID

from .base_model import BaseModel


class GetEngagementUuids(BaseModel):
    engagements: "GetEngagementUuidsEngagements"


class GetEngagementUuidsEngagements(BaseModel):
    objects: List["GetEngagementUuidsEngagementsObjects"]


class GetEngagementUuidsEngagementsObjects(BaseModel):
    uuid: UUID


GetEngagementUuids.update_forward_refs()
GetEngagementUuidsEngagements.update_forward_refs()
GetEngagementUuidsEngagementsObjects.update_forward_refs()
