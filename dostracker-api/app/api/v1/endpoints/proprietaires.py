from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Any, Optional

from app.core.deps import get_current_active_user
from app.database import get_supabase
from app.models.proprietaire import Proprietaire, ProprietaireCreate, ProprietaireUpdate

router = APIRouter(prefix="/proprietaires", tags=["Propriétaires"])

@router.get("/", response_model=List[Proprietaire])
async def read_proprietaires(
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = Query(None, description="Recherche par nom ou contact"),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Récupère tous les propriétaires avec pagination et recherche optionnelle
    """
    supabase = get_supabase()
    query = supabase.table("proprietaires").select("*")
    
    # Ajouter la recherche si spécifiée
    if search:
        query = query.or_(f"nom_complet.ilike.%{search}%,contact.ilike.%{search}%")
    
    # Ajouter la pagination
    query = query.range(skip, skip + limit - 1).order("created_at", desc=True)
    
    response = query.execute()
    
    return response.data

@router.post("/", response_model=Proprietaire)
async def create_proprietaire(
    proprietaire_in: ProprietaireCreate,
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Crée un nouveau propriétaire
    """
    supabase = get_supabase()
    
    # Vérifier si un propriétaire avec le même contact existe déjà
    existing = supabase.table("proprietaires").select("id").eq("contact", proprietaire_in.contact).execute()
    
    if existing.data and len(existing.data) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un propriétaire avec ce numéro de contact existe déjà"
        )
    
    # Créer le propriétaire
    response = supabase.table("proprietaires").insert(proprietaire_in.dict()).execute()
    
    if not response.data or len(response.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur lors de la création du propriétaire"
        )
    
    return response.data[0]

@router.get("/{proprietaire_id}", response_model=Proprietaire)
async def read_proprietaire(
    proprietaire_id: str,
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Récupère un propriétaire par son ID
    """
    supabase = get_supabase()
    response = supabase.table("proprietaires").select("*").eq("id", proprietaire_id).execute()
    
    if not response.data or len(response.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propriétaire non trouvé"
        )
    
    return response.data[0]

@router.put("/{proprietaire_id}", response_model=Proprietaire)
async def update_proprietaire(
    proprietaire_id: str,
    proprietaire_in: ProprietaireUpdate,
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Met à jour un propriétaire
    """
    supabase = get_supabase()
    
    # Vérifier si le propriétaire existe
    existing = supabase.table("proprietaires").select("id").eq("id", proprietaire_id).execute()
    
    if not existing.data or len(existing.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propriétaire non trouvé"
        )
    
    # Vérifier si le contact est déjà utilisé par un autre propriétaire
    if proprietaire_in.contact:
        contact_check = supabase.table("proprietaires").select("id").eq("contact", proprietaire_in.contact).neq("id", proprietaire_id).execute()
        
        if contact_check.data and len(contact_check.data) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce numéro de contact est déjà utilisé par un autre propriétaire"
            )
    
    # Mettre à jour le propriétaire
    update_data = proprietaire_in.dict(exclude_unset=True)
    response = supabase.table("proprietaires").update(update_data).eq("id", proprietaire_id).execute()
    
    if not response.data or len(response.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur lors de la mise à jour du propriétaire"
        )
    
    return response.data[0]

@router.get("/{proprietaire_id}/dossiers", response_model=List[dict])
async def read_proprietaire_dossiers(
    proprietaire_id: str,
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    Récupère tous les dossiers d'un propriétaire
    """
    supabase = get_supabase()
    
    # Vérifier si le propriétaire existe
    proprietaire = supabase.table("proprietaires").select("*").eq("id", proprietaire_id).execute()
    
    if not proprietaire.data or len(proprietaire.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propriétaire non trouvé"
        )
    
    # Récupérer les dossiers du propriétaire
    response = supabase.table("dossiers").select("*").eq("proprietaire_id", proprietaire_id).execute()
    
    return response.data
