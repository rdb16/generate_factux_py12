-- ============================================================
-- Migration : rattacher chaque facture à son émetteur
-- A lancer manuellement : psql -f resources/sql/alter_add_emitter_siret.sql
-- ============================================================
-- Ajoute l'identifiant de NOTRE émetteur sur les factures :
--   - sent_invoices.emitter_siret     : SIRET de l'émetteur ayant généré la facture
--   - incoming_invoices.recipient_siret : SIRET de l'émetteur destinataire
-- Les lignes existantes sont rattachées à l'émetteur historique
-- (Burger Queen, SIRET 00000000200000), seul émetteur avant cette migration.
-- ============================================================

-- Factures générées
ALTER TABLE sent_invoices
    ADD COLUMN IF NOT EXISTS emitter_siret VARCHAR(14);

UPDATE sent_invoices
    SET emitter_siret = '00000000200000'
    WHERE emitter_siret IS NULL;

CREATE INDEX IF NOT EXISTS idx_sent_invoices_emitter_siret
    ON sent_invoices (emitter_siret);

-- Factures reçues
ALTER TABLE incoming_invoices
    ADD COLUMN IF NOT EXISTS recipient_siret VARCHAR(14);

UPDATE incoming_invoices
    SET recipient_siret = '00000000200000'
    WHERE recipient_siret IS NULL;

CREATE INDEX IF NOT EXISTS idx_incoming_invoices_recipient_siret
    ON incoming_invoices (recipient_siret);
