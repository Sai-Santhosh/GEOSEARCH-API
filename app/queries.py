"""
Optimized SQL queries for geospatial operations.
"""
from sqlalchemy import text

# Nearby search with geohash pre-filtering and PostGIS distance calculation
NEARBY_SQL = """
SELECT
    id,
    name,
    category,
    lat,
    lon,
    metadata,
    created_at,
    updated_at,
    ST_Distance(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) AS dist_m
FROM poi
WHERE
    geohash5 = ANY(:gh5)
    AND (:category IS NULL OR category = :category)
    AND ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)
ORDER BY dist_m ASC
LIMIT :limit OFFSET :offset;
"""

# Count for nearby search
NEARBY_COUNT_SQL = """
SELECT COUNT(*) as total
FROM poi
WHERE
    geohash5 = ANY(:gh5)
    AND (:category IS NULL OR category = :category)
    AND ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m);
"""

# Bounding box search
BBOX_SQL = """
SELECT
    id,
    name,
    category,
    lat,
    lon,
    metadata,
    created_at,
    updated_at,
    NULL as dist_m
FROM poi
WHERE
    lat BETWEEN :min_lat AND :max_lat
    AND lon BETWEEN :min_lon AND :max_lon
    AND (:category IS NULL OR category = :category)
ORDER BY id DESC
LIMIT :limit OFFSET :offset;
"""

# Count for bounding box search
BBOX_COUNT_SQL = """
SELECT COUNT(*) as total
FROM poi
WHERE
    lat BETWEEN :min_lat AND :max_lat
    AND lon BETWEEN :min_lon AND :max_lon
    AND (:category IS NULL OR category = :category);
"""

# Text search using trigram similarity
TEXT_SEARCH_SQL = """
SELECT
    id,
    name,
    category,
    lat,
    lon,
    metadata,
    created_at,
    updated_at,
    NULL as dist_m,
    similarity(name, :query) as relevance
FROM poi
WHERE
    name ILIKE :pattern
    OR similarity(name, :query) > 0.2
    AND (:category IS NULL OR category = :category)
ORDER BY relevance DESC, name ASC
LIMIT :limit OFFSET :offset;
"""

# Get POI by ID
GET_POI_SQL = """
SELECT
    id,
    name,
    category,
    lat,
    lon,
    metadata,
    created_at,
    updated_at
FROM poi
WHERE id = :id;
"""

# Insert POI
INSERT_POI_SQL = """
INSERT INTO poi (name, category, lat, lon, geohash5, geom, metadata)
VALUES (
    :name,
    :category,
    :lat,
    :lon,
    :geohash5,
    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
    :metadata
)
RETURNING id, name, category, lat, lon, metadata, created_at, updated_at;
"""

# Update POI
UPDATE_POI_SQL = """
UPDATE poi
SET
    name = COALESCE(:name, name),
    category = COALESCE(:category, category),
    lat = COALESCE(:lat, lat),
    lon = COALESCE(:lon, lon),
    geohash5 = COALESCE(:geohash5, geohash5),
    geom = CASE
        WHEN :lat IS NOT NULL OR :lon IS NOT NULL
        THEN ST_SetSRID(ST_MakePoint(
            COALESCE(:lon, lon),
            COALESCE(:lat, lat)
        ), 4326)::geography
        ELSE geom
    END,
    metadata = CASE
        WHEN :metadata IS NOT NULL
        THEN :metadata::jsonb
        ELSE metadata
    END,
    updated_at = NOW()
WHERE id = :id
RETURNING id, name, category, lat, lon, metadata, created_at, updated_at;
"""

# Delete POI
DELETE_POI_SQL = """
DELETE FROM poi
WHERE id = :id
RETURNING id;
"""

# Get categories with counts
CATEGORIES_SQL = """
SELECT
    category,
    COUNT(*) as count
FROM poi
WHERE category IS NOT NULL
GROUP BY category
ORDER BY count DESC;
"""

# Get POI statistics
POI_STATS_SQL = """
SELECT
    COUNT(*) as total_pois,
    COUNT(DISTINCT category) as category_count,
    MIN(created_at) as oldest_poi,
    MAX(created_at) as newest_poi,
    ST_XMin(ST_Extent(geom::geometry)) as min_lon,
    ST_YMin(ST_Extent(geom::geometry)) as min_lat,
    ST_XMax(ST_Extent(geom::geometry)) as max_lon,
    ST_YMax(ST_Extent(geom::geometry)) as max_lat
FROM poi;
"""

# Bulk insert
BULK_INSERT_SQL = """
INSERT INTO poi (name, category, lat, lon, geohash5, geom, metadata)
VALUES (
    :name,
    :category,
    :lat,
    :lon,
    :geohash5,
    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
    :metadata
);
"""

# Create text objects for queries
nearby_query = text(NEARBY_SQL)
nearby_count_query = text(NEARBY_COUNT_SQL)
bbox_query = text(BBOX_SQL)
bbox_count_query = text(BBOX_COUNT_SQL)
text_search_query = text(TEXT_SEARCH_SQL)
get_poi_query = text(GET_POI_SQL)
insert_poi_query = text(INSERT_POI_SQL)
update_poi_query = text(UPDATE_POI_SQL)
delete_poi_query = text(DELETE_POI_SQL)
categories_query = text(CATEGORIES_SQL)
poi_stats_query = text(POI_STATS_SQL)
bulk_insert_query = text(BULK_INSERT_SQL)