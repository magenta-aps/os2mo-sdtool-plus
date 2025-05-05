from uuid import UUID

from .base_model import BaseModel


class GetOrganization(BaseModel):
    org: "GetOrganizationOrg"


class GetOrganizationOrg(BaseModel):
    uuid: UUID


GetOrganization.update_forward_refs()
GetOrganizationOrg.update_forward_refs()
