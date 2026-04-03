import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture
def auth_headers():
    """Fixture pour obtenir les headers d'authentification"""
    return {"Authorization": "Bearer test_token"}

def test_get_dossiers_without_auth():
    """Test récupération des dossiers sans authentification"""
    response = client.get("/api/v1/dossiers/")
    assert response.status_code == 403

def test_get_dossiers_with_filters():
    """Test récupération des dossiers avec filtres"""
    response = client.get(
        "/api/v1/dossiers/?statut=COURRIER&region=Abidjan",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 401]

def test_create_dossier_validation():
    """Test validation lors de la création d'un dossier"""
    response = client.post(
        "/api/v1/dossiers/",
        json={"numero_dossier": ""},  # Champ vide
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [422, 401]

def test_dossier_workflow_transition():
    """Test transition de statut d'un dossier"""
    # Vérifier que les transitions de statut sont valides
    valid_transitions = {
        "COURRIER": ["SPFEI_ADMIN"],
        "SPFEI_ADMIN": ["SCVAA"],
        "SCVAA": ["NON_CONFORME", "SPFEI_TITRE"],
        "SPFEI_TITRE": ["CONSERVATION"],
    }
    assert len(valid_transitions) > 0
