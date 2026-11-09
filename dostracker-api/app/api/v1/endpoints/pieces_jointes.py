from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List
from uuid import UUID
from datetime import datetime
from app.core.deps import get_current_user
from app.database import get_supabase
from logger import get_logger
import os
import re
import uuid
from pathlib import Path
from app.database import get_supabase_admin

logger = get_logger()
router = APIRouter(prefix="/pieces-jointes", tags=["Pièces Jointes"])

BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "pieces-jointes")
SIGNED_URL_TTL = 300  # secondes
CONTENT_TYPES = {
    '.pdf': 'application/pdf', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.png': 'image/png', '.gif': 'image/gif', '.bmp': 'image/bmp',
}
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


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

    # Chemin sûr : pas de nom client brut (évite path traversal / caractères invalides)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(file.filename).name)
    filepath = f"{dossier_id}/{timestamp}_{uuid.uuid4().hex[:8]}_{safe_name}"

    try:
        get_supabase_admin().storage.from_(BUCKET).upload(
            filepath, contents, {"content-type": CONTENT_TYPES[file_ext]}
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur stockage fichier: {e}")

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


@router.get("/{piece_id}/download")
async def download_piece_jointe(
    piece_id: str,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Retourne une URL signée (valide 5 min) pour télécharger la pièce jointe"""

    try:
        piece_uuid = UUID(piece_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID pièce jointe invalide")

    piece_res = get_supabase().table("pieces_jointes").select(
        "url_stockage,nom_original"
    ).eq("id", str(piece_uuid)).execute()
    if not piece_res.data:
        raise HTTPException(status_code=404, detail="Pièce jointe non trouvée")

    piece = piece_res.data[0]
    try:
        signed = get_supabase_admin().storage.from_(BUCKET).create_signed_url(
            piece["url_stockage"], SIGNED_URL_TTL, {"download": piece["nom_original"]}
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur génération du lien: {e}")

    url = signed.get("signedURL") or signed.get("signedUrl")
    if not url:
        raise HTTPException(status_code=404, detail="Fichier introuvable dans le stockage")
    return {"url": url, "nom_original": piece["nom_original"], "expires_in": SIGNED_URL_TTL}


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
        get_supabase_admin().storage.from_(BUCKET).remove([piece_res.data[0]["url_stockage"]])
    except Exception as e:
        logger.warning(f"Erreur suppression fichier storage: {e}")

    supabase.table("pieces_jointes").delete().eq("id", str(piece_uuid)).execute()

    return {"message": "Pièce jointe supprimée avec succès"}
