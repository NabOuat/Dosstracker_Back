from pydantic import BaseModel, EmailStr, Field, UUID4
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    nom_complet: str
    username: str
    email: EmailStr
    service_id: int

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    nom_complet: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    service_id: Optional[int] = None

class UserInDB(UserBase):
    id: UUID4
    hashed_password: str
    is_active: bool = True
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class User(UserBase):
    id: UUID4
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    service: Optional[str] = None  # Nom du service

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    nom_complet: str
    service_id: int
    service: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    service_id: Optional[int] = None
