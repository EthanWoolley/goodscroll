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

CREATE TABLE IF NOT EXISTS wikipedia_shown (
  id TEXT PRIMARY KEY,
  article_title TEXT NOT NULL,
  shown_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_keywords (
  project_id TEXT PRIMARY KEY,
  keywords TEXT NOT NULL,
  generated_at TEXT NOT NULL,
  description_snapshot TEXT,
  FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS project_context_overrides (
  project_id TEXT PRIMARY KEY,
  context TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS wiki_interest_cards (
  id TEXT PRIMARY KEY,
  parent_category TEXT NOT NULL,
  options TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'unanswered',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wiki_interest_answers (
  id TEXT PRIMARY KEY,
  card_id TEXT NOT NULL,
  selected_options TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (card_id) REFERENCES wiki_interest_cards(id)
);

CREATE TABLE IF NOT EXISTS wiki_category_reads (
  user_id TEXT NOT NULL DEFAULT 'default_user',
  category_title TEXT NOT NULL,
  read_count INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (user_id, category_title)
);
