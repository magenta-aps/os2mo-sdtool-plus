# Generated by ariadne-codegen on 2025-04-11 09:35
# Source: queries.graphql

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class CreateAddress(BaseModel):
    address_create: "CreateAddressAddressCreate"


class CreateAddressAddressCreate(BaseModel):
    current: Optional["CreateAddressAddressCreateCurrent"]


class CreateAddressAddressCreateCurrent(BaseModel):
    validity: "CreateAddressAddressCreateCurrentValidity"
    uuid: UUID
    name: Optional[str]
    address_type: "CreateAddressAddressCreateCurrentAddressType"


class CreateAddressAddressCreateCurrentValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


class CreateAddressAddressCreateCurrentAddressType(BaseModel):
    user_key: str


CreateAddress.update_forward_refs()
CreateAddressAddressCreate.update_forward_refs()
CreateAddressAddressCreateCurrent.update_forward_refs()
CreateAddressAddressCreateCurrentValidity.update_forward_refs()
CreateAddressAddressCreateCurrentAddressType.update_forward_refs()
