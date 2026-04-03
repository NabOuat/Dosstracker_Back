from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.core.deps import get_current_user, get_db
from app.models.correction import (
    CorrectionDossier,
    CorrectionDossierCreate,
    CorrectionDossierUpdate
)
from app.models.user import User
from sqlalchemy import text

router = APIRouter(prefix="/corrections", tags=["Corrections"])

@router.post("/", response_model=CorrectionDossier, status_code=status.HTTP_201_CREATED)
async def creer_correction_dossier(
    correction: CorrectionDossierCreate,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Créer un retour de correction pour un dossier NON_CONFORME.
    
    - Accessible par SERVICE SCVAA uniquement
    - Change le statut du dossier à RETOUR_CORRECTION
    - Crée une trace avec agent_transmettant, date et éléments
    """
    
    # Vérifier que l'utilisateur est du SERVICE SCVAA
    if current_user.service_id != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le SERVICE SCVAA peut créer des retours de correction"
        )
    
    try:
        # Vérifier que le dossier existe et est NON_CONFORME
        dossier_check = db.execute(
            text("SELECT id, statut FROM dossiers WHERE id = :dossier_id"),
            {"dossier_id": str(correction.dossier_id)}
        ).fetchone()
        
        if not dossier_check:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier non trouvé"
            )
        
        if dossier_check[1] != "NON_CONFORME":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les dossiers NON_CONFORME peuvent être retournés en correction"
            )
        
        # Créer la correction
        query = text("""
            INSERT INTO corrections_dossier 
            (dossier_id, agent_transmettant_id, elements_transmis, statut)
            VALUES (:dossier_id, :agent_id, :elements, 'EN_ATTENTE')
            RETURNING id, dossier_id, agent_transmettant_id, elements_transmis, 
                      statut, created_at, updated_at
        """)
        
        result = db.execute(query, {
            "dossier_id": str(correction.dossier_id),
            "agent_id": str(correction.agent_transmettant_id),
            "elements": correction.elements_transmis
        }).fetchone()
        
        # Mettre à jour le statut du dossier
        db.execute(
            text("UPDATE dossiers SET statut = 'RETOUR_CORRECTION' WHERE id = :id"),
            {"id": str(correction.dossier_id)}
        )
        
        # Enregistrer dans l'historique
        db.execute(
            text("""
                INSERT INTO workflow_history 
                (dossier_id, user_id, service_id, ancien_statut, nouveau_statut, action)
                VALUES (:dossier_id, :user_id, :service_id, 'NON_CONFORME', 'RETOUR_CORRECTION', 
                        'Dossier retourné en correction avec motifs')
            """),
            {
                "dossier_id": str(correction.dossier_id),
                "user_id": str(current_user.id),
                "service_id": current_user.service_id
            }
        )
        
        db.commit()
        
        # Récupérer les données complètes
        agent_info = db.execute(
            text("SELECT nom_complet FROM users WHERE id = :id"),
            {"id": str(correction.agent_transmettant_id)}
        ).fetchone()
        
        dossier_info = db.execute(
            text("SELECT numero_dossier FROM dossiers WHERE id = :id"),
            {"id": str(correction.dossier_id)}
        ).fetchone()
        
        return {
            "id": result[0],
            "dossier_id": result[1],
            "agent_transmettant_id": result[2],
            "elements_transmis": result[3],
            "statut": result[4],
            "created_at": result[5],
            "updated_at": result[6],
            "agent_transmettant_nom": agent_info[0] if agent_info else None,
            "dossier_numero": dossier_info[0] if dossier_info else None
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la création de la correction: {str(e)}"
        )

@router.get("/dossier/{dossier_id}", response_model=List[CorrectionDossier])
async def lister_corrections_dossier(
    dossier_id: UUID,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Récupérer tous les retours de correction pour un dossier spécifique.
    """
    
    try:
        query = text("""
            SELECT c.id, c.dossier_id, c.agent_transmettant_id, c.elements_transmis,
                   c.statut, c.created_at, c.updated_at,
                   u.nom_complet, d.numero_dossier
            FROM corrections_dossier c
            JOIN users u ON u.id = c.agent_transmettant_id
            JOIN dossiers d ON d.id = c.dossier_id
            WHERE c.dossier_id = :dossier_id
            ORDER BY c.created_at DESC
        """)
        
        results = db.execute(query, {"dossier_id": str(dossier_id)}).fetchall()
        
        corrections = []
        for row in results:
            corrections.append({
                "id": row[0],
                "dossier_id": row[1],
                "agent_transmettant_id": row[2],
                "elements_transmis": row[3],
                "statut": row[4],
                "created_at": row[5],
                "updated_at": row[6],
                "agent_transmettant_nom": row[7],
                "dossier_numero": row[8]
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
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Mettre à jour le statut d'une correction (EN_ATTENTE → RECU → TRAITE).
    """
    
    try:
        # Récupérer la correction
        correction = db.execute(
            text("SELECT id, dossier_id, statut FROM corrections_dossier WHERE id = :id"),
            {"id": str(correction_id)}
        ).fetchone()
        
        if not correction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Correction non trouvée"
            )
        
        # Mettre à jour
        update_query = text("""
            UPDATE corrections_dossier 
            SET statut = COALESCE(:statut, statut),
                elements_transmis = COALESCE(:elements, elements_transmis)
            WHERE id = :id
            RETURNING id, dossier_id, agent_transmettant_id, elements_transmis,
                      statut, created_at, updated_at
        """)
        
        result = db.execute(update_query, {
            "id": str(correction_id),
            "statut": correction_update.statut,
            "elements": correction_update.elements_transmis
        }).fetchone()
        
        db.commit()
        
        # Récupérer les données complètes
        agent_info = db.execute(
            text("SELECT nom_complet FROM users WHERE id = :id"),
            {"id": str(result[2])}
        ).fetchone()
        
        dossier_info = db.execute(
            text("SELECT numero_dossier FROM dossiers WHERE id = :id"),
            {"id": str(result[1])}
        ).fetchone()
        
        return {
            "id": result[0],
            "dossier_id": result[1],
            "agent_transmettant_id": result[2],
            "elements_transmis": result[3],
            "statut": result[4],
            "created_at": result[5],
            "updated_at": result[6],
            "agent_transmettant_nom": agent_info[0] if agent_info else None,
            "dossier_numero": dossier_info[0] if dossier_info else None
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la mise à jour: {str(e)}"
        )

@router.delete("/{correction_id}", status_code=status.HTTP_200_OK)
async def supprimer_correction(
    correction_id: UUID,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Supprimer un retour de correction.

    - Accessible par SERVICE SCVAA uniquement
    - Supprime la correction et remet le dossier à NON_CONFORME
    """

    if current_user.service_id != 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le SERVICE SCVAA peut supprimer des retours de correction"
        )

    try:
        correction = db.execute(
            text("SELECT id, dossier_id FROM corrections_dossier WHERE id = :id"),
            {"id": str(correction_id)}
        ).fetchone()

        if not correction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Correction non trouvée"
            )

        # Remettre le dossier à NON_CONFORME
        db.execute(
            text("UPDATE dossiers SET statut = 'NON_CONFORME' WHERE id = :id"),
            {"id": str(correction[1])}
        )

        db.execute(
            text("DELETE FROM corrections_dossier WHERE id = :id"),
            {"id": str(correction_id)}
        )

        db.execute(
            text("""
                INSERT INTO workflow_history
                (dossier_id, user_id, service_id, ancien_statut, nouveau_statut, action)
                VALUES (:dossier_id, :user_id, :service_id, 'RETOUR_CORRECTION', 'NON_CONFORME',
                        'Retour de correction annulé')
            """),
            {
                "dossier_id": str(correction[1]),
                "user_id": str(current_user.id),
                "service_id": current_user.service_id
            }
        )

        db.commit()
        return {"message": "Retour de correction supprimé avec succès"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la suppression: {str(e)}"
        )


@router.get("/{correction_id}", response_model=CorrectionDossier)
async def obtenir_correction(
    correction_id: UUID,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Récupérer les détails d'une correction spécifique.
    """
    
    try:
        query = text("""
            SELECT c.id, c.dossier_id, c.agent_transmettant_id, c.elements_transmis,
                   c.statut, c.created_at, c.updated_at,
                   u.nom_complet, d.numero_dossier
            FROM corrections_dossier c
            JOIN users u ON u.id = c.agent_transmettant_id
            JOIN dossiers d ON d.id = c.dossier_id
            WHERE c.id = :id
        """)
        
        result = db.execute(query, {"id": str(correction_id)}).fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Correction non trouvée"
            )
        
        return {
            "id": result[0],
            "dossier_id": result[1],
            "agent_transmettant_id": result[2],
            "elements_transmis": result[3],
            "statut": result[4],
            "created_at": result[5],
            "updated_at": result[6],
            "agent_transmettant_nom": result[7],
            "dossier_numero": result[8]
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )
