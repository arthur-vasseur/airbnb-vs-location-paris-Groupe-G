"""Meublé à Paris : location longue durée ou Airbnb ? Comparaison avant et après impôt.

Lancement : streamlit run app.py
"""

import altair as alt
import branca.colormap as cm
import folium
import pandas as pd
import streamlit as st
from shapely.geometry import Point
from streamlit_folium import st_folium

import sources
from analyse import (NUITS_MAX_RP, OPTIONS, Exploitation, Logement, bilan, estimer_quartiers,
                     nets_quartiers, nuits_seuil, preparer_airbnb, saisonnalite)
from fiscalite import TAUX_COTISATIONS_INDICATIF, Bien, Foyer

st.set_page_config(page_title="Meublé à Paris : longue durée ou Airbnb ?", page_icon="🏠",
                   layout="wide")

CENTRE_PARIS = (48.857, 2.345)
SURFACE_PAR_DEFAUT = {1: 25, 2: 40, 3: 60, 4: 80}
EPOQUES = {"Avant 1946": "Avant 1946", "1946-1970": "1946 – 1970",
           "1971-1990": "1971 – 1990", "Apres 1990": "Après 1990"}
# Palette catégorielle validée (skill dataviz) : bleu = longue durée, orange = Airbnb.
BLEU, ORANGE, ORANGE_CLAIR = "#2a78d6", "#eb6834", "#f4a582"
COULEURS_OPTIONS = dict(zip(OPTIONS.values(), [BLEU, ORANGE_CLAIR, ORANGE]))


def euros(v: float, signe: bool = False) -> str:
    """1263.4 -> « 1 263 € » (format français), « — » si la valeur manque."""
    if v != v:
        return "—"
    texte = f"{v:+,.0f} €" if signe else f"{v:,.0f} €"
    return texte.replace(",", " ").replace("-", "−")


def pourcent(v: float) -> str:
    return "—" if v != v else f"{v:.0%}"


@st.cache_resource(show_spinner="Chargement des données…")
def donnees():
    zones = sources.quartiers()
    calendrier = sources.airbnb_calendrier()
    return {
        "zones": zones,
        "airbnb": preparer_airbnb(sources.airbnb_annonces(), calendrier, zones),
        "calendrier": calendrier,
        "loyers": sources.loyers_reference(),
    }


d = donnees()
zones = d["zones"].set_index("id_quartier").sort_index()

# Un clic sur la carte choisit le quartier : on l'applique avant de créer les widgets.
if "quartier_clique" in st.session_state:
    st.session_state["quartier"] = st.session_state.pop("quartier_clique")

st.title("Meublé à Paris : location longue durée ou Airbnb ?")
st.caption(f"Simulation de l'imposition 2026 des revenus 2025. Données : Inside Airbnb "
           f"({sources.DATE_AIRBNB}) et encadrement des loyers de Paris (arrêté 2025).")

etape1, etape2, etape3, onglet_carte, onglet_methode = st.tabs(
    ["① Mon logement et ma situation", "② Revenus avant impôt", "③ Résultat après impôt",
     "🗺️ Carte des quartiers", "ℹ️ Méthode et limites"])

# ---------- Étape 1 : formulaire ----------
with etape1:
    gauche, droite = st.columns([1, 1], gap="large")
    with gauche:
        st.subheader("🏠 Mon appartement")
        id_quartier = st.selectbox(
            "Quartier (ou cliquez sur la carte)", zones.index, key="quartier",
            format_func=lambda i: f"{zones.loc[i, 'arrondissement']}e – {zones.loc[i, 'nom_quartier']}")
        c1, c2 = st.columns(2)
        pieces = c1.selectbox("Nombre de pièces", [1, 2, 3, 4], index=1,
                              format_func=lambda p: f"{p} pièce{'s' if p > 1 else ''}"
                              if p < 4 else "4 pièces et plus")
        surface = c2.number_input("Surface (m²)", 9, 300, SURFACE_PAR_DEFAUT[pieces], step=1,
                                  key=f"surface_{pieces}")
        c3, c4 = st.columns(2)
        epoque = c3.selectbox("Période de construction", list(EPOQUES), format_func=EPOQUES.get)
        dpe = c4.selectbox("Classe énergie (DPE)", list("ABCDEFG"), index=3)
        residence_principale = st.radio(
            "Ce logement est-il votre résidence principale ?", ["Non", "Oui"], horizontal=True,
            help="À Paris, une résidence principale ne peut être louée sur Airbnb que "
                 f"{NUITS_MAX_RP} nuits par an.") == "Oui"
        loyer_majore = st.radio(
            "Loyer longue durée", ["Loyer majoré (maximum légal)", "Loyer de référence"],
            horizontal=True,
            help="Encadrement des loyers : le loyer hors charges ne peut pas dépasser le loyer "
                 "majoré (loyer de référence + 20 %).") == "Loyer majoré (maximum légal)"
        charges = st.number_input(
            "Charges annuelles du propriétaire (€/an)", 0, 50_000, int(surface * 30), step=100,
            help="Taxe foncière, charges de copropriété non récupérables, assurance, entretien, "
                 "intérêts d'emprunt. Identiques pour les deux options.")

        st.subheader("👤 Ma situation fiscale")
        c5, c6 = st.columns(2)
        couple = c5.radio("Situation", ["Célibataire, divorcé(e), veuf(ve)", "Marié(e) ou pacsé(e)"]
                          ) == "Marié(e) ou pacsé(e)"
        enfants = c6.number_input("Enfants à charge", 0, 10, 0)
        parent_isole = False
        if not couple and enfants > 0:
            parent_isole = st.checkbox("J'élève seul(e) mes enfants (case T)")
        autres_revenus = st.number_input(
            "Autres revenus nets imposables du foyer (€/an)", 0, 2_000_000, 40_000, step=1_000,
            help="Salaires après abattement de 10 %, pensions, revenus fonciers… "
                 "(ligne « revenu net imposable » de votre avis d'impôt).")

        with st.expander("Paramètres avancés (frais, régime réel, cotisations)"):
            a1, a2 = st.columns(2)
            frais_airbnb = a1.slider("Frais Airbnb (% des recettes)", 0, 50, 25,
                                     help="Commission, ménage, linge, énergie, internet, "
                                          "conciergerie…") / 100
            frais_ld = a2.slider("Frais longue durée (% des recettes)", 0, 30, 5,
                                 help="Vacance locative, frais de gestion.") / 100
            valeur = a1.number_input("Valeur du logement (€)", 0, 10_000_000,
                                     int(surface * 10_000), step=10_000,
                                     help="Sert à l'amortissement au régime réel.")
            mobilier = a2.number_input("Valeur du mobilier (€)", 0, 200_000, 6_000, step=500)
            part_terrain = a1.slider("Part du terrain (non amortissable)", 0, 40, 15,
                                     format="%d %%") / 100
            taux_cotisations = a2.slider(
                "Taux des cotisations sociales (si recettes > 23 000 €)", 20, 50,
                int(TAUX_COTISATIONS_INDICATIF * 100), format="%d %%",
                help="Taux indicatif : il n'est pas publié officiellement (35 à 45 % du "
                     "bénéfice selon les sources privées).") / 100

    with droite:
        st.subheader("📍 Localisation")
        q = zones.loc[id_quartier]
        st.markdown(f"**{q['nom_quartier']}**, {q['arrondissement']}e arrondissement")
        m = folium.Map(location=CENTRE_PARIS, zoom_start=12, tiles="OpenStreetMap")
        folium.GeoJson(
            d["zones"][["id_quartier", "nom_quartier", "geometry"]].to_json(),
            style_function=lambda f: {
                "fillColor": ORANGE if f["properties"]["id_quartier"] == id_quartier else BLEU,
                "fillOpacity": 0.6 if f["properties"]["id_quartier"] == id_quartier else 0.08,
                "color": "#555", "weight": 0.6},
            tooltip=folium.GeoJsonTooltip(fields=["nom_quartier"], labels=False),
        ).add_to(m)
        clic = st_folium(m, height=520, use_container_width=True,
                         returned_objects=["last_clicked"], key="carte_choix")
        point = (clic or {}).get("last_clicked")
        if point and point != st.session_state.get("dernier_clic"):
            st.session_state["dernier_clic"] = point
            dedans = d["zones"][d["zones"].contains(Point(point["lng"], point["lat"]))]
            if len(dedans) and dedans["id_quartier"].iloc[0] != id_quartier:
                st.session_state["quartier_clique"] = int(dedans["id_quartier"].iloc[0])
                st.rerun()

# ---------- Calculs ----------
logement = Logement(id_quartier=id_quartier, pieces=pieces, surface=surface, epoque=epoque,
                    residence_principale=residence_principale, loyer_majore=loyer_majore)
foyer = Foyer(couple=couple, enfants=enfants, parent_isole=parent_isole,
              autres_revenus=autres_revenus)
bien = Bien(charges_proprietaire=charges, valeur=valeur, part_terrain=part_terrain,
            mobilier=mobilier)
ex = Exploitation(frais_airbnb=frais_airbnb, frais_longue_duree=frais_ld)

estimations = estimer_quartiers(d["airbnb"], d["loyers"], d["zones"], logement)
e = estimations.set_index("id_quartier").loc[id_quartier]
recettes = {"longue_duree": e["recettes_longue_duree"],
            "airbnb_basse": e["recettes_airbnb_basse"],
            "airbnb_haute": e["recettes_airbnb_haute"]}
tableau = bilan(recettes, bien, foyer, ex, taux_cotisations)
nets = tableau.loc["Revenu net après impôt"]
nuits_max = NUITS_MAX_RP if residence_principale else 365
seuil = nuits_seuil(e["prix_nuit"], e["recettes_longue_duree"], bien, foyer, ex,
                    taux_cotisations, nuits_max)

alertes_legales = []
if residence_principale:
    alertes_legales.append(
        f"Résidence principale : Airbnb est limité à {NUITS_MAX_RP} nuits par an. La location "
        "longue durée suppose, elle, que vous quittiez le logement.")
else:
    alertes_legales.append(
        "Ce n'est pas votre résidence principale : à Paris, le louer sur Airbnb exige une "
        "autorisation de changement d'usage avec compensation (achat de m² transformés en "
        "logement dans le même quartier), très coûteuse. Sans autorisation : jusqu'à "
        "100 000 € d'amende.")
if dpe == "G":
    alertes_legales.append("DPE G : la location longue durée est interdite depuis le "
                           "1er janvier 2025.")
elif dpe == "F":
    alertes_legales.append("DPE F : la location longue durée sera interdite à partir du "
                           "1er janvier 2028.")
elif dpe == "E":
    alertes_legales.append("DPE E : la location longue durée sera interdite à partir du "
                           "1er janvier 2034.")


def afficher_tableau(lignes: list[str]) -> None:
    t = tableau.loc[lignes].copy()
    for ligne in lignes:
        if ligne != "Régime fiscal":
            t.loc[ligne] = t.loc[ligne].map(euros)
    st.dataframe(t, width="stretch")


LIBELLES_COURTS = dict(zip(OPTIONS.values(), ["Longue durée", "Airbnb (bas)", "Airbnb (haut)"]))


def barres(valeurs: pd.Series, titre: str) -> alt.Chart:
    df = valeurs.rename("valeur").rename_axis("Option").reset_index()
    df["texte"] = df["valeur"].map(euros)
    df["court"] = df["Option"].map(LIBELLES_COURTS)
    base = alt.Chart(df).encode(
        x=alt.X("court:N", title=None, sort=list(LIBELLES_COURTS.values()),
                axis=alt.Axis(labelAngle=0)),
        y=alt.Y("valeur:Q", title=titre, axis=alt.Axis(format=",.0f")))
    return (base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=70).encode(
                color=alt.Color("Option:N", legend=None,
                                scale=alt.Scale(domain=list(COULEURS_OPTIONS),
                                                range=list(COULEURS_OPTIONS.values()))),
                tooltip=["Option:N", alt.Tooltip("texte:N", title=titre)])
            + base.mark_text(dy=-8, fontSize=13).encode(text="texte:N")
            ).properties(height=300)


# ---------- Étape 2 : revenus avant impôt ----------
with etape2:
    st.subheader(f"Revenus avant impôt — {pieces} pièce{'s' if pieces > 1 else ''} de "
                 f"{surface} m², {q['nom_quartier']} ({q['arrondissement']}e)")
    if pd.isna(e["loyer_m2"]):
        st.error("Pas de loyer de référence pour cette combinaison dans les données.")
        st.stop()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Loyer longue durée", euros(e["recettes_longue_duree"] / 12) + "/mois",
              help=f"{e['loyer_m2']:.1f} €/m² ({'majoré' if loyer_majore else 'référence'}, "
                   f"meublé, {EPOQUES[epoque]}) × {surface} m²")
    k2.metric("Prix Airbnb médian", euros(e["prix_nuit"]) + "/nuit",
              help=f"Médiane de {e['annonces']} annonces de {pieces} pièce(s) — échelle : "
                   f"{e['comparables']}")
    k3.metric("Nuits louées par an", f"{e['nuits_basse']:.0f} à {e['nuits_haute']:.0f}",
              help="Basse : estimation d'Inside Airbnb (fondée sur les avis). Haute : nuits "
                   "indisponibles dans le calendrier (réservées ou bloquées).")
    k4.metric("Annonces comparables", f"{e['annonces']}",
              help=f"Même nombre de pièces, à l'échelle du {e['comparables']}.")
    if e["comparables"] != "quartier":
        st.info(f"Moins de 5 annonces comparables dans le quartier : l'estimation Airbnb "
                f"utilise celles de l'{e['comparables']}." if e["comparables"] == "arrondissement"
                else "Peu d'annonces comparables : l'estimation Airbnb utilise tout Paris.")

    g, dr = st.columns([3, 2], gap="large")
    with g:
        afficher_tableau(["Recettes annuelles", "Frais d'exploitation",
                          "Charges du propriétaire", "Revenu avant impôt"])
        st.altair_chart(barres(tableau.loc["Revenu avant impôt"].astype(float),
                               "Revenu avant impôt (€/an)"), width="stretch")
    with dr:
        st.markdown("**Saisonnalité Airbnb dans le quartier**")
        st.altair_chart(
            alt.Chart(saisonnalite(d["airbnb"], d["calendrier"], id_quartier)
                      .melt("mois", var_name="Série", value_name="valeur"))
            .mark_line(point=alt.OverlayMarkDef(size=50), strokeWidth=2)
            .encode(x=alt.X("mois:O", title=None, axis=alt.Axis(labelAngle=-45)),
                    y=alt.Y("valeur:Q", title="Nuits indisponibles",
                            axis=alt.Axis(format=".0%"), scale=alt.Scale(zero=False)),
                    color=alt.Color("Série:N", title=None, legend=alt.Legend(orient="top"),
                                    scale=alt.Scale(domain=["Quartier", "Paris"],
                                                    range=[ORANGE, BLEU])),
                    tooltip=["mois:O", "Série:N",
                             alt.Tooltip("valeur:Q", format=".0%", title="Indisponibles")])
            .properties(height=260), width="stretch")
        st.caption(f"Calendrier au {sources.DATE_AIRBNB}. Les mois lointains sont "
                   "sous-estimés : beaucoup de réservations ne sont pas encore prises.")
        for a in alertes_legales:
            st.warning(a)

# ---------- Étape 3 : après impôt ----------
with etape3:
    st.subheader("Résultat après impôt")
    longue = nets[OPTIONS["longue_duree"]]
    basse, haute = nets[OPTIONS["airbnb_basse"]], nets[OPTIONS["airbnb_haute"]]
    if basse > longue:
        st.success(f"**Airbnb est plus rentable, même avec l'occupation basse** : "
                   f"{euros(basse - longue, True)} à {euros(haute - longue, True)} par an "
                   "après impôt.")
    elif haute < longue:
        st.success(f"**La location meublée longue durée est plus rentable** : elle rapporte "
                   f"{euros(longue - haute, True)} à {euros(longue - basse, True)} de plus "
                   "par an après impôt, même face à l'occupation haute d'Airbnb.")
    else:
        st.info(f"**Ça dépend de l'occupation.** Airbnb devient plus rentable après impôt "
                f"au-delà de **{seuil} nuits louées par an** (l'estimation est entre "
                f"{e['nuits_basse']:.0f} et {e['nuits_haute']:.0f}).")
    if seuil is not None and (basse > longue or haute < longue):
        st.caption(f"Seuil de rentabilité d'Airbnb après impôt : {seuil} nuits louées par an.")
    elif seuil is None:
        st.caption(f"Airbnb ne dépasse jamais la longue durée, même à {nuits_max} nuits par an.")

    g, dr = st.columns([3, 2], gap="large")
    with g:
        afficher_tableau(["Recettes annuelles", "Frais d'exploitation",
                          "Charges du propriétaire", "Revenu avant impôt", "Régime fiscal",
                          "Revenu imposable", "Impôt sur le revenu",
                          "Prélèvements / cotisations sociales", "Revenu net après impôt",
                          "Revenu net par mois"])
        natures = tableau.loc["Nature des prélèvements"]
        st.caption("Prélèvements sociaux (18,6 %) ou cotisations sociales au-delà de 23 000 € "
                   "de recettes : " + ", ".join(f"{k} → {v}" for k, v in natures.items()) + ".")
    with dr:
        st.altair_chart(barres(nets.astype(float), "Revenu net après impôt (€/an)"),
                        width="stretch")
        st.markdown(f"Foyer : **{foyer.parts:g} part{'s' if foyer.parts > 1 else ''}**, "
                    f"{euros(autres_revenus)} d'autres revenus imposables.")
        for option, alertes in tableau.loc["Alertes"].items():
            for a in alertes:
                st.caption(f"⚠️ {option} : {a}")
        for a in alertes_legales:
            st.warning(a)

# ---------- Carte des quartiers ----------
with onglet_carte:
    st.subheader("Et si votre appartement était ailleurs dans Paris ?")
    st.caption("Même appartement, même situation fiscale, dans chacun des 80 quartiers. Airbnb "
               "est pris au milieu de sa fourchette d'occupation.")
    carte = estimations.join(nets_quartiers(estimations, bien, foyer, ex, taux_cotisations))
    carte["part_enregistrees"] = carte["id_quartier"].map(
        d["airbnb"].groupby("id_quartier")["numero_enregistrement"].mean())
    VUES = {
        "Gain annuel d'Airbnb après impôt (€)": ("gain_airbnb", True),
        "Revenu net après impôt – longue durée (€/an)": ("net_longue_duree", False),
        "Revenu net après impôt – Airbnb (€/an)": ("net_airbnb", False),
        "Prix Airbnb médian (€/nuit)": ("prix_nuit", False),
        "Loyer longue durée (€/m²)": ("loyer_m2", False),
        "Annonces avec n° d'enregistrement (%)": ("part_enregistrees", False),
    }
    vue = st.selectbox("Colorer la carte selon", list(VUES))
    col, divergente = VUES[vue]
    v = carte[col].dropna()
    if divergente:
        # Bleu = longue durée gagnante, orange = Airbnb gagnant, gris neutre à 0.
        lo, hi = min(v.min(), -1), max(v.max(), 1)
        palette = cm.LinearColormap([BLEU, "#efefed", ORANGE], index=[lo, 0, hi], vmin=lo, vmax=hi)
    else:
        palette = cm.LinearColormap(["#eef4fc", "#7fb0ea", "#174a8b"], vmin=v.min(), vmax=v.max())
    palette.caption = vue

    infos = {
        "Quartier": carte["nom_quartier"] + " (" + carte["arrondissement"].astype(str) + "e)",
        "Net longue durée": carte["net_longue_duree"].map(euros),
        "Net Airbnb": carte["net_airbnb"].map(euros),
        "Gain Airbnb": carte["gain_airbnb"].map(lambda x: euros(x, True)),
        "Prix / nuit": carte["prix_nuit"].map(euros),
        "Loyer": carte["loyer_m2"].map(lambda x: f"{x:.1f} €/m²".replace(".", ",")),
        "Annonces enregistrées": carte["part_enregistrees"].map(pourcent),
    }
    noms = {f"t{i}": k for i, k in enumerate(infos)}
    for cle, libelle in noms.items():
        carte[cle] = infos[libelle]

    m2 = folium.Map(location=CENTRE_PARIS, zoom_start=12, tiles="OpenStreetMap")
    folium.GeoJson(
        carte[list(noms) + [col, "id_quartier", "geometry"]].to_json(),
        style_function=lambda f: {
            "fillColor": palette(f["properties"][col]) if f["properties"][col] is not None
                         else "#cccccc",
            "fillOpacity": 0.75,
            "color": "#000" if f["properties"]["id_quartier"] == id_quartier else "#555",
            "weight": 3 if f["properties"]["id_quartier"] == id_quartier else 0.6},
        highlight_function=lambda f: {"weight": 2.5, "color": "#000"},
        tooltip=folium.GeoJsonTooltip(fields=list(noms), aliases=list(noms.values())),
    ).add_to(m2)
    palette.add_to(m2)
    st_folium(m2, height=600, use_container_width=True, returned_objects=[], key="carte_marche")

    gagnants = (carte["gain_airbnb"] > 0).sum()
    st.markdown(f"Pour ce profil, **Airbnb rapporte plus après impôt dans {gagnants} quartiers "
                f"sur {carte['gain_airbnb'].notna().sum()}**.")
    classement = (carte.drop(columns="geometry").sort_values("gain_airbnb", ascending=False)
                  [["nom_quartier", "arrondissement", "prix_nuit", "loyer_m2",
                    "net_longue_duree", "net_airbnb", "gain_airbnb"]])
    st.dataframe(classement, hide_index=True, width="stretch", column_config={
        "nom_quartier": "Quartier",
        "arrondissement": st.column_config.NumberColumn("Arr.", format="%de"),
        "prix_nuit": st.column_config.NumberColumn("Prix/nuit", format="%.0f €"),
        "loyer_m2": st.column_config.NumberColumn("Loyer €/m²", format="%.1f €"),
        "net_longue_duree": st.column_config.NumberColumn("Net longue durée", format="%.0f €"),
        "net_airbnb": st.column_config.NumberColumn("Net Airbnb", format="%.0f €"),
        "gain_airbnb": st.column_config.NumberColumn("Gain Airbnb", format="%+.0f €"),
    })
    st.download_button("Télécharger le classement (CSV)", classement.to_csv(index=False).encode(),
                       file_name="longue_duree_vs_airbnb_paris.csv")

# ---------- Méthode ----------
with onglet_methode:
    st.markdown(f"""
#### 1. Recettes
- **Longue durée** : loyer de l'encadrement des loyers (arrêté 2025, dernier publié en open
  data) pour un **meublé** du quartier, du même nombre de pièces et de la même période de
  construction, × surface × 12. Loyer majoré = loyer de référence + 20 % (maximum légal).
- **Airbnb** : annonces de **logements entiers actifs** (loués dans les 12 derniers mois, séjour
  minimum ≤ 30 nuits, prix entre 20 et 1 500 €) du même nombre de pièces dans le quartier
  (arrondissement, puis Paris, s'il y en a moins de 5). Recettes = médiane de prix/nuit × nuits
  louées par an, avec deux scénarios :
  - *occupation basse* : estimation d'Inside Airbnb à partir des avis, prudente ;
  - *occupation haute* : nuits indisponibles dans le calendrier, qui compte aussi les nuits
    bloquées par l'hôte.
  Résidence principale : nuits plafonnées à {NUITS_MAX_RP} par an.

#### 2. Revenu avant impôt
Recettes − frais d'exploitation (part des recettes, réglable) − charges annuelles du
propriétaire (identiques pour les deux options).

#### 3. Impôt (imposition 2026 des revenus 2025)
- **Régime** : micro-BIC si les recettes le permettent (longue durée : ≤ 77 700 €, abattement
  50 % ; meublé de tourisme non classé : ≤ 15 000 €, abattement 30 %) ou réel (recettes −
  frais − charges − amortissement du bien hors terrain sur 30 ans et du mobilier sur 7 ans,
  sans créer de déficit). L'application retient le régime le moins coûteux.
- **Impôt sur le revenu** = impôt du foyer avec le revenu locatif − impôt sans lui (barème,
  quotient familial plafonné à 1 807 € par demi-part, décote).
- **Prélèvements sociaux** : 18,6 % du revenu imposable ; au-delà de 23 000 € de recettes,
  **cotisations sociales** à un taux indicatif réglable.

Le détail et les sources officielles sont dans `REGLES_FISCALES.md`.

#### Limites
Meublé de tourisme supposé non classé ; plus-value à la revente, taxe de séjour, CFE et
déductibilité partielle de la CSG non pris en compte ; le coût d'une autorisation de changement
d'usage n'est pas chiffré ; les loyers de référence ont un an de retard sur l'arrêté 2026.
""")
