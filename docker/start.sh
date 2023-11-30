#!/bin/bash
# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
set -o nounset
set -o errexit
set -o pipefail

# Apply Alembic migrations
alembic upgrade head

# Run app
uvicorn --factory sdtoolplus.fastapi:create_app --host 0.0.0.0
