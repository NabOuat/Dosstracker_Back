from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List
from uuid import UUID
from datetime import datetime
from app.core.deps import get_current_user
from app.database import get_supabase
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
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Upload une pièce jointe (PDF/Image) pour un dossier"""

    try:
        dossier_uuid = UUID(dossier_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID dossier invalide")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Type de fichier non autorisé. Formats acceptés: {', '.join(ALLOWED_EXTENSIONS)}")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 10 MB)")

    supabase = get_supabase()

    dossier_res = supabase.table("dossiers").select("id").eq("id", str(dossier_uuid)).execute()
    if not dossier_res.data:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    type_fichier = 'PDF' if file_ext == '.pdf' else 'IMAGE'

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{dossier_id}_{timestamp}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    async with aiofiles.open(filepath, 'wb') as f:
        await f.write(contents)

    result = supabase.table("pieces_jointes").insert({
        "dossier_id": str(dossier_uuid),
        "user_id": str(current_user["id"]),
        "service_id": current_user["service_id"],
        "nom_original": file.filename,
        "url_stockage": filepath,
        "type_fichier": type_fichier,
        "taille_octets": len(contents)
    }).execute()

    if not result.data:
        raise HTTPException(status_code=400, detail="Erreur lors de l'enregistrement")

    piece = result.data[0]

    return {
        "id": str(piece["id"]),
        "dossier_id": dossier_id,
        "nom_original": file.filename,
        "type_fichier": type_fichier,
        "taille_octets": len(contents),
        "url_stockage": filepath,
        "created_at": piece.get("created_at"),
        "message": "Fichier uploadé avec succès"
    }


@router.get("/dossier/{dossier_id}")
async def get_pieces_jointes_dossier(
    dossier_id: str,
    current_user: dict = Depends(get_current_user)
) -> List[dict]:
    """Récupère toutes les pièces jointes d'un dossier"""

    try:
        dossier_uuid = UUID(dossier_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID dossier invalide")

    supabase = get_supabase()

    result = supabase.table("pieces_jointes").select(
        "id,dossier_id,nom_original,type_fichier,taille_octets,created_at"
    ).eq("dossier_id", str(dossier_uuid)).order("created_at", desc=True).execute()

    return [
        {
            "id": str(p["id"]),
            "dossier_id": str(p["dossier_id"]),
            "nom_original": p["nom_original"],
            "type_fichier": p["type_fichier"],
            "taille_octets": p["taille_octets"],
            "created_at": p["created_at"]
        }
        for p in result.data
    ]


@router.delete("/{piece_id}")
async def delete_piece_jointe(
    piece_id: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Supprime une pièce jointe"""

    try:
        piece_uuid = UUID(piece_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID pièce jointe invalide")

    supabase = get_supabase()

    piece_res = supabase.table("pieces_jointes").select("url_stockage").eq("id", str(piece_uuid)).execute()
    if not piece_res.data:
        raise HTTPException(status_code=404, detail="Pièce jointe non trouvée")

    try:
        filepath = piece_res.data[0]["url_stockage"]
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Erreur lors de la suppression du fichier: {e}")

    supabase.table("pieces_jointes").delete().eq("id", str(piece_uuid)).execute()

    return {"message": "Pièce jointe supprimée avec succès"}
