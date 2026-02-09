-- Base k_factur_x dans PG 16
-- Métadonnées client nécessaires à l'émission d'une Factur-X

CREATE TABLE IF NOT EXISTS client_metadata (
    id                  SERIAL                   PRIMARY KEY,
    recipient_name      VARCHAR(255)             NOT NULL,
    cie_legal_form      VARCHAR(20),
    recipient_siret     VARCHAR(14)              NOT NULL UNIQUE,
    recipient_vat_number VARCHAR(20),
    recipient_address   VARCHAR(500),
    recipient_postal_code VARCHAR(10),
    recipient_city      VARCHAR(100),
    recipient_country_code VARCHAR(2)            NOT NULL DEFAULT 'FR',
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_client_metadata_siret
    ON client_metadata (recipient_siret);

CREATE INDEX IF NOT EXISTS idx_client_metadata_name
    ON client_metadata (recipient_name);
