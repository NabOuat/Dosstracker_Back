from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List

from app.core.deps import get_current_user
from app.database import get_supabase
from app.models.user import User

router = APIRouter(prefix="/service-dashboard", tags=["Service Dashboard"])

@router.get("/overview")
async def get_service_dashboard_overview(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Récupère l'aperçu du tableau de bord pour un service.
    Accessible uniquement aux utilisateurs avec service_tag = 'Bob'
    
    Retourne:
    - Aperçu des dossiers par statut
    - Activités des utilisateurs du service
    - Performances des utilisateurs
    - Statistiques des dossiers
    """
    
    # Vérifier que l'utilisateur a le tag 'Bob'
    if not current_user.service_tag or current_user.service_tag != 'Bob':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux responsables de service (service_tag='Bob')"
        )
    
    service_id = current_user.service_id
    
    try:
        # 1. APERÇU DES DOSSIERS PAR STATUT
        dossiers_query = text("""
            SELECT statut, COUNT(*) as count
            FROM dossiers
            WHERE statut IN (
                SELECT DISTINCT statut FROM dossiers 
                WHERE agent_courrier_id IN (SELECT id FROM users WHERE service_id = :service_id)
                OR agent_spfei_admin_id IN (SELECT id FROM users WHERE service_id = :service_id)
                OR agent_scvaa_id IN (SELECT id FROM users WHERE service_id = :service_id)
                OR agent_spfei_titre_id IN (SELECT id FROM users WHERE service_id = :service_id)
            )
            GROUP BY statut
            ORDER BY count DESC
        """)
        
        dossiers_result = db.execute(dossiers_query, {"service_id": service_id}).fetchall()
        
        dossiers_overview = {}
        total_dossiers = 0
        for row in dossiers_result:
            dossiers_overview[row[0]] = row[1]
            total_dossiers += row[1]
        
        # 2. ACTIVITÉS DES UTILISATEURS DU SERVICE
        activites_query = text("""
            SELECT 
                u.id,
                u.nom_complet,
                COUNT(DISTINCT wh.dossier_id) as dossiers_traites,
                MAX(wh.created_at) as derniere_action,
                COUNT(DISTINCT CASE WHEN wh.created_at >= NOW() - INTERVAL '7 days' THEN wh.dossier_id END) as dossiers_cette_semaine
            FROM users u
            LEFT JOIN workflow_history wh ON wh.user_id = u.id
            WHERE u.service_id = :service_id AND u.is_active = TRUE
            GROUP BY u.id, u.nom_complet
            ORDER BY dossiers_traites DESC
        """)
        
        activites_result = db.execute(activites_query, {"service_id": service_id}).fetchall()
        
        activites = []
        for row in activites_result:
            activites.append({
                "user_id": str(row[0]),
                "nom_complet": row[1],
                "dossiers_traites": row[2] or 0,
                "derniere_action": row[3].isoformat() if row[3] else None,
                "dossiers_cette_semaine": row[4] or 0
            })
        
        # 3. PERFORMANCES DES UTILISATEURS
        performances_query = text("""
            SELECT 
                u.id,
                u.nom_complet,
                COUNT(DISTINCT wh.dossier_id) as total_actions,
                COUNT(DISTINCT CASE WHEN wh.nouveau_statut IN ('CONFORME', 'SPFEI_TITRE', 'CONSERVATION') THEN wh.dossier_id END) as actions_positives,
                ROUND(
                    100.0 * COUNT(DISTINCT CASE WHEN wh.nouveau_statut IN ('CONFORME', 'SPFEI_TITRE', 'CONSERVATION') THEN wh.dossier_id END) / 
                    NULLIF(COUNT(DISTINCT wh.dossier_id), 0),
                    2
                ) as taux_reussite
            FROM users u
            LEFT JOIN workflow_history wh ON wh.user_id = u.id
            WHERE u.service_id = :service_id AND u.is_active = TRUE
            GROUP BY u.id, u.nom_complet
            ORDER BY taux_reussite DESC NULLS LAST
        """)
        
        performances_result = db.execute(performances_query, {"service_id": service_id}).fetchall()
        
        performances = []
        for row in performances_result:
            performances.append({
                "user_id": str(row[0]),
                "nom_complet": row[1],
                "total_actions": row[2] or 0,
                "actions_positives": row[3] or 0,
                "taux_reussite": float(row[4]) if row[4] else 0.0
            })
        
        # 4. STATISTIQUES DES DOSSIERS
        stats_query = text("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE statut = 'COURRIER') as en_courrier,
                COUNT(*) FILTER (WHERE statut = 'SPFEI_ADMIN') as en_spfei_admin,
                COUNT(*) FILTER (WHERE statut = 'SCVAA') as en_scvaa,
                COUNT(*) FILTER (WHERE statut = 'NON_CONFORME') as non_conformes,
                COUNT(*) FILTER (WHERE statut = 'SPFEI_TITRE') as en_spfei_titre,
                COUNT(*) FILTER (WHERE statut = 'CONSERVATION') as en_conservation,
                COUNT(*) FILTER (WHERE statut = 'RETOUR_CORRECTION') as en_retour_correction,
                COUNT(*) FILTER (WHERE statut = 'RETOUR_CONSERVATION') as en_retour_conservation,
                COUNT(*) FILTER (WHERE statut = 'ATTENTE_SIGNATURE_APFR') as en_attente_apfr,
                ROUND(AVG(EXTRACT(DAY FROM (updated_at - created_at)))::numeric, 2) as temps_moyen_jours,
                COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') as dossiers_ce_mois
            FROM dossiers
            WHERE agent_courrier_id IN (SELECT id FROM users WHERE service_id = :service_id)
            OR agent_spfei_admin_id IN (SELECT id FROM users WHERE service_id = :service_id)
            OR agent_scvaa_id IN (SELECT id FROM users WHERE service_id = :service_id)
            OR agent_spfei_titre_id IN (SELECT id FROM users WHERE service_id = :service_id)
        """)
        
        stats_result = db.execute(stats_query, {"service_id": service_id}).fetchone()
        
        statistiques = {
            "total": stats_result[0] or 0,
            "en_courrier": stats_result[1] or 0,
            "en_spfei_admin": stats_result[2] or 0,
            "en_scvaa": stats_result[3] or 0,
            "non_conformes": stats_result[4] or 0,
            "en_spfei_titre": stats_result[5] or 0,
            "en_conservation": stats_result[6] or 0,
            "en_retour_correction": stats_result[7] or 0,
            "en_retour_conservation": stats_result[8] or 0,
            "en_attente_apfr": stats_result[9] or 0,
            "temps_moyen_jours": float(stats_result[10]) if stats_result[10] else 0.0,
            "dossiers_ce_mois": stats_result[11] or 0
        }
        
        # 5. TAUX DE CONFORMITÉ
        conformite_query = text("""
            SELECT 
                COUNT(*) FILTER (WHERE decision_conformite = 'CONFORME') as conformes,
                COUNT(*) FILTER (WHERE decision_conformite = 'NON_CONFORME') as non_conformes,
                COUNT(*) FILTER (WHERE decision_conformite IS NOT NULL) as total_evalues
            FROM dossiers
            WHERE agent_scvaa_id IN (SELECT id FROM users WHERE service_id = :service_id)
        """)
        
        conformite_result = db.execute(conformite_query, {"service_id": service_id}).fetchone()
        
        taux_conformite = {
            "conformes": conformite_result[0] or 0,
            "non_conformes": conformite_result[1] or 0,
            "total_evalues": conformite_result[2] or 0,
            "pourcentage": round(
                (conformite_result[0] or 0) / (conformite_result[2] or 1) * 100, 2
            ) if conformite_result[2] else 0.0
        }
        
        return {
            "service_id": service_id,
            "dossiers_overview": dossiers_overview,
            "total_dossiers": total_dossiers,
            "activites_utilisateurs": activites,
            "performances_utilisateurs": performances,
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
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Récupère la répartition des dossiers par région pour le service.
    Accessible uniquement aux utilisateurs avec service_tag = 'Bob'
    """
    
    if not current_user.service_tag or current_user.service_tag != 'Bob':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux responsables de service"
        )
    
    service_id = current_user.service_id
    
    try:
        query = text("""
            SELECT 
                d.region,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE d.statut = 'CONSERVATION') as termines,
                COUNT(*) FILTER (WHERE d.statut = 'NON_CONFORME') as non_conformes,
                COUNT(*) FILTER (WHERE d.statut NOT IN ('CONSERVATION')) as en_cours
            FROM dossiers d
            WHERE d.agent_courrier_id IN (SELECT id FROM users WHERE service_id = :service_id)
            OR d.agent_spfei_admin_id IN (SELECT id FROM users WHERE service_id = :service_id)
            OR d.agent_scvaa_id IN (SELECT id FROM users WHERE service_id = :service_id)
            OR d.agent_spfei_titre_id IN (SELECT id FROM users WHERE service_id = :service_id)
            GROUP BY d.region
            ORDER BY total DESC
        """)
        
        results = db.execute(query, {"service_id": service_id}).fetchall()
        
        regions = []
        for row in results:
            regions.append({
                "region": row[0],
                "total": row[1],
                "termines": row[2],
                "non_conformes": row[3],
                "en_cours": row[4]
            })
        
        return regions
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la récupération des dossiers par région: {str(e)}"
        )

@router.get("/utilisateurs")
async def get_utilisateurs_service(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Récupère la liste détaillée des utilisateurs du service avec leurs statistiques.
    Accessible uniquement aux utilisateurs avec service_tag = 'Bob'
    """
    
    if not current_user.service_tag or current_user.service_tag != 'Bob':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux responsables de service"
        )
    
    service_id = current_user.service_id
    
    try:
        query = text("""
            SELECT 
                u.id,
                u.nom_complet,
                u.email,
                u.is_active,
                u.last_login,
                COUNT(DISTINCT wh.dossier_id) as dossiers_traites,
                MAX(wh.created_at) as derniere_action,
                COUNT(DISTINCT CASE WHEN wh.created_at >= NOW() - INTERVAL '7 days' THEN wh.dossier_id END) as dossiers_semaine,
                COUNT(DISTINCT CASE WHEN wh.created_at >= NOW() - INTERVAL '30 days' THEN wh.dossier_id END) as dossiers_mois
            FROM users u
            LEFT JOIN workflow_history wh ON wh.user_id = u.id
            WHERE u.service_id = :service_id
            GROUP BY u.id, u.nom_complet, u.email, u.is_active, u.last_login
            ORDER BY dossiers_traites DESC
        """)
        
        results = db.execute(query, {"service_id": service_id}).fetchall()
        
        utilisateurs = []
        for row in results:
            utilisateurs.append({
                "user_id": str(row[0]),
                "nom_complet": row[1],
                "email": row[2],
                "is_active": row[3],
                "last_login": row[4].isoformat() if row[4] else None,
                "dossiers_traites": row[5] or 0,
                "derniere_action": row[6].isoformat() if row[6] else None,
                "dossiers_semaine": row[7] or 0,
                "dossiers_mois": row[8] or 0
            })
        
        return utilisateurs
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la récupération des utilisateurs: {str(e)}"
        )
