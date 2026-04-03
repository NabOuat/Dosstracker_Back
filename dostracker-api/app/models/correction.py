from pydantic import BaseModel, UUID4, Field
from typing import Optional
from datetime import datetime

class CorrectionDossierBase(BaseModel):
    dossier_id: UUID4
    agent_transmettant_id: UUID4
    elements_transmis: str = Field(..., min_length=10, description="Description des éléments retournés et corrections demandées")

class CorrectionDossierCreate(CorrectionDossierBase):
    pass

class CorrectionDossierUpdate(BaseModel):
    elements_transmis: Optional[str] = None
    statut: Optional[str] = None  # EN_ATTENTE, RECU, TRAITE

class CorrectionDossier(CorrectionDossierBase):
    id: UUID4
    statut: str
    created_at: datetime
    updated_at: datetime
    
    # Données jointes (non stockées dans la table)
    agent_transmettant_nom: Optional[str] = None
    dossier_numero: Optional[str] = None

    class Config:
        from_attributes = True
