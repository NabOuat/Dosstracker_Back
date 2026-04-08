from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID
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

router = APIRouter(prefix="/apfr", tags=["Signature APFR"])


# ================================================================
# ENDPOINTS : Demandes de Signature APFR
# ================================================================

@router.post("/demandes", response_model=DemandSignatureAPFR, status_code=status.HTTP_201_CREATED)
async def creer_demande_signature_apfr(
    demande: DemandSignatureAPFRCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["service_id"] != 2:
        raise HTTPException(status_code=403, detail="Seul le SERVICE SPFEI peut créer des demandes de signature APFR")

    supabase = get_supabase()

    try:
        for dossier_id in demande.dossier_ids:
            res = supabase.table("dossiers").select("id,statut").eq("id", str(dossier_id)).execute()
            if not res.data:
                raise HTTPException(status_code=404, detail=f"Dossier {dossier_id} non trouvé")
            if res.data[0]["statut"] != "SPFEI_TITRE":
                raise HTTPException(status_code=400, detail=f"Le dossier {dossier_id} n'est pas au statut SPFEI_TITRE")

        demande_res = supabase.table("demandes_signature_apfr").insert({
            "numero_demande": demande.numero_demande,
            "agent_spfei_id": str(current_user["id"]),
            "statut": "EN_ATTENTE"
        }).execute()

        if not demande_res.data:
            raise HTTPException(status_code=400, detail="Erreur lors de la création de la demande")

        demande_data = demande_res.data[0]
        demande_id = demande_data["id"]

        for ordre, dossier_id in enumerate(demande.dossier_ids, start=1):
            supabase.table("dossiers_apfr").insert({
                "dossier_id": str(dossier_id),
                "demande_apfr_id": str(demande_id),
                "ordre": ordre
            }).execute()
            supabase.table("dossiers").update({"statut": "ATTENTE_SIGNATURE_APFR"}).eq("id", str(dossier_id)).execute()
            supabase.table("workflow_history").insert({
                "dossier_id": str(dossier_id),
                "user_id": str(current_user["id"]),
                "service_id": current_user["service_id"],
                "ancien_statut": "SPFEI_TITRE",
                "nouveau_statut": "ATTENTE_SIGNATURE_APFR",
                "action": "Dossier inclus dans demande de signature APFR"
            }).execute()

        agent_res = supabase.table("users").select("nom_complet").eq("id", str(current_user["id"])).execute()
        agent_nom = agent_res.data[0]["nom_complet"] if agent_res.data else None

        dossiers_res = supabase.table("dossiers_apfr").select("dossiers(numero_dossier)").eq("demande_apfr_id", str(demande_id)).execute()
        nombre_dossiers = len(dossiers_res.data) if dossiers_res.data else 0
        dossiers_list = ", ".join([d["dossiers"]["numero_dossier"] for d in dossiers_res.data if d.get("dossiers")]) if dossiers_res.data else None

        return {
            "id": demande_data["id"],
            "numero_demande": demande_data["numero_demande"],
            "agent_spfei_id": demande_data["agent_spfei_id"],
            "statut": demande_data["statut"],
            "date_creation": demande_data.get("date_creation"),
            "created_at": demande_data.get("created_at"),
            "updated_at": demande_data.get("updated_at"),
            "agent_spfei_nom": agent_nom,
            "nombre_dossiers": nombre_dossiers,
            "dossiers_list": dossiers_list
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lors de la création de la demande APFR: {str(e)}")


@router.get("/demandes", response_model=List[DemandSignatureAPFR])
async def lister_demandes_apfr(
    statut: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    supabase = get_supabase()

    try:
        query = supabase.table("demandes_signature_apfr").select("*")
        if statut:
            query = query.eq("statut", statut)
        results = query.order("created_at", desc=True).execute()

        demandes = []
        for row in results.data:
            agent_res = supabase.table("users").select("nom_complet").eq("id", row["agent_spfei_id"]).execute()
            agent_nom = agent_res.data[0]["nom_complet"] if agent_res.data else None

            dossiers_res = supabase.table("dossiers_apfr").select("dossiers(numero_dossier)").eq("demande_apfr_id", row["id"]).execute()
            nombre_dossiers = len(dossiers_res.data) if dossiers_res.data else 0
            dossiers_list = ", ".join([d["dossiers"]["numero_dossier"] for d in dossiers_res.data if d.get("dossiers")]) if dossiers_res.data else None

            demandes.append({
                "id": row["id"],
                "numero_demande": row["numero_demande"],
                "agent_spfei_id": row["agent_spfei_id"],
                "statut": row["statut"],
                "date_creation": row.get("date_creation"),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "agent_spfei_nom": agent_nom,
                "nombre_dossiers": nombre_dossiers,
                "dossiers_list": dossiers_list
            })

        return demandes

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lors de la récupération des demandes: {str(e)}")


@router.get("/demandes/{demande_id}", response_model=DemandSignatureAPFR)
async def obtenir_demande_apfr(
    demande_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    supabase = get_supabase()

    try:
        result = supabase.table("demandes_signature_apfr").select("*").eq("id", str(demande_id)).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Demande APFR non trouvée")

        row = result.data[0]

        agent_res = supabase.table("users").select("nom_complet").eq("id", row["agent_spfei_id"]).execute()
        agent_nom = agent_res.data[0]["nom_complet"] if agent_res.data else None

        dossiers_res = supabase.table("dossiers_apfr").select("dossiers(numero_dossier)").eq("demande_apfr_id", str(demande_id)).execute()
        nombre_dossiers = len(dossiers_res.data) if dossiers_res.data else 0
        dossiers_list = ", ".join([d["dossiers"]["numero_dossier"] for d in dossiers_res.data if d.get("dossiers")]) if dossiers_res.data else None

        return {
            "id": row["id"],
            "numero_demande": row["numero_demande"],
            "agent_spfei_id": row["agent_spfei_id"],
            "statut": row["statut"],
            "date_creation": row.get("date_creation"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "agent_spfei_nom": agent_nom,
            "nombre_dossiers": nombre_dossiers,
            "dossiers_list": dossiers_list
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lors de la récupération: {str(e)}")


@router.put("/demandes/{demande_id}", response_model=DemandSignatureAPFR)
async def mettre_a_jour_demande_apfr(
    demande_id: UUID,
    demande_update: DemandSignatureAPFRUpdate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["service_id"] != 2:
        raise HTTPException(status_code=403, detail="Seul le SERVICE SPFEI peut mettre à jour les demandes APFR")

    supabase = get_supabase()

    try:
        demande_res = supabase.table("demandes_signature_apfr").select("id,statut").eq("id", str(demande_id)).execute()
        if not demande_res.data:
            raise HTTPException(status_code=404, detail="Demande APFR non trouvée")

        update_res = supabase.table("demandes_signature_apfr").update({"statut": demande_update.statut}).eq("id", str(demande_id)).execute()
        if not update_res.data:
            raise HTTPException(status_code=400, detail="Erreur lors de la mise à jour")

        row = update_res.data[0]

        if demande_update.statut == "SIGNEE":
            dossiers_res = supabase.table("dossiers_apfr").select("dossier_id").eq("demande_apfr_id", str(demande_id)).execute()
            for d in dossiers_res.data:
                supabase.table("dossiers").update({"statut": "CONSERVATION"}).eq("id", d["dossier_id"]).execute()

        agent_res = supabase.table("users").select("nom_complet").eq("id", row["agent_spfei_id"]).execute()
        agent_nom = agent_res.data[0]["nom_complet"] if agent_res.data else None

        dossiers_info = supabase.table("dossiers_apfr").select("dossiers(numero_dossier)").eq("demande_apfr_id", str(demande_id)).execute()
        nombre_dossiers = len(dossiers_info.data) if dossiers_info.data else 0
        dossiers_list = ", ".join([d["dossiers"]["numero_dossier"] for d in dossiers_info.data if d.get("dossiers")]) if dossiers_info.data else None

        return {
            "id": row["id"],
            "numero_demande": row["numero_demande"],
            "agent_spfei_id": row["agent_spfei_id"],
            "statut": row["statut"],
            "date_creation": row.get("date_creation"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "agent_spfei_nom": agent_nom,
            "nombre_dossiers": nombre_dossiers,
            "dossiers_list": dossiers_list
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lors de la mise à jour: {str(e)}")


@router.delete("/demandes/{demande_id}", status_code=status.HTTP_200_OK)
async def supprimer_demande_apfr(
    demande_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    if current_user["service_id"] != 2:
        raise HTTPException(status_code=403, detail="Seul le SERVICE SPFEI peut supprimer des demandes APFR")

    supabase = get_supabase()

    try:
        demande_res = supabase.table("demandes_signature_apfr").select("id,statut").eq("id", str(demande_id)).execute()
        if not demande_res.data:
            raise HTTPException(status_code=404, detail="Demande APFR non trouvée")
        if demande_res.data[0]["statut"] != "EN_ATTENTE":
            raise HTTPException(status_code=400, detail="Seules les demandes EN_ATTENTE peuvent être supprimées")

        dossiers_res = supabase.table("dossiers_apfr").select("dossier_id").eq("demande_apfr_id", str(demande_id)).execute()

        for d in dossiers_res.data:
            supabase.table("dossiers").update({"statut": "SPFEI_TITRE"}).eq("id", d["dossier_id"]).execute()
            supabase.table("workflow_history").insert({
                "dossier_id": d["dossier_id"],
                "user_id": str(current_user["id"]),
                "service_id": current_user["service_id"],
                "ancien_statut": "ATTENTE_SIGNATURE_APFR",
                "nouveau_statut": "SPFEI_TITRE",
                "action": "Demande APFR annulée"
            }).execute()

        supabase.table("dossiers_apfr").delete().eq("demande_apfr_id", str(demande_id)).execute()
        supabase.table("demandes_signature_apfr").delete().eq("id", str(demande_id)).execute()

        return {"message": "Demande APFR supprimée avec succès"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lors de la suppression: {str(e)}")


# ================================================================
# ENDPOINTS : Retour de Conservation
# ================================================================

@router.post("/retour-conservation", response_model=RetourConservation, status_code=status.HTTP_201_CREATED)
async def creer_retour_conservation(
    retour: RetourConservationCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["service_id"] != 2:
        raise HTTPException(status_code=403, detail="Seul le SERVICE SPFEI peut créer des retours de conservation")

    supabase = get_supabase()

    try:
        dossier_res = supabase.table("dossiers").select("id,statut,numero_dossier").eq("id", str(retour.dossier_id)).execute()
        if not dossier_res.data:
            raise HTTPException(status_code=404, detail="Dossier non trouvé")
        if dossier_res.data[0]["statut"] != "CONSERVATION":
            raise HTTPException(status_code=400, detail="Seuls les dossiers au statut CONSERVATION peuvent avoir un retour de conservation")

        update_res = supabase.table("dossiers").update({
            "num_titre_foncier_conservation": retour.num_titre_foncier_conservation,
            "superficie_conservation": float(retour.superficie_conservation) if retour.superficie_conservation else None,
            "reference_courier_conservation": retour.reference_courier_conservation,
            "agent_retour_conservation_id": str(retour.agent_retour_conservation_id),
            "statut": "RETOUR_CONSERVATION"
        }).eq("id", str(retour.dossier_id)).execute()

        if not update_res.data:
            raise HTTPException(status_code=400, detail="Erreur lors de la mise à jour du dossier")

        result = update_res.data[0]

        supabase.table("workflow_history").insert({
            "dossier_id": str(retour.dossier_id),
            "user_id": str(current_user["id"]),
            "service_id": current_user["service_id"],
            "ancien_statut": "CONSERVATION",
            "nouveau_statut": "RETOUR_CONSERVATION",
            "action": "Retour de la conservation avec titre foncier et superficie"
        }).execute()

        agent_res = supabase.table("users").select("nom_complet").eq("id", str(retour.agent_retour_conservation_id)).execute()
        agent_nom = agent_res.data[0]["nom_complet"] if agent_res.data else None

        return {
            "dossier_id": retour.dossier_id,
            "agent_retour_conservation_id": retour.agent_retour_conservation_id,
            "num_titre_foncier_conservation": result.get("num_titre_foncier_conservation"),
            "superficie_conservation": result.get("superficie_conservation"),
            "reference_courier_conservation": result.get("reference_courier_conservation"),
            "date_retour_conservation": result.get("date_retour_conservation"),
            "agent_retour_conservation_nom": agent_nom,
            "dossier_numero": dossier_res.data[0].get("numero_dossier")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lors de la création du retour de conservation: {str(e)}")


@router.get("/retour-conservation/dossier/{dossier_id}", response_model=RetourConservation)
async def obtenir_retour_conservation(
    dossier_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    supabase = get_supabase()

    try:
        result = supabase.table("dossiers").select(
            "id,num_titre_foncier_conservation,superficie_conservation,"
            "reference_courier_conservation,agent_retour_conservation_id,"
            "date_retour_conservation,numero_dossier"
        ).eq("id", str(dossier_id)).execute()

        if not result.data or not result.data[0].get("num_titre_foncier_conservation"):
            raise HTTPException(status_code=404, detail="Aucun retour de conservation trouvé pour ce dossier")

        row = result.data[0]

        agent_nom = None
        if row.get("agent_retour_conservation_id"):
            agent_res = supabase.table("users").select("nom_complet").eq("id", row["agent_retour_conservation_id"]).execute()
            agent_nom = agent_res.data[0]["nom_complet"] if agent_res.data else None

        return {
            "dossier_id": row["id"],
            "num_titre_foncier_conservation": row.get("num_titre_foncier_conservation"),
            "superficie_conservation": row.get("superficie_conservation"),
            "reference_courier_conservation": row.get("reference_courier_conservation"),
            "agent_retour_conservation_id": row.get("agent_retour_conservation_id"),
            "date_retour_conservation": row.get("date_retour_conservation"),
            "agent_retour_conservation_nom": agent_nom,
            "dossier_numero": row.get("numero_dossier")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lors de la récupération: {str(e)}")
