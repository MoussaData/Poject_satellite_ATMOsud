import json
import requests
import os
from getpass import getpass
from tqdm import tqdm
from datetime import datetime
import re

UTILISATEUR = {
    "Moussa" :  {"USER" : "moussa.dieng@atmosud.org", "password" : "XM:~G'%SL>26pr2"}
   
}
# Définir les paramètres personnalisés
POLLUANT = "SO2" #"AER_AI"  #  "O3"   #"NO2" , #'CO', "SO2", "HCH0", "CH4" ....
ZONE = "POLYGON((4.15 43.01, 7.73 43.01, 7.73 44.76, 4.15 44.76, 4.15 43.01))"
START_DATE = "2024-08-01T00:00:00.000Z"
END_DATE = "2024-08-02T23:59:59.999Z"

# Définir les informations d'utilisateur

USERNAME = UTILISATEUR["Moussa"]["USER"]
password = UTILISATEUR["Moussa"]["password"]

#USERNAME = "moussa.dieng@atmosud.org"
#password = "XM:~G'%SL>26pr2"      # mot de passs compte COPERNICUS password = "XM:~G'%SL>26pr2"
def get_keycloak(username: str, password: str) -> str:
    data = {
        "client_id": "cdse-public",
        "username": username,
        "password": password,
        "grant_type": "password"
    }
    r = requests.post("https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token", data=data)
    r.raise_for_status()
    return r.json()["access_token"], r.json()["refresh_token"]

def refresh_keycloak(refresh_token: str) -> str:
    data = {
        "client_id": "cdse-public",
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    r = requests.post("https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token", data=data)
    r.raise_for_status()
    return r.json()["access_token"], r.json()["refresh_token"]

#passwd = str(getpass())
passwd = password 
keycloak_token, refresh_token = get_keycloak(USERNAME, passwd)

def download_netcdf(url: str, fname: str, chunk_size=1024):
    session = requests.Session()
    session.headers.update({'Authorization': 'Bearer {}'.format(keycloak_token)})

    resp = requests.get(url, allow_redirects=False)
    while resp.status_code in (301, 302, 303, 307):
        url = resp.headers['Location']
        resp = session.get(url, verify=True, stream=True, allow_redirects=False)
    
    total = int(resp.headers.get('content-length', 0))
    with open(fname, 'wb') as file, tqdm(desc=fname, total=total, unit='iB', unit_scale=True, unit_divisor=1024) as bar:
        for data in resp.iter_content(chunk_size=chunk_size):
            size = file.write(data)
            bar.update(size)

print("Recherche des produits...")

if POLLUANT == "AER_AI":
   products_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?&$filter=((Collection/Name%20eq%20%27SENTINEL-5P%27%20and%20(Attributes/OData.CSC.StringAttribute/any(att:att/Name%20eq%20%27instrumentShortName%27%20and%20att/OData.CSC.StringAttribute/Value%20eq%20%27TROPOMI%27)%20and%20(contains(Name,%27L2__{POLLUANT}_%27)%20and%20OData.CSC.Intersects(area=geography%27SRID=4326;{ZONE}%27)))%20and%20Online%20eq%20true)%20and%20ContentDate/Start%20ge%20{START_DATE}%20and%20ContentDate/Start%20lt%20{END_DATE})&$orderby=ContentDate/Start%20desc&$expand=Attributes&$count=True&$top=1000&$expand=Assets&$skip=0"
else :
   products_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?&$filter=((Collection/Name%20eq%20%27SENTINEL-5P%27%20and%20(Attributes/OData.CSC.StringAttribute/any(att:att/Name%20eq%20%27instrumentShortName%27%20and%20att/OData.CSC.StringAttribute/Value%20eq%20%27TROPOMI%27)%20and%20(contains(Name,%27L2__{POLLUANT}___%27)%20and%20OData.CSC.Intersects(area=geography%27SRID=4326;{ZONE}%27)))%20and%20Online%20eq%20true)%20and%20ContentDate/Start%20ge%20{START_DATE}%20and%20ContentDate/Start%20lt%20{END_DATE})&$orderby=ContentDate/Start%20desc&$expand=Attributes&$count=True&$top=1000&$expand=Assets&$skip=0"


session = requests.Session()
session.headers.update({'Authorization': 'Bearer {}'.format(keycloak_token)})
response = requests.get(products_url, headers=session.headers)

try:
    lines = response.json()
except json.JSONDecodeError:
    print("Erreur : Impossible de décoder la réponse JSON.")
    exit(1)

if "value" not in lines:
    print("Erreur : La clé 'value' est absente de la réponse API.")
    print("Réponse API :", lines)
    exit(1)

# Chemin de stockage automatiquement en fonction du polluant
destination_root =f"N:/MOD_SERVER/SATELLITES/tropomi_s5_annuel/alternance_moussa/output/{POLLUANT}"
if not os.path.exists(destination_root):
    os.makedirs(destination_root)

for value_data in lines["value"]:
    product_name = value_data["Name"]
    product_identyficator = str(value_data['Id'])

    match = re.search(r"(\d{8}T\d{6})", product_name)
    if not match:
        print(f"Erreur : Impossible d'extraire la date du fichier {product_name}")
        continue

    date_str = match.group(1)
    date_obj = datetime.strptime(date_str, "%Y%m%dT%H%M%S")
    folder_name = f"{date_obj.year}_{date_obj.month:02d}"
    destination_folder = os.path.join(destination_root, folder_name)

    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    file_path = os.path.join(destination_folder, product_name)

    url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({product_identyficator})/$value"
    keycloak_token, refresh_token = refresh_keycloak(refresh_token)

    download_netcdf(url, file_path)

    print(f"Téléchargement terminé : {file_path}")

