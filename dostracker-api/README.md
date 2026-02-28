# DosTracker API

API backend FastAPI pour l'application DosTracker de gestion des dossiers fonciers.

## Technologies utilisées

- **FastAPI**: Framework API moderne, rapide et performant
- **Supabase**: Base de données PostgreSQL avec authentification et stockage
- **JWT**: Authentification sécurisée par tokens
- **Pydantic**: Validation de données et sérialisation
- **Twilio**: Service d'envoi de SMS (optionnel)

## Prérequis

- Python 3.8+
- Compte Supabase avec base de données configurée selon le schéma fourni
- Compte Twilio (optionnel pour l'envoi de SMS)

## Installation

1. Cloner le dépôt:

```bash
git clone https://github.com/votre-utilisateur/dostracker-api.git
cd dostracker-api
```

2. Créer un environnement virtuel:

```bash
python -m venv venv
```

3. Activer l'environnement virtuel:

- Windows:
```bash
venv\Scripts\activate
```

- Linux/Mac:
```bash
source venv/bin/activate
```

4. Installer les dépendances:

```bash
pip install -r requirements.txt
```

5. Configurer les variables d'environnement:

Copier le fichier `.env.example` vers `.env` et remplir les informations nécessaires:

```
# Configuration Supabase
SUPABASE_URL=https://pldminqtbnkeyvhzotda.supabase.co
SUPABASE_KEY=sb_publishable_y1g-GuL04IDUCzVywknVCg_b-TqEUEJ
SUPABASE_SERVICE_KEY=dQx9PbXpe0TZJVtk

# Configuration de la base de données PostgreSQL
DATABASE_URL=postgresql://postgres.pldminqtbnkeyvhzotda:dQx9PbXpe0TZJVtk@aws-1-eu-west-1.pooler.supabase.com:6543/postgres

# Configuration JWT
SECRET_KEY=votre_cle_secrete_tres_securisee_a_changer_en_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Configuration Twilio (optionnel)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
```

## Démarrage de l'API

Pour lancer le serveur de développement:

```bash
uvicorn main:app --reload
```

L'API sera disponible à l'adresse: http://localhost:8000

La documentation interactive Swagger UI sera disponible à: http://localhost:8000/docs

## Structure du projet

```
dostracker-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py
│   │       │   ├── dossiers.py
│   │       │   ├── proprietaires.py
│   │       │   ├── sms.py
│   │       │   └── users.py
│   │       └── __init__.py
│   ├── core/
│   │   ├── deps.py
│   │   ├── security.py
│   │   └── __init__.py
│   ├── models/
│   │   ├── dossier.py
│   │   ├── enums.py
│   │   ├── proprietaire.py
│   │   ├── sms.py
│   │   ├── user.py
│   │   └── __init__.py
│   ├── database.py
│   └── __init__.py
├── .env
├── main.py
├── README.md
└── requirements.txt
```

## Points d'API

### Authentification

- `POST /api/v1/auth/login`: Authentification et récupération du token JWT
- `POST /api/v1/auth/refresh-token`: Rafraîchissement du token JWT

### Utilisateurs

- `GET /api/v1/users/`: Liste des utilisateurs (admin uniquement)
- `POST /api/v1/users/`: Création d'un utilisateur (admin uniquement)
- `GET /api/v1/users/me`: Récupération de l'utilisateur connecté
- `GET /api/v1/users/{user_id}`: Récupération d'un utilisateur par ID (admin uniquement)
- `PUT /api/v1/users/{user_id}`: Mise à jour d'un utilisateur (admin uniquement)

### Propriétaires

- `GET /api/v1/proprietaires/`: Liste des propriétaires
- `POST /api/v1/proprietaires/`: Création d'un propriétaire
- `GET /api/v1/proprietaires/{proprietaire_id}`: Récupération d'un propriétaire par ID
- `PUT /api/v1/proprietaires/{proprietaire_id}`: Mise à jour d'un propriétaire
- `GET /api/v1/proprietaires/{proprietaire_id}/dossiers`: Liste des dossiers d'un propriétaire

### Dossiers

- `GET /api/v1/dossiers/`: Liste des dossiers avec filtres
- `POST /api/v1/dossiers/`: Création d'un dossier (SERVICE COURRIER uniquement)
- `GET /api/v1/dossiers/{dossier_id}`: Récupération d'un dossier par ID
- `PUT /api/v1/dossiers/{dossier_id}/spfei-admin`: Mise à jour des informations administratives (SERVICE SPFEI uniquement)
- `PUT /api/v1/dossiers/{dossier_id}/scvaa`: Mise à jour des informations techniques (SERVICE SCVAA uniquement)
- `PUT /api/v1/dossiers/{dossier_id}/spfei-titre`: Attribution d'un titre foncier (SERVICE SPFEI uniquement)
- `POST /api/v1/dossiers/{dossier_id}/envoyer`: Envoi d'un dossier au service suivant

### SMS

- `GET /api/v1/sms/`: Liste des SMS avec filtres
- `POST /api/v1/sms/`: Création et envoi d'un SMS
- `GET /api/v1/sms/{sms_id}`: Récupération d'un SMS par ID
- `POST /api/v1/sms/{sms_id}/resend`: Renvoi d'un SMS existant
- `GET /api/v1/sms/dossier/{dossier_id}`: Liste des SMS pour un dossier spécifique

## Sécurité

L'API utilise JWT (JSON Web Tokens) pour l'authentification. Chaque requête aux endpoints protégés doit inclure un header `Authorization: Bearer {token}`.

Les permissions sont gérées par service:
- SERVICE_COURRIER (1): Accès aux fonctionnalités du service courrier
- SERVICE_SPFEI (2): Accès aux fonctionnalités du service SPFEI
- SERVICE_SCVAA (3): Accès aux fonctionnalités du service SCVAA
- ADMIN (4): Accès complet à toutes les fonctionnalités

## Déploiement en production

Pour le déploiement en production:

1. Générer une clé secrète forte pour `SECRET_KEY`
2. Configurer correctement les paramètres CORS dans `main.py`
3. Utiliser un serveur ASGI comme Uvicorn ou Hypercorn derrière un proxy comme Nginx
4. Configurer HTTPS pour sécuriser les communications

Exemple de déploiement avec Gunicorn et Uvicorn:

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Intégration avec le frontend

Le frontend React peut se connecter à cette API en utilisant les endpoints décrits ci-dessus. Assurez-vous de:

1. Stocker le token JWT de manière sécurisée (localStorage ou cookies HttpOnly)
2. Inclure le token dans chaque requête API
3. Gérer le rafraîchissement du token lorsqu'il expire

## Licence

Ce projet est sous licence MIT.
