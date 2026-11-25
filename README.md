# Meublé à Paris : location longue durée ou Airbnb ?

Application Python qui aide le propriétaire d'un appartement meublé à Paris à choisir entre
la **location meublée longue durée** et la **location courte durée sur Airbnb**, en comparant
les revenus **avant impôt** puis **après impôt**, selon sa situation fiscale.

## Lancer l'application

**Le plus simple** : double-cliquer sur `Lancer.command` (Mac) ou `Lancer.bat` (Windows).
Il faut Python 3.11 ou plus récent ([python.org](https://www.python.org/downloads/)). Le
premier lancement installe les bibliothèques (1 à 2 minutes), puis l'application s'ouvre
dans le navigateur. Fermer la fenêtre du terminal arrête l'application.

Sur Mac, la première fois, macOS peut bloquer le fichier : clic droit sur `Lancer.command`
→ **Ouvrir** → **Ouvrir**.

En ligne de commande :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

L'application ne télécharge rien : elle lit uniquement les données figées de `data/prepare/`.

## Le parcours

1. **Mon logement et ma situation** : quartier (liste ou clic sur la carte), surface, nombre
   de pièces, période de construction, DPE, résidence principale ou non, charges annuelles ;
   situation familiale, enfants, autres revenus imposables. Des paramètres avancés permettent
   d'ajuster les frais, l'amortissement et le taux de cotisations.
2. **Revenus avant impôt** : recettes, frais et revenu annuel pour la longue durée et pour
   Airbnb (fourchette d'occupation basse / haute), annonces comparables, saisonnalité.
3. **Résultat après impôt** : tableau comparatif (régime fiscal retenu, impôt sur le revenu,
   prélèvements ou cotisations sociales, revenu net), verdict et nombre de nuits à partir
   duquel Airbnb devient plus rentable.
4. **Carte des quartiers** : le gain d'Airbnb après impôt pour ce même appartement et ce même
   foyer dans chacun des 80 quartiers.

## Le calcul

- **Longue durée** : loyer majoré (ou de référence) de l'encadrement pour un meublé du
  quartier, de la même taille et de la même époque × surface × 12.
- **Airbnb** : médiane des annonces comparables (logements entiers actifs, même nombre de
  pièces, même quartier) de prix/nuit × nuits louées, avec deux scénarios d'occupation.
  Résidence principale : 90 nuits par an maximum.
- **Revenu avant impôt** = recettes − frais d'exploitation − charges du propriétaire.
- **Impôt** (imposition 2026 des revenus 2025) : régime micro-BIC ou réel (le moins
  coûteux), impôt sur le revenu supplémentaire du foyer, prélèvements sociaux de 18,6 % ou
  cotisations sociales au-delà de 23 000 € de recettes. Règles et sources officielles :
  [REGLES_FISCALES.md](REGLES_FISCALES.md).

## Les données (figées, Paris uniquement)

Trois sources seulement, collectées une fois le 04/11/2026 et qui ne doivent plus être
modifiées. Le détail de chaque fichier (source, lien, taille, empreinte SHA-256) est dans
[data/MANIFESTE.md](data/MANIFESTE.md).

| Thème | Source | Période | Fichier préparé |
|---|---|---|---|
| Annonces Airbnb | Inside Airbnb | extraction du 16/09/2026 | `airbnb_annonces.parquet` |
| Disponibilité Airbnb | Inside Airbnb (calendrier) | 09/2026 → 09/2027, par mois | `airbnb_calendrier_mensuel.parquet` |
| Loyers de référence | Encadrement des loyers, Ville de Paris | 2019 → 2025 | `loyers_reference.parquet` |
| Contours des 80 quartiers | Ville de Paris (même fichier) | — | `quartiers.geojson` |

- `data/brut/` : les fichiers tels que téléchargés (~183 Mo), conservés pour la traçabilité.
- `data/prepare/` : les fichiers nettoyés (~6 Mo), seuls lus par l'application.
- `preparer_donnees.py` : passe de `brut/` à `prepare/` et écrit le manifeste. Il ne
  touche pas à Internet ; inutile de le relancer.
- `verifier_donnees.py` : vérifie que rien n'a changé depuis la préparation.

```bash
python verifier_donnees.py
```

Choix de nettoyage à connaître :
- **Airbnb** : prix convertis en nombre (en euros), chaque annonce rattachée à son quartier.
- **Calendrier** : une nuit « indisponible » est soit réservée, soit bloquée par l'hôte.

## Organisation du code

- `app.py` : interface Streamlit (formulaire, tableaux, graphiques, cartes).
- `analyse.py` : estimation des recettes d'un logement et bilan avant/après impôt.
- `fiscalite.py` : barème de l'impôt, micro-BIC / réel, prélèvements et cotisations.
- `sources.py` : lecture des données figées.
- `preparer_donnees.py` / `verifier_donnees.py` : préparation et contrôle des données.

## Tests

```bash
python -m unittest test_fiscalite
```

Les tests reprennent les exemples chiffrés de la brochure officielle de l'impôt 2026.

## Limites

- L'occupation Airbnb est une fourchette : l'estimation d'Inside Airbnb est prudente, le
  calendrier compte aussi les nuits bloquées par l'hôte.
- Inside Airbnb ne donne pas la surface des logements : les comparables sont choisis par
  nombre de pièces.
- Le loyer de référence est celui de l'arrêté 2025 (dernier en open data).
- Le meublé de tourisme est supposé non classé ; le taux des cotisations sociales est
  indicatif ; plus-value, taxe de séjour, CFE et coût d'un changement d'usage non pris en
  compte.

## Licences des données

- Inside Airbnb (annonces et calendrier) : licence Creative Commons Attribution 4.0,
  http://insideairbnb.com.
- Encadrement des loyers (Ville de Paris, opendata.paris.fr) : licence ODbL.
