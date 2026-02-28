import os
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Stockage en mémoire des codes 2FA
# Format: {user_id: {"code": "123456", "expires_at": datetime, "attempts": 0}}
_2fa_codes: Dict[str, Dict] = {}

class TwoFactorAuth:
    """Gestionnaire d'authentification à deux facteurs via SMS"""
    
    @staticmethod
    def generate_code(length: int = 6) -> str:
        """Générer un code 2FA aléatoire"""
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def send_2fa_code(user_id: str, phone_number: str, username: str) -> tuple[bool, str]:
        """
        Envoyer un code 2FA via SMS
        Retourne (success: bool, message: str)
        """
        try:
            # Générer le code
            code = TwoFactorAuth.generate_code()
            
            # Stocker le code avec expiration (5 minutes)
            _2fa_codes[user_id] = {
                "code": code,
                "expires_at": datetime.utcnow() + timedelta(minutes=5),
                "attempts": 0,
                "phone_number": phone_number
            }
            
            # Envoyer via Twilio
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            message = client.messages.create(
                body=f"Votre code de vérification DosTracker est: {code}\nValide pendant 5 minutes.",
                from_=TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            
            return True, f"Code envoyé au {phone_number}"
        
        except Exception as e:
            return False, f"Erreur lors de l'envoi du code: {str(e)}"
    
    @staticmethod
    def verify_2fa_code(user_id: str, code: str) -> tuple[bool, str]:
        """
        Vérifier un code 2FA
        Retourne (valid: bool, message: str)
        """
        if user_id not in _2fa_codes:
            return False, "Aucun code 2FA en attente"
        
        code_data = _2fa_codes[user_id]
        
        # Vérifier l'expiration
        if datetime.utcnow() > code_data["expires_at"]:
            del _2fa_codes[user_id]
            return False, "Le code a expiré"
        
        # Vérifier le nombre de tentatives
        if code_data["attempts"] >= 3:
            del _2fa_codes[user_id]
            return False, "Trop de tentatives. Veuillez demander un nouveau code."
        
        # Vérifier le code
        if code != code_data["code"]:
            code_data["attempts"] += 1
            return False, f"Code incorrect. {3 - code_data['attempts']} tentatives restantes."
        
        # Code valide
        del _2fa_codes[user_id]
        return True, "Code vérifié avec succès"
    
    @staticmethod
    def get_2fa_status(user_id: str) -> bool:
        """Vérifier si un code 2FA est en attente"""
        return user_id in _2fa_codes
    
    @staticmethod
    def cancel_2fa(user_id: str):
        """Annuler un code 2FA en attente"""
        if user_id in _2fa_codes:
            del _2fa_codes[user_id]
