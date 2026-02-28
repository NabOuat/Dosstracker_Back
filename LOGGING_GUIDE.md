# Guide du Système de Logging - DosTracker

## Vue d'ensemble

Un système de logging complet a été mis en place pour le frontend et le backend afin de faciliter le débogage des problèmes de connexion et autres erreurs.

---

## Backend (FastAPI)

### Fichier de configuration
- **Fichier**: `dostracker-api/logger.py`
- **Emplacement des logs**: `dostracker-api/logs/dostracker_YYYY-MM-DD.log`

### Fonctionnalités
- Logs rotatifs (10MB par fichier, 5 fichiers de sauvegarde)
- Niveaux de log: DEBUG, INFO, WARN, ERROR
- Format: `[timestamp] - [logger_name] - [level] - [file:line] - [message]`
- Affichage en console et sauvegarde en fichier

### Utilisation dans le code
```python
from logger import get_logger

logger = get_logger()

# Différents niveaux de log
logger.debug("Message de débogage", {"data": "value"})
logger.info("Information importante")
logger.warning("Avertissement")
logger.error("Erreur critique", exc_info=True)
```

### Logs d'authentification
Le fichier `dostracker-api/app/api/v1/endpoints/auth.py` contient des logs détaillés pour chaque tentative de connexion:
- Tentative de connexion
- Vérification de l'utilisateur dans la base de données
- Vérification du mot de passe
- Vérification du statut actif
- Succès ou erreur de connexion

---

## Frontend (React)

### Fichiers de configuration
- **Logger principal**: `dostracker-app/src/utils/logger.js`
- **Logger API**: `dostracker-app/src/utils/apiLogger.js`
- **Composant d'affichage**: `dostracker-app/src/components/LogViewer.jsx`

### Fonctionnalités
- Logs stockés en mémoire (max 1000 entrées)
- Sauvegarde automatique dans localStorage
- Niveaux de log: DEBUG, INFO, WARN, ERROR
- Interface visuelle pour consulter les logs
- Téléchargement des logs en fichier `.log`
- Filtrage des logs en temps réel

### Utilisation dans le code
```javascript
import logger from '../utils/logger'

// Différents niveaux de log
logger.debug('Message de débogage', { data: 'value' })
logger.info('Information importante')
logger.warn('Avertissement')
logger.error('Erreur critique', { details: 'error details' })
```

### Accès aux logs
1. **Interface visuelle**: Un bouton "📋 Logs" apparaît en bas à droite de l'application
2. **Fonctionnalités du LogViewer**:
   - Affichage de tous les logs avec timestamps
   - Filtrage par niveau ou par texte
   - Téléchargement en fichier `.log`
   - Effacement des logs
   - Affichage du nombre total de logs

### Logs d'authentification (Frontend)
Les logs détaillés sont enregistrés à plusieurs niveaux:

#### Page de Login (`src/pages/Login.jsx`)
- Tentative de connexion
- Validation des champs
- Appel de la fonction login
- Redirection après succès
- Erreurs avec détails

#### Contexte d'authentification (`src/context/AuthContext.jsx`)
- Restauration de l'utilisateur depuis localStorage
- Appel de loginApi
- Sauvegarde des données
- Déconnexion

#### API d'authentification (`src/api/auth.js`)
- Appel de chaque endpoint
- Réponses réussies
- Erreurs avec status HTTP et détails

---

## Dépannage des problèmes de connexion

### Étapes pour déboguer

1. **Ouvrir le LogViewer**
   - Cliquez sur le bouton "📋 Logs" en bas à droite

2. **Vérifier les logs du frontend**
   - Cherchez les messages d'erreur en rouge
   - Vérifiez les détails de la requête API
   - Notez le status HTTP (401, 500, etc.)

3. **Télécharger les logs du frontend**
   - Cliquez sur "Télécharger" dans le LogViewer
   - Cela crée un fichier `dostracker_logs_YYYY-MM-DD.log`

4. **Vérifier les logs du backend**
   - Ouvrez le fichier `dostracker-api/logs/dostracker_YYYY-MM-DD.log`
   - Cherchez les messages correspondant à votre tentative de connexion
   - Vérifiez les détails de l'erreur (utilisateur non trouvé, mot de passe incorrect, etc.)

### Erreurs courantes

#### 401 Unauthorized
- **Frontend**: "Nom d'utilisateur ou mot de passe incorrect"
- **Backend**: Vérifiez les logs pour:
  - Utilisateur non trouvé
  - Mot de passe incorrect
  - Utilisateur inactif

#### 500 Internal Server Error
- **Frontend**: "Erreur serveur lors de l'authentification"
- **Backend**: Vérifiez les logs pour les exceptions Python
- Vérifiez la connexion à Supabase

#### Erreur de connexion API
- Vérifiez que le backend est en cours d'exécution
- Vérifiez l'URL de l'API dans les variables d'environnement
- Vérifiez les logs CORS

---

## Variables d'environnement

### Backend (`.env`)
```
DATABASE_URL=...
JWT_SECRET=...
```

### Frontend (`.env`)
```
VITE_API_URL=http://localhost:8000
```

---

## Commandes utiles

### Démarrer le backend avec logs
```bash
cd dostracker-api
python main.py
```

### Démarrer le frontend avec logs
```bash
cd dostracker-app
npm run dev
```

### Consulter les logs du backend
```bash
tail -f dostracker-api/logs/dostracker_2026-02-28.log
```

---

## Stockage des logs

### Backend
- **Emplacement**: `dostracker-api/logs/`
- **Format**: `dostracker_YYYY-MM-DD.log`
- **Rotation**: 10MB par fichier, 5 fichiers conservés

### Frontend
- **localStorage**: Clé `dostracker_logs` (max 1000 entrées)
- **Téléchargement**: Fichier `dostracker_logs_YYYY-MM-DD.log`

---

## Exemple de flux de débogage

1. Tentez de vous connecter avec des identifiants incorrects
2. Ouvrez le LogViewer (bouton "📋 Logs")
3. Cherchez les messages d'erreur en rouge
4. Notez le status HTTP et le message d'erreur
5. Téléchargez les logs du frontend
6. Vérifiez les logs du backend dans `dostracker-api/logs/`
7. Comparez les timestamps pour identifier le problème

---

## Support

Pour plus d'informations sur le système de logging, consultez:
- Backend: `dostracker-api/logger.py`
- Frontend: `dostracker-app/src/utils/logger.js`
- Composant: `dostracker-app/src/components/LogViewer.jsx`
