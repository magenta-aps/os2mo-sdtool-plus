from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetLeave(BaseModel):
    leaves: "GetLeaveLeaves"


class GetLeaveLeaves(BaseModel):
    objects: List["GetLeaveLeavesObjects"]


class GetLeaveLeavesObjects(BaseModel):
    uuid: UUID
    validities: List["GetLeaveLeavesObjectsValidities"]


class GetLeaveLeavesObjectsValidities(BaseModel):
    user_key: str
    employee_uuid: UUID
    engagement_uuid: UUID
    leave_type_uuid: UUID
    validity: "GetLeaveLeavesObjectsValiditiesValidity"


class GetLeaveLeavesObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


GetLeave.update_forward_refs()
GetLeaveLeaves.update_forward_refs()
GetLeaveLeavesObjects.update_forward_refs()
GetLeaveLeavesObjectsValidities.update_forward_refs()
GetLeaveLeavesObjectsValiditiesValidity.update_forward_refs()
