from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class UpdateAddress(BaseModel):
    address_update: "UpdateAddressAddressUpdate"


class UpdateAddressAddressUpdate(BaseModel):
    uuid: UUID
    current: Optional["UpdateAddressAddressUpdateCurrent"]


class UpdateAddressAddressUpdateCurrent(BaseModel):
    validity: "UpdateAddressAddressUpdateCurrentValidity"
    uuid: UUID
    name: Optional[str]
    address_type: "UpdateAddressAddressUpdateCurrentAddressType"


class UpdateAddressAddressUpdateCurrentValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


class UpdateAddressAddressUpdateCurrentAddressType(BaseModel):
    user_key: str


UpdateAddress.update_forward_refs()
UpdateAddressAddressUpdate.update_forward_refs()
UpdateAddressAddressUpdateCurrent.update_forward_refs()
UpdateAddressAddressUpdateCurrentValidity.update_forward_refs()
UpdateAddressAddressUpdateCurrentAddressType.update_forward_refs()
