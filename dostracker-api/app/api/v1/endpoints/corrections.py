from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.core.deps import get_current_user
from app.database import get_supabase
from app.models.correction import (
    CorrectionDossier,
    CorrectionDossierCreate,
    CorrectionDossierUpdate
)
from app.models.user import User

router = APIRouter(prefix="/corrections", tags=["Corrections"])

@router.post("/", response_model=CorrectionDossier, status_code=status.HTTP_201_CREATED)
async def creer_correction_dossier(
    correction: CorrectionDossierCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Créer un retour de correction pour un dossier NON_CONFORME.
    
    - Accessible par SERVICE SCVAA uniquement
    - Change le statut du dossier à RETOUR_CORRECTION
    - Crée une trace avec agent_transmettant, date et éléments
    """
    
    # Vérifier que l'utilisateur est du SERVICE SCVAA
    if current_user["service_id"] != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le SERVICE SCVAA peut créer des retours de correction"
        )
    
    try:
        supabase = get_supabase()
        
        # Vérifier que le dossier existe et est NON_CONFORME
        dossier_check = supabase.table("dossiers").select("id, statut").eq("id", str(correction.dossier_id)).execute()
        
        if not dossier_check.data or len(dossier_check.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier non trouvé"
            )
        
        if dossier_check.data[0]["statut"] != "NON_CONFORME":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les dossiers NON_CONFORME peuvent être retournés en correction"
            )
        
        # Créer la correction
        correction_data = {
            "dossier_id": str(correction.dossier_id),
            "agent_transmettant_id": str(correction.agent_transmettant_id),
            "elements_transmis": correction.elements_transmis,
            "statut": "EN_ATTENTE"
        }
        
        result = supabase.table("corrections_dossier").insert(correction_data).execute()
        
        if not result.data or len(result.data) == 0:
            raise Exception("Erreur lors de l'insertion de la correction")
        
        correction_record = result.data[0]
        
        # Mettre à jour le statut du dossier
        supabase.table("dossiers").update({"statut": "RETOUR_CORRECTION"}).eq("id", str(correction.dossier_id)).execute()
        
        # Enregistrer dans l'historique
        history_data = {
            "dossier_id": str(correction.dossier_id),
            "user_id": str(current_user["id"]),
            "service_id": current_user["service_id"],
            "ancien_statut": "NON_CONFORME",
            "nouveau_statut": "RETOUR_CORRECTION",
            "action": "Dossier retourné en correction avec motifs"
        }
        supabase.table("workflow_history").insert(history_data).execute()
        
        # Récupérer les données complètes
        agent_info = supabase.table("users").select("nom_complet").eq("id", str(correction.agent_transmettant_id)).execute()
        dossier_info = supabase.table("dossiers").select("numero_dossier").eq("id", str(correction.dossier_id)).execute()
        
        return {
            "id": correction_record["id"],
            "dossier_id": correction_record["dossier_id"],
            "agent_transmettant_id": correction_record["agent_transmettant_id"],
            "elements_transmis": correction_record["elements_transmis"],
            "statut": correction_record["statut"],
            "created_at": correction_record.get("created_at"),
            "updated_at": correction_record.get("updated_at"),
            "agent_transmettant_nom": agent_info.data[0]["nom_complet"] if agent_info.data else None,
            "dossier_numero": dossier_info.data[0]["numero_dossier"] if dossier_info.data else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la création de la correction: {str(e)}"
        )

@router.get("/dossier/{dossier_id}", response_model=List[CorrectionDossier])
async def lister_corrections_dossier(
    dossier_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer tous les retours de correction pour un dossier spécifique.
    """
    
    try:
        supabase = get_supabase()
        
        results = supabase.table("corrections_dossier").select(
            "id, dossier_id, agent_transmettant_id, elements_transmis, statut, created_at, updated_at"
        ).eq("dossier_id", str(dossier_id)).order("created_at", desc=True).execute()
        
        corrections = []
        for row in results.data:
            # Get agent and dossier info
            agent_info = supabase.table("users").select("nom_complet").eq("id", row["agent_transmettant_id"]).execute()
            dossier_info = supabase.table("dossiers").select("numero_dossier").eq("id", row["dossier_id"]).execute()
            
            corrections.append({
                "id": row["id"],
                "dossier_id": row["dossier_id"],
                "agent_transmettant_id": row["agent_transmettant_id"],
                "elements_transmis": row["elements_transmis"],
                "statut": row["statut"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "agent_transmettant_nom": agent_info.data[0]["nom_complet"] if agent_info.data else None,
                "dossier_numero": dossier_info.data[0]["numero_dossier"] if dossier_info.data else None
            })
        
        return corrections
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la récupération des corrections: {str(e)}"
        )

@router.put("/{correction_id}", response_model=CorrectionDossier)
async def mettre_a_jour_correction(
    correction_id: UUID,
    correction_update: CorrectionDossierUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Mettre à jour le statut d'une correction (EN_ATTENTE → RECU → TRAITE).
    """
    
    try:
        supabase = get_supabase()
        
        # Récupérer la correction
        correction = supabase.table("corrections_dossier").select("id, dossier_id, statut").eq("id", str(correction_id)).execute()
        
        if not correction.data or len(correction.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Correction non trouvée"
            )
        
        # Mettre à jour
        update_data = {}
        if correction_update.statut:
            update_data["statut"] = correction_update.statut
        if correction_update.elements_transmis:
            update_data["elements_transmis"] = correction_update.elements_transmis
        
        result = supabase.table("corrections_dossier").update(update_data).eq("id", str(correction_id)).execute()
        
        if not result.data or len(result.data) == 0:
            raise Exception("Erreur lors de la mise à jour")
        
        correction_record = result.data[0]
        
        # Récupérer les données complètes
        agent_info = supabase.table("users").select("nom_complet").eq("id", correction_record["agent_transmettant_id"]).execute()
        dossier_info = supabase.table("dossiers").select("numero_dossier").eq("id", correction_record["dossier_id"]).execute()
        
        return {
            "id": correction_record["id"],
            "dossier_id": correction_record["dossier_id"],
            "agent_transmettant_id": correction_record["agent_transmettant_id"],
            "elements_transmis": correction_record["elements_transmis"],
            "statut": correction_record["statut"],
            "created_at": correction_record.get("created_at"),
            "updated_at": correction_record.get("updated_at"),
            "agent_transmettant_nom": agent_info.data[0]["nom_complet"] if agent_info.data else None,
            "dossier_numero": dossier_info.data[0]["numero_dossier"] if dossier_info.data else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la mise à jour: {str(e)}"
        )

@router.delete("/{correction_id}", status_code=status.HTTP_200_OK)
async def supprimer_correction(
    correction_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Supprimer un retour de correction.

    - Accessible par SERVICE SCVAA uniquement
    - Supprime la correction et remet le dossier à NON_CONFORME
    """

    if current_user["service_id"] != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le SERVICE SCVAA peut supprimer des retours de correction"
        )

    try:
        supabase = get_supabase()
        
        correction = supabase.table("corrections_dossier").select("id, dossier_id").eq("id", str(correction_id)).execute()

        if not correction.data or len(correction.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Correction non trouvée"
            )

        correction_record = correction.data[0]
        dossier_id = correction_record["dossier_id"]

        # Remettre le dossier à NON_CONFORME
        supabase.table("dossiers").update({"statut": "NON_CONFORME"}).eq("id", dossier_id).execute()

        # Supprimer la correction
        supabase.table("corrections_dossier").delete().eq("id", str(correction_id)).execute()

        # Enregistrer dans l'historique
        history_data = {
            "dossier_id": dossier_id,
            "user_id": str(current_user["id"]),
            "service_id": current_user["service_id"],
            "ancien_statut": "RETOUR_CORRECTION",
            "nouveau_statut": "NON_CONFORME",
            "action": "Retour de correction annulé"
        }
        supabase.table("workflow_history").insert(history_data).execute()

        return {"message": "Retour de correction supprimé avec succès"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la suppression: {str(e)}"
        )


@router.get("/{correction_id}", response_model=CorrectionDossier)
async def obtenir_correction(
    correction_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer les détails d'une correction spécifique.
    """
    
    try:
        supabase = get_supabase()
        
        result = supabase.table("corrections_dossier").select(
            "id, dossier_id, agent_transmettant_id, elements_transmis, statut, created_at, updated_at"
        ).eq("id", str(correction_id)).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Correction non trouvée"
            )
        
        correction_record = result.data[0]
        
        # Get agent and dossier info
        agent_info = supabase.table("users").select("nom_complet").eq("id", correction_record["agent_transmettant_id"]).execute()
        dossier_info = supabase.table("dossiers").select("numero_dossier").eq("id", correction_record["dossier_id"]).execute()
        
        return {
            "id": correction_record["id"],
            "dossier_id": correction_record["dossier_id"],
            "agent_transmettant_id": correction_record["agent_transmettant_id"],
            "elements_transmis": correction_record["elements_transmis"],
            "statut": correction_record["statut"],
            "created_at": correction_record["created_at"],
            "updated_at": correction_record["updated_at"],
            "agent_transmettant_nom": agent_info.data[0]["nom_complet"] if agent_info.data else None,
            "dossier_numero": dossier_info.data[0]["numero_dossier"] if dossier_info.data else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )
