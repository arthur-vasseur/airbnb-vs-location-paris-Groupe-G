"""Lecture des données figées de Paris (data/prepare/).

Ces fichiers sont produits une seule fois par preparer_donnees.py à partir de data/brut/.
L'application ne télécharge plus rien : tout vient d'ici. Le détail des sources et
leurs empreintes SHA-256 sont dans data/MANIFESTE.md.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

PREPARE = Path(__file__).parent / "data" / "prepare"
DATE_AIRBNB = "2026-09-16"


def _lire(nom: str) -> pd.DataFrame:
    chemin = PREPARE / nom
    if not chemin.exists():
        raise FileNotFoundError(
            f"{chemin} est introuvable. Lancez d'abord : python preparer_donnees.py")
    return pd.read_parquet(chemin)


def quartiers() -> gpd.GeoDataFrame:
    """Les 80 quartiers administratifs : id, nom, arrondissement, zone de loyer, contour."""
    return gpd.read_file(PREPARE / "quartiers.geojson")


def airbnb_annonces() -> pd.DataFrame:
    """Annonces Inside Airbnb (prix en euros), déjà rattachées à leur quartier."""
    return _lire("airbnb_annonces.parquet")


def airbnb_calendrier() -> pd.DataFrame:
    """Nuits indisponibles (réservées ou bloquées) par annonce et par mois, sur 12 mois."""
    return _lire("airbnb_calendrier_mensuel.parquet")


def loyers_reference() -> pd.DataFrame:
    """Encadrement des loyers 2019-2025 : €/m² par quartier, pièces, époque, meublé."""
    return _lire("loyers_reference.parquet")
