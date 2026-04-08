from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.core.deps import get_current_user
from app.database import get_supabase
from app.models.apfr import (
    DemandSignatureAPFR,
    DemandSignatureAPFRCreate,
    DemandSignatureAPFRUpdate,
    RetourConservation,
    RetourConservationCreate,
    RetourConservationUpdate
)
from app.models.user import User

router = APIRouter(prefix="/apfr", tags=["Signature APFR"])

# ================================================================
# ENDPOINTS : Demandes de Signature APFR
# ================================================================

@router.post("/demandes", response_model=DemandSignatureAPFR, status_code=status.HTTP_201_CREATED)
async def creer_demande_signature_apfr(
    demande: DemandSignatureAPFRCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Créer une demande de signature APFR groupant plusieurs dossiers.
    
    - Accessible par SERVICE SPFEI uniquement
    - Crée une demande avec statut EN_ATTENTE
    - Ajoute les dossiers à la demande avec ordre
    - Change le statut des dossiers à ATTENTE_SIGNATURE_APFR
    """
    
    # Vérifier que l'utilisateur est du SERVICE SPFEI
    if current_user.service_id != 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le SERVICE SPFEI peut créer des demandes de signature APFR"
        )
    
    try:
        # Vérifier que tous les dossiers existent et sont au statut SPFEI_TITRE
        for dossier_id in demande.dossier_ids:
            dossier_check = db.execute(
                text("SELECT id, statut FROM dossiers WHERE id = :dossier_id"),
                {"dossier_id": str(dossier_id)}
            ).fetchone()
            
            if not dossier_check:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Dossier {dossier_id} non trouvé"
                )
            
            if dossier_check[1] != "SPFEI_TITRE":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Le dossier {dossier_id} n'est pas au statut SPFEI_TITRE"
                )
        
        # Créer la demande APFR
        query = text("""
            INSERT INTO demandes_signature_apfr 
            (numero_demande, agent_spfei_id, statut)
            VALUES (:numero_demande, :agent_id, 'EN_ATTENTE')
            RETURNING id, numero_demande, agent_spfei_id, statut, date_creation, created_at, updated_at
        """)
        
        result = db.execute(query, {
            "numero_demande": demande.numero_demande,
            "agent_id": str(current_user.id)
        }).fetchone()
        
        demande_id = result[0]
        
        # Ajouter les dossiers à la demande
        for ordre, dossier_id in enumerate(demande.dossier_ids, start=1):
            db.execute(
                text("""
                    INSERT INTO dossiers_apfr (dossier_id, demande_apfr_id, ordre)
                    VALUES (:dossier_id, :demande_id, :ordre)
                """),
                {
                    "dossier_id": str(dossier_id),
                    "demande_id": str(demande_id),
                    "ordre": ordre
                }
            )
            
            # Mettre à jour le statut du dossier
            db.execute(
                text("UPDATE dossiers SET statut = 'ATTENTE_SIGNATURE_APFR' WHERE id = :id"),
                {"id": str(dossier_id)}
            )
            
            # Enregistrer dans l'historique
            db.execute(
                text("""
                    INSERT INTO workflow_history 
                    (dossier_id, user_id, service_id, ancien_statut, nouveau_statut, action)
                    VALUES (:dossier_id, :user_id, :service_id, 'SPFEI_TITRE', 'ATTENTE_SIGNATURE_APFR', 
                            'Dossier inclus dans demande de signature APFR')
                """),
                {
                    "dossier_id": str(dossier_id),
                    "user_id": str(current_user.id),
                    "service_id": current_user.service_id
                }
            )
        
        db.commit()
        
        # Récupérer les données complètes
        agent_info = db.execute(
            text("SELECT nom_complet FROM users WHERE id = :id"),
            {"id": str(current_user.id)}
        ).fetchone()
        
        dossiers_info = db.execute(
            text("""
                SELECT COUNT(*), STRING_AGG(d.numero_dossier, ', ' ORDER BY da.ordre)
                FROM dossiers_apfr da
                JOIN dossiers d ON d.id = da.dossier_id
                WHERE da.demande_apfr_id = :demande_id
            """),
            {"demande_id": str(demande_id)}
        ).fetchone()
        
        return {
            "id": result[0],
            "numero_demande": result[1],
            "agent_spfei_id": result[2],
            "statut": result[3],
            "date_creation": result[4],
            "created_at": result[5],
            "updated_at": result[6],
            "agent_spfei_nom": agent_info[0] if agent_info else None,
            "nombre_dossiers": dossiers_info[0] if dossiers_info else 0,
            "dossiers_list": dossiers_info[1] if dossiers_info else None
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la création de la demande APFR: {str(e)}"
        )

@router.get("/demandes", response_model=List[DemandSignatureAPFR])
async def lister_demandes_apfr(
    statut: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer la liste des demandes de signature APFR avec filtrage optionnel par statut.
    """
    
    try:
        query = """
            SELECT dsa.id, dsa.numero_demande, dsa.agent_spfei_id, dsa.statut, 
                   dsa.date_creation, dsa.created_at, dsa.updated_at,
                   us.nom_complet,
                   COUNT(da.dossier_id) AS nombre_dossiers,
                   STRING_AGG(d.numero_dossier, ', ' ORDER BY da.ordre) AS dossiers_list
            FROM demandes_signature_apfr dsa
            JOIN users us ON us.id = dsa.agent_spfei_id
            LEFT JOIN dossiers_apfr da ON da.demande_apfr_id = dsa.id
            LEFT JOIN dossiers d ON d.id = da.dossier_id
        """
        
        params = {}
        if statut:
            query += " WHERE dsa.statut = :statut"
            params["statut"] = statut
        
        query += " GROUP BY dsa.id, dsa.numero_demande, dsa.agent_spfei_id, dsa.statut, dsa.date_creation, dsa.created_at, dsa.updated_at, us.nom_complet"
        query += " ORDER BY dsa.created_at DESC"
        
        results = db.execute(text(query), params).fetchall()
        
        demandes = []
        for row in results:
            demandes.append({
                "id": row[0],
                "numero_demande": row[1],
                "agent_spfei_id": row[2],
                "statut": row[3],
                "date_creation": row[4],
                "created_at": row[5],
                "updated_at": row[6],
                "agent_spfei_nom": row[7],
                "nombre_dossiers": row[8],
                "dossiers_list": row[9]
            })
        
        return demandes
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la récupération des demandes: {str(e)}"
        )

@router.get("/demandes/{demande_id}", response_model=DemandSignatureAPFR)
async def obtenir_demande_apfr(
    demande_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer les détails d'une demande APFR spécifique avec tous ses dossiers.
    """
    
    try:
        query = text("""
            SELECT dsa.id, dsa.numero_demande, dsa.agent_spfei_id, dsa.statut, 
                   dsa.date_creation, dsa.created_at, dsa.updated_at,
                   us.nom_complet,
                   COUNT(da.dossier_id) AS nombre_dossiers,
                   STRING_AGG(d.numero_dossier, ', ' ORDER BY da.ordre) AS dossiers_list
            FROM demandes_signature_apfr dsa
            JOIN users us ON us.id = dsa.agent_spfei_id
            LEFT JOIN dossiers_apfr da ON da.demande_apfr_id = dsa.id
            LEFT JOIN dossiers d ON d.id = da.dossier_id
            WHERE dsa.id = :demande_id
            GROUP BY dsa.id, dsa.numero_demande, dsa.agent_spfei_id, dsa.statut, 
                     dsa.date_creation, dsa.created_at, dsa.updated_at, us.nom_complet
        """)
        
        result = db.execute(query, {"demande_id": str(demande_id)}).fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Demande APFR non trouvée"
            )
        
        return {
            "id": result[0],
            "numero_demande": result[1],
            "agent_spfei_id": result[2],
            "statut": result[3],
            "date_creation": result[4],
            "created_at": result[5],
            "updated_at": result[6],
            "agent_spfei_nom": result[7],
            "nombre_dossiers": result[8],
            "dossiers_list": result[9]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )

@router.put("/demandes/{demande_id}", response_model=DemandSignatureAPFR)
async def mettre_a_jour_demande_apfr(
    demande_id: UUID,
    demande_update: DemandSignatureAPFRUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Mettre à jour le statut d'une demande APFR (EN_ATTENTE → SIGNEE ou REJETEE).
    """
    
    if current_user.service_id != 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le SERVICE SPFEI peut mettre à jour les demandes APFR"
        )
    
    try:
        # Récupérer la demande
        demande = db.execute(
            text("SELECT id, statut FROM demandes_signature_apfr WHERE id = :id"),
            {"id": str(demande_id)}
        ).fetchone()
        
        if not demande:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Demande APFR non trouvée"
            )
        
        # Mettre à jour le statut
        update_query = text("""
            UPDATE demandes_signature_apfr 
            SET statut = :statut
            WHERE id = :id
            RETURNING id, numero_demande, agent_spfei_id, statut, date_creation, created_at, updated_at
        """)
        
        result = db.execute(update_query, {
            "id": str(demande_id),
            "statut": demande_update.statut
        }).fetchone()
        
        # Si SIGNEE, mettre à jour les dossiers à CONSERVATION
        if demande_update.statut == "SIGNEE":
            db.execute(
                text("""
                    UPDATE dossiers 
                    SET statut = 'CONSERVATION'
                    WHERE id IN (
                        SELECT dossier_id FROM dossiers_apfr WHERE demande_apfr_id = :demande_id
                    )
                """),
                {"demande_id": str(demande_id)}
            )
        
        db.commit()
        
        # Récupérer les données complètes
        agent_info = db.execute(
            text("SELECT nom_complet FROM users WHERE id = :id"),
            {"id": str(result[2])}
        ).fetchone()
        
        dossiers_info = db.execute(
            text("""
                SELECT COUNT(*), STRING_AGG(d.numero_dossier, ', ' ORDER BY da.ordre)
                FROM dossiers_apfr da
                JOIN dossiers d ON d.id = da.dossier_id
                WHERE da.demande_apfr_id = :demande_id
            """),
            {"demande_id": str(demande_id)}
        ).fetchone()
        
        return {
            "id": result[0],
            "numero_demande": result[1],
            "agent_spfei_id": result[2],
            "statut": result[3],
            "date_creation": result[4],
            "created_at": result[5],
            "updated_at": result[6],
            "agent_spfei_nom": agent_info[0] if agent_info else None,
            "nombre_dossiers": dossiers_info[0] if dossiers_info else 0,
            "dossiers_list": dossiers_info[1] if dossiers_info else None
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la mise à jour: {str(e)}"
        )

@router.delete("/demandes/{demande_id}", status_code=status.HTTP_200_OK)
async def supprimer_demande_apfr(
    demande_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Supprimer une demande de signature APFR.

    - Accessible par SERVICE SPFEI uniquement
    - Uniquement si la demande est EN_ATTENTE
    - Remet les dossiers inclus au statut SPFEI_TITRE
    """

    if current_user.service_id != 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le SERVICE SPFEI peut supprimer des demandes APFR"
        )

    try:
        demande = db.execute(
            text("SELECT id, statut FROM demandes_signature_apfr WHERE id = :id"),
            {"id": str(demande_id)}
        ).fetchone()

        if not demande:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Demande APFR non trouvée"
            )

        if demande[1] != "EN_ATTENTE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seules les demandes EN_ATTENTE peuvent être supprimées"
            )

        # Récupérer les dossiers liés
        dossiers_lies = db.execute(
            text("SELECT dossier_id FROM dossiers_apfr WHERE demande_apfr_id = :id"),
            {"id": str(demande_id)}
        ).fetchall()

        # Remettre les dossiers à SPFEI_TITRE
        for row in dossiers_lies:
            db.execute(
                text("UPDATE dossiers SET statut = 'SPFEI_TITRE' WHERE id = :id"),
                {"id": str(row[0])}
            )
            db.execute(
                text("""
                    INSERT INTO workflow_history
                    (dossier_id, user_id, service_id, ancien_statut, nouveau_statut, action)
                    VALUES (:dossier_id, :user_id, :service_id, 'ATTENTE_SIGNATURE_APFR', 'SPFEI_TITRE',
                            'Demande APFR annulée')
                """),
                {
                    "dossier_id": str(row[0]),
                    "user_id": str(current_user.id),
                    "service_id": current_user.service_id
                }
            )

        # Supprimer les liens dossiers_apfr puis la demande
        db.execute(
            text("DELETE FROM dossiers_apfr WHERE demande_apfr_id = :id"),
            {"id": str(demande_id)}
        )
        db.execute(
            text("DELETE FROM demandes_signature_apfr WHERE id = :id"),
            {"id": str(demande_id)}
        )

        db.commit()
        return {"message": "Demande APFR supprimée avec succès"}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la suppression: {str(e)}"
        )


# ================================================================
# ENDPOINTS : Retour de Conservation
# ================================================================

@router.post("/retour-conservation", response_model=RetourConservation, status_code=status.HTTP_201_CREATED)
async def creer_retour_conservation(
    retour: RetourConservationCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Créer un retour de conservation pour un dossier.
    
    - Accessible par SERVICE SPFEI uniquement
    - Change le statut du dossier à RETOUR_CONSERVATION
    - Enregistre : num titre foncier, superficie, référence courrier, PDF
    """
    
    # Vérifier que l'utilisateur est du SERVICE SPFEI
    if current_user.service_id != 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le SERVICE SPFEI peut créer des retours de conservation"
        )
    
    try:
        # Vérifier que le dossier existe et est à CONSERVATION
        dossier_check = db.execute(
            text("SELECT id, statut FROM dossiers WHERE id = :dossier_id"),
            {"dossier_id": str(retour.dossier_id)}
        ).fetchone()
        
        if not dossier_check:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier non trouvé"
            )
        
        if dossier_check[1] != "CONSERVATION":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les dossiers au statut CONSERVATION peuvent avoir un retour de conservation"
            )
        
        # Mettre à jour le dossier avec les informations de retour
        update_query = text("""
            UPDATE dossiers 
            SET num_titre_foncier_conservation = :num_tf,
                superficie_conservation = :superficie,
                reference_courier_conservation = :ref_courier,
                agent_retour_conservation_id = :agent_id,
                date_retour_conservation = NOW(),
                statut = 'RETOUR_CONSERVATION'
            WHERE id = :dossier_id
            RETURNING id, num_titre_foncier_conservation, superficie_conservation, 
                      reference_courier_conservation, agent_retour_conservation_id, 
                      date_retour_conservation
        """)
        
        result = db.execute(update_query, {
            "dossier_id": str(retour.dossier_id),
            "num_tf": retour.num_titre_foncier_conservation,
            "superficie": retour.superficie_conservation,
            "ref_courier": retour.reference_courier_conservation,
            "agent_id": str(retour.agent_retour_conservation_id)
        }).fetchone()
        
        # Enregistrer dans l'historique
        db.execute(
            text("""
                INSERT INTO workflow_history 
                (dossier_id, user_id, service_id, ancien_statut, nouveau_statut, action)
                VALUES (:dossier_id, :user_id, :service_id, 'CONSERVATION', 'RETOUR_CONSERVATION', 
                        'Retour de la conservation avec titre foncier et superficie')
            """),
            {
                "dossier_id": str(retour.dossier_id),
                "user_id": str(current_user.id),
                "service_id": current_user.service_id
            }
        )
        
        db.commit()
        
        # Récupérer les données complètes
        agent_info = db.execute(
            text("SELECT nom_complet FROM users WHERE id = :id"),
            {"id": str(retour.agent_retour_conservation_id)}
        ).fetchone()
        
        dossier_info = db.execute(
            text("SELECT numero_dossier FROM dossiers WHERE id = :id"),
            {"id": str(retour.dossier_id)}
        ).fetchone()
        
        return {
            "dossier_id": retour.dossier_id,
            "agent_retour_conservation_id": retour.agent_retour_conservation_id,
            "num_titre_foncier_conservation": result[1],
            "superficie_conservation": result[2],
            "reference_courier_conservation": result[3],
            "date_retour_conservation": result[5],
            "agent_retour_conservation_nom": agent_info[0] if agent_info else None,
            "dossier_numero": dossier_info[0] if dossier_info else None
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la création du retour de conservation: {str(e)}"
        )

@router.get("/retour-conservation/dossier/{dossier_id}", response_model=RetourConservation)
async def obtenir_retour_conservation(
    dossier_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer les informations de retour de conservation pour un dossier.
    """
    
    try:
        query = text("""
            SELECT d.id, d.num_titre_foncier_conservation, d.superficie_conservation,
                   d.reference_courier_conservation, d.agent_retour_conservation_id,
                   d.date_retour_conservation, u.nom_complet, d.numero_dossier
            FROM dossiers d
            LEFT JOIN users u ON u.id = d.agent_retour_conservation_id
            WHERE d.id = :dossier_id
        """)
        
        result = db.execute(query, {"dossier_id": str(dossier_id)}).fetchone()
        
        if not result or not result[1]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun retour de conservation trouvé pour ce dossier"
            )
        
        return {
            "dossier_id": result[0],
            "num_titre_foncier_conservation": result[1],
            "superficie_conservation": result[2],
            "reference_courier_conservation": result[3],
            "agent_retour_conservation_id": result[4],
            "date_retour_conservation": result[5],
            "agent_retour_conservation_nom": result[6],
            "dossier_numero": result[7]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la récupération: {str(e)}"
        )
