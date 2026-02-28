from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: str
    username: str
    nom_complet: str
    service_id: int
    service: str

class TokenRefresh(BaseModel):
    refresh_token: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    service_id: Optional[int] = None
    nom_complet: Optional[str] = None
    service: Optional[str] = None
