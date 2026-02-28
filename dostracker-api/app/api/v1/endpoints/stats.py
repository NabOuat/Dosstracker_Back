from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone

from app.core.deps import get_current_active_user
from app.database import get_supabase

router = APIRouter(prefix="/stats", tags=["Statistiques"])

@router.get("/")
async def get_stats(
    current_user: dict = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Récupère les statistiques globales ou filtrées par service selon le rôle de l'utilisateur
    """
    supabase = get_supabase()
    service_id = current_user["service_id"]
    
    # Initialiser les statistiques
    stats = {
        "total": 0,
        "courrier": 0,
        "spfei_admin": 0,
        "scvaa": 0,
        "non_conforme": 0,
        "spfei_titre": 0,
        "conservation": 0,
        "sms_envoyes": 0,
        "temps_moyen": {}
    }
    
    # Filtrer les statistiques selon le service de l'utilisateur
    if service_id == 1:  # SERVICE_COURRIER
        # Le service courrier ne voit que ses propres dossiers
        dossiers = supabase.table("dossiers").select("id, statut").eq("statut", "COURRIER").execute()
        stats["total"] = len(dossiers.data) if dossiers.data else 0
        stats["courrier"] = stats["total"]
        
        # Nombre de SMS envoyés pour les dossiers du service
        sms = supabase.table("sms_log").select("id").execute()
        stats["sms_envoyes"] = len(sms.data) if sms.data else 0
        
    elif service_id == 2:  # SERVICE_SPFEI
        # Le service SPFEI voit ses dossiers actuels et ceux qu'il a traités
        dossiers = supabase.table("dossiers").select("id, statut").in_("statut", ["SPFEI_ADMIN", "SPFEI_TITRE", "SCVAA", "NON_CONFORME", "CONSERVATION"]).execute()
        
        if dossiers.data:
            stats["total"] = len(dossiers.data)
            
            # Compter par statut
            for d in dossiers.data:
                if d["statut"] == "SPFEI_ADMIN":
                    stats["spfei_admin"] += 1
                elif d["statut"] == "SPFEI_TITRE":
                    stats["spfei_titre"] += 1
                elif d["statut"] == "SCVAA":
                    stats["scvaa"] += 1
                elif d["statut"] == "NON_CONFORME":
                    stats["non_conforme"] += 1
                elif d["statut"] == "CONSERVATION":
                    stats["conservation"] += 1
        
        # Nombre de SMS envoyés pour les dossiers du service
        sms = supabase.table("sms_log").select("id").execute()
        stats["sms_envoyes"] = len(sms.data) if sms.data else 0
        
    elif service_id == 3:  # SERVICE_SCVAA
        # Le service SCVAA voit ses dossiers actuels et ceux qu'il a traités
        dossiers = supabase.table("dossiers").select("id, statut").in_("statut", ["SCVAA", "NON_CONFORME", "SPFEI_TITRE", "CONSERVATION"]).execute()
        
        if dossiers.data:
            stats["total"] = len(dossiers.data)
            
            # Compter par statut
            for d in dossiers.data:
                if d["statut"] == "SCVAA":
                    stats["scvaa"] += 1
                elif d["statut"] == "NON_CONFORME":
                    stats["non_conforme"] += 1
                elif d["statut"] == "SPFEI_TITRE":
                    stats["spfei_titre"] += 1
                elif d["statut"] == "CONSERVATION":
                    stats["conservation"] += 1
        
        # Nombre de SMS envoyés pour les dossiers du service
        sms = supabase.table("sms_log").select("id").execute()
        stats["sms_envoyes"] = len(sms.data) if sms.data else 0
        
        # Temps moyen de traitement pour le service SCVAA
        stats["temps_moyen"] = await calculate_processing_times()
        
    else:  # ADMIN ou CONSERVATION - voit tout
        # Compter le nombre total de dossiers
        dossiers = supabase.table("dossiers").select("id, statut").execute()
        
        if dossiers.data:
            stats["total"] = len(dossiers.data)
            
            # Compter par statut
            for d in dossiers.data:
                if d["statut"] == "COURRIER":
                    stats["courrier"] += 1
                elif d["statut"] == "SPFEI_ADMIN":
                    stats["spfei_admin"] += 1
                elif d["statut"] == "SCVAA":
                    stats["scvaa"] += 1
                elif d["statut"] == "NON_CONFORME":
                    stats["non_conforme"] += 1
                elif d["statut"] == "SPFEI_TITRE":
                    stats["spfei_titre"] += 1
                elif d["statut"] == "CONSERVATION":
                    stats["conservation"] += 1
        
        # Nombre de SMS envoyés
        sms = supabase.table("sms_log").select("id").execute()
        stats["sms_envoyes"] = len(sms.data) if sms.data else 0
        
        # Temps moyen de traitement
        stats["temps_moyen"] = await calculate_processing_times()
    
    return stats

async def calculate_processing_times() -> Dict[str, Any]:
    """
    Calcule les temps moyens de traitement entre les différentes étapes du workflow
    """
    supabase = get_supabase()
    
    # Récupérer tous les dossiers avec leurs dates de transition
    dossiers = supabase.table("dossiers").select(
        "id, date_enregistrement, date_envoi_spfei, date_envoi_scvaa, date_decision_scvaa, date_attribution_titre, date_envoi_conservation"
    ).execute()
    
    if not dossiers.data:
        return {}
    
    # Initialiser les compteurs
    times = {
        "courrier_to_spfei": {"total_days": 0, "count": 0},
        "spfei_to_scvaa": {"total_days": 0, "count": 0},
        "scvaa_to_decision": {"total_days": 0, "count": 0},
        "spfei_titre_to_conservation": {"total_days": 0, "count": 0},
        "total_process": {"total_days": 0, "count": 0}
    }
    
    # Calculer les temps pour chaque dossier
    for d in dossiers.data:
        # Courrier → SPFEI
        if d["date_enregistrement"] and d["date_envoi_spfei"]:
            try:
                # Convertir date_enregistrement (date) en datetime UTC
                if isinstance(d["date_enregistrement"], str):
                    start = datetime.fromisoformat(d["date_enregistrement"]).replace(tzinfo=timezone.utc)
                else:
                    start = datetime.combine(d["date_enregistrement"], datetime.min.time()).replace(tzinfo=timezone.utc)
                
                # Convertir date_envoi_spfei (timestamp) en datetime UTC
                end = datetime.fromisoformat(d["date_envoi_spfei"].replace("Z", "+00:00"))
                
                days = (end - start).total_seconds() / 86400  # Convertir en jours
                times["courrier_to_spfei"]["total_days"] += days
                times["courrier_to_spfei"]["count"] += 1
            except Exception:
                pass
        
        # SPFEI → SCVAA
        if d["date_envoi_spfei"] and d["date_envoi_scvaa"]:
            try:
                start = datetime.fromisoformat(d["date_envoi_spfei"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(d["date_envoi_scvaa"].replace("Z", "+00:00"))
                days = (end - start).total_seconds() / 86400
                times["spfei_to_scvaa"]["total_days"] += days
                times["spfei_to_scvaa"]["count"] += 1
            except Exception:
                pass
        
        # SCVAA → Décision
        if d["date_envoi_scvaa"] and d["date_decision_scvaa"]:
            try:
                start = datetime.fromisoformat(d["date_envoi_scvaa"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(d["date_decision_scvaa"].replace("Z", "+00:00"))
                days = (end - start).total_seconds() / 86400
                times["scvaa_to_decision"]["total_days"] += days
                times["scvaa_to_decision"]["count"] += 1
            except Exception:
                pass
        
        # SPFEI Titre → Conservation
        if d["date_attribution_titre"] and d["date_envoi_conservation"]:
            try:
                start = datetime.fromisoformat(d["date_attribution_titre"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(d["date_envoi_conservation"].replace("Z", "+00:00"))
                days = (end - start).total_seconds() / 86400
                times["spfei_titre_to_conservation"]["total_days"] += days
                times["spfei_titre_to_conservation"]["count"] += 1
            except Exception:
                pass
        
        # Processus complet
        if d["date_enregistrement"] and d["date_envoi_conservation"]:
            try:
                # Convertir date_enregistrement (date) en datetime UTC
                if isinstance(d["date_enregistrement"], str):
                    start = datetime.fromisoformat(d["date_enregistrement"]).replace(tzinfo=timezone.utc)
                else:
                    start = datetime.combine(d["date_enregistrement"], datetime.min.time()).replace(tzinfo=timezone.utc)
                
                end = datetime.fromisoformat(d["date_envoi_conservation"].replace("Z", "+00:00"))
                days = (end - start).total_seconds() / 86400
                times["total_process"]["total_days"] += days
                times["total_process"]["count"] += 1
            except Exception:
                pass
    
    # Calculer les moyennes
    result = {}
    for key, data in times.items():
        if data["count"] > 0:
            result[key] = round(data["total_days"] / data["count"], 1)  # Arrondir à 1 décimale
        else:
            result[key] = 0
    
    return result

@router.get("/performance")
async def get_performance_stats(
    current_user: dict = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Récupère les statistiques de performance par service
    """
    # Vérifier si l'utilisateur a accès à ces statistiques
    service_id = current_user["service_id"]
    if service_id != 3 and service_id != 4:  # Seulement SCVAA et ADMIN
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas accès à ces statistiques"
        )
    
    supabase = get_supabase()
    
    # Récupérer les données pour calculer les performances
    dossiers = supabase.table("dossiers").select(
        "id, statut, date_enregistrement, date_envoi_spfei, date_envoi_scvaa, date_decision_scvaa, date_attribution_titre, date_envoi_conservation"
    ).execute()
    
    if not dossiers.data:
        return {"services": {}, "global": {}}
    
    # Initialiser les compteurs par service
    services = {
        "courrier": {"dossiers": 0, "temps_moyen": 0, "total_jours": 0},
        "spfei_admin": {"dossiers": 0, "temps_moyen": 0, "total_jours": 0},
        "scvaa": {"dossiers": 0, "temps_moyen": 0, "total_jours": 0},
        "spfei_titre": {"dossiers": 0, "temps_moyen": 0, "total_jours": 0}
    }
    
    # Calculer les performances par service
    for d in dossiers.data:
        # SERVICE COURRIER
        if d["date_enregistrement"] and d["date_envoi_spfei"]:
            start = datetime.fromisoformat(d["date_enregistrement"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(d["date_envoi_spfei"].replace("Z", "+00:00"))
            jours = (end - start).total_seconds() / 86400
            services["courrier"]["dossiers"] += 1
            services["courrier"]["total_jours"] += jours
        
        # SERVICE SPFEI (Admin)
        if d["date_envoi_spfei"] and d["date_envoi_scvaa"]:
            start = datetime.fromisoformat(d["date_envoi_spfei"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(d["date_envoi_scvaa"].replace("Z", "+00:00"))
            jours = (end - start).total_seconds() / 86400
            services["spfei_admin"]["dossiers"] += 1
            services["spfei_admin"]["total_jours"] += jours
        
        # SERVICE SCVAA
        if d["date_envoi_scvaa"] and d["date_decision_scvaa"]:
            start = datetime.fromisoformat(d["date_envoi_scvaa"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(d["date_decision_scvaa"].replace("Z", "+00:00"))
            jours = (end - start).total_seconds() / 86400
            services["scvaa"]["dossiers"] += 1
            services["scvaa"]["total_jours"] += jours
        
        # SERVICE SPFEI (Titre)
        if d["date_attribution_titre"] and d["date_envoi_conservation"]:
            start = datetime.fromisoformat(d["date_attribution_titre"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(d["date_envoi_conservation"].replace("Z", "+00:00"))
            jours = (end - start).total_seconds() / 86400
            services["spfei_titre"]["dossiers"] += 1
            services["spfei_titre"]["total_jours"] += jours
    
    # Calculer les temps moyens
    for service, data in services.items():
        if data["dossiers"] > 0:
            data["temps_moyen"] = round(data["total_jours"] / data["dossiers"], 1)
    
    # Statistiques globales
    global_stats = {
        "dossiers_total": len(dossiers.data),
        "dossiers_termines": sum(1 for d in dossiers.data if d["statut"] == "CONSERVATION"),
        "dossiers_en_cours": sum(1 for d in dossiers.data if d["statut"] != "CONSERVATION"),
        "taux_conformite": calculate_conformity_rate(dossiers.data)
    }
    
    return {
        "services": services,
        "global": global_stats
    }

def calculate_conformity_rate(dossiers: List[Dict[str, Any]]) -> float:
    """
    Calcule le taux de conformité des dossiers
    """
    if not dossiers:
        return 0
    
    total_decisions = sum(1 for d in dossiers if d.get("date_decision_scvaa"))
    if total_decisions == 0:
        return 0
    
    non_conformes = sum(1 for d in dossiers if d.get("statut") == "NON_CONFORME")
    
    # Calculer le taux de conformité (pourcentage de dossiers conformes)
    return round(((total_decisions - non_conformes) / total_decisions) * 100, 1)
