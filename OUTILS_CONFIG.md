# Guide de Configuration des Outils — DosTracker

## Sommaire
1. [Sentry — Monitoring des erreurs](#1-sentry--monitoring-des-erreurs)
2. [GitHub Actions — CI/CD](#2-github-actions--cicd)
3. [Codecov — Couverture de tests](#3-codecov--couverture-de-tests)
4. [GitHub Secrets — Variables sensibles](#4-github-secrets--variables-sensibles)
5. [Docker — Déploiement](#5-docker--déploiement)

---

## 1. Sentry — Monitoring des erreurs

Sentry capture automatiquement les erreurs en production (frontend et backend).

### Backend (FastAPI)

**1. Créer un compte Sentry**
- Aller sur https://sentry.io → S'inscrire gratuitement
- Créer un nouveau projet → choisir **FastAPI**
- Copier le **DSN** affiché (ex: `https://abc123@o123.ingest.sentry.io/456`)

**2. Ajouter le DSN dans le fichier `.env`**
```env
SENTRY_DSN=https://abc123@o123.ingest.sentry.io/456
ENVIRONMENT=production
```

**3. Installer le paquet** (déjà dans requirements.txt)
```bash
pip install -r requirements.txt
```

Sentry s'activera automatiquement au démarrage de l'API si `SENTRY_DSN` est défini.

---

### Frontend (React)

**1. Dans Sentry, créer un second projet → choisir **React****
- Copier le DSN du projet React

**2. Créer le fichier `.env` dans `dostracker-app/`**
```env
VITE_SENTRY_DSN=https://xyz789@o123.ingest.sentry.io/789
VITE_ENVIRONMENT=production
```

**3. Installer le paquet**
```bash
cd dostracker-app
npm install
```

Sentry s'active automatiquement si `VITE_SENTRY_DSN` est présent.
En développement, laisser `VITE_SENTRY_DSN` vide pour ne pas polluer les alertes.

---

### Vérifier que Sentry fonctionne

Déclencher une erreur test depuis le backend :
```bash
curl http://localhost:8000/api/v1/debug/error-test
```

---

## 2. GitHub Actions — CI/CD

Le pipeline CI/CD se déclenche automatiquement à chaque `push` ou `pull_request`.

### Ce qu'il fait automatiquement

| Étape | Déclencheur | Description |
|-------|-------------|-------------|
| Tests backend | Push/PR sur `main` ou `develop` | flake8 + black + pytest |
| Tests frontend | Push/PR sur `main` ou `develop` | ESLint + build Vite |
| Scan sécurité | Push/PR | Trivy (vulnérabilités) |
| Build Docker | Push sur `main` uniquement | Images backend + frontend |
| Déploiement staging | Push sur `develop` uniquement | SSH + docker-compose |

### Configurer le pipeline

**Étape 1 — Créer les GitHub Secrets** (voir section 4)

**Étape 2 — Pousser sur les bonnes branches**
```bash
# Développement → déclenche tests + staging
git push origin develop

# Production → déclenche tests + build Docker
git push origin main
```

**Étape 3 — Voir les résultats**
- Aller sur GitHub → onglet **Actions**
- Chaque pipeline affiche les étapes en vert/rouge

---

## 3. Codecov — Couverture de tests

Codecov affiche le pourcentage de code couvert par les tests.

**1. Créer un compte** sur https://codecov.io (gratuit pour les repos publics)

**2. Connecter le repo GitHub**
- Aller sur codecov.io → Add Repository → sélectionner `DosTracker`
- Copier le **CODECOV_TOKEN**

**3. Ajouter le token dans GitHub Secrets**
```
Nom   : CODECOV_TOKEN
Valeur: le token copié depuis codecov.io
```

Le badge de couverture sera automatiquement mis à jour après chaque CI.

---

## 4. GitHub Secrets — Variables sensibles

Les secrets sont des variables d'environnement injectées dans le CI/CD.
**Ne jamais les mettre dans le code.**

### Ajouter un secret

1. Aller sur GitHub → votre repo → **Settings** → **Secrets and variables** → **Actions**
2. Cliquer **New repository secret**
3. Ajouter chaque secret ci-dessous

### Secrets requis

| Nom | Description | Où le trouver |
|-----|-------------|---------------|
| `SUPABASE_URL` | URL du projet Supabase | Dashboard Supabase → Settings → API |
| `SUPABASE_KEY` | Clé publique Supabase | Dashboard Supabase → Settings → API |
| `SECRET_KEY` | Clé JWT | Générer : `openssl rand -hex 32` |
| `CODECOV_TOKEN` | Token Codecov | codecov.io → votre repo |
| `DEPLOY_HOST` | IP ou domaine du serveur | Votre hébergeur |
| `DEPLOY_USER` | Utilisateur SSH | Votre hébergeur |
| `DEPLOY_KEY` | Clé SSH privée | `cat ~/.ssh/id_rsa` |

### Générer une clé secrète JWT sécurisée
```bash
openssl rand -hex 32
# Exemple de résultat : a3f8c2e1d4b7...
```

---

## 5. Docker — Déploiement

### Lancer en local avec Docker Compose
```bash
# À la racine du projet
docker-compose up --build

# Backend accessible sur : http://localhost:8000
# Frontend accessible sur : http://localhost:3000
```

### Variables d'environnement pour Docker

Créer un fichier `.env` à la racine (copier depuis `.env.example`) :
```bash
cp dostracker-api/.env.example dostracker-api/.env
# Remplir les valeurs dans dostracker-api/.env
```

### Déploiement manuel sur un serveur

```bash
# Sur le serveur
git pull origin main
docker-compose pull
docker-compose up -d

# Vérifier que tout tourne
docker-compose ps
docker-compose logs -f
```

---

## Résumé — Ordre de configuration recommandé

```
1. Créer les comptes Sentry (backend + frontend)
2. Ajouter les DSN dans les fichiers .env
3. Créer le compte Codecov + récupérer le token
4. Ajouter tous les secrets dans GitHub Settings
5. Faire un premier push sur develop → vérifier le CI dans l'onglet Actions
6. Si tout est vert → push sur main → déploiement production
```
