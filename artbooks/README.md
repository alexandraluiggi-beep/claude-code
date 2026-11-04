# Bibliothèque d'artbooks (usage local et privé)

## Installation (une seule fois, sur Mac)

```bash
cd artbooks
python3 -m venv .venv
source .venv/bin/activate
pip install pymupdf
```

## Étape 2 : extraction

```bash
source .venv/bin/activate          # à chaque nouvelle session de Terminal

# 1. Échantillon de 5 livres pour valider
python3 extract.py ~/chemin/vers/CATALOGUES --limit 5

# 2. Toute la collection (les livres déjà traités sont ignorés)
python3 extract.py ~/chemin/vers/CATALOGUES

# Une couverture n'est pas la bonne ? Prendre la page 3 à la place :
python3 extract.py --cover "Arzach" 3

# Revoir le contenu de la base
python3 extract.py --list
```

Astuce : glissez le dossier CATALOGUES depuis le Finder dans le Terminal pour obtenir son chemin.

Le script crée `bibliotheque.db` (SQLite) et `covers/`. Les deux sont ignorés par Git.
