# Generated by ariadne-codegen on 2025-02-24 08:06
# Source: queries.graphql

from uuid import UUID

from .base_model import BaseModel


class TerminateOrgUnit(BaseModel):
    org_unit_terminate: "TerminateOrgUnitOrgUnitTerminate"


class TerminateOrgUnitOrgUnitTerminate(BaseModel):
    uuid: UUID


TerminateOrgUnit.update_forward_refs()
TerminateOrgUnitOrgUnitTerminate.update_forward_refs()
