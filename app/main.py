from fastapi import FastAPI
from .db import init_db
from .routes import router

app = FastAPI(
    title="GeoSearch API",
    version="1.0.0",
    description="Geospatial search API with PostGIS + Redis caching.",
)

@app.on_event("startup")
def startup():
    init_db()

app.include_router(router)
