from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetAddressTimeline(BaseModel):
    addresses: "GetAddressTimelineAddresses"


class GetAddressTimelineAddresses(BaseModel):
    objects: List["GetAddressTimelineAddressesObjects"]


class GetAddressTimelineAddressesObjects(BaseModel):
    uuid: UUID
    validities: List["GetAddressTimelineAddressesObjectsValidities"]


class GetAddressTimelineAddressesObjectsValidities(BaseModel):
    address_type: "GetAddressTimelineAddressesObjectsValiditiesAddressType"
    visibility_uuid: Optional[UUID]
    user_key: str
    value: str
    uuid: UUID
    validity: "GetAddressTimelineAddressesObjectsValiditiesValidity"


class GetAddressTimelineAddressesObjectsValiditiesAddressType(BaseModel):
    uuid: UUID
    name: str
    user_key: str


class GetAddressTimelineAddressesObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


GetAddressTimeline.update_forward_refs()
GetAddressTimelineAddresses.update_forward_refs()
GetAddressTimelineAddressesObjects.update_forward_refs()
GetAddressTimelineAddressesObjectsValidities.update_forward_refs()
GetAddressTimelineAddressesObjectsValiditiesAddressType.update_forward_refs()
GetAddressTimelineAddressesObjectsValiditiesValidity.update_forward_refs()
