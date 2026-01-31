"""SQL queries for the DAM system."""

# Asset queries
INSERT_ASSET = """
INSERT INTO assets (
    source_id, source_type, source_scheme,
    filename, content_type, media_type, file_size,
    width, height, resolution, orientation, md5_checksum,
    album_path, album_name,
    source_tags, source_keywords, approval_status, owner_name,
    canto_created_at, canto_modified_at, canto_time,
    thumbnail_url, full_url, canto_preview_240, canto_preview_uri,
    asset_type, processing_status
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
    $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27
)
ON CONFLICT (source_id) DO UPDATE SET
    filename = EXCLUDED.filename,
    content_type = EXCLUDED.content_type,
    file_size = EXCLUDED.file_size,
    width = EXCLUDED.width,
    height = EXCLUDED.height,
    md5_checksum = EXCLUDED.md5_checksum,
    album_path = EXCLUDED.album_path,
    album_name = EXCLUDED.album_name,
    source_tags = EXCLUDED.source_tags,
    source_keywords = EXCLUDED.source_keywords,
    canto_modified_at = EXCLUDED.canto_modified_at,
    thumbnail_url = EXCLUDED.thumbnail_url,
    updated_in_db = NOW()
RETURNING id;
"""

GET_ASSET_BY_ID = """
SELECT * FROM assets WHERE id = $1;
"""

GET_ASSET_BY_SOURCE_ID = """
SELECT * FROM assets WHERE source_id = $1;
"""

UPDATE_ASSET_PROCESSING = """
UPDATE assets
SET processing_status = $2, processing_error = $3, updated_in_db = NOW()
WHERE id = $1;
"""

UPDATE_ASSET_CLASSIFICATION = """
UPDATE assets
SET asset_type = $2, processing_status = 'classified', updated_in_db = NOW()
WHERE id = $1;
"""

UPDATE_ASSET_SEARCH_TEXT = """
UPDATE assets
SET search_text = $2, processing_status = 'enriched', updated_in_db = NOW()
WHERE id = $1;
"""

UPDATE_ASSET_EMBEDDING = """
UPDATE assets
SET embedding = $2, embedding_version = $3, processing_status = 'indexed',
    indexed_at = NOW(), updated_in_db = NOW()
WHERE id = $1;
"""

UPDATE_ASSET_VISION = """
UPDATE assets
SET scene = $2, people = $3, objects = $4, text_content = $5,
    hardcoded_elements = $6, composition = $7, framing = $8, edges = $9,
    colors = $10, style = $11, quality = $12, brand = $13, sub_brand = $14,
    mood = $15, tone = $16, editorial = $17, editing_notes = $18,
    video_metadata = $19, auto_tags = $20, semantic_description = $21,
    search_queries = $22, reusability_score = $23,
    analyzed_at = NOW(), updated_in_db = NOW()
WHERE id = $1;
"""

# Search queries
HYBRID_SEARCH = """
WITH semantic_results AS (
    SELECT id, 1 - (embedding <=> $1::vector) as semantic_score
    FROM assets
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> $1::vector
    LIMIT 100
),
keyword_results AS (
    SELECT id, similarity(search_text, $2) as keyword_score
    FROM assets
    WHERE search_text IS NOT NULL AND search_text % $2
    LIMIT 100
)
SELECT a.*,
       COALESCE(s.semantic_score, 0) * 0.7 +
       COALESCE(k.keyword_score, 0) * 0.3 as combined_score
FROM assets a
LEFT JOIN semantic_results s ON a.id = s.id
LEFT JOIN keyword_results k ON a.id = k.id
WHERE s.id IS NOT NULL OR k.id IS NOT NULL
ORDER BY combined_score DESC
LIMIT $3;
"""

SEMANTIC_SEARCH = """
SELECT a.*, 1 - (embedding <=> $1::vector) as score
FROM assets a
WHERE embedding IS NOT NULL
ORDER BY embedding <=> $1::vector
LIMIT $2;
"""

KEYWORD_SEARCH = """
SELECT a.*, similarity(search_text, $1) as score
FROM assets a
WHERE search_text IS NOT NULL AND search_text % $1
ORDER BY similarity(search_text, $1) DESC
LIMIT $2;
"""

FILTERED_HYBRID_SEARCH = """
WITH semantic_results AS (
    SELECT id, 1 - (embedding <=> $1::vector) as semantic_score
    FROM assets
    WHERE embedding IS NOT NULL
      AND ($4::text IS NULL OR asset_type = $4)
      AND ($5::text IS NULL OR album_name = $5)
      AND ($6::text IS NULL OR media_type = $6)
    ORDER BY embedding <=> $1::vector
    LIMIT 100
),
keyword_results AS (
    SELECT id, similarity(search_text, $2) as keyword_score
    FROM assets
    WHERE search_text IS NOT NULL AND search_text % $2
      AND ($4::text IS NULL OR asset_type = $4)
      AND ($5::text IS NULL OR album_name = $5)
      AND ($6::text IS NULL OR media_type = $6)
    LIMIT 100
)
SELECT a.*,
       COALESCE(s.semantic_score, 0) * 0.7 +
       COALESCE(k.keyword_score, 0) * 0.3 as combined_score
FROM assets a
LEFT JOIN semantic_results s ON a.id = s.id
LEFT JOIN keyword_results k ON a.id = k.id
WHERE (s.id IS NOT NULL OR k.id IS NOT NULL)
  AND ($4::text IS NULL OR a.asset_type = $4)
  AND ($5::text IS NULL OR a.album_name = $5)
  AND ($6::text IS NULL OR a.media_type = $6)
ORDER BY combined_score DESC
LIMIT $3;
"""

# Album queries
GET_ALBUMS = """
SELECT
    album_name as name,
    album_path as path,
    COUNT(*) as asset_count,
    BOOL_OR(asset_type = 'template') as has_templates
FROM assets
WHERE album_name IS NOT NULL
GROUP BY album_name, album_path
ORDER BY album_name;
"""

UPSERT_ALBUM = """
INSERT INTO albums (path, name, asset_count, is_reusable)
VALUES ($1, $2, $3, $4)
ON CONFLICT (path) DO UPDATE SET
    asset_count = EXCLUDED.asset_count,
    is_reusable = EXCLUDED.is_reusable;
"""

# Stats queries
GET_PROCESSING_STATS = """
SELECT
    processing_status,
    COUNT(*) as count
FROM assets
GROUP BY processing_status;
"""

GET_ASSET_COUNT = """
SELECT COUNT(*) FROM assets;
"""

GET_PENDING_ASSETS = """
SELECT id, filename, media_type, processing_status, created_in_db
FROM assets
WHERE processing_status NOT IN ('indexed', 'failed')
ORDER BY
    CASE processing_status
        WHEN 'pending' THEN 1
        WHEN 'classified' THEN 2
        WHEN 'enriched' THEN 3
        ELSE 4
    END,
    created_in_db ASC
LIMIT $1;
"""
