import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Récupérer les informations de connexion à Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Créer le client Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Client avec clé de service pour les opérations administratives
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def get_supabase() -> Client:
    """
    Fonction pour obtenir une instance du client Supabase
    """
    return supabase

def get_supabase_admin() -> Client:
    """
    Fonction pour obtenir une instance du client Supabase avec des privilèges administratifs
    """
    return supabase_admin
