"""Fiscalité d'un loueur en meublé : impôt sur le revenu, régimes micro-BIC et réel,
prélèvements ou cotisations sociales.

Paramètres de l'imposition 2026 des revenus 2025, vérifiés le 04/11/2026 sur les sources
officielles listées dans REGLES_FISCALES.md.
"""

from dataclasses import dataclass, field

# ---------- Paramètres officiels ----------

# Barème 2026 (revenus 2025) : (borne basse de la tranche, taux), pour une part.
BAREME = [(0, 0.0), (11_600, 0.11), (29_579, 0.30), (84_577, 0.41), (181_917, 0.45)]
PLAFOND_DEMI_PART = 1_807          # avantage maximal par demi-part supplémentaire
PLAFOND_PARENT_ISOLE = 4_262       # pour la première part liée au 1er enfant (case T)
DECOTE = {"seul": (1_982, 897), "couple": (3_277, 1_483)}  # (seuil d'impôt brut, montant)
TAUX_DECOTE = 0.4525

# Micro-BIC (revenus 2025) : (plafond de recettes, abattement).
MICRO_BIC = {
    "longue_duree": (77_700, 0.50),
    "tourisme_non_classe": (15_000, 0.30),
}
TAUX_PRELEVEMENTS_SOCIAUX = 0.186  # location meublée, depuis la LFSS 2026
SEUIL_COTISATIONS = 23_000         # au-delà, cotisations sociales au lieu des prélèvements
TAUX_COTISATIONS_INDICATIF = 0.40  # non publié officiellement : 35 à 45 % du bénéfice

DUREE_AMORTISSEMENT_BIEN = 30      # ans (usage courant, hors terrain)
DUREE_AMORTISSEMENT_MOBILIER = 7


# ---------- Impôt sur le revenu ----------

@dataclass
class Foyer:
    couple: bool = False           # marié ou pacsé (imposition commune)
    enfants: int = 0               # enfants à charge
    parent_isole: bool = False     # élève seul ses enfants (case T)
    autres_revenus: float = 0.0    # revenu net imposable hors location, €/an

    @property
    def parts(self) -> float:
        base = 2.0 if self.couple else 1.0
        enfants = 0.5 * min(self.enfants, 2) + 1.0 * max(self.enfants - 2, 0)
        isole = 0.5 if (self.parent_isole and not self.couple and self.enfants > 0) else 0.0
        return base + enfants + isole


def _bareme(revenu: float, parts: float) -> float:
    quotient = max(revenu, 0) / parts
    impot = 0.0
    for i, (bas, taux) in enumerate(BAREME):
        haut = BAREME[i + 1][0] if i + 1 < len(BAREME) else float("inf")
        if quotient > bas:
            impot += (min(quotient, haut) - bas) * taux
    return impot * parts


def impot_revenu(revenu_imposable: float, foyer: Foyer) -> float:
    """Impôt net du foyer : barème, plafonnement du quotient familial, puis décote."""
    parts = foyer.parts
    base = 2.0 if foyer.couple else 1.0
    impot = _bareme(revenu_imposable, parts)

    # Plafonnement : l'avantage dû aux demi-parts au-delà de la base est limité.
    demi_parts = round((parts - base) * 2)
    if demi_parts > 0:
        if foyer.parent_isole and not foyer.couple and foyer.enfants > 0:
            plafond = PLAFOND_PARENT_ISOLE + PLAFOND_DEMI_PART * max(demi_parts - 2, 0)
        else:
            plafond = PLAFOND_DEMI_PART * demi_parts
        impot = max(impot, _bareme(revenu_imposable, base) - plafond)

    seuil, montant = DECOTE["couple" if foyer.couple else "seul"]
    if impot < seuil:
        impot -= max(montant - TAUX_DECOTE * impot, 0)
    return max(round(impot), 0)


# ---------- Location meublée ----------

@dataclass
class Bien:
    """Ce qu'il faut pour le régime réel : charges déductibles et amortissement."""
    charges_proprietaire: float = 0.0   # €/an : taxe foncière, copropriété, assurance, intérêts…
    valeur: float = 0.0                 # valeur du logement, €
    part_terrain: float = 0.15          # part non amortissable
    mobilier: float = 0.0               # valeur du mobilier, €

    @property
    def amortissement(self) -> float:
        return (self.valeur * (1 - self.part_terrain) / DUREE_AMORTISSEMENT_BIEN
                + self.mobilier / DUREE_AMORTISSEMENT_MOBILIER)


@dataclass
class Resultat:
    regime: str
    recettes: float
    revenu_imposable: float
    impot_revenu: float
    social: float
    social_nature: str                 # « prélèvements sociaux » ou « cotisations sociales »
    alertes: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return self.impot_revenu + self.social


def imposer(type_location: str, recettes: float, frais: float, bien: Bien, foyer: Foyer,
            taux_cotisations: float = TAUX_COTISATIONS_INDICATIF) -> Resultat:
    """Calcule l'impôt dû sur une location et retient le régime le plus favorable.

    type_location : "longue_duree" ou "tourisme_non_classe".
    frais : frais d'exploitation de l'année (commission, ménage, gestion…), déductibles au réel.
    """
    plafond, abattement = MICRO_BIC[type_location]
    candidats = {}
    if recettes <= plafond:
        candidats["Micro-BIC"] = recettes * (1 - abattement)
    # Au réel, l'amortissement ne peut pas créer de déficit ; un déficit de charges n'est
    # imputable que sur de futurs revenus de location meublée, on le compte donc pour 0.
    avant_amortissement = recettes - frais - bien.charges_proprietaire
    candidats["Réel"] = max(avant_amortissement - bien.amortissement, 0)

    cotisations = recettes > SEUIL_COTISATIONS
    impot_sans = impot_revenu(foyer.autres_revenus, foyer)
    resultats = []
    for regime, imposable in candidats.items():
        ir = impot_revenu(foyer.autres_revenus + imposable, foyer) - impot_sans
        social = imposable * (taux_cotisations if cotisations else TAUX_PRELEVEMENTS_SOCIAUX)
        resultats.append(Resultat(
            regime=regime, recettes=recettes, revenu_imposable=imposable, impot_revenu=ir,
            social=social,
            social_nature="cotisations sociales" if cotisations else "prélèvements sociaux"))
    meilleur = min(resultats, key=lambda r: r.total)

    if recettes > plafond:
        meilleur.alertes.append(
            f"Recettes au-dessus du plafond micro-BIC ({plafond:,.0f} €) : régime réel "
            "obligatoire.".replace(",", " "))
    if cotisations:
        meilleur.alertes.append(
            "Recettes au-dessus de 23 000 € : cotisations sociales dues (taux indicatif) "
            "au lieu des prélèvements sociaux.")
    return meilleur
