-- Base k_factur_x dans PG 16
-- Ajout du statut et du champ exception sur sent_invoices

-- Enum pour le statut d'envoi
DO $$ BEGIN
    CREATE TYPE invoice_status AS ENUM ('OK', 'KO');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Nouvelles colonnes
ALTER TABLE sent_invoices
    ADD COLUMN IF NOT EXISTS status    invoice_status DEFAULT 'OK',
    ADD COLUMN IF NOT EXISTS exception TEXT           DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS total_ttc NUMERIC(12,2)  DEFAULT NULL;

-- Index sur le statut
CREATE INDEX IF NOT EXISTS idx_sent_invoices_status
    ON sent_invoices (status);

-- Trigger : exception obligatoire quand status = 'KO'
CREATE OR REPLACE FUNCTION check_exception_on_ko()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'KO' AND (NEW.exception IS NULL OR TRIM(NEW.exception) = '') THEN
        RAISE EXCEPTION 'Le champ exception est obligatoire quand status vaut KO';
    END IF;
    -- Si status = 'OK', on force exception à NULL
    IF NEW.status = 'OK' THEN
        NEW.exception := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_exception_on_ko ON sent_invoices;

CREATE TRIGGER trg_check_exception_on_ko
    BEFORE INSERT OR UPDATE ON sent_invoices
    FOR EACH ROW
    EXECUTE FUNCTION check_exception_on_ko();
