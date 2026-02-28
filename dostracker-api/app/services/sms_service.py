from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import os
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import logging

# Charger les variables d'environnement
load_dotenv()

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SMSService:
    """Service pour gérer l'envoi de SMS et les vérifications via Twilio"""
    
    def __init__(self):
        """Initialise le service SMS avec les identifiants Twilio"""
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.verify_sid = os.getenv("TWILIO_VERIFY_SID")
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        if not all([self.account_sid, self.auth_token, self.verify_sid]):
            logger.warning("Configuration Twilio incomplète. Certaines fonctionnalités SMS peuvent ne pas fonctionner.")
        
        self.client = Client(self.account_sid, self.auth_token) if self.account_sid and self.auth_token else None
    
    def send_sms(self, to_number: str, message: str) -> Dict[str, Any]:
        """
        Envoie un SMS à un numéro spécifié
        
        Args:
            to_number: Numéro de téléphone du destinataire (format E.164, ex: +2250576610155)
            message: Contenu du message à envoyer
            
        Returns:
            Dict contenant les informations sur le message envoyé ou l'erreur
        """
        if not self.client:
            logger.error("Client Twilio non initialisé. Impossible d'envoyer le SMS.")
            return {"success": False, "error": "Configuration Twilio manquante"}
        
        try:
            # Normaliser le numéro de téléphone si nécessaire
            if not to_number.startswith('+'):
                to_number = f"+{to_number}"
                
            # Envoyer le SMS
            message = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to_number
            )
            
            logger.info(f"SMS envoyé avec succès. SID: {message.sid}")
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status,
                "to": to_number
            }
            
        except TwilioRestException as e:
            logger.error(f"Erreur lors de l'envoi du SMS: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "code": e.code,
                "to": to_number
            }
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'envoi du SMS: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "to": to_number
            }
    
    def send_verification_code(self, to_number: str, channel: str = "sms") -> Dict[str, Any]:
        """
        Envoie un code de vérification via le service Twilio Verify
        
        Args:
            to_number: Numéro de téléphone du destinataire (format E.164)
            channel: Canal d'envoi ('sms' ou 'call')
            
        Returns:
            Dict contenant les informations sur la vérification ou l'erreur
        """
        if not self.client or not self.verify_sid:
            logger.error("Client Twilio ou SID de vérification non initialisé.")
            return {"success": False, "error": "Configuration Twilio Verify manquante"}
        
        try:
            # Normaliser le numéro de téléphone si nécessaire
            if not to_number.startswith('+'):
                to_number = f"+{to_number}"
                
            # Envoyer le code de vérification
            verification = self.client.verify \
                .v2 \
                .services(self.verify_sid) \
                .verifications \
                .create(to=to_number, channel=channel)
            
            logger.info(f"Code de vérification envoyé. SID: {verification.sid}")
            return {
                "success": True,
                "verification_sid": verification.sid,
                "status": verification.status,
                "to": to_number,
                "channel": channel
            }
            
        except TwilioRestException as e:
            logger.error(f"Erreur lors de l'envoi du code de vérification: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "code": e.code,
                "to": to_number
            }
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'envoi du code de vérification: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "to": to_number
            }
    
    def check_verification_code(self, to_number: str, code: str) -> Dict[str, Any]:
        """
        Vérifie un code de vérification
        
        Args:
            to_number: Numéro de téléphone (format E.164)
            code: Code de vérification reçu par l'utilisateur
            
        Returns:
            Dict contenant le résultat de la vérification ou l'erreur
        """
        if not self.client or not self.verify_sid:
            logger.error("Client Twilio ou SID de vérification non initialisé.")
            return {"success": False, "error": "Configuration Twilio Verify manquante"}
        
        try:
            # Normaliser le numéro de téléphone si nécessaire
            if not to_number.startswith('+'):
                to_number = f"+{to_number}"
                
            # Vérifier le code
            verification_check = self.client.verify \
                .v2 \
                .services(self.verify_sid) \
                .verification_checks \
                .create(to=to_number, code=code)
            
            is_valid = verification_check.status == "approved"
            
            logger.info(f"Vérification du code: {verification_check.status}")
            return {
                "success": True,
                "valid": is_valid,
                "status": verification_check.status,
                "to": to_number
            }
            
        except TwilioRestException as e:
            logger.error(f"Erreur lors de la vérification du code: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "code": e.code,
                "to": to_number
            }
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la vérification du code: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "to": to_number
            }
    
    def send_notification_sms(self, to_number: str, notification_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envoie un SMS de notification basé sur un type prédéfini
        
        Args:
            to_number: Numéro de téléphone du destinataire (format E.164)
            notification_type: Type de notification ('non_conforme', 'finalise', etc.)
            context: Données contextuelles pour personnaliser le message
            
        Returns:
            Dict contenant les informations sur le message envoyé ou l'erreur
        """
        # Modèles de messages prédéfinis
        templates = {
            "non_conforme": "Dossier N° {numero} : Votre dossier a été jugé NON CONFORME. Motifs : {motifs}. Veuillez vous rapprocher du SERVICE SCVAA pour effectuer les corrections nécessaires.",
            "finalise": "Dossier N° {numero} : Votre dossier foncier a été finalisé avec succès. Titre Foncier N° {titre}. Votre dossier est désormais enregistré à la Conservation Foncière.",
            "en_cours": "Dossier N° {numero} : Votre dossier est en cours de traitement par le service {service}. Nous vous tiendrons informé de son avancement."
        }
        
        # Vérifier si le type de notification est valide
        if notification_type not in templates:
            logger.error(f"Type de notification inconnu: {notification_type}")
            return {"success": False, "error": f"Type de notification inconnu: {notification_type}"}
        
        try:
            # Générer le message à partir du template et du contexte
            message = templates[notification_type].format(**context)
            
            # Envoyer le SMS
            return self.send_sms(to_number, message)
            
        except KeyError as e:
            logger.error(f"Données manquantes pour le template '{notification_type}': {str(e)}")
            return {"success": False, "error": f"Données manquantes: {str(e)}"}
        except Exception as e:
            logger.error(f"Erreur lors de la génération du message: {str(e)}")
            return {"success": False, "error": str(e)}


# Instance singleton du service
sms_service = SMSService()
