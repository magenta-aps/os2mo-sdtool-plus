# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from pydantic import AnyHttpUrl
from pydantic import BaseSettings
from pydantic import PositiveInt
from pydantic import SecretStr

from .log import LogLevel
from .mo_org_unit_importer import OrgUnitUUID


class SDToolPlusSettings(BaseSettings):
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


def get_settings(*args, **kwargs) -> SDToolPlusSettings:
    return SDToolPlusSettings(*args, **kwargs)
