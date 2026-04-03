-- ================================================================
-- MIGRATIONS — Nouvelles Fonctionnalités DosTracker
-- ================================================================
-- 1. Attribution de Titre Foncier (champs enrichis)
-- 2. Retour de Correction (dossiers non conformes)
-- 3. Retour de Conservation (SCVAA)
-- 4. Demande de Signature APFR (multi-dossiers)
-- ================================================================

-- ================================================================
-- ÉTAPE 1 : Modifier l'ENUM statut_dossier
-- ================================================================

ALTER TYPE statut_dossier ADD VALUE 'RETOUR_CORRECTION' AFTER 'NON_CONFORME';
ALTER TYPE statut_dossier ADD VALUE 'RETOUR_CONSERVATION' AFTER 'RETOUR_CORRECTION';
ALTER TYPE statut_dossier ADD VALUE 'ATTENTE_SIGNATURE_APFR' AFTER 'RETOUR_CONSERVATION';

-- ================================================================
-- ÉTAPE 2 : Enrichir la table dossiers
-- (Attribution de Titre + Retour Conservation)
-- ================================================================

-- Ajouter les nouveaux champs pour l'attribution de titre
ALTER TABLE dossiers ADD COLUMN date_transmission DATE;
ALTER TABLE dossiers ADD COLUMN reference_courier_dg VARCHAR(100);
-- Le PDF est stocké dans pieces_jointes avec type_fichier='PDF'

-- Ajouter les champs pour le retour de conservation (SCVAA)
ALTER TABLE dossiers ADD COLUMN num_titre_foncier_conservation VARCHAR(100);
ALTER TABLE dossiers ADD COLUMN superficie_conservation NUMERIC(10, 4);
ALTER TABLE dossiers ADD COLUMN reference_courier_conservation VARCHAR(100);
-- Le PDF de conservation est stocké dans pieces_jointes

-- Ajouter le champ pour tracer l'agent qui a traité le retour de conservation
ALTER TABLE dossiers ADD COLUMN agent_retour_conservation_id UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE dossiers ADD COLUMN date_retour_conservation TIMESTAMPTZ;

-- ================================================================
-- ÉTAPE 3 : Créer la table corrections_dossier
-- (Traçabilité des retours de correction)
-- ================================================================

CREATE TABLE corrections_dossier (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dossier_id UUID NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
    
    -- Agent qui transmet le dossier en retour
    agent_transmettant_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    
    -- Date et éléments du retour
    date_retour_correction TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    elements_transmis TEXT NOT NULL,  -- Description des éléments/corrections demandées
    
    -- Statut du retour
    statut VARCHAR(50) NOT NULL DEFAULT 'EN_ATTENTE',  -- EN_ATTENTE, RECU, TRAITE
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_corrections_dossier ON corrections_dossier(dossier_id);
CREATE INDEX idx_corrections_agent ON corrections_dossier(agent_transmettant_id);
CREATE INDEX idx_corrections_statut ON corrections_dossier(statut);

COMMENT ON TABLE corrections_dossier IS 'Traçabilité des retours de correction pour dossiers NON_CONFORME';
COMMENT ON COLUMN corrections_dossier.elements_transmis IS 'Description des éléments retournés et corrections demandées';

-- Trigger updated_at pour corrections_dossier
CREATE TRIGGER trg_corrections_dossier_updated_at
    BEFORE UPDATE ON corrections_dossier
    FOR EACH ROW EXECUTE FUNCTION fn_updated_at();

-- ================================================================
-- ÉTAPE 4 : Créer la table demandes_signature_apfr
-- (Demandes de signature groupées par plusieurs dossiers)
-- ================================================================

CREATE TABLE demandes_signature_apfr (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Identification de la demande
    numero_demande VARCHAR(100) NOT NULL UNIQUE,
    date_creation TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Agent du SERVICE SPFEI qui crée la demande
    agent_spfei_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    
    -- Statut de la demande
    statut VARCHAR(50) NOT NULL DEFAULT 'EN_ATTENTE',  
    -- EN_ATTENTE, SIGNEE, REJETEE
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_apfr_statut ON demandes_signature_apfr(statut);
CREATE INDEX idx_apfr_agent ON demandes_signature_apfr(agent_spfei_id);
CREATE INDEX idx_apfr_created ON demandes_signature_apfr(created_at DESC);

COMMENT ON TABLE demandes_signature_apfr IS 'Demandes de signature APFR groupant plusieurs dossiers';

-- Trigger updated_at
CREATE TRIGGER trg_apfr_updated_at
    BEFORE UPDATE ON demandes_signature_apfr
    FOR EACH ROW EXECUTE FUNCTION fn_updated_at();

-- ================================================================
-- ÉTAPE 5 : Créer la table de liaison dossiers_apfr
-- (Relation many-to-many entre dossiers et demandes APFR)
-- ================================================================

CREATE TABLE dossiers_apfr (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dossier_id UUID NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
    demande_apfr_id UUID NOT NULL REFERENCES demandes_signature_apfr(id) ON DELETE CASCADE,
    
    -- Ordre dans la demande (pour affichage)
    ordre SMALLINT NOT NULL DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(dossier_id, demande_apfr_id)
);

CREATE INDEX idx_dossiers_apfr_dossier ON dossiers_apfr(dossier_id);
CREATE INDEX idx_dossiers_apfr_demande ON dossiers_apfr(demande_apfr_id);

COMMENT ON TABLE dossiers_apfr IS 'Liaison many-to-many : dossiers inclus dans une demande APFR';

-- ================================================================
-- ÉTAPE 6 : Créer la table pieces_jointes
-- (PDFs et images attachés aux dossiers)
-- ================================================================

CREATE TABLE IF NOT EXISTS pieces_jointes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dossier_id UUID NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    service_id INTEGER,

    -- Informations du fichier
    nom_original VARCHAR(255) NOT NULL,
    url_stockage TEXT NOT NULL,
    type_fichier VARCHAR(10) NOT NULL CHECK (type_fichier IN ('PDF', 'IMAGE')),
    taille_octets INTEGER NOT NULL,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pieces_jointes_dossier ON pieces_jointes(dossier_id);
CREATE INDEX idx_pieces_jointes_user ON pieces_jointes(user_id);

COMMENT ON TABLE pieces_jointes IS 'Pièces jointes (PDFs et images) associées aux dossiers fonciers';

-- ================================================================
-- ÉTAPE 7 : Mettre à jour la vue v_dossiers
-- ================================================================

DROP VIEW IF EXISTS v_dossiers CASCADE;

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

    -- SERVICE SPFEI - Titre (enrichi)
    d.date_transmission,
    d.reference_courier_dg,
    d.conservation,
    d.numero_titre_foncier,
    ut.nom_complet  AS agent_spfei_titre,
    d.date_attribution_titre,
    d.date_envoi_conservation,

    -- Retour Conservation (SCVAA)
    d.num_titre_foncier_conservation,
    d.superficie_conservation,
    d.reference_courier_conservation,
    urc.nom_complet AS agent_retour_conservation,
    d.date_retour_conservation,

    d.created_at,
    d.updated_at

FROM dossiers d
JOIN  proprietaires p ON p.id  = d.proprietaire_id
LEFT JOIN users uc    ON uc.id = d.agent_courrier_id
LEFT JOIN users ua    ON ua.id = d.agent_spfei_admin_id
LEFT JOIN users us    ON us.id = d.agent_scvaa_id
LEFT JOIN users ut    ON ut.id = d.agent_spfei_titre_id
LEFT JOIN users urc   ON urc.id = d.agent_retour_conservation_id;

-- ================================================================
-- ÉTAPE 8 : Créer une vue pour les demandes APFR avec dossiers
-- ================================================================

CREATE VIEW v_demandes_apfr_detail AS
SELECT
    dsa.id AS demande_id,
    dsa.numero_demande,
    dsa.statut,
    dsa.date_creation,
    us.nom_complet AS agent_spfei,
    COUNT(da.dossier_id) AS nombre_dossiers,
    STRING_AGG(d.numero_dossier, ', ' ORDER BY da.ordre) AS dossiers_list
FROM demandes_signature_apfr dsa
JOIN users us ON us.id = dsa.agent_spfei_id
LEFT JOIN dossiers_apfr da ON da.demande_apfr_id = dsa.id
LEFT JOIN dossiers d ON d.id = da.dossier_id
GROUP BY dsa.id, dsa.numero_demande, dsa.statut, dsa.date_creation, us.nom_complet;

-- ================================================================
-- ÉTAPE 9 : Ajouter des commentaires de documentation
-- ================================================================

COMMENT ON COLUMN dossiers.date_transmission IS 'Date de transmission du dossier pour attribution titre (SERVICE SPFEI)';
COMMENT ON COLUMN dossiers.reference_courier_dg IS 'Référence du courrier du DG pour attribution titre';
COMMENT ON COLUMN dossiers.num_titre_foncier_conservation IS 'Numéro du titre foncier retourné par la conservation (SCVAA)';
COMMENT ON COLUMN dossiers.superficie_conservation IS 'Superficie confirmée par la conservation (SCVAA)';
COMMENT ON COLUMN dossiers.reference_courier_conservation IS 'Référence du courrier de la conservation (SCVAA)';
COMMENT ON COLUMN dossiers.agent_retour_conservation_id IS 'Agent SCVAA qui a traité le retour de conservation';
COMMENT ON COLUMN dossiers.date_retour_conservation IS 'Date du retour de conservation';

-- ================================================================
-- RÉSUMÉ DES MODIFICATIONS
-- ================================================================
--
-- NOUVELLES TABLES (4)
-- ─────────────────────────────────────────────────────────────
-- corrections_dossier      Traçabilité des retours de correction (NON_CONFORME)
-- demandes_signature_apfr  Demandes de signature groupées (SERVICE SPFEI)
-- dossiers_apfr            Liaison many-to-many dossiers ↔ demandes APFR
-- pieces_jointes           PDFs et images attachés aux dossiers
--
-- MODIFICATIONS ENUM (3)
-- ─────────────────────────────────────────────────────────────
-- RETOUR_CORRECTION        Dossier retourné pour corrections (SCVAA → SCVAA)
-- RETOUR_CONSERVATION      Dossier retourné par conservation (CONSERVATION → SCVAA)
-- ATTENTE_SIGNATURE_APFR   Dossier en attente signature APFR (SERVICE SPFEI)
--
-- NOUVEAUX CHAMPS dossiers (7)
-- ─────────────────────────────────────────────────────────────
-- date_transmission                Date transmission titre
-- reference_courier_dg             Référence courrier DG
-- num_titre_foncier_conservation   Titre retourné par conservation
-- superficie_conservation          Superficie confirmée
-- reference_courier_conservation   Référence courrier conservation
-- agent_retour_conservation_id     Agent SCVAA retour
-- date_retour_conservation         Date retour conservation
--
-- NOUVELLES VUES (1)
-- ─────────────────────────────────────────────────────────────
-- v_demandes_apfr_detail   Demandes APFR avec détail dossiers
--
-- ================================================================
