from fastapi import APIRouter, HTTPException, status
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from logger import get_logger
from app.database import get_supabase

logger = get_logger()
router = APIRouter(prefix="/debug", tags=["Debug"])

@router.get("/users")
async def debug_get_users():
    """
    Endpoint de diagnostic pour vérifier les utilisateurs dans la base de données
    """
    logger.info("Endpoint debug /users appelé")
    try:
        supabase = get_supabase()
        logger.debug("Connexion à Supabase établie")
        
        # Essayer de récupérer tous les utilisateurs
        logger.debug("Tentative de récupération de tous les utilisateurs...")
        response = supabase.table("users").select("id, username, email, nom_complet, is_active").execute()
        
        logger.debug(f"Réponse reçue: {response.data}")
        logger.info(f"Nombre d'utilisateurs trouvés: {len(response.data) if response.data else 0}")
        
        return {
            "success": True,
            "count": len(response.data) if response.data else 0,
            "users": response.data if response.data else [],
            "message": "Récupération réussie"
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des utilisateurs: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Erreur lors de la récupération des utilisateurs"
        }

@router.get("/users/{username}")
async def debug_get_user_by_username(username: str):
    """
    Endpoint de diagnostic pour vérifier un utilisateur spécifique
    """
    logger.info(f"Endpoint debug /users/{username} appelé")
    try:
        supabase = get_supabase()
        logger.debug("Connexion à Supabase établie")
        
        # Essayer de récupérer l'utilisateur
        logger.debug(f"Tentative de récupération de l'utilisateur: {username}")
        response = supabase.table("users").select("*").eq("username", username).execute()
        
        logger.debug(f"Réponse reçue: {response.data}")
        
        if response.data and len(response.data) > 0:
            logger.info(f"Utilisateur trouvé: {username}")
            return {
                "success": True,
                "user": response.data[0],
                "message": "Utilisateur trouvé"
            }
        else:
            logger.warning(f"Utilisateur non trouvé: {username}")
            return {
                "success": False,
                "user": None,
                "message": "Utilisateur non trouvé"
            }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'utilisateur {username}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Erreur lors de la récupération de l'utilisateur"
        }

@router.get("/rls-check")
async def debug_rls_check():
    """
    Endpoint de diagnostic pour vérifier les politiques RLS
    """
    logger.info("Endpoint debug /rls-check appelé")
    try:
        supabase = get_supabase()
        logger.debug("Connexion à Supabase établie")
        
        # Essayer de récupérer les utilisateurs avec différentes approches
        logger.debug("Test 1: Récupération simple de la table users")
        response1 = supabase.table("users").select("count", count="exact").execute()
        logger.debug(f"Réponse 1: {response1}")
        
        logger.debug("Test 2: Récupération avec limit")
        response2 = supabase.table("users").select("*").limit(1).execute()
        logger.debug(f"Réponse 2: {response2.data}")
        
        logger.debug("Test 3: Récupération avec filtre simple")
        response3 = supabase.table("users").select("*").eq("is_active", True).limit(1).execute()
        logger.debug(f"Réponse 3: {response3.data}")
        
        return {
            "success": True,
            "tests": {
                "count_test": "Réussi" if response1 else "Échoué",
                "limit_test": "Réussi" if response2.data else "Échoué",
                "filter_test": "Réussi" if response3.data else "Échoué"
            },
            "message": "Tests RLS complétés"
        }
    except Exception as e:
        logger.error(f"Erreur lors du test RLS: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Erreur lors du test RLS"
        }
