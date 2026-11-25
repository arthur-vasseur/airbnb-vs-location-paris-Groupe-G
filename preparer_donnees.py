"""Préparation, une fois pour toutes, des données figées de Paris.

Lit uniquement les fichiers de data/brut/ (jamais Internet), les nettoie et écrit
des fichiers Parquet dans data/prepare/, puis régénère data/MANIFESTE.md avec
l'empreinte SHA-256 de chaque fichier.

Lancement : python preparer_donnees.py
L'application n'a pas besoin de ce script : elle lit directement data/prepare/.
"""

import hashlib
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

DATA = Path(__file__).parent / "data"
BRUT = DATA / "brut"
PREPARE = DATA / "prepare"
DATE_AIRBNB = "2026-09-16"

# Description et origine de chaque fichier brut, reprises dans le manifeste.
SOURCES_BRUTES = {
    "airbnb/listings_2026-09-16.csv.gz": (
        "Inside Airbnb – annonces de Paris, extraction du 16/09/2026",
        "https://data.insideairbnb.com/france/ile-de-france/paris/2026-09-16/data/listings.csv.gz"),
    "airbnb/calendar_2026-09-16.csv.gz": (
        "Inside Airbnb – calendrier de disponibilité sur 365 jours",
        "https://data.insideairbnb.com/france/ile-de-france/paris/2026-09-16/data/calendar.csv.gz"),
    "loyers_encadrement/encadrement_loyers_paris.json": (
        "Ville de Paris – encadrement des loyers 2019-2025, avec contour des 80 quartiers",
        "https://opendata.paris.fr/explore/dataset/logement-encadrement-des-loyers/"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def ecrire(df: pd.DataFrame, nom: str) -> None:
    df.to_parquet(PREPARE / nom, index=False)
    print(f"  {nom} : {len(df):,} lignes".replace(",", " "))


# ---------- Quartiers et loyers de référence ----------

def preparer_encadrement() -> gpd.GeoDataFrame:
    e = pd.read_json(BRUT / "loyers_encadrement/encadrement_loyers_paris.json")
    e["annee"] = e["annee"].astype(int)
    e["arrondissement"] = e["code_grand_quartier"] // 100 % 100

    zones = e.drop_duplicates("id_quartier").sort_values("id_quartier")
    quartiers = gpd.GeoDataFrame(
        zones[["id_quartier", "nom_quartier", "arrondissement", "code_grand_quartier", "id_zone"]],
        geometry=zones["geo_shape"].apply(lambda g: shape(g["geometry"])).values,
        crs="EPSG:4326",
    ).reset_index(drop=True)
    quartiers.to_file(PREPARE / "quartiers.geojson", driver="GeoJSON")
    print(f"  quartiers.geojson : {len(quartiers)} quartiers")

    ecrire(e.rename(columns={"piece": "pieces", "meuble_txt": "meuble", "ref": "loyer_reference",
                             "max": "loyer_majore", "min": "loyer_minore"})
           [["annee", "id_quartier", "id_zone", "pieces", "epoque", "meuble",
             "loyer_reference", "loyer_minore", "loyer_majore"]],
           "loyers_reference.parquet")
    return quartiers


def rattacher(df: pd.DataFrame, quartiers: gpd.GeoDataFrame) -> pd.DataFrame:
    """Ajoute id_quartier à partir des colonnes latitude/longitude (points hors Paris retirés)."""
    points = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs="EPSG:4326")
    joint = gpd.sjoin(points, quartiers[["id_quartier", "geometry"]], predicate="within")
    return pd.DataFrame(joint.drop(columns=["geometry", "index_right"]))


# ---------- Airbnb ----------

COLONNES_ANNONCES = [
    "id", "host_id", "host_since", "host_is_superhost", "calculated_host_listings_count",
    "latitude", "longitude", "property_type", "room_type", "accommodates", "bathrooms",
    "bedrooms", "beds", "price", "minimum_nights", "maximum_nights", "availability_30",
    "availability_90", "availability_365", "number_of_reviews", "number_of_reviews_ltm",
    "first_review", "last_review", "review_scores_rating", "estimated_occupancy_l365d",
    "estimated_revenue_l365d", "license", "instant_bookable",
]


def preparer_annonces(quartiers: gpd.GeoDataFrame) -> None:
    a = pd.read_csv(BRUT / f"airbnb/listings_{DATE_AIRBNB}.csv.gz", usecols=COLONNES_ANNONCES)
    # Inside Airbnb écrit « $ » mais les montants sont en euros.
    a["price"] = pd.to_numeric(a["price"].astype(str).str.replace(r"[$,]", "", regex=True),
                               errors="coerce")
    for c in ["host_is_superhost", "instant_bookable"]:
        a[c] = a[c].map({"t": True, "f": False})
    for c in ["host_since", "first_review", "last_review"]:
        a[c] = pd.to_datetime(a[c], errors="coerce")
    # Numéro d'enregistrement en mairie : obligatoire à Paris pour louer en courte durée.
    a["numero_enregistrement"] = a["license"].notna() & ~a["license"].astype(str).str.contains(
        "exempt|available", case=False)
    a = a.rename(columns={"id": "listing_id", "price": "prix_nuit", "license": "licence"})
    ecrire(rattacher(a, quartiers), "airbnb_annonces.parquet")


def preparer_calendrier() -> None:
    """Nuits indisponibles par annonce et par mois (réservées ou bloquées par l'hôte)."""
    c = pd.read_csv(BRUT / f"airbnb/calendar_{DATE_AIRBNB}.csv.gz",
                    usecols=["listing_id", "date", "available"])
    c["mois"] = c["date"].str[:7]
    c["indisponible"] = c["available"] == "f"
    m = (c.groupby(["listing_id", "mois"])
          .agg(nuits=("indisponible", "size"), nuits_indisponibles=("indisponible", "sum"))
          .reset_index())
    ecrire(m, "airbnb_calendrier_mensuel.parquet")


# ---------- Manifeste ----------

def ecrire_manifeste() -> None:
    lignes = [
        "# Manifeste des données figées – Paris",
        "",
        f"Préparé le {date.today():%d/%m/%Y} par `preparer_donnees.py`. Ces données ne doivent "
        "plus être modifiées : l'empreinte SHA-256 de chaque fichier permet de vérifier qu'il "
        "est resté identique (`python verifier_donnees.py`).",
        "",
        "## Données brutes (`data/brut/`), telles que téléchargées",
        "",
        "| Fichier | Contenu | Source | Taille | SHA-256 |",
        "|---|---|---|---|---|",
    ]
    for rel, (desc, url) in SOURCES_BRUTES.items():
        p = BRUT / rel
        lignes.append(f"| `{rel}` | {desc} | {url} | {p.stat().st_size / 1e6:.1f} Mo | `{sha256(p)}` |")
    lignes += ["", "## Données préparées (`data/prepare/`), lues par l'application", "",
               "| Fichier | Taille | SHA-256 |", "|---|---|---|"]
    for p in sorted(PREPARE.iterdir()):
        lignes.append(f"| `{p.name}` | {p.stat().st_size / 1e6:.1f} Mo | `{sha256(p)}` |")
    (DATA / "MANIFESTE.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("  MANIFESTE.md écrit")


if __name__ == "__main__":
    PREPARE.mkdir(exist_ok=True)
    print("Préparation des données de Paris…")
    quartiers = preparer_encadrement()
    preparer_annonces(quartiers)
    preparer_calendrier()
    ecrire_manifeste()
    print("Terminé.")
