# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from pydantic import SecretStr
from ra_utils.job_settings import JobSettings


class SDToolPlusSettings(JobSettings):
    client_secret: SecretStr = SecretStr("")  # type: ignore
    sd_username: str | None
    sd_institution_identifier: str | None
    sd_password: SecretStr | None
    org_unit_type: str = "Enhed"
