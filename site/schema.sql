-- Cloudflare D1 schema for signups and error reports (Phase 4: wrangler d1 execute).
CREATE TABLE IF NOT EXISTS subscribers (
  email TEXT NOT NULL,
  country TEXT NOT NULL,
  family TEXT NOT NULL DEFAULT '',
  lang TEXT NOT NULL DEFAULT 'en',
  created_at TEXT NOT NULL,
  PRIMARY KEY (email, country, family)
);
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL,
  country TEXT NOT NULL,
  verdict TEXT,
  kind TEXT NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL
);
