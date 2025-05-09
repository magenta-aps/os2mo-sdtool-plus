from uuid import UUID

from .base_model import BaseModel


class TerminateAddress(BaseModel):
    address_terminate: "TerminateAddressAddressTerminate"


class TerminateAddressAddressTerminate(BaseModel):
    uuid: UUID


TerminateAddress.update_forward_refs()
TerminateAddressAddressTerminate.update_forward_refs()
