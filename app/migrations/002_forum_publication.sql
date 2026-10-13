ALTER TABLE threads ADD COLUMN published_at TEXT;
-- Older approval times are unknown; do not invent them from creation dates.
CREATE INDEX IF NOT EXISTS threads_public_feed ON threads(category_id,state,published_at,id);
