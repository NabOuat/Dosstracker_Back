from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from typing import List, Any, Optional, Dict
import os
from datetime import datetime
from pydantic import BaseModel

from app.core.deps import get_current_active_user, get_admin_user
from app.database import get_supabase
from app.models.sms import SMS, SMSCreate, SMSUpdate
from app.models.enums import StatutSMS, TypeSMS
from app.services.sms_service import sms_service

router = APIRouter(prefix="/sms", tags=["SMS"])

# Modèles pour les nouvelles fonctionnalités
class VerificationRequest(BaseModel):
    phone_number: str
    channel: str = "sms"

class VerificationCheck(BaseModel):
    phone_number: str
    code: str

class NotificationRequest(BaseModel):
    phone_number: str
    notification_type: str
    context: Dict[str, Any]

@router.get("/", response_model=List[SMS])
async def read_sms(
    skip: int = 0, 
    limit: int = 100,
    dossier_id: Optional[str] = Query(None, description="Filtrer par ID de dossier"),
    type_sms: Optional[TypeSMS] = Query(None, description="Filtrer par type de SMS"),
    statut: Optional[StatutSMS] = Query(None, description="Filtrer par statut"),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Récupère tous les SMS avec filtres optionnels
    """
    supabase = get_supabase()
    query = supabase.table("sms_log").select("*")
    
    # Appliquer les filtres
    if dossier_id:
        query = query.eq("dossier_id", dossier_id)
    
    if type_sms:
        query = query.eq("type_sms", type_sms)
    
    if statut:
        query = query.eq("statut", statut)
    
    # Ajouter la pagination et le tri
    query = query.range(skip, skip + limit - 1).order("created_at", desc=True)
    
    response = query.execute()
    
    return response.data

@router.post("/", response_model=SMS)
async def create_sms(
    sms_in: SMSCreate,
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Crée et envoie un nouveau SMS
    """
    supabase = get_supabase()
    
    # Vérifier si le dossier existe
    dossier = supabase.table("dossiers").select("*").eq("id", sms_in.dossier_id).execute()
    
    if not dossier.data or len(dossier.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé"
        )
    
    # Vérifier si le propriétaire existe
    proprietaire = supabase.table("proprietaires").select("*").eq("id", sms_in.proprietaire_id).execute()
    
    if not proprietaire.data or len(proprietaire.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propriétaire non trouvé"
        )
    
    # Préparer les données du SMS
    sms_data = sms_in.dict()
    sms_data["envoye_par_id"] = current_user["id"]
    sms_data["statut"] = "SIMULE"  # Par défaut, à changer si Twilio est configuré
    
    # Essayer d'envoyer le SMS via Twilio si configuré
    twilio_client = get_twilio_client()
    if twilio_client and TWILIO_PHONE_NUMBER:
        try:
            message = twilio_client.messages.create(
                body=sms_in.contenu_message,
                from_=TWILIO_PHONE_NUMBER,
                to=sms_in.numero_destinataire
            )
            
            sms_data["statut"] = "ENVOYE"
            sms_data["twilio_sid"] = message.sid
        except Exception as e:
            sms_data["statut"] = "ECHEC"
            sms_data["erreur"] = str(e)
    
    # Enregistrer le SMS dans la base de données
    response = supabase.table("sms_log").insert(sms_data).execute()
    
    if not response.data or len(response.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur lors de l'enregistrement du SMS"
        )
    
    return response.data[0]

@router.get("/{sms_id}", response_model=SMS)
async def read_sms_by_id(
    sms_id: str,
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Récupère un SMS par son ID
    """
    supabase = get_supabase()
    response = supabase.table("sms_log").select("*").eq("id", sms_id).execute()
    
    if not response.data or len(response.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SMS non trouvé"
        )
    
    return response.data[0]

@router.post("/{sms_id}/resend", response_model=SMS)
async def resend_sms(
    sms_id: str,
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Renvoie un SMS existant
    """
    supabase = get_supabase()
    
    # Récupérer le SMS
    sms = supabase.table("sms_log").select("*").eq("id", sms_id).execute()
    
    if not sms.data or len(sms.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SMS non trouvé"
        )
    
    sms_data = sms.data[0]
    
    # Créer un nouveau SMS avec les mêmes données
    new_sms = {
        "dossier_id": sms_data["dossier_id"],
        "proprietaire_id": sms_data["proprietaire_id"],
        "type_sms": sms_data["type_sms"],
        "numero_destinataire": sms_data["numero_destinataire"],
        "contenu_message": sms_data["contenu_message"],
        "envoye_par_id": current_user["id"],
        "statut": "SIMULE"  # Par défaut, à changer si Twilio est configuré
    }
    
    # Utiliser le service SMS pour envoyer le message
    result = sms_service.send_sms(
        to_number=sms_data["numero_destinataire"],
        message=sms_data["contenu_message"]
    )
    
    if result["success"]:
        new_sms["statut"] = "ENVOYE"
        new_sms["twilio_sid"] = result.get("message_sid", "")
    else:
        new_sms["statut"] = "ECHEC"
        new_sms["erreur"] = result.get("error", "Erreur inconnue")
    
    # Enregistrer le nouveau SMS dans la base de données
    response = supabase.table("sms_log").insert(new_sms).execute()
    
    if not response.data or len(response.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur lors du renvoi du SMS"
        )
    
    return response.data[0]


@router.post("/send-verification", status_code=status.HTTP_200_OK)
async def send_verification_code(
    request: VerificationRequest,
    current_user: dict = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Envoie un code de vérification via Twilio Verify
    """
    result = sms_service.send_verification_code(
        to_number=request.phone_number,
        channel=request.channel
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Erreur lors de l'envoi du code de vérification")
        )
    
    return {
        "message": "Code de vérification envoyé avec succès",
        "status": result.get("status"),
        "verification_sid": result.get("verification_sid")
    }


@router.post("/check-verification", status_code=status.HTTP_200_OK)
async def check_verification_code(
    request: VerificationCheck,
    current_user: dict = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Vérifie un code de vérification
    """
    result = sms_service.check_verification_code(
        to_number=request.phone_number,
        code=request.code
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Erreur lors de la vérification du code")
        )
    
    if not result.get("valid", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code de vérification invalide"
        )
    
    return {
        "message": "Code de vérification validé avec succès",
        "status": result.get("status")
    }


@router.post("/send-notification", status_code=status.HTTP_200_OK)
async def send_notification(
    request: NotificationRequest,
    current_user: dict = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Envoie une notification SMS basée sur un type prédéfini
    """
    result = sms_service.send_notification_sms(
        to_number=request.phone_number,
        notification_type=request.notification_type,
        context=request.context
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Erreur lors de l'envoi de la notification")
        )
    
    # Enregistrer la notification dans la base de données
    supabase = get_supabase()
    
    sms_data = {
        "type_sms": request.notification_type.upper(),
        "numero_destinataire": request.phone_number,
        "contenu_message": "Notification de type " + request.notification_type,
        "envoye_par_id": current_user["id"],
        "statut": "ENVOYE" if result["success"] else "ECHEC",
    }
    
    # Ajouter le dossier_id s'il est fourni dans le contexte
    if "numero" in request.context:
        # Rechercher le dossier par son numéro
        dossier_response = supabase.table("dossiers").select("id").eq("numero", request.context["numero"]).execute()
        if dossier_response.data and len(dossier_response.data) > 0:
            sms_data["dossier_id"] = dossier_response.data[0]["id"]
    
    # Enregistrer dans la base de données
    supabase.table("sms_log").insert(sms_data).execute()
    
    return {
        "message": "Notification envoyée avec succès",
        "status": result.get("status"),
        "message_sid": result.get("message_sid")
    }

@router.get("/dossier/{dossier_id}", response_model=List[SMS])
async def read_sms_by_dossier(
    dossier_id: str,
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Récupère tous les SMS pour un dossier spécifique
    """
    supabase = get_supabase()
    
    # Vérifier si le dossier existe
    dossier = supabase.table("dossiers").select("id").eq("id", dossier_id).execute()
    
    if not dossier.data or len(dossier.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé"
        )
    
    # Récupérer les SMS
    response = supabase.table("sms_log").select("*").eq("dossier_id", dossier_id).order("created_at", desc=True).execute()
    
    return response.data
