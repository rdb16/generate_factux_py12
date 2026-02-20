"""Test d'envoi de facture Factur-X vers la PDP SuperPDP."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.super_pdp import send_facturx_to_pdp

if len(sys.argv) < 2:
    print(f"Usage : {sys.argv[0]} <chemin_vers_pdf_facturx>")
    sys.exit(1)

pdf_path = sys.argv[1]
print(f"Envoi de {pdf_path} vers SuperPDP...")

response = send_facturx_to_pdp(pdf_path)
print(json.dumps(response, indent=2, ensure_ascii=False))
