# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import asyncio
from datetime import date

from more_itertools import one
from sdclient.client import SDClient
from sdclient.requests import GetPersonRequest

from sdtoolplus.models import Person


# Persons in SD has no timeline and can only be queried at a specific date
async def get_sd_person(
    sd_client: SDClient,
    institution_identifier: str,
    cpr: str,
    effective_date: date,
) -> Person:
    sd_response = await asyncio.to_thread(
        sd_client.get_person,
        GetPersonRequest(
            InstitutionIdentifier=institution_identifier,
            PersonCivilRegistrationIdentifier=cpr,
            EffectiveDate=effective_date,
            ContactInformationIndicator=True,
            PostalAddressIndicator=True,
        ),
    )

    sd_response_person = one(sd_response.Person)

    return Person(
        cpr=sd_response_person.PersonCivilRegistrationIdentifier,
        given_name=sd_response_person.PersonGivenName,
        surname=sd_response_person.PersonSurnameName,
    )
