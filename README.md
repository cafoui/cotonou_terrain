# Enquête terrain – infrastructures (Web Mapping + formulaire)

Carte (OpenStreetMap / Satellite) avec la base de départ, formulaire selon le questionnaire, photo obligatoire,
ajout de nouvelles infrastructures, position GPS de l'enquêteur, et **export de la base actualisée pour QGIS**.

## Déploiement gratuit (≈ 15 min)

**1. Base de données (Neon – gratuit, sans expiration)**
Render gratuit efface les fichiers à chaque redémarrage : les fiches et photos sont donc stockées dans une base externe.
- Créer un compte sur https://neon.tech → nouveau projet → copier la *connection string* (`postgresql://...`).

**2. GitHub**
- Créer un dépôt, y déposer tout le contenu de ce dossier (`git init`, `git add .`, `git commit`, `git push`).

**3. Render**
- https://render.com → *New* → *Blueprint* (ou *Web Service*) → choisir le dépôt. Plan **Free**.
- Renseigner les variables : `DATABASE_URL` = chaîne Neon ; `ACCESS_CODE` = un code que vous donnerez à vos enquêteurs.
- Après le déploiement, l'adresse `https://xxx.onrender.com` est le lien à partager. (1er chargement après 15 min d'inactivité : ~1 min.)

## Utilisation
- Toucher une infrastructure → remplir la fiche → Enregistrer (vert = renseigné).
- ➕ Ajouter : catégorie, puis « à ma position » ou « sur la carte » (les lignes se tracent point par point).
- ⬇ Export QGIS : GeoPackage (recommandé, 1 couche par catégorie) ou Shapefiles. Champ `statut` : `non_visite` / `verifie` / `nouveau`.
  Colonnes `x_utm31`, `y_utm31` (WGS 84 / UTM 31N), `photo_url` (lien de la photo), `gps_*` (position de l'agent).

## À compléter
- `static/data/quartiers.json` : listes de quartiers par arrondissement (`{"1":["Quartier A",...]}`). Vide = saisie libre.
- Si la base de départ change : `python prepare_data.py Vecteur` puis pousser `static/data/base.json`.

## Limites
Pas de mode hors-ligne (connexion requise) ; en cas de modification simultanée de la même fiche, la dernière enregistrée l'emporte.









