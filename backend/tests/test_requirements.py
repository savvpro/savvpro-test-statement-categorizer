from importlib.metadata import version
from pathlib import Path

REQUIREMENTS = Path(__file__).parents[1] / "requirements.txt"


def test_requirements_match_installed_versions():
    """requirements.txt must describe the env the tests run in, not another Python."""
    for line in REQUIREMENTS.read_text().splitlines():
        name, _, pinned = line.partition("==")
        assert version(name) == pinned, (
            f"{name}: requirements pin {pinned}, installed {version(name)}"
        )
