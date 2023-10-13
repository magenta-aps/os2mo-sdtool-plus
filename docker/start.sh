#!/bin/bash
# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
set -o nounset
set -o errexit
set -o pipefail

# Run app
uvicorn --factory sdtoolplus.fastapi:create_app --host 0.0.0.0
