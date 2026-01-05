from pydantic import BaseModel

class POIOut(BaseModel):
    id: int
    name: str
    category: str | None = None
    lat: float
    lon: float
    dist_m: float | None = None

class NearbyResponse(BaseModel):
    cached: bool
    items: list[POIOut]

class BBoxResponse(BaseModel):
    cached: bool
    items: list[POIOut]

class HealthResponse(BaseModel):
    ok: bool = True
    version: str = "1.0.0"
