# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from sdtoolplus.config import Mode
from sdtoolplus.config import SDToolPlusSettings


def split_engagement_user_key(
    settings: SDToolPlusSettings, user_key: str
) -> tuple[str, str]:
    if settings.mode == Mode.MUNICIPALITY:
        return settings.sd_institution_identifier, user_key
    institution_identifier, employment_id = user_key.split("-")
    return institution_identifier, employment_id
