import os
import requests
from dotenv import load_dotenv
from typing import Dict, Any
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class SMSService:
    """Envoi SMS via TextBee (prioritaire) ou Twilio (fallback)."""

    def __init__(self):
        # WhatsApp Cloud API (Meta) — prioritaire
        self.whatsapp_token = os.getenv("WHATSAPP_TOKEN")
        self.whatsapp_phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

        # TextBee — fallback
        self.textbee_api_key = os.getenv("TEXTBEE_API_KEY")
        self.textbee_device_id = os.getenv("TEXTBEE_DEVICE_ID")

        # Twilio — fallback / vérification OTP uniquement
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        self.twilio_verify_sid = os.getenv("TWILIO_VERIFY_SID")
        self._twilio_client = None

        if self.whatsapp_token and self.whatsapp_phone_number_id:
            logger.info("Provider: WhatsApp Cloud API (Meta)")
        elif self.textbee_api_key and self.textbee_device_id:
            logger.info("Provider: TextBee")
        elif self.twilio_account_sid and self.twilio_auth_token:
            logger.info("Provider: Twilio")
        else:
            logger.warning("Aucun provider configure — messages simules.")

    # ── WhatsApp Cloud API (Meta) ──────────────────────────────────────────────

    def _send_via_whatsapp(self, to_number: str, message: str) -> Dict[str, Any]:
        # Supprimer le + pour l'API Meta (ex: +2250576610155 → 2250576610155)
        to_number_clean = to_number.lstrip('+')
        url = f"https://graph.facebook.com/v19.0/{self.whatsapp_phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number_clean,
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }
        try:
            resp = requests.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.whatsapp_token}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            data = resp.json()
            if resp.status_code == 200 and data.get("messages"):
                msg_id = data["messages"][0].get("id")
                logger.info(f"WhatsApp envoye a {to_number}. ID: {msg_id}")
                return {"success": True, "provider": "whatsapp", "message_id": msg_id, "to": to_number}
            logger.error(f"WhatsApp erreur {resp.status_code}: {data}")
            error_msg = data.get("error", {}).get("message", str(data))
            return {"success": False, "provider": "whatsapp", "error": error_msg, "to": to_number}
        except Exception as e:
            logger.error(f"WhatsApp exception: {e}")
            return {"success": False, "provider": "whatsapp", "error": str(e), "to": to_number}

    # ── TextBee ────────────────────────────────────────────────────────────────

    def _send_via_textbee(self, to_number: str, message: str) -> Dict[str, Any]:
        if not to_number.startswith('+'):
            to_number = f"+{to_number}"
        url = f"https://api.textbee.dev/api/v1/gateway/devices/{self.textbee_device_id}/sendSMS"
        try:
            resp = requests.post(
                url,
                json={"recipients": [to_number], "message": message},
                headers={"x-api-key": self.textbee_api_key},
                timeout=15,
            )
            data = resp.json()
            if resp.status_code in (200, 201) and data.get("success"):
                logger.info(f"TextBee SMS envoye a {to_number}")
                return {"success": True, "provider": "textbee", "to": to_number}
            logger.error(f"TextBee erreur {resp.status_code}: {data}")
            return {"success": False, "provider": "textbee", "error": str(data), "to": to_number}
        except Exception as e:
            logger.error(f"TextBee exception: {e}")
            return {"success": False, "provider": "textbee", "error": str(e), "to": to_number}

    # ── Twilio ─────────────────────────────────────────────────────────────────

    def _get_twilio_client(self):
        if self._twilio_client is None:
            from twilio.rest import Client
            self._twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
        return self._twilio_client

    def _send_via_twilio(self, to_number: str, message: str) -> Dict[str, Any]:
        if not to_number.startswith('+'):
            to_number = f"+{to_number}"
        try:
            client = self._get_twilio_client()
            msg = client.messages.create(
                body=message,
                from_=self.twilio_phone_number,
                to=to_number,
            )
            logger.info(f"Twilio SMS envoye. SID: {msg.sid}")
            return {"success": True, "provider": "twilio", "message_sid": msg.sid, "to": to_number}
        except Exception as e:
            logger.error(f"Twilio erreur: {e}")
            return {"success": False, "provider": "twilio", "error": str(e), "to": to_number}

    # ── Vérification OTP (Twilio Verify uniquement) ────────────────────────────

    def send_verification_code(self, to_number: str, channel: str = "sms") -> Dict[str, Any]:
        if not self.twilio_account_sid or not self.twilio_verify_sid:
            return {"success": False, "error": "Configuration Twilio Verify manquante"}
        if not to_number.startswith('+'):
            to_number = f"+{to_number}"
        try:
            verification = self._get_twilio_client().verify \
                .v2.services(self.twilio_verify_sid) \
                .verifications.create(to=to_number, channel=channel)
            return {"success": True, "verification_sid": verification.sid, "status": verification.status, "to": to_number}
        except Exception as e:
            return {"success": False, "error": str(e), "to": to_number}

    def check_verification_code(self, to_number: str, code: str) -> Dict[str, Any]:
        if not self.twilio_account_sid or not self.twilio_verify_sid:
            return {"success": False, "error": "Configuration Twilio Verify manquante"}
        if not to_number.startswith('+'):
            to_number = f"+{to_number}"
        try:
            check = self._get_twilio_client().verify \
                .v2.services(self.twilio_verify_sid) \
                .verification_checks.create(to=to_number, code=code)
            return {"success": True, "valid": check.status == "approved", "status": check.status, "to": to_number}
        except Exception as e:
            return {"success": False, "error": str(e), "to": to_number}

    # ── Point d'entrée principal ───────────────────────────────────────────────

    def send_sms(self, to_number: str, message: str) -> Dict[str, Any]:
        """Envoie via WhatsApp (prioritaire), TextBee, ou Twilio en fallback."""
        if self.whatsapp_token and self.whatsapp_phone_number_id:
            return self._send_via_whatsapp(to_number, message)
        if self.textbee_api_key and self.textbee_device_id:
            return self._send_via_textbee(to_number, message)
        if self.twilio_account_sid and self.twilio_auth_token:
            return self._send_via_twilio(to_number, message)
        logger.warning("Message simule (aucun provider configure)")
        return {"success": False, "error": "Aucun provider configure"}

    def send_notification_sms(self, to_number: str, notification_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Templates sans accents — GSM 7-bit, 1 segment (<160 chars)
        templates = {
            "non_conforme": "Dossier N {numero}: NON CONFORME. Motifs: {motifs}. Rapprochez-vous du SERVICE SCVAA.",
            "finalise": "Dossier N {numero}: finalise. Titre Foncier N {titre} enregistre a la Conservation Fonciere.",
            "en_cours": "Dossier N {numero}: en cours de traitement par le service {service}.",
        }
        if notification_type not in templates:
            return {"success": False, "error": f"Type de notification inconnu: {notification_type}"}
        try:
            message = templates[notification_type].format(**context)
            return self.send_sms(to_number, message)
        except KeyError as e:
            return {"success": False, "error": f"Donnees manquantes: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


sms_service = SMSService()
