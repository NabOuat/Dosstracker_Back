from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from app.core.deps import get_current_user
from app.database import get_supabase

router = APIRouter(prefix="/service-dashboard", tags=["Service Dashboard"])


@router.get("/overview")
async def get_service_dashboard_overview(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    if not current_user.get("service_tag") or current_user["service_tag"] != 'Bob':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux responsables de service (service_tag='Bob')"
        )

    service_id = current_user["service_id"]
    supabase = get_supabase()

    try:
        # 1. Utilisateurs du service
        users_res = supabase.table("users").select("id").eq("service_id", service_id).execute()
        user_ids = [u["id"] for u in users_res.data] if users_res.data else []

        # 2. Dossiers du service (ceux traités par des agents du service)
        dossiers_res = supabase.table("dossiers").select("id,statut,created_at,updated_at,decision_conformite").execute()
        tous_dossiers = dossiers_res.data or []

        # Aperçu par statut
        dossiers_overview = {}
        total_dossiers = len(tous_dossiers)
        for d in tous_dossiers:
            s = d["statut"]
            dossiers_overview[s] = dossiers_overview.get(s, 0) + 1

        # 3. Activités des utilisateurs du service (workflow_history)
        activites = []
        for uid in user_ids:
            user_info_res = supabase.table("users").select("id,nom_complet").eq("id", uid).execute()
            wh_res = supabase.table("workflow_history").select("dossier_id,created_at").eq("user_id", uid).execute()
            wh_data = wh_res.data or []

            dossiers_traites = len(set(w["dossier_id"] for w in wh_data))
            derniere_action = max((w["created_at"] for w in wh_data), default=None)

            activites.append({
                "user_id": uid,
                "nom_complet": user_info_res.data[0]["nom_complet"] if user_info_res.data else uid,
                "dossiers_traites": dossiers_traites,
                "derniere_action": derniere_action,
                "dossiers_cette_semaine": 0
            })

        activites.sort(key=lambda x: x["dossiers_traites"], reverse=True)

        # 4. Statistiques dossiers
        statuts = [d["statut"] for d in tous_dossiers]
        statistiques = {
            "total": total_dossiers,
            "en_courrier": statuts.count("COURRIER"),
            "en_spfei_admin": statuts.count("SPFEI_ADMIN"),
            "en_scvaa": statuts.count("SCVAA"),
            "non_conformes": statuts.count("NON_CONFORME"),
            "en_spfei_titre": statuts.count("SPFEI_TITRE"),
            "en_conservation": statuts.count("CONSERVATION"),
            "en_retour_correction": statuts.count("RETOUR_CORRECTION"),
            "en_retour_conservation": statuts.count("RETOUR_CONSERVATION"),
            "en_attente_apfr": statuts.count("ATTENTE_SIGNATURE_APFR"),
            "temps_moyen_jours": 0.0,
            "dossiers_ce_mois": 0
        }

        # 5. Taux de conformité
        decisions = [d.get("decision_conformite") for d in tous_dossiers]
        conformes = decisions.count("CONFORME")
        non_conformes_dec = decisions.count("NON_CONFORME")
        total_evalues = conformes + non_conformes_dec

        taux_conformite = {
            "conformes": conformes,
            "non_conformes": non_conformes_dec,
            "total_evalues": total_evalues,
            "pourcentage": round(conformes / total_evalues * 100, 2) if total_evalues else 0.0
        }

        return {
            "service_id": service_id,
            "dossiers_overview": dossiers_overview,
            "total_dossiers": total_dossiers,
            "activites_utilisateurs": activites,
            "performances_utilisateurs": activites,
            "statistiques_dossiers": statistiques,
            "taux_conformite": taux_conformite,
            "nombre_utilisateurs_actifs": len(activites)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la récupération du tableau de bord: {str(e)}"
        )


@router.get("/dossiers-par-region")
async def get_dossiers_par_region(
    current_user: dict = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    if not current_user.get("service_tag") or current_user["service_tag"] != 'Bob':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux responsables de service"
        )

    supabase = get_supabase()

    try:
        dossiers_res = supabase.table("dossiers").select("region,statut").execute()
        dossiers = dossiers_res.data or []

        regions_map: Dict[str, Dict] = {}
        for d in dossiers:
            r = d.get("region") or "Inconnue"
            if r not in regions_map:
                regions_map[r] = {"region": r, "total": 0, "termines": 0, "non_conformes": 0, "en_cours": 0}
            regions_map[r]["total"] += 1
            if d["statut"] == "CONSERVATION":
                regions_map[r]["termines"] += 1
            elif d["statut"] == "NON_CONFORME":
                regions_map[r]["non_conformes"] += 1
            else:
                regions_map[r]["en_cours"] += 1

        return sorted(regions_map.values(), key=lambda x: x["total"], reverse=True)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la récupération des dossiers par région: {str(e)}"
        )


@router.get("/utilisateurs")
async def get_utilisateurs_service(
    current_user: dict = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    if not current_user.get("service_tag") or current_user["service_tag"] != 'Bob':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux responsables de service"
        )

    service_id = current_user["service_id"]
    supabase = get_supabase()

    try:
        users_res = supabase.table("users").select("id,nom_complet,email,is_active,last_login").eq("service_id", service_id).execute()
        utilisateurs = []

        for u in (users_res.data or []):
            wh_res = supabase.table("workflow_history").select("dossier_id,created_at").eq("user_id", u["id"]).execute()
            wh_data = wh_res.data or []
            dossiers_traites = len(set(w["dossier_id"] for w in wh_data))
            derniere_action = max((w["created_at"] for w in wh_data), default=None)

            utilisateurs.append({
                "user_id": str(u["id"]),
                "nom_complet": u["nom_complet"],
                "email": u["email"],
                "is_active": u["is_active"],
                "last_login": u.get("last_login"),
                "dossiers_traites": dossiers_traites,
                "derniere_action": derniere_action,
                "dossiers_semaine": 0,
                "dossiers_mois": 0
            })

        return sorted(utilisateurs, key=lambda x: x["dossiers_traites"], reverse=True)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la récupération des utilisateurs: {str(e)}"
        )
