from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Any, Optional
from datetime import datetime, timezone, date
from pydantic import BaseModel

from app.core.deps import get_current_active_user, get_courrier_user, get_spfei_user, get_scvaa_user
from app.database import get_supabase
from app.models.dossier import (
    Dossier, DossierCreate, DossierDetail,
    DossierSPFEIAdmin, DossierSCVAA, DossierSPFEITitre
)
from app.models.enums import StatutDossier

router = APIRouter(prefix="/dossiers", tags=["Dossiers"])


# ── Modèles locaux ─────────────────────────────────────────────────────────────

class EnvoyerRequest(BaseModel):
    destination: StatutDossier

class DossierCourrierUpdate(BaseModel):
    region: Optional[str] = None
    prefecture: Optional[str] = None
    sous_prefecture: Optional[str] = None
    village: Optional[str] = None
    numero_cf: Optional[str] = None

class DemandeDroitsRequest(BaseModel):
    motif: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_delai_heures(supabase) -> int:
    """Récupère le délai de modification configuré (en heures, défaut 24)."""
    try:
        resp = supabase.table("system_config").select("value").eq("key", "delai_modification_heures").execute()
        if resp.data:
            return int(resp.data[0]["value"])
    except Exception:
        pass
    return 24


def _is_modifiable(supabase, dossier_id: str, created_at_str: str) -> bool:
    """Vérifie si un dossier est encore dans le délai de modification."""
    delai_heures = _get_delai_heures(supabase)
    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
    if age_hours <= delai_heures:
        return True
    # Vérifier si une autorisation admin a été accordée
    try:
        auth = supabase.table("demandes_droits").select("id").eq("dossier_id", dossier_id).eq("statut", "APPROUVE").execute()
        if auth.data:
            return True
    except Exception:
        pass
    return False


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[Dossier])
async def read_dossiers(
    skip: int = 0,
    limit: int = 100,
    statut: Optional[str] = Query(None, description="Filtrer par statut"),
    region: Optional[str] = Query(None, description="Filtrer par région"),
    search: Optional[str] = Query(None, description="Recherche par numéro de dossier"),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """Récupère tous les dossiers avec filtres optionnels"""
    supabase = get_supabase()
    query = supabase.table("v_dossiers").select("*")

    if statut:
        query = query.eq("statut", statut)
    if region:
        query = query.eq("region", region)
    if search:
        query = query.ilike("numero_dossier", f"%{search}%")

    service_id = current_user["service_id"]
    if service_id == 1:      # SERVICE_COURRIER
        query = query.eq("statut", "COURRIER")
    elif service_id == 2:    # SERVICE_SPFEI
        query = query.in_("statut", ["SPFEI_ADMIN", "SPFEI_TITRE"])
    elif service_id == 3:    # SERVICE_SCVAA
        query = query.in_("statut", ["SCVAA", "NON_CONFORME"])
    # Admins (service_id == 4) voient tout

    query = query.range(skip, skip + limit - 1).order("created_at", desc=True)
    response = query.execute()
    return response.data


@router.post("/", response_model=Dossier)
async def create_dossier(
    dossier_in: DossierCreate,
    current_user: dict = Depends(get_courrier_user)
) -> Any:
    """Crée un nouveau dossier (SERVICE COURRIER uniquement)"""
    supabase = get_supabase()

    existing = supabase.table("dossiers").select("id").eq("numero_dossier", dossier_in.numero_dossier).execute()
    if existing.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Un dossier avec ce numéro existe déjà")

    proprietaire = supabase.table("proprietaires").select("id").eq("id", dossier_in.proprietaire_id).execute()
    if not proprietaire.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Propriétaire non trouvé")

    dossier_data = dossier_in.model_dump()
    dossier_data["agent_courrier_id"] = current_user["id"]
    dossier_data["statut"] = "COURRIER"
    
    # Convertir les dates en chaînes pour la sérialisation JSON
    if isinstance(dossier_data.get("date_enregistrement"), date):
        dossier_data["date_enregistrement"] = dossier_data["date_enregistrement"].isoformat()
    
    # Convertir les UUIDs en chaînes pour la sérialisation JSON
    if dossier_data.get("proprietaire_id"):
        dossier_data["proprietaire_id"] = str(dossier_data["proprietaire_id"])

    response = supabase.table("dossiers").insert(dossier_data).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erreur lors de la création du dossier")

    supabase.table("workflow_history").insert({
        "dossier_id": response.data[0]["id"],
        "user_id": current_user["id"],
        "service_id": current_user["service_id"],
        "nouveau_statut": "COURRIER",
        "action": "Création du dossier",
    }).execute()

    created = supabase.table("v_dossiers").select("*").eq("id", response.data[0]["id"]).execute()
    return created.data[0] if created.data else response.data[0]


@router.get("/{dossier_id}/modifiable")
async def check_modifiable(
    dossier_id: str,
    current_user: dict = Depends(get_courrier_user)
) -> Any:
    """Vérifie si un dossier est encore modifiable par le service Courrier"""
    supabase = get_supabase()
    dossier = supabase.table("dossiers").select("id, statut, created_at").eq("id", dossier_id).execute()
    if not dossier.data:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")
    d = dossier.data[0]
    if d["statut"] != "COURRIER":
        return {"modifiable": False}
    return {"modifiable": _is_modifiable(supabase, dossier_id, d["created_at"])}


@router.put("/{dossier_id}/courrier")
async def update_courrier_dossier(
    dossier_id: str,
    data: DossierCourrierUpdate,
    current_user: dict = Depends(get_courrier_user)
) -> Any:
    """Met à jour les champs de base d'un dossier Courrier"""
    supabase = get_supabase()
    dossier = supabase.table("dossiers").select("id, statut, created_at").eq("id", dossier_id).execute()
    if not dossier.data:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")
    if dossier.data[0]["statut"] != "COURRIER":
        raise HTTPException(status_code=400, detail="Ce dossier ne peut plus être modifié")

    if not _is_modifiable(supabase, dossier_id, dossier.data[0]["created_at"]):
        raise HTTPException(status_code=403, detail="Délai de modification expiré")

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        supabase.table("dossiers").update(update_data).eq("id", dossier_id).execute()

    updated = supabase.table("v_dossiers").select("*").eq("id", dossier_id).execute()
    return updated.data[0]


@router.post("/{dossier_id}/demande-droits")
async def demander_droits(
    dossier_id: str,
    data: DemandeDroitsRequest,
    current_user: dict = Depends(get_courrier_user)
) -> Any:
    """Soumet une demande de droits de modification spéciaux (service Courrier)"""
    supabase = get_supabase()
    dossier = supabase.table("dossiers").select("id").eq("id", dossier_id).execute()
    if not dossier.data:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")
    try:
        resp = supabase.table("demandes_droits").insert({
            "dossier_id": dossier_id,
            "user_id": current_user["id"],
            "motif": data.motif,
            "statut": "EN_ATTENTE",
        }).execute()
        return resp.data[0] if resp.data else {"message": "Demande enregistrée"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dossier_id}", response_model=DossierDetail)
async def read_dossier(
    dossier_id: str,
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """Récupère un dossier par son ID avec tous les détails"""
    supabase = get_supabase()

    dossier = supabase.table("v_dossiers").select("*").eq("id", dossier_id).execute()
    if not dossier.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier non trouvé")

    commentaires = supabase.table("commentaires").select(
        "id, contenu, est_important, created_at, users(nom_complet), services(libelle)"
    ).eq("dossier_id", dossier_id).order("created_at", desc=True).execute()

    pieces_jointes = supabase.table("pieces_jointes").select(
        "id, nom_original, url_stockage, type_fichier, taille_octets, created_at, users(nom_complet)"
    ).eq("dossier_id", dossier_id).order("created_at", desc=True).execute()

    historique = supabase.table("workflow_history").select(
        "id, ancien_statut, nouveau_statut, action, details, created_at, users(nom_complet), services(libelle)"
    ).eq("dossier_id", dossier_id).order("created_at", desc=True).execute()

    result = dossier.data[0]
    result["commentaires"] = commentaires.data or []
    result["pieces_jointes"] = pieces_jointes.data or []
    result["historique"] = historique.data or []
    return result


@router.put("/{dossier_id}/spfei-admin", response_model=Dossier)
async def update_spfei_admin(
    dossier_id: str,
    dossier_in: DossierSPFEIAdmin,
    current_user: dict = Depends(get_spfei_user)
) -> Any:
    """Met à jour les informations administratives et transmet au SCVAA (SERVICE SPFEI)"""
    supabase = get_supabase()

    dossier = supabase.table("dossiers").select("*").eq("id", dossier_id).eq("statut", "SPFEI_ADMIN").execute()
    if not dossier.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier non trouvé ou non au statut SPFEI_ADMIN")

    update_data = dossier_in.model_dump()
    update_data["agent_spfei_admin_id"] = current_user["id"]
    update_data["statut"] = "SCVAA"
    update_data["date_envoi_scvaa"] = datetime.now(timezone.utc).isoformat()

    response = supabase.table("dossiers").update(update_data).eq("id", dossier_id).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erreur lors de la mise à jour du dossier")

    supabase.table("workflow_history").insert({
        "dossier_id": dossier_id,
        "user_id": current_user["id"],
        "service_id": current_user["service_id"],
        "ancien_statut": "SPFEI_ADMIN",
        "nouveau_statut": "SCVAA",
        "action": "Contrôle administratif effectué — dossier transmis au SCVAA",
    }).execute()

    updated = supabase.table("v_dossiers").select("*").eq("id", dossier_id).execute()
    return updated.data[0] if updated.data else response.data[0]


@router.put("/{dossier_id}/scvaa", response_model=Dossier)
async def update_scvaa(
    dossier_id: str,
    dossier_in: DossierSCVAA,
    current_user: dict = Depends(get_scvaa_user)
) -> Any:
    """Met à jour les informations techniques d'un dossier (SERVICE SCVAA)"""
    supabase = get_supabase()

    dossier = supabase.table("dossiers").select("*").eq("id", dossier_id).eq("statut", "SCVAA").execute()
    if not dossier.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier non trouvé ou non au statut SCVAA")

    update_data = dossier_in.model_dump()
    update_data["agent_scvaa_id"] = current_user["id"]
    update_data["date_decision_scvaa"] = datetime.now(timezone.utc).isoformat()

    nouveau_statut = "NON_CONFORME" if dossier_in.decision_conformite == "NON_CONFORME" else "SPFEI_TITRE"
    update_data["statut"] = nouveau_statut

    response = supabase.table("dossiers").update(update_data).eq("id", dossier_id).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erreur lors de la mise à jour du dossier")

    supabase.table("workflow_history").insert({
        "dossier_id": dossier_id,
        "user_id": current_user["id"],
        "service_id": current_user["service_id"],
        "ancien_statut": "SCVAA",
        "nouveau_statut": nouveau_statut,
        "action": f"Décision SCVAA: {dossier_in.decision_conformite}",
        "details": {"decision": dossier_in.decision_conformite, "motifs": dossier_in.motifs_inconformite},
    }).execute()

    if nouveau_statut == "NON_CONFORME":
        dossier_info = supabase.table("v_dossiers").select("*").eq("id", dossier_id).execute()
        if dossier_info.data:
            d = dossier_info.data[0]
            motifs_str = ", ".join(dossier_in.motifs_inconformite) if dossier_in.motifs_inconformite else ""
            if dossier_in.autre_motif:
                motifs_str += f", {dossier_in.autre_motif}" if motifs_str else dossier_in.autre_motif
            supabase.table("sms_log").insert({
                "dossier_id": dossier_id,
                "proprietaire_id": d["proprietaire_id"],
                "type_sms": "NON_CONFORMITE",
                "numero_destinataire": d["contact_demandeur"],
                "contenu_message": f"Dossier N° {d['numero_dossier']} : NON CONFORME. Motifs : {motifs_str}.",
                "statut": "SIMULE",
                "envoye_par_id": current_user["id"],
            }).execute()

    updated = supabase.table("v_dossiers").select("*").eq("id", dossier_id).execute()
    return updated.data[0] if updated.data else response.data[0]


@router.put("/{dossier_id}/spfei-titre", response_model=Dossier)
async def update_spfei_titre(
    dossier_id: str,
    dossier_in: DossierSPFEITitre,
    current_user: dict = Depends(get_spfei_user)
) -> Any:
    """Attribue un titre foncier et transmet à la Conservation (SERVICE SPFEI)"""
    supabase = get_supabase()

    dossier = supabase.table("dossiers").select("*").eq("id", dossier_id).eq("statut", "SPFEI_TITRE").execute()
    if not dossier.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier non trouvé ou non au statut SPFEI_TITRE")

    update_data = dossier_in.model_dump()
    update_data["agent_spfei_titre_id"] = current_user["id"]
    update_data["date_attribution_titre"] = datetime.now(timezone.utc).isoformat()
    update_data["statut"] = "CONSERVATION"
    update_data["date_envoi_conservation"] = datetime.now(timezone.utc).isoformat()

    response = supabase.table("dossiers").update(update_data).eq("id", dossier_id).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erreur lors de la mise à jour du dossier")

    supabase.table("workflow_history").insert({
        "dossier_id": dossier_id,
        "user_id": current_user["id"],
        "service_id": current_user["service_id"],
        "ancien_statut": "SPFEI_TITRE",
        "nouveau_statut": "CONSERVATION",
        "action": "Titre foncier attribué — dossier envoyé à la Conservation Foncière",
    }).execute()

    dossier_info = supabase.table("v_dossiers").select("*").eq("id", dossier_id).execute()
    if dossier_info.data:
        d = dossier_info.data[0]
        supabase.table("sms_log").insert({
            "dossier_id": dossier_id,
            "proprietaire_id": d["proprietaire_id"],
            "type_sms": "FINALISATION",
            "numero_destinataire": d["contact_demandeur"],
            "contenu_message": f"Dossier N° {d['numero_dossier']} : finalisé avec succès. Titre Foncier N° {dossier_in.numero_titre_foncier}.",
            "statut": "SIMULE",
            "envoye_par_id": current_user["id"],
        }).execute()

    updated = supabase.table("v_dossiers").select("*").eq("id", dossier_id).execute()
    return updated.data[0] if updated.data else response.data[0]


@router.post("/{dossier_id}/envoyer", response_model=Dossier)
async def envoyer_dossier(
    dossier_id: str,
    data: EnvoyerRequest,
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """Envoie un dossier au service suivant dans le workflow"""
    supabase = get_supabase()
    destination = data.destination

    dossier = supabase.table("dossiers").select("*").eq("id", dossier_id).execute()
    if not dossier.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier non trouvé")

    dossier_data = dossier.data[0]
    statut_actuel = dossier_data["statut"]
    service_id = current_user["service_id"]

    transitions_autorisees = {
        "COURRIER": ["SPFEI_ADMIN"],
        "SPFEI_ADMIN": ["SCVAA"],
        "SPFEI_TITRE": ["CONSERVATION"],
        "NON_CONFORME": ["SCVAA"],
    }

    if statut_actuel not in transitions_autorisees or destination not in transitions_autorisees[statut_actuel]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Transition non autorisée de {statut_actuel} vers {destination}")

    if (service_id == 1 and statut_actuel != "COURRIER") or \
       (service_id == 2 and statut_actuel not in ["SPFEI_ADMIN", "SPFEI_TITRE"]) or \
       (service_id == 3 and statut_actuel not in ["SCVAA", "NON_CONFORME"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits pour effectuer cette action")

    update_data = {"statut": destination}
    now = datetime.now(timezone.utc).isoformat()
    if statut_actuel == "COURRIER" and destination == "SPFEI_ADMIN":
        update_data["date_envoi_spfei"] = now
    elif statut_actuel == "SPFEI_ADMIN" and destination == "SCVAA":
        update_data["date_envoi_scvaa"] = now
    elif statut_actuel == "SPFEI_TITRE" and destination == "CONSERVATION":
        update_data["date_envoi_conservation"] = now

    response = supabase.table("dossiers").update(update_data).eq("id", dossier_id).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erreur lors de l'envoi du dossier")

    supabase.table("workflow_history").insert({
        "dossier_id": dossier_id,
        "user_id": current_user["id"],
        "service_id": service_id,
        "ancien_statut": statut_actuel,
        "nouveau_statut": destination,
        "action": f"Dossier envoyé de {statut_actuel} vers {destination}",
    }).execute()

    updated = supabase.table("v_dossiers").select("*").eq("id", dossier_id).execute()
    return updated.data[0] if updated.data else response.data[0]
