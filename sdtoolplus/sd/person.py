# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import asyncio
from datetime import date
from typing import Callable

import structlog.stdlib
from more_itertools import nth
from more_itertools import one
from sdclient.client import SDClient
from sdclient.exceptions import SDRootElementNotFound
from sdclient.requests import GetEmploymentChangedRequest
from sdclient.requests import GetPersonRequest
from sdclient.responses import ContactInformation
from sdclient.responses import GetEmploymentChangedResponse
from sdclient.responses import PersonEmployment

from sdtoolplus.exceptions import MoreThanOnePersonError
from sdtoolplus.exceptions import PersonNotFoundError
from sdtoolplus.models import Engagement
from sdtoolplus.models import EngagementAddresses
from sdtoolplus.models import Person

logger = structlog.stdlib.get_logger()


def _get_phone_numbers(
    contact_info: ContactInformation | None,
) -> tuple[str | None, str | None]:
    """Get the (maximum) two SD person phone numbers"""
    if contact_info is None or contact_info.TelephoneNumberIdentifier is None:
        return None, None
    phone1 = nth(contact_info.TelephoneNumberIdentifier, 0, None)
    phone2 = nth(contact_info.TelephoneNumberIdentifier, 1, None)
    return phone1, phone2


def _get_emails(
    contact_info: ContactInformation | None,
) -> tuple[str | None, str | None]:
    """Get the (maximum) two SD person emails"""
    if contact_info is None or contact_info.EmailAddressIdentifier is None:
        return None, None
    email1 = nth(contact_info.EmailAddressIdentifier, 0, None)
    email2 = nth(contact_info.EmailAddressIdentifier, 1, None)
    return email1, email2


def _get_employment_addresses(
    institution_identifier: str,
    cpr: str,
    employments: list[PersonEmployment],
    address_extractor: Callable[
        [ContactInformation | None], tuple[str | None, str | None]
    ],
) -> list[EngagementAddresses]:
    """Get the (maximum) two SD person employment addresses for each employment"""
    engagement_phone_numbers = []
    for employment in employments:
        engagement = Engagement(
            institution_identifier=institution_identifier,
            cpr=cpr,
            employment_identifier=employment.EmploymentIdentifier,
        )
        address1, address2 = address_extractor(employment.ContactInformation)

        engagement_phone_numbers.append(
            EngagementAddresses(
                engagement=engagement,
                address1=address1,
                address2=address2,
            )
        )
    return engagement_phone_numbers


# Persons in SD has no timeline and can only be queried at a specific date
async def get_sd_person(
    sd_client: SDClient,
    institution_identifier: str,
    cpr: str,
    effective_date: date,
    contact_information: bool = True,
    postal_address: bool = True,
) -> Person:
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

    sd_person_response = one(
        sd_response.Person,
        too_short=PersonNotFoundError,
        too_long=MoreThanOnePersonError,
    )

    sd_person_phone_number1, sd_person_phone_number2 = _get_phone_numbers(
        sd_person_response.ContactInformation
    )

    sd_postal_address = (
        f"{sd_person_response.PostalAddress.StandardAddressIdentifier}, {sd_person_response.PostalAddress.PostalCode}, {sd_person_response.PostalAddress.DistrictName}"
        if sd_person_response.PostalAddress is not None
        and sd_person_response.PostalAddress.StandardAddressIdentifier is not None
        and sd_person_response.PostalAddress.PostalCode is not None
        and sd_person_response.PostalAddress.DistrictName is not None
        and sd_person_response.PostalAddress.StandardAddressIdentifier
        != "**ADRESSEBESKYTTELSE**"
        else None
    )

    sd_person_email1, sd_person_email2 = _get_emails(
        sd_person_response.ContactInformation
    )

    sd_eng_phone_numbers = _get_employment_addresses(
        institution_identifier, cpr, sd_person_response.Employment, _get_phone_numbers
    )

    sd_eng_emails = _get_employment_addresses(
        institution_identifier, cpr, sd_person_response.Employment, _get_emails
    )

    person = Person(
        cpr=sd_person_response.PersonCivilRegistrationIdentifier,
        given_name=sd_person_response.PersonGivenName,
        surname=sd_person_response.PersonSurnameName,
        person_email1=sd_person_email1,
        person_email2=sd_person_email2,
        person_phone_number1=sd_person_phone_number1,
        person_phone_number2=sd_person_phone_number2,
        person_address=sd_postal_address,
        engagement_phone_numbers=sd_eng_phone_numbers,
        engagement_emails=sd_eng_emails,
    )
    logger.debug("SD person", person=person.dict())

    return person


async def get_all_sd_persons(
    sd_client: SDClient,
    institution_identifier: str,
    effective_date: date,
    only_active_persons: bool,
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
            StatusPassiveIndicator=not only_active_persons,
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
            ActivationDate=date.min,
            DeactivationDate=date.max,
            DepartmentIndicator=True,
            EmploymentStatusIndicator=True,
            ProfessionIndicator=True,
            WorkingTimeIndicator=True,
            UUIDIndicator=True,
        ),
    )
