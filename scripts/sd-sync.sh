# SPDX-FileCopyrightText: Magenta ApS
# SPDX-License-Identifier: MPL-2.0

#!/usr/bin/env bash

# Usage:
#   sd-sync eng <InstitutionIdentifier> <CPR> <EmploymentIdentifier>
#   sd-sync ou  <InstitutionIdentifier> <OrgUnit>
#   sd-sync person <InstitutionIdentifier> <CPR>

set -euo pipefail

BASE_URL="http://localhost:8000/timeline/sync"

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

        curl --json "{
          \"institution_identifier\": \"$INSTITUTION_IDENTIFIER\",
          \"cpr\": \"$CPR\",
          \"employment_identifier\": \"$EMPLOYMENT_IDENTIFIER\"
        }" \
        "$BASE_URL/engagement"
        ;;

    ou)
        if [[ $# -ne 3 ]]; then
            echo "Usage: sd-sync ou <InstitutionIdentifier> <OrgUnit>"
            exit 1
        fi

        INSTITUTION_IDENTIFIER="$2"
        ORG_UNIT="$3"

        curl --json "{
          \"institution_identifier\": \"$INSTITUTION_IDENTIFIER\",
          \"org_unit\": \"$ORG_UNIT\"
        }" \
        "$BASE_URL/ou"
        ;;

    person)
        if [[ $# -ne 3 ]]; then
            echo "Usage: sd-sync person <InstitutionIdentifier> <CPR>"
            exit 1
        fi

        INSTITUTION_IDENTIFIER="$2"
        CPR="$3"

        curl --json "{
          \"institution_identifier\": \"$INSTITUTION_IDENTIFIER\",
          \"cpr\": \"$CPR\"
        }" \
        "$BASE_URL/person"
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
