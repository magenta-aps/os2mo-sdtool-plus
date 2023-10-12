# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from pydantic import BaseSettings
from pydantic import SecretStr



class SDToolPlusSettings(BaseSettings):
    # Credentials, etc. for authenticating against MO and performing GraphQL queries
    mora_base: str = "http://mo:5000"
    client_id: str = "dipex"
    client_secret: SecretStr
    auth_realm: str = "mo"
    auth_server: str = "http://keycloak:8080/auth"

    # Configures Sentry error monitoring
    sentry_dsn: str | None = None

    # Credentials, etc. for authenticating against SD and performing SD API calls
    sd_username: str | None
    sd_institution_identifier: str | None
    sd_password: SecretStr | None

    # Specifies the 'user_key' of the `org_unit_type` class to use when creating new
    # org units in MO. The default value matches the existing setup at SD customers.
    org_unit_type: str = "Enhed"
