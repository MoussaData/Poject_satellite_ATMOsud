POLLUANTS_CONFIG = {
    "NO2": {"var": "nitrogendioxide_tropospheric_column", "unite": "µmol/m²"},
    "CO": {"var": "carbonmonoxide_total_column", "unite": "µmol/m²"},
    "CH4": {"var": "methane_mixing_ratio", "unite": "mixing_ratio"},
    "O3": {"var": "ozone_total_vertical_column", "unite": "µmol/m²"},
    "SO2": {"var": "sulfurdioxide_total_vertical_column", "unite": "µmol/m²"},
    "HCHO": {"var": "formaldehyde_tropospheric_vertical_column","unite": "µmol/m²" },
    "AER_AI": {"var": "aerosol_index_340_380", "unite": "AOD"} # pour les PM, aérosols
}


from datetime import datetime
import rasterio
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob
import re
from rasterio.plot import show


def parse_filename(filename):
    """Extrait les composants temporels du nom de fichier avec regex"""
    pattern = r"(\w+)_mean_(\d{4})_(\d{2})_(\d{2})_T(\d+-\d+)"
    match = re.match(pattern, filename)
    if match:
        return {
            'polluant': match.group(1),
            'year': match.group(2),
            'month': match.group(3),
            'day': match.group(4),
            'time': match.group(5)
        }
    return None

def format_timestamp(date_str, time_str=None):
    """Formate les dates/heures avec gestion des erreurs"""
    try:
        date_obj = datetime.strptime(date_str, "%Y_%m_%d")
        if time_str:
            start, end = time_str.split('-')
            start_time = datetime.strptime(start, "%H%M%S").strftime("%H:%M UTC")
            end_time = datetime.strptime(end, "%H%M%S").strftime("%H:%M UTC")
            return {
                'date_display': date_obj.strftime("%d/%m/%Y"),
                'time_display': f"{start_time} - {end_time}",
                'file_suffix': f"{date_str}_T{time_str}"
            }
        return {
            'date_display': date_obj.strftime("%B %Y") if len(date_str) > 7 else date_str,
            'file_suffix': date_str
        }
    except ValueError as e:
        print(f"Erreur de format de date : {e}")
        return None

def visualize_raster(date, polluant="NO2", raster_dir=None, shp_path=None):
    polluant = polluant.upper()
    if polluant not in POLLUANTS_CONFIG:
        print(f"Polluant '{polluant}' non pris en charge")
        return

    # Configuration des chemins réels
    base_path = "N:/MOD_SERVER/SATELLITES/tropomi_s5_annuel/alternance_moussa/output"
    if raster_dir is None:
        raster_dir = os.path.join(base_path, polluant, "output_rasters")
    
    # Vérification de l'existence du répertoire
    if not os.path.exists(raster_dir):
        print(f"Répertoire introuvable : {raster_dir}")
        return

    # Construction du pattern de recherche basé sur la date
    if len(date) == 8:  # Journalier (YYYYMMDD)
        year = date[:4]
        month = date[4:6]
        day = date[6:8]
        search_pattern = f"{polluant}_mean_{year}_{month}_{day}_T*.tif"
    elif len(date) == 6:  # Mensuel (YYYYMM)
        year = date[:4]
        month = date[4:6]
        search_pattern = f"{polluant}_mean_{year}_{month}.tif"
    elif len(date) == 4:  # Annuel (YYYY)
        search_pattern = f"{polluant}_mean_{date}.tif"
    else:
        print("Format de date invalide")
        return

    # Recherche précise du fichier
    full_pattern = os.path.join(raster_dir, search_pattern)
    matching_files = glob.glob(full_pattern)
    
    print(f"Recherche : {full_pattern}")
    print(f"{len(matching_files)} fichiers trouvés")

    if not matching_files:
        print(f"Aucun raster correspondant à {date}")
        return
    
    # Sélection du fichier le plus récent
    raster_path = sorted(matching_files, key=os.path.getmtime)[-1]
    print(f"Fichier sélectionné : {os.path.basename(raster_path)}")

    # Extraction des métadonnées
    filename = os.path.basename(raster_path).split('.')[0]
    meta = parse_filename(filename)
    
    if not meta:
        print("Format de fichier invalide")
        return

    # Formatage des dates
    date_str = f"{meta['year']}_{meta['month']}_{meta['day']}"
    time_info = format_timestamp(date_str, meta.get('time'))
    
    if not time_info:
        return

    # Création du titre
    title_template = {
        8: f"Concentration de {polluant}\n{time_info['date_display']} ({time_info['time_display']})",
        6: f"Moyenne mensuelle de {polluant}\n{time_info['date_display']}",
        4: f"Moyenne annuelle de {polluant}\n{meta['year']}"
    }
    plot_title = title_template.get(len(date), "Visualisation des données")

    # Chargement des données
    try:
        with rasterio.open(raster_path) as src:
            data = src.read(1)
            data = np.ma.masked_where(data == src.nodata, data)
            extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]
    except Exception as e:
        print(f"Erreur de chargement : {e}")
        return

    # Visualisation
    fig, ax = plt.subplots(figsize=(14, 10))
    img = ax.imshow(data, extent=extent, 
                    #cmap=POLLUANTS_CONFIG[polluant]['cmap'], 
                    origin='upper',
                    aspect='auto')

    # Ajout du shapefile
    if shp_path and os.path.exists(shp_path):
        gdf = gpd.read_file(shp_path)
        gdf.boundary.plot(ax=ax, edgecolor='#FF4500', linewidth=1.2, linestyle='-')

    # Configuration du graphique
    ax.set_title(plot_title, fontsize=16, pad=25)
    ax.set_xlabel("Longitude", fontsize=14)
    ax.set_ylabel("Latitude", fontsize=14)
    
    cbar = fig.colorbar(img, ax=ax, shrink=0.8)
    
    cbar.ax.set_title(POLLUANTS_CONFIG[polluant]['unite'], fontsize=12, pad=10) 
    # Sauvegarde
    output_dir = os.path.join(base_path, polluant, "graphes")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, f"{polluant}_{time_info['file_suffix']}.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight', transparent=True)
    print(f"Sauvegarde réussie : {output_path}")
    
    plt.show()
    plt.close()

# Exemple d'utilisation avec debug
shp_path = "N:/MOD_SERVER/SATELLITES/tropomi_s5_annuel/Stage_Moussa/fichiers_shp/contour_region_4326.shp"
visualize_raster(date="20240801", polluant="SO2", shp_path=shp_path) # NO2, O3, CO
