from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import datetime
from .enums import TypeSMS, StatutSMS

class SMSBase(BaseModel):
    dossier_id: UUID4
    proprietaire_id: UUID4
    type_sms: TypeSMS
    numero_destinataire: str
    contenu_message: str

class SMSCreate(SMSBase):
    pass

class SMSUpdate(BaseModel):
    statut: StatutSMS
    twilio_sid: Optional[str] = None
    erreur: Optional[str] = None

class SMS(SMSBase):
    id: UUID4
    statut: StatutSMS
    twilio_sid: Optional[str] = None
    erreur: Optional[str] = None
    envoye_par_id: Optional[UUID4] = None
    created_at: datetime

    class Config:
        from_attributes = True
