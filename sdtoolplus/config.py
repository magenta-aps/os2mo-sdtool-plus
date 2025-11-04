# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

from fastramqpi.config import Settings as FastRAMQPISettings
from pydantic import AmqpDsn
from pydantic import AnyHttpUrl
from pydantic import BaseModel
from pydantic import BaseSettings
from pydantic import EmailStr
from pydantic import Field
from pydantic import PositiveInt
from pydantic import SecretStr
from pydantic import root_validator

from .mo_org_unit_importer import OrgUnitUUID

SD_RETRY_WAIT_TIME = 15
SD_RETRY_ATTEMPTS = 10
TIMEZONE = ZoneInfo("Europe/Copenhagen")
PNUMBER_CLASS_USER_KEY = "Pnummer"


class Mode(Enum):
    MUNICIPALITY = "municipality"
    REGION = "region"


class AMQPTLS(BaseModel):
    ca: bytes
    cert: bytes
    key: bytes


class SDAMQPSettings(BaseModel):
    url: AmqpDsn
    tls: AMQPTLS | None = None

    class Config:
        env_nested_delimiter = "__"


class SDToolPlusSettings(BaseSettings):
    fastramqpi: FastRAMQPISettings = Field(
        default_factory=FastRAMQPISettings, description="FastRAMQPI settings"
    )

    apply_ny_logic: bool = True
    httpx_timeout_ny_logic: PositiveInt = 120

    # Compare the SD tree to the MO tree found at the path. The path must be a
    # list of UUIDs
    mo_subtree_path_for_root: list[OrgUnitUUID] = []

    # Same as the above, but for the case where there are multiple
    # InstitutionIdentifiers. In this case we make a map from the InstitutionIdentifier
    # to the list of OrgUnitUUIDs. If this ENV is set, it will take precedence over the
    # above.
    mo_subtree_paths_for_root: dict[str, list[OrgUnitUUID]] | None = None

    # Some of the SD institution units (i.e. the MO units which are
    # *institutions* and NOT *departments* in SD) may for historic reasons have
    # been created with random UUIDs in MO, which does not match the SD
    # institution UUIDs. This ENV maps the SD institution UUIDs to the MO unit
    # UUIDs which is needed in order to keep the children of the SD institutions
    # in (OU) sync. Note that this map is only for the top MO units
    # corresponding to an SD institution.
    sd_institution_to_mo_root_ou_uuid_map: dict[OrgUnitUUID, OrgUnitUUID] = dict()

    # In some cases, the name of an SD institution (or department) needs to be
    # something other than the value in SD
    sd_to_mo_ou_name_map: dict[OrgUnitUUID, str] = dict()

    # Configures Sentry error monitoring
    sentry_dsn: str | None = None

    # Credentials, etc. for authenticating against SD and performing SD API calls
    sd_username: str
    sd_institution_identifier: str
    sd_region_identifier: str | None = None
    sd_password: SecretStr
    sd_use_test_env: bool = False

    # Whether to run in "municipality" mode or "region" mode.
    # In "municipality" mode, we
    # 1) Do not prefix unitIDs with the SD institution identifier
    # 2) May (or may not) apply the NY-logic, which elevates engagement from
    #    "Afdelings-niveau" to the parent "NY-niveau" - see the APPLY_NY_LOGIC flag.
    # In "region" mode, we
    # 1) Prefix unitIDs with the SD institution identifier
    # 2) Apply the special engagement OU strategy for the regions.
    mode: Mode = Mode.MUNICIPALITY

    # If true, we prefix the engagement user keys in "municipality" mode
    prefix_engagement_user_keys: bool = False

    # A list of engagement type user keys which the application is allowed to process
    engagement_types_to_process: list[str] = [
        "timelønnet",
        "deltid",
        "fuldtid",
        "recalculate",
    ]

    # Enable new event-based timeline-sync
    event_based_sync: bool = False
    # If true, we only process SD events and not MO events
    disable_mo_events: bool = False

    # SD AMQP
    sd_amqp: SDAMQPSettings | None = None

    # Specifies the 'user_key' of the `org_unit_type` class to use when creating new
    # org units in MO. The default value matches the existing setup at SD customers.
    org_unit_type: str = "Enhed"
    sd_lon_base_url: AnyHttpUrl = "http://sdlon:8000"  # type: ignore

    # If true, the application will ensure that the SD institutions (which are
    # NOT SD units) are created as MO units with the same UUIDs as the SD
    # institutions in the unit tree location specified by the
    # "mo_subtree_paths_for_root" setting
    ensure_sd_institution_units: bool = False

    # In some cases, the SD InstitutionIdentifier UUID does not match the MO
    # organization UUID (which it should), so in such cases we can override
    # the UUID of the SD root to match the MO organization UUID
    use_mo_root_uuid_as_sd_root_uuid: bool = False

    # Do not add org units whose names match one or more of these
    # regular expressions
    regex_unit_names_to_remove: list[str] = []

    # Apply regex name filter on updates
    apply_name_filter_on_update: bool = True

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

    # Whether to enable org unit address sync. NOTE: this flag is not used in
    # the legacy part of the SDTool+ integration.
    enable_ou_address_sync: bool = True
    # If true, OU addresses will be persisted to MO as DAR address UUIDs
    use_dar_addresses: bool = False
    # If true, only the postal addresses from the line management
    # ("Linjeorganisationen") org units are synchronized. This flag is only
    # used in the legacy part of the SDTool+ integration.
    only_sync_line_mgmt_postal_addresses: bool = False

    # Truncate the SD unit start dates to min_mo_datetime, if the SD start date
    # for a unit is before this datetime
    min_mo_datetime: datetime = datetime(1930, 1, 1, tzinfo=TIMEZONE)

    # Email notifications
    email_notifications_enabled: bool = False
    email_host: str = ""
    email_user: str = ""
    email_password: SecretStr = SecretStr("")
    email_port: PositiveInt = 587
    email_use_login: bool = True
    email_from: EmailStr | None = None
    email_to: list[EmailStr] = []

    # Disable email notifications for these units
    # (see https://redmine.magenta.dk/issues/61134)
    email_notifications_disabled_units: list[OrgUnitUUID] = []
    ##################################################################

    # UUID of the unit "Ukendt" (only used when running in "region" mode)
    unknown_unit: OrgUnitUUID | None = None

    # If the engagement SD unit UUID value changes (stored in MOs engagement attribute
    # extension_5), we will re-calculate the engagement placement - see the
    # engagement_ou_strategy_region. The only situation where this flag has to be set
    # to "False" is for the initial population of the extension_5 attribute
    # (this setting is only used in "region" mode)
    recalc_mo_unit_when_sd_employment_moved: bool = True

    class Config:
        env_nested_delimiter = "__"

    @root_validator
    def check_region_settings(cls, values: dict[str, Any]) -> dict[str, Any]:
        if not values["mode"] == Mode.REGION:
            return values

        if values["unknown_unit"] is None:
            raise ValueError("Unknown unit must be set when running in region mode")
        if values["apply_ny_logic"] is True:
            raise ValueError("Apply NY logic not allowed to be enabled in region mode")
        if values["mo_subtree_paths_for_root"] is None:
            raise ValueError("MO_SUBTREE_PATHS_FOR_ROOT must be set in region mode")
        if values["prefix_engagement_user_keys"] is False:
            raise ValueError("prefix_engagement_user_keys must be true in region mode")

        return values

    @root_validator
    def check_ensure_institution_settings(
        cls, values: dict[str, Any]
    ) -> dict[str, Any]:
        if not values["ensure_sd_institution_units"]:
            return values

        if values["sd_region_identifier"] is None:
            raise ValueError(
                "SD_REGION_IDENTIFIER must be set when ENSURE_SD_INSTITUTION_UNITS is true"
            )
        if values["mo_subtree_paths_for_root"] is None:
            raise ValueError(
                "MO_SUBTREE_PATHS_FOR_ROOT must be set when ENSURE_SD_INSTITUTION_UNITS is true"
            )

        if values["unknown_unit"] is None:
            raise ValueError(
                "UNKNOWN_UNIT must be set when ENSURE_SD_INSTITUTION_UNITS is true"
            )

        return values


def get_settings(*args, **kwargs) -> SDToolPlusSettings:
    return SDToolPlusSettings(*args, **kwargs)
