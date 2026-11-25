"""Estimation des revenus d'un appartement meublé à Paris, en location longue durée ou sur
Airbnb, puis bilan après impôt avec fiscalite.py."""

from dataclasses import dataclass

import geopandas as gpd
import pandas as pd

from fiscalite import TAUX_COTISATIONS_INDICATIF, Bien, Foyer, imposer

MIN_ANNONCES = 5        # en dessous, la médiane n'est pas fiable : on élargit la zone
NUITS_MAX_RP = 90       # résidence principale à Paris : 90 nuits par an au maximum
ANNEE_LOYERS = 2025     # dernier arrêté d'encadrement disponible dans les données figées


@dataclass
class Logement:
    id_quartier: int
    pieces: int                     # 1, 2, 3 ou 4 (= 4 pièces et plus)
    surface: float                  # m²
    epoque: str                     # "Avant 1946", "1946-1970", "1971-1990", "Apres 1990"
    residence_principale: bool      # limite Airbnb à 90 nuits par an
    loyer_majore: bool = True       # loyer majoré (maximum légal) ou loyer de référence


@dataclass
class Exploitation:
    """Frais d'exploitation, en part des recettes (déductibles au régime réel)."""
    frais_airbnb: float = 0.25      # commission, ménage, linge, énergie, conciergerie…
    frais_longue_duree: float = 0.05  # vacance locative, gestion


# ---------- Préparation ----------

def preparer_airbnb(annonces: pd.DataFrame, calendrier: pd.DataFrame,
                    zones: gpd.GeoDataFrame) -> pd.DataFrame:
    """Logements entiers actifs, avec leurs deux estimations d'occupation."""
    df = annonces[
        (annonces["room_type"] == "Entire home/apt")
        & annonces["prix_nuit"].between(20, 1500)      # écarte les prix aberrants
        & (annonces["minimum_nights"] <= 30)           # location courte durée
        & (annonces["number_of_reviews_ltm"] > 0)      # loué au moins une fois en 12 mois
    ].copy()
    # Inside Airbnb donne les chambres ; l'encadrement raisonne en pièces (chambres + séjour).
    df["pieces"] = (df["bedrooms"].fillna(0) + 1).clip(1, 4).astype(int)
    # Estimation prudente d'Inside Airbnb, fondée sur le nombre d'avis.
    df["occupation_basse"] = (df["estimated_occupancy_l365d"] / 365).clip(0, 1)
    # Part des nuits indisponibles sur les 12 prochains mois : réservées OU bloquées par
    # l'hôte, donc un majorant de l'occupation réelle.
    cal = calendrier.groupby("listing_id")[["nuits", "nuits_indisponibles"]].sum()
    df["occupation_haute"] = df["listing_id"].map(cal["nuits_indisponibles"] / cal["nuits"])
    df["arrondissement"] = df["id_quartier"].map(zones.set_index("id_quartier")["arrondissement"])
    return df


# ---------- Estimation des recettes, pour tous les quartiers ----------

def _recettes_airbnb(annonces: pd.DataFrame, residence_principale: bool) -> dict:
    """Médianes des annonces comparables : prix/nuit, nuits louées et recettes annuelles."""
    resultat = {"annonces": len(annonces), "prix_nuit": annonces["prix_nuit"].median()}
    for niveau in ("basse", "haute"):
        nuits = annonces[f"occupation_{niveau}"] * 365
        if residence_principale:
            nuits = nuits.clip(upper=NUITS_MAX_RP)
        resultat[f"nuits_{niveau}"] = nuits.median()
        resultat[f"recettes_airbnb_{niveau}"] = (annonces["prix_nuit"] * nuits).median()
    return resultat


def estimer_quartiers(airbnb: pd.DataFrame, loyers: pd.DataFrame, zones: gpd.GeoDataFrame,
                      lg: Logement) -> gpd.GeoDataFrame:
    """Recettes annuelles estimées du logement s'il était situé dans chacun des 80 quartiers.

    Les annonces comparables sont celles du quartier ayant le même nombre de pièces ; s'il y
    en a moins de MIN_ANNONCES, on élargit à l'arrondissement, puis à tout Paris.
    """
    meme_taille = airbnb[airbnb["pieces"] == lg.pieces]
    lignes = []
    for z in zones.itertuples():
        for zone, comp in [
            ("quartier", meme_taille[meme_taille["id_quartier"] == z.id_quartier]),
            ("arrondissement", meme_taille[meme_taille["arrondissement"] == z.arrondissement]),
            ("Paris", meme_taille),
        ]:
            if len(comp) >= MIN_ANNONCES:
                break
        lignes.append({"id_quartier": z.id_quartier, "comparables": zone,
                       **_recettes_airbnb(comp, lg.residence_principale)})
    res = zones.merge(pd.DataFrame(lignes), on="id_quartier")

    l = loyers[(loyers["annee"] == ANNEE_LOYERS) & (loyers["pieces"] == lg.pieces)
               & (loyers["epoque"] == lg.epoque) & (loyers["meuble"] == "meublé")]
    colonne = "loyer_majore" if lg.loyer_majore else "loyer_reference"
    res["loyer_m2"] = res["id_quartier"].map(l.set_index("id_quartier")[colonne])
    res["recettes_longue_duree"] = res["loyer_m2"] * lg.surface * 12
    return res


# ---------- Bilan avant et après impôt ----------

OPTIONS = {
    "longue_duree": "Meublé longue durée",
    "airbnb_basse": "Airbnb – occupation basse",
    "airbnb_haute": "Airbnb – occupation haute",
}


def bilan(recettes: dict, bien: Bien, foyer: Foyer, ex: Exploitation,
          taux_cotisations: float = TAUX_COTISATIONS_INDICATIF) -> pd.DataFrame:
    """Tableau comparatif : une colonne par option, des recettes au revenu net après impôt.

    recettes : {"longue_duree": €, "airbnb_basse": €, "airbnb_haute": €}
    """
    colonnes = {}
    for option, libelle in OPTIONS.items():
        r = recettes[option]
        longue = option == "longue_duree"
        frais = r * (ex.frais_longue_duree if longue else ex.frais_airbnb)
        avant_impot = r - frais - bien.charges_proprietaire
        f = imposer("longue_duree" if longue else "tourisme_non_classe", r, frais, bien,
                    foyer, taux_cotisations)
        colonnes[libelle] = {
            "Recettes annuelles": r,
            "Frais d'exploitation": -frais,
            "Charges du propriétaire": -bien.charges_proprietaire,
            "Revenu avant impôt": avant_impot,
            "Régime fiscal": f.regime,
            "Revenu imposable": f.revenu_imposable,
            "Impôt sur le revenu": -f.impot_revenu,
            "Prélèvements / cotisations sociales": -f.social,
            "Nature des prélèvements": f.social_nature,
            "Revenu net après impôt": avant_impot - f.total,
            "Revenu net par mois": (avant_impot - f.total) / 12,
            "Alertes": f.alertes,
        }
    return pd.DataFrame(colonnes)


def net_apres_impot(option: str, recettes: float, bien: Bien, foyer: Foyer,
                    ex: Exploitation, taux_cotisations: float) -> float:
    longue = option == "longue_duree"
    frais = recettes * (ex.frais_longue_duree if longue else ex.frais_airbnb)
    f = imposer("longue_duree" if longue else "tourisme_non_classe", recettes, frais, bien,
                foyer, taux_cotisations)
    return recettes - frais - bien.charges_proprietaire - f.total


def nuits_seuil(prix_nuit: float, recettes_longue: float, bien: Bien, foyer: Foyer,
                ex: Exploitation, taux_cotisations: float, nuits_max: int = 365) -> int | None:
    """Nombre de nuits louées par an à partir duquel Airbnb rapporte plus, après impôt,
    que la location longue durée. None si ce n'est jamais le cas."""
    cible = net_apres_impot("longue_duree", recettes_longue, bien, foyer, ex, taux_cotisations)
    for nuits in range(nuits_max + 1):
        if net_apres_impot("airbnb", prix_nuit * nuits, bien, foyer, ex,
                           taux_cotisations) >= cible:
            return nuits
    return None


def nets_quartiers(estimations: pd.DataFrame, bien: Bien, foyer: Foyer, ex: Exploitation,
                   taux_cotisations: float) -> pd.DataFrame:
    """Revenu net après impôt de chaque option, pour chaque quartier. Airbnb est pris au
    milieu de la fourchette d'occupation (moyenne des recettes basse et haute)."""
    def nets(ligne):
        if pd.isna(ligne["recettes_longue_duree"]):
            return pd.Series({"net_longue_duree": float("nan"), "net_airbnb": float("nan")})
        airbnb = (ligne["recettes_airbnb_basse"] + ligne["recettes_airbnb_haute"]) / 2
        return pd.Series({
            "net_longue_duree": net_apres_impot("longue_duree", ligne["recettes_longue_duree"],
                                                bien, foyer, ex, taux_cotisations),
            "net_airbnb": net_apres_impot("airbnb", airbnb, bien, foyer, ex, taux_cotisations),
        })
    res = estimations.apply(nets, axis=1)
    res["gain_airbnb"] = res["net_airbnb"] - res["net_longue_duree"]
    return res


# ---------- Séries pour les graphiques ----------

def saisonnalite(airbnb: pd.DataFrame, calendrier: pd.DataFrame, id_quartier: int) -> pd.DataFrame:
    """Part des nuits indisponibles par mois, pour le quartier et pour tout Paris."""
    cal = calendrier.merge(airbnb[["listing_id", "id_quartier"]], on="listing_id")
    # Les mois extrêmes ne sont que partiellement couverts par l'extraction.
    mois = sorted(cal["mois"].unique())[1:-1]
    cal = cal[cal["mois"].isin(mois)]

    def taux(df):
        s = df.groupby("mois")[["nuits", "nuits_indisponibles"]].sum()
        return s["nuits_indisponibles"] / s["nuits"]

    return pd.DataFrame({"Quartier": taux(cal[cal["id_quartier"] == id_quartier]),
                         "Paris": taux(cal)}).rename_axis("mois").reset_index()
