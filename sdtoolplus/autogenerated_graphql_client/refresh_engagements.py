from typing import List
from uuid import UUID

from .base_model import BaseModel


class RefreshEngagements(BaseModel):
    engagement_refresh: "RefreshEngagementsEngagementRefresh"


class RefreshEngagementsEngagementRefresh(BaseModel):
    objects: List[UUID]


RefreshEngagements.update_forward_refs()
RefreshEngagementsEngagementRefresh.update_forward_refs()
