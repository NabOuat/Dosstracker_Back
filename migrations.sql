-- ================================================================
--  DosTracker — Migration : tables manquantes
--  À exécuter dans l'éditeur SQL de Supabase
-- ================================================================


-- ── 1. Configuration système ───────────────────────────────────────────────────
-- Stocke les paramètres configurables depuis le panneau admin
-- (ex : délai de modification autorisé par le SERVICE COURRIER)

CREATE TABLE IF NOT EXISTS system_config (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Valeur par défaut : 24 heures de délai de modification
INSERT INTO system_config (key, value)
VALUES ('delai_modification_heures', '24')
ON CONFLICT (key) DO NOTHING;


-- ── 2. Motifs de non-conformité (gérés par l'admin) ───────────────────────────
-- Liste dynamique que l'admin peut compléter / supprimer
-- Distinct de motifs_ref qui est la référence statique du cahier des charges

CREATE TABLE IF NOT EXISTS motifs_nonconformite (
    id         UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    libelle    TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Motifs initiaux (identiques à motifs_ref pour cohérence)
INSERT INTO motifs_nonconformite (libelle) VALUES
    ('Limites non bornées'),
    ('Plan cadastral incomplet'),
    ('Documents manquants'),
    ('Surface non conforme'),
    ('Chevauchement de parcelles')
ON CONFLICT DO NOTHING;


-- ── 3. Demandes de droits de modification ─────────────────────────────────────
-- Un agent SERVICE COURRIER soumet une demande quand le délai de modification
-- est expiré. L'admin peut l'approuver ou la rejeter.

CREATE TABLE IF NOT EXISTS demandes_droits (
    id             UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    dossier_id     UUID        NOT NULL REFERENCES dossiers(id)  ON DELETE CASCADE,
    user_id        UUID        NOT NULL REFERENCES users(id)     ON DELETE RESTRICT,
    motif          TEXT        NOT NULL,
    statut         TEXT        NOT NULL DEFAULT 'EN_ATTENTE'
                               CHECK (statut IN ('EN_ATTENTE', 'APPROUVE', 'REJETE')),
    traite_par_id  UUID        REFERENCES users(id) ON DELETE SET NULL,
    traite_at      TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_demandes_droits_dossier ON demandes_droits(dossier_id);
CREATE INDEX IF NOT EXISTS idx_demandes_droits_statut  ON demandes_droits(statut);
CREATE INDEX IF NOT EXISTS idx_demandes_droits_user    ON demandes_droits(user_id);
