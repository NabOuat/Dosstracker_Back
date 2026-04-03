"""
Module pour optimiser les requêtes Supabase et éviter les N+1 queries
"""
from typing import List, Dict, Any, Optional
from app.database import get_supabase

class QueryOptimizer:
    """Optimiseur de requêtes pour éviter les N+1 queries"""
    
    @staticmethod
    def get_dossiers_with_relations(
        statut: Optional[str] = None,
        region: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Récupère les dossiers avec leurs relations (proprietaire, agent, service)
        en une seule requête pour éviter N+1 queries
        """
        supabase = get_supabase()
        
        query = supabase.table("dossiers").select(
            """
            id, numero_dossier, statut, region, prefecture, sous_prefecture, village,
            numero_cf, superficie, date_bornage, date_levee_plan, date_depot_dossier,
            date_reception_courrier, date_transmission_spfei, date_transmission_scvaa,
            date_transmission_titre, date_attribution_titre, date_envoi_conservation,
            created_at, updated_at,
            proprietaires(id, nom_complet, telephone, email, genre),
            users!agent_courrier_id(id, nom_complet, username),
            users!agent_spfei_admin_id(id, nom_complet, username),
            users!agent_scvaa_id(id, nom_complet, username),
            users!agent_spfei_titre_id(id, nom_complet, username)
            """
        )
        
        if statut:
            query = query.eq("statut", statut)
        if region:
            query = query.eq("region", region)
        
        response = query.range(skip, skip + limit).execute()
        return response.data if response.data else []
    
    @staticmethod
    def get_dossier_detail(dossier_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un dossier avec toutes ses relations et données associées
        """
        supabase = get_supabase()
        
        # Requête principale
        dossier_response = supabase.table("dossiers").select(
            """
            id, numero_dossier, statut, region, prefecture, sous_prefecture, village,
            numero_cf, superficie, date_bornage, date_levee_plan, date_depot_dossier,
            date_reception_courrier, date_transmission_spfei, date_transmission_scvaa,
            date_transmission_titre, date_attribution_titre, date_envoi_conservation,
            created_at, updated_at,
            proprietaires(id, nom_complet, telephone, email, genre),
            users!agent_courrier_id(id, nom_complet, username),
            users!agent_spfei_admin_id(id, nom_complet, username),
            users!agent_scvaa_id(id, nom_complet, username),
            users!agent_spfei_titre_id(id, nom_complet, username)
            """
        ).eq("id", dossier_id).single().execute()
        
        if not dossier_response.data:
            return None
        
        dossier = dossier_response.data
        
        # Récupérer les commentaires
        comments_response = supabase.table("commentaires").select(
            "id, contenu, est_important, created_at, users(nom_complet, username)"
        ).eq("dossier_id", dossier_id).order("created_at", desc=True).execute()
        
        dossier["commentaires"] = comments_response.data if comments_response.data else []
        
        # Récupérer les pièces jointes
        pieces_response = supabase.table("pieces_jointes").select(
            "id, nom_original, type_fichier, taille_octets, created_at"
        ).eq("dossier_id", dossier_id).order("created_at", desc=True).execute()
        
        dossier["pieces_jointes"] = pieces_response.data if pieces_response.data else []
        
        # Récupérer l'historique
        history_response = supabase.table("workflow_history").select(
            "id, ancien_statut, nouveau_statut, action, details, created_at, users(nom_complet)"
        ).eq("dossier_id", dossier_id).order("created_at", desc=True).execute()
        
        dossier["historique"] = history_response.data if history_response.data else []
        
        return dossier
    
    @staticmethod
    def get_stats_optimized(service_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Récupère les statistiques de manière optimisée avec une seule requête
        """
        supabase = get_supabase()
        
        # Utiliser les vues matérialisées si disponibles
        query = supabase.table("v_stats_statut").select("*")
        
        if service_id:
            query = query.eq("service_id", service_id)
        
        response = query.execute()
        
        stats = {
            "total": 0,
            "courrier": 0,
            "spfei_admin": 0,
            "scvaa": 0,
            "non_conforme": 0,
            "spfei_titre": 0,
            "conservation": 0
        }
        
        if response.data:
            for row in response.data:
                statut = row.get("statut", "").lower()
                count = row.get("count", 0)
                
                if statut == "courrier":
                    stats["courrier"] = count
                elif statut == "spfei_admin":
                    stats["spfei_admin"] = count
                elif statut == "scvaa":
                    stats["scvaa"] = count
                elif statut == "non_conforme":
                    stats["non_conforme"] = count
                elif statut == "spfei_titre":
                    stats["spfei_titre"] = count
                elif statut == "conservation":
                    stats["conservation"] = count
                
                stats["total"] += count
        
        return stats
    
    @staticmethod
    def batch_get_dossiers(dossier_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Récupère plusieurs dossiers en une seule requête
        """
        supabase = get_supabase()
        
        response = supabase.table("dossiers").select(
            """
            id, numero_dossier, statut, region, prefecture, sous_prefecture, village,
            numero_cf, superficie, created_at, updated_at,
            proprietaires(id, nom_complet, telephone, email)
            """
        ).in_("id", dossier_ids).execute()
        
        return response.data if response.data else []
