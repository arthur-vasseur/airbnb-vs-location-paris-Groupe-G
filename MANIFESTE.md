# Manifeste des données figées – Paris

Préparé le 04/11/2026 par `preparer_donnees.py`. Ces données ne doivent plus être modifiées : l'empreinte SHA-256 de chaque fichier permet de vérifier qu'il est resté identique (`python verifier_donnees.py`).

## Données brutes (`data/brut/`), telles que téléchargées

| Fichier | Contenu | Source | Taille | SHA-256 |
|---|---|---|---|---|
| `airbnb/listings_2026-09-16.csv.gz` | Inside Airbnb – annonces de Paris, extraction du 16/09/2026 | https://data.insideairbnb.com/france/ile-de-france/paris/2026-09-16/data/listings.csv.gz | 40.3 Mo | `3285e5096c1869a684d5e65eb38526f07aa16bdc41cd76686feba8a2b78bd019` |
| `airbnb/calendar_2026-09-16.csv.gz` | Inside Airbnb – calendrier de disponibilité sur 365 jours | https://data.insideairbnb.com/france/ile-de-france/paris/2026-09-16/data/calendar.csv.gz | 68.1 Mo | `a3b71a9c4e6468a0bdaf0623e5a9b84fb770984f1a523d80fcc0808705d00ca3` |
| `loyers_encadrement/encadrement_loyers_paris.json` | Ville de Paris – encadrement des loyers 2019-2025, avec contour des 80 quartiers | https://opendata.paris.fr/explore/dataset/logement-encadrement-des-loyers/ | 83.7 Mo | `79faf4b87b31863f738bcec99aae49539495846d2d0ebcdff478f9840f4542ab` |

## Données préparées (`data/prepare/`), lues par l'application

| Fichier | Taille | SHA-256 |
|---|---|---|
| `airbnb_annonces.parquet` | 4.0 Mo | `16ad44b2659228a653d80cfca31946b81ef19ce2a109d0dc5eef4f9f4fe0ea62` |
| `airbnb_calendrier_mensuel.parquet` | 1.4 Mo | `05fa0b867b30c8a39cb5a26dbbea3d579bd9cc73343912891935b752f6439fcd` |
| `loyers_reference.parquet` | 0.1 Mo | `c0fa00d8725b8ad4938924fae618fd3ec8888f2eff5bb530e42ce7de6d328289` |
| `quartiers.geojson` | 0.4 Mo | `707afb2423da5bf2bb76fe3ffbd64c45679459bdac9069932419bffe014eb9f4` |
