from typing import List
from uuid import UUID

from .base_model import BaseModel


class GetManagers(BaseModel):
    managers: "GetManagersManagers"


class GetManagersManagers(BaseModel):
    objects: List["GetManagersManagersObjects"]


class GetManagersManagersObjects(BaseModel):
    uuid: UUID


GetManagers.update_forward_refs()
GetManagersManagers.update_forward_refs()
GetManagersManagersObjects.update_forward_refs()
