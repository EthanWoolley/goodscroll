CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  project_type TEXT NOT NULL,
  end_goal TEXT,
  deadline TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cards (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  type TEXT NOT NULL,
  question TEXT NOT NULL,
  options TEXT,
  status TEXT NOT NULL DEFAULT 'unanswered',
  round INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS answers (
  id TEXT PRIMARY KEY,
  card_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  answer TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (card_id) REFERENCES cards(id),
  FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS user_interests (
  id TEXT PRIMARY KEY,
  interests TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rss_feeds (
  id TEXT PRIMARY KEY,
  url TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);
