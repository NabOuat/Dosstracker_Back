from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from logger import get_logger
import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

# Charger les variables d'environnement
load_dotenv()

# Initialiser Sentry pour le monitoring (optionnel)
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
            environment=os.getenv("ENVIRONMENT", "development")
        )
except ImportError:
    pass

# Initialiser le logger
logger = get_logger()

# Créer l'application FastAPI
app = FastAPI(
    title="DosTracker API",
    description="API pour la gestion des dossiers fonciers",
    version="1.0.0"
)

# Initialiser le rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Trop de requêtes. Veuillez réessayer plus tard."}
    )

# Configuration CORS stricte
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Type"],
    max_age=3600,
)

# Point d'entrée racine
@app.get("/")
async def root():
    return {
        "message": "Bienvenue sur l'API DosTracker",
        "version": "1.0.0",
        "documentation": "/docs"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Endpoint pour vérifier la santé de l'API"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

# Importer les routers après la création de l'app
from app.api.v1.endpoints import users, dossiers, proprietaires, auth, sms, debug, auth_enhanced, admin, stats, corrections, apfr, service_dashboard, pieces_jointes

# Inclure les routers
app.include_router(auth.router, prefix="/api/v1", tags=["Authentification"])
app.include_router(auth_enhanced.router, prefix="/api/v1", tags=["Authentification Améliorée"])
app.include_router(users.router, prefix="/api/v1", tags=["Utilisateurs"])
app.include_router(dossiers.router, prefix="/api/v1", tags=["Dossiers"])
app.include_router(proprietaires.router, prefix="/api/v1", tags=["Propriétaires"])
app.include_router(sms.router, prefix="/api/v1", tags=["SMS"])
app.include_router(corrections.router, prefix="/api/v1", tags=["Corrections"])
app.include_router(apfr.router, prefix="/api/v1", tags=["APFR"])
app.include_router(pieces_jointes.router, prefix="/api/v1", tags=["Pièces Jointes"])
app.include_router(service_dashboard.router, prefix="/api/v1", tags=["Service Dashboard"])
app.include_router(stats.router, prefix="/api/v1", tags=["Statistiques"])
app.include_router(admin.router, prefix="/api/v1", tags=["Administration"])
app.include_router(debug.router, prefix="/api/v1", tags=["Debug"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
