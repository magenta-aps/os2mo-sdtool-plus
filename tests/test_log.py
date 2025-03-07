# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import pytest

from sdtoolplus.log import anonymize_cpr


def test_anonymize_cpr():
    assert anonymize_cpr("0101011234") == "010101xxxx"


def test_anonymize_cpr_assert():
    with pytest.raises(AssertionError):
        anonymize_cpr("xyz")
