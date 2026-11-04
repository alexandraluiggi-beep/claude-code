#!/bin/bash
# Double-cliquez sur ce fichier pour lancer l'extraction (échantillon de 5 livres).
cd "$(dirname "$0")"
DOSSIER=$(osascript -e 'POSIX path of (choose folder with prompt "Choisissez votre dossier CATALOGUES")') || exit 1
echo "Préparation (la première fois, cela peut prendre une minute)..."
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q pymupdf
python3 extract.py "$DOSSIER" --limit 5
open covers
echo
echo "Terminé. Copiez le tableau ci-dessus et envoyez-le à Claude."
read -p "Appuyez sur Entrée pour fermer cette fenêtre."
