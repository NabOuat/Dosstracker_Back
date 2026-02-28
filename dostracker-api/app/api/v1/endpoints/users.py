from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Any
from pydantic import BaseModel

from app.core.deps import get_admin_user, get_current_active_user
from app.core.security import get_password_hash, verify_password
from app.database import get_supabase
from app.models.user import User, UserCreate, UserUpdate
from logger import get_logger

logger = get_logger()

# Modèles pour les endpoints supplémentaires
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class UserPreferences(BaseModel):
    notifications: dict = {}
    channels: dict = {}
    security: dict = {}

class FirstLoginResponse(BaseModel):
    is_first_login: bool
    message: str = ""

router = APIRouter(prefix="/users", tags=["Utilisateurs"])

@router.get("/", response_model=List[User])
async def read_users(
    skip: int = 0, 
    limit: int = 100,
    current_user: dict = Depends(get_admin_user)
) -> Any:
    """
    Récupère tous les utilisateurs (admin uniquement)
    """
    supabase = get_supabase()
    response = supabase.table("users").select("*, services(nom, libelle)").range(skip, skip + limit).execute()
    
    # Transformer les données pour correspondre au modèle User
    users = []
    for user in response.data:
        user_data = {**user}
        if "services" in user_data and user_data["services"]:
            user_data["service"] = user_data["services"]["libelle"]
        users.append(user_data)
    
    return users

@router.post("/", response_model=User)
async def create_user(
    user_in: UserCreate,
    current_user: dict = Depends(get_admin_user)
) -> Any:
    """
    Crée un nouvel utilisateur (admin uniquement)
    """
    supabase = get_supabase()
    
    # Vérifier si l'utilisateur existe déjà
    user_exists = supabase.table("users").select("id").or_(f"username.eq.{user_in.username},email.eq.{user_in.email}").execute()
    
    if user_exists.data and len(user_exists.data) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nom d'utilisateur ou email déjà utilisé"
        )
    
    # Créer l'utilisateur
    hashed_password = get_password_hash(user_in.password)
    user_data = user_in.dict()
    user_data.pop("password")
    user_data["hashed_password"] = hashed_password
    
    response = supabase.table("users").insert(user_data).execute()
    
    if not response.data or len(response.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur lors de la création de l'utilisateur"
        )
    
    # Récupérer l'utilisateur créé avec les informations du service
    created_user = supabase.table("users").select("*, services(nom, libelle)").eq("id", response.data[0]["id"]).execute()
    
    if created_user.data and len(created_user.data) > 0:
        user_data = created_user.data[0]
        if "services" in user_data and user_data["services"]:
            user_data["service"] = user_data["services"]["libelle"]
        return user_data
    
    return response.data[0]

@router.get("/me", response_model=User)
async def read_user_me(
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Récupère l'utilisateur connecté
    """
    # Récupérer les informations du service
    supabase = get_supabase()
    user_with_service = supabase.table("users").select("*, services(nom, libelle)").eq("id", current_user["id"]).execute()
    
    if user_with_service.data and len(user_with_service.data) > 0:
        user_data = user_with_service.data[0]
        if "services" in user_data and user_data["services"]:
            user_data["service"] = user_data["services"]["libelle"]
        return user_data
    
    return current_user

@router.get("/{user_id}", response_model=User)
async def read_user(
    user_id: str,
    current_user: dict = Depends(get_admin_user)
) -> Any:
    """
    Récupère un utilisateur par son ID (admin uniquement)
    """
    supabase = get_supabase()
    response = supabase.table("users").select("*, services(nom, libelle)").eq("id", user_id).execute()
    
    if not response.data or len(response.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    user_data = response.data[0]
    if "services" in user_data and user_data["services"]:
        user_data["service"] = user_data["services"]["libelle"]
    
    return user_data

@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    current_user: dict = Depends(get_admin_user)
) -> Any:
    """
    Met à jour un utilisateur (admin uniquement)
    """
    supabase = get_supabase()
    
    # Vérifier si l'utilisateur existe
    user_exists = supabase.table("users").select("id").eq("id", user_id).execute()
    
    if not user_exists.data or len(user_exists.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    # Préparer les données à mettre à jour
    update_data = user_in.dict(exclude_unset=True)
    
    # Hasher le mot de passe si fourni
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    # Mettre à jour l'utilisateur
    response = supabase.table("users").update(update_data).eq("id", user_id).execute()
    
    if not response.data or len(response.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur lors de la mise à jour de l'utilisateur"
        )
    
    # Récupérer l'utilisateur mis à jour avec les informations du service
    updated_user = supabase.table("users").select("*, services(nom, libelle)").eq("id", user_id).execute()
    
    if updated_user.data and len(updated_user.data) > 0:
        user_data = updated_user.data[0]
        if "services" in user_data and user_data["services"]:
            user_data["service"] = user_data["services"]["libelle"]
        return user_data
    
    return response.data[0]

@router.put("/me", response_model=User)
async def update_user_me(
    user_in: UserUpdate,
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Met à jour le profil de l'utilisateur connecté
    """
    logger.debug(f"Mise à jour du profil pour l'utilisateur: {current_user['username']}")
    supabase = get_supabase()
    
    # Préparer les données à mettre à jour
    update_data = user_in.dict(exclude_unset=True)
    
    # Hasher le mot de passe si fourni
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    # Mettre à jour l'utilisateur
    response = supabase.table("users").update(update_data).eq("id", current_user["id"]).execute()
    
    if not response.data or len(response.data) == 0:
        logger.error(f"Erreur lors de la mise à jour du profil pour {current_user['username']}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur lors de la mise à jour du profil"
        )
    
    # Récupérer l'utilisateur mis à jour avec les informations du service
    updated_user = supabase.table("users").select("*, services(nom, libelle)").eq("id", current_user["id"]).execute()
    
    if updated_user.data and len(updated_user.data) > 0:
        user_data = updated_user.data[0]
        if "services" in user_data and user_data["services"]:
            user_data["service"] = user_data["services"]["libelle"]
        logger.info(f"Profil mis à jour avec succès pour {current_user['username']}")
        return user_data
    
    return response.data[0]

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_active_user)
) -> dict:
    """
    Change le mot de passe de l'utilisateur connecté
    """
    logger.debug(f"Changement de mot de passe pour l'utilisateur: {current_user['username']}")
    supabase = get_supabase()
    
    # Récupérer l'utilisateur actuel
    user_response = supabase.table("users").select("hashed_password").eq("id", current_user["id"]).execute()
    
    if not user_response.data or len(user_response.data) == 0:
        logger.error(f"Utilisateur non trouvé: {current_user['username']}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    user = user_response.data[0]
    
    # Vérifier le mot de passe actuel
    if not verify_password(password_data.current_password, user["hashed_password"]):
        logger.warning(f"Mot de passe actuel incorrect pour {current_user['username']}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mot de passe actuel incorrect"
        )
    
    # Hasher le nouveau mot de passe
    new_hashed_password = get_password_hash(password_data.new_password)
    
    # Mettre à jour le mot de passe
    response = supabase.table("users").update({
        "hashed_password": new_hashed_password
    }).eq("id", current_user["id"]).execute()
    
    if not response.data or len(response.data) == 0:
        logger.error(f"Erreur lors du changement de mot de passe pour {current_user['username']}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur lors du changement de mot de passe"
        )
    
    logger.info(f"Mot de passe changé avec succès pour {current_user['username']}")
    return {"message": "Mot de passe changé avec succès"}

@router.get("/preferences")
async def get_user_preferences(
    current_user: dict = Depends(get_current_active_user)
) -> dict:
    """
    Récupère les préférences de l'utilisateur connecté
    """
    logger.debug(f"Récupération des préférences pour l'utilisateur: {current_user['username']}")
    supabase = get_supabase()
    
    # Récupérer les préférences depuis la table user_preferences
    response = supabase.table("user_preferences").select("*").eq("user_id", current_user["id"]).execute()
    
    if response.data and len(response.data) > 0:
        logger.debug(f"Préférences trouvées pour {current_user['username']}")
        return response.data[0]
    
    # Retourner les préférences par défaut si aucune n'existe
    logger.debug(f"Pas de préférences trouvées, retour des valeurs par défaut")
    return {
        "user_id": current_user["id"],
        "notifications": {},
        "channels": {},
        "security": {}
    }

@router.put("/preferences")
async def update_user_preferences(
    preferences: UserPreferences,
    current_user: dict = Depends(get_current_active_user)
) -> dict:
    """
    Met à jour les préférences de l'utilisateur connecté
    """
    logger.debug(f"Mise à jour des préférences pour l'utilisateur: {current_user['username']}")
    supabase = get_supabase()
    
    # Vérifier si les préférences existent
    existing = supabase.table("user_preferences").select("id").eq("user_id", current_user["id"]).execute()
    
    preference_data = {
        "user_id": current_user["id"],
        "notifications": preferences.notifications,
        "channels": preferences.channels,
        "security": preferences.security
    }
    
    if existing.data and len(existing.data) > 0:
        # Mettre à jour les préférences existantes
        response = supabase.table("user_preferences").update(preference_data).eq("user_id", current_user["id"]).execute()
    else:
        # Créer les préférences
        response = supabase.table("user_preferences").insert(preference_data).execute()
    
    if not response.data or len(response.data) == 0:
        logger.error(f"Erreur lors de la mise à jour des préférences pour {current_user['username']}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur lors de la mise à jour des préférences"
        )
    
    logger.info(f"Préférences mises à jour avec succès pour {current_user['username']}")
    return response.data[0]

@router.get("/first-login/check", response_model=FirstLoginResponse)
async def check_first_login(
    current_user: dict = Depends(get_current_active_user)
) -> dict:
    """
    Vérifie si c'est la première connexion de l'utilisateur
    """
    logger.debug(f"Vérification de la première connexion pour {current_user['username']}")
    
    # Si last_login est None, c'est la première connexion
    is_first_login = current_user.get("last_login") is None
    
    logger.info(f"Première connexion pour {current_user['username']}: {is_first_login}")
    
    return {
        "is_first_login": is_first_login,
        "message": "Veuillez changer votre mot de passe pour sécuriser votre compte" if is_first_login else ""
    }

@router.post("/first-login/complete")
async def complete_first_login(
    current_user: dict = Depends(get_current_active_user)
) -> dict:
    """
    Marque la première connexion comme complétée
    """
    logger.debug(f"Marquage de la première connexion comme complétée pour {current_user['username']}")
    supabase = get_supabase()
    
    # Mettre à jour le timestamp last_login si ce n'est pas déjà fait
    response = supabase.table("users").update({
        "last_login": "now()"
    }).eq("id", current_user["id"]).execute()
    
    if not response.data or len(response.data) == 0:
        logger.error(f"Erreur lors de la mise à jour de last_login pour {current_user['username']}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur lors de la mise à jour du profil"
        )
    
    logger.info(f"Première connexion marquée comme complétée pour {current_user['username']}")
    return {"message": "Première connexion complétée"}
