 
POLLUANTS_CONFIG = {
    "NO2": {"var": "nitrogendioxide_tropospheric_column", "unite": "µmol/m²"},
    "CO": {"var": "carbonmonoxide_total_column", "unite": "µmol/m²"},
    "CH4": {"var": "methane_mixing_ratio", "unite": "mixing_ratio"},
    "O3": {"var": "ozone_total_vertical_column", "unite": "µmol/m²"},
    "SO2": {"var": "sulfurdioxide_total_vertical_column", "unite": "µmol/m²"},
    "HCHO": {"var": "formaldehyde_tropospheric_vertical_column","unite": "µmol/m²" },
    "AER_AI": {"var": "aerosol_index_340_380", "unite": "AOD"} # pour les PM, aérosols
}



import os
import numpy as np
import rasterio
import xarray as xr
import pandas as pd
from shapely.geometry import Polygon, Point
import geopandas as gpd
from scipy.spatial import cKDTree
from rasterio.transform import from_origin
import re

#  Extraction des heures depuis le nom du fichier
def extract_times_from_filename(filename):
    match = re.search(r"(\d{8}T\d{6})_(\d{8}T\d{6})", filename)
    if match:
        return match.group(1)[9:], match.group(2)[9:]  # Extraction HHMMSS
    return None, None

#  Génération de la grille
def create_parallelogram_grid(lat_min, lat_max, lon_min, lon_max, dx, dy):
    polygons, centers = [], []
    for x in np.arange(lon_min, lon_max, dx):
        for y in np.arange(lat_min, lat_max, dy):
            p = Polygon([
                (x, y), (x + dx, y), (x + dx + dy / 2, y + dy), (x + dy / 2, y + dy)
            ])
            polygons.append(p)
            centers.append(Point(x + dx / 2, y + dy / 2))
    return gpd.GeoDataFrame(geometry=polygons), centers

#  Fonction principale de traitement
def process_netcdf_to_raster(year, pollutant, base_dir, qa_min=0.75, month=None, day=None):
    pollutant = pollutant.upper()
    if pollutant not in POLLUANTS_CONFIG:
        print(f" Polluant '{pollutant}' non reconnu.")
        return

    var_name = POLLUANTS_CONFIG[pollutant]["var"]
    periods = [f"{year}_{month}"] if month else [f"{year}_{m:02d}" for m in range(1, 13)]

    # Recherche des fichiers NetCDF
    files = []
    for period in periods:
        input_dir = os.path.join(base_dir, pollutant, period)
        if os.path.exists(input_dir):
            files.extend([os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith(".nc")])

    # 🔹 Filtrer les fichiers correspondant exactement à la date demandée
    if day:
        files = [f for f in files if f"{year}{month}{day}" in os.path.basename(f)]

    #  Si aucun fichier n'existe pour cette date, on arrête ici
    if not files:
        print(f" Aucun fichier NetCDF trouvé pour {pollutant} le {day}/{month}/{year}. Pas de raster généré.")
        return

    #  Détermination des heures min/max
    times = [extract_times_from_filename(os.path.basename(f)) for f in files]
    start_times = sorted([t[0] for t in times if t[0] is not None])
    end_times = sorted([t[1] for t in times if t[1] is not None])

    first_start_time = start_times[0] if start_times else "000000"
    last_end_time = end_times[-1] if end_times else "235959"

    #  Définition de la grille
    lat_min, lat_max = 42.3, 45.4
    lon_min, lon_max = 3.63, 8
    resolution_x, resolution_y = 0.1, 0.06
    grid, grid_centers = create_parallelogram_grid(lat_min, lat_max, lon_min, lon_max, resolution_x, resolution_y)

    sum_values = np.zeros(len(grid), dtype=np.float32)
    count_values = np.zeros(len(grid), dtype=np.int32)

    for file in files:
        ds = xr.open_dataset(file, group="PRODUCT")
        data_array = ds[var_name].isel(time=0).values.astype(np.float32)
        qa = ds["qa_value"].isel(time=0).values.astype(np.float32)
        lat = ds["latitude"].values.astype(np.float32)
        lon = ds["longitude"].values.astype(np.float32)
        ds.close()

        df = pd.DataFrame({
            "lat": lat.ravel(),
            "lon": lon.ravel(),
            "value": data_array.ravel(),
            "qa_value": qa.ravel()
        })
        df = df[df["qa_value"] >= qa_min]
        df = df[(df["lat"] >= lat_min) & (df["lat"] <= lat_max) & 
                (df["lon"] >= lon_min) & (df["lon"] <= lon_max)]

        if df.empty:
            continue

        tree = cKDTree(np.array([[p.x, p.y] for p in grid_centers]))
        indices = tree.query(df[['lon', 'lat']].values)[1]

        for i, idx in enumerate(indices):
            sum_values[idx] += df['value'].iloc[i]
            count_values[idx] += 1

    mean_values = np.full(len(grid), np.nan, dtype=np.float32)
    valid_cells = count_values > 0
    mean_values[valid_cells] = sum_values[valid_cells] / count_values[valid_cells]
    grid["mean_value"] = mean_values

    #  Vérification finale avant export
    if np.isnan(mean_values).all():
        print(f" Aucun pixel valide trouvé. Pas de raster généré pour {pollutant} le {day}/{month}/{year}.")
        return

    # Définition du fichier de sortie
    if day:
        output_name = f"{pollutant}_mean_{year}_{month}_{day}_T{first_start_time}-{last_end_time}.tif"
    elif month:
        output_name = f"{pollutant}_mean_{year}_{month}.tif"
    else:
        output_name = f"{pollutant}_mean_{year}.tif"

    print(f" Génération du raster : {output_name}")

    # Création du raster
    raster_size_x = len(np.arange(lon_min, lon_max, resolution_x))
    raster_size_y = len(np.arange(lat_min, lat_max, resolution_y))
    transform = from_origin(lon_min, lat_max, resolution_x, resolution_y)

    raster_data = np.full((raster_size_y, raster_size_x), np.nan, dtype=np.float32)
    for idx, row in grid.iterrows():
        poly = row.geometry
        x_idx = int((poly.centroid.x - lon_min) / resolution_x)
        y_idx = int((lat_max - poly.centroid.y) / resolution_y)
        if 0 <= x_idx < raster_size_x and 0 <= y_idx < raster_size_y:
            raster_data[y_idx, x_idx] = row["mean_value"]

    output_dir = os.path.join(base_dir, pollutant, "output_rasters")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_name)

    with rasterio.open(output_path, 'w', driver='GTiff', height=raster_size_y, width=raster_size_x,
                       count=1, dtype='float32', crs='EPSG:4326', transform=transform) as dst:
        dst.write(raster_data, 1)

    print(f" Raster enregistré sous {output_path}")

# Exemples d'utilisation :

base_dir = "N:/MOD_SERVER/SATELLITES/tropomi_s5_annuel/alternance_moussa/output"
process_netcdf_to_raster("2024", "SO2", base_dir, month="08", day="01")  # Raster journalier, AER_AI, O3   
