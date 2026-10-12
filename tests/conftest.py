import pytest

from database import Database
from memory_service import MemoryService


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "journal.sqlite3")


@pytest.fixture
def service(db, tmp_path):
    return MemoryService(db, tmp_path / "media")
