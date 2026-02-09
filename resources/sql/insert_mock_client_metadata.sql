-- Données mock pour la table client_metadata

INSERT INTO client_metadata (recipient_name, cie_legal_form, recipient_siret, recipient_vat_number, recipient_address, recipient_postal_code, recipient_city, recipient_country_code)
VALUES
    ('Dupont & Fils',          'SARL',   '12345678900011', 'FR12345678901', '15 rue de la Paix',         '75002', 'Paris',     'FR'),
    ('Tech Solutions Europe',  'SAS',    '98765432100022', 'FR98765432102', '8 avenue des Champs',       '69003', 'Lyon',      'FR'),
    ('Boulangerie Martin',     'EI',     '45678912300033', 'FR45678912303', '3 place du Marché',         '33000', 'Bordeaux',  'FR'),
    ('Schmidt & Partner GmbH', 'GmbH',   '55443322110044', 'DE123456789',   '12 Friedrichstrasse',       '10117', 'Berlin',    'DE'),
    ('Garage Leroy Automobile', 'SA',    '66778899000055', 'FR66778899005', '120 route Nationale 7',     '13100', 'Aix-en-Provence', 'FR');
