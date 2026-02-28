from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import Any
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from logger import get_logger

from app.core.security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import get_supabase
from app.models.user import Token, UserLogin

logger = get_logger()

router = APIRouter(prefix="/auth", tags=["Authentification"])

@router.post("/login", response_model=Token)
async def login_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    """
    Authentification OAuth2 avec username et password
    """
    logger.info(f"Tentative de connexion pour l'utilisateur: {form_data.username}")
    
    try:
        # Récupérer l'utilisateur depuis Supabase
        supabase = get_supabase()
        logger.debug(f"Connexion à Supabase établie")
        
        logger.debug(f"Tentative de requête: table='users', colonne='username', valeur='{form_data.username}'")
        user_response = supabase.table("users").select("*, services(nom, libelle)").eq("username", form_data.username).execute()
        logger.debug(f"Réponse Supabase reçue pour l'utilisateur {form_data.username}")
        logger.debug(f"Données reçues: {user_response.data}")
        logger.debug(f"Nombre d'utilisateurs trouvés: {len(user_response.data) if user_response.data else 0}")
        
        if user_response.data is None or len(user_response.data) == 0:
            logger.warning(f"Utilisateur non trouvé: {form_data.username}")
            logger.debug(f"Tentative de requête alternative sans jointure...")
            # Essayer sans la jointure pour diagnostiquer
            user_response_alt = supabase.table("users").select("*").eq("username", form_data.username).execute()
            logger.debug(f"Réponse alternative: {user_response_alt.data}")
            
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
        
        # Créer le token d'accès
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # NE PAS mettre à jour last_login ici - cela sera fait après la première connexion
        # pour permettre au frontend de détecter la première connexion
        logger.debug(f"Saut de la mise à jour de last_login pour permettre la détection de première connexion")
        
        # Récupérer le nom du service
        service_nom = user["services"]["nom"] if user["services"] else ""
        service_libelle = user["services"]["libelle"] if user["services"] else ""
        
        logger.info(f"Connexion réussie pour l'utilisateur: {form_data.username}")
        
        return {
            "access_token": create_access_token(
                subject=user["username"],
                user_id=user["id"],
                service_id=user["service_id"],
                nom_complet=user["nom_complet"],
                service=service_libelle
            ),
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
async def refresh_token(current_token: Token) -> Any:
    """
    Rafraîchit un token d'accès
    """
    # Créer un nouveau token avec une nouvelle date d'expiration
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    return {
        "access_token": create_access_token(
            subject=current_token.username,
            user_id=current_token.user_id,
            service_id=current_token.service_id,
            nom_complet=current_token.nom_complet,
            service=current_token.service,
            expires_delta=access_token_expires
        ),
        "token_type": "bearer",
        "user_id": current_token.user_id,
        "username": current_token.username,
        "nom_complet": current_token.nom_complet,
        "service_id": current_token.service_id,
        "service": current_token.service
    }
