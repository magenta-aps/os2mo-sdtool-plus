# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import asyncio
import datetime
from datetime import date

import structlog.stdlib
from more_itertools import one
from sdclient.client import SDClient
from sdclient.requests import GetEmploymentChangedRequest
from sdclient.requests import GetPersonRequest
from sdclient.responses import GetEmploymentChangedResponse

from sdtoolplus.models import Person

logger = structlog.stdlib.get_logger()


# Persons in SD has no timeline and can only be queried at a specific date
async def get_sd_person(
    sd_client: SDClient,
    institution_identifier: str,
    cpr: str,
    effective_date: date,
    contact_information: bool = True,
    postal_address: bool = True,
):
    sd_response = await asyncio.to_thread(
        sd_client.get_person,
        GetPersonRequest(
            InstitutionIdentifier=institution_identifier,
            PersonCivilRegistrationIdentifier=cpr,
            EffectiveDate=effective_date,
            ContactInformationIndicator=contact_information,
            PostalAddressIndicator=postal_address,
        ),
    )

    sd_response_person = one(sd_response.Person)

    person = Person(
        cpr=sd_response_person.PersonCivilRegistrationIdentifier,
        given_name=sd_response_person.PersonGivenName,
        surname=sd_response_person.PersonSurnameName,
        emails=sd_response_person.ContactInformation.EmailAddressIdentifier
        if sd_response_person.ContactInformation
        else [],
        phone_numbers=sd_response_person.ContactInformation.TelephoneNumberIdentifier
        if sd_response_person.ContactInformation
        else [],
        address=f"{sd_response_person.PostalAddress.StandardAddressIdentifier}, {sd_response_person.PostalAddress.PostalCode}, {sd_response_person.PostalAddress.DistrictName}"
        if sd_response_person.PostalAddress
        else None,
    )
    logger.debug("SD person", person=person.dict())

    return person


async def get_all_sd_persons(
    sd_client: SDClient,
    institution_identifier: str,
    effective_date: date,
    contact_information: bool = False,
    postal_address: bool = False,
) -> list[Person]:
    # TODO: handle SD call errors
    sd_response = await asyncio.to_thread(
        sd_client.get_person,
        GetPersonRequest(
            InstitutionIdentifier=institution_identifier,
            PersonCivilRegistrationIdentifier=None,
            EffectiveDate=effective_date,
            ContactInformationIndicator=contact_information,
            PostalAddressIndicator=postal_address,
        ),
    )
    return [
        Person(
            cpr=sd_response_person.PersonCivilRegistrationIdentifier,
            given_name=sd_response_person.PersonGivenName,
            surname=sd_response_person.PersonSurnameName,
            emails=[],
            phone_numbers=[],
            address=None,
        )
        for sd_response_person in sd_response.Person
    ]


async def get_sd_person_engagements(
    sd_client: SDClient, institution_identifier: str, cpr: str
) -> GetEmploymentChangedResponse:
    return await asyncio.to_thread(
        sd_client.get_employment_changed,
        GetEmploymentChangedRequest(
            InstitutionIdentifier=institution_identifier,
            PersonCivilRegistrationIdentifier=cpr,
            ActivationDate=datetime.date.min,
            DeactivationDate=datetime.date.max,
        ),
    )
