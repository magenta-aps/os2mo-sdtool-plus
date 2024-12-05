# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
FROM python:3.11
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VERSION=1.3.1 \
    ENVIRONMENT=production \
    RUN_ALEMBIC_MIGRATIONS=true

RUN curl -sSL https://install.python-poetry.org | python3 -
COPY pyproject.toml poetry.lock ./

RUN POETRY_NO_INTERACTION=1 /opt/poetry/bin/poetry install --no-root

COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY docker/start.sh ./docker/start.sh
COPY scripts ./scripts
COPY sdtoolplus ./sdtoolplus

# Useful for debugging
RUN apt update && apt install -y jq vim less

ENTRYPOINT ["./docker/start.sh"]

# Add build version to the environment last to avoid build cache misses
ARG COMMIT_TAG
ARG COMMIT_SHA
ENV COMMIT_TAG=${COMMIT_TAG:-HEAD} \
    COMMIT_SHA=${COMMIT_SHA}
