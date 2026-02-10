"""
Fonctions de calcul partagées pour les totaux de facture.

Utilisées par facturx_generator, pdf_generator et app.
"""

from decimal import Decimal, ROUND_HALF_UP


def calculate_line_totals(line: dict) -> dict:
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


def calculate_invoice_totals(lines: list[dict]) -> dict:
    """Calcule les totaux globaux de la facture."""
    total_ht = Decimal('0')
    total_vat = Decimal('0')
    vat_breakdown = {}

    for line in lines:
        totals = calculate_line_totals(line)
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
