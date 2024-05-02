# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from fastramqpi.config import Settings as FastRAMQPISettings
from pydantic import AnyHttpUrl
from pydantic import BaseSettings
from pydantic import EmailStr
from pydantic import Field
from pydantic import PositiveInt
from pydantic import SecretStr
from pydantic import validator

from .log import LogLevel
from .mo_org_unit_importer import OrgUnitUUID


class SDToolPlusSettings(BaseSettings):
    fastramqpi: FastRAMQPISettings = Field(
        default_factory=FastRAMQPISettings, description="FastRAMQPI settings"
    )

    # Credentials, etc. for authenticating against MO and performing GraphQL queries
    mora_base: str = "http://mo:5000"
    client_id: str = "integration_sdtool_plus"
    client_secret: SecretStr
    auth_realm: str = "mo"
    auth_server: str = "http://keycloak:8080/auth"

    httpx_timeout_ny_logic: PositiveInt = 120

    # Compare the SD tree to the MO tree found at the path. The path must be a
    # list of UUIDs
    mo_subtree_path_for_root: list[OrgUnitUUID] = []

    # Configures log level
    log_level: LogLevel = LogLevel.INFO

    # Configures Sentry error monitoring
    sentry_dsn: str | None = None

    # Credentials, etc. for authenticating against SD and performing SD API calls
    sd_username: str
    sd_institution_identifier: str
    sd_password: SecretStr

    # Specifies the 'user_key' of the `org_unit_type` class to use when creating new
    # org units in MO. The default value matches the existing setup at SD customers.
    org_unit_type: str = "Enhed"
    sd_lon_base_url: AnyHttpUrl = "http://sdlon:8000"  # type: ignore

    # In some cases, the SD InstitutionIdentifier UUID does not match the MO
    # organization UUID (which it should), so in such cases we can override
    # the UUID of the SD root to match the MO organization UUID
    use_mo_root_uuid_as_sd_root_uuid: bool = False

    # Do not add or update org units whose names match one or more of these
    # regular expressions
    regex_unit_names_to_remove: list[str] = []

    # Database settings for the RunDB
    db_user: str = "sdtool_plus"
    db_password: SecretStr
    db_host: str = "sd-db"
    db_name: str = "sdtool_plus"

    # List of UUIDs of "Udgåede afdelinger" (there can be several of these)
    obsolete_unit_roots: list[OrgUnitUUID]

    # Extend parent validities recursively if the validity of a unit
    # exceeds that of the parent unit
    extend_parent_validities: bool = False

    # If true, we will build the entire SD tree, i.e. by including
    # the units found in SDs GetDepartment, but not in GetOrganization.
    # The units missing from the latter are those in the tree branches,
    # who do not have an "Afdelings-niveau" as leafs.
    build_extra_tree: bool = False

    # Email notifications
    email_notifications_enabled: bool = False
    email_host: str = ""
    email_user: str = ""
    email_password: SecretStr = SecretStr("")
    email_port: PositiveInt = 465
    email_from: EmailStr | None = None
    email_to: list[EmailStr] = []

    @validator("obsolete_unit_roots")
    def obsolete_unit_roots_not_empty(cls, v):
        if len(v) == 0:
            raise ValueError("OBSOLETE_UNIT_ROOTS cannot not be empty")
        return v

    class Config:
        env_nested_delimiter = "__"


def get_settings(*args, **kwargs) -> SDToolPlusSettings:
    return SDToolPlusSettings(*args, **kwargs)
