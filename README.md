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
podman compose run sdtool-plus pytest tests/integration/test_engagement_timeline.py
```

All tests should be runnable both locally and in CI -- it is considered a bug
if not.
