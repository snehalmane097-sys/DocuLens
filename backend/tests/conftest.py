import pytest

@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv("DOCULENS_DB_PATH", str(tmp_path / "api.sqlite3"))
