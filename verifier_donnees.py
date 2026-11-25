"""Vérifie que les données figées n'ont pas changé depuis leur préparation.

Recalcule l'empreinte SHA-256 de chaque fichier listé dans data/MANIFESTE.md et la
compare à celle qui y est notée.

Lancement : python verifier_donnees.py
"""

import re
import sys
from pathlib import Path

from preparer_donnees import BRUT, DATA, PREPARE, sha256

manifeste = (DATA / "MANIFESTE.md").read_text(encoding="utf-8")
attendus = []
for ligne in manifeste.splitlines():
    m = re.match(r"\| `([^`]+)` \|.*\| `([0-9a-f]{64})` \|$", ligne)
    if m:
        nom, empreinte = m.groups()
        dossier = BRUT if "/" in nom else PREPARE
        attendus.append((dossier / nom, empreinte))

erreurs = 0
for chemin, empreinte in attendus:
    rel = chemin.relative_to(DATA)
    if not chemin.exists():
        print(f"MANQUANT  {rel}")
        erreurs += 1
    elif sha256(chemin) != empreinte:
        print(f"MODIFIÉ   {rel}")
        erreurs += 1
    else:
        print(f"ok        {rel}")

print(f"\n{len(attendus) - erreurs}/{len(attendus)} fichiers identiques au manifeste.")
sys.exit(1 if erreurs else 0)
