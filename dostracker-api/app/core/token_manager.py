import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "votre_cle_secrete_tres_securisee_a_changer_en_production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Stockage en mémoire des tokens révoqués et des sessions actives
# En production, utiliser Redis ou une base de données
_revoked_tokens: set = set()
_active_sessions: Dict[str, List[Dict]] = {}

class TokenManager:
    """Gestionnaire de tokens et sessions"""
    
    @staticmethod
    def create_access_token(
        subject: str,
        user_id: str,
        service_id: int,
        nom_complet: str,
        service: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Créer un token d'accès JWT"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode = {
            "sub": subject,
            "user_id": user_id,
            "service_id": service_id,
            "nom_complet": nom_complet,
            "service": service,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(
        subject: str,
        user_id: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Créer un token de rafraîchissement"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode = {
            "sub": subject,
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict]:
        """Vérifier et décoder un token JWT"""
        try:
            # Vérifier si le token est révoqué
            if token in _revoked_tokens:
                return None
            
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def revoke_token(token: str):
        """Révoquer un token (logout)"""
        _revoked_tokens.add(token)
    
    @staticmethod
    def create_session(user_id: str, username: str, ip_address: str, user_agent: str) -> str:
        """Créer une nouvelle session"""
        session_id = f"{user_id}_{datetime.utcnow().timestamp()}"
        
        if user_id not in _active_sessions:
            _active_sessions[user_id] = []
        
        session = {
            "session_id": session_id,
            "username": username,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }
        
        _active_sessions[user_id].append(session)
        return session_id
    
    @staticmethod
    def get_active_sessions(user_id: str) -> List[Dict]:
        """Récupérer les sessions actives d'un utilisateur"""
        return _active_sessions.get(user_id, [])
    
    @staticmethod
    def invalidate_session(user_id: str, session_id: str):
        """Invalider une session spécifique"""
        if user_id in _active_sessions:
            _active_sessions[user_id] = [
                s for s in _active_sessions[user_id]
                if s["session_id"] != session_id
            ]
    
    @staticmethod
    def invalidate_all_sessions(user_id: str):
        """Invalider toutes les sessions d'un utilisateur"""
        if user_id in _active_sessions:
            _active_sessions[user_id] = []
    
    @staticmethod
    def update_session_activity(user_id: str, session_id: str):
        """Mettre à jour l'activité d'une session"""
        if user_id in _active_sessions:
            for session in _active_sessions[user_id]:
                if session["session_id"] == session_id:
                    session["last_activity"] = datetime.utcnow().isoformat()
                    break
