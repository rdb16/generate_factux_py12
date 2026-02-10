"""
Générateur de PDF de facture avec ReportLab.

Ce module génère un PDF de facture standard qui sera ensuite converti
en PDF Factur-X avec le module factur-x.
"""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path

# Configurer la police par défaut AVANT tout autre import ReportLab
from reportlab import rl_config
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONTS_DIR = Path(__file__).parent / 'resources' / 'fonts'
pdfmetrics.registerFont(TTFont('LiberationSans', str(_FONTS_DIR / 'LiberationSans-Regular.ttf')))
pdfmetrics.registerFont(TTFont('LiberationSans-Bold', str(_FONTS_DIR / 'LiberationSans-Bold.ttf')))
pdfmetrics.registerFont(TTFont('LiberationSans-Italic', str(_FONTS_DIR / 'LiberationSans-Italic.ttf')))
pdfmetrics.registerFont(TTFont('LiberationSans-BoldItalic', str(_FONTS_DIR / 'LiberationSans-BoldItalic.ttf')))
pdfmetrics.registerFontFamily(
    'LiberationSans',
    normal='LiberationSans',
    bold='LiberationSans-Bold',
    italic='LiberationSans-Italic',
    boldItalic='LiberationSans-BoldItalic',
)
rl_config.canvas_basefontname = 'LiberationSans'

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

# Chemin du profil ICC sRGB pour conformité PDF/A-3
_ICC_PROFILE_PATH = Path(__file__).parent / 'resources' / 'profiles' / 'sRGB.icc'


def _format_amount(value) -> str:
    """Formate un montant avec 2 décimales."""
    d = Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f"{d:,.2f}".replace(',', ' ').replace('.', ',')


def _format_date(date_str: str) -> str:
    """Convertit une date ISO en format français."""
    if not date_str:
        return ''
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d/%m/%Y')
    except ValueError:
        return date_str


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

        rate_key = f"{totals['vat_rate']}_{totals['vat_category']}"
        if rate_key not in vat_breakdown:
            vat_breakdown[rate_key] = {
                'rate': totals['vat_rate'],
                'vat_category': totals['vat_category'],
                'vat_exemption_reason': totals.get('vat_exemption_reason', ''),
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


def _add_output_intent(pdf_bytes: bytes) -> bytes:
    """Ajoute un OutputIntent sRGB au PDF pour conformité PDF/A-3."""
    if not _ICC_PROFILE_PATH.exists():
        return pdf_bytes

    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (
        ArrayObject, DecodedStreamObject, DictionaryObject,
        NameObject, NumberObject, TextStringObject,
    )

    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter(clone_from=reader)

    icc_data = _ICC_PROFILE_PATH.read_bytes()

    # Flux ICC
    icc_stream = DecodedStreamObject()
    icc_stream.set_data(icc_data)
    icc_stream[NameObject('/N')] = NumberObject(3)
    icc_stream[NameObject('/Alternate')] = NameObject('/DeviceRGB')
    icc_ref = writer._add_object(icc_stream)

    # OutputIntent
    output_intent = DictionaryObject({
        NameObject('/Type'): NameObject('/OutputIntent'),
        NameObject('/S'): NameObject('/GTS_PDFA1'),
        NameObject('/OutputConditionIdentifier'): TextStringObject('sRGB IEC61966-2.1'),
        NameObject('/RegistryName'): TextStringObject('http://www.color.org'),
        NameObject('/Info'): TextStringObject('sRGB IEC61966-2.1'),
        NameObject('/DestOutputProfile'): icc_ref,
    })
    output_intent_ref = writer._add_object(output_intent)

    writer._root_object[NameObject('/OutputIntents')] = ArrayObject([output_intent_ref])

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def generate_invoice_pdf(data: dict, logo_path: str = None) -> bytes:
    """
    Génère un PDF de facture.

    Args:
        data: Dictionnaire contenant 'emitter', 'invoice', et 'lines'
        logo_path: Chemin vers le logo (optionnel)

    Returns:
        Contenu PDF en bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm)

    emitter = data['emitter']
    invoice = data['invoice']
    lines = data['lines']
    invoice_totals = _calculate_invoice_totals(lines)

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontName='LiberationSans-Bold',
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=12,
        alignment=TA_CENTER,
    )

    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontName='LiberationSans',
        fontSize=9,
        leading=12,
    )

    bold_style = ParagraphStyle(
        'Bold',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        fontName='LiberationSans-Bold',
    )

    story = []

    # En-tête avec logo et titre
    header_data = []

    if logo_path and Path(logo_path).exists():
        try:
            img = Image(logo_path, width=3*cm, height=3*cm, kind='proportional')
            header_data.append([img, Paragraph('FACTURE', title_style)])
        except Exception:
            header_data.append(['', Paragraph('FACTURE', title_style)])
    else:
        header_data.append(['', Paragraph('FACTURE', title_style)])

    header_table = Table(header_data, colWidths=[4*cm, 15*cm])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.5*cm))

    # Informations émetteur et destinataire
    # Construire l'adresse du destinataire
    recipient_address_parts = []
    if invoice.get('recipient_address'):
        recipient_address_parts.append(invoice['recipient_address'])
    if invoice.get('recipient_postal_code') or invoice.get('recipient_city'):
        city_line = f"{invoice.get('recipient_postal_code', '')} {invoice.get('recipient_city', '')}".strip()
        recipient_address_parts.append(city_line)
    recipient_address_text = '<br/>'.join(recipient_address_parts) if recipient_address_parts else 'N/A'

    info_data = [
        [
            Paragraph(f"<b>Émetteur</b><br/>{emitter['name']}{' - ' + emitter['legal_form'] if emitter.get('legal_form') else ''}<br/>{emitter['address']}<br/>{emitter['postal_code']} {emitter['city']}<br/>SIRET: {emitter['siret']}<br/>TVA: {emitter.get('vat_number', 'N/A')}", normal_style),
            Paragraph(f"<b>Destinataire</b><br/>{invoice['recipient_name']}<br/>{recipient_address_text}<br/>SIRET: {invoice['recipient_siret']}<br/>TVA: {invoice.get('recipient_vat_number', 'N/A')}", normal_style),
        ]
    ]

    info_table = Table(info_data, colWidths=[9*cm, 9*cm])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    # Informations facture
    invoice_info_data = [
        ['Numéro', invoice['invoice_number']],
        ['Date', _format_date(invoice['issue_date'])],
        ['Échéance', _format_date(invoice.get('due_date', ''))],
        ['Devise', invoice.get('currency_code', 'EUR')],
    ]

    invoice_info_table = Table(invoice_info_data, colWidths=[5*cm, 8*cm])
    invoice_info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'LiberationSans'),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('FONTNAME', (0, 0), (0, -1), 'LiberationSans-Bold'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(invoice_info_table)
    story.append(Spacer(1, 0.7*cm))

    # Lignes de facture
    line_data = [['Description', 'Qté', 'P.U. HT', 'TVA %', 'Total HT']]

    for line in lines:
        totals = _calculate_line_totals(line)
        # Afficher "0% (E)" si catégorie ≠ S, sinon juste le taux
        vat_label = _format_amount(totals['vat_rate'])
        if totals['vat_category'] != 'S':
            vat_label = f"{vat_label} ({totals['vat_category']})"
        line_data.append([
            Paragraph(line['description'], normal_style),
            _format_amount(totals['quantity']),
            _format_amount(totals['unit_price']) + ' €',
            vat_label,
            _format_amount(totals['net_ht']) + ' €',
        ])

    line_table = Table(line_data, colWidths=[7*cm, 2*cm, 3*cm, 2*cm, 3*cm])
    line_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'LiberationSans'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#148f77')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'LiberationSans-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 0.7*cm))

    # Récap TVA par taux/catégorie
    vat_recap_data = [['Taux TVA', 'Base HT', 'Montant TVA']]
    for rate_key in sorted(invoice_totals['vat_breakdown'].keys()):
        info = invoice_totals['vat_breakdown'][rate_key]
        rate_label = _format_amount(info['rate']) + ' %'
        if info['vat_category'] != 'S':
            rate_label += f" ({info['vat_category']})"
        vat_recap_data.append([
            rate_label,
            _format_amount(info['base_ht']) + ' €',
            _format_amount(info['vat_amount']) + ' €',
        ])
        # Motif d'exonération sous la ligne du taux
        if info.get('vat_exemption_reason'):
            vat_recap_data.append([
                Paragraph(f"<i>{info['vat_exemption_reason']}</i>", ParagraphStyle('VatNote', parent=normal_style, fontSize=7, textColor=colors.grey)),
                '', '',
            ])

    if len(vat_recap_data) > 1:
        vat_recap_table = Table(vat_recap_data, colWidths=[7*cm, 5*cm, 5*cm])
        vat_recap_style = [
            ('FONTNAME', (0, 0), (-1, -1), 'LiberationSans'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf2f7')),
            ('FONTNAME', (0, 0), (-1, 0), 'LiberationSans-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e2e8f0')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]
        vat_recap_table.setStyle(TableStyle(vat_recap_style))
        story.append(vat_recap_table)
        story.append(Spacer(1, 0.3*cm))

    # Totaux
    total_data = [
        ['Total HT', _format_amount(invoice_totals['total_ht']) + ' €'],
        ['Total TVA', _format_amount(invoice_totals['total_vat']) + ' €'],
        ['Total TTC', _format_amount(invoice_totals['total_ttc']) + ' €'],
    ]

    total_table = Table(total_data, colWidths=[10*cm, 7*cm])
    total_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'LiberationSans'),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'LiberationSans-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('BACKGROUND', (1, -1), (1, -1), colors.HexColor('#f0f0f0')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(total_table)

    # Conditions de paiement
    if invoice.get('payment_terms'):
        story.append(Spacer(1, 0.7*cm))
        story.append(Paragraph(f"<b>Conditions de paiement:</b> {invoice['payment_terms']}", normal_style))

    # IBAN
    if emitter.get('iban'):
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(f"<i>En votre aimable règlement par virement bancaire au {emitter['iban']}.</i>", normal_style))

    # Mentions légales PMT / PMD
    small_style = ParagraphStyle('Small', parent=normal_style, fontSize=7, textColor=colors.grey)
    if emitter.get('pmt_text'):
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(emitter['pmt_text'], small_style))
    if emitter.get('pmd_text'):
        story.append(Spacer(1, 0.1*cm))
        story.append(Paragraph(emitter['pmd_text'], small_style))

    # Générer le PDF
    doc.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    # Ajouter OutputIntent sRGB pour conformité PDF/A-3
    pdf_bytes = _add_output_intent(pdf_bytes)

    return pdf_bytes
