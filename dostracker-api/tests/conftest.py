import pytest
from fastapi.testclient import TestClient
from main import app
import os

@pytest.fixture(scope="session")
def test_client():
    """Client de test pour l'API"""
    return TestClient(app)

@pytest.fixture
def auth_token():
    """Token JWT de test"""
    return "test_token_placeholder"

@pytest.fixture
def test_dossier_data():
    """Données de test pour un dossier"""
    return {
        "numero_dossier": "DOS-2024-001",
        "region": "Abidjan",
        "prefecture": "Abidjan",
        "sous_prefecture": "Abobo",
        "village": "Test Village",
        "numero_cf": "CF-001",
        "superficie": 1000.5,
        "proprietaire_id": "test-proprietaire-id"
    }

@pytest.fixture
def test_user_data():
    """Données de test pour un utilisateur"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "nom_complet": "Test User",
        "service_id": 1
    }

@pytest.fixture
def test_proprietaire_data():
    """Données de test pour un propriétaire"""
    return {
        "nom_complet": "Jean Dupont",
        "telephone": "+225 01 23 45 67 89",
        "email": "jean@example.com",
        "genre": "Masculin"
    }

@pytest.fixture(autouse=True)
def reset_env():
    """Réinitialiser les variables d'environnement pour chaque test"""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)
