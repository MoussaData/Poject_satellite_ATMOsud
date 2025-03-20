#  Projet : Téléchargement, Traitement et Visualisation des Données Satellitaires TROPOMI/S5P

Ce projet permet de télécharger, traiter et visualiser les données de pollution issues du satellite **TROPOMI/S5P** sous format **NetCDF**.  
Il génère des rasters pour différents polluants et propose des cartes de visualisation.

---



##  Structure du Projet

- `download_netcdf.py` : Télécharge les fichiers NetCDF avec une barre de progression.
- `process_netcdf_to_raster.py` : Génère des rasters journaliers à partir des fichiers NetCDF téléchargés.
- `visualize_raster.py` : Affiche les rasters avec la date et l’heure, superposant un shapefile des limites régionales.


##  1. Téléchargement des Données

Le script **`download_netcdf.py`** permet de récupérer les fichiers **NetCDF** depuis le service Copernicus Data Space Ecosystem (CDSE).

### 🛠 Paramètres à configurer :
1. **Polluant** : Modifier `POLLUTANT` (`'NO2'`, `'O3'`, etc.).
2. **Zone géographique** : Modifier `ZONE` (définie en `POLYGON`).
3. **Plage de dates** : Modifier `START_DATE` et `END_DATE`.
4. **Identifiants CDSE** : Modifier `USERNAME` (votre e-mail) et fournir le mot de passe à l'exécution.
5. **Dossier de stockage** : Vérifier `destination_folder`.

 **Liste des polluants disponibles** :  
_Aerosol Index (AERI), Méthane (CH4), Carbone (CO), Formaldehyde (HCHO),  
Dioxyde d’azote (NO2), Ozone (O3), Dioxyde de soufre (SO2)._


## 2 Script de Traitement : `process_netcdf_to_raster.py`
###  Objectif :
Ce script extrait et agrège les données de pollution atmosphérique depuis des fichiers **NetCDF** issus du satellite **TROPOMI/S5P** et les convertit en **rasters GeoTIFF**.

### Fonctionnalités :
 **Filtrage automatique des fichiers NetCDF** disponibles sur une période donnée.  
 **Agrégation des données journalières** lorsque plusieurs passages satellites existent sur une même journée.  
 **Prise en compte des heures de début et de fin des passages** pour générer des rasters horaires précis.  
 **Stockage des rasters** dans un répertoire organisé par polluant.  

###  Utilisation :
1. Spécifier la période d'analyse (YYYYMMDD).
2. Définir le polluant à traiter (ex. `"NO2"`, `"SO2"`).
3. Exécuter le script, qui génère automatiquement les rasters.

 **Exemple de sortie :**  
- `NO2_mean_2024_08_02_0930_1530.tif` (raster pour le 2 août 2024, de 09h30 à 15h30)  

---

## 3 Script de Visualisation : `visualize_raster.py`
###  Objectif :
Ce script permet d'afficher les rasters générés et d'ajouter un shapefile des limites régionales pour une meilleure interprétation.

###  Fonctionnalités :
 **Lecture automatique des rasters** disponibles pour une date donnée.  
 **Extraction des heures de début et de fin** depuis le nom du fichier raster.  
 **Affichage des concentrations de polluants sur une carte** avec échelle colorimétrique.  
 **Superposition d’un shapefile des limites régionales** (optionnel).  
 **Sauvegarde automatique des graphiques** pour archivage et reporting.  

###  Utilisation :
1. Spécifier la date du raster à afficher (YYYYMMDD).
2. Indiquer le polluant à visualiser (`"NO2"`, `"SO2"`, etc.).
3. Fournir un shapefile (`.shp`) des contours régionaux si nécessaire.
4. Exécuter le script, qui génère et affiche la carte.

 **Exemple de sortie :**  
- `NO2_20240802.png` (graphique de la concentration de NO₂ le 2 août 2024)  

---

#  Points Clés pour la Production :
 **Assurer la disponibilité des fichiers NetCDF et des rasters générés** avant d’exécuter la visualisation.  
 **Maintenir une structure organisée des répertoires** pour faciliter l’automatisation.  
 **Vérifier que les noms des fichiers suivent le format attendu** pour garantir le bon fonctionnement du script.  

 **Ces scripts permettent d’automatiser le traitement et l’analyse des données de pollution atmosphérique, offrant ainsi une meilleure compréhension de l'évolution des concentrations en fonction du temps.**  



##  Installation et Utilisation  

###  1️ Installation des Dépendances

Avant d'exécuter les scripts, installez les bibliothèques nécessaires :

```bash
pip install numpy rasterio xarray geopandas matplotlib scipy requests tqdm shapely
