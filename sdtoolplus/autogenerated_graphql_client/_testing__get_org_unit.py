from datetime import datetime
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import BaseModel


class TestingGetOrgUnit(BaseModel):
    org_units: "TestingGetOrgUnitOrgUnits"


class TestingGetOrgUnitOrgUnits(BaseModel):
    objects: List["TestingGetOrgUnitOrgUnitsObjects"]


class TestingGetOrgUnitOrgUnitsObjects(BaseModel):
    current: Optional["TestingGetOrgUnitOrgUnitsObjectsCurrent"]


class TestingGetOrgUnitOrgUnitsObjectsCurrent(BaseModel):
    validity: "TestingGetOrgUnitOrgUnitsObjectsCurrentValidity"
    uuid: UUID
    user_key: str
    name: str
    parent: Optional["TestingGetOrgUnitOrgUnitsObjectsCurrentParent"]
    org_unit_level: Optional["TestingGetOrgUnitOrgUnitsObjectsCurrentOrgUnitLevel"]


class TestingGetOrgUnitOrgUnitsObjectsCurrentValidity(BaseModel):
    from_: datetime = Field(alias="from")
    to: Optional[datetime]


class TestingGetOrgUnitOrgUnitsObjectsCurrentParent(BaseModel):
    uuid: UUID
    name: str


class TestingGetOrgUnitOrgUnitsObjectsCurrentOrgUnitLevel(BaseModel):
    uuid: UUID
    user_key: str
    name: str


TestingGetOrgUnit.update_forward_refs()
TestingGetOrgUnitOrgUnits.update_forward_refs()
TestingGetOrgUnitOrgUnitsObjects.update_forward_refs()
TestingGetOrgUnitOrgUnitsObjectsCurrent.update_forward_refs()
TestingGetOrgUnitOrgUnitsObjectsCurrentValidity.update_forward_refs()
TestingGetOrgUnitOrgUnitsObjectsCurrentParent.update_forward_refs()
TestingGetOrgUnitOrgUnitsObjectsCurrentOrgUnitLevel.update_forward_refs()
