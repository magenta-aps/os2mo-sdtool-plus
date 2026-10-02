from uuid import UUID

from .base_model import BaseModel


class TestingCreateFacet(BaseModel):
    facet_create: "TestingCreateFacetFacetCreate"


class TestingCreateFacetFacetCreate(BaseModel):
    uuid: UUID


TestingCreateFacet.update_forward_refs()
TestingCreateFacetFacetCreate.update_forward_refs()
