from sqlalchemy import text

NEARBY_SQL = """
SELECT
  id, name, category, lat, lon,
  ST_Distance(geom, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography) AS dist_m
FROM poi
WHERE
  geohash5 = ANY(:gh5)
  AND (:category IS NULL OR category = :category)
  AND ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography, :radius_m)
ORDER BY dist_m ASC
LIMIT :limit OFFSET :offset;
"""

BBOX_SQL = """
SELECT id, name, category, lat, lon
FROM poi
WHERE lat BETWEEN :min_lat AND :max_lat
  AND lon BETWEEN :min_lon AND :max_lon
  AND (:category IS NULL OR category = :category)
ORDER BY id DESC
LIMIT :limit OFFSET :offset;
"""

nearby_query = text(NEARBY_SQL)
bbox_query = text(BBOX_SQL)
