from typing import List
from typing import Optional
from uuid import UUID

from .base_model import BaseModel


class GetClass(BaseModel):
    classes: "GetClassClasses"


class GetClassClasses(BaseModel):
    objects: List["GetClassClassesObjects"]


class GetClassClassesObjects(BaseModel):
    uuid: UUID
    current: Optional["GetClassClassesObjectsCurrent"]


class GetClassClassesObjectsCurrent(BaseModel):
    uuid: UUID
    user_key: str
    name: str
    scope: Optional[str]
    parent: Optional["GetClassClassesObjectsCurrentParent"]


class GetClassClassesObjectsCurrentParent(BaseModel):
    uuid: UUID
    user_key: str
    scope: Optional[str]


GetClass.update_forward_refs()
GetClassClasses.update_forward_refs()
GetClassClassesObjects.update_forward_refs()
GetClassClassesObjectsCurrent.update_forward_refs()
GetClassClassesObjectsCurrentParent.update_forward_refs()
