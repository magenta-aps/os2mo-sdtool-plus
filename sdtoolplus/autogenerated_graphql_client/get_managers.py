from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetManagers(BaseModel):
    managers: "GetManagersManagers"


class GetManagersManagers(BaseModel):
    objects: List["GetManagersManagersObjects"]


class GetManagersManagersObjects(BaseModel):
    uuid: UUID
    validities: List["GetManagersManagersObjectsValidities"]


class GetManagersManagersObjectsValidities(BaseModel):
    validity: "GetManagersManagersObjectsValiditiesValidity"


class GetManagersManagersObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


GetManagers.update_forward_refs()
GetManagersManagers.update_forward_refs()
GetManagersManagersObjects.update_forward_refs()
GetManagersManagersObjectsValidities.update_forward_refs()
GetManagersManagersObjectsValiditiesValidity.update_forward_refs()
