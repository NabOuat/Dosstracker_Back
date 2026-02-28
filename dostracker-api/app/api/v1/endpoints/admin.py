from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel

from app.core.deps import get_admin_user
from app.database import get_supabase

router = APIRouter(prefix="/admin", tags=["Administration"])


# ── Modèles ────────────────────────────────────────────────────────────────────

class ReinitialiserDossierRequest(BaseModel):
    nouveau_statut: str
    motif: str

class UpdateServiceRequest(BaseModel):
    libelle: str

class UpdateConfigRequest(BaseModel):
    delai_modification_heures: int

class CreateMotifRequest(BaseModel):
    libelle: str

class TraiterDemandeRequest(BaseModel):
    approuver: bool


# ── Transitions retour autorisées ──────────────────────────────────────────────

TRANSITIONS_RETOUR = {
    "SPFEI_ADMIN":  ["COURRIER"],
    "SCVAA":        ["SPFEI_ADMIN"],
    "NON_CONFORME": ["SCVAA"],
    "SPFEI_TITRE":  ["SCVAA"],
    "CONSERVATION": ["SPFEI_TITRE"],
}

# ── Dossiers : actions admin ───────────────────────────────────────────────────

@router.post("/dossiers/{dossier_id}/reinitialiser")
async def reinitialiser_dossier(
    dossier_id: str,
    data: ReinitialiserDossierRequest,
    current_user: dict = Depends(get_admin_user),
) -> Any:
    """Réinitialise un dossier à un statut antérieur (admin uniquement)"""
    supabase = get_supabase()

    resp = supabase.table("dossiers").select("id, statut, numero_dossier").eq("id", dossier_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    statut_actuel = resp.data[0]["statut"]
    valides = TRANSITIONS_RETOUR.get(statut_actuel, [])
    if data.nouveau_statut not in valides:
        raise HTTPException(
            status_code=400,
            detail=f"Réinitialisation de {statut_actuel} vers {data.nouveau_statut} non autorisée",
        )

    supabase.table("dossiers").update({"statut": data.nouveau_statut}).eq("id", dossier_id).execute()

    supabase.table("workflow_history").insert({
        "dossier_id": dossier_id,
        "user_id": current_user["id"],
        "service_id": current_user["service_id"],
        "ancien_statut": statut_actuel,
        "nouveau_statut": data.nouveau_statut,
        "action": "[ADMIN] Réinitialisation du dossier",
        "details": {"motif": data.motif, "admin": current_user["nom_complet"]},
    }).execute()

    return {"message": "Dossier réinitialisé", "nouveau_statut": data.nouveau_statut}


@router.delete("/dossiers/{dossier_id}")
async def supprimer_dossier(
    dossier_id: str,
    motif: str = Query(..., description="Motif de suppression"),
    current_user: dict = Depends(get_admin_user),
) -> Any:
    """Supprime définitivement un dossier (admin uniquement)"""
    supabase = get_supabase()

    resp = supabase.table("dossiers").select("id, statut, numero_dossier").eq("id", dossier_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    dossier = resp.data[0]

    # Enregistrer l'action avant suppression
    supabase.table("workflow_history").insert({
        "dossier_id": dossier_id,
        "user_id": current_user["id"],
        "service_id": current_user["service_id"],
        "ancien_statut": dossier["statut"],
        "nouveau_statut": "SUPPRIME",
        "action": "[ADMIN] Suppression du dossier",
        "details": {
            "motif": motif,
            "admin": current_user["nom_complet"],
            "numero_dossier": dossier["numero_dossier"],
        },
    }).execute()

    supabase.table("dossiers").delete().eq("id", dossier_id).execute()

    return {"message": f"Dossier {dossier['numero_dossier']} supprimé"}


# ── Journal d'activité ─────────────────────────────────────────────────────────

@router.get("/journal")
async def get_journal(
    skip: int = 0,
    limit: int = 30,
    user_id: Optional[str] = None,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    current_user: dict = Depends(get_admin_user),
) -> Any:
    """Journal d'activité : historique du workflow (admin uniquement)"""
    supabase = get_supabase()

    query = supabase.table("workflow_history").select(
        "id, dossier_id, ancien_statut, nouveau_statut, action, details, created_at, "
        "users(nom_complet, username), services(libelle), dossiers(numero_dossier)"
    )

    if user_id:
        query = query.eq("user_id", user_id)
    if date_debut:
        query = query.gte("created_at", date_debut)
    if date_fin:
        query = query.lte("created_at", date_fin + "T23:59:59")

    response = query.order("created_at", desc=True).range(skip, skip + limit - 1).execute()
    return response.data or []


# ── Statistiques par agent ─────────────────────────────────────────────────────

@router.get("/stats/agents")
async def get_agent_stats(
    current_user: dict = Depends(get_admin_user),
) -> Any:
    """Statistiques de productivité par agent (admin uniquement)"""
    supabase = get_supabase()

    users_resp = supabase.table("users").select(
        "id, nom_complet, username, service_id, is_active, last_login, services(libelle)"
    ).execute()

    wh_resp = supabase.table("workflow_history").select("user_id, created_at").execute()

    # Agréger par user_id en Python
    actions_by_user: dict = {}
    for row in (wh_resp.data or []):
        uid = row["user_id"]
        if uid not in actions_by_user:
            actions_by_user[uid] = {"count": 0, "derniere": None}
        actions_by_user[uid]["count"] += 1
        ts = row["created_at"]
        if actions_by_user[uid]["derniere"] is None or ts > actions_by_user[uid]["derniere"]:
            actions_by_user[uid]["derniere"] = ts

    agents = []
    for u in (users_resp.data or []):
        uid = str(u["id"])
        ag = actions_by_user.get(uid, {"count": 0, "derniere": None})
        service_libelle = "–"
        if isinstance(u.get("services"), dict):
            service_libelle = u["services"].get("libelle", "–")
        agents.append({
            "id": uid,
            "nom_complet": u["nom_complet"],
            "username": u["username"],
            "service_id": u["service_id"],
            "service": service_libelle,
            "is_active": u["is_active"],
            "last_login": u["last_login"],
            "nb_actions": ag["count"],
            "derniere_action": ag["derniere"],
        })

    # Statistiques globales
    dossiers_resp = supabase.table("dossiers").select("id, statut").execute()
    par_statut: dict = {}
    for d in (dossiers_resp.data or []):
        s = d["statut"]
        par_statut[s] = par_statut.get(s, 0) + 1

    return {
        "agents": agents,
        "global": {
            "total_dossiers": len(dossiers_resp.data or []),
            "par_statut": par_statut,
        },
    }


# ── Services ───────────────────────────────────────────────────────────────────

@router.get("/services")
async def get_services(current_user: dict = Depends(get_admin_user)) -> Any:
    """Liste les services (admin uniquement)"""
    supabase = get_supabase()
    return supabase.table("services").select("*").order("id").execute().data or []


@router.put("/services/{service_id}")
async def update_service(
    service_id: int,
    data: UpdateServiceRequest,
    current_user: dict = Depends(get_admin_user),
) -> Any:
    """Met à jour le libellé d'un service (admin uniquement)"""
    supabase = get_supabase()
    resp = supabase.table("services").update({"libelle": data.libelle}).eq("id", service_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Service non trouvé")
    return resp.data[0]


# ── Configuration système ──────────────────────────────────────────────────────

DEFAULT_CONFIG = {"delai_modification_heures": 24}


@router.get("/config")
async def get_config(current_user: dict = Depends(get_admin_user)) -> Any:
    """Récupère la configuration système (admin uniquement)"""
    supabase = get_supabase()
    try:
        resp = supabase.table("system_config").select("*").execute()
        cfg = dict(DEFAULT_CONFIG)
        for item in (resp.data or []):
            val = item.get("value", "")
            cfg[item["key"]] = int(val) if str(val).isdigit() else val
        return cfg
    except Exception:
        return DEFAULT_CONFIG


@router.put("/config")
async def update_config(
    data: UpdateConfigRequest,
    current_user: dict = Depends(get_admin_user),
) -> Any:
    """Met à jour la configuration système (admin uniquement)"""
    supabase = get_supabase()
    try:
        supabase.table("system_config").upsert({
            "key": "delai_modification_heures",
            "value": str(data.delai_modification_heures),
        }).execute()
        return {"message": "Configuration mise à jour", **data.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Motifs de non-conformité ───────────────────────────────────────────────────

DEFAULT_MOTIFS = [
    {"id": "default-1", "libelle": "Limites non bornées"},
    {"id": "default-2", "libelle": "Plan cadastral incomplet"},
    {"id": "default-3", "libelle": "Documents manquants"},
    {"id": "default-4", "libelle": "Surface non conforme"},
    {"id": "default-5", "libelle": "Chevauchement de parcelles"},
]


@router.get("/motifs")
async def get_motifs(current_user: dict = Depends(get_admin_user)) -> Any:
    """Liste les motifs de non-conformité (admin uniquement)"""
    supabase = get_supabase()
    try:
        resp = supabase.table("motifs_nonconformite").select("*").order("libelle").execute()
        return resp.data if resp.data is not None else DEFAULT_MOTIFS
    except Exception:
        return DEFAULT_MOTIFS


@router.post("/motifs")
async def create_motif(
    data: CreateMotifRequest,
    current_user: dict = Depends(get_admin_user),
) -> Any:
    """Crée un motif de non-conformité (admin uniquement)"""
    supabase = get_supabase()
    try:
        resp = supabase.table("motifs_nonconformite").insert({"libelle": data.libelle}).execute()
        if not resp.data:
            raise HTTPException(status_code=400, detail="Erreur lors de la création")
        return resp.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/motifs/{motif_id}")
async def delete_motif(
    motif_id: str,
    current_user: dict = Depends(get_admin_user),
) -> Any:
    """Supprime un motif de non-conformité (admin uniquement)"""
    supabase = get_supabase()
    try:
        supabase.table("motifs_nonconformite").delete().eq("id", motif_id).execute()
        return {"message": "Motif supprimé"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Demandes de droits de modification ─────────────────────────────────────────

@router.get("/demandes-droits")
async def get_demandes_droits(
    current_user: dict = Depends(get_admin_user),
) -> Any:
    """Liste les demandes de droits de modification en attente (admin uniquement)"""
    supabase = get_supabase()
    try:
        resp = supabase.table("demandes_droits").select(
            "*, users(nom_complet, username), dossiers(numero_dossier)"
        ).order("created_at", desc=True).execute()
        return resp.data or []
    except Exception:
        return []


@router.post("/demandes-droits/{demande_id}/traiter")
async def traiter_demande_droits(
    demande_id: str,
    data: TraiterDemandeRequest,
    current_user: dict = Depends(get_admin_user),
) -> Any:
    """Approuve ou rejette une demande de droits de modification (admin uniquement)"""
    supabase = get_supabase()
    try:
        demande = supabase.table("demandes_droits").select("id, dossier_id, statut").eq("id", demande_id).execute()
        if not demande.data:
            raise HTTPException(status_code=404, detail="Demande non trouvée")
        if demande.data[0]["statut"] != "EN_ATTENTE":
            raise HTTPException(status_code=400, detail="Cette demande a déjà été traitée")

        nouveau_statut = "APPROUVE" if data.approuver else "REJETE"
        supabase.table("demandes_droits").update({
            "statut": nouveau_statut,
            "traite_par_id": current_user["id"],
        }).eq("id", demande_id).execute()

        return {"message": f"Demande {nouveau_statut.lower()}", "statut": nouveau_statut}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
