from typing import List
from uuid import UUID

from .base_model import BaseModel


class GetOrgUnitUserKeys(BaseModel):
    org_units: "GetOrgUnitUserKeysOrgUnits"


class GetOrgUnitUserKeysOrgUnits(BaseModel):
    objects: List["GetOrgUnitUserKeysOrgUnitsObjects"]


class GetOrgUnitUserKeysOrgUnitsObjects(BaseModel):
    uuid: UUID
    validities: List["GetOrgUnitUserKeysOrgUnitsObjectsValidities"]


class GetOrgUnitUserKeysOrgUnitsObjectsValidities(BaseModel):
    user_key: str


GetOrgUnitUserKeys.update_forward_refs()
GetOrgUnitUserKeysOrgUnits.update_forward_refs()
GetOrgUnitUserKeysOrgUnitsObjects.update_forward_refs()
GetOrgUnitUserKeysOrgUnitsObjectsValidities.update_forward_refs()
