# Correction du Problème RLS - DosTracker

## Problème Identifié

Les utilisateurs sont présents dans la base de données Supabase, mais les requêtes d'authentification ne les trouvent pas. 

**Cause**: Les politiques RLS (Row Level Security) sur la table `users` bloquent l'accès avec la clé publique.

### Diagnostic
- ✓ Connexion à Supabase établie
- ✓ Utilisateurs présents dans la base de données
- ✗ Requête avec clé publique retourne 0 utilisateurs
- ✗ Requête avec clé service retourne erreur 401 (clé invalide)

---

## Solution

### Option 1: Désactiver RLS (Recommandé pour développement)

1. **Accédez à Supabase Dashboard**
   - URL: https://app.supabase.com
   - Sélectionnez votre projet

2. **Ouvrez l'éditeur SQL**
   - Cliquez sur "SQL Editor" dans le menu de gauche
   - Cliquez sur "New query"

3. **Exécutez le script SQL**
   ```sql
   -- Désactiver RLS sur la table users
   ALTER TABLE users DISABLE ROW LEVEL SECURITY;
   ```

4. **Vérifiez que RLS est désactivé**
   ```sql
   SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'users';
   ```
   - Vous devriez voir `rowsecurity = false`

5. **Testez la connexion**
   - Relancez le backend
   - Essayez de vous connecter avec vos identifiants

### Option 2: Configurer les politiques RLS (Recommandé pour production)

Si vous préférez garder RLS activé, créez des politiques permissives:

1. **Ouvrez l'éditeur SQL** dans Supabase

2. **Exécutez le script SQL**
   ```sql
   -- Créer les politiques RLS pour la table users
   
   -- Politique de lecture publique (pour l'authentification)
   CREATE POLICY "Allow public read for auth" ON users
     FOR SELECT
     USING (true);
   
   -- Politique de mise à jour (pour last_login)
   CREATE POLICY "Allow public update for auth" ON users
     FOR UPDATE
     USING (true)
     WITH CHECK (true);
   ```

3. **Vérifiez les politiques**
   - Allez dans "Authentication" > "Policies"
   - Vous devriez voir les deux politiques créées

---

## Vérification

Après avoir appliqué la solution, testez avec le script de diagnostic:

```bash
cd dostracker-api
python test_supabase.py
```

Vous devriez voir:
- ✓ Test 1: Récupération de tous les utilisateurs - **X utilisateurs trouvés**
- ✓ Test 2: Recherche de 'diallo.fatoumata' - **Utilisateur trouvé**
- ✓ Test 3: Recherche de 'admin' - **Utilisateur trouvé**
- ✓ Test 4: Recherche avec jointure - **Utilisateur trouvé**

---

## Fichiers de diagnostic

- `test_supabase.py` - Script pour tester la connexion Supabase
- `fix_rls.sql` - Script SQL pour corriger RLS
- `dostracker-api/logs/dostracker_*.log` - Logs du backend

---

## Prochaines étapes

1. Appliquez la solution RLS (Option 1 ou 2)
2. Testez avec `python test_supabase.py`
3. Relancez le backend
4. Testez la connexion dans l'application

---

## Notes

- **Option 1** est plus simple pour le développement
- **Option 2** est plus sécurisée pour la production
- Les logs du backend vous aideront à identifier d'autres problèmes potentiels
- Le LogViewer du frontend enregistre tous les détails des tentatives de connexion
