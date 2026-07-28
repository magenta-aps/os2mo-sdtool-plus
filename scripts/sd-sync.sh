# SPDX-FileCopyrightText: Magenta ApS
# SPDX-License-Identifier: MPL-2.0

#!/usr/bin/env bash

# Usage:
#   sd-sync eng <InstitutionIdentifier> <CPR> <EmploymentIdentifier>
#   sd-sync ou  <InstitutionIdentifier> <OrgUnit>
#   sd-sync person <InstitutionIdentifier> <CPR>

set -euo pipefail

EVENTS_URL="http://localhost:8000/events/sd"

if [[ $# -lt 1 ]]; then
    echo "Usage:"
    echo "  sd-sync eng <InstitutionIdentifier> <CPR> <EmploymentIdentifier>"
    echo "  sd-sync ou <InstitutionIdentifier> <OrgUnit>"
    echo "  sd-sync person <InstitutionIdentifier> <CPR>"
    exit 1
fi

COMMAND="$1"

case "$COMMAND" in
    eng)
        if [[ $# -ne 4 ]]; then
            echo "Usage: sd-sync eng <InstitutionIdentifier> <CPR> <EmploymentIdentifier>"
            exit 1
        fi

        INSTITUTION_IDENTIFIER="$2"
        CPR="$3"
        EMPLOYMENT_IDENTIFIER="$4"

        SUBJECT=$(printf \
          '{"institution_identifier": "%s", "cpr": "%s", "employment_identifier": "%s"}' \
          "$INSTITUTION_IDENTIFIER" "$CPR" "$EMPLOYMENT_IDENTIFIER")
        ESCAPED_SUBJECT=${SUBJECT//\"/\\\"}

        curl --json "{
          \"subject\": \"$ESCAPED_SUBJECT\",
          \"priority\": 9000
        }" \
        "$EVENTS_URL/person-and-employment"
        ;;

    ou)
        if [[ $# -ne 3 ]]; then
            echo "Usage: sd-sync ou <InstitutionIdentifier> <OrgUnit>"
            exit 1
        fi

        INSTITUTION_IDENTIFIER="$2"
        ORG_UNIT="$3"

        SUBJECT=$(printf '{"institution_identifier": "%s", "org_unit": "%s"}' \
          "$INSTITUTION_IDENTIFIER" "$ORG_UNIT")
        ESCAPED_SUBJECT=${SUBJECT//\"/\\\"}

        curl --json "{
          \"subject\": \"$ESCAPED_SUBJECT\",
          \"priority\": 9000
        }" \
        "$EVENTS_URL/org"
        ;;

    person)
        if [[ $# -ne 3 ]]; then
            echo "Usage: sd-sync person <InstitutionIdentifier> <CPR>"
            exit 1
        fi

        INSTITUTION_IDENTIFIER="$2"
        CPR="$3"

        SUBJECT=$(printf '{"institution_identifier": "%s", "cpr": "%s"}' \
          "$INSTITUTION_IDENTIFIER" "$CPR")
        ESCAPED_SUBJECT=${SUBJECT//\"/\\\"}

        curl --json "{
          \"subject\": \"$ESCAPED_SUBJECT\",
          \"priority\": 9000
        }" \
        "$EVENTS_URL/person-and-employment"
        ;;

    *)
        echo "Unknown command: $COMMAND"
        echo
        echo "Supported commands:"
        echo "  eng"
        echo "  ou"
        echo "  person"
        exit 1
        ;;
esac
