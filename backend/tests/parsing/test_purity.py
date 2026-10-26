import subprocess
import sys

import pytest

FORBIDDEN = ("sqlalchemy", "fastapi", "starlette", "app.db", "app.api")


@pytest.mark.parametrize("package", ["app.parsing", "app.brain.engine"])
def test_imports_no_db_or_web_modules(package: str) -> None:
    # A fresh interpreter, so modules imported by other tests do not leak in.
    code = (
        f"import sys, {package}; "
        f"bad = [m for m in sys.modules if m.startswith({FORBIDDEN!r})]; "
        "print(','.join(bad))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == ""
