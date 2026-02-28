from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from logger import get_logger

# Charger les variables d'environnement
load_dotenv()

# Initialiser le logger
logger = get_logger()

# Créer l'application FastAPI
app = FastAPI(
    title="DosTracker API",
    description="API pour la gestion des dossiers fonciers",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À remplacer par les domaines autorisés en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Point d'entrée racine
@app.get("/")
async def root():
    return {
        "message": "Bienvenue sur l'API DosTracker",
        "version": "1.0.0",
        "documentation": "/docs"
    }

# Importer les routers après la création de l'app
from app.api.v1.endpoints import users, dossiers, proprietaires, auth, sms, debug, auth_enhanced, admin

# Inclure les routers
app.include_router(auth.router, prefix="/api/v1", tags=["Authentification"])
app.include_router(auth_enhanced.router, prefix="/api/v1", tags=["Authentification Améliorée"])
app.include_router(users.router, prefix="/api/v1", tags=["Utilisateurs"])
app.include_router(dossiers.router, prefix="/api/v1", tags=["Dossiers"])
app.include_router(proprietaires.router, prefix="/api/v1", tags=["Propriétaires"])
app.include_router(sms.router, prefix="/api/v1", tags=["SMS"])
app.include_router(admin.router, prefix="/api/v1", tags=["Administration"])
app.include_router(debug.router, prefix="/api/v1", tags=["Debug"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
