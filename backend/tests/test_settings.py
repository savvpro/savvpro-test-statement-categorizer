import pytest

from app.core.settings import Settings


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    # conftest points DATABASE_URL at a temp database for the whole test run
    for name in ("DATABASE_URL", "CORS_ORIGINS", "MAX_UPLOAD_MB"):
        monkeypatch.delenv(name, raising=False)
    s = Settings(_env_file=None)
    assert s.database_url == "sqlite:///./data/app.db"
    assert s.cors_origin_list == ["http://localhost:5173"]
    assert s.max_upload_mb == 5
    assert s.max_upload_bytes == 5 * 1024 * 1024


def test_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./other.db")
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test ,")
    monkeypatch.setenv("MAX_UPLOAD_MB", "2")
    s = Settings(_env_file=None)
    assert s.database_url == "sqlite:///./other.db"
    assert s.cors_origin_list == ["http://a.test", "http://b.test"]
    assert s.max_upload_bytes == 2 * 1024 * 1024


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_invalid_upload_limit_rejected(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("MAX_UPLOAD_MB", value)
    with pytest.raises(ValueError):
        Settings(_env_file=None)
