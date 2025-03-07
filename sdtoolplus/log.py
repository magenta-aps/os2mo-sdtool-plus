# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import re

CPR_REGEX = re.compile("[0-9]{10}")


def anonymize_cpr(cpr: str) -> str:
    assert CPR_REGEX.match(cpr)
    return cpr[:6] + "xxxx"
