# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import pytest
from fastramqpi.config import Settings as FastRAMQPISettings
from fastramqpi.ramqp.config import AMQPConnectionSettings

from sdtoolplus.config import SDToolPlusSettings


def test_obsolete_unit_roots_cannot_be_empty():
    with pytest.raises(ValueError) as error:
        SDToolPlusSettings(
            client_id="client_id",
            client_secret="secret",
            sd_username="sd_username",
            sd_password="sd_password",
            sd_institution_identifier="ii",
            db_password="db_password",
            obsolete_unit_roots=[],  # Not allowed
            fastramqpi=FastRAMQPISettings(
                client_id="client_id",
                client_secret="secret",
                amqp=AMQPConnectionSettings(url="amqp://guest:guest@msg-broker"),
            ),
        )
