import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models import *  # noqa: F401,F403


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_register_and_login_flow(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "new.patient@test.com", "password": "Password@123", "full_name": "New Patient"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "PATIENT"

    login_resp = client.post(
        "/api/v1/auth/login", json={"email": "new.patient@test.com", "password": "Password@123"}
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_duplicate_registration_returns_409(client):
    payload = {"email": "dup@test.com", "password": "Password@123", "full_name": "Dup"}
    client.post("/api/v1/auth/register", json=payload)
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "CONFLICT"


def test_wrong_password_returns_401(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpw@test.com", "password": "Password@123", "full_name": "Test"},
    )
    resp = client.post("/api/v1/auth/login", json={"email": "wrongpw@test.com", "password": "WrongPass1"})
    assert resp.status_code == 401


def test_patient_cannot_access_admin_endpoint(client):
    register_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "patientrole@test.com", "password": "Password@123", "full_name": "Test"},
    )
    token = register_resp.json()["access_token"]
    resp = client.post(
        "/api/v1/admin/doctors",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "d@test.com", "password": "x", "full_name": "Dr X"},
    )
    assert resp.status_code == 403


def test_missing_token_returns_401(client):
    resp = client.get("/api/v1/appointments")
    assert resp.status_code == 401
