# Règles fiscales et juridiques retenues

Vérifiées le 04/11/2026 sur les sources officielles indiquées. L'application simule
l'**imposition 2026 des revenus 2025** : c'est la dernière année dont tous les paramètres
sont officiels (le budget 2027 n'est pas encore voté).

## 1. Impôt sur le revenu (barème 2026, revenus 2025)

Source : brochure pratique IR 2026 (impots.gouv.fr), service-public.gouv.fr F1419.

| Revenu imposable par part | Taux |
|---|---|
| jusqu'à 11 600 € | 0 % |
| 11 601 € à 29 579 € | 11 % |
| 29 580 € à 84 577 € | 30 % |
| 84 578 € à 181 917 € | 41 % |
| au-delà de 181 917 € | 45 % |

- **Quotient familial** : revenu ÷ nombre de parts, barème, × nombre de parts.
- **Plafonnement** : l'avantage de chaque demi-part au-delà de 1 part (célibataire) ou
  2 parts (couple) est plafonné à **1 807 €**. Parent isolé : 4 262 € pour la première part
  liée au 1er enfant.
- **Décote** : si l'impôt brut est inférieur à **1 982 €** (personne seule) ou **3 277 €**
  (couple), décote = **897 €** (seule) ou **1 483 €** (couple) − **45,25 %** de l'impôt brut.
- **Méthode du projet** : impôt dû au titre de la location = impôt(autres revenus + revenu
  locatif imposable) − impôt(autres revenus seuls).

## 2. Régime fiscal de la location meublée (LMNP)

Source : service-public.gouv.fr F32744 (vérifié le 15/04/2026).

| Type de location | Micro-BIC : plafond de recettes (revenus 2025) | Abattement |
|---|---|---|
| Meublé longue durée | 77 700 € | 50 % |
| Meublé de tourisme **non classé** (Airbnb) | **15 000 €** | **30 %** |
| Meublé de tourisme classé | 77 700 € | 50 % |

- Pour les revenus 2026, les plafonds de 77 700 € passent à 83 600 € ; celui de 15 000 € ne change pas.
- Micro-BIC : revenu imposable = recettes × (1 − abattement), charges non déductibles.
- **Régime réel** : obligatoire au-dessus du plafond, possible sur option en dessous. Charges
  réelles et amortissement du bien et du mobilier déductibles. Un déficit ne s'impute que sur
  des revenus de location meublée (report sur 10 ans).
- **LMNP ou LMP** : on est LMNP si les recettes du foyer sont ≤ 23 000 € **ou** inférieures
  aux autres revenus d'activité du foyer.

## 3. Prélèvements sociaux et cotisations sociales

Sources : impots.gouv.fr « Je donne un bien en location… » (modifié le 17/07/2026),
service-public.gouv.fr F34102 (vérifié le 20/02/2026).

- **Prélèvements sociaux en location meublée : 18,6 %** (CSG 10,6 % + CRDS 0,5 % +
  prélèvement de solidarité 7,5 %), sur le revenu net imposable (après abattement ou après
  charges). Ils étaient de 17,2 % avant la loi de financement de la Sécurité sociale 2026 ;
  la location nue reste à 17,2 %.
- **Au-delà de 23 000 € de recettes annuelles** : le loueur est considéré comme professionnel
  pour la Sécurité sociale et paie des **cotisations sociales** (Urssaf), à la place des
  prélèvements sociaux. Pour un meublé de tourisme non classé, le statut de travailleur
  indépendant s'applique.
  Les taux de cotisation ne figurent pas sur les pages officielles consultées : l'application
  utilisera un taux indicatif réglable (sources privées : 35 % à 45 % du bénéfice).

## 4. Règles propres à Paris

Sources : paris.fr (meublés touristiques, encadrement des loyers), loi n° 2024-1039 dite
« Le Meur ».

- **Résidence principale** : location en meublé de tourisme limitée à **90 nuits par an**
  depuis le 1er janvier 2025 (120 auparavant). Enregistrement obligatoire.
- **Logement qui n'est pas la résidence principale** : location touristique possible
  seulement avec une **autorisation de changement d'usage avec compensation** dans le même
  quartier, très coûteuse. Amende jusqu'à 100 000 € sans autorisation.
- **Encadrement des loyers** : loyer majoré = référence **+ 20 %** (plafond légal du loyer
  hors charges) ; loyer minoré = référence − 30 %. Les loyers de référence des meublés
  intègrent déjà une majoration. Un complément de loyer n'est possible que si le loyer de base
  atteint le loyer majoré.
- **Données figées** : notre fichier va jusqu'à l'arrêté 2025 (dernière année publiée en
  open data au 04/11/2026). Un arrêté de juin 2026 existe mais n'est pas encore en open data.

## 5. Performance énergétique (DPE)

- **Location longue durée** : logement classé **G** interdit à la location depuis le
  1er janvier 2025, **F** à partir de 2028, **E** à partir de 2034 (loi Climat et résilience).
- **Meublé de tourisme** : des exigences existent pour les nouveaux meublés soumis à
  changement d'usage, avec une échéance de 2034 pour tous les meublés. Les sources consultées
  ne concordent pas sur le détail : l'application affichera une simple alerte.

## 6. Hors du périmètre (à mentionner comme limites)

- Plus-value à la revente (y compris la réintégration des amortissements LMNP).
- Taxe de séjour, cotisation foncière des entreprises (CFE), taxe foncière.
- Option pour le versement libératoire (micro-entrepreneur).
- Classement du meublé de tourisme (l'application suppose un meublé **non classé**).
