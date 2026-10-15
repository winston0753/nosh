-- PostGIS is pre-installed in the postgis/postgis image.
-- pgvector is not available in postgis/postgis; it is deferred to a future
-- phase when embedding-based craving retrieval has a defined evaluation set.
-- See DECISIONS.md D013.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
