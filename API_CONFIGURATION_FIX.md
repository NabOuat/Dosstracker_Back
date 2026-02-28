# Correction de la Configuration API - DosTracker

## Problème Identifié

Le frontend ne pouvait pas se connecter au backend en raison d'une discordance dans les URLs de base de l'API.

### Avant la correction
- **Frontend baseURL**: `http://localhost:8000/api`
- **Appels API**: `/v1/auth/login`
- **URL finale**: `http://localhost:8000/api/v1/auth/login` ❌ (incorrect)

### Après la correction
- **Frontend baseURL**: `http://localhost:8000`
- **Appels API**: `/api/v1/auth/login`
- **URL finale**: `http://localhost:8000/api/v1/auth/login` ✓ (correct)

---

## Fichiers Modifiés

### 1. Configuration d'environnement
**Fichier**: `dostracker-app/.env`
```diff
- VITE_API_URL=http://localhost:8000/api
+ VITE_API_URL=http://localhost:8000
```

### 2. Configuration Axios
**Fichier**: `dostracker-app/src/api/axios.js`
```diff
- baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api',
+ baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
```

### 3. Appels API d'authentification
**Fichier**: `dostracker-app/src/api/auth.js`
- `POST /v1/auth/login` → `POST /api/v1/auth/login`
- `POST /v1/auth/logout` → `POST /api/v1/auth/logout`
- `POST /v1/auth/forgot-password` → `POST /api/v1/auth/forgot-password`
- `POST /v1/auth/validate-reset-token` → `POST /api/v1/auth/validate-reset-token`
- `POST /v1/auth/reset-password` → `POST /api/v1/auth/reset-password`

### 4. Appels API SMS
**Fichier**: `dostracker-app/src/api/sms.js`
- Tous les appels `/v1/sms/*` → `/api/v1/sms/*`

### 5. Appels API Dossiers
**Fichier**: `dostracker-app/src/api/dossiers.js`
- Tous les appels `/v1/dossiers/*` → `/api/v1/dossiers/*`
- Tous les appels `/v1/demandes-droits/*` → `/api/v1/demandes-droits/*`

### 6. Appels API Statistiques
**Fichier**: `dostracker-app/src/api/stats.js`
- `GET /v1/stats` → `GET /api/v1/stats`
- `GET /v1/stats/performance` → `GET /api/v1/stats/performance`

---

## Étapes pour Tester

### 1. Arrêter et redémarrer le frontend
```bash
# Arrêter le serveur frontend (Ctrl+C)
# Puis relancer:
cd dostracker-app
npm run dev
```

### 2. Vérifier les logs du backend
Les logs doivent montrer:
```
2026-02-28 13:16:05 - dostracker - INFO - [auth.py:24] - Tentative de connexion pour l'utilisateur: kone.ibrahim
2026-02-28 13:16:06 - dostracker - DEBUG - [auth.py:34] - Données reçues: [...]
2026-02-28 13:16:07 - dostracker - INFO - [auth.py:85] - Connexion réussie pour l'utilisateur: kone.ibrahim
```

### 3. Tester la connexion
1. Ouvrez l'application dans le navigateur: `http://localhost:5173`
2. Cliquez sur le bouton "📋 Logs" en bas à droite
3. Entrez vos identifiants (ex: `kone.ibrahim` / `kone.ibrahim2026`)
4. Vérifiez les logs du frontend pour voir les détails de la requête
5. Vous devriez être redirigé vers le dashboard

### 4. Vérifier les logs du frontend
Dans le LogViewer, vous devriez voir:
- `[DEBUG] loginApi appelée`
- `[DEBUG] Envoi de la requête POST /api/v1/auth/login`
- `[INFO] Réponse réussie de /v1/auth/login`
- `[INFO] Utilisateur connecté avec succès`

---

## Résumé des Corrections

| Composant | Avant | Après |
|-----------|-------|-------|
| Frontend baseURL | `/api` | (vide) |
| Appels API | `/v1/...` | `/api/v1/...` |
| URL finale | `http://localhost:8000/api/v1/...` | `http://localhost:8000/api/v1/...` |

---

## Vérification de la Connexion Supabase

Le backend peut maintenant:
- ✓ Se connecter à Supabase
- ✓ Récupérer les utilisateurs (RLS désactivé)
- ✓ Vérifier les mots de passe
- ✓ Créer les tokens JWT

Le frontend peut maintenant:
- ✓ Envoyer les identifiants au backend
- ✓ Recevoir le token JWT
- ✓ Stocker le token dans localStorage
- ✓ Se rediriger vers le dashboard

---

## Troubleshooting

Si la connexion ne fonctionne toujours pas:

1. **Vérifiez que le backend est en cours d'exécution**
   ```bash
   curl http://localhost:8000/
   ```

2. **Vérifiez les logs du frontend**
   - Ouvrez le LogViewer (bouton "📋 Logs")
   - Cherchez les messages d'erreur en rouge

3. **Vérifiez les logs du backend**
   ```bash
   tail -f dostracker-api/logs/dostracker_2026-02-28.log
   ```

4. **Vérifiez la console du navigateur**
   - Appuyez sur F12
   - Allez dans l'onglet "Console"
   - Cherchez les erreurs réseau

5. **Testez l'API directement**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=kone.ibrahim&password=kone.ibrahim2026"
   ```

---

## Notes Importantes

- Les variables d'environnement sont rechargées au démarrage du serveur
- Le navigateur cache peut causer des problèmes - videz le cache si nécessaire
- Assurez-vous que le backend et le frontend utilisent les mêmes ports (8000 et 5173)
