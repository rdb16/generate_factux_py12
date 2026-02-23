-- Base k_factur_x dans PG 16
-- Table sent_invoices avec statut, exception et trigger

-- Enum pour le statut d'envoi
DO $$ BEGIN
    CREATE TYPE invoice_status AS ENUM ('PENDING', 'SENT-OK', 'SENT-ERROR');
EXCEPTION
    WHEN duplicate_object THEN
        -- Le type existe avec d'anciennes valeurs : on supprime la table et le type puis on recrée
        DROP TABLE IF EXISTS sent_invoices;
        DROP TYPE invoice_status;
        CREATE TYPE invoice_status AS ENUM ('PENDING', 'SENT-OK', 'SENT-ERROR');
END $$;

CREATE TABLE IF NOT EXISTS sent_invoices (
    invoice_num     VARCHAR(50)              PRIMARY KEY,
    company_name    VARCHAR(255)             NOT NULL,
    company_siret   VARCHAR(14)              NOT NULL,
    xml_facture     XML                      NOT NULL,
    pdf_path        VARCHAR(500)             NOT NULL,
    invoice_date    DATE                     NOT NULL,
    total_ttc       NUMERIC(12,2)            DEFAULT NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sent_at         TIMESTAMP WITH TIME ZONE DEFAULT NULL,   
    sent_status     invoice_status           DEFAULT 'PENDING',
    pa_id           BIGINT                   DEFAULT NULL,
    pa_validation   BOOLEAN                  DEFAULT NULL,
    exception       TEXT                     DEFAULT NULL   
);

-- Index
CREATE INDEX IF NOT EXISTS idx_sent_invoices_company_name
    ON sent_invoices (company_name);

CREATE INDEX IF NOT EXISTS idx_sent_invoices_company_siret
    ON sent_invoices (company_siret);

CREATE INDEX IF NOT EXISTS idx_sent_invoices_invoice_date
    ON sent_invoices (invoice_date);

CREATE INDEX IF NOT EXISTS idx_sent_invoices_sent_status
    ON sent_invoices (sent_status);


