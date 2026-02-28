# Améliorations de Sécurité - DosTracker

## Vue d'ensemble

5 améliorations de sécurité ont été implémentées pour renforcer l'authentification et la gestion des sessions.

---

## 1. Refresh Tokens

### Implémentation Backend
- **Fichier**: `app/core/token_manager.py`
- **Fonctionnalités**:
  - Création de tokens d'accès (30 minutes)
  - Création de refresh tokens (7 jours)
  - Vérification et révocation de tokens
  - Gestion des tokens révoqués

### Implémentation Frontend
- **Fichier**: `src/context/AuthContextEnhanced.jsx`
- **Fonctionnalités**:
  - Stockage sécurisé des tokens (localStorage)
  - Rafraîchissement automatique du token (tous les 25 minutes)
  - Rafraîchissement manuel si nécessaire
  - Déconnexion automatique si refresh token invalide

### Endpoints
```
POST /api/v1/auth/login → Retourne access_token + refresh_token
POST /api/v1/auth/refresh-token → Retourne nouveau access_token
```

---

## 2. Logout Côté Serveur

### Implémentation Backend
- **Fichier**: `app/core/token_manager.py`
- **Fonctionnalités**:
  - Révocation des tokens
  - Invalidation des sessions
  - Gestion des sessions actives

### Implémentation Frontend
- **Fichier**: `src/api/authEnhanced.js`
- **Fonctionnalités**:
  - Suppression des tokens du localStorage
  - Suppression des données utilisateur

### Endpoint
```
POST /api/v1/auth/logout → Invalide la session et révoque le token
```

---

## 3. Rate Limiting

### Implémentation Backend
- **Fichier**: `app/core/rate_limiter.py`
- **Fonctionnalités**:
  - Limite: 5 tentatives par 15 minutes
  - Basé sur l'adresse IP
  - Retour du temps d'attente restant
  - Réinitialisation automatique après la fenêtre

### Intégration
- Intégré dans l'endpoint `/api/v1/auth/login`
- Retourne erreur 429 si limite dépassée

### Réponse d'erreur
```json
{
  "detail": "Trop de tentatives. Réessayez dans 847 secondes."
}
```

---

## 4. 2FA avec SMS (Twilio)

### Implémentation Backend
- **Fichier**: `app/core/two_factor_auth.py`
- **Fonctionnalités**:
  - Génération de codes aléatoires (6 chiffres)
  - Envoi via Twilio SMS
  - Expiration après 5 minutes
  - Limite de 3 tentatives
  - Stockage sécurisé des codes

### Implémentation Frontend
- **Fichier**: `src/components/TwoFactorAuth.jsx`
- **Fonctionnalités**:
  - Interface pour envoyer le code
  - Saisie du code avec validation
  - Timer d'expiration
  - Gestion des erreurs

### Endpoints
```
POST /api/v1/auth/2fa/send → Envoie un code SMS
POST /api/v1/auth/2fa/verify → Vérifie le code
```

---

## 5. Gestion des Sessions Actives

### Implémentation Backend
- **Fichier**: `app/core/token_manager.py`
- **Fonctionnalités**:
  - Création de sessions avec ID unique
  - Stockage de: IP, User-Agent, timestamps
  - Récupération des sessions actives
  - Invalidation de sessions spécifiques
  - Invalidation de toutes les sessions

### Implémentation Frontend
- **Fichier**: `src/components/SessionManager.jsx`
- **Fonctionnalités**:
  - Affichage des sessions actives
  - Détection du type d'appareil
  - Affichage de l'IP et des timestamps
  - Rafraîchissement des sessions

### Endpoint
```
GET /api/v1/auth/sessions → Retourne les sessions actives
```

---

## Architecture Globale

### Backend
```
app/
├── core/
│   ├── token_manager.py      (Gestion des tokens et sessions)
│   ├── rate_limiter.py       (Rate limiting)
│   └── two_factor_auth.py    (2FA avec SMS)
├── models/
│   └── token.py              (Modèles Pydantic)
└── api/v1/endpoints/
    └── auth_enhanced.py      (Endpoints améliorés)
```

### Frontend
```
src/
├── api/
│   └── authEnhanced.js       (Appels API)
├── context/
│   └── AuthContextEnhanced.jsx (Contexte avec refresh tokens)
└── components/
    ├── TwoFactorAuth.jsx     (Composant 2FA)
    └── SessionManager.jsx    (Gestion des sessions)
```

---

## Flux d'Authentification Amélioré

### 1. Connexion
```
1. Utilisateur envoie username + password
2. Backend vérifie rate limiting
3. Backend valide les identifiants
4. Backend crée access_token + refresh_token
5. Backend crée une session
6. Frontend stocke les tokens
7. Frontend configure le rafraîchissement automatique
```

### 2. Requêtes Authentifiées
```
1. Frontend envoie access_token dans Authorization header
2. Backend valide le token
3. Si valide: traite la requête
4. Si expiré: frontend rafraîchit automatiquement
```

### 3. Déconnexion
```
1. Utilisateur clique sur "Déconnexion"
2. Frontend envoie POST /logout avec token
3. Backend révoque le token
4. Backend invalide la session
5. Frontend supprime les tokens du localStorage
6. Redirection vers page de connexion
```

---

## Configuration Requise

### Variables d'Environnement Backend
```
REFRESH_TOKEN_EXPIRE_DAYS=7
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=...
```

### Dépendances
- `python-jose` (JWT)
- `twilio` (SMS)
- `passlib` (Hachage)

---

## Utilisation

### Utiliser les Endpoints Améliorés
```javascript
// Au lieu de:
import { loginApi } from './api/auth'

// Utiliser:
import { loginEnhanced, refreshAccessToken } from './api/authEnhanced'
```

### Utiliser le Contexte Amélioré
```javascript
// Au lieu de:
import { AuthProvider } from './context/AuthContext'

// Utiliser:
import { AuthProvider } from './context/AuthContextEnhanced'
```

---

## Sécurité

### Points Forts
- ✓ Tokens JWT signés
- ✓ Refresh tokens séparés
- ✓ Rate limiting sur login
- ✓ 2FA avec SMS
- ✓ Sessions tracées
- ✓ Révocation de tokens
- ✓ Expiration automatique

### Limitations Actuelles
- Stockage en mémoire (utiliser Redis en production)
- Pas de persistance de sessions
- Pas de gestion des appareils de confiance

---

## Prochaines Étapes

1. **Tester les endpoints améliorés**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=admin2026"
   ```

2. **Intégrer les nouveaux composants dans l'application**
   - Remplacer AuthContext par AuthContextEnhanced
   - Ajouter SessionManager dans les paramètres
   - Ajouter TwoFactorAuth si nécessaire

3. **Tester le rafraîchissement automatique**
   - Vérifier que le token se rafraîchit automatiquement
   - Vérifier que la déconnexion fonctionne correctement

4. **Tester le rate limiting**
   - Faire 5+ tentatives de connexion rapides
   - Vérifier que l'erreur 429 est retournée

5. **Tester le 2FA**
   - Envoyer un code SMS
   - Vérifier la réception
   - Vérifier la validation du code

---

## Fichiers Créés

### Backend
- `app/core/token_manager.py`
- `app/core/rate_limiter.py`
- `app/core/two_factor_auth.py`
- `app/models/token.py`
- `app/api/v1/endpoints/auth_enhanced.py`

### Frontend
- `src/api/authEnhanced.js`
- `src/context/AuthContextEnhanced.jsx`
- `src/components/TwoFactorAuth.jsx`
- `src/components/SessionManager.jsx`

---

## Documentation Complète

Pour plus de détails, consultez:
- Backend: Docstrings dans les fichiers Python
- Frontend: Commentaires dans les fichiers JavaScript/JSX
- Logs: Consultez le LogViewer pour le débogage
