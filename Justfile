# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0

# set up environment for running tests, rebuilding from scratch
_test-setup-clean:
    docker compose down
    docker compose build --no-cache
    docker compose up -d
    docker compose stop sdtool-plus

# set up environment for running tests
_test-setup:
    docker compose down
    docker compose up -d --build
    docker compose stop sdtool-plus

# run a specified test path, or all tests if {{target}} not set
_test target="":
    docker compose run --rm sdtool-plus pytest {{target}}

test target="": _test-setup (_test target)

test-clean target="": _test-setup-clean (_test target)
