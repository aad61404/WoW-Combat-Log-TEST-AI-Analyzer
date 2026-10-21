"""Keep test startup away from developer databases and external credentials."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir

_test_directory: TemporaryDirectory | None = None
_previous_environment: dict[str, str | None] = {}


def pytest_configure():
    # This hook runs before collection imports app.config and the global engine.
    global _test_directory
    _test_directory = TemporaryDirectory(prefix="wow-analyzer-tests-")
    database_path = (Path(_test_directory.name) / "startup.db").as_posix()
    overrides = {
        "DATABASE_URL": f"sqlite+aiosqlite:///{database_path}",
        "WCL_CLIENT_ID": "",
        "WCL_CLIENT_SECRET": "",
        "GEMINI_API_KEY": "",
    }
    for key, value in overrides.items():
        _previous_environment[key] = os.environ.get(key)
        os.environ[key] = value


def pytest_unconfigure():
    for key, value in _previous_environment.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    if _test_directory is not None:
        target = Path(_test_directory.name).resolve()
        # Only clean the exact temporary directory allocated for this test run.
        if target.parent == Path(gettempdir()).resolve() and target.name.startswith(
            "wow-analyzer-tests-"
        ):
            _test_directory.cleanup()
