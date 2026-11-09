from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from app.core.deps import get_current_active_user
from app.database import get_supabase

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# Statuts pertinents par service
_SERVICE_STATUTS = {
    1: ["COURRIER"],
    2: ["SPFEI_ADMIN", "SPFEI_TITRE"],
    3: ["SCVAA", "NON_CONFORME"],
    4: None,  # Admin voit tout
}

_STATUT_TYPE = {
    "NON_CONFORME": "warning",
    "CONSERVATION": "success",
}


@router.get("/", response_model=List[Dict[str, Any]])
async def get_notifications(
    current_user: dict = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """Retourne les 10 derniers événements du workflow pertinents pour l'utilisateur connecté."""
    supabase = get_supabase()
    service_id = current_user.get("service_id")
    statuts = _SERVICE_STATUTS.get(service_id)

    query = (
        supabase.table("workflow_history")
        .select("id, action, nouveau_statut, created_at, dossier_id")
        .order("created_at", desc=True)
        .limit(20)
    )
    if statuts:
        query = query.in_("nouveau_statut", statuts)

    resp = query.execute()
    history = resp.data or []

    # Récupérer les numéros de dossier en batch
    dossier_ids = list({h["dossier_id"] for h in history if h.get("dossier_id")})
    dossier_map: Dict[str, str] = {}
    if dossier_ids:
        d_resp = (
            supabase.table("dossiers")
            .select("id, numero_dossier")
            .in_("id", dossier_ids)
            .execute()
        )
        dossier_map = {d["id"]: d["numero_dossier"] for d in (d_resp.data or [])}

    notifications: List[Dict[str, Any]] = []
    for h in history:
        numero = dossier_map.get(h.get("dossier_id", ""), "")
        notifications.append({
            "id": h["id"],
            "type": _STATUT_TYPE.get(h.get("nouveau_statut", ""), "info"),
            "title": f"Dossier {numero}" if numero else "Événement",
            "message": h.get("action", ""),
            "time": h.get("created_at", ""),
        })

    # Pour les admins : ajouter les demandes de droits en attente
    if service_id == 4:
        req_resp = (
            supabase.table("demandes_droits")
            .select("id, motif, created_at, dossier_id, users(nom_complet)")
            .eq("statut", "EN_ATTENTE")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        req_ids = list({r["dossier_id"] for r in (req_resp.data or []) if r.get("dossier_id")})
        req_map: Dict[str, str] = {}
        if req_ids:
            rd = supabase.table("dossiers").select("id, numero_dossier").in_("id", req_ids).execute()
            req_map = {d["id"]: d["numero_dossier"] for d in (rd.data or [])}

        for r in (req_resp.data or []):
            u = r.get("users")
            nom = u.get("nom_complet", "Inconnu") if isinstance(u, dict) else "Inconnu"
            numero = req_map.get(r.get("dossier_id", ""), "")
            notifications.append({
                "id": r["id"],
                "type": "warning",
                "title": "Demande de droits",
                "message": f"{nom} demande l'accès au dossier {numero}",
                "time": r.get("created_at", ""),
            })

    # Dédupliquer + trier + limiter à 10
    seen: set = set()
    result: List[Dict[str, Any]] = []
    for n in sorted(notifications, key=lambda x: x.get("time", ""), reverse=True):
        if n["id"] not in seen:
            seen.add(n["id"])
            result.append(n)
        if len(result) == 10:
            break

    return result
