from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class GetOrgUnitTimeline(BaseModel):
    org_units: "GetOrgUnitTimelineOrgUnits"


class GetOrgUnitTimelineOrgUnits(BaseModel):
    objects: List["GetOrgUnitTimelineOrgUnitsObjects"]


class GetOrgUnitTimelineOrgUnitsObjects(BaseModel):
    validities: List["GetOrgUnitTimelineOrgUnitsObjectsValidities"]


class GetOrgUnitTimelineOrgUnitsObjectsValidities(BaseModel):
    validity: "GetOrgUnitTimelineOrgUnitsObjectsValiditiesValidity"
    uuid: UUID
    user_key: str
    name: str
    org_unit_level: Optional["GetOrgUnitTimelineOrgUnitsObjectsValiditiesOrgUnitLevel"]
    unit_type: Optional["GetOrgUnitTimelineOrgUnitsObjectsValiditiesUnitType"]
    org_unit_hierarchy_model: Optional[
        "GetOrgUnitTimelineOrgUnitsObjectsValiditiesOrgUnitHierarchyModel"
    ]
    time_planning: Optional["GetOrgUnitTimelineOrgUnitsObjectsValiditiesTimePlanning"]
    parent: Optional["GetOrgUnitTimelineOrgUnitsObjectsValiditiesParent"]
    addresses: List["GetOrgUnitTimelineOrgUnitsObjectsValiditiesAddresses"]


class GetOrgUnitTimelineOrgUnitsObjectsValiditiesValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


class GetOrgUnitTimelineOrgUnitsObjectsValiditiesOrgUnitLevel(BaseModel):
    name: str


class GetOrgUnitTimelineOrgUnitsObjectsValiditiesUnitType(BaseModel):
    uuid: UUID


class GetOrgUnitTimelineOrgUnitsObjectsValiditiesOrgUnitHierarchyModel(BaseModel):
    uuid: UUID


class GetOrgUnitTimelineOrgUnitsObjectsValiditiesTimePlanning(BaseModel):
    uuid: UUID


class GetOrgUnitTimelineOrgUnitsObjectsValiditiesParent(BaseModel):
    uuid: UUID


class GetOrgUnitTimelineOrgUnitsObjectsValiditiesAddresses(BaseModel):
    uuid: UUID
    name: Optional[str]
    user_key: str
    value: str
    address_type: "GetOrgUnitTimelineOrgUnitsObjectsValiditiesAddressesAddressType"
    visibility: Optional[
        "GetOrgUnitTimelineOrgUnitsObjectsValiditiesAddressesVisibility"
    ]


class GetOrgUnitTimelineOrgUnitsObjectsValiditiesAddressesAddressType(BaseModel):
    user_key: str
    name: str


class GetOrgUnitTimelineOrgUnitsObjectsValiditiesAddressesVisibility(BaseModel):
    uuid: UUID


GetOrgUnitTimeline.update_forward_refs()
GetOrgUnitTimelineOrgUnits.update_forward_refs()
GetOrgUnitTimelineOrgUnitsObjects.update_forward_refs()
GetOrgUnitTimelineOrgUnitsObjectsValidities.update_forward_refs()
GetOrgUnitTimelineOrgUnitsObjectsValiditiesValidity.update_forward_refs()
GetOrgUnitTimelineOrgUnitsObjectsValiditiesOrgUnitLevel.update_forward_refs()
GetOrgUnitTimelineOrgUnitsObjectsValiditiesUnitType.update_forward_refs()
GetOrgUnitTimelineOrgUnitsObjectsValiditiesOrgUnitHierarchyModel.update_forward_refs()
GetOrgUnitTimelineOrgUnitsObjectsValiditiesTimePlanning.update_forward_refs()
GetOrgUnitTimelineOrgUnitsObjectsValiditiesParent.update_forward_refs()
GetOrgUnitTimelineOrgUnitsObjectsValiditiesAddresses.update_forward_refs()
GetOrgUnitTimelineOrgUnitsObjectsValiditiesAddressesAddressType.update_forward_refs()
GetOrgUnitTimelineOrgUnitsObjectsValiditiesAddressesVisibility.update_forward_refs()
