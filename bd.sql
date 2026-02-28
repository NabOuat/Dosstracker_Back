-- ================================================================
--  DosTracker — Schéma PostgreSQL FINAL
--  Gestion Foncière Numérique · Côte d'Ivoire
--  Basé STRICTEMENT sur le cahier des charges
-- ================================================================
--
--  CIRCUIT :
--  SERVICE COURRIER → SERVICE SPFEI → SERVICE SCVAA
--    ├── Non conforme : SMS motifs → propriétaire → corrections → SCVAA
--    └── Conforme     : → SERVICE SPFEI → Conservation Foncière + SMS propriétaire
--
--  RÈGLES :
--  - 1 dossier = 1 demande (pas de multi-parcelles)
--  - Conservation Foncière = destination finale (PAS un service actif)
--  - Users reliés à leur service via FK service_id → services
-- ================================================================


-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";


-- ================================================================
-- ENUMS
-- ================================================================

CREATE TYPE statut_dossier AS ENUM (
    'COURRIER',           -- Étape 1 : reçu et enregistré par le SERVICE COURRIER
    'SPFEI_ADMIN',        -- Étape 2 : en contrôle administratif au SERVICE SPFEI
    'SCVAA',              -- Étape 3 : en contrôle technique au SERVICE SCVAA
    'NON_CONFORME',       -- Étape 3b: jugé non conforme (SMS envoyé, attente corrections)
    'SPFEI_TITRE',        -- Étape 4 : attribution titre foncier au SERVICE SPFEI
    'CONSERVATION'        -- Étape 5 : envoyé à la Conservation Foncière (FINAL, SMS envoyé)
);

CREATE TYPE conformite AS ENUM (
    'CONFORME',
    'NON_CONFORME'
);

CREATE TYPE genre AS ENUM (
    'Masculin',
    'Féminin'
);

CREATE TYPE statut_sms AS ENUM (
    'ENVOYE',
    'ECHEC',
    'SIMULE'
);

CREATE TYPE type_sms AS ENUM (
    'NON_CONFORMITE',   -- déclenché quand SCVAA juge non conforme
    'FINALISATION'      -- déclenché quand dossier envoyé à la Conservation
);

CREATE TYPE type_fichier AS ENUM (
    'PDF',
    'IMAGE',
    'AUTRE'
);


-- ================================================================
-- TABLE : services
-- Les 3 services actifs + ADMIN
-- Chaque user est rattaché à un service via service_id
-- ================================================================

CREATE TABLE services (
    id       SMALLINT     PRIMARY KEY,   -- 1=COURRIER, 2=SPFEI, 3=SCVAA, 4=ADMIN
    nom      VARCHAR(50)  NOT NULL UNIQUE,
    libelle  VARCHAR(100) NOT NULL
);

-- Données fixes — ne changent jamais
INSERT INTO services (id, nom, libelle) VALUES
(1, 'SERVICE_COURRIER', 'Service Courrier'),
(2, 'SERVICE_SPFEI',    'Service SPFEI'),
(3, 'SERVICE_SCVAA',    'Service SCVAA'),
(4, 'ADMIN',            'Administration');


-- ================================================================
-- TABLE : users
-- Agents — plusieurs par service — reliés à services via service_id
-- ================================================================

CREATE TABLE users (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    nom_complet     VARCHAR(150) NOT NULL,
    username        VARCHAR(80)  NOT NULL UNIQUE,
    email           VARCHAR(150) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    service_id      SMALLINT     NOT NULL REFERENCES services(id),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    last_login      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_service_id ON users(service_id);

COMMENT ON COLUMN users.service_id IS 'FK → services.id — détermine les droits d accès dans l appli';


-- ================================================================
-- TABLE : proprietaires
-- = "Demandeur" dans le cahier des charges
-- Un propriétaire peut avoir plusieurs dossiers
-- ================================================================

CREATE TABLE proprietaires (
    id          UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    nom_complet VARCHAR(200) NOT NULL,
    contact     VARCHAR(20)  NOT NULL,   -- numéro de téléphone pour les SMS Twilio
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_proprietaires_nom     ON proprietaires USING gin(nom_complet gin_trgm_ops);
CREATE INDEX idx_proprietaires_contact ON proprietaires(contact);

COMMENT ON COLUMN proprietaires.contact IS 'Numéro utilisé par Twilio pour envoyer les SMS';


-- ================================================================
-- TABLE : dossiers
-- TABLE CENTRALE — 1 dossier = 1 demande foncière
-- Champs organisés par service, EXACTEMENT selon le cahier des charges
-- ================================================================

CREATE TABLE dossiers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- ────────────────────────────────────────────────────────
    -- SECTION A — SERVICE COURRIER
    -- Saisie à la réception du dossier physique
    -- Champs : Numero de Dossier, Date d'enregistrement, REGION,
    --          Prefecture, Sous-Préfecture, Village, Numero du CF,
    --          Demandeur (→ proprietaires), Contact (→ proprietaires.contact)
    -- ────────────────────────────────────────────────────────
    numero_dossier      VARCHAR(50)  NOT NULL UNIQUE,
    date_enregistrement DATE         NOT NULL,
    region              VARCHAR(100) NOT NULL,
    prefecture          VARCHAR(100),
    sous_prefecture     VARCHAR(100),
    village             VARCHAR(100),
    numero_cf           VARCHAR(80),
    proprietaire_id     UUID         NOT NULL REFERENCES proprietaires(id),
    -- Agent du SERVICE COURRIER qui a enregistré et envoyé le dossier
    agent_courrier_id   UUID         REFERENCES users(id) ON DELETE SET NULL,
    date_envoi_spfei    TIMESTAMPTZ,

    -- ────────────────────────────────────────────────────────
    -- SECTION B — SERVICE SPFEI (1er passage — Contrôle Administratif)
    -- Champs : NATIONALITE, Genre, Type CF,
    --          Date Enquête Officielle, Date Validation Enq Officielle,
    --          Date d'établissement du CF, Date de demande d'immatriculation
    -- ────────────────────────────────────────────────────────
    nationalite             VARCHAR(80),
    genre                   genre,
    type_cf                 VARCHAR(100),
    date_enquete_officielle DATE,
    date_valid_enq          DATE,
    date_etab_cf            DATE,
    date_demande_immat      DATE,
    -- Agent du SERVICE SPFEI qui a fait le contrôle admin
    agent_spfei_admin_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    date_envoi_scvaa        TIMESTAMPTZ,

    -- ────────────────────────────────────────────────────────
    -- SECTION C — SERVICE SCVAA (Contrôle Technique)
    -- Champs : Superficie en ha, date de bornage,
    --          Géomètre Expert, Contact (du géomètre)
    --          + Décision conformité + motifs si non conforme
    -- ────────────────────────────────────────────────────────
    superficie_ha       NUMERIC(10, 4),
    date_bornage        DATE,
    geometre_expert     VARCHAR(150),
    contact_geometre    VARCHAR(20),
    -- Décision du SCVAA
    decision_conformite conformite,
    -- Motifs cochés (codes de motifs_ref) + motif libre
    -- Stockés en JSONB : ex. ["LIMITES_NON_BORNEES", "PLAN_INCOMPLET"]
    motifs_inconformite JSONB,
    autre_motif         TEXT,
    -- Agent du SERVICE SCVAA
    agent_scvaa_id      UUID REFERENCES users(id) ON DELETE SET NULL,
    date_decision_scvaa TIMESTAMPTZ,

    -- ────────────────────────────────────────────────────────
    -- SECTION D — SERVICE SPFEI (2ème passage — Titre Foncier)
    -- Champs : CONSERVATION, N° TITRE FONCIER
    -- ────────────────────────────────────────────────────────
    conservation            VARCHAR(200),
    numero_titre_foncier    VARCHAR(100),
    -- Agent du SERVICE SPFEI qui a attribué le titre
    agent_spfei_titre_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    date_attribution_titre  TIMESTAMPTZ,
    -- Date d'envoi à la Conservation Foncière (= fin du circuit)
    date_envoi_conservation TIMESTAMPTZ,

    -- ────────────────────────────────────────────────────────
    -- METADATA
    -- ────────────────────────────────────────────────────────
    statut      statut_dossier NOT NULL DEFAULT 'COURRIER',
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dossiers_statut       ON dossiers(statut);
CREATE INDEX idx_dossiers_region       ON dossiers(region);
CREATE INDEX idx_dossiers_proprietaire ON dossiers(proprietaire_id);
CREATE INDEX idx_dossiers_numero       ON dossiers(numero_dossier);
CREATE INDEX idx_dossiers_num_trgm     ON dossiers USING gin(numero_dossier gin_trgm_ops);
CREATE INDEX idx_dossiers_motifs       ON dossiers USING gin(motifs_inconformite);
CREATE INDEX idx_dossiers_created      ON dossiers(created_at DESC);

COMMENT ON TABLE  dossiers                     IS '1 dossier = 1 demande foncière. Champs stricts du cahier des charges.';
COMMENT ON COLUMN dossiers.proprietaire_id     IS '"Demandeur" dans le cahier des charges';
COMMENT ON COLUMN dossiers.motifs_inconformite IS 'JSONB array des codes : ["LIMITES_NON_BORNEES", "PLAN_INCOMPLET", ...]';
COMMENT ON COLUMN dossiers.statut              IS 'COURRIER → SPFEI_ADMIN → SCVAA → NON_CONFORME|SPFEI_TITRE → CONSERVATION';


-- ================================================================
-- TABLE : motifs_ref
-- Référentiel des 8 motifs prédéfinis du cahier des charges
-- Affiché comme checkboxes dans l'interface SCVAA
-- ================================================================

CREATE TABLE motifs_ref (
    id       SMALLINT     PRIMARY KEY,
    code     VARCHAR(60)  NOT NULL UNIQUE,  -- stocké dans dossiers.motifs_inconformite
    libelle  VARCHAR(200) NOT NULL,
    is_active BOOLEAN     NOT NULL DEFAULT TRUE,
    ordre    SMALLINT     NOT NULL DEFAULT 0
);

INSERT INTO motifs_ref (id, code, libelle, ordre) VALUES
(1, 'LIMITES_NON_BORNEES',     'Limites non bornées',                1),
(2, 'PLAN_CADASTRAL_INCOMPLET', 'Plan cadastral incomplet',           2),
(3, 'SUPERFICIE_NON_CONFORME',  'Superficie non conforme',            3),
(4, 'CHEVAUCHEMENT_PARCELLES',  'Chevauchement de parcelles',         4),
(5, 'DOCUMENTS_MANQUANTS',      'Documents justificatifs manquants',  5),
(6, 'ERREUR_COORDONNEES_GPS',   'Erreur de coordonnées GPS',          6),
(7, 'NON_RESPECT_URBANISME',    'Non-respect du plan d urbanisme',    7),
(8, 'LITIGE_FONCIER',           'Litige foncier en cours',            8);


-- ================================================================
-- TABLE : workflow_history
-- Traçabilité complète : qui / quoi / quand sur chaque dossier
-- ================================================================

CREATE TABLE workflow_history (
    id             UUID           PRIMARY KEY DEFAULT uuid_generate_v4(),
    dossier_id     UUID           NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
    user_id        UUID           REFERENCES users(id) ON DELETE SET NULL,
    service_id     SMALLINT       REFERENCES services(id) ON DELETE SET NULL,
    ancien_statut  statut_dossier,
    nouveau_statut statut_dossier NOT NULL,
    action         VARCHAR(300)   NOT NULL,   -- ex : "Dossier transmis au SERVICE SPFEI"
    details        JSONB,                     -- champs modifiés, valeurs avant/après
    created_at     TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wh_dossier  ON workflow_history(dossier_id);
CREATE INDEX idx_wh_user     ON workflow_history(user_id);
CREATE INDEX idx_wh_created  ON workflow_history(created_at DESC);


-- ================================================================
-- TABLE : commentaires
-- Notes internes entre services sur un dossier
-- ================================================================

CREATE TABLE commentaires (
    id            UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    dossier_id    UUID        NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
    user_id       UUID        NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    service_id    SMALLINT    NOT NULL REFERENCES services(id) ON DELETE RESTRICT,
    contenu       TEXT        NOT NULL,
    est_important BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_comm_dossier ON commentaires(dossier_id);


-- ================================================================
-- TABLE : pieces_jointes
-- Documents scannés liés à un dossier (Supabase Storage)
-- ================================================================

CREATE TABLE pieces_jointes (
    id            UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    dossier_id    UUID         NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
    user_id       UUID         REFERENCES users(id) ON DELETE SET NULL,
    service_id    SMALLINT     REFERENCES services(id) ON DELETE SET NULL,
    nom_original  VARCHAR(255) NOT NULL,
    url_stockage  TEXT         NOT NULL,
    type_fichier  type_fichier NOT NULL DEFAULT 'PDF',
    taille_octets BIGINT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pj_dossier ON pieces_jointes(dossier_id);


-- ================================================================
-- TABLE : sms_log
-- Journal de tous les SMS envoyés via Twilio
-- 2 déclencheurs automatiques :
--   1. SCVAA juge NON_CONFORME → SMS avec liste des motifs
--   2. SPFEI envoie à Conservation → SMS de finalisation
-- ================================================================

CREATE TABLE sms_log (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    dossier_id          UUID        NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
    proprietaire_id     UUID        NOT NULL REFERENCES proprietaires(id),
    type_sms            type_sms    NOT NULL,
    numero_destinataire VARCHAR(20) NOT NULL,
    contenu_message     TEXT        NOT NULL,
    statut              statut_sms  NOT NULL DEFAULT 'ENVOYE',
    twilio_sid          VARCHAR(50),   -- SID retourné par Twilio
    erreur              TEXT,          -- détail si ECHEC
    envoye_par_id       UUID        REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sms_dossier  ON sms_log(dossier_id);
CREATE INDEX idx_sms_created  ON sms_log(created_at DESC);


-- ================================================================
-- TRIGGER : updated_at automatique
-- ================================================================

CREATE OR REPLACE FUNCTION fn_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION fn_updated_at();

CREATE TRIGGER trg_proprietaires_updated_at
    BEFORE UPDATE ON proprietaires
    FOR EACH ROW EXECUTE FUNCTION fn_updated_at();

CREATE TRIGGER trg_dossiers_updated_at
    BEFORE UPDATE ON dossiers
    FOR EACH ROW EXECUTE FUNCTION fn_updated_at();


-- ================================================================
-- VUES
-- ================================================================

-- Vue principale : listing des dossiers avec toutes les jointures
CREATE VIEW v_dossiers AS
SELECT
    d.id,
    d.numero_dossier,
    d.date_enregistrement,
    d.region,
    d.prefecture,
    d.sous_prefecture,
    d.village,
    d.numero_cf,
    d.statut,

    -- Demandeur (propriétaire)
    p.nom_complet   AS demandeur,
    p.contact       AS contact_demandeur,

    -- SERVICE COURRIER
    uc.nom_complet  AS agent_courrier,
    d.date_envoi_spfei,

    -- SERVICE SPFEI - Admin
    d.nationalite, d.genre, d.type_cf,
    d.date_enquete_officielle,
    d.date_valid_enq,
    d.date_etab_cf,
    d.date_demande_immat,
    ua.nom_complet  AS agent_spfei_admin,
    d.date_envoi_scvaa,

    -- SERVICE SCVAA
    d.superficie_ha,
    d.date_bornage,
    d.geometre_expert,
    d.contact_geometre,
    d.decision_conformite,
    d.motifs_inconformite,
    d.autre_motif,
    us.nom_complet  AS agent_scvaa,
    d.date_decision_scvaa,

    -- SERVICE SPFEI - Titre
    d.conservation,
    d.numero_titre_foncier,
    ut.nom_complet  AS agent_spfei_titre,
    d.date_attribution_titre,
    d.date_envoi_conservation,

    d.created_at,
    d.updated_at

FROM dossiers d
JOIN  proprietaires p ON p.id  = d.proprietaire_id
LEFT JOIN users uc    ON uc.id = d.agent_courrier_id
LEFT JOIN users ua    ON ua.id = d.agent_spfei_admin_id
LEFT JOIN users us    ON us.id = d.agent_scvaa_id
LEFT JOIN users ut    ON ut.id = d.agent_spfei_titre_id;


-- Vue stats par statut (tableau de bord)
CREATE VIEW v_stats_statut AS
SELECT
    statut,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') AS ce_mois
FROM dossiers
GROUP BY statut;


-- Vue stats par région
CREATE VIEW v_stats_region AS
SELECT
    region,
    COUNT(*)                                                   AS total,
    COUNT(*) FILTER (WHERE statut = 'CONSERVATION')            AS termines,
    COUNT(*) FILTER (WHERE statut = 'NON_CONFORME')            AS non_conformes,
    COUNT(*) FILTER (WHERE statut NOT IN ('CONSERVATION'))     AS en_cours
FROM dossiers
GROUP BY region
ORDER BY total DESC;


-- Vue activité des agents par service
CREATE VIEW v_activite_agents AS
SELECT
    u.nom_complet,
    s.libelle AS service,
    COUNT(DISTINCT wh.dossier_id) AS dossiers_traites,
    MAX(wh.created_at)            AS derniere_action
FROM users u
JOIN services s ON s.id = u.service_id
LEFT JOIN workflow_history wh ON wh.user_id = u.id
WHERE u.is_active = TRUE
GROUP BY u.id, u.nom_complet, s.libelle
ORDER BY dossiers_traites DESC;


-- ================================================================
-- DONNÉES DE TEST — Utilisateurs
-- ================================================================

INSERT INTO users (nom_complet, username, email, hashed_password, service_id) VALUES

-- SERVICE COURRIER (service_id = 1)
('COULIBALY Mamadou',    'coul.mamadou',     'coul.mamadou@dostracker.ci',    '$2b$12$HASH_ICI', 1),
('BAMBA Aïssatou',       'bamba.aissatou',   'bamba.aissatou@dostracker.ci',  '$2b$12$HASH_ICI', 1),

-- SERVICE SPFEI (service_id = 2)
('KONE Ibrahim',         'kone.ibrahim',     'kone.ibrahim@dostracker.ci',    '$2b$12$HASH_ICI', 2),
('DIALLO Fatoumata',     'diallo.fatoumata', 'diallo.fatoumata@dostracker.ci','$2b$12$HASH_ICI', 2),

-- SERVICE SCVAA (service_id = 3)
('TRAORE Seydou',        'traore.seydou',    'traore.seydou@dostracker.ci',   '$2b$12$HASH_ICI', 3),
('OUATTARA Nadia',       'ouattara.nadia',   'ouattara.nadia@dostracker.ci',  '$2b$12$HASH_ICI', 3),

-- ADMIN (service_id = 4)
('Administrateur',       'admin',            'admin@dostracker.ci',           '$2b$12$HASH_ICI', 4);

-- >> Remplacer $2b$12$HASH_ICI par de vrais hash bcrypt
-- >> Python : from passlib.context import CryptContext
-- >>          CryptContext(schemes=["bcrypt"]).hash("MonMotDePasse")


-- ================================================================
-- RÉSUMÉ
-- ================================================================
--
--  TABLES (9)
--  ─────────────────────────────────────────────────────────────
--  services           3 services actifs + ADMIN (données fixes)
--  users              Agents — reliés à services via service_id (FK)
--  proprietaires      "Demandeur" — 1 propriétaire peut avoir N dossiers
--  dossiers     ⭐    TABLE CENTRALE — 1 dossier = 1 demande
--  motifs_ref         8 motifs prédéfinis (checkboxes SCVAA)
--  workflow_history   Traçabilité : qui/quoi/quand
--  commentaires       Notes inter-services
--  pieces_jointes     Documents scannés (Supabase Storage)
--  sms_log            Journal SMS Twilio
--
--  VUES (4)
--  ─────────────────────────────────────────────────────────────
--  v_dossiers         Listing complet avec jointures
--  v_stats_statut     Comptage par étape du workflow
--  v_stats_region     Répartition géographique
--  v_activite_agents  Dossiers traités par agent
--
--  CHAMPS EXACTS PAR SERVICE (cahier des charges)
--  ─────────────────────────────────────────────────────────────
--  COURRIER  : Numero de Dossier, Date d'enregistrement, REGION,
--              Prefecture, Sous-Préfecture, Village, Numero du CF,
--              Demandeur, Contact
--
--  SPFEI (1) : NATIONALITE, Genre, Type CF,
--              Date Enquête Officielle, Date Validation Enq Officielle,
--              Date d'établissement du CF, Date de demande d'immatriculation
--
--  SCVAA     : Superficie en ha, date de bornage,
--              Géomètre Expert, Contact
--              + Conformité + Motifs d'inconformité (8 checkboxes + autre)
--
--  SPFEI (2) : CONSERVATION, N° TITRE FONCIER
--
--  Conservation Foncière = destination finale (pas de service actif)
-- ================================================================