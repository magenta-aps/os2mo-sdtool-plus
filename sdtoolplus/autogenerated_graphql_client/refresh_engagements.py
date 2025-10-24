from typing import Any
from typing import List
from typing import Optional
from uuid import UUID

from .base_model import BaseModel


class RefreshEngagements(BaseModel):
    engagement_refresh: "RefreshEngagementsEngagementRefresh"


class RefreshEngagementsEngagementRefresh(BaseModel):
    objects: List[UUID]
    page_info: "RefreshEngagementsEngagementRefreshPageInfo"


class RefreshEngagementsEngagementRefreshPageInfo(BaseModel):
    next_cursor: Optional[Any]


RefreshEngagements.update_forward_refs()
RefreshEngagementsEngagementRefresh.update_forward_refs()
RefreshEngagementsEngagementRefreshPageInfo.update_forward_refs()
