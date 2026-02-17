-- ============================================================
-- Insertion de 3 factures de test dans incoming_invoices
-- A lancer manuellement : psql -f resources/sql/insert_mock_incoming_invoices.sql
-- ============================================================
-- Pre-requis : la table incoming_invoices doit exister
--   (cf. resources/sql/create_table_incoming_invoices.sql)
-- Les fichiers PDF et XML correspondants sont dans :
--   data/incoming-invoices/
-- ============================================================

-- 1) Papeterie Centrale SAS - Fournitures de bureau
INSERT INTO incoming_invoices (
    invoice_num,
    company_name,
    company_siret,
    xml_facture,
    pdf_path,
    invoice_date,
    total_ttc,
    received_at
) VALUES (
    'FRNS-2026-001',
    'Papeterie Centrale SAS',
    '98765432100011',
    XMLPARSE(DOCUMENT '<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
    <rsm:ExchangedDocumentContext>
        <ram:GuidelineSpecifiedDocumentContextParameter>
            <ram:ID>urn:cen.eu:en16931:2017</ram:ID>
        </ram:GuidelineSpecifiedDocumentContextParameter>
    </rsm:ExchangedDocumentContext>
    <rsm:ExchangedDocument>
        <ram:ID>FRNS-2026-001</ram:ID>
        <ram:TypeCode>380</ram:TypeCode>
        <ram:IssueDateTime>
            <udt:DateTimeString format="102">20260115</udt:DateTimeString>
        </ram:IssueDateTime>
    </rsm:ExchangedDocument>
    <rsm:SupplyChainTradeTransaction>
        <ram:IncludedSupplyChainTradeLineItem>
            <ram:AssociatedDocumentLineDocument><ram:LineID>1</ram:LineID></ram:AssociatedDocumentLineDocument>
            <ram:SpecifiedTradeProduct><ram:Name>Ramettes papier A4 80g (x20)</ram:Name></ram:SpecifiedTradeProduct>
            <ram:SpecifiedLineTradeAgreement><ram:NetPriceProductTradePrice><ram:ChargeAmount>4.50</ram:ChargeAmount></ram:NetPriceProductTradePrice></ram:SpecifiedLineTradeAgreement>
            <ram:SpecifiedLineTradeDelivery><ram:BilledQuantity unitCode="C62">20</ram:BilledQuantity></ram:SpecifiedLineTradeDelivery>
            <ram:SpecifiedLineTradeSettlement>
                <ram:ApplicableTradeTax><ram:TypeCode>VAT</ram:TypeCode><ram:CategoryCode>S</ram:CategoryCode><ram:RateApplicablePercent>20.00</ram:RateApplicablePercent></ram:ApplicableTradeTax>
                <ram:SpecifiedTradeSettlementLineMonetarySummation><ram:LineTotalAmount>90.00</ram:LineTotalAmount></ram:SpecifiedTradeSettlementLineMonetarySummation>
            </ram:SpecifiedLineTradeSettlement>
        </ram:IncludedSupplyChainTradeLineItem>
        <ram:IncludedSupplyChainTradeLineItem>
            <ram:AssociatedDocumentLineDocument><ram:LineID>2</ram:LineID></ram:AssociatedDocumentLineDocument>
            <ram:SpecifiedTradeProduct><ram:Name>Cartouches encre imprimante HP (x5)</ram:Name></ram:SpecifiedTradeProduct>
            <ram:SpecifiedLineTradeAgreement><ram:NetPriceProductTradePrice><ram:ChargeAmount>39.80</ram:ChargeAmount></ram:NetPriceProductTradePrice></ram:SpecifiedLineTradeAgreement>
            <ram:SpecifiedLineTradeDelivery><ram:BilledQuantity unitCode="C62">5</ram:BilledQuantity></ram:SpecifiedLineTradeDelivery>
            <ram:SpecifiedLineTradeSettlement>
                <ram:ApplicableTradeTax><ram:TypeCode>VAT</ram:TypeCode><ram:CategoryCode>S</ram:CategoryCode><ram:RateApplicablePercent>20.00</ram:RateApplicablePercent></ram:ApplicableTradeTax>
                <ram:SpecifiedTradeSettlementLineMonetarySummation><ram:LineTotalAmount>199.00</ram:LineTotalAmount></ram:SpecifiedTradeSettlementLineMonetarySummation>
            </ram:SpecifiedLineTradeSettlement>
        </ram:IncludedSupplyChainTradeLineItem>
        <ram:ApplicableHeaderTradeAgreement>
            <ram:SellerTradeParty>
                <ram:Name>Papeterie Centrale SAS</ram:Name>
                <ram:SpecifiedLegalOrganization><ram:ID schemeID="0002">987654321</ram:ID></ram:SpecifiedLegalOrganization>
                <ram:PostalTradeAddress><ram:LineOne>45 avenue des Champs</ram:LineOne><ram:PostcodeCode>69003</ram:PostcodeCode><ram:CityName>Lyon</ram:CityName><ram:CountryID>FR</ram:CountryID></ram:PostalTradeAddress>
                <ram:URIUniversalCommunication><ram:URIID schemeID="0009">98765432100011</ram:URIID></ram:URIUniversalCommunication>
                <ram:SpecifiedTaxRegistration><ram:ID schemeID="VA">FR98765432101</ram:ID></ram:SpecifiedTaxRegistration>
            </ram:SellerTradeParty>
            <ram:BuyerTradeParty>
                <ram:Name>Mon Entreprise DUPONT LA JOIE</ram:Name>
                <ram:SpecifiedLegalOrganization><ram:ID schemeID="0002">123456789</ram:ID></ram:SpecifiedLegalOrganization>
                <ram:PostalTradeAddress><ram:LineOne>12 rue de la Paix</ram:LineOne><ram:PostcodeCode>75001</ram:PostcodeCode><ram:CityName>Paris</ram:CityName><ram:CountryID>FR</ram:CountryID></ram:PostalTradeAddress>
                <ram:URIUniversalCommunication><ram:URIID schemeID="0009">12345678900012</ram:URIID></ram:URIUniversalCommunication>
                <ram:SpecifiedTaxRegistration><ram:ID schemeID="VA">FR12345678901</ram:ID></ram:SpecifiedTaxRegistration>
            </ram:BuyerTradeParty>
        </ram:ApplicableHeaderTradeAgreement>
        <ram:ApplicableHeaderTradeDelivery>
            <ram:ActualDeliverySupplyChainEvent><ram:OccurrenceDateTime><udt:DateTimeString format="102">20260115</udt:DateTimeString></ram:OccurrenceDateTime></ram:ActualDeliverySupplyChainEvent>
        </ram:ApplicableHeaderTradeDelivery>
        <ram:ApplicableHeaderTradeSettlement>
            <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
            <ram:ApplicableTradeTax><ram:CalculatedAmount>57.80</ram:CalculatedAmount><ram:TypeCode>VAT</ram:TypeCode><ram:BasisAmount>289.00</ram:BasisAmount><ram:CategoryCode>S</ram:CategoryCode><ram:RateApplicablePercent>20.00</ram:RateApplicablePercent></ram:ApplicableTradeTax>
            <ram:SpecifiedTradePaymentTerms><ram:DueDateDateTime><udt:DateTimeString format="102">20260215</udt:DateTimeString></ram:DueDateDateTime></ram:SpecifiedTradePaymentTerms>
            <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
                <ram:LineTotalAmount>289.00</ram:LineTotalAmount>
                <ram:TaxBasisTotalAmount>289.00</ram:TaxBasisTotalAmount>
                <ram:TaxTotalAmount currencyID="EUR">57.80</ram:TaxTotalAmount>
                <ram:GrandTotalAmount>346.80</ram:GrandTotalAmount>
                <ram:DuePayableAmount>346.80</ram:DuePayableAmount>
            </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        </ram:ApplicableHeaderTradeSettlement>
    </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>'),
    './data/incoming-invoices/facture-FRNS-2026-001.pdf',
    '2026-01-15',
    346.80,
    '2026-01-20 09:30:00+01'
);

-- 2) InfoTech Services SARL - Maintenance informatique
INSERT INTO incoming_invoices (
    invoice_num,
    company_name,
    company_siret,
    xml_facture,
    pdf_path,
    invoice_date,
    total_ttc,
    received_at
) VALUES (
    'IT-2026-0042',
    'InfoTech Services SARL',
    '55443322100033',
    XMLPARSE(DOCUMENT '<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
    <rsm:ExchangedDocumentContext>
        <ram:GuidelineSpecifiedDocumentContextParameter>
            <ram:ID>urn:cen.eu:en16931:2017</ram:ID>
        </ram:GuidelineSpecifiedDocumentContextParameter>
    </rsm:ExchangedDocumentContext>
    <rsm:ExchangedDocument>
        <ram:ID>IT-2026-0042</ram:ID>
        <ram:TypeCode>380</ram:TypeCode>
        <ram:IssueDateTime>
            <udt:DateTimeString format="102">20260128</udt:DateTimeString>
        </ram:IssueDateTime>
    </rsm:ExchangedDocument>
    <rsm:SupplyChainTradeTransaction>
        <ram:IncludedSupplyChainTradeLineItem>
            <ram:AssociatedDocumentLineDocument><ram:LineID>1</ram:LineID></ram:AssociatedDocumentLineDocument>
            <ram:SpecifiedTradeProduct><ram:Name>Maintenance informatique trimestrielle - Forfait</ram:Name></ram:SpecifiedTradeProduct>
            <ram:SpecifiedLineTradeAgreement><ram:NetPriceProductTradePrice><ram:ChargeAmount>900.00</ram:ChargeAmount></ram:NetPriceProductTradePrice></ram:SpecifiedLineTradeAgreement>
            <ram:SpecifiedLineTradeDelivery><ram:BilledQuantity unitCode="C62">1</ram:BilledQuantity></ram:SpecifiedLineTradeDelivery>
            <ram:SpecifiedLineTradeSettlement>
                <ram:ApplicableTradeTax><ram:TypeCode>VAT</ram:TypeCode><ram:CategoryCode>S</ram:CategoryCode><ram:RateApplicablePercent>20.00</ram:RateApplicablePercent></ram:ApplicableTradeTax>
                <ram:SpecifiedTradeSettlementLineMonetarySummation><ram:LineTotalAmount>900.00</ram:LineTotalAmount></ram:SpecifiedTradeSettlementLineMonetarySummation>
            </ram:SpecifiedLineTradeSettlement>
        </ram:IncludedSupplyChainTradeLineItem>
        <ram:IncludedSupplyChainTradeLineItem>
            <ram:AssociatedDocumentLineDocument><ram:LineID>2</ram:LineID></ram:AssociatedDocumentLineDocument>
            <ram:SpecifiedTradeProduct><ram:Name>Remplacement disque SSD serveur NAS</ram:Name></ram:SpecifiedTradeProduct>
            <ram:SpecifiedLineTradeAgreement><ram:NetPriceProductTradePrice><ram:ChargeAmount>120.00</ram:ChargeAmount></ram:NetPriceProductTradePrice></ram:SpecifiedLineTradeAgreement>
            <ram:SpecifiedLineTradeDelivery><ram:BilledQuantity unitCode="C62">2</ram:BilledQuantity></ram:SpecifiedLineTradeDelivery>
            <ram:SpecifiedLineTradeSettlement>
                <ram:ApplicableTradeTax><ram:TypeCode>VAT</ram:TypeCode><ram:CategoryCode>S</ram:CategoryCode><ram:RateApplicablePercent>20.00</ram:RateApplicablePercent></ram:ApplicableTradeTax>
                <ram:SpecifiedTradeSettlementLineMonetarySummation><ram:LineTotalAmount>240.00</ram:LineTotalAmount></ram:SpecifiedTradeSettlementLineMonetarySummation>
            </ram:SpecifiedLineTradeSettlement>
        </ram:IncludedSupplyChainTradeLineItem>
        <ram:IncludedSupplyChainTradeLineItem>
            <ram:AssociatedDocumentLineDocument><ram:LineID>3</ram:LineID></ram:AssociatedDocumentLineDocument>
            <ram:SpecifiedTradeProduct><ram:Name>Licence antivirus annuelle (10 postes)</ram:Name></ram:SpecifiedTradeProduct>
            <ram:SpecifiedLineTradeAgreement><ram:NetPriceProductTradePrice><ram:ChargeAmount>60.00</ram:ChargeAmount></ram:NetPriceProductTradePrice></ram:SpecifiedLineTradeAgreement>
            <ram:SpecifiedLineTradeDelivery><ram:BilledQuantity unitCode="C62">1</ram:BilledQuantity></ram:SpecifiedLineTradeDelivery>
            <ram:SpecifiedLineTradeSettlement>
                <ram:ApplicableTradeTax><ram:TypeCode>VAT</ram:TypeCode><ram:CategoryCode>S</ram:CategoryCode><ram:RateApplicablePercent>20.00</ram:RateApplicablePercent></ram:ApplicableTradeTax>
                <ram:SpecifiedTradeSettlementLineMonetarySummation><ram:LineTotalAmount>60.00</ram:LineTotalAmount></ram:SpecifiedTradeSettlementLineMonetarySummation>
            </ram:SpecifiedLineTradeSettlement>
        </ram:IncludedSupplyChainTradeLineItem>
        <ram:ApplicableHeaderTradeAgreement>
            <ram:SellerTradeParty>
                <ram:Name>InfoTech Services SARL</ram:Name>
                <ram:SpecifiedLegalOrganization><ram:ID schemeID="0002">554433221</ram:ID></ram:SpecifiedLegalOrganization>
                <ram:PostalTradeAddress><ram:LineOne>8 rue du Progres</ram:LineOne><ram:PostcodeCode>31000</ram:PostcodeCode><ram:CityName>Toulouse</ram:CityName><ram:CountryID>FR</ram:CountryID></ram:PostalTradeAddress>
                <ram:URIUniversalCommunication><ram:URIID schemeID="0009">55443322100033</ram:URIID></ram:URIUniversalCommunication>
                <ram:SpecifiedTaxRegistration><ram:ID schemeID="VA">FR55443322101</ram:ID></ram:SpecifiedTaxRegistration>
            </ram:SellerTradeParty>
            <ram:BuyerTradeParty>
                <ram:Name>Mon Entreprise DUPONT LA JOIE</ram:Name>
                <ram:SpecifiedLegalOrganization><ram:ID schemeID="0002">123456789</ram:ID></ram:SpecifiedLegalOrganization>
                <ram:PostalTradeAddress><ram:LineOne>12 rue de la Paix</ram:LineOne><ram:PostcodeCode>75001</ram:PostcodeCode><ram:CityName>Paris</ram:CityName><ram:CountryID>FR</ram:CountryID></ram:PostalTradeAddress>
                <ram:URIUniversalCommunication><ram:URIID schemeID="0009">12345678900012</ram:URIID></ram:URIUniversalCommunication>
                <ram:SpecifiedTaxRegistration><ram:ID schemeID="VA">FR12345678901</ram:ID></ram:SpecifiedTaxRegistration>
            </ram:BuyerTradeParty>
        </ram:ApplicableHeaderTradeAgreement>
        <ram:ApplicableHeaderTradeDelivery>
            <ram:ActualDeliverySupplyChainEvent><ram:OccurrenceDateTime><udt:DateTimeString format="102">20260128</udt:DateTimeString></ram:OccurrenceDateTime></ram:ActualDeliverySupplyChainEvent>
        </ram:ApplicableHeaderTradeDelivery>
        <ram:ApplicableHeaderTradeSettlement>
            <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
            <ram:ApplicableTradeTax><ram:CalculatedAmount>240.00</ram:CalculatedAmount><ram:TypeCode>VAT</ram:TypeCode><ram:BasisAmount>1200.00</ram:BasisAmount><ram:CategoryCode>S</ram:CategoryCode><ram:RateApplicablePercent>20.00</ram:RateApplicablePercent></ram:ApplicableTradeTax>
            <ram:SpecifiedTradePaymentTerms><ram:DueDateDateTime><udt:DateTimeString format="102">20260228</udt:DateTimeString></ram:DueDateDateTime></ram:SpecifiedTradePaymentTerms>
            <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
                <ram:LineTotalAmount>1200.00</ram:LineTotalAmount>
                <ram:TaxBasisTotalAmount>1200.00</ram:TaxBasisTotalAmount>
                <ram:TaxTotalAmount currencyID="EUR">240.00</ram:TaxTotalAmount>
                <ram:GrandTotalAmount>1440.00</ram:GrandTotalAmount>
                <ram:DuePayableAmount>1440.00</ram:DuePayableAmount>
            </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        </ram:ApplicableHeaderTradeSettlement>
    </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>'),
    './data/incoming-invoices/facture-IT-2026-0042.pdf',
    '2026-01-28',
    1440.00,
    '2026-02-01 14:15:00+01'
);

-- 3) Energie Verte SA - Fourniture electricite
INSERT INTO incoming_invoices (
    invoice_num,
    company_name,
    company_siret,
    xml_facture,
    pdf_path,
    invoice_date,
    total_ttc,
    received_at
) VALUES (
    'EV-2026-00187',
    'Energie Verte SA',
    '77889900100022',
    XMLPARSE(DOCUMENT '<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
    <rsm:ExchangedDocumentContext>
        <ram:GuidelineSpecifiedDocumentContextParameter>
            <ram:ID>urn:cen.eu:en16931:2017</ram:ID>
        </ram:GuidelineSpecifiedDocumentContextParameter>
    </rsm:ExchangedDocumentContext>
    <rsm:ExchangedDocument>
        <ram:ID>EV-2026-00187</ram:ID>
        <ram:TypeCode>380</ram:TypeCode>
        <ram:IssueDateTime>
            <udt:DateTimeString format="102">20260205</udt:DateTimeString>
        </ram:IssueDateTime>
    </rsm:ExchangedDocument>
    <rsm:SupplyChainTradeTransaction>
        <ram:IncludedSupplyChainTradeLineItem>
            <ram:AssociatedDocumentLineDocument><ram:LineID>1</ram:LineID></ram:AssociatedDocumentLineDocument>
            <ram:SpecifiedTradeProduct><ram:Name>Fourniture electricite - Janvier 2026</ram:Name></ram:SpecifiedTradeProduct>
            <ram:SpecifiedLineTradeAgreement><ram:NetPriceProductTradePrice><ram:ChargeAmount>623.72</ram:ChargeAmount></ram:NetPriceProductTradePrice></ram:SpecifiedLineTradeAgreement>
            <ram:SpecifiedLineTradeDelivery><ram:BilledQuantity unitCode="KWH">1</ram:BilledQuantity></ram:SpecifiedLineTradeDelivery>
            <ram:SpecifiedLineTradeSettlement>
                <ram:ApplicableTradeTax><ram:TypeCode>VAT</ram:TypeCode><ram:CategoryCode>S</ram:CategoryCode><ram:RateApplicablePercent>20.00</ram:RateApplicablePercent></ram:ApplicableTradeTax>
                <ram:SpecifiedTradeSettlementLineMonetarySummation><ram:LineTotalAmount>623.72</ram:LineTotalAmount></ram:SpecifiedTradeSettlementLineMonetarySummation>
            </ram:SpecifiedLineTradeSettlement>
        </ram:IncludedSupplyChainTradeLineItem>
        <ram:IncludedSupplyChainTradeLineItem>
            <ram:AssociatedDocumentLineDocument><ram:LineID>2</ram:LineID></ram:AssociatedDocumentLineDocument>
            <ram:SpecifiedTradeProduct><ram:Name>Abonnement compteur professionnel C5</ram:Name></ram:SpecifiedTradeProduct>
            <ram:SpecifiedLineTradeAgreement><ram:NetPriceProductTradePrice><ram:ChargeAmount>119.83</ram:ChargeAmount></ram:NetPriceProductTradePrice></ram:SpecifiedLineTradeAgreement>
            <ram:SpecifiedLineTradeDelivery><ram:BilledQuantity unitCode="C62">1</ram:BilledQuantity></ram:SpecifiedLineTradeDelivery>
            <ram:SpecifiedLineTradeSettlement>
                <ram:ApplicableTradeTax><ram:TypeCode>VAT</ram:TypeCode><ram:CategoryCode>S</ram:CategoryCode><ram:RateApplicablePercent>20.00</ram:RateApplicablePercent></ram:ApplicableTradeTax>
                <ram:SpecifiedTradeSettlementLineMonetarySummation><ram:LineTotalAmount>119.83</ram:LineTotalAmount></ram:SpecifiedTradeSettlementLineMonetarySummation>
            </ram:SpecifiedLineTradeSettlement>
        </ram:IncludedSupplyChainTradeLineItem>
        <ram:ApplicableHeaderTradeAgreement>
            <ram:SellerTradeParty>
                <ram:Name>Energie Verte SA</ram:Name>
                <ram:SpecifiedLegalOrganization><ram:ID schemeID="0002">778899001</ram:ID></ram:SpecifiedLegalOrganization>
                <ram:PostalTradeAddress><ram:LineOne>200 boulevard Voltaire</ram:LineOne><ram:PostcodeCode>44000</ram:PostcodeCode><ram:CityName>Nantes</ram:CityName><ram:CountryID>FR</ram:CountryID></ram:PostalTradeAddress>
                <ram:URIUniversalCommunication><ram:URIID schemeID="0009">77889900100022</ram:URIID></ram:URIUniversalCommunication>
                <ram:SpecifiedTaxRegistration><ram:ID schemeID="VA">FR77889900101</ram:ID></ram:SpecifiedTaxRegistration>
            </ram:SellerTradeParty>
            <ram:BuyerTradeParty>
                <ram:Name>Mon Entreprise DUPONT LA JOIE</ram:Name>
                <ram:SpecifiedLegalOrganization><ram:ID schemeID="0002">123456789</ram:ID></ram:SpecifiedLegalOrganization>
                <ram:PostalTradeAddress><ram:LineOne>12 rue de la Paix</ram:LineOne><ram:PostcodeCode>75001</ram:PostcodeCode><ram:CityName>Paris</ram:CityName><ram:CountryID>FR</ram:CountryID></ram:PostalTradeAddress>
                <ram:URIUniversalCommunication><ram:URIID schemeID="0009">12345678900012</ram:URIID></ram:URIUniversalCommunication>
                <ram:SpecifiedTaxRegistration><ram:ID schemeID="VA">FR12345678901</ram:ID></ram:SpecifiedTaxRegistration>
            </ram:BuyerTradeParty>
        </ram:ApplicableHeaderTradeAgreement>
        <ram:ApplicableHeaderTradeDelivery>
            <ram:ActualDeliverySupplyChainEvent><ram:OccurrenceDateTime><udt:DateTimeString format="102">20260131</udt:DateTimeString></ram:OccurrenceDateTime></ram:ActualDeliverySupplyChainEvent>
        </ram:ApplicableHeaderTradeDelivery>
        <ram:ApplicableHeaderTradeSettlement>
            <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
            <ram:ApplicableTradeTax><ram:CalculatedAmount>148.71</ram:CalculatedAmount><ram:TypeCode>VAT</ram:TypeCode><ram:BasisAmount>743.55</ram:BasisAmount><ram:CategoryCode>S</ram:CategoryCode><ram:RateApplicablePercent>20.00</ram:RateApplicablePercent></ram:ApplicableTradeTax>
            <ram:SpecifiedTradePaymentTerms><ram:DueDateDateTime><udt:DateTimeString format="102">20260305</udt:DateTimeString></ram:DueDateDateTime></ram:SpecifiedTradePaymentTerms>
            <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
                <ram:LineTotalAmount>743.55</ram:LineTotalAmount>
                <ram:TaxBasisTotalAmount>743.55</ram:TaxBasisTotalAmount>
                <ram:TaxTotalAmount currencyID="EUR">148.71</ram:TaxTotalAmount>
                <ram:GrandTotalAmount>892.26</ram:GrandTotalAmount>
                <ram:DuePayableAmount>892.26</ram:DuePayableAmount>
            </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        </ram:ApplicableHeaderTradeSettlement>
    </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>'),
    './data/incoming-invoices/facture-EV-2026-00187.pdf',
    '2026-02-05',
    892.26,
    '2026-02-10 11:45:00+01'
);
