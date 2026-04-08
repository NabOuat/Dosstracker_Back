from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List
from uuid import UUID
from datetime import datetime
from app.core.deps import get_current_user
from app.database import get_supabase
from app.models.user import User
from app.models.apfr import PieceJointe
import os
import aiofiles
from pathlib import Path

router = APIRouter(prefix="/pieces-jointes", tags=["Pièces Jointes"])

UPLOAD_DIR = "uploads/pieces_jointes"
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_piece_jointe(
    dossier_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> dict:
    """Upload une pièce jointe (PDF/Image) pour un dossier"""
    
    try:
        dossier_uuid = UUID(dossier_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID dossier invalide")
    
    # Vérifier l'extension du fichier
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non autorisé. Formats acceptés: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Vérifier la taille du fichier
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 10 MB)")
    
    # Vérifier que le dossier existe
    dossier = db.execute(
        "SELECT id FROM dossiers WHERE id = %s",
        (str(dossier_uuid),)
    ).fetchone()
    
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")
    
    # Déterminer le type de fichier
    type_fichier = 'PDF' if file_ext == '.pdf' else 'IMAGE'
    
    # Générer un nom de fichier unique
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{dossier_id}_{timestamp}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    # Sauvegarder le fichier
    async with aiofiles.open(filepath, 'wb') as f:
        await f.write(contents)
    
    # Enregistrer dans la base de données
    piece_jointe_id = db.execute(
        """INSERT INTO pieces_jointes 
           (dossier_id, user_id, service_id, nom_original, url_stockage, type_fichier, taille_octets, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
           RETURNING id, created_at""",
        (str(dossier_uuid), str(current_user.id), current_user.service_id, file.filename, filepath, type_fichier, len(contents))
    ).fetchone()
    
    db.commit()
    
    return {
        "id": str(piece_jointe_id[0]),
        "dossier_id": dossier_id,
        "nom_original": file.filename,
        "type_fichier": type_fichier,
        "taille_octets": len(contents),
        "url_stockage": filepath,
        "created_at": piece_jointe_id[1].isoformat() if piece_jointe_id[1] else None,
        "message": "Fichier uploadé avec succès"
    }

@router.get("/dossier/{dossier_id}")
async def get_pieces_jointes_dossier(
    dossier_id: str,
    current_user: User = Depends(get_current_user)
) -> List[dict]:
    """Récupère toutes les pièces jointes d'un dossier"""
    
    try:
        dossier_uuid = UUID(dossier_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID dossier invalide")
    
    pieces = db.execute(
        """SELECT id, dossier_id, nom_original, type_fichier, taille_octets, created_at
           FROM pieces_jointes
           WHERE dossier_id = %s
           ORDER BY created_at DESC""",
        (str(dossier_uuid),)
    ).fetchall()
    
    return [
        {
            "id": str(p[0]),
            "dossier_id": str(p[1]),
            "nom_original": p[2],
            "type_fichier": p[3],
            "taille_octets": p[4],
            "created_at": p[5].isoformat() if p[5] else None
        }
        for p in pieces
    ]

@router.delete("/{piece_id}")
async def delete_piece_jointe(
    piece_id: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Supprime une pièce jointe"""
    
    try:
        piece_uuid = UUID(piece_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID pièce jointe invalide")
    
    # Récupérer la pièce jointe
    piece = db.execute(
        "SELECT url_stockage FROM pieces_jointes WHERE id = %s",
        (str(piece_uuid),)
    ).fetchone()
    
    if not piece:
        raise HTTPException(status_code=404, detail="Pièce jointe non trouvée")
    
    # Supprimer le fichier physique
    try:
        if os.path.exists(piece[0]):
            os.remove(piece[0])
    except Exception as e:
        print(f"Erreur lors de la suppression du fichier: {e}")
    
    # Supprimer de la base de données
    db.execute("DELETE FROM pieces_jointes WHERE id = %s", (str(piece_uuid),))
    db.commit()
    
    return {"message": "Pièce jointe supprimée avec succès"}
