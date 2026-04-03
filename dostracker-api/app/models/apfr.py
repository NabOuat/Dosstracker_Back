from pydantic import BaseModel, UUID4, Field
from typing import Optional, List
from datetime import datetime

class DemandSignatureAPFRBase(BaseModel):
    numero_demande: str = Field(..., min_length=5, description="Numéro unique de la demande")
    agent_spfei_id: UUID4

class DemandSignatureAPFRCreate(DemandSignatureAPFRBase):
    dossier_ids: List[UUID4] = Field(..., min_items=1, description="Liste des dossiers à inclure")

class DemandSignatureAPFRUpdate(BaseModel):
    statut: Optional[str] = None  # EN_ATTENTE, SIGNEE, REJETEE

class DemandSignatureAPFR(DemandSignatureAPFRBase):
    id: UUID4
    statut: str
    date_creation: datetime
    created_at: datetime
    updated_at: datetime
    
    # Données jointes
    agent_spfei_nom: Optional[str] = None
    nombre_dossiers: Optional[int] = None
    dossiers_list: Optional[str] = None  # Liste des numéros de dossiers

    class Config:
        from_attributes = True

class DossierAPFRBase(BaseModel):
    dossier_id: UUID4
    demande_apfr_id: UUID4
    ordre: int = 0

class DossierAPFRCreate(DossierAPFRBase):
    pass

class DossierAPFR(DossierAPFRBase):
    id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True

class RetourConservationBase(BaseModel):
    dossier_id: UUID4
    agent_retour_conservation_id: UUID4
    num_titre_foncier_conservation: str
    superficie_conservation: float
    reference_courier_conservation: str

class RetourConservationCreate(RetourConservationBase):
    pass

class RetourConservationUpdate(BaseModel):
    num_titre_foncier_conservation: Optional[str] = None
    superficie_conservation: Optional[float] = None
    reference_courier_conservation: Optional[str] = None

class RetourConservation(RetourConservationBase):
    date_retour_conservation: datetime
    agent_retour_conservation_nom: Optional[str] = None
    dossier_numero: Optional[str] = None

    class Config:
        from_attributes = True

class AttributionTitreEnrichie(BaseModel):
    date_transmission: str  # Format: YYYY-MM-DD
    reference_courier_dg: str
    conservation: str
    numero_titre_foncier: str
    # PDF stocké via pieces_jointes

class AttributionTitreUpdate(BaseModel):
    date_transmission: Optional[str] = None
    reference_courier_dg: Optional[str] = None
    conservation: Optional[str] = None
    numero_titre_foncier: Optional[str] = None

class PieceJointeBase(BaseModel):
    dossier_id: UUID4
    nom_original: str
    type_fichier: str = 'PDF'

class PieceJointeCreate(PieceJointeBase):
    url_stockage: str

class PieceJointe(PieceJointeBase):
    id: UUID4
    user_id: Optional[UUID4] = None
    service_id: Optional[int] = None
    taille_octets: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
