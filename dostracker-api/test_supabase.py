#!/usr/bin/env python3
"""
Script de diagnostic pour tester la connexion à Supabase et les requêtes utilisateurs
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Charger les variables d'environnement
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

print("=" * 80)
print("TEST DE CONNEXION À SUPABASE")
print("=" * 80)

print(f"\n1. Configuration:")
print(f"   - URL: {SUPABASE_URL}")
print(f"   - Clé publique: {SUPABASE_KEY[:20]}...")
print(f"   - Clé service: {SUPABASE_SERVICE_KEY[:20]}...")

# Test avec clé publique
print(f"\n2. Test avec clé publique:")
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("   ✓ Connexion établie")
    
    # Test 1: Récupérer tous les utilisateurs
    print("\n   Test 1: Récupération de tous les utilisateurs")
    response = supabase.table("users").select("*").execute()
    print(f"   ✓ Réponse reçue: {len(response.data) if response.data else 0} utilisateurs")
    if response.data:
        for user in response.data[:3]:
            print(f"     - {user.get('username')} ({user.get('nom_complet')})")
    
    # Test 2: Chercher un utilisateur spécifique
    print("\n   Test 2: Recherche de 'diallo.fatoumata'")
    response = supabase.table("users").select("*").eq("username", "diallo.fatoumata").execute()
    print(f"   ✓ Réponse reçue: {len(response.data) if response.data else 0} utilisateurs")
    if response.data:
        print(f"     - Utilisateur trouvé: {response.data[0]}")
    else:
        print("     - Aucun utilisateur trouvé")
    
    # Test 3: Chercher 'admin'
    print("\n   Test 3: Recherche de 'admin'")
    response = supabase.table("users").select("*").eq("username", "admin").execute()
    print(f"   ✓ Réponse reçue: {len(response.data) if response.data else 0} utilisateurs")
    if response.data:
        print(f"     - Utilisateur trouvé: {response.data[0]}")
    else:
        print("     - Aucun utilisateur trouvé")
    
    # Test 4: Avec jointure
    print("\n   Test 4: Recherche avec jointure (services)")
    response = supabase.table("users").select("*, services(nom, libelle)").eq("username", "diallo.fatoumata").execute()
    print(f"   ✓ Réponse reçue: {len(response.data) if response.data else 0} utilisateurs")
    if response.data:
        print(f"     - Utilisateur trouvé: {response.data[0]}")
    else:
        print("     - Aucun utilisateur trouvé")

except Exception as e:
    print(f"   ✗ Erreur: {str(e)}")
    import traceback
    traceback.print_exc()

# Test avec clé service
print(f"\n3. Test avec clé service:")
try:
    supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("   ✓ Connexion établie")
    
    # Test 1: Récupérer tous les utilisateurs
    print("\n   Test 1: Récupération de tous les utilisateurs")
    response = supabase_admin.table("users").select("*").execute()
    print(f"   ✓ Réponse reçue: {len(response.data) if response.data else 0} utilisateurs")
    if response.data:
        for user in response.data[:3]:
            print(f"     - {user.get('username')} ({user.get('nom_complet')})")
    
    # Test 2: Chercher un utilisateur spécifique
    print("\n   Test 2: Recherche de 'diallo.fatoumata'")
    response = supabase_admin.table("users").select("*").eq("username", "diallo.fatoumata").execute()
    print(f"   ✓ Réponse reçue: {len(response.data) if response.data else 0} utilisateurs")
    if response.data:
        print(f"     - Utilisateur trouvé: {response.data[0]}")
    else:
        print("     - Aucun utilisateur trouvé")

except Exception as e:
    print(f"   ✗ Erreur: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("FIN DU TEST")
print("=" * 80)
