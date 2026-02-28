from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Optional
import os
from datetime import datetime

from app.database import get_supabase
from app.models.user import TokenData
from .security import SECRET_KEY, ALGORITHM

# Point de terminaison pour l'authentification
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Valide le token JWT et récupère l'utilisateur correspondant
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Décodage du token JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        service_id: int = payload.get("service_id")
        
        if username is None or user_id is None:
            raise credentials_exception
            
        token_data = TokenData(username=username, user_id=user_id, service_id=service_id)
    except JWTError:
        raise credentials_exception
        
    # Récupérer l'utilisateur depuis Supabase
    supabase = get_supabase()
    user_response = supabase.table("users").select("*").eq("id", token_data.user_id).execute()
    
    if user_response.data is None or len(user_response.data) == 0:
        raise credentials_exception
        
    user = user_response.data[0]
    
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utilisateur inactif"
        )
        
    return user

async def get_current_active_user(current_user = Depends(get_current_user)):
    """
    Vérifie que l'utilisateur est actif
    """
    if not current_user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utilisateur inactif"
        )
    return current_user

def check_service_permission(required_services: list):
    """
    Crée un dépendance pour vérifier si l'utilisateur appartient à un service autorisé
    """
    async def service_permission(current_user = Depends(get_current_active_user)):
        if current_user["service_id"] not in required_services and current_user["service_id"] != 4:  # 4 = ADMIN
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès non autorisé pour ce service"
            )
        return current_user
    return service_permission

# Dépendances pour chaque service
get_courrier_user = check_service_permission([1])  # SERVICE_COURRIER
get_spfei_user = check_service_permission([2])     # SERVICE_SPFEI
get_scvaa_user = check_service_permission([3])     # SERVICE_SCVAA
get_admin_user = check_service_permission([4])     # ADMIN
