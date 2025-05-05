#!/bin/bash
# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
set -o nounset
set -o errexit
set -o pipefail

# Apply Alembic migrations
if [ "$RUN_ALEMBIC_MIGRATIONS" = "true" ]; then
    alembic upgrade head
fi

# Run app
if [ "$ENVIRONMENT" = "development" ]; then
    echo "Running in development mode (hot-reload)"
    exec uvicorn --factory sdtoolplus.main:create_app --host 0.0.0.0 --reload
else
    echo "Running in production mode"
    exec uvicorn --factory sdtoolplus.main:create_app --host 0.0.0.0
fi
