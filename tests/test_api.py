import io
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_certificates_returns_zip(client):
    response = client.post(
        "/certificates/generate",
        files={"csv_file": ("recipients.csv", b"name,course\nAda Lovelace,Python\n")},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["x-recipient-count"] == "1"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.namelist() == ["0001_Ada_Lovelace.pdf"]
        assert archive.read(archive.namelist()[0]).startswith(b"%PDF-")


def test_generate_certificates_rejects_missing_name_column(client):
    response = client.post(
        "/certificates/generate",
        files={"csv_file": ("recipients.csv", b"email\na@example.com\n")},
    )

    assert response.status_code == 422
    assert "name" in response.json()["detail"]