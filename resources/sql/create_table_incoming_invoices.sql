-- Base k_factur_x dans PG 16
-- Factures reçues depuis la plateforme agréée

CREATE TABLE IF NOT EXISTS incoming_invoices (
    invoice_num     VARCHAR(50)              PRIMARY KEY,
    company_name    VARCHAR(255)             NOT NULL,
    company_siret   VARCHAR(14)              NOT NULL,
    xml_facture     XML                      NOT NULL,
    pdf_path        VARCHAR(500)             NOT NULL,
    invoice_date    DATE                     NOT NULL,
    received_at     TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_incoming_invoices_company_name
    ON incoming_invoices (company_name);

CREATE INDEX IF NOT EXISTS idx_incoming_invoices_company_siret
    ON incoming_invoices (company_siret);

CREATE INDEX IF NOT EXISTS idx_incoming_invoices_invoice_date
    ON incoming_invoices (invoice_date);
