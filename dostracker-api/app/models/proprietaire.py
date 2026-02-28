from pydantic import BaseModel, UUID4, Field
from typing import Optional
from datetime import datetime

class ProprietaireBase(BaseModel):
    nom_complet: str
    contact: str = Field(..., description="Numéro de téléphone pour les SMS")

class ProprietaireCreate(ProprietaireBase):
    pass

class ProprietaireUpdate(BaseModel):
    nom_complet: Optional[str] = None
    contact: Optional[str] = None

class Proprietaire(ProprietaireBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
