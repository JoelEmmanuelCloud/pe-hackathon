import os
import pytest
from peewee import SqliteDatabase

TEST_DB = SqliteDatabase(":memory:")

os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")


@pytest.fixture(scope="session")
def app():
    from app.database import database_proxy
    from app.models.user import User
    from app.models.url import Url
    from app.models.event import Event

    database_proxy.initialize(TEST_DB)
    TEST_DB.connect()
    TEST_DB.create_tables([User, Url, Event])

    from app import create_app
    flask_app = create_app(db=TEST_DB)
    flask_app.config["TESTING"] = True
    yield flask_app

    TEST_DB.drop_tables([User, Url, Event])
    TEST_DB.close()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    from app.models.user import User
    from app.models.url import Url
    from app.models.event import Event
    if TEST_DB.is_closed():
        TEST_DB.connect()
    yield
    if TEST_DB.is_closed():
        TEST_DB.connect()
    Event.delete().execute()
    Url.delete().execute()
    User.delete().execute()


@pytest.fixture
def sample_user():
    from app.models.user import User
    return User.create(username="testuser", email="test@example.com")


@pytest.fixture
def sample_url(sample_user):
    from app.models.url import Url
    return Url.create(
        user=sample_user,
        short_code="test01",
        original_url="https://example.com",
        title="Test URL",
        is_active=True,
    )
