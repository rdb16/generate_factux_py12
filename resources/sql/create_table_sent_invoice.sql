-- Base k_factur_x dans PG 16

CREATE TABLE IF NOT EXISTS sent_invoices (
    invoice_num     VARCHAR(50)              PRIMARY KEY,
    company_name    VARCHAR(255)             NOT NULL,
    company_siret   VARCHAR(14)              NOT NULL,
    xml_facture     XML                      NOT NULL,
    pdf_path        VARCHAR(500)             NOT NULL,
    invoice_date    DATE                     NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    validated_at    TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_sent_invoices_company_name
    ON sent_invoices (company_name);

CREATE INDEX IF NOT EXISTS idx_sent_invoices_company_siret
    ON sent_invoices (company_siret);

CREATE INDEX IF NOT EXISTS idx_sent_invoices_invoice_date
    ON sent_invoices (invoice_date);
