# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import json
import sys

# The logs in Grafane are hard to read - this script parses a Grafana (JSON) log file
# and pretty-print the result.

log_file_name = sys.argv[1]
with open(log_file_name, "r") as fp:
    log_file = json.load(fp)

for obj in log_file:
    line = json.loads(obj["line"])
    print(f"{obj['date']}   {line['event']}")
    print(json.dumps(line, indent=2))
    print(120 * "-")
