#!/usr/bin/env python3
"""
Extraction de la bibliothèque d'artbooks.

Pour chaque PDF du dossier donné :
  - rend la couverture (page 1 par défaut) en JPEG dans covers/
  - lit les métadonnées du PDF (titre, auteur, date) si présentes
  - devine titre / auteur / année à partir du nom de fichier
  - enregistre le tout dans la base SQLite bibliotheque.db (table `livres`)

Usage :
  python3 extract.py ~/Documents/CATALOGUES --limit 5     # échantillon
  python3 extract.py ~/Documents/CATALOGUES               # toute la collection
  python3 extract.py --cover "nom du fichier.pdf" 3       # utiliser la page 3 comme couverture
  python3 extract.py --list                               # afficher le contenu de la base

Relancer le script est sans risque : les livres déjà en base sont ignorés
(sauf avec --force), et les champs que vous avez corrigés ne sont jamais écrasés.
"""

import argparse
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

try:
    import pymupdf  # PyMuPDF >= 1.24
except ImportError:  # anciennes versions
    import fitz as pymupdf

ICI = Path(__file__).resolve().parent
DB_PATH = ICI / "bibliotheque.db"
COVERS_DIR = ICI / "covers"
LARGEUR_COUVERTURE = 900  # pixels

SCHEMA = """
CREATE TABLE IF NOT EXISTS livres (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    titre             TEXT,
    auteur            TEXT,
    chemin_pdf        TEXT UNIQUE NOT NULL,
    chemin_couverture TEXT,
    categorie         TEXT,
    technique         TEXT,
    annee             TEXT,
    editeur           TEXT,
    -- champs complémentaires
    fiche_auteur      TEXT,      -- rempli à l'étape d'enrichissement
    nb_pages          INTEGER,
    page_couverture   INTEGER DEFAULT 1,
    meta_titre        TEXT,      -- métadonnées brutes du PDF, pour comparaison
    meta_auteur       TEXT,
    meta_date         TEXT,
    statut            TEXT DEFAULT 'extrait',  -- extrait -> valide
    date_ajout        TEXT
);
"""

# ---------------------------------------------------------------- nom de fichier

SEPARATEURS = re.compile(r"\s+[-–—]\s+|\s*_-_\s*|\s*--\s*")
ANNEE = re.compile(r"(?<!\d)(1[5-9]\d\d|20\d\d)(?!\d)")
BRUIT = re.compile(
    r"\b(ebook|scan(ne)?|hq|hd|ocr|pdf|v\d|final|copie|copy)\b", re.IGNORECASE
)


def nettoyer(texte: str) -> str:
    texte = texte.replace("_", " ").replace(".", " ") if " " not in texte else texte.replace("_", " ")
    texte = re.sub(r"[\[\](){}]", " ", texte)
    texte = BRUIT.sub(" ", texte)
    return re.sub(r"\s{2,}", " ", texte).strip(" -–—,;")


def deviner_depuis_nom(nom_fichier: str) -> dict:
    """'Dubuffet - Asphyxiante culture (1968).pdf' -> auteur, titre, année."""
    base = unicodedata.normalize("NFC", Path(nom_fichier).stem)
    annee = None
    m = ANNEE.search(base)
    if m:
        annee = m.group(1)
        base = (base[: m.start()] + base[m.end():])
    morceaux = [nettoyer(p) for p in SEPARATEURS.split(base)]
    morceaux = [p for p in morceaux if p]
    if len(morceaux) >= 2:
        auteur, titre = morceaux[0], " – ".join(morceaux[1:])
    else:
        auteur, titre = None, nettoyer(base)
    return {"auteur": auteur, "titre": titre or Path(nom_fichier).stem, "annee": annee}


# ---------------------------------------------------------------- métadonnées PDF

def lire_meta(doc) -> dict:
    meta = doc.metadata or {}
    def propre(v):
        v = (v or "").strip()
        # ignorer les valeurs inutiles fréquentes (logiciel de scan, "untitled"...)
        if not v or v.lower() in {"untitled", "sans titre", "unknown", "anonymous"}:
            return None
        if re.search(r"\.(pdf|indd|docx?|qxd)$", v, re.IGNORECASE) or "microsoft word" in v.lower():
            return None
        return v
    date = meta.get("creationDate") or ""
    m = re.match(r"D:(\d{4})", date)
    return {
        "titre": propre(meta.get("title")),
        "auteur": propre(meta.get("author")),
        "date": m.group(1) if m else None,
    }


# ---------------------------------------------------------------- couverture

def nom_couverture(chemin_pdf: Path) -> str:
    slug = unicodedata.normalize("NFKD", chemin_pdf.stem).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug).strip("-").lower()[:80] or "livre"
    return f"{slug}.jpg"


def rendre_couverture(doc, page_num: int, destination: Path) -> None:
    page = doc[page_num - 1]
    zoom = LARGEUR_COUVERTURE / max(page.rect.width, 1)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    pix.save(str(destination), jpg_quality=85)


# ---------------------------------------------------------------- base

def connexion() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def traiter(con, chemin: Path, force: bool) -> str:
    existe = con.execute("SELECT id FROM livres WHERE chemin_pdf = ?", (str(chemin),)).fetchone()
    if existe and not force:
        return "déjà en base"
    try:
        doc = pymupdf.open(chemin)
    except Exception as e:  # PDF corrompu, protégé...
        return f"ERREUR ouverture : {e}"
    if doc.needs_pass:
        return "ERREUR : PDF protégé par mot de passe"
    if doc.page_count == 0:
        return "ERREUR : PDF vide"

    COVERS_DIR.mkdir(exist_ok=True)
    cover = COVERS_DIR / nom_couverture(chemin)
    rendre_couverture(doc, 1, cover)

    meta = lire_meta(doc)
    nom = deviner_depuis_nom(chemin.name)
    # Le nom de fichier est jugé plus fiable ; les métadonnées PDF complètent.
    titre = nom["titre"] or meta["titre"]
    auteur = nom["auteur"] or meta["auteur"]
    # « Saul Leiter Early Color » + auteur méta « Saul Leiter » -> titre « Early Color »
    if not nom["auteur"] and auteur and titre.lower().startswith(auteur.lower() + " "):
        titre = titre[len(auteur):].strip(" -–—,")
    annee = nom["annee"]  # la date de création du PDF n'est pas l'année d'édition

    valeurs = dict(
        titre=titre, auteur=auteur, chemin_pdf=str(chemin),
        chemin_couverture=f"covers/{cover.name}", annee=annee,
        nb_pages=doc.page_count, meta_titre=meta["titre"],
        meta_auteur=meta["auteur"], meta_date=meta["date"],
        date_ajout=datetime.now().isoformat(timespec="seconds"),
    )
    if existe:  # --force : on ne rafraîchit que les champs techniques
        con.execute(
            """UPDATE livres SET chemin_couverture=:chemin_couverture, nb_pages=:nb_pages,
               page_couverture=1, meta_titre=:meta_titre, meta_auteur=:meta_auteur,
               meta_date=:meta_date WHERE chemin_pdf=:chemin_pdf""", valeurs)
        statut = "mis à jour"
    else:
        cols = ", ".join(valeurs)
        con.execute(f"INSERT INTO livres ({cols}) VALUES ({', '.join(':' + c for c in valeurs)})", valeurs)
        statut = "ajouté"
    con.commit()
    doc.close()
    return statut


def changer_couverture(con, nom_fichier: str, page: int) -> None:
    rows = con.execute("SELECT * FROM livres WHERE chemin_pdf LIKE ?", (f"%{nom_fichier}%",)).fetchall()
    if len(rows) != 1:
        sys.exit(f"{len(rows)} livre(s) correspondent à « {nom_fichier} » — précisez le nom.")
    row = rows[0]
    with pymupdf.open(row["chemin_pdf"]) as doc:
        if not 1 <= page <= doc.page_count:
            sys.exit(f"Ce PDF a {doc.page_count} pages.")
        rendre_couverture(doc, page, ICI / row["chemin_couverture"])
    con.execute("UPDATE livres SET page_couverture=? WHERE id=?", (page, row["id"]))
    con.commit()
    print(f"Couverture de « {row['titre']} » remplacée par la page {page}.")


def afficher(con) -> None:
    rows = con.execute("SELECT * FROM livres ORDER BY auteur, titre").fetchall()
    print(f"\n{len(rows)} livre(s) en base ({DB_PATH.name})\n")
    print(f"{'id':>3}  {'auteur':<28} {'titre':<40} {'année':<5} {'pages':>5}  meta PDF (titre / auteur)")
    print("-" * 120)
    for r in rows:
        meta = " / ".join(x for x in (r["meta_titre"], r["meta_auteur"]) if x) or "—"
        print(f"{r['id']:>3}  {(r['auteur'] or '?')[:28]:<28} {(r['titre'] or '')[:40]:<40} "
              f"{r['annee'] or '':<5} {r['nb_pages'] or 0:>5}  {meta[:40]}")


def main():
    p = argparse.ArgumentParser(description="Extraction des couvertures et métadonnées des PDF.")
    p.add_argument("dossier", nargs="?", help="dossier contenant les PDF (sous-dossiers inclus)")
    p.add_argument("--limit", type=int, help="ne traiter que les N premiers PDF (échantillon)")
    p.add_argument("--force", action="store_true", help="re-générer couverture et méta techniques")
    p.add_argument("--cover", nargs=2, metavar=("FICHIER", "PAGE"), help="choisir une autre page comme couverture")
    p.add_argument("--list", action="store_true", help="afficher le contenu de la base")
    a = p.parse_args()

    con = connexion()
    if a.cover:
        changer_couverture(con, a.cover[0], int(a.cover[1]))
        return
    if a.list:
        afficher(con)
        return
    if not a.dossier:
        p.error("indiquez le dossier des PDF (ou --list / --cover)")

    dossier = Path(a.dossier).expanduser().resolve()
    if not dossier.is_dir():
        sys.exit(f"Dossier introuvable : {dossier}")
    pdfs = sorted(f for f in dossier.rglob("*") if f.suffix.lower() == ".pdf" and not f.name.startswith("._"))
    if a.limit:
        pdfs = pdfs[: a.limit]
    print(f"{len(pdfs)} PDF à traiter dans {dossier}\n")

    for i, pdf in enumerate(pdfs, 1):
        statut = traiter(con, pdf, a.force)
        print(f"[{i:>3}/{len(pdfs)}] {statut:<14} {pdf.relative_to(dossier)}")
    afficher(con)
    print(f"\nCouvertures : {COVERS_DIR}")


if __name__ == "__main__":
    main()
