from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetOUAddressTimeline(BaseModel):
    addresses: "GetOUAddressTimelineAddresses"


class GetOUAddressTimelineAddresses(BaseModel):
    objects: List["GetOUAddressTimelineAddressesObjects"]


class GetOUAddressTimelineAddressesObjects(BaseModel):
    uuid: UUID
    validities: List["GetOUAddressTimelineAddressesObjectsValidities"]


class GetOUAddressTimelineAddressesObjectsValidities(BaseModel):
    address_type: "GetOUAddressTimelineAddressesObjectsValiditiesAddressType"
    visibility_uuid: Optional[UUID]
    user_key: str
    value: str
    uuid: UUID
    validity: "GetOUAddressTimelineAddressesObjectsValiditiesValidity"


class GetOUAddressTimelineAddressesObjectsValiditiesAddressType(BaseModel):
    uuid: UUID
    name: str
    user_key: str


class GetOUAddressTimelineAddressesObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


GetOUAddressTimeline.update_forward_refs()
GetOUAddressTimelineAddresses.update_forward_refs()
GetOUAddressTimelineAddressesObjects.update_forward_refs()
GetOUAddressTimelineAddressesObjectsValidities.update_forward_refs()
GetOUAddressTimelineAddressesObjectsValiditiesAddressType.update_forward_refs()
GetOUAddressTimelineAddressesObjectsValiditiesValidity.update_forward_refs()
