from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import Any
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from logger import get_logger
from app.core.security import verify_password
from app.core.token_manager import TokenManager
from app.core.rate_limiter import login_rate_limiter
from app.core.two_factor_auth import TwoFactorAuth
from app.database import get_supabase
from app.models.token import Token, TokenRefresh

logger = get_logger()
router = APIRouter(prefix="/auth", tags=["Authentification"])

def get_client_ip(request: Request) -> str:
    """Extraire l'adresse IP du client"""
    if request.client:
        return request.client.host
    return "unknown"

@router.post("/login", response_model=Token)
async def login_enhanced(form_data: OAuth2PasswordRequestForm = Depends(), request: Request = None) -> Any:
    """
    Authentification avec rate limiting et refresh tokens
    """
    client_ip = get_client_ip(request)
    logger.info(f"Tentative de connexion pour l'utilisateur: {form_data.username} depuis {client_ip}")
    
    # Vérifier le rate limiting
    allowed, remaining = login_rate_limiter.is_allowed(client_ip, form_data.username)
    if not allowed:
        remaining_time = login_rate_limiter.get_remaining_time(client_ip)
        logger.warning(f"Rate limit dépassé pour {client_ip}. Réessai dans {remaining_time}s")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Trop de tentatives. Réessayez dans {remaining_time} secondes."
        )
    
    logger.debug(f"Rate limiting: {remaining} tentatives restantes pour {client_ip}")
    
    try:
        # Récupérer l'utilisateur depuis Supabase
        supabase = get_supabase()
        logger.debug(f"Connexion à Supabase établie")
        
        user_response = supabase.table("users").select("*, services(nom, libelle)").eq("username", form_data.username).execute()
        logger.debug(f"Réponse Supabase reçue pour l'utilisateur {form_data.username}")
        
        if user_response.data is None or len(user_response.data) == 0:
            logger.warning(f"Utilisateur non trouvé: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nom d'utilisateur ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = user_response.data[0]
        logger.debug(f"Utilisateur trouvé: {user['username']}, ID: {user['id']}")
        
        # Vérifier le mot de passe
        if not verify_password(form_data.password, user["hashed_password"]):
            logger.warning(f"Mot de passe incorrect pour l'utilisateur: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nom d'utilisateur ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.debug(f"Mot de passe vérifié pour l'utilisateur: {form_data.username}")
        
        # Vérifier si l'utilisateur est actif
        if not user["is_active"]:
            logger.warning(f"Utilisateur inactif: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Utilisateur inactif"
            )
        
        logger.debug(f"Utilisateur actif: {form_data.username}")
        
        # Récupérer le nom du service
        service_libelle = user["services"]["libelle"] if user["services"] else ""
        
        # Créer les tokens
        access_token = TokenManager.create_access_token(
            subject=user["username"],
            user_id=user["id"],
            service_id=user["service_id"],
            nom_complet=user["nom_complet"],
            service=service_libelle
        )
        
        refresh_token = TokenManager.create_refresh_token(
            subject=user["username"],
            user_id=user["id"]
        )
        
        # Créer une session
        session_id = TokenManager.create_session(
            user_id=user["id"],
            username=user["username"],
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent", "unknown") if request else "unknown"
        )
        
        logger.debug(f"Session créée: {session_id}")
        
        # Mettre à jour la date de dernière connexion
        supabase.table("users").update({"last_login": "now()"}).eq("id", user["id"]).execute()
        logger.debug(f"Date de dernière connexion mise à jour pour: {form_data.username}")
        
        logger.info(f"Connexion réussie pour l'utilisateur: {form_data.username}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user["id"],
            "username": user["username"],
            "nom_complet": user["nom_complet"],
            "service_id": user["service_id"],
            "service": service_libelle
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la connexion pour l'utilisateur {form_data.username}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur lors de l'authentification"
        )

@router.post("/refresh-token", response_model=Token)
async def refresh_token_endpoint(token_data: TokenRefresh) -> Any:
    """
    Rafraîchir un token d'accès avec un refresh token
    """
    logger.debug("Endpoint refresh-token appelé")
    
    try:
        # Vérifier le refresh token
        payload = TokenManager.verify_token(token_data.refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            logger.warning("Refresh token invalide ou expiré")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token invalide ou expiré"
            )
        
        username = payload.get("sub")
        user_id = payload.get("user_id")
        
        logger.debug(f"Refresh token valide pour l'utilisateur: {username}")
        
        # Récupérer les données utilisateur
        supabase = get_supabase()
        user_response = supabase.table("users").select("*, services(nom, libelle)").eq("id", user_id).execute()
        
        if not user_response.data:
            logger.warning(f"Utilisateur non trouvé: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur non trouvé"
            )
        
        user = user_response.data[0]
        service_libelle = user["services"]["libelle"] if user["services"] else ""
        
        # Créer un nouveau token d'accès
        new_access_token = TokenManager.create_access_token(
            subject=user["username"],
            user_id=user["id"],
            service_id=user["service_id"],
            nom_complet=user["nom_complet"],
            service=service_libelle
        )
        
        logger.info(f"Token rafraîchi pour l'utilisateur: {username}")
        
        return {
            "access_token": new_access_token,
            "refresh_token": token_data.refresh_token,
            "token_type": "bearer",
            "user_id": user["id"],
            "username": user["username"],
            "nom_complet": user["nom_complet"],
            "service_id": user["service_id"],
            "service": service_libelle
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du rafraîchissement du token: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur lors du rafraîchissement du token"
        )

@router.post("/logout")
async def logout(request: Request) -> dict:
    """
    Déconnexion avec invalidation de session
    """
    logger.info("Endpoint logout appelé")
    
    try:
        # Récupérer le token du header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("Token manquant dans le header Authorization")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token manquant"
            )
        
        token = auth_header.split(" ")[1]
        
        # Vérifier et décoder le token
        payload = TokenManager.verify_token(token)
        if not payload:
            logger.warning("Token invalide ou expiré")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide ou expiré"
            )
        
        user_id = payload.get("user_id")
        username = payload.get("sub")
        
        # Révoquer le token
        TokenManager.revoke_token(token)
        logger.debug(f"Token révoqué pour l'utilisateur: {username}")
        
        # Invalider toutes les sessions
        TokenManager.invalidate_all_sessions(user_id)
        logger.info(f"Déconnexion réussie pour l'utilisateur: {username}")
        
        return {"message": "Déconnexion réussie"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la déconnexion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur lors de la déconnexion"
        )

@router.get("/sessions")
async def get_sessions(request: Request) -> dict:
    """
    Récupérer les sessions actives de l'utilisateur
    """
    logger.debug("Endpoint get-sessions appelé")
    
    try:
        # Récupérer le token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token manquant"
            )
        
        token = auth_header.split(" ")[1]
        payload = TokenManager.verify_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide ou expiré"
            )
        
        user_id = payload.get("user_id")
        sessions = TokenManager.get_active_sessions(user_id)
        
        logger.debug(f"Sessions actives pour l'utilisateur {user_id}: {len(sessions)}")
        
        return {
            "sessions": sessions,
            "total": len(sessions)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des sessions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur"
        )

@router.post("/2fa/send")
async def send_2fa(request: Request) -> dict:
    """
    Envoyer un code 2FA via SMS
    """
    logger.debug("Endpoint 2fa/send appelé")
    
    try:
        # Récupérer le token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token manquant"
            )
        
        token = auth_header.split(" ")[1]
        payload = TokenManager.verify_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide ou expiré"
            )
        
        user_id = payload.get("user_id")
        username = payload.get("sub")
        
        # Récupérer le numéro de téléphone de l'utilisateur
        supabase = get_supabase()
        user_response = supabase.table("users").select("phone_number").eq("id", user_id).execute()
        
        if not user_response.data or not user_response.data[0].get("phone_number"):
            logger.warning(f"Numéro de téléphone manquant pour l'utilisateur: {username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Numéro de téléphone manquant"
            )
        
        phone_number = user_response.data[0]["phone_number"]
        
        # Envoyer le code 2FA
        success, message = TwoFactorAuth.send_2fa_code(user_id, phone_number, username)
        
        if not success:
            logger.error(f"Erreur lors de l'envoi du code 2FA: {message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=message
            )
        
        logger.info(f"Code 2FA envoyé pour l'utilisateur: {username}")
        
        return {"message": message}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du code 2FA: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur"
        )

@router.post("/2fa/verify")
async def verify_2fa(code: str, request: Request) -> dict:
    """
    Vérifier un code 2FA
    """
    logger.debug("Endpoint 2fa/verify appelé")
    
    try:
        # Récupérer le token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token manquant"
            )
        
        token = auth_header.split(" ")[1]
        payload = TokenManager.verify_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide ou expiré"
            )
        
        user_id = payload.get("user_id")
        username = payload.get("sub")
        
        # Vérifier le code
        valid, message = TwoFactorAuth.verify_2fa_code(user_id, code)
        
        if not valid:
            logger.warning(f"Code 2FA invalide pour l'utilisateur: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message
            )
        
        logger.info(f"Code 2FA vérifié pour l'utilisateur: {username}")
        
        return {"message": message}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du code 2FA: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur"
        )
