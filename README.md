# OS2mo SDTool+

OS2mo integration for [SD](https://sd.dk).

## Usage

```sh
podman compose up -d
```

Configuration is done through environment variables. Available options can be
seen in `sdtoolplus/config.py`. Complex variables such as dict or lists can be
given as JSON strings, as specified by Pydantic's settings parser.

## Testing

After starting the project, tests can be run using
[pytest](https://pytest.org), for example:

```sh
podman compose stop sdtool-plus
podman compose run --rm sdtool-plus pytest tests/integration/test_engagement_timeline.py
```

All tests should be runnable both locally and in CI -- it is considered a bug
if not.

## APOS
When running in REGION mode, engagements are placed in the units related to
the SD payroll units according to the strategy implemented in the function
`engagement_ou_strategy_region` in [engagements.py](sdtoolplus/sync/engagement.py).
In order for this to work, the `extension_5` attributes of the MO engagements
(originating from APOS) need to be populated with the UUID of the organization unit
where the engagement is placed in SD, _before_ the engagements are imported to MO
for production. This is done by generating a JSON file with these data to be consumed
by the APOS importer. Generating the JSON file is a two-step process as described
below.

### Step 1
This step is _very_ time-consuming and needs to be performed in multiple
iterations due to the opening ours of the SD API.

1. Extract all engagements directly from the MO database (to save time). This
   can be done by using the SQL query found in
   [all-engagements.sql](scripts/all-engagements.sql). The query will generate
   a CSV file to be used by the Python script in 2).
2. Run the Python script [sd_engagement_json.py](scripts/sd_engagement_json.py)
   from the SD pod (see more optional parameters in the file):
   ```
   $ python -m scripts.sd_engagement_json --username <SD_USERNAME> --password <SD_PASSWORD>
   ```
   This will generate a JSON file in `/tmp/engagements.json` containing the
   `extension_5` data for all the engagements in MO.

### Step 2
Since step 1 is very time-consuming, it is preferable to only do this once
(e.g. a few weeks before the system goes live). Immediately before the final
APOS import is run, the JSON file from step 1 must be updated with the latest
changes from SD. This is done using the script
[update_engagement_placement_cache.py](scripts/update_engagement_placement_cache.py)
(see more optional parameters in the file):
```
$ python -m scripts.update_engagement_placement_cache --username <SD_USERNAME> \
  --password <SD_PASSWORD> \
  --file /tmp/engagements.json \
  --since <DATETIME-WHEN-ENGAGEMENT-JSON-WAS-GENERATED>
```
This will result in the file `/tmp/engagements-patched.json` containing the latest
changed from SD.
