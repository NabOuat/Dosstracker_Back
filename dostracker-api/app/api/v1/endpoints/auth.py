from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field
from jose import jwt, JWTError
from datetime import datetime
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import Any
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from logger import get_logger

from app.core.security import SECRET_KEY, ALGORITHM, get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import get_supabase
from app.models.user import Token, UserLogin
from app.services.email_service import email_service

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


# ---------------------------------------------------------------------------
# Réinitialisation de mot de passe (token JWT stateless, usage unique)
# ---------------------------------------------------------------------------
RESET_TOKEN_MINUTES = 30


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class TokenIn(BaseModel):
    token: str


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)


def _create_reset_token(user: dict) -> str:
    # "pwd" = empreinte du hash actuel : le token devient invalide dès que le mot de passe change
    return jwt.encode(
        {
            "sub": str(user["id"]),
            "type": "reset",
            "pwd": user["hashed_password"][-12:],
            "exp": datetime.utcnow() + timedelta(minutes=RESET_TOKEN_MINUTES),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def _user_from_reset_token(token: str) -> dict:
    invalid = HTTPException(status_code=400, detail="Lien invalide ou expiré.")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise invalid
    if payload.get("type") != "reset":
        raise invalid
    res = get_supabase().table("users").select("id, username, hashed_password").eq("id", payload["sub"]).execute()
    if not res.data or res.data[0]["hashed_password"][-12:] != payload.get("pwd"):
        raise invalid
    return res.data[0]


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordIn, background: BackgroundTasks) -> dict:
    """Envoie un lien de réinitialisation. Réponse identique que l'email existe ou non (anti-énumération)."""
    res = get_supabase().table("users").select("id, username, nom_complet, email, hashed_password").eq("email", data.email).execute()
    if res.data:
        user = res.data[0]
        front = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        link = f"{front}/reset-password/{_create_reset_token(user)}"
        html = (
            f"<p>Bonjour {user.get('nom_complet') or user['username']},</p>"
            f"<p>Une réinitialisation de votre mot de passe DosTracker a été demandée. "
            f"Ce lien est valable {RESET_TOKEN_MINUTES} minutes :</p>"
            f'<p><a href="{link}">Réinitialiser mon mot de passe</a></p>'
            f"<p>Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.</p>"
        )
        background.add_task(email_service.send, user["email"], "DosTracker — Réinitialisation du mot de passe", html, f"Lien : {link}")
    return {"message": "Si cette adresse est connue, un email de réinitialisation vient d'être envoyé."}


@router.post("/validate-reset-token")
async def validate_reset_token(data: TokenIn) -> dict:
    user = _user_from_reset_token(data.token)
    return {"valid": True, "username": user["username"]}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordIn) -> dict:
    user = _user_from_reset_token(data.token)
    get_supabase().table("users").update({"hashed_password": get_password_hash(data.new_password)}).eq("id", user["id"]).execute()
    logger.info(f"Mot de passe réinitialisé pour {user['username']}")
    return {"message": "Mot de passe réinitialisé avec succès."}
