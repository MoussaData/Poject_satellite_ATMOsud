from fastapi import FastAPI
from src.api.routers import download, process, visualize

app = FastAPI(title="Air Quality Dashboard API")

# Ajouter les routes
app.include_router(download.router, prefix="/download", tags=["Téléchargement"])
app.include_router(process.router, prefix="/process", tags=["Traitement"])
app.include_router(visualize.router, prefix="/visualisation", tags=["Visualisation"])

@app.get("/")
def home():
    return {"message": "Bienvenue sur l'API Air Quality Dashboard"}
