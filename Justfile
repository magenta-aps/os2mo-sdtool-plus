# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0

test:
    docker compose down
    docker compose up -d --build
    docker compose stop sdtool-plus
    docker compose run --rm sdtool-plus pytest
