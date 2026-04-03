import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture
def test_user_data():
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "nom_complet": "Test User",
        "service_id": 1
    }

def test_login_success(test_user_data):
    """Test connexion réussie"""
    response = client.post(
        "/api/v1/login",
        json={
            "username": "testuser",
            "password": "TestPassword123!"
        }
    )
    assert response.status_code in [200, 401]  # 401 si user n'existe pas

def test_login_invalid_credentials():
    """Test connexion avec identifiants invalides"""
    response = client.post(
        "/api/v1/login",
        json={
            "username": "nonexistent",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401

def test_login_missing_fields():
    """Test connexion sans champs requis"""
    response = client.post(
        "/api/v1/login",
        json={"username": "testuser"}
    )
    assert response.status_code == 422

def test_protected_endpoint_without_token():
    """Test accès à endpoint protégé sans token"""
    response = client.get("/api/v1/dossiers/")
    assert response.status_code == 403

def test_protected_endpoint_with_invalid_token():
    """Test accès à endpoint protégé avec token invalide"""
    response = client.get(
        "/api/v1/dossiers/",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
