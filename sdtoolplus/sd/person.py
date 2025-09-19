# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import asyncio
import datetime
from datetime import date

import structlog.stdlib
from more_itertools import one
from sdclient.client import SDClient
from sdclient.exceptions import SDRootElementNotFound
from sdclient.requests import GetEmploymentChangedRequest
from sdclient.requests import GetPersonRequest
from sdclient.responses import GetEmploymentChangedResponse

from sdtoolplus.exceptions import MoreThanOnePersonError
from sdtoolplus.exceptions import PersonNotFoundError
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
    try:
        sd_response = await asyncio.to_thread(
            sd_client.get_person,
            GetPersonRequest(
                InstitutionIdentifier=institution_identifier,
                PersonCivilRegistrationIdentifier=cpr,
                EffectiveDate=effective_date,
                ContactInformationIndicator=contact_information,
                StatusPassiveIndicator=True,
                PostalAddressIndicator=postal_address,
            ),
        )
    except SDRootElementNotFound as sd_error:
        logger.warning(
            "Person not found in SD",
            institution_identifier=institution_identifier,
            cpr=cpr,
            error=sd_error.error,
        )
        raise PersonNotFoundError()

    sd_response_person = one(
        sd_response.Person,
        too_short=PersonNotFoundError,
        too_long=MoreThanOnePersonError,
    )

    person = Person(
        cpr=sd_response_person.PersonCivilRegistrationIdentifier,
        given_name=sd_response_person.PersonGivenName,
        surname=sd_response_person.PersonSurnameName,
        emails=[],
        phone_numbers=[],
        addresses=[],
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
    persons = []
    for sd_response_person in sd_response.Person:
        try:
            person = Person(
                cpr=sd_response_person.PersonCivilRegistrationIdentifier,
                given_name=str(sd_response_person.PersonGivenName),
                surname=str(sd_response_person.PersonSurnameName),
                emails=[],
                phone_numbers=[],
                addresses=[],
            )
        except ValueError as error:
            logger.error("Could not parse person", person=sd_response_person)
            raise error
        persons.append(person)

    return persons


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
