#!/usr/bin/env bash
# SPDX-FileCopyrightText: Magenta ApS
# SPDX-License-Identifier: MPL-2.0

# Usage:
#   sd-event eng <InstitutionIdentifier> <CPR> <EmploymentIdentifier>
#   sd-event ou  <InstitutionIdentifier> <OrgUnit> [--priority N]
#   sd-event rerun [--namespace NS] [--routing-key KEY]... [--subject SUBJECT]...
#                  [--priority N]...

set -euo pipefail

PYTHONPATH=/app exec python -m scripts.send_event "$@"
