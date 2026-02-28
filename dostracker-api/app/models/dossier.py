from pydantic import BaseModel, UUID4, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from .enums import StatutDossier, Conformite, Genre

class DossierBase(BaseModel):
    # SERVICE COURRIER
    numero_dossier: str
    date_enregistrement: date
    region: str
    prefecture: Optional[str] = None
    sous_prefecture: Optional[str] = None
    village: Optional[str] = None
    departement: Optional[str] = None
    numero_cf: Optional[str] = None
    proprietaire_id: Optional[UUID4] = None

class DossierCreate(DossierBase):
    pass

class DossierUpdate(BaseModel):
    # SERVICE COURRIER
    prefecture: Optional[str] = None
    sous_prefecture: Optional[str] = None
    village: Optional[str] = None
    departement: Optional[str] = None
    numero_cf: Optional[str] = None
    
    # SERVICE SPFEI (Admin)
    nationalite: Optional[str] = None
    genre: Optional[Genre] = None
    type_cf: Optional[str] = None
    date_enquete_officielle: Optional[date] = None
    date_valid_enq: Optional[date] = None
    date_etab_cf: Optional[date] = None
    date_demande_immat: Optional[date] = None
    
    # SERVICE SCVAA
    superficie_ha: Optional[float] = None
    date_bornage: Optional[date] = None
    geometre_expert: Optional[str] = None
    contact_geometre: Optional[str] = None
    decision_conformite: Optional[Conformite] = None
    motifs_inconformite: Optional[List[str]] = None
    autre_motif: Optional[str] = None
    
    # SERVICE SPFEI (Titre)
    conservation: Optional[str] = None
    numero_titre_foncier: Optional[str] = None
    
    # Statut
    statut: Optional[StatutDossier] = None

class DossierSPFEIAdmin(BaseModel):
    nationalite: Optional[str] = None
    genre: Optional[Genre] = None
    type_cf: Optional[str] = None
    date_enquete_officielle: Optional[date] = None
    date_valid_enq: Optional[date] = None
    date_etab_cf: Optional[date] = None
    date_demande_immat: Optional[date] = None

class DossierSCVAA(BaseModel):
    superficie_ha: float
    date_bornage: Optional[date] = None
    geometre_expert: Optional[str] = None
    contact_geometre: Optional[str] = None
    decision_conformite: Conformite
    motifs_inconformite: Optional[List[str]] = None
    autre_motif: Optional[str] = None

class DossierSPFEITitre(BaseModel):
    conservation: str
    numero_titre_foncier: str

class DossierEnvoi(BaseModel):
    dossier_id: UUID4
    destination: StatutDossier

class Dossier(DossierBase):
    id: UUID4
    
    # SERVICE COURRIER
    agent_courrier_id: Optional[UUID4] = None
    date_envoi_spfei: Optional[datetime] = None
    
    # SERVICE SPFEI (Admin)
    nationalite: Optional[str] = None
    genre: Optional[Genre] = None
    type_cf: Optional[str] = None
    date_enquete_officielle: Optional[date] = None
    date_valid_enq: Optional[date] = None
    date_etab_cf: Optional[date] = None
    date_demande_immat: Optional[date] = None
    agent_spfei_admin_id: Optional[UUID4] = None
    date_envoi_scvaa: Optional[datetime] = None
    
    # SERVICE SCVAA
    superficie_ha: Optional[float] = None
    date_bornage: Optional[date] = None
    geometre_expert: Optional[str] = None
    contact_geometre: Optional[str] = None
    decision_conformite: Optional[Conformite] = None
    motifs_inconformite: Optional[List[str]] = None
    autre_motif: Optional[str] = None
    agent_scvaa_id: Optional[UUID4] = None
    date_decision_scvaa: Optional[datetime] = None
    
    # SERVICE SPFEI (Titre)
    conservation: Optional[str] = None
    numero_titre_foncier: Optional[str] = None
    agent_spfei_titre_id: Optional[UUID4] = None
    date_attribution_titre: Optional[datetime] = None
    date_envoi_conservation: Optional[datetime] = None
    
    # Metadata
    statut: StatutDossier
    created_at: datetime
    updated_at: datetime
    
    # Données jointes (non stockées dans la table dossiers)
    demandeur: Optional[str] = None
    contact_demandeur: Optional[str] = None
    agent_courrier: Optional[str] = None
    agent_spfei_admin: Optional[str] = None
    agent_scvaa: Optional[str] = None
    agent_spfei_titre: Optional[str] = None

    class Config:
        from_attributes = True

class DossierDetail(Dossier):
    commentaires: Optional[List[Dict[str, Any]]] = None
    pieces_jointes: Optional[List[Dict[str, Any]]] = None
    historique: Optional[List[Dict[str, Any]]] = None
