"""
Générateur de fichiers XML au format Factur-X (profil EN16931).

Basé sur la norme EN 16931 et le standard Factur-X 1.07 (UN/CEFACT CII D22B).
"""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from xml.etree import ElementTree as ET
from xml.dom import minidom


# Namespaces Factur-X / ZUGFeRD (CII D22B — URIs identiques à D16B)
NAMESPACES = {
    'rsm': 'urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100',
    'qdt': 'urn:un:unece:uncefact:data:standard:QualifiedDataType:100',
    'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100',
    'udt': 'urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100',
}


def _register_namespaces():
    """Enregistre les namespaces pour une sortie XML propre."""
    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)


def _qname(ns: str, tag: str) -> str:
    """Génère un nom qualifié avec namespace."""
    return f'{{{NAMESPACES[ns]}}}{tag}'


def _format_amount(value) -> str:
    """Formate un montant avec 2 décimales."""
    d = Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return str(d)


def _format_quantity(value) -> str:
    """Formate une quantité avec jusqu'à 4 décimales."""
    d = Decimal(str(value)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    return str(d).rstrip('0').rstrip('.')


def _format_date(date_str: str) -> str:
    """Convertit une date ISO en format YYYYMMDD."""
    if not date_str:
        return ''
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%Y%m%d')
    except ValueError:
        return date_str.replace('-', '')


def _calculate_line_totals(line: dict) -> dict:
    """Calcule les totaux d'une ligne avec rabais."""
    qty = Decimal(str(line.get('quantity', 0) or 0))
    unit_price = Decimal(str(line.get('unit_price_ht', 0) or 0))
    vat_rate = Decimal(str(line.get('vat_rate', 20) or 20))
    discount_value = Decimal(str(line.get('discount_value', 0) or 0))
    discount_type = line.get('discount_type', 'percent')

    gross_ht = qty * unit_price

    if discount_value > 0:
        if discount_type == 'percent':
            discount_amount = gross_ht * (discount_value / 100)
        else:
            discount_amount = discount_value
    else:
        discount_amount = Decimal('0')

    net_ht = max(Decimal('0'), gross_ht - discount_amount)
    vat_amount = net_ht * (vat_rate / 100)

    # Catégorie TVA : S si taux > 0, sinon la catégorie fournie (défaut Z)
    if vat_rate > 0:
        vat_category = 'S'
    else:
        vat_category = line.get('vat_category', '').strip() or 'Z'

    return {
        'quantity': qty,
        'unit_price': unit_price,
        'gross_ht': gross_ht,
        'discount_amount': discount_amount,
        'net_ht': net_ht,
        'vat_rate': vat_rate,
        'vat_amount': vat_amount,
        'total_ttc': net_ht + vat_amount,
        'vat_category': vat_category,
        'vat_exemption_code': line.get('vat_exemption_code', '').strip(),
        'vat_exemption_reason': line.get('vat_exemption_reason', '').strip(),
    }


def _calculate_invoice_totals(lines: list[dict]) -> dict:
    """Calcule les totaux globaux de la facture."""
    total_ht = Decimal('0')
    total_vat = Decimal('0')
    vat_breakdown = {}

    for line in lines:
        totals = _calculate_line_totals(line)
        total_ht += totals['net_ht']
        total_vat += totals['vat_amount']

        # Clé de regroupement : rate + catégorie (distingue les catégories à 0%)
        rate_key = f"{totals['vat_rate']}_{totals['vat_category']}"
        if rate_key not in vat_breakdown:
            vat_breakdown[rate_key] = {
                'rate': totals['vat_rate'],
                'vat_category': totals['vat_category'],
                'vat_exemption_code': totals['vat_exemption_code'],
                'vat_exemption_reason': totals['vat_exemption_reason'],
                'base_ht': Decimal('0'),
                'vat_amount': Decimal('0'),
            }
        vat_breakdown[rate_key]['base_ht'] += totals['net_ht']
        vat_breakdown[rate_key]['vat_amount'] += totals['vat_amount']

    return {
        'total_ht': total_ht,
        'total_vat': total_vat,
        'total_ttc': total_ht + total_vat,
        'vat_breakdown': vat_breakdown,
    }


def generate_facturx_xml(data: dict) -> str:
    """
    Génère le XML Factur-X au profil BASIC.

    Args:
        data: Dictionnaire contenant 'emitter', 'invoice', et 'lines'

    Returns:
        Chaîne XML formatée
    """
    _register_namespaces()

    emitter = data['emitter']
    invoice = data['invoice']
    lines = data['lines']

    invoice_totals = _calculate_invoice_totals(lines)

    # Racine
    root = ET.Element(_qname('rsm', 'CrossIndustryInvoice'))

    # === ExchangedDocumentContext ===
    context = ET.SubElement(root, _qname('rsm', 'ExchangedDocumentContext'))

    guideline = ET.SubElement(context, _qname('ram', 'GuidelineSpecifiedDocumentContextParameter'))
    guideline_id = ET.SubElement(guideline, _qname('ram', 'ID'))
    guideline_id.text = 'urn:cen.eu:en16931:2017'

    # === ExchangedDocument ===
    doc = ET.SubElement(root, _qname('rsm', 'ExchangedDocument'))

    doc_id = ET.SubElement(doc, _qname('ram', 'ID'))
    doc_id.text = invoice['invoice_number']

    doc_type = ET.SubElement(doc, _qname('ram', 'TypeCode'))
    doc_type.text = invoice.get('type_code', '380')

    issue_dt = ET.SubElement(doc, _qname('ram', 'IssueDateTime'))
    issue_dt_str = ET.SubElement(issue_dt, _qname('udt', 'DateTimeString'))
    issue_dt_str.set('format', '102')
    issue_dt_str.text = _format_date(invoice['issue_date'])

    # Notes (conditions de paiement)
    if invoice.get('payment_terms'):
        note = ET.SubElement(doc, _qname('ram', 'IncludedNote'))
        note_content = ET.SubElement(note, _qname('ram', 'Content'))
        note_content.text = invoice['payment_terms']

    # Notes obligatoires BR-FR-05 (réglementation française)
    # PMT — Frais de recouvrement (texte configurable via ma-conf.txt)
    pmt_default = (
        "En cas de retard de paiement, une indemnité forfaitaire "
        "pour frais de recouvrement de 40€ sera exigée "
        "(Art. L441-10 et D441-5 du Code de commerce)."
    )
    note_pmt = ET.SubElement(doc, _qname('ram', 'IncludedNote'))
    note_pmt_content = ET.SubElement(note_pmt, _qname('ram', 'Content'))
    note_pmt_content.text = emitter.get('pmt_text') or pmt_default
    note_pmt_code = ET.SubElement(note_pmt, _qname('ram', 'SubjectCode'))
    note_pmt_code.text = 'PMT'

    # PMD — Pénalités de retard (texte configurable via ma-conf.txt)
    pmd_default = (
        "En cas de retard de paiement, des pénalités de retard seront appliquées "
        "au taux de 3 fois le taux d'intérêt légal en vigueur "
        "(Art. L441-10 du Code de commerce)."
    )
    note_pmd = ET.SubElement(doc, _qname('ram', 'IncludedNote'))
    note_pmd_content = ET.SubElement(note_pmd, _qname('ram', 'Content'))
    note_pmd_content.text = emitter.get('pmd_text') or pmd_default
    note_pmd_code = ET.SubElement(note_pmd, _qname('ram', 'SubjectCode'))
    note_pmd_code.text = 'PMD'

    # AAB — Escompte
    note_aab = ET.SubElement(doc, _qname('ram', 'IncludedNote'))
    note_aab_content = ET.SubElement(note_aab, _qname('ram', 'Content'))
    note_aab_content.text = "Pas d'escompte pour paiement anticipé."
    note_aab_code = ET.SubElement(note_aab, _qname('ram', 'SubjectCode'))
    note_aab_code.text = 'AAB'

    # === SupplyChainTradeTransaction ===
    transaction = ET.SubElement(root, _qname('rsm', 'SupplyChainTradeTransaction'))

    # --- Lignes de facture ---
    for i, line in enumerate(lines, start=1):
        line_totals = _calculate_line_totals(line)

        line_item = ET.SubElement(transaction, _qname('ram', 'IncludedSupplyChainTradeLineItem'))

        # Numéro de ligne
        line_doc = ET.SubElement(line_item, _qname('ram', 'AssociatedDocumentLineDocument'))
        line_id = ET.SubElement(line_doc, _qname('ram', 'LineID'))
        line_id.text = str(i)

        # Produit/Service
        product = ET.SubElement(line_item, _qname('ram', 'SpecifiedTradeProduct'))
        product_name = ET.SubElement(product, _qname('ram', 'Name'))
        product_name.text = line['description']

        # Accord commercial (prix)
        agreement = ET.SubElement(line_item, _qname('ram', 'SpecifiedLineTradeAgreement'))

        # Prix net
        net_price = ET.SubElement(agreement, _qname('ram', 'NetPriceProductTradePrice'))
        net_price_amount = ET.SubElement(net_price, _qname('ram', 'ChargeAmount'))
        net_price_amount.text = _format_amount(line_totals['unit_price'])

        # Livraison (quantité)
        delivery = ET.SubElement(line_item, _qname('ram', 'SpecifiedLineTradeDelivery'))
        billed_qty = ET.SubElement(delivery, _qname('ram', 'BilledQuantity'))
        billed_qty.set('unitCode', 'C62')  # Unité par défaut
        billed_qty.text = _format_quantity(line_totals['quantity'])

        # Règlement de la ligne
        settlement = ET.SubElement(line_item, _qname('ram', 'SpecifiedLineTradeSettlement'))

        # TVA de la ligne
        line_tax = ET.SubElement(settlement, _qname('ram', 'ApplicableTradeTax'))
        line_tax_type = ET.SubElement(line_tax, _qname('ram', 'TypeCode'))
        line_tax_type.text = 'VAT'
        line_tax_cat = ET.SubElement(line_tax, _qname('ram', 'CategoryCode'))
        line_tax_cat.text = line_totals['vat_category']
        line_tax_rate = ET.SubElement(line_tax, _qname('ram', 'RateApplicablePercent'))
        line_tax_rate.text = _format_amount(line_totals['vat_rate'])

        # Rabais sur la ligne
        if line_totals['discount_amount'] > 0:
            allowance = ET.SubElement(settlement, _qname('ram', 'SpecifiedTradeAllowanceCharge'))
            allowance_indicator = ET.SubElement(allowance, _qname('ram', 'ChargeIndicator'))
            allowance_indicator_val = ET.SubElement(allowance_indicator, _qname('udt', 'Indicator'))
            allowance_indicator_val.text = 'false'
            allowance_amount = ET.SubElement(allowance, _qname('ram', 'ActualAmount'))
            allowance_amount.text = _format_amount(line_totals['discount_amount'])
            allowance_reason = ET.SubElement(allowance, _qname('ram', 'Reason'))
            allowance_reason.text = 'Rabais'

        # Total ligne
        line_sum = ET.SubElement(settlement, _qname('ram', 'SpecifiedTradeSettlementLineMonetarySummation'))
        line_total = ET.SubElement(line_sum, _qname('ram', 'LineTotalAmount'))
        line_total.text = _format_amount(line_totals['net_ht'])

    # --- ApplicableHeaderTradeAgreement ---
    agreement = ET.SubElement(transaction, _qname('ram', 'ApplicableHeaderTradeAgreement'))

    # Référence acheteur
    if invoice.get('buyer_reference'):
        buyer_ref = ET.SubElement(agreement, _qname('ram', 'BuyerReference'))
        buyer_ref.text = invoice['buyer_reference']

    # Vendeur (émetteur)
    seller = ET.SubElement(agreement, _qname('ram', 'SellerTradeParty'))
    seller_name = ET.SubElement(seller, _qname('ram', 'Name'))
    seller_name.text = emitter['name']

    # Identifiants légaux du vendeur (SIREN — 9 chiffres, BR-FR-10)
    seller_legal = ET.SubElement(seller, _qname('ram', 'SpecifiedLegalOrganization'))
    seller_siren = ET.SubElement(seller_legal, _qname('ram', 'ID'))
    seller_siren.set('schemeID', '0002')
    seller_siren.text = emitter['siren']

    # Adresse du vendeur (ordre important pour validation XSD: LineOne, CityName, CountryID)
    seller_addr = ET.SubElement(seller, _qname('ram', 'PostalTradeAddress'))
    seller_line = ET.SubElement(seller_addr, _qname('ram', 'LineOne'))
    seller_line.text = emitter['address']
    seller_city = ET.SubElement(seller_addr, _qname('ram', 'CityName'))
    seller_city.text = emitter['city']
    seller_country = ET.SubElement(seller_addr, _qname('ram', 'CountryID'))
    seller_country.text = emitter['country_code']

    # Adresse électronique du vendeur (BT-34, BR-FR-13)
    seller_endpoint = ET.SubElement(seller, _qname('ram', 'URIUniversalCommunication'))
    seller_endpoint_uri = ET.SubElement(seller_endpoint, _qname('ram', 'URIID'))
    seller_endpoint_uri.set('schemeID', '0009')
    seller_endpoint_uri.text = emitter['siret']

    # TVA du vendeur
    if emitter.get('vat_number'):
        seller_tax = ET.SubElement(seller, _qname('ram', 'SpecifiedTaxRegistration'))
        seller_vat = ET.SubElement(seller_tax, _qname('ram', 'ID'))
        seller_vat.set('schemeID', 'VA')
        seller_vat.text = emitter['vat_number']

    # Acheteur (client)
    buyer = ET.SubElement(agreement, _qname('ram', 'BuyerTradeParty'))
    buyer_name = ET.SubElement(buyer, _qname('ram', 'Name'))
    buyer_name.text = invoice['recipient_name']

    # Identifiants légaux de l'acheteur
    buyer_legal = ET.SubElement(buyer, _qname('ram', 'SpecifiedLegalOrganization'))
    buyer_siret = ET.SubElement(buyer_legal, _qname('ram', 'ID'))
    buyer_siret.set('schemeID', '0002')
    buyer_siret.text = invoice['recipient_siret']

    # Adresse de l'acheteur (LineOne, CityName, CountryID)
    if invoice.get('recipient_address') or invoice.get('recipient_city'):
        buyer_addr = ET.SubElement(buyer, _qname('ram', 'PostalTradeAddress'))

        # LineOne (adresse)
        if invoice.get('recipient_address'):
            buyer_line = ET.SubElement(buyer_addr, _qname('ram', 'LineOne'))
            buyer_line.text = invoice['recipient_address']

        # CityName (ville)
        if invoice.get('recipient_city'):
            buyer_city = ET.SubElement(buyer_addr, _qname('ram', 'CityName'))
            buyer_city.text = invoice['recipient_city']

        # CountryID (pays)
        buyer_country = ET.SubElement(buyer_addr, _qname('ram', 'CountryID'))
        buyer_country.text = invoice['recipient_country_code']

    # Adresse électronique de l'acheteur (BT-49, BR-FR-12)
    buyer_endpoint = ET.SubElement(buyer, _qname('ram', 'URIUniversalCommunication'))
    buyer_endpoint_uri = ET.SubElement(buyer_endpoint, _qname('ram', 'URIID'))
    buyer_endpoint_uri.set('schemeID', '0009')
    buyer_endpoint_uri.text = invoice['recipient_siret']

    # TVA de l'acheteur
    if invoice.get('recipient_vat_number'):
        buyer_tax = ET.SubElement(buyer, _qname('ram', 'SpecifiedTaxRegistration'))
        buyer_vat = ET.SubElement(buyer_tax, _qname('ram', 'ID'))
        buyer_vat.set('schemeID', 'VA')
        buyer_vat.text = invoice['recipient_vat_number']

    # Référence bon de commande
    if invoice.get('purchase_order_reference'):
        order_ref = ET.SubElement(agreement, _qname('ram', 'BuyerOrderReferencedDocument'))
        order_ref_id = ET.SubElement(order_ref, _qname('ram', 'IssuerAssignedID'))
        order_ref_id.text = invoice['purchase_order_reference']

    # --- ApplicableHeaderTradeDelivery ---
    delivery = ET.SubElement(transaction, _qname('ram', 'ApplicableHeaderTradeDelivery'))
    # Date de livraison (obligatoire pour éviter un élément vide — PEPPOL-EN16931-R008)
    delivery_event = ET.SubElement(delivery, _qname('ram', 'ActualDeliverySupplyChainEvent'))
    delivery_date = ET.SubElement(delivery_event, _qname('ram', 'OccurrenceDateTime'))
    delivery_date_str = ET.SubElement(delivery_date, _qname('udt', 'DateTimeString'))
    delivery_date_str.set('format', '102')
    delivery_date_str.text = _format_date(invoice.get('delivery_date', invoice['issue_date']))

    # --- ApplicableHeaderTradeSettlement ---
    settlement = ET.SubElement(transaction, _qname('ram', 'ApplicableHeaderTradeSettlement'))

    # Devise
    currency = ET.SubElement(settlement, _qname('ram', 'InvoiceCurrencyCode'))
    currency.text = invoice.get('currency_code', 'EUR')

    # Récapitulatif TVA par taux
    for rate_key, vat_info in invoice_totals['vat_breakdown'].items():
        tax = ET.SubElement(settlement, _qname('ram', 'ApplicableTradeTax'))

        tax_amount = ET.SubElement(tax, _qname('ram', 'CalculatedAmount'))
        tax_amount.text = _format_amount(vat_info['vat_amount'])

        tax_type = ET.SubElement(tax, _qname('ram', 'TypeCode'))
        tax_type.text = 'VAT'

        # BT-120 / BT-121 : motif d'exonération (requis pour catégories E, AE, G, K, O)
        category = vat_info['vat_category']
        if category in ('E', 'AE', 'G', 'K', 'O'):
            if vat_info.get('vat_exemption_reason'):
                exemption_reason = ET.SubElement(tax, _qname('ram', 'ExemptionReason'))
                exemption_reason.text = vat_info['vat_exemption_reason']
            if vat_info.get('vat_exemption_code'):
                exemption_code = ET.SubElement(tax, _qname('ram', 'ExemptionReasonCode'))
                exemption_code.text = vat_info['vat_exemption_code']

        tax_base = ET.SubElement(tax, _qname('ram', 'BasisAmount'))
        tax_base.text = _format_amount(vat_info['base_ht'])

        tax_cat = ET.SubElement(tax, _qname('ram', 'CategoryCode'))
        tax_cat.text = category

        tax_rate = ET.SubElement(tax, _qname('ram', 'RateApplicablePercent'))
        tax_rate.text = _format_amount(vat_info['rate'])

    # Conditions de paiement
    if invoice.get('due_date'):
        payment_terms = ET.SubElement(settlement, _qname('ram', 'SpecifiedTradePaymentTerms'))
        due_dt = ET.SubElement(payment_terms, _qname('ram', 'DueDateDateTime'))
        due_dt_str = ET.SubElement(due_dt, _qname('udt', 'DateTimeString'))
        due_dt_str.set('format', '102')
        due_dt_str.text = _format_date(invoice['due_date'])

    # Totaux
    monetary_sum = ET.SubElement(settlement, _qname('ram', 'SpecifiedTradeSettlementHeaderMonetarySummation'))

    line_total_sum = ET.SubElement(monetary_sum, _qname('ram', 'LineTotalAmount'))
    line_total_sum.text = _format_amount(invoice_totals['total_ht'])

    tax_basis_total = ET.SubElement(monetary_sum, _qname('ram', 'TaxBasisTotalAmount'))
    tax_basis_total.text = _format_amount(invoice_totals['total_ht'])

    tax_total = ET.SubElement(monetary_sum, _qname('ram', 'TaxTotalAmount'))
    tax_total.set('currencyID', invoice.get('currency_code', 'EUR'))
    tax_total.text = _format_amount(invoice_totals['total_vat'])

    grand_total = ET.SubElement(monetary_sum, _qname('ram', 'GrandTotalAmount'))
    grand_total.text = _format_amount(invoice_totals['total_ttc'])

    due_payable = ET.SubElement(monetary_sum, _qname('ram', 'DuePayableAmount'))
    due_payable.text = _format_amount(invoice_totals['total_ttc'])

    # Génération du XML formaté
    xml_string = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_string)
    pretty_xml = dom.toprettyxml(indent='  ', encoding='UTF-8')

    # Retirer la ligne XML générée par minidom et la remplacer
    lines_list = pretty_xml.decode('utf-8').split('\n')
    if lines_list[0].startswith('<?xml'):
        lines_list[0] = '<?xml version="1.0" encoding="UTF-8"?>'

    return '\n'.join(lines_list)
